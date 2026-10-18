import json
from copy import deepcopy
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.models import IELTSStudyPlan, UserModuleAccess
from core.services.ielts_planner_validate import validate_document


def _sample_document(*, exam_days=90, done=False):
    today = date.today()
    exam = today + timedelta(days=exam_days)
    start = today.isoformat()
    exam_s = exam.isoformat()
    return {
        'version': 1,
        'view': 'list',
        'plan': {
            'contentVersion': 3,
            'profile': {
                'scores': {
                    'Listening': 6.5,
                    'Reading': 6.0,
                    'Writing': 5.5,
                    'Speaking': 6.0,
                },
                'target': 7.0,
                'exam': exam_s,
                'days': [0, 1, 3, 4, 5],
                'minutes': 60,
                'time': '19:00',
                'weak': ['Writing', 'Speaking'],
            },
            'startDate': start,
            'generatedAt': start,
            'tasks': [
                {
                    'id': f'{start}-Writing-0',
                    'date': start,
                    'time': '19:00',
                    'duration': 30,
                    'skill': 'Writing',
                    'resource': 'writingVideo',
                    'title': 'Writing video: Task 2',
                    'source': 'Video darslar → Writing',
                    'description': 'Ton Academy Writing darsini oching.',
                    'outcome': 'Konspekt va tuzatilgan paragraf.',
                    'checkpoint': 'Asosiy qoidani tushuntira olasizmi?',
                    'ifStuck': 'Qiyin joyni belgilang va qayta urinib ko‘ring.',
                    'reviewNext': 'Keyingi mashqda shu qoidani tekshiring.',
                    'minimumDuration': 15,
                    'steps': [
                        {'minutes': 10, 'text': 'Darsni ko‘ring.'},
                        {'minutes': 10, 'text': 'Paragraf yozing.'},
                        {'minutes': 10, 'text': 'Xatoni tuzating.'},
                    ],
                    'lessonIndex': 0,
                    'phaseKey': 'foundation',
                    'contentVersion': 3,
                    'done': done,
                }
            ],
        },
    }


@override_settings(ALLOWED_HOSTS=['*'])
class IELTSPlannerAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='planner-a', password='Pass12345!')
        self.other = User.objects.create_user(username='planner-b', password='Pass12345!')
        for user in (self.user, self.other):
            access, _ = UserModuleAccess.objects.get_or_create(user=user)
            access.can_access_ielts = True
            access.save(update_fields=['can_access_ielts'])
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username='planner-a', password='Pass12345!')
        self.client.get(reverse('core:study_planner'))
        self.csrf = self.client.cookies['csrftoken'].value
        self.api = reverse('core:study_planner_api')

    def _put(self, payload, client=None):
        client = client or self.client
        return client.put(
            self.api,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf if client is self.client else client.cookies.get('csrftoken').value,
        )

    def test_page_renders(self):
        response = self.client.get(reverse('core:study_planner'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('data-planner-api', body)
        self.assertIn('csrf-token', body)
        self.assertIn('ielts-planner/app.js', body)
        self.assertIn('id="plannerResourceRoutes"', body)
        self.assertIn('planner-app', body)
        self.assertIn('planner-hero', body)
        self.assertIn('sample-banner', body)
        self.assertIn('/mashqlar/reading/', body)
        self.assertIn('/tests/collection/writing/', body)
        self.assertIn('Kabinetga qaytish', body)
        self.assertIn('navbar', body)

    def test_get_empty_plan(self):
        response = self.client.get(self.api)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['revision'], 0)
        self.assertIsNone(data['document'])
        self.assertEqual(data['accountKey'], f'user-{self.user.pk}')
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_put_create_and_conflict(self):
        doc = _sample_document()
        self.assertIsNone(validate_document(doc))
        key = f'user-{self.user.pk}'
        created = self._put({'accountKey': key, 'baseRevision': 0, 'document': doc})
        self.assertEqual(created.status_code, 200, created.content)
        self.assertEqual(created.json()['revision'], 1)
        self.assertTrue(IELTSStudyPlan.objects.filter(user=self.user, revision=1).exists())

        conflict = self._put({'accountKey': key, 'baseRevision': 0, 'document': doc})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()['error'], 'REVISION_CONFLICT')

        updated = self._put({'accountKey': key, 'baseRevision': 1, 'document': doc})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['revision'], 2)

    def test_account_isolation(self):
        doc = _sample_document()
        key = f'user-{self.user.pk}'
        self._put({'accountKey': key, 'baseRevision': 0, 'document': doc})

        other = Client(enforce_csrf_checks=True)
        other.login(username='planner-b', password='Pass12345!')
        other.get(reverse('core:study_planner'))
        csrf = other.cookies['csrftoken'].value
        empty = other.get(self.api)
        self.assertEqual(empty.json()['revision'], 0)
        self.assertIsNone(empty.json()['document'])

        steal = other.put(
            self.api,
            data=json.dumps({'accountKey': key, 'baseRevision': 0, 'document': doc}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(steal.status_code, 409)
        self.assertEqual(steal.json()['error'], 'ACCOUNT_CHANGED')

    def test_invalid_document_rejected(self):
        key = f'user-{self.user.pk}'
        bad = deepcopy(_sample_document())
        bad['plan']['tasks'][0]['steps'][0]['minutes'] = 99
        response = self._put({'accountKey': key, 'baseRevision': 0, 'document': bad})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error'], 'INVALID_STEPS')

    def test_csrf_required_on_put(self):
        key = f'user-{self.user.pk}'
        response = self.client.put(
            self.api,
            data=json.dumps({'accountKey': key, 'baseRevision': 0, 'document': _sample_document()}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)


class IELTSPlannerValidateTests(TestCase):
    def test_valid_sample(self):
        self.assertIsNone(validate_document(_sample_document()))

    def test_rejects_wrong_content_version(self):
        doc = _sample_document()
        doc['plan']['contentVersion'] = 2
        self.assertEqual(validate_document(doc), 'INVALID_PLAN')
