from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from core.models import (
    AIAnswerExplanation,
    AITestInsight,
    Category,
    Question,
    Test,
    UserTestAnswer,
    UserTestResult,
)
from core.services.ai_rl_explanation import (
    _local_explanation,
    explanation_slot_key,
    generate_explanation_for_item,
    prepare_answer_explanation_placeholders,
    supports_answer_explanations,
)


class RLExplanationHelpersTests(SimpleTestCase):
    def test_supports_only_reading_listening(self):
        self.assertTrue(supports_answer_explanations(type('T', (), {'test_type': 'reading'})()))
        self.assertTrue(supports_answer_explanations(type('T', (), {'test_type': 'listening'})()))
        self.assertFalse(supports_answer_explanations(type('T', (), {'test_type': 'writing'})()))

    def test_local_explanation_has_fields(self):
        item = {
            'question': type('Q', (), {
                'pk': 1,
                'question_type': 'mcq',
                'question_text': 'Why?',
                'question_instruction': '',
            })(),
            'user_part': 'A',
            'correct_part': 'B',
            'display_num': 1,
            'slot_label': '',
        }
        payload = _local_explanation(item, skill='reading')
        self.assertIn('explanation', payload)
        self.assertTrue(payload['why_wrong'])
        self.assertGreaterEqual(len(payload['explanation']), 80)
        self.assertEqual(explanation_slot_key(item), 'q1-n1')

    def test_local_explanation_uses_blank_context(self):
        item = {
            'question': type('Q', (), {
                'pk': 2,
                'question_type': 'notes_completion',
                'question_text': 'Type: [1]\nRent per week: £ [2]',
                'question_instruction': '',
            })(),
            'user_part': 's',
            'correct_part': '150',
            'display_num': 2,
            'slot_label': '[2]',
            'slot_placeholder': '[2]',
            'slot_before': 'Rent per week: £ ',
            'slot_after': '',
            'slot_context': 'Rent per week: £ [2]',
        }
        payload = _local_explanation(item, skill='listening')
        self.assertIn('Rent per week', payload['explanation'])
        self.assertIn('150', payload['explanation'])
        self.assertIn('Rent per week', payload['evidence_quote'])
        from core.services.ai_rl_explanation import _item_blank_context
        self.assertEqual(_item_blank_context(item), 'Rent per week: £ [2]')

    def test_gemini_russian_not_overwritten_by_local(self):
        from core.services.ai_rl_explanation import _localize_rl_explanation

        item = {
            'question': type('Q', (), {
                'pk': 3,
                'question_type': 'mcq',
                'question_text': 'Q',
                'question_instruction': '',
            })(),
            'user_part': 'A',
            'correct_part': 'B',
            'display_num': 1,
        }
        gemini_payload = {
            'explanation': 'Правильный ответ B, потому что в тексте прямо сказано after 1990 и это подтверждает утверждение.',
            'why_wrong': 'A противоречит абзацу.',
            'tip': 'Ищите точную дату в пассаже.',
            'evidence_quote': 'after 1990',
            'trap': 'Дистрактор с другой датой.',
            'provider_name': 'gemini',
            'model_name': 'gemini-2.5-flash',
            'raw_response_json': {},
        }
        out = _localize_rl_explanation(gemini_payload, item, skill='reading', lang='ru')
        self.assertIn('Правильный ответ B', out['explanation'])
        self.assertEqual(out['provider_name'], 'gemini')
        self.assertEqual(out['raw_response_json'].get('ai_language'), 'ru')

    def test_short_answer_prompt_not_replaced_by_label(self):
        from core.services.ai_rl_explanation import _item_blank_context

        item = {
            'question': type('Q', (), {
                'pk': 5,
                'question_type': 'short_answer',
                'question_text': 'Questions 1–2',
                'question_instruction': '',
            })(),
            'user_part': 'x',
            'correct_part': 'gold',
            'slot_label': "Bo'sh joy 1",
            'slot_placeholder': '',
            'slot_before': '',
            'slot_after': '',
            'slot_context': 'What type of mineral?',
            'review_layout': 'prompt',
        }
        self.assertEqual(_item_blank_context(item), 'What type of mineral?')
        payload = _local_explanation(item, skill='reading')
        self.assertIn('What type of mineral?', payload['explanation'])
        self.assertNotIn("Bo'sh joy 1", payload['explanation'])

    def test_weak_payload_merged_with_local(self):
        from core.services.ai_rl_explanation import _merge_explanation_payload, _payload_is_weak

        item = {
            'question': type('Q', (), {
                'pk': 4,
                'question_type': 'notes_completion',
                'question_text': 'Rent per week: £ [2]',
                'question_instruction': '',
            })(),
            'user_part': 's',
            'correct_part': '150',
            'slot_before': 'Rent per week: £ ',
            'slot_after': '',
            'slot_placeholder': '[2]',
            'slot_context': 'Rent per week: £ [2]',
        }
        weak = {
            'explanation': 'Wrong.',
            'why_wrong': '',
            'tip': 'Be careful',
            'evidence_quote': '',
            'trap': '',
            'provider_name': 'gemini',
            'model_name': 'x',
            'raw_response_json': {},
        }
        self.assertTrue(_payload_is_weak(weak))
        local = _local_explanation(item, skill='listening')
        merged = _merge_explanation_payload(weak, local)
        self.assertIn('Rent per week', merged['explanation'])
        self.assertTrue(merged['why_wrong'])


class RLExplanationIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='rlai', password='pass12345')
        self.category = Category.objects.create(name='RL AI', slug='rl-ai')
        self.exam = Test.objects.create(
            title='Reading AI',
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
        )
        self.answer = UserTestAnswer.objects.create(
            test_result=self.result,
            question=self.question,
            user_answer='false',
            is_correct=False,
        )

    def test_mixed_writing_test_supports_explanations(self):
        mixed = Test.objects.create(
            title='Mixed Writing',
            category=self.category,
            test_type='writing',
            reading_passages_json=[],
            reading_text='',
        )
        Question.objects.create(
            test=mixed,
            question_type='mcq',
            order=1,
            question_text='Pick one',
            option_a='A',
            option_b='B',
            correct_answer='a',
        )
        self.assertTrue(supports_answer_explanations(mixed))
        essay_only = Test.objects.create(
            title='Essay only',
            category=self.category,
            test_type='writing',
            reading_passages_json=[],
            reading_text='',
        )
        Question.objects.create(
            test=essay_only,
            question_type='essay',
            order=1,
            question_text='Discuss both views.',
        )
        self.assertFalse(supports_answer_explanations(essay_only))

    def test_prepare_placeholders_for_wrong(self):
        created = prepare_answer_explanation_placeholders(self.result)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].status, AIAnswerExplanation.STATUS_PENDING)

    def test_generate_falls_back_to_local_when_provider_local(self):
        item = {
            'question': self.question,
            'answer': self.answer,
            'user_part': 'false',
            'correct_part': 'true',
            'display_num': 1,
            'slot_label': '',
            'state': 'wrong',
        }
        with self.settings(AI_WRITING_FEEDBACK_PROVIDER='local'):
            payload = generate_explanation_for_item(item, test=self.exam)
        self.assertEqual(payload['provider_name'], 'local')
        self.assertTrue(payload['explanation'])
        self.assertIn('evidence_quote', payload)
        self.assertIn('trap', payload)

    def test_local_insight_lists_weak_types(self):
        from core.services.ai_rl_explanation import _local_insight
        item = {
            'question': self.question,
            'user_part': 'false',
            'correct_part': 'true',
            'display_num': 1,
        }
        insight = _local_insight(self.result, [item, item])
        self.assertTrue(insight['summary'])
        self.assertTrue(insight['weak_types'])
        self.assertEqual(insight['weak_types'][0]['count'], 2)

    def test_status_endpoint(self):
        prepare_answer_explanation_placeholders(self.result)
        obj = AIAnswerExplanation.objects.get(test_result=self.result)
        obj.apply_completed({
            'explanation': 'Matnda after 1990 deyilgan.',
            'why_wrong': 'false emas.',
            'tip': 'Kalit so‘zlarni belgilang.',
            'evidence_quote': 'grew rapidly after 1990',
            'trap': 'Opposite meaning',
            'provider_name': 'local',
            'model_name': 'test',
            'raw_response_json': {},
        })
        from core.services.ai_rl_explanation import generate_test_insight
        generate_test_insight(self.result, force=True)
        self.client.login(username='rlai', password='pass12345')
        with patch('core.views.schedule_answer_explanations'):
            response = self.client.get(
                reverse('core:answer_explanation_status', args=[self.result.pk]),
                {'fragments': '1'},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['completed'])
        self.assertIn('fragments', data)
    def test_status_not_complete_while_insight_pending(self):
        prepare_answer_explanation_placeholders(self.result)
        obj = AIAnswerExplanation.objects.get(test_result=self.result)
        obj.apply_completed({
            'explanation': 'ok',
            'why_wrong': 'x',
            'tip': 'y',
            'provider_name': 'local',
            'model_name': 't',
            'raw_response_json': {},
        })
        from core.services.ai_rl_explanation import ensure_insight_placeholder
        insight = ensure_insight_placeholder(self.result)
        insight.status = AITestInsight.STATUS_PENDING
        insight.summary = ''
        insight.save(update_fields=['status', 'summary', 'updated_at'])

        self.client.login(username='rlai', password='pass12345')
        with patch('core.views.ensure_answer_explanations_for_result'):
            response = self.client.get(
                reverse('core:answer_explanation_status', args=[self.result.pk]),
                {'fragments': '1'},
            )
        data = response.json()
        self.assertFalse(data['completed'])
        self.assertTrue(data['pending'])
        self.assertIn('insight_html', data)

    def test_single_regen_schedules_only_one(self):
        prepare_answer_explanation_placeholders(self.result)
        obj = AIAnswerExplanation.objects.get(test_result=self.result)
        self.client.login(username='rlai', password='pass12345')
        with patch('core.views.schedule_single_explanation') as mock_one:
            with patch('core.views.schedule_answer_explanations') as mock_all:
                response = self.client.post(
                    reverse('core:regenerate_answer_explanation', args=[obj.pk]),
                )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        mock_one.assert_called_once_with(obj.pk)
        mock_all.assert_not_called()
