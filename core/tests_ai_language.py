from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    AIAnswerExplanation,
    AITestInsight,
    Category,
    Question,
    Test,
    UserTestAnswer,
    UserTestResult,
)
from core.services.ai_language import language_still_matches, learner_language_rules, normalize_ai_lang, t


class AILanguageHelperTests(SimpleTestCase):
    def test_normalize_ai_lang(self):
        self.assertEqual(normalize_ai_lang('ru'), 'ru')
        self.assertEqual(normalize_ai_lang('russian'), 'ru')
        self.assertEqual(normalize_ai_lang('uz'), 'uz')
        self.assertEqual(normalize_ai_lang(''), 'uz')

    def test_learner_rules_and_t(self):
        self.assertIn('Russian', learner_language_rules('ru'))
        self.assertIn('Uzbek', learner_language_rules('uz'))
        self.assertEqual(t('ru', 'salom', 'привет'), 'привет')
        self.assertEqual(t('uz', 'salom', 'привет'), 'salom')


class AILanguageIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ailang', password='pass12345')
        self.category = Category.objects.create(name='Lang', slug='ai-lang')
        self.exam = Test.objects.create(
            title='Reading Lang',
            category=self.category,
            test_type='reading',
            reading_passages_json=[],
            reading_text='The city grew rapidly after 1990.',
        )
        self.question = Question.objects.create(
            test=self.exam,
            question_type='true_false_not_given',
            order=1,
            question_text='The city grew after 1990.',
            correct_answer='true',
        )
        self.result = UserTestResult.objects.create(
            user=self.user,
            test=self.exam,
            answers_json={str(self.question.pk): 'false'},
            completed_at=timezone.now(),
            total_questions=1,
            correct_answers=0,
            wrong_answers=1,
            percentage=0,
            ai_language='uz',
        )
        UserTestAnswer.objects.create(
            test_result=self.result,
            question=self.question,
            user_answer='false',
            is_correct=False,
        )

    def test_local_explanation_russian(self):
        from core.services.ai_rl_explanation import generate_explanation_for_item

        item = {
            'question': self.question,
            'user_part': 'false',
            'correct_part': 'true',
            'display_num': 1,
            'slot_label': '',
        }
        with self.settings(AI_WRITING_FEEDBACK_PROVIDER='local'):
            payload = generate_explanation_for_item(item, test=self.exam, lang='ru')
        self.assertIn('Правильный', payload['explanation'])
        self.assertEqual(payload['raw_response_json'].get('ai_language'), 'ru')

    def test_local_writing_feedback_russian(self):
        from core.services.ai_writing_feedback import generate_writing_feedback

        writing = Test.objects.create(
            title='Writing Lang',
            category=self.category,
            test_type='writing',
            reading_passages_json=[],
            reading_text='',
        )
        question = Question.objects.create(
            test=writing,
            question_type='essay',
            order=1,
            question_text='Discuss both views about city life.',
            options_json={'part': '2'},
        )
        with self.settings(AI_WRITING_FEEDBACK_PROVIDER='local'):
            payload = generate_writing_feedback(
                test=writing,
                question=question,
                essay_text='I think cities offer jobs. However villages are calm.',
                lang='ru',
            )
        self.assertIn('балл', payload['summary'].lower())
        self.assertEqual(payload['raw_response_json'].get('ai_language'), 'ru')

    def test_set_language_endpoint_regenerates(self):
        self.client.login(username='ailang', password='pass12345')
        with patch('core.views.schedule_answer_explanations') as mock_sched:
            response = self.client.post(
                reverse('core:set_ai_feedback_language', args=[self.result.pk]),
                data='{"ai_lang":"ru"}',
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['lang'], 'ru')
        self.assertTrue(data['changed'])
        mock_sched.assert_called_once_with(self.result.pk, force=True)
        self.result.refresh_from_db()
        self.assertEqual(self.result.ai_language, 'ru')
        self.assertEqual(self.client.cookies.get('ai_lang').value, 'ru')

    def test_set_language_marks_outputs_pending(self):
        from core.services.ai_rl_explanation import prepare_answer_explanation_placeholders

        prepare_answer_explanation_placeholders(self.result)
        obj = AIAnswerExplanation.objects.get(test_result=self.result)
        obj.apply_completed({
            'explanation': 'uz text',
            'why_wrong': 'x',
            'tip': 'y',
            'provider_name': 'local',
            'model_name': 't',
            'raw_response_json': {},
        })
        insight = AITestInsight.objects.create(
            test_result=self.result,
            status=AITestInsight.STATUS_COMPLETED,
            summary='uz summary',
        )
        self.client.login(username='ailang', password='pass12345')
        with patch('core.views.schedule_answer_explanations'):
            response = self.client.post(
                reverse('core:set_ai_feedback_language', args=[self.result.pk]),
                data='{"ai_lang":"ru"}',
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        insight.refresh_from_db()
        self.assertEqual(obj.status, AIAnswerExplanation.STATUS_PENDING)
        self.assertEqual(insight.status, AITestInsight.STATUS_PENDING)
        self.assertEqual(insight.summary, '')

    def test_stale_generation_does_not_match_new_language(self):
        self.result.ai_language = 'ru'
        self.result.save(update_fields=['ai_language'])
        self.assertFalse(language_still_matches(self.result, 'uz'))
        self.assertTrue(language_still_matches(self.result, 'ru'))
