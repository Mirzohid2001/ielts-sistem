"""Essay matnida AI writing_errors va sentence_corrections bo'yicha highlight."""

from __future__ import annotations

import html
import re
from typing import Any

ERROR_TYPES = frozenset({
    'grammar', 'spelling', 'punctuation', 'article', 'tense', 'preposition',
    'subject_verb', 'word_choice', 'plural', 'capitalization', 'word_form',
})

ERROR_TYPE_LABELS = {
    'grammar': 'Grammatika',
    'spelling': 'Imlo',
    'punctuation': 'Tinish belgisi',
    'article': 'Artikl',
    'tense': 'Zamon',
    'preposition': 'Predlog',
    'subject_verb': 'Subject-verb',
    'word_choice': "So'z tanlovi",
    'plural': "Ko'plik",
    'capitalization': 'Katta harf',
    'word_form': "So'z shakli",
}

ERROR_TYPE_ORDER = (
    'grammar', 'spelling', 'punctuation', 'article', 'tense', 'preposition',
    'subject_verb', 'word_choice', 'plural', 'capitalization', 'word_form',
)


def build_writing_error_stats(writing_errors: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Xatolar ro'yxatidan tur bo'yicha statistika."""
    items = writing_errors if isinstance(writing_errors, list) else []
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        etype = str(item.get('type') or 'grammar').strip().lower()
        counts[etype] = counts.get(etype, 0) + 1

    total = sum(counts.values())
    if total == 0:
        return {
            'total': 0,
            'by_type': [],
            'top_type': '',
            'top_type_label': '',
            'grammar_count': 0,
            'spelling_count': 0,
            'other_count': 0,
        }

    by_type = []
    for etype in ERROR_TYPE_ORDER:
        count = counts.get(etype, 0)
        if not count:
            continue
        by_type.append({
            'type': etype,
            'label': ERROR_TYPE_LABELS.get(etype, etype.replace('_', ' ').title()),
            'count': count,
            'pct': round(count * 100 / total),
        })

    for etype, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        if etype in ERROR_TYPE_ORDER:
            continue
        by_type.append({
            'type': etype,
            'label': ERROR_TYPE_LABELS.get(etype, etype.replace('_', ' ').title()),
            'count': count,
            'pct': round(count * 100 / total),
        })

    top = max(counts.items(), key=lambda x: (x[1], x[0]))
    grammar_count = counts.get('grammar', 0)
    spelling_count = counts.get('spelling', 0)
    other_count = total - grammar_count - spelling_count

    return {
        'total': total,
        'by_type': by_type,
        'top_type': top[0],
        'top_type_label': ERROR_TYPE_LABELS.get(top[0], top[0]),
        'grammar_count': grammar_count,
        'spelling_count': spelling_count,
        'other_count': other_count,
    }


def _normalize_phrase(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').strip())


def _find_phrase_span(essay: str, phrase: str) -> tuple[int, int] | None:
    """Essay ichida phrase joylashuvini qidirish (case-insensitive)."""
    phrase = _normalize_phrase(phrase)
    if not phrase or len(phrase) < 2:
        return None

    essay_norm = essay
    pattern = re.escape(phrase)
    match = re.search(pattern, essay_norm, flags=re.IGNORECASE)
    if match:
        return match.start(), match.end()

    words = phrase.split()
    if len(words) >= 2:
        loose = r'\s+'.join(re.escape(w) for w in words)
        match = re.search(loose, essay_norm, flags=re.IGNORECASE)
        if match:
            return match.start(), match.end()
    return None


def _ranges_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _collect_candidates(
    essay: str,
    items: list[dict[str, Any]] | None,
    *,
    source: str,
    phrase_key: str,
    corrected_key: str,
    default_type: str,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for idx, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        phrase = _normalize_phrase(item.get(phrase_key) or '')
        if not phrase:
            continue
        span = _find_phrase_span(essay, phrase)
        if not span:
            continue
        ctype = _normalize_phrase(item.get('type') or default_type)
        severity = 'error' if source == 'error' or ctype in ERROR_TYPES else 'improve'
        candidates.append({
            'start': span[0],
            'end': span[1],
            'original': essay[span[0]:span[1]],
            'corrected': _normalize_phrase(item.get(corrected_key) or ''),
            'why': _normalize_phrase(item.get('why') or ''),
            'type': ctype,
            'severity': severity,
            'order': idx,
            'length': span[1] - span[0],
        })
    return candidates


def collect_essay_highlights(
    essay_text: str,
    sentence_corrections: list[dict[str, Any]] | None,
    writing_errors: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Essay uchun highlight qilinadigan oraliklar ro'yxati."""
    essay = essay_text or ''
    if not essay.strip():
        return []

    candidates = []
    candidates.extend(_collect_candidates(
        essay,
        writing_errors,
        source='error',
        phrase_key='wrong',
        corrected_key='correct',
        default_type='grammar',
    ))
    candidates.extend(_collect_candidates(
        essay,
        sentence_corrections,
        source='correction',
        phrase_key='original',
        corrected_key='corrected',
        default_type='vocabulary',
    ))

    # Xatolar ustun; keyin uzunroq iboralar
    candidates.sort(key=lambda x: (
        0 if x['severity'] == 'error' else 1,
        -x['length'],
        x['start'],
        x['order'],
    ))

    used: list[tuple[int, int]] = []
    highlights: list[dict[str, Any]] = []
    for item in candidates:
        span = (item['start'], item['end'])
        if any(_ranges_overlap(span, u) for u in used):
            continue
        used.append(span)
        highlights.append(item)

    highlights.sort(key=lambda x: x['start'])
    return highlights


def build_highlighted_essay_html(
    essay_text: str,
    sentence_corrections: list[dict[str, Any]] | None,
    writing_errors: list[dict[str, Any]] | None = None,
) -> str:
    """Essay matnini xavfsiz HTML bilan highlight qiladi."""
    essay = essay_text or ''
    highlights = collect_essay_highlights(essay, sentence_corrections, writing_errors)
    if not highlights:
        return html.escape(essay).replace('\n', '<br>')

    parts: list[str] = []
    cursor = 0
    for item in highlights:
        start, end = item['start'], item['end']
        if start < cursor:
            continue
        if cursor < start:
            parts.append(html.escape(essay[cursor:start]).replace('\n', '<br>'))
        hl_class = 'tr-ai-hl tr-ai-hl--error' if item['severity'] == 'error' else 'tr-ai-hl tr-ai-hl--improve'
        attrs = [
            f'data-original="{html.escape(item["original"], quote=True)}"',
            f'data-corrected="{html.escape(item["corrected"], quote=True)}"',
            f'data-why="{html.escape(item["why"], quote=True)}"',
            f'data-severity="{html.escape(item["severity"], quote=True)}"',
        ]
        if item['type']:
            attrs.append(f'data-type="{html.escape(item["type"], quote=True)}"')
        mark_open = (
            f'<mark class="{hl_class}" {" ".join(attrs)} '
            f'title="{html.escape(item["corrected"], quote=True)}">'
        )
        parts.append(mark_open)
        parts.append(html.escape(essay[start:end]))
        parts.append('</mark>')
        cursor = end

    if cursor < len(essay):
        parts.append(html.escape(essay[cursor:]).replace('\n', '<br>'))
    return ''.join(parts)


def build_writing_feedback_comparison(
    current_feedback,
    previous_feedback,
) -> dict[str, Any] | None:
    """Ikki feedback o'rtasida band va mezon farqi."""
    if not current_feedback or not previous_feedback:
        return None
    if current_feedback.status != 'completed' or previous_feedback.status != 'completed':
        return None

    def _delta(cur_val, prev_val):
        if cur_val is None or prev_val is None:
            return None
        try:
            return round(float(cur_val) - float(prev_val), 1)
        except (TypeError, ValueError):
            return None

    band_delta = _delta(current_feedback.estimated_band, previous_feedback.estimated_band)
    criteria = {
        'task_achievement': _delta(current_feedback.task_achievement, previous_feedback.task_achievement),
        'coherence_cohesion': _delta(current_feedback.coherence_cohesion, previous_feedback.coherence_cohesion),
        'lexical_resource': _delta(current_feedback.lexical_resource, previous_feedback.lexical_resource),
        'grammar_range_accuracy': _delta(
            current_feedback.grammar_range_accuracy,
            previous_feedback.grammar_range_accuracy,
        ),
    }
    improved = [k for k, v in criteria.items() if v is not None and v > 0]
    declined = [k for k, v in criteria.items() if v is not None and v < 0]

    return {
        'prev_band': previous_feedback.estimated_band,
        'band_delta': band_delta,
        'criteria': criteria,
        'improved': improved,
        'declined': declined,
        'has_previous': True,
    }
