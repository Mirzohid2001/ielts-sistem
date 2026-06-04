"""Test yechish: javoblarni yig'ish, merge, imtihon varianti filtri."""
import json
import re

from django.db.models import Q

SUMMARY_BOX_TYPE = 'summary_box'
MATCHING_TYPES = (
    'matching_headings', 'matching_features', 'matching_info',
    'matching_sentences', 'classification',
)
FILL_TYPES = (
    'fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion',
    'table_completion', 'short_answer',
)
SINGLE_CHOICE = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
MATCHING_SCORE_TYPES = MATCHING_TYPES + (SUMMARY_BOX_TYPE,)

# Natija qayta hisoblash: versiya oshganda eski urinishlar yangilanadi
SCORING_VERSION = 2


def exam_variant_session_key(test_pk):
    return f'test_{test_pk}_exam_variant'


def normalize_exam_variant(value, max_variants=3):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(v, max_variants))


def get_exam_variant(request, test, default=1):
    key = exam_variant_session_key(test.pk)
    raw = request.GET.get('exam_variant') or request.session.get(key)
    max_v = int(getattr(test, 'variants_to_select', 1) or 1)
    if max_v < 2:
        return 1
    return normalize_exam_variant(raw, max_v)


def set_exam_variant(request, test, variant):
    request.session[exam_variant_session_key(test.pk)] = normalize_exam_variant(
        variant, int(getattr(test, 'variants_to_select', 1) or 1)
    )
    request.session.modified = True


def clear_exam_variant(request, test):
    request.session.pop(exam_variant_session_key(test.pk), None)
    request.session.modified = True


def filter_questions_by_exam_variant(test, exam_variant):
    """2/3 imtihon qog'ozi: faqat tanlangan variant (variant bo'sh = barcha variantlarda)."""
    qs = test.questions.all()
    max_v = int(getattr(test, 'variants_to_select', 1) or 1)
    if max_v < 2:
        return list(qs.order_by('order'))
    v = normalize_exam_variant(exam_variant, max_v)
    return list(
        qs.filter(Q(variant__isnull=True) | Q(variant=v)).order_by('order')
    )


def _summary_box_slot_count(question):
    n = len(re.findall(r'\[[^\]]+\]', question.question_text or ''))
    if n:
        return n
    c = question.correct_answer_json if isinstance(question.correct_answer_json, dict) else {}
    return len(c) if c else 0


def collect_answer_from_post(request, question):
    """Bitta savol uchun POST dan javob (bo'sh bo'lsa '')."""
    q = question
    val = ''
    if q.question_type in SINGLE_CHOICE:
        if int(getattr(q, 'max_choices', 1) or 1) >= 2:
            selected = []
            opts_json = q.options_json or {}
            mcq_opts = opts_json.get('options') or []
            if mcq_opts:
                letters = [
                    str(o.get('letter', '')).strip().lower()
                    for o in mcq_opts
                    if o.get('letter')
                ]
            else:
                letters = ['a', 'b', 'c', 'd']
            for letter in letters:
                if letter and request.POST.get(f'answer_{q.pk}_{letter}'):
                    selected.append(letter)
            if selected:
                val = json.dumps(sorted(selected))
        else:
            val = (request.POST.get(f'answer_{q.pk}') or '').strip()
    elif q.question_type in FILL_TYPES:
        expected = q.fill_blanks_count()
        vals = []
        for i in range(1, expected + 1):
            vals.append((request.POST.get(f'answer_{q.pk}_{i}') or '').strip())
        if vals and not any(vals[1:]) and vals[0] and ',' in vals[0]:
            vals = [v.strip() for v in vals[0].split(',')]
        if any(v for v in vals):
            val = json.dumps(vals)
    elif q.question_type == SUMMARY_BOX_TYPE:
        match_dict = {}
        n_slots = _summary_box_slot_count(q)
        for i in range(1, n_slots + 1):
            mval = (request.POST.get(f'match_{q.pk}_{i}') or '').strip()
            if mval:
                match_dict[str(i)] = mval
        if match_dict:
            val = json.dumps(match_dict)
    elif q.question_type in MATCHING_TYPES:
        match_dict = {}
        opts = q.options_json or {}
        items = opts.get('items', [])
        if not items:
            items = [{'num': i + 1} for i in range(len((q.correct_answer_json or {})))]
        for idx, it in enumerate(items):
            num = str(it.get('num', idx + 1))
            mval = (request.POST.get(f'match_{q.pk}_{num}') or '').strip()
            if mval:
                match_dict[num] = mval
        if match_dict:
            val = json.dumps(match_dict)
    elif q.question_type == 'list_selection':
        selected = []
        for opt in (q.options_json or {}).get('options', []):
            letter = str(opt.get('letter', '')).strip()
            if letter and request.POST.get(f'list_{q.pk}_{letter}'):
                selected.append(letter)
        if selected:
            val = json.dumps(sorted(selected))
    elif q.question_type == 'essay':
        val = (request.POST.get(f'answer_{q.pk}') or '').strip()
    else:
        val = (request.POST.get(f'answer_{q.pk}') or '').strip()
    return val


def collect_answers_from_post(request, questions):
    """POST dan barcha savollar javoblari: {str(pk): value} (bo'sh = tozalash)."""
    return {str(q.pk): collect_answer_from_post(request, q) for q in questions}


