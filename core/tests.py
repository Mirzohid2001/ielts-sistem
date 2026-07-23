from datetime import timedelta
import json

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from core.admin.forms import QuestionAdminForm
from core.models import (
    AIWritingFeedback,
    AdminAnnouncement,
    blank_answers_match,
    Category,
    Question,
    ReadingPassage,
    SATResource,
    SATResourceBookmark,
    SATResourceNote,
    SATResourceProgress,
    Test,
    StudyStreak,
    UserTestAnswer,
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
        self.assertEqual(q.score_multi_letter_choice('["a","c"]'), (2, 3))
        self.assertEqual(q.score_multi_letter_choice('["a","c","f","b"]'), (0, 3))

    def test_gradable_slots_three(self):
        q = self._q()
        self.assertEqual(q.gradable_answer_slots(), 3)


class ListSelectionScoringTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="LS", slug="cat-ls")

    def _q(self, correct=None):
        exam = Test.objects.create(
            title="LS",
            category=self.category,
            test_type="listening",
            reading_passages_json=[],
            reading_text="",
        )
        return Question.objects.create(
            test=exam,
            question_type="list_selection",
            order=1,
            options_json={
                "options": [
                    {"letter": "A", "text": "One"},
                    {"letter": "B", "text": "Two"},
                    {"letter": "C", "text": "Three"},
                ]
            },
            correct_answer_json=correct or ["A", "C"],
        )

    def test_list_selection_partial_and_full(self):
        q = self._q()
        self.assertEqual(q.score_list_selection('["a","c"]'), (2, 2))
        self.assertEqual(q.score_list_selection('["a","b"]'), (1, 2))
        self.assertEqual(q.score_list_selection('["a","b","c"]'), (0, 2))
        self.assertTrue(q.check_user_answer('["a","c"]'))
        self.assertFalse(q.check_user_answer('["a","b"]'))


class StrictMultiChoiceScoringTests(TestCase):
    def test_mcq_extra_choice_zero_score(self):
        category = Category.objects.create(name="S", slug="cat-strict")
        exam = Test.objects.create(
            title="E", category=category, test_type="listening",
            reading_passages_json=[], reading_text="",
        )
        q = Question.objects.create(
            test=exam, question_type="mcq", order=1, max_choices=2,
            correct_answer_json=["a", "c"], option_a="A", option_b="B", option_c="C", option_d="D",
        )
        self.assertEqual(q.score_multi_letter_choice('["a","c","b"]'), (0, 2))


class TestTotalQuestionsSlotsTests(TestCase):
    def test_total_questions_counts_gradable_slots(self):
        category = Category.objects.create(name="T", slug="cat-slots")
        exam = Test.objects.create(
            title="E", category=category, test_type="reading",
            reading_passages_json=[], reading_text="",
        )
        Question.objects.create(
            test=exam, question_type="fill_blank", order=1,
            question_text="[1] and [2]", correct_answer_json=["a", "b"],
        )
        self.assertEqual(exam.question_count, 1)
        self.assertEqual(exam.total_questions, 2)


class BuildReviewItemsTests(TestCase):
    def test_expands_multi_slot_questions(self):
        from core.test_session_helpers import build_review_items, total_gradable_slots_for_questions

        category = Category.objects.create(name="R", slug="cat-review")
        exam = Test.objects.create(
            title="E", category=category, test_type="reading",
            reading_passages_json=[], reading_text="",
        )
        q1 = Question.objects.create(
            test=exam, question_type="true_false", order=1,
            question_text="Q1", correct_answer="true",
        )
        q2 = Question.objects.create(
            test=exam, question_type="matching_headings", order=2,
            question_text="Match", correct_answer_json={"1": "i", "2": "ii", "3": "iii"},
        )
        questions = [q1, q2]
        self.assertEqual(total_gradable_slots_for_questions(questions), 4)
        items = build_review_items(questions, {})
        self.assertEqual(len(items), 4)
        self.assertEqual([i['display_num'] for i in items], [1, 2, 3, 4])
        self.assertEqual(items[0]['state'], 'empty')
        self.assertEqual(items[1]['slot_label'], '#1')


class TypeStatsPartialTests(TestCase):
    def test_build_type_stats_uses_slot_points(self):
        from core.test_session_helpers import build_type_stats
        from core.views import question_type_display_label

        category = Category.objects.create(name="TS", slug="cat-ts")
        exam = Test.objects.create(
            title="E", category=category, test_type="reading",
            reading_passages_json=[], reading_text="",
        )
        q = Question.objects.create(
            test=exam,
            question_type="fill_blank",
            order=1,
            question_text="[1] [2]",
            correct_answer_json=["a", "b"],
        )
        answers_json = {str(q.pk): '["a","x"]'}
        stats = build_type_stats([q], answers_json, {}, question_type_display_label)
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]['points'], 1.0)
        self.assertEqual(stats[0]['max_points'], 2)
        self.assertEqual(stats[0]['accuracy'], 50.0)


