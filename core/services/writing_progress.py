"""Foydalanuvchi writing progress statistikasi."""

from __future__ import annotations

from core.models import AIWritingFeedback
from core.services.ai_writing_feedback import _task_meta

CRITERIA_FIELDS = (
    ('task_achievement', 'Task'),
    ('coherence_cohesion', 'Coherence'),
    ('lexical_resource', 'Lexical'),
    ('grammar_range_accuracy', 'Grammar'),
)


def build_writing_progress_summary(user, *, limit=20):
    feedbacks = list(
        AIWritingFeedback.objects
        .filter(
            test_result__user=user,
            test_result__completed_at__isnull=False,
            status=AIWritingFeedback.STATUS_COMPLETED,
            estimated_band__isnull=False,
        )
        .select_related('test_result', 'test_result__test', 'question')
        .order_by('test_result__completed_at', 'id')
    )

    points = []
    for fb in feedbacks:
        completed_at = fb.test_result.completed_at
        meta = _task_meta(fb.question)
        points.append({
            'date': completed_at,
            'date_label': completed_at.strftime('%d.%m') if completed_at else '',
            'band': float(fb.estimated_band),
            'test_title': fb.test_result.test.title,
            'task_label': meta['task_label'],
            'result_id': fb.test_result_id,
            'feedback_id': fb.pk,
        })

    chart_source = points[-12:]
    chart_points = [
        {
            **point,
            'height_pct': round(point['band'] / 9.0 * 100, 1),
        }
        for point in chart_source
    ]

    bands = [point['band'] for point in points]
    avg_band = round(sum(bands) / len(bands), 1) if bands else None
    latest_band = bands[-1] if bands else None
    trend = round(latest_band - bands[0], 1) if len(bands) >= 2 else None

    criterion_avgs = {}
    weakest = None
    weakest_avg = None
    for key, label in CRITERIA_FIELDS:
        vals = [
            float(getattr(fb, key))
            for fb in feedbacks
            if getattr(fb, key, None) is not None
        ]
        if not vals:
            continue
        avg = round(sum(vals) / len(vals), 1)
        criterion_avgs[key] = avg
        if weakest_avg is None or avg < weakest_avg:
            weakest_avg = avg
            weakest = {'key': key, 'label': label, 'avg': avg}

    recent_essays = []
    for fb in reversed(feedbacks[-5:]):
        meta = _task_meta(fb.question)
        recent_essays.append({
            'band': float(fb.estimated_band),
            'test_title': fb.test_result.test.title,
            'task_label': meta['task_label'],
            'date_label': fb.test_result.completed_at.strftime('%d.%m.%Y') if fb.test_result.completed_at else '',
            'result_id': fb.test_result_id,
        })

    return {
        'has_data': bool(points),
        'essay_count': len(points),
        'avg_band': avg_band,
        'latest_band': latest_band,
        'trend': trend,
        'weakest': weakest,
        'criterion_avgs': criterion_avgs,
        'chart_points': chart_points,
        'recent_essays': recent_essays,
    }
