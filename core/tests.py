from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from core.models import (
    AdminAnnouncement,
    Category,
    Question,
    ReadingPassage,
    SATResource,
    SATResourceBookmark,
    SATResourceNote,
    SATResourceProgress,
    Test,
    StudyStreak,
    UserTestResult,
    UserModuleAccess,
)


class GetReadingPassagesTests(TestCase):
    """Test.get_reading_passages() — 1 / 2 / 3 variant va JSON / inline."""

    def setUp(self):
        self.category = Category.objects.create(name="Cat", slug="cat-reading-passages")

    def _reading_test(self, **kwargs):
        data = {
            "title": "R",
            "category": self.category,
            "test_type": "reading",
            "reading_passages_json": [],
            "reading_text": "",
        }
        data.update(kwargs)
        return Test.objects.create(**data)

    def test_one_variant_inline_flat_list(self):
        exam = self._reading_test(variants_to_select=1)
        ReadingPassage.objects.create(
            test=exam, order=2, title="P2", text="b", variant=1
        )
        ReadingPassage.objects.create(
            test=exam, order=1, title="P1", text="a", variant=2
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["title"], "P1")
        self.assertEqual(out[1]["title"], "P2")

    def test_two_variant_inline_buckets(self):
        exam = self._reading_test(variants_to_select=2)
        ReadingPassage.objects.create(test=exam, order=1, title="A1", text="a", variant=1)
        ReadingPassage.objects.create(test=exam, order=2, title="B1", text="b", variant=2)
        ReadingPassage.objects.create(test=exam, order=1, title="A2", text="c", variant=1)
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 2)
        self.assertEqual([r["title"] for r in out[0]], ["A1", "A2"])
        self.assertEqual([r["title"] for r in out[1]], ["B1"])

    def test_three_variant_inline_invalid_variant_falls_back_to_v1(self):
        exam = self._reading_test(variants_to_select=3)
        ReadingPassage.objects.create(test=exam, order=1, title="X", text="x", variant=99)
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 3)
        self.assertEqual(len(out[0]), 1)
        self.assertEqual(out[0][0]["title"], "X")
        self.assertEqual(out[1], [])
        self.assertEqual(out[2], [])

    def test_two_variant_json_half_split(self):
        exam = self._reading_test(
            variants_to_select=2,
            reading_passages_json=[
                {"title": "L1", "text": "a"},
                {"title": "L2", "text": "b"},
                {"title": "R1", "text": "c"},
                {"title": "R2", "text": "d"},
            ],
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 2)
        self.assertEqual([r["title"] for r in out[0]], ["L1", "L2"])
        self.assertEqual([r["title"] for r in out[1]], ["R1", "R2"])

    def test_three_variant_json_all_tagged(self):
        exam = self._reading_test(
            variants_to_select=3,
            reading_passages_json=[
                {"title": "V2a", "text": "", "variant": 2, "order": 2},
                {"title": "V1a", "text": "", "variant": 1, "order": 1},
                {"title": "V3a", "text": "", "variant": 3},
            ],
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 3)
        self.assertEqual([r["title"] for r in out[0]], ["V1a"])
        self.assertEqual([r["title"] for r in out[1]], ["V2a"])
        self.assertEqual([r["title"] for r in out[2]], ["V3a"])

    def test_three_variant_json_no_variant_thirds_order(self):
        exam = self._reading_test(
            variants_to_select=3,
            reading_passages_json=[
                {"title": "a", "text": ""},
                {"title": "b", "text": ""},
                {"title": "c", "text": ""},
                {"title": "d", "text": ""},
                {"title": "e", "text": ""},
                {"title": "f", "text": ""},
            ],
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 3)
        # (6+2)//3=2, (6-2+1)//2=2 → [0:2],[2:4],[4:6]
        self.assertEqual([r["title"] for r in out[0]], ["a", "b"])
        self.assertEqual([r["title"] for r in out[1]], ["c", "d"])
        self.assertEqual([r["title"] for r in out[2]], ["e", "f"])

    def test_three_variant_json_mixed_keeps_assigned_splits_unassigned(self):
        exam = self._reading_test(
            variants_to_select=3,
            reading_passages_json=[
                {"title": "u1", "text": ""},
                {"title": "V1", "text": "", "variant": 1},
                {"title": "u2", "text": ""},
            ],
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 3)
        titles_v1 = [r["title"] for r in out[0]]
        self.assertIn("V1", titles_v1)
        all_titles = titles_v1 + [r["title"] for r in out[1]] + [r["title"] for r in out[2]]
        self.assertCountEqual(all_titles, ["u1", "V1", "u2"])

    def test_inline_takes_precedence_over_json(self):
        exam = self._reading_test(
            variants_to_select=1,
            reading_passages_json=[{"title": "json", "text": "j"}],
        )
        ReadingPassage.objects.create(test=exam, order=1, title="db", text="d", variant=None)
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "db")