def get_answers_meta(answers_json):
    if not isinstance(answers_json, dict):
        return {}
    meta = answers_json.get('_meta')
    return meta if isinstance(meta, dict) else {}


def exam_variant_from_answers(answers_json, default=1):
    return normalize_exam_variant(get_answers_meta(answers_json).get('exam_variant', default))


def stamp_answers_meta(answers_json, exam_variant):
    """Javoblar JSON ichida sessiya meta (variant, baholash versiyasi)."""
    merged = dict(answers_json or {})
    meta = get_answers_meta(merged)
    meta['exam_variant'] = normalize_exam_variant(exam_variant)
    meta['scoring_version'] = SCORING_VERSION
    merged['_meta'] = meta
    return merged


def needs_scoring_refresh(test_result):
    if not test_result.completed_at:
        return False
    return int(get_answers_meta(test_result.answers_json).get('scoring_version', 1)) < SCORING_VERSION


def merge_answers_json(existing, posted_updates, active_question_pks, exam_variant=None):
    """
    Serverda saqlangan javoblarni yangilash.
    Faqat joriy sessiyadagi savollar yangilanadi (boshqa variant javoblari saqlanadi).
    """
    merged = dict(existing or {})
    merged.pop('_meta', None)
    active = {str(pk) for pk in active_question_pks}
    for key in active:
        if key in posted_updates:
            if posted_updates[key]:
                merged[key] = posted_updates[key]
            else:
                merged.pop(key, None)
    for key, val in posted_updates.items():
        if key.startswith('_') or key in active:
            continue
        if val:
            merged[key] = val
    ev = exam_variant if exam_variant is not None else old_meta.get('exam_variant', 1)
    return stamp_answers_meta(merged, ev)


def user_answer_text(question, answers_json, answers_by_id=None):
    """UserTestAnswer yoki answers_json dan javob matni."""
    if answers_by_id:
        ans = answers_by_id.get(question.pk)
        if ans is not None:
            return (getattr(ans, 'user_answer', None) or '').strip()
    if isinstance(answers_json, dict):
        return (answers_json.get(str(question.pk), '') or '').strip()
    return ''


def score_question_points(question, user_answer):
    """
    Bitta savol uchun (to'g'ri_ball, jami_ball).
    Javob bo'sh bo'lsa (0, jami).
    """
    ua = (user_answer or '').strip()
    if question.question_type == 'essay':
        return (0, 0)
    tot = question.gradable_answer_slots() or 1
    if not ua:
        return (0, tot)
    if question.uses_choose_two_letter_scoring():
        return question.score_mcq_choose_two_dual(ua)
    if question.question_type in MATCHING_SCORE_TYPES:
        return question.score_matching_answer(ua)
    if question.question_type in FILL_TYPES:
        return question.score_fill_answer(ua)
    if question.question_type == 'list_selection':
        return question.score_list_selection(ua)
    return (1, 1) if question.check_user_answer(ua) else (0, 1)


def compute_session_scores(questions, answers_json, answers_by_id=None):
    """
    Test yakunlash / qayta hisoblash: ball, slot, writing holati.
    """
    answers_by_id = answers_by_id or {}
    correct_pts = 0
    total_slots = 0
    essay_total = 0
    essays_submitted = 0

    for q in questions:
        ua = user_answer_text(q, answers_json, answers_by_id)
        if q.question_type == 'essay':
            essay_total += 1
            if ua:
                essays_submitted += 1
            continue
        pts, tot = score_question_points(q, ua)
        correct_pts += pts
        total_slots += tot

    writing_only = total_slots == 0 and essay_total > 0
    return {
        'correct_pts': correct_pts,
        'total_slots': total_slots,
        'essay_total': essay_total,
        'essays_submitted': essays_submitted,
        'writing_only': writing_only,
    }


def build_type_stats(questions, answers_json, answers_by_id, question_type_label_fn):
    """
    Performance Insights: slot bo'yicha aniqlik (qisman ball hisobga olinadi).
    """
    type_stats_map = {}
    answers_by_id = answers_by_id or {}

    for q in questions:
        q_type = q.question_type or 'unknown'
        if q_type == 'essay':
            continue
        if q_type not in type_stats_map:
            type_stats_map[q_type] = {
                'question_type': q_type,
                'label': question_type_label_fn(q_type),
                'total': 0,
                'answered': 0,
                'points': 0.0,
                'max_points': 0,
                'accuracy': 0.0,
            }
        entry = type_stats_map[q_type]
        entry['total'] += 1
        ua = user_answer_text(q, answers_json, answers_by_id)
        pts, tot = score_question_points(q, ua)
        entry['max_points'] += tot
        entry['points'] += pts
        if ua:
            entry['answered'] += 1

    type_stats = []
    for item in type_stats_map.values():
        mp = item['max_points']
        if mp > 0:
            item['accuracy'] = round((item['points'] / mp) * 100, 1)
        else:
            item['accuracy'] = 0.0
        item['accuracy_width'] = max(0, min(100, int(round(item['accuracy']))))
        # Shablon mosligi: correct = ball, answered = javob berilgan savollar
        item['correct'] = item['points']
        type_stats.append(item)
    type_stats.sort(key=lambda x: x['accuracy'])
    return type_stats


def total_gradable_slots_for_questions(questions):
    return sum(
        q.gradable_answer_slots()
        for q in questions
        if q.question_type != 'essay'
    )
