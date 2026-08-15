"""Natija sahifasidagi writing feedback konteksti va fragmentlari."""

from django.template.loader import render_to_string

from core.models import AIWritingFeedback, UserTestAnswer, UserTestResult
from core.services.ai_language import language_for_result
from core.services.ai_writing_feedback import load_writing_feedback_for_result
from core.services.essay_highlight import build_writing_feedback_comparison
from core.services.writing_chat_coach import build_coach_panel_context, coach_chat_remaining

FEEDBACK_REGENERATE_DAILY_LIMIT = 3


def sync_essay_answers_from_json(test_result):
    """answers_json dagi essay matnlarini UserTestAnswer qatorlariga yozadi."""
    answers_json = test_result.answers_json or {}
    synced = 0
    for question in test_result.test.questions.filter(question_type='essay'):
        essay_text = (answers_json.get(str(question.pk), '') or '').strip()
        if not essay_text:
            continue
        answer, created = UserTestAnswer.objects.get_or_create(
            test_result=test_result,
            question=question,
            defaults={'user_answer': essay_text, 'is_correct': False},
        )
        if created:
            synced += 1
        elif not (answer.user_answer or '').strip():
            answer.user_answer = essay_text
            answer.save(update_fields=['user_answer'])
            synced += 1
    return synced


def feedback_regenerate_remaining(user):
    from django.core.cache import cache
    from django.utils import timezone

    key = f'wf_regen:{user.pk}:{timezone.localdate().isoformat()}'
    used = int(cache.get(key, 0) or 0)
    return max(0, FEEDBACK_REGENERATE_DAILY_LIMIT - used)


def record_feedback_regenerate(user):
    from django.core.cache import cache
    from django.utils import timezone

    key = f'wf_regen:{user.pk}:{timezone.localdate().isoformat()}'
    used = int(cache.get(key, 0) or 0)
    cache.set(key, used + 1, timeout=86400)


def build_writing_comparison_maps(test_result, user, writing_feedback_items):
    writing_comparison_by_answer_id = {}
    writing_overall_comparison = None

    if test_result.test.test_type != 'writing' or not test_result.completed_at:
        return writing_comparison_by_answer_id, writing_overall_comparison

    previous_writing_result = (
        UserTestResult.objects
        .filter(
            user=user,
            test=test_result.test,
            completed_at__isnull=False,
            completed_at__lt=test_result.completed_at,
        )
        .exclude(pk=test_result.pk)
        .order_by('-completed_at')
        .first()
    )
    if not previous_writing_result:
        return writing_comparison_by_answer_id, writing_overall_comparison

    prev_feedback_by_question = {
        item.question_id: item
        for item in load_writing_feedback_for_result(previous_writing_result)
    }
    for item in writing_feedback_items:
        prev_item = prev_feedback_by_question.get(item.question_id)
        comparison = build_writing_feedback_comparison(item, prev_item)
        if comparison and item.test_answer_id:
            writing_comparison_by_answer_id[item.test_answer_id] = comparison

    cur_bands = [
        item.estimated_band
        for item in writing_feedback_items
        if item.status == AIWritingFeedback.STATUS_COMPLETED and item.estimated_band is not None
    ]
    prev_bands = [
        item.estimated_band
        for item in prev_feedback_by_question.values()
        if item.status == AIWritingFeedback.STATUS_COMPLETED and item.estimated_band is not None
    ]
    if cur_bands and prev_bands:
        cur_avg = round(sum(cur_bands) / len(cur_bands), 1)
        prev_avg = round(sum(prev_bands) / len(prev_bands), 1)
        writing_overall_comparison = {
            'prev_band': prev_avg,
            'band_delta': round(cur_avg - prev_avg, 1),
            'attempt_date': previous_writing_result.completed_at,
        }

    return writing_comparison_by_answer_id, writing_overall_comparison


def render_writing_feedback_fragments(
    review_items,
    writing_feedback_by_answer_id,
    writing_comparison_by_answer_id,
    *,
    test_result=None,
    user=None,
):
    fragments = {}
    regen_remaining = feedback_regenerate_remaining(user) if user else 0
    chat_remaining = coach_chat_remaining(user) if user else 0
    for item in review_items:
        question = item['question']
        answer = item.get('answer')
        if question.question_type != 'essay' or not answer:
            continue

        feedback = writing_feedback_by_answer_id.get(answer.id)
        comparison = writing_comparison_by_answer_id.get(answer.id)
        ctx = {
            'essay_text': item['user_part'],
            'feedback': feedback,
            'comparison': comparison,
            'show_regenerate': bool(test_result),
            'feedback_regenerate_remaining': regen_remaining,
            'coach_chat_remaining': chat_remaining,
            'test_result_pk': test_result.pk if test_result else None,
            'ai_lang': language_for_result(test_result) if test_result else 'uz',
        }
        if feedback:
            ctx.update(build_coach_panel_context(feedback))
        fragments[str(answer.id)] = {
            'essay_html': render_to_string('core/tests/partials/essay_highlight.html', ctx),
            'feedback_html': render_to_string('core/tests/partials/essay_ai_feedback.html', ctx),
        }
    return fragments