class McqMaxChoicesThreeTests(TestCase):
    """Tanlash soni = 3: to‘liq javob, qisman ball, gradable slotlar."""

    def setUp(self):
        self.category = Category.objects.create(name="C2", slug="cat-mcq3")

    def _q(self, **kwargs):
        exam = Test.objects.create(
            title="E",
            category=self.category,
            test_type="listening",
            reading_passages_json=[],
            reading_text="",
        )
        data = {
            "test": exam,
            "question_type": "mcq",
            "order": 1,
            "max_choices": 3,
            "correct_answer": "a",
            "correct_answer_json": ["a", "c", "f"],
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
        }
        data.update(kwargs)
        return Question.objects.create(**data)

    def test_check_user_answer_three_letters(self):
        q = self._q()
        self.assertTrue(q.check_user_answer('["a","c","f"]'))
        self.assertFalse(q.check_user_answer('["a","c","b"]'))
        self.assertFalse(q.check_user_answer('["a","c"]'))

    def test_score_multi_letter_partial(self):
        q = self._q()
        self.assertEqual(q.score_multi_letter_choice('["a","c","f"]'), (3, 3))
        self.assertEqual(q.score_multi_letter_choice('["a","c","b"]'), (2, 3))
        self.assertEqual(q.score_multi_letter_choice('["a","c"]'), (0, 3))

    def test_gradable_slots_three(self):
        q = self._q()
        self.assertEqual(q.gradable_answer_slots(), 3)


class ModuleSelectorViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="module_user",
            password="secret123",
        )
        self.client.force_login(self.user)

    def test_module_selector_loads_for_authenticated_user(self):
        response = self.client.get(reverse('core:module_selector'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bo'limni tanlang")

    def test_module_selector_shows_denied_button_when_sat_closed(self):
        access = UserModuleAccess.objects.get(user=self.user)
        access.can_access_sat = False
        access.save(update_fields=['can_access_sat'])

        response = self.client.get(reverse('core:module_selector'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ruxsat yo'q")


class ModuleAccessMiddlewareTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="guarded_user",
            password="secret123",
        )
        self.client.force_login(self.user)

    def test_sat_blocked_when_user_has_no_sat_access(self):
        access = UserModuleAccess.objects.get(user=self.user)
        access.can_access_sat = False
        access.save(update_fields=['can_access_sat'])

        response = self.client.get(reverse('sat:sat_home'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:module_selector'))

    def test_ielts_blocked_when_user_has_no_ielts_access(self):
        access = UserModuleAccess.objects.get(user=self.user)
        access.can_access_ielts = False
        access.save(update_fields=['can_access_ielts'])

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:module_selector'))

    def test_ielts_allowed_when_access_exists(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)


class SatExperienceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='sat_user', password='secret123')
        self.client.force_login(self.user)
        self.math_1 = SATResource.objects.create(title='Algebra Basics', subject=SATResource.SUBJECT_MATH, is_active=True)
        self.math_2 = SATResource.objects.create(title='Geometry', subject=SATResource.SUBJECT_MATH, is_active=True)
        self.eng_1 = SATResource.objects.create(title='Reading Drill', subject=SATResource.SUBJECT_ENGLISH, is_active=True)
        SATResourceBookmark.objects.create(user=self.user, resource=self.math_1)

    def test_sat_subject_search_filters_results(self):
        response = self.client.get(reverse('sat:sat_subject', kwargs={'subject': 'math'}), {'q': 'Algebra'})
        self.assertEqual(response.status_code, 200)
        items = response.context['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['obj'].title, 'Algebra Basics')

    def test_sat_subject_bookmark_filter_returns_only_bookmarked(self):
        response = self.client.get(reverse('sat:sat_subject', kwargs={'subject': 'math'}), {'bookmarked': '1'})
        self.assertEqual(response.status_code, 200)
        items = response.context['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['obj'].pk, self.math_1.pk)

    def test_sat_home_shows_recent_notes(self):
        SATResourceNote.objects.create(user=self.user, resource=self.math_1, note_text='First note')
        SATResourceNote.objects.create(user=self.user, resource=self.eng_1, note_text='Second note')
        response = self.client.get(reverse('sat:sat_home'))
        self.assertEqual(response.status_code, 200)
        notes = list(response.context['recent_notes'])
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[0].note_text, 'Second note')

    def test_sat_toggle_bookmark_by_type(self):
        response_video = self.client.post(
            reverse('sat:sat_toggle_bookmark', kwargs={'pk': self.math_1.pk}),
            data={'bookmark_type': 'video'},
        )
        self.assertEqual(response_video.status_code, 200)
        self.assertTrue(SATResourceBookmark.objects.filter(user=self.user, resource=self.math_1, bookmark_type='video').exists())

        response_pdf = self.client.post(
            reverse('sat:sat_toggle_bookmark', kwargs={'pk': self.math_1.pk}),
            data={'bookmark_type': 'pdf'},
        )
        self.assertEqual(response_pdf.status_code, 200)
        self.assertTrue(SATResourceBookmark.objects.filter(user=self.user, resource=self.math_1, bookmark_type='pdf').exists())

    def test_sat_clear_bookmarks_by_type(self):
        SATResourceBookmark.objects.create(user=self.user, resource=self.math_1, bookmark_type='video')
        SATResourceBookmark.objects.create(user=self.user, resource=self.math_1, bookmark_type='pdf')

        response = self.client.post(reverse('sat:sat_clear_bookmarks'), data={'type': 'video'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SATResourceBookmark.objects.filter(user=self.user, resource=self.math_1, bookmark_type='video').exists())
        self.assertTrue(SATResourceBookmark.objects.filter(user=self.user, resource=self.math_1, bookmark_type='pdf').exists())

    def test_sat_update_progress_saves_last_position(self):
        response = self.client.post(
            reverse('sat:sat_update_progress', kwargs={'pk': self.math_1.pk}),
            data={'progress': '42', 'position_seconds': '135'},
        )
        self.assertEqual(response.status_code, 200)
        progress = SATResourceProgress.objects.get(user=self.user, resource=self.math_1)
        self.assertEqual(progress.watch_percentage, 42)
        self.assertEqual(progress.last_position_seconds, 135)

    def test_sat_subject_is_paginated(self):
        for i in range(8):
            SATResource.objects.create(
                title=f'Math item {i}',
                subject=SATResource.SUBJECT_MATH,
                is_active=True,
            )
        response = self.client.get(reverse('sat:sat_subject', kwargs={'subject': 'math'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['items']), 6)
        self.assertTrue(response.context['page_obj'].has_next())

    def test_sat_subject_content_type_filter_pdf(self):
        self.math_1.pdf_file = 'sat/pdfs/test.pdf'
        self.math_1.save(update_fields=['pdf_file'])
        response = self.client.get(
            reverse('sat:sat_subject', kwargs={'subject': 'math'}),
            {'content_type': 'pdf'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['results_count'], 1)

    def test_sat_home_contains_history_and_recommendations(self):
        SATResourceProgress.objects.create(user=self.user, resource=self.math_1, watch_percentage=35)
        SATResource.objects.create(title='Next Math', subject=SATResource.SUBJECT_MATH, is_active=True)

        response = self.client.get(reverse('sat:sat_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['recent_progress_items']) >= 1)
        self.assertTrue(len(response.context['recommended_resources']) >= 1)


class NotificationContextTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="notif_user", password="secret123")
        self.client.force_login(self.user)
        self.category = Category.objects.create(name="Notif Cat", slug="notif-cat")
        self.test = Test.objects.create(
            title="Paused Test",
            category=self.category,
            test_type="reading",
            reading_text="",
            reading_passages_json=[],
        )
        self.sat_resource = SATResource.objects.create(
            title="SAT Continue",
            subject=SATResource.SUBJECT_MATH,
            is_active=True,
        )

    def test_navbar_shows_dynamic_notification_sources(self):
        StudyStreak.objects.create(user=self.user, date=timezone.localdate() - timedelta(days=1), activities_count=1)
        UserTestResult.objects.create(user=self.user, test=self.test, total_questions=10, is_paused=True)
        SATResourceProgress.objects.create(user=self.user, resource=self.sat_resource, watch_percentage=40)
        AdminAnnouncement.objects.create(title="Yangi e'lon", message="Bugun yangilik bor", is_active=True)

        response = self.client.get(reverse('core:module_selector'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Eslatmalar va e'lonlar")
        self.assertContains(response, "IELTS davom ettirish")
        self.assertContains(response, "SAT davom ettirish")
        self.assertContains(response, "Bugun yangilik bor")
        self.assertContains(response, "Hammasini ko'rish")

    def test_notifications_page_renders_time_and_icons(self):
        AdminAnnouncement.objects.create(title="Yangi e'lon", message="Bugun yangilik bor", is_active=True)
        response = self.client.get(reverse('core:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bildirishnomalar")
        self.assertContains(response, "fa-bullhorn")