class WritingScoreTests(TestCase):
    def test_writing_only_session(self):
        from core.test_session_helpers import compute_session_scores

        category = Category.objects.create(name="W", slug="cat-w")
        exam = Test.objects.create(
            title="W", category=category, test_type="writing",
            reading_passages_json=[], reading_text="",
        )
        q1 = Question.objects.create(test=exam, question_type="essay", order=1, question_text="T1")
        q2 = Question.objects.create(test=exam, question_type="essay", order=2, question_text="T2")
        scores = compute_session_scores(
            [q1, q2],
            {str(q1.pk): "text one", str(q2.pk): ""},
            {},
        )
        self.assertTrue(scores['writing_only'])
        self.assertEqual(scores['essay_total'], 2)
        self.assertEqual(scores['essays_submitted'], 1)


class AIWritingFeedbackTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="writer", password="pass12345")
        self.category = Category.objects.create(name="Writing", slug="cat-writing-ai")
        self.exam = Test.objects.create(
            title="Writing Mock",
            category=self.category,
            test_type="writing",
            reading_passages_json=[],
            reading_text="",
            allow_retake=True,
        )
        self.question = Question.objects.create(
            test=self.exam,
            question_type="essay",
            order=1,
            question_text="Some people think cities are the best places to live. Discuss both views.",
            options_json={"part": "2"},
        )
        self.result = UserTestResult.objects.create(
            user=self.user,
            test=self.exam,
            answers_json={str(self.question.pk): "I think cities offer jobs and education. However, villages provide calm life.\n\nIn my opinion cities are better when public services are strong."},
            completed_at=timezone.now(),
            total_questions=1,
            correct_answers=1,
        )
        self.answer = UserTestAnswer.objects.create(
            test_result=self.result,
            question=self.question,
            user_answer=self.result.answers_json[str(self.question.pk)],
            is_correct=False,
        )

    def test_feedback_service_returns_structured_payload(self):
        from core.services.ai_writing_feedback import generate_writing_feedback

        payload = generate_writing_feedback(
            test=self.exam,
            question=self.question,
            essay_text=self.answer.user_answer,
        )
        self.assertIn(payload['provider_name'], {'local', 'gemini', 'openai'})
        self.assertTrue(payload['summary'])
        self.assertTrue(payload['strengths'])
        self.assertTrue(payload['improvements'])
        self.assertTrue(payload['next_steps'])
        self.assertIsNotNone(payload.get('estimated_band'))

    def test_feedback_off_topic_essay_gets_low_band(self):
        from core.services.ai_writing_feedback import generate_writing_feedback

        payload = generate_writing_feedback(
            test=self.exam,
            question=self.question,
            essay_text='salom. Mening ismim Mirzohid',
        )
        self.assertLessEqual(payload['estimated_band'], 4.5)
        self.assertTrue(payload['improvements'])
        summary = payload['summary'].lower()
        self.assertTrue(
            any(token in summary for token in (
                'tanishuv', 'salom', 'insho emas', 'essay emas', 'mirzohid', 'mavzu',
            )),
            msg=f'Unexpected summary: {payload["summary"]}',
        )

    def test_feedback_differs_by_essay_type(self):
        from core.models import Question
        from core.services.ai_writing_feedback import generate_writing_feedback

        task1_q = Question.objects.create(
            test=self.exam,
            question_type='essay',
            order=2,
            question_text=(
                'Write at least 150 words.\n\n'
                'The diagram below shows how bamboo fabric is made. Summarise the information.'
            ),
            options_json={'part': 1},
        )
        greeting = generate_writing_feedback(
            test=self.exam,
            question=task1_q,
            essay_text='salom. Mening ismim Mirzohid',
        )
        prompt_echo = generate_writing_feedback(
            test=self.exam,
            question=task1_q,
            essay_text='The diagram below shows how bamboo fabric is made.',
        )
        self.assertNotEqual(greeting['summary'], prompt_echo['summary'])
        self.assertIn('bamboo', prompt_echo['summary'].lower())
        self.assertLessEqual(greeting['estimated_band'], 4.5)
        self.assertLessEqual(prompt_echo['estimated_band'], 5.0)

    def test_rich_feedback_for_nonsense_and_short(self):
        from core.services.ai_writing_feedback import generate_writing_feedback

        nonsense = generate_writing_feedback(
            test=self.exam,
            question=self.question,
            essay_text='qdwdqfdqwfqwfqwfqwf asdfgh jklqwerty',
        )
        self.assertGreaterEqual(len(nonsense['improvements']), 4)
        self.assertGreaterEqual(len(nonsense['next_steps']), 4)
        self.assertGreaterEqual(len(nonsense['strengths']), 2)
        self.assertGreater(len(nonsense['rewrite_suggestion']), 80)
        self.assertLessEqual(nonsense['estimated_band'], 4.5)

        short = generate_writing_feedback(
            test=self.exam,
            question=self.question,
            essay_text='Cities are better.',
        )
        self.assertGreaterEqual(len(short['improvements']), 4)
        self.assertIn('cities', short['summary'].lower() + short['rewrite_suggestion'].lower())
        self.assertGreaterEqual(len(short.get('vocabulary_upgrades') or []), 5)
        sample = short['vocabulary_upgrades'][0]
        self.assertTrue(sample.get('from') and sample.get('to'))
        self.assertGreaterEqual(len(short.get('sentence_corrections') or []), 3)
        corr = short['sentence_corrections'][0]
        self.assertTrue(corr.get('original') and corr.get('corrected'))

    def test_writing_errors_detected_in_feedback(self):
        from core.services.ai_writing_feedback import generate_writing_feedback

        essay = "Many peoples dont like informations and they discuss about this topic."
        payload = generate_writing_feedback(
            test=self.exam,
            question=self.question,
            essay_text=essay,
        )
        errors = payload.get('writing_errors') or []
        self.assertGreaterEqual(len(errors), 2)
        wrongs = ' '.join(e.get('wrong', '') for e in errors).lower()
        self.assertTrue('peoples' in wrongs or 'dont' in wrongs)

    def test_vocabulary_upgrades_from_basic_essay_words(self):
        from core.services.ai_writing_feedback import generate_writing_feedback

        essay = (
            "I think cities are very good because a lot of people can get better jobs. "
            "But villages are also important. So I agree with this idea. "
            "For example, money and education help people every day."
        )
        payload = generate_writing_feedback(
            test=self.exam,
            question=self.question,
            essay_text=essay,
        )
        upgrades = payload.get('vocabulary_upgrades') or []
        self.assertGreaterEqual(len(upgrades), 5)
        joined = ' '.join(f"{u.get('from','')}->{u.get('to','')}" for u in upgrades).lower()
        self.assertTrue(
            any(token in joined for token in ('think', 'good', 'a lot of', 'get better', 'people', 'important', 'but', 'so')),
            msg=f'Expected basic→academic upgrades, got: {upgrades}',
        )
        corrections = payload.get('sentence_corrections') or []
        self.assertGreaterEqual(len(corrections), 3)
        # At least one correction should improve an actual learner phrase
        originals = ' '.join((c.get('original') or '').lower() for c in corrections)
        self.assertTrue(
            any(token in originals for token in ('think', 'good', 'a lot', 'but', 'cities')),
            msg=f'Expected essay-specific corrections, got: {corrections}',
        )

    def test_gemini_fallback_chain_prefers_working_model(self):
        from core.services.ai_writing_feedback import _gemini_model_chain
        chain = _gemini_model_chain('gemini-2.0-flash')
        self.assertEqual(chain[0], 'gemini-2.0-flash')
        self.assertIn('gemini-2.5-flash', chain)
        self.assertIn('gemini-flash-lite-latest', chain)

    def test_result_view_generates_feedback_record(self):
        from unittest.mock import patch
        from core.services.ai_writing_feedback import generate_writing_feedback_for_result

        def _run_sync(test_result_id, *, force=False):
            generate_writing_feedback_for_result(
                UserTestResult.objects.get(pk=test_result_id),
                force=force,
            )

        self.client.login(username="writer", password="pass12345")
        with patch(
            'core.services.ai_writing_feedback.schedule_writing_feedback_generation',
            side_effect=_run_sync,
        ):
            response = self.client.get(reverse('core:test_result', args=[self.result.pk]))
        self.assertEqual(response.status_code, 200)
        feedback = AIWritingFeedback.objects.get(test_answer=self.answer)
        self.assertEqual(feedback.status, AIWritingFeedback.STATUS_COMPLETED)
        self.assertContains(response, "AI tavsiya")


