import json
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models import UserModuleAccess, VocabularyLabProgress
from core.services.vocabulary_lab_validate import validate_document

User = get_user_model()


def _empty_doc():
    return {
        'version': 1,
        'level': 'B2',
        'count': 6,
        'mode': 'Learn',
        'items': {},
        'metrics': {'Recognition': {'ok': 0, 'n': 0}, 'Production': {'ok': 0, 'n': 0}},
        'history': [],
        'session': None,
        'plan': {'date': 'Mon Oct 26 2026', 'budget': 30, 'heavy': False, 'done': []},
        'events': [],
    }


class VocabularyLabTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='vocab-a', password='Pass12345!')
        access, _ = UserModuleAccess.objects.get_or_create(user=self.user)
        access.can_access_ielts = True
        access.save(update_fields=['can_access_ielts'])
        self.other = User.objects.create_user(username='vocab-b', password='Pass12345!')
        other_access, _ = UserModuleAccess.objects.get_or_create(user=self.other)
        other_access.can_access_ielts = True
        other_access.save(update_fields=['can_access_ielts'])
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username='vocab-a', password='Pass12345!')
        self.client.get(reverse('core:vocabulary_lab'))
        self.api = reverse('core:vocabulary_lab_api')

    def _csrf(self):
        return self.client.cookies['csrftoken'].value

    def _put(self, payload):
        return self.client.put(
            self.api,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self._csrf(),
        )

    def test_page_renders_in_cabinet_chrome(self):
        response = self.client.get(reverse('core:vocabulary_lab'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('vocabLabBoot', body)
        self.assertIn('vocabLabI18n', body)
        self.assertIn('vocabulary-lab/app.js', body)
        self.assertIn('navbar', body)
        self.assertIn('vocab-shell', body)
        self.assertIn('vocab-crumb', body)
        self.assertIn('class="vocab-lab"', body)
        self.assertIn('Ton academy', body)
        boot = json.loads(
            body.split('id="vocabLabBoot"', 1)[1].split('>', 1)[1].split('</script>', 1)[0]
        )
        self.assertEqual(boot['apiUrl'], '/ielts/vocabulary/api/')
        self.assertEqual(boot['dashboardUrl'], '/ielts/')
        self.assertEqual(boot['plannerUrl'], '/ielts/rejam/')
        self.assertEqual(boot['writingUrl'], '/mashqlar/writing/')
        i18n = json.loads(
            body.split('id="vocabLabI18n"', 1)[1].split('>', 1)[1].split('</script>', 1)[0]
        )
        self.assertEqual(i18n.get('navOverview'), 'Umumiy sahifa')
        self.assertEqual(i18n.get('learnTitle'), 'Yangi lug‘at o‘rganish')

    def test_page_russian_i18n(self):
        self.client.cookies['ai_lang'] = 'ru'
        response = self.client.get(reverse('core:vocabulary_lab'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('lang="ru"', body)
        self.assertIn('Vocabulary Lab', body)
        # json_script ensure_ascii: Обзор → \u041e\u0431\u0437\u043e\u0440
        self.assertIn('\\u041e\\u0431\\u0437\\u043e\\u0440', body)
        self.assertIn(
            '\\u041d\\u0430\\u0447\\u0430\\u0442\\u044c \\u0438\\u0437\\u0443\\u0447\\u0435\\u043d\\u0438\\u0435',
            body,
        )
        i18n = json.loads(
            body.split('id="vocabLabI18n"', 1)[1].split('>', 1)[1].split('</script>', 1)[0]
        )
        self.assertEqual(i18n.get('navOverview'), 'Обзор')
        self.assertEqual(i18n.get('startLearning'), 'Начать изучение')
        self.assertEqual(i18n.get('dailyPractice'), 'Практика на сегодня')
        self.assertEqual(i18n.get('recByPlan'), 'Рекомендовано вашим планом IELTS')

    def test_navbar_and_dashboard_links(self):
        page = self.client.get(reverse('core:vocabulary_lab'))
        body = page.content.decode()
        self.assertIn('/ielts/vocabulary/', body)
        self.assertIn('nav-link active', body)
        self.assertIn('/ielts/rejam/', body)
        dash = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dash.status_code, 200)
        dash_body = dash.content.decode()
        self.assertIn('/ielts/vocabulary/', dash_body)
        self.assertIn('/ielts/rejam/', dash_body)

    def test_login_and_module_access_required(self):
        anon = Client()
        self.assertEqual(anon.get(reverse('core:vocabulary_lab')).status_code, 302)
        self.assertEqual(anon.get(self.api).status_code, 302)

        blocked = User.objects.create_user(username='vocab-blocked', password='Pass12345!')
        access, _ = UserModuleAccess.objects.get_or_create(user=blocked)
        access.can_access_ielts = False
        access.save(update_fields=['can_access_ielts'])
        c = Client()
        c.login(username='vocab-blocked', password='Pass12345!')
        response = c.get(reverse('core:vocabulary_lab'))
        self.assertEqual(response.status_code, 302)

    def test_get_empty_and_put(self):
        response = self.client.get(self.api)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['revision'], 0)
        self.assertIsNone(data['document'])
        self.assertEqual(data['accountKey'], f'user-{self.user.pk}')
        self.assertEqual(response['Cache-Control'], 'private, no-store')

        doc = _empty_doc()
        self.assertIsNone(validate_document(doc))
        put = self._put({'accountKey': data['accountKey'], 'baseRevision': 0, 'document': doc})
        self.assertEqual(put.status_code, 200, put.content)
        self.assertEqual(put.json()['revision'], 1)
        self.assertTrue(VocabularyLabProgress.objects.filter(user=self.user, revision=1).exists())

        again = self.client.get(self.api).json()
        self.assertEqual(again['revision'], 1)
        self.assertEqual(again['document']['level'], 'B2')

    def test_put_conflict_and_update(self):
        key = f'user-{self.user.pk}'
        doc = _empty_doc()
        created = self._put({'accountKey': key, 'baseRevision': 0, 'document': doc})
        self.assertEqual(created.status_code, 200)
        conflict = self._put({'accountKey': key, 'baseRevision': 0, 'document': doc})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()['error'], 'REVISION_CONFLICT')
        doc2 = deepcopy(doc)
        doc2['level'] = 'C1'
        doc2['count'] = 7
        updated = self._put({'accountKey': key, 'baseRevision': 1, 'document': doc2})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['revision'], 2)
        self.assertEqual(self.client.get(self.api).json()['document']['level'], 'C1')

    def test_account_isolation(self):
        key = f'user-{self.user.pk}'
        self._put({'accountKey': key, 'baseRevision': 0, 'document': _empty_doc()})

        other = Client(enforce_csrf_checks=True)
        other.login(username='vocab-b', password='Pass12345!')
        other.get(reverse('core:vocabulary_lab'))
        empty = other.get(self.api)
        self.assertEqual(empty.json()['revision'], 0)
        self.assertIsNone(empty.json()['document'])
        steal = other.put(
            self.api,
            data=json.dumps({'accountKey': key, 'baseRevision': 0, 'document': _empty_doc()}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=other.cookies['csrftoken'].value,
        )
        self.assertEqual(steal.status_code, 409)
        self.assertEqual(steal.json()['error'], 'ACCOUNT_CHANGED')

    def test_invalid_document_rejected(self):
        key = f'user-{self.user.pk}'
        bad = {'version': 2}
        response = self._put({'accountKey': key, 'baseRevision': 0, 'document': bad})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error'], 'INVALID_DOCUMENT')

    def test_csrf_required_on_put(self):
        key = f'user-{self.user.pk}'
        response = self.client.put(
            self.api,
            data=json.dumps({'accountKey': key, 'baseRevision': 0, 'document': _empty_doc()}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)


class VocabularyLabValidateTests(TestCase):
    def test_valid_empty(self):
        self.assertIsNone(validate_document(_empty_doc()))

    def test_rejects_bad_level(self):
        doc = _empty_doc()
        doc['level'] = 'A2'
        self.assertEqual(validate_document(doc), 'INVALID_DOCUMENT')

    def test_rejects_bad_count(self):
        doc = _empty_doc()
        doc['count'] = 3
        self.assertEqual(validate_document(doc), 'INVALID_DOCUMENT')