class EssayHighlightTests(TestCase):
    def test_collect_highlights_finds_phrases(self):
        from core.services.essay_highlight import collect_essay_highlights

        essay = "I think cities are very good because jobs are better."
        corrections = [
            {'original': 'I think cities are very good', 'corrected': 'Urban areas offer advantages', 'type': 'vocabulary'},
            {'original': 'jobs are better', 'corrected': 'employment prospects are stronger', 'type': 'grammar'},
        ]
        highlights = collect_essay_highlights(essay, corrections)
        self.assertEqual(len(highlights), 2)
        self.assertEqual(highlights[0]['original'], 'I think cities are very good')

    def test_highlights_skip_overlapping_ranges(self):
        from core.services.essay_highlight import collect_essay_highlights

        essay = "Cities are good for people."
        corrections = [
            {'original': 'Cities are good', 'corrected': 'A'},
            {'original': 'good for people', 'corrected': 'B'},
        ]
        highlights = collect_essay_highlights(essay, corrections)
        self.assertEqual(len(highlights), 1)

    def test_collect_highlights_marks_writing_errors(self):
        from core.services.essay_highlight import collect_essay_highlights

        essay = "Many peoples live in big citys and they dont have enough time."
        errors = [
            {'wrong': 'peoples', 'correct': 'people', 'type': 'plural', 'why': 'test'},
            {'wrong': 'dont', 'correct': "don't", 'type': 'spelling', 'why': 'test'},
        ]
        highlights = collect_essay_highlights(essay, [], errors)
        self.assertGreaterEqual(len(highlights), 2)
        self.assertEqual(highlights[0]['severity'], 'error')

    def test_detect_writing_errors_patterns(self):
        from core.services.writing_error_detection import detect_heuristic_errors

        essay = "Many peoples dont like informations about citys."
        detected = detect_heuristic_errors(essay)
        wrongs = {item['wrong'].lower() for item in detected}
        self.assertIn('peoples', wrongs)
        self.assertIn('dont', wrongs)
        self.assertIn('informations', wrongs)

    def test_build_writing_error_stats(self):
        from core.services.essay_highlight import build_writing_error_stats

        stats = build_writing_error_stats([
            {'wrong': 'peoples', 'correct': 'people', 'type': 'plural'},
            {'wrong': 'dont', 'correct': "don't", 'type': 'spelling'},
            {'wrong': 'informations', 'correct': 'information', 'type': 'grammar'},
            {'wrong': 'discuss about', 'correct': 'discuss', 'type': 'grammar'},
        ])
        self.assertEqual(stats['total'], 4)
        self.assertEqual(stats['grammar_count'], 2)
        self.assertEqual(stats['spelling_count'], 1)
        self.assertEqual(stats['top_type'], 'grammar')
        self.assertEqual(len(stats['by_type']), 3)

    def test_build_highlighted_html_escapes_and_marks(self):
        from core.services.essay_highlight import build_highlighted_essay_html

        essay = "I think <script>alert(1)</script> cities are good."
        html_out = build_highlighted_essay_html(
            essay,
            [{'original': 'cities are good', 'corrected': 'urban living is beneficial', 'why': 'tone'}],
        )
        self.assertIn('class="tr-ai-hl tr-ai-hl--improve"', html_out)
        self.assertIn('&lt;script&gt;', html_out)
        self.assertNotIn('<script>alert', html_out)

    def test_build_writing_feedback_comparison(self):
        from core.services.essay_highlight import build_writing_feedback_comparison

        current = AIWritingFeedback(
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band=6.0,
            task_achievement=6.0,
            coherence_cohesion=5.5,
            lexical_resource=6.5,
            grammar_range_accuracy=6.0,
        )
        previous = AIWritingFeedback(
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band=5.5,
            task_achievement=5.5,
            coherence_cohesion=6.0,
            lexical_resource=5.0,
            grammar_range_accuracy=5.5,
        )
        comp = build_writing_feedback_comparison(current, previous)
        self.assertIsNotNone(comp)
        self.assertEqual(comp['band_delta'], 0.5)
        self.assertIn('lexical_resource', comp['improved'])
        self.assertIn('coherence_cohesion', comp['declined'])

    def test_result_view_shows_highlight_markup(self):
        from unittest.mock import patch
        from core.services.ai_writing_feedback import generate_writing_feedback_for_result

        user = get_user_model().objects.create_user(username="hluser", password="pass12345")
        category = Category.objects.create(name="W2", slug="cat-w2-hl")
        exam = Test.objects.create(
            title="Writing HL",
            category=category,
            test_type="writing",
            reading_passages_json=[],
            reading_text="",
        )
        question = Question.objects.create(
            test=exam,
            question_type="essay",
            order=1,
            question_text="Discuss city life.",
            options_json={"part": "2"},
        )
        result = UserTestResult.objects.create(
            user=user,
            test=exam,
            answers_json={str(question.pk): "I think cities are very good for young people."},
            completed_at=timezone.now(),
            total_questions=1,
            correct_answers=1,
        )
        answer = UserTestAnswer.objects.create(
            test_result=result,
            question=question,
            user_answer=result.answers_json[str(question.pk)],
            is_correct=False,
        )

        def _run_sync(test_result_id, *, force=False):
            generate_writing_feedback_for_result(
                UserTestResult.objects.get(pk=test_result_id),
                force=force,
            )

        self.client.login(username="hluser", password="pass12345")
        with patch(
            'core.services.ai_writing_feedback.schedule_writing_feedback_generation',
            side_effect=_run_sync,
        ):
            response = self.client.get(reverse('core:test_result', args=[result.pk]))
        self.assertEqual(response.status_code, 200)
        feedback = AIWritingFeedback.objects.get(test_answer=answer)
        if feedback.sentence_corrections or feedback.writing_errors:
            self.assertContains(response, 'tr-ai-hl')
        if feedback.writing_errors:
            self.assertContains(response, 'Aniq xatolar')

    def test_result_view_shows_comparison_after_retake(self):
        from unittest.mock import patch
        from core.services.ai_writing_feedback import generate_writing_feedback_for_result

        user = get_user_model().objects.create_user(username="cmpuser", password="pass12345")
        category = Category.objects.create(name="W3", slug="cat-w3-cmp")
        exam = Test.objects.create(
            title="Writing CMP",
            category=category,
            test_type="writing",
            reading_passages_json=[],
            reading_text="",
            allow_retake=True,
        )
        question = Question.objects.create(
            test=exam,
            question_type="essay",
            order=1,
            question_text="Discuss city life.",
            options_json={"part": "2"},
        )
        old_result = UserTestResult.objects.create(
            user=user,
            test=exam,
            answers_json={str(question.pk): "Short essay one."},
            completed_at=timezone.now() - timedelta(days=1),
            total_questions=1,
            correct_answers=1,
        )
        old_answer = UserTestAnswer.objects.create(
            test_result=old_result,
            question=question,
            user_answer="Short essay one.",
            is_correct=False,
        )
        AIWritingFeedback.objects.create(
            test_result=old_result,
            test_answer=old_answer,
            question=question,
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band=5.0,
            task_achievement=5.0,
            coherence_cohesion=5.0,
            lexical_resource=5.0,
            grammar_range_accuracy=5.0,
            summary="Old",
        )
        new_result = UserTestResult.objects.create(
            user=user,
            test=exam,
            answers_json={str(question.pk): "I think cities are very good for young people."},
            completed_at=timezone.now(),
            total_questions=1,
            correct_answers=1,
        )
        new_answer = UserTestAnswer.objects.create(
            test_result=new_result,
            question=question,
            user_answer=new_result.answers_json[str(question.pk)],
            is_correct=False,
        )
        AIWritingFeedback.objects.create(
            test_result=new_result,
            test_answer=new_answer,
            question=question,
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band=6.0,
            task_achievement=6.0,
            coherence_cohesion=6.0,
            lexical_resource=6.0,
            grammar_range_accuracy=6.0,
            summary="New",
            sentence_corrections=[
                {'original': 'I think cities are very good', 'corrected': 'Urban areas offer advantages', 'type': 'vocabulary'},
            ],
        )

        self.client.login(username="cmpuser", password="pass12345")
        response = self.client.get(reverse('core:test_result', args=[new_result.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tr-ai__delta')
        self.assertContains(response, 'oldingi urinish')


    def test_result_view_without_answer_record(self):
        """Essay matni answers_json da bor, lekin UserTestAnswer yo'q — sahifa ochilishi kerak."""
        user = get_user_model().objects.create_user(username="noans", password="pass12345")
        category = Category.objects.create(name="W4", slug="cat-w4-noans")
        exam = Test.objects.create(
            title="Writing No Answer",
            category=category,
            test_type="writing",
            reading_passages_json=[],
            reading_text="",
        )
        question = Question.objects.create(
            test=exam,
            question_type="essay",
            order=1,
            question_text="Discuss city life.",
            options_json={"part": "2"},
        )
        result = UserTestResult.objects.create(
            user=user,
            test=exam,
            answers_json={str(question.pk): "Essay text without answer row."},
            completed_at=timezone.now(),
            total_questions=1,
            correct_answers=1,
        )
        self.client.login(username="noans", password="pass12345")
        response = self.client.get(reverse('core:test_result', args=[result.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Essay text without answer row")


class WritingProgressTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="wpuser", password="pass12345")
        self.category = Category.objects.create(name="Writing WP", slug="cat-writing-wp")
        self.exam = Test.objects.create(
            title="Writing Progress Mock",
            category=self.category,
            test_type="writing",
            reading_passages_json=[],
            reading_text="",
        )
        self.question = Question.objects.create(
            test=self.exam,
            question_type="essay",
            order=1,
            question_text="Discuss city life.",
            options_json={"part": "2"},
        )

    def _create_feedback(self, band, *, days_ago=0):
        result = UserTestResult.objects.create(
            user=self.user,
            test=self.exam,
            answers_json={str(self.question.pk): f"Essay band {band}"},
            completed_at=timezone.now() - timedelta(days=days_ago),
            total_questions=1,
            correct_answers=1,
        )
        answer = UserTestAnswer.objects.create(
            test_result=result,
            question=self.question,
            user_answer=f"Essay band {band}",
            is_correct=False,
        )
        AIWritingFeedback.objects.create(
            test_result=result,
            test_answer=answer,
            question=self.question,
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band=band,
            task_achievement=band,
            coherence_cohesion=band - 0.5,
            lexical_resource=band,
            grammar_range_accuracy=band - 0.5,
            summary="ok",
        )
        return result

    def test_build_writing_progress_summary(self):
        from core.services.writing_progress import build_writing_progress_summary

        self._create_feedback(5.0, days_ago=3)
        self._create_feedback(5.5, days_ago=1)
        summary = build_writing_progress_summary(self.user)
        self.assertTrue(summary['has_data'])
        self.assertEqual(summary['essay_count'], 2)
        self.assertEqual(summary['latest_band'], 5.5)
        self.assertEqual(summary['trend'], 0.5)
        self.assertTrue(summary['chart_points'])
        self.assertEqual(summary['weakest']['label'], 'Coherence')

    def test_profile_shows_writing_progress(self):
        self._create_feedback(6.0)
        self.client.login(username="wpuser", password="pass12345")
        response = self.client.get(reverse('core:profile_section', args=['ielts']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Writing progress')
        self.assertContains(response, 'wp-chart')

    def test_profile_test_results_pagination(self):
        for i in range(12):
            UserTestResult.objects.create(
                user=self.user,
                test=self.exam,
                answers_json={str(self.question.pk): f"Essay {i}"},
                completed_at=timezone.now() - timedelta(hours=i),
                total_questions=1,
                correct_answers=0,
                score=0,
                percentage=0,
            )
        self.client.login(username="wpuser", password="pass12345")
        response = self.client.get(reverse('core:profile_section', args=['ielts']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'profile-table-pagination')
        self.assertContains(response, 'Jami <strong>12</strong> ta natija')

        page2 = self.client.get(reverse('core:profile_section', args=['ielts']), {'page': 2})
        self.assertEqual(page2.status_code, 200)
        self.assertContains(page2, 'Sahifa 2/2')

    def test_writing_feedback_status_returns_fragments(self):
        result = self._create_feedback(6.0)
        feedback = AIWritingFeedback.objects.get(test_result=result)
        feedback.sentence_corrections = [
            {'original': 'Essay band 6.0', 'corrected': 'Improved phrase', 'type': 'vocabulary', 'why': 'Better'},
        ]
        feedback.save(update_fields=['sentence_corrections'])

        self.client.login(username="wpuser", password="pass12345")
        response = self.client.get(
            reverse('core:writing_feedback_status', args=[result.pk]),
            {'fragments': '1'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['completed'])
        self.assertIn('fragments', data)
        answer_id = str(AIWritingFeedback.objects.get(test_result=result).test_answer_id)
        self.assertIn(answer_id, data['fragments'])
        self.assertIn('tr-ai', data['fragments'][answer_id]['feedback_html'])

    def test_writing_feedback_status_partial_not_terminal_failed(self):
        """Bitta essay failed, boshqasi completed → toast uchun failed=false, fragments bor."""
        from unittest.mock import patch

        q2 = Question.objects.create(
            test=self.exam,
            question_type="essay",
            order=2,
            question_text="Discuss tourism.",
            options_json={"part": "2"},
        )
        result = UserTestResult.objects.create(
            user=self.user,
            test=self.exam,
            answers_json={
                str(self.question.pk): "Task one essay text here.",
                str(q2.pk): "Task two essay text here about tourism.",
            },
            completed_at=timezone.now(),
            total_questions=2,
            correct_answers=0,
        )
        a1 = UserTestAnswer.objects.create(
            test_result=result, question=self.question, user_answer="Task one essay text here.",
        )
        a2 = UserTestAnswer.objects.create(
            test_result=result, question=q2, user_answer="Task two essay text here about tourism.",
        )
        AIWritingFeedback.objects.create(
            test_result=result,
            test_answer=a1,
            question=self.question,
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band=6.0,
            summary="ok",
        )
        AIWritingFeedback.objects.create(
            test_result=result,
            test_answer=a2,
            question=q2,
            status=AIWritingFeedback.STATUS_FAILED,
            summary="timeout",
        )

        self.client.login(username="wpuser", password="pass12345")
        with patch('core.views.schedule_writing_feedback_generation') as mock_schedule:
            response = self.client.get(
                reverse('core:writing_feedback_status', args=[result.pk]),
                {'fragments': '1'},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['failed'])
        self.assertTrue(data['partial'])
        self.assertTrue(data['pending'])
        self.assertIn('fragments', data)
        self.assertIn(str(a1.pk), data['fragments'])
        mock_schedule.assert_called()


class WritingFeedbackEnhancementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="enhuser", password="pass12345")
        self.category = Category.objects.create(name="Enh", slug="cat-enh")
        self.exam = Test.objects.create(
            title="Enh Writing",
            category=self.category,
            test_type="writing",
            reading_passages_json=[],
            reading_text="",
        )
        self.question = Question.objects.create(
            test=self.exam,
            question_type="essay",
            order=1,
            question_text="Describe the chart.",
            options_json={"part": "1"},
        )
        self.result = UserTestResult.objects.create(
            user=self.user,
            test=self.exam,
            answers_json={str(self.question.pk): "The chart shows an increase in sales."},
            completed_at=timezone.now(),
            total_questions=1,
            correct_answers=1,
        )

    def test_sync_essay_answers_from_json(self):
        from core.writing_result_context import sync_essay_answers_from_json

        self.assertFalse(UserTestAnswer.objects.filter(test_result=self.result).exists())
        synced = sync_essay_answers_from_json(self.result)
        self.assertEqual(synced, 1)
        answer = UserTestAnswer.objects.get(test_result=self.result, question=self.question)
        self.assertIn('increase', answer.user_answer)

    def test_regenerate_writing_feedback_endpoint(self):
        from unittest.mock import patch

        answer = UserTestAnswer.objects.create(
            test_result=self.result,
            question=self.question,
            user_answer="The chart shows an increase in sales.",
            is_correct=False,
        )
        AIWritingFeedback.objects.create(
            test_result=self.result,
            test_answer=answer,
            question=self.question,
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band=6.0,
            summary="done",
        )
        self.client.login(username="enhuser", password="pass12345")
        with patch('core.views.schedule_writing_feedback_generation') as mock_schedule:
            response = self.client.post(
                reverse('core:regenerate_writing_feedback', args=[self.result.pk]),
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['remaining'], 2)
        mock_schedule.assert_called_once_with(self.result.pk, force=True)

    def test_regenerate_daily_limit(self):
        from core.writing_result_context import record_feedback_regenerate

        for _ in range(3):
            record_feedback_regenerate(self.user)
        self.client.login(username="enhuser", password="pass12345")
        response = self.client.post(
            reverse('core:regenerate_writing_feedback', args=[self.result.pk]),
        )
        self.assertEqual(response.status_code, 429)

    def test_load_question_image_parts_from_file(self):
        import base64
        import tempfile
        from unittest.mock import patch
        from core.services.ai_writing_feedback import _load_question_image_parts

        png_bytes = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
        )
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(png_bytes)
            tmp_path = tmp.name

        with patch(
            'core.services.ai_writing_feedback._collect_question_image_file_paths',
            return_value=[tmp_path],
        ):
            parts = _load_question_image_parts(self.question)
        self.assertEqual(len(parts), 1)
        self.assertIn('inline_data', parts[0])


class WritingFlashcardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="fcuser", password="pass12345")
        self.category = Category.objects.create(name="FC", slug="cat-fc")
        self.exam = Test.objects.create(
            title="Writing FC Test",
            category=self.category,
            test_type="writing",
            reading_passages_json=[],
            reading_text="",
        )
        self.question = Question.objects.create(
            test=self.exam,
            question_type="essay",
            order=1,
            question_text="Discuss cities.",
            options_json={"part": "2"},
        )
        self.result = UserTestResult.objects.create(
            user=self.user,
            test=self.exam,
            answers_json={},
            completed_at=timezone.now(),
        )
        self.answer = UserTestAnswer.objects.create(
            test_result=self.result,
            question=self.question,
            user_answer="Essay",
            is_correct=False,
        )
        self.feedback = AIWritingFeedback.objects.create(
            test_result=self.result,
            test_answer=self.answer,
            question=self.question,
            status=AIWritingFeedback.STATUS_COMPLETED,
            vocabulary_upgrades=[
                {'from': 'good', 'to': 'beneficial', 'why': 'academic'},
                {'from': 'a lot of', 'to': 'numerous', 'why': 'formal'},
            ],
            summary="ok",
        )

    def test_create_flashcards_from_feedback(self):
        from core.models import Flashcard
        from core.services.writing_flashcards import create_flashcards_from_feedback

        out = create_flashcards_from_feedback(self.user, self.feedback)
        self.assertEqual(out['created'], 2)
        self.assertEqual(Flashcard.objects.filter(user=self.user).count(), 2)

        out2 = create_flashcards_from_feedback(self.user, self.feedback)
        self.assertEqual(out2['created'], 0)
        self.assertEqual(out2['skipped'], 2)

    def test_save_feedback_flashcards_endpoint(self):
        self.client.login(username="fcuser", password="pass12345")
        response = self.client.post(
            reverse('core:save_feedback_flashcards', args=[self.feedback.pk]),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['created'], 2)


class WritingCoachChatTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="coachuser", password="pass12345")
        self.category = Category.objects.create(name="Coach", slug="cat-coach")
        self.exam = Test.objects.create(
            title="Writing Coach Test",
            category=self.category,
            test_type="writing",
            reading_passages_json=[],
            reading_text="",
        )
        self.question = Question.objects.create(
            test=self.exam,
            question_type="essay",
            order=1,
            question_text="Describe a chart.",
            options_json={"part": "1"},
        )
        self.result = UserTestResult.objects.create(
            user=self.user,
            test=self.exam,
            answers_json={},
            completed_at=timezone.now(),
        )
        self.answer = UserTestAnswer.objects.create(
            test_result=self.result,
            question=self.question,
            user_answer="The chart shows population growth in cities.",
            is_correct=False,
        )
        self.feedback = AIWritingFeedback.objects.create(
            test_result=self.result,
            test_answer=self.answer,
            question=self.question,
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band=6.0,
            summary="Overview aniq emas.",
            sentence_corrections=[
                {
                    'original': 'The chart shows',
                    'corrected': 'The diagram illustrates',
                    'why': 'academic opener',
                }
            ],
        )

    def test_coach_chat_local_reply(self):
        from core.services.writing_chat_coach import answer_writing_coach_question

        with self.settings(AI_WRITING_FEEDBACK_PROVIDER='local'):
            out = answer_writing_coach_question(
                feedback=self.feedback,
                essay_text=self.answer.user_answer,
                message='Bandim qanday?',
            )
        self.assertEqual(out['provider'], 'local')
        self.assertIn('6', out['reply'])

    def test_writing_coach_chat_endpoint(self):
        from django.core.cache import cache
        from core.services.writing_chat_coach import coach_chat_remaining

        cache.clear()
        self.client.login(username="coachuser", password="pass12345")
        self.assertEqual(coach_chat_remaining(self.user), 25)

        response = self.client.post(
            reverse('core:writing_coach_chat', args=[self.feedback.pk]),
            data=json.dumps({'message': 'Eng katta muammo nimada?'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['reply'])
        self.assertEqual(data['remaining'], 24)

    def test_writing_coach_chat_rejects_pending_feedback(self):
        self.feedback.status = AIWritingFeedback.STATUS_PENDING
        self.feedback.save(update_fields=['status'])
        self.client.login(username="coachuser", password="pass12345")
        response = self.client.post(
            reverse('core:writing_coach_chat', args=[self.feedback.pk]),
            data=json.dumps({'message': 'Salom'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])

    def test_build_coach_panel_context_task1(self):
        from core.services.writing_chat_coach import build_coach_panel_context

        self.feedback.task_achievement = 5.5
        self.feedback.lexical_resource = 7.0
        panel = build_coach_panel_context(self.feedback)
        self.assertEqual(panel['task_type'], 'task1')
        self.assertEqual(panel['weakest_criterion']['key'], 'task_achievement')
        labels = [p['label'] for p in panel['coach_quick_prompts']]
        self.assertIn('Overview', labels)


class ExamVariantFilterTests(TestCase):
    def test_filter_questions_by_variant(self):
        from core.test_session_helpers import filter_questions_by_exam_variant

        category = Category.objects.create(name="V", slug="cat-var")
        exam = Test.objects.create(
            title="E", category=category, test_type="reading",
            variants_to_select=2, reading_passages_json=[], reading_text="",
        )
        Question.objects.create(test=exam, question_type="mcq", order=1, variant=1, option_a="A", option_b="B", correct_answer="a")
        Question.objects.create(test=exam, question_type="mcq", order=2, variant=2, option_a="A", option_b="B", correct_answer="a")
        Question.objects.create(test=exam, question_type="mcq", order=3, variant=None, option_a="A", option_b="B", correct_answer="a")
        v1 = filter_questions_by_exam_variant(exam, 1)
        self.assertEqual(len(v1), 2)
        v2 = filter_questions_by_exam_variant(exam, 2)
        self.assertEqual(len(v2), 2)


class AnswerNormalizationTests(TestCase):
    def test_blank_synonym_pipe(self):
        self.assertTrue(blank_answers_match("Colour", "color|colour"))
        self.assertTrue(blank_answers_match("color", "colour|color"))


class QuestionAdminFormInitialTests(TestCase):
    """Admin tahrirlashda saqlangan ma'lumotlar formaga qayta yuklanishi."""

    def setUp(self):
        self.category = Category.objects.create(name="Adm", slug="cat-adm-form")
        self.test = Test.objects.create(
            title="T",
            category=self.category,
            test_type="reading",
            reading_passages_json=[],
            reading_text="",
        )

    def test_summary_box_loads_matching_fields_on_edit(self):
        q = Question.objects.create(
            test=self.test,
            question_type="summary_box",
            order=1,
            question_text="Text [1] and [2].",
            options_json={
                "options": [
                    {"letter": "a", "text": "Alpha"},
                    {"letter": "b", "text": "Beta"},
                ]
            },
            correct_answer_json={"1": "a", "2": "b"},
        )
        form = QuestionAdminForm(instance=q)
        self.assertIn("a|Alpha", form.fields["matching_options"].initial)
        self.assertIn("1:a", form.fields["matching_correct"].initial)
        self.assertIn("2:b", form.fields["matching_correct"].initial)

    def test_mcq_three_choices_loads_correct_answer_and_max_choices(self):
        q = Question.objects.create(
            test=self.test,
            question_type="mcq",
            order=1,
            max_choices=3,
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="a",
            correct_answer_json=["a", "c", "f"],
        )
        form = QuestionAdminForm(instance=q)
        self.assertEqual(form.fields["correct_answer"].initial, "a,c,f")
        self.assertEqual(form["max_choices"].value(), 3)


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
