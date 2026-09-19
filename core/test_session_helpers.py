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


def _sorted_dict_keys(keys):
    def _sk(k):
        try:
            return (0, int(k))
        except (TypeError, ValueError):
            return (1, str(k))
    return sorted(keys, key=_sk)


def _parse_answer_value(user_answer):
    if user_answer is None:
        return None
    if isinstance(user_answer, (list, dict)):
        return user_answer
    s = str(user_answer).strip()
    if not s:
        return None
    if s.startswith('[') or s.startswith('{'):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return s
    return s


def _mcq_letter_display(question, letter):
    opts = {
        'a': getattr(question, 'option_a', '') or '',
        'b': getattr(question, 'option_b', '') or '',
        'c': getattr(question, 'option_c', '') or '',
        'd': getattr(question, 'option_d', '') or '',
    }
    lt = str(letter or '').strip().lower()
    if not lt:
        return ''
    text = opts.get(lt, '')
    return f"{lt.upper()}) {text}".strip() if text else lt.upper()


def _list_selection_letter_display(question, letter):
    opts = (question.options_json or {}).get('options', [])
    lt = str(letter).strip().lower()
    for o in opts:
        if str(o.get('letter', '')).strip().lower() == lt:
            txt = o.get('text', '') or ''
            return f"{str(letter).upper()}) {txt}".strip() if txt else str(letter).upper()
    return str(letter).upper()


def _nth_bracket_match(text, index):
    """Savol matnidagi N-chi (0-based) [..] joylashuvini qaytaradi."""
    matches = list(re.finditer(r'\[[^\]]+\]', text or ''))
    if 0 <= index < len(matches):
        return matches[index]
    return None


def _line_around_span(text, start, end, max_len=160):
    """Bo'sh joy atrofidagi qator / qisqa snippet."""
    text = text or ''
    if start is None or end is None or start < 0 or end > len(text):
        return ''
    line_start = text.rfind('\n', 0, start) + 1
    line_end = text.find('\n', end)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    if not line:
        return ''
    if len(line) <= max_len:
        return line
    local_start = start - line_start
    local_end = end - line_start
    raw_line = text[line_start:line_end]
    pad = max(24, (max_len - (local_end - local_start)) // 2)
    a = max(0, local_start - pad)
    b = min(len(raw_line), local_end + pad)
    snippet = raw_line[a:b].strip()
    if a > 0:
        snippet = '…' + snippet
    if b < len(raw_line):
        snippet = snippet + '…'
    return snippet


def _split_context_around_placeholder(context, placeholder):
    """Kontekstni [N] oldi/orqasi qilib ajratadi (inline review uchun)."""
    context = context or ''
    placeholder = placeholder or ''
    if context and placeholder and placeholder in context:
        before, after = context.split(placeholder, 1)
        before, after = _pad_blank_edges(before, after)
        return before, after, placeholder
    return context, '', placeholder


def _pad_blank_edges(before, after):
    """
    Matnda [20] atrofida space bo'lmasa ham UI da so'zlar yopishib ketmasin:
    never[20]he → never _ he
    """
    before = before or ''
    after = after or ''
    if before and before[-1] not in ' \t\n\u00a0([{/\'"“‘':
        before = before + ' '
    if after and after[0] not in ' \t\n\u00a0.,;:!?)]}…\'"”’':
        after = ' ' + after
    return before, after


def _paper_num_from_placeholder(placeholder):
    """[20] / #18 / 18 → 20; bo'lmasa None."""
    raw = (placeholder or '').strip()
    if not raw:
        return None
    m = re.match(r'^\[(\d+)\]$', raw)
    if m:
        return int(m.group(1))
    m = re.match(r'^#?(\d+)$', raw)
    if m:
        return int(m.group(1))
    return None


def _matching_paper_num(question, key, slot_context='') -> int | None:
    """
    Matching kaliti IELTS qog'oz raqami bo'lsa qaytaradi.
    '1' + 'Paragraph A' kabi paragraf indekslarini qog'oz raqami deb olmaydi.
    """
    sk = str(key).strip()
    if not sk.isdigit():
        return None
    n = int(sk)
    ctx = (slot_context or '').strip().lower()
    if ctx.startswith('paragraph ') or re.match(r'^paragraph\s+[a-z]\b', ctx):
        return None
    text = getattr(question, 'question_text', None) or ''
    # Matnda "18. ..." deb yozilgan bo'lsa — aniq qog'oz raqami
    if re.search(rf'(?m)^\s*{n}\s*[.):\-]', text):
        return n
    # 10+ odatda IELTS question number (14–40)
    if n >= 10:
        return n
    return None


def _matching_slot_context(question, key) -> str:
    """Matching item uchun ko'rinadigan matn (masalan: 'Link between nature...')."""
    opts = question.options_json if isinstance(getattr(question, 'options_json', None), dict) else {}
    rows = opts.get('items') or []
    sk = str(key)
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                num = row.get('num', row.get('id', row.get('key', row.get('number'))))
                if str(num) == sk:
                    label = (
                        row.get('label')
                        or row.get('text')
                        or row.get('prompt')
                        or row.get('statement')
                        or ''
                    ).strip()
                    if label:
                        return label
            elif isinstance(row, str) and row.strip():
                # "18. A concern about new parks"
                m = re.match(r'^(\d+)\s*[.):\-]\s*(.+)$', row.strip())
                if m and m.group(1) == sk:
                    return m.group(2).strip()
    # question_text ichidan "18. ..." qatorini qidirish
    text = getattr(question, 'question_text', None) or ''
    for line in text.splitlines():
        line = line.strip()
        m = re.match(rf'^{re.escape(sk)}\s*[.):\-]\s*(.+)$', line)
        if m:
            return m.group(1).strip()
    return ''


def _highlight_blank_in_context(context, placeholder):
    """Kontekst ichida [N] ni mark bilan ajratib, HTML xavfsiz qaytaradi."""
    from django.utils.html import escape
    from django.utils.safestring import mark_safe

    if not context:
        return ''
    if not placeholder or placeholder not in context:
        return escape(context)
    parts = context.split(placeholder, 1)
    html = (
        escape(parts[0])
        + f'<mark class="tr-blank-mark">{escape(placeholder)}</mark>'
        + escape(parts[1] if len(parts) > 1 else '')
    )
    return mark_safe(html)


def _slot_meta_result(
    *,
    slot_label='',
    slot_context='',
    placeholder='',
    show_question_text=True,
    review_layout='default',
):
    before, after, ph = _split_context_around_placeholder(slot_context, placeholder)
    paper_num = _paper_num_from_placeholder(ph) or _paper_num_from_placeholder(slot_label)
    return {
        'slot_label': slot_label,
        'slot_context': slot_context,
        'slot_before': before,
        'slot_after': after,
        'slot_placeholder': ph,
        'paper_num': paper_num,
        'slot_context_html': _highlight_blank_in_context(slot_context, ph),
        'show_question_text': show_question_text,
        'review_layout': review_layout,
    }


def fill_review_slot_meta(question, slot_index, n_slots):
    """
    FILL turidagi review kartasi uchun label + kontekst.
    Ko'p bo'sh joyli notes/summary da foydalanuvchi qaysi qator ekanini ko'radi.
    """
    slot_label = f"Bo'sh joy {slot_index + 1}" if n_slots > 1 else ''

    # short_answer: alohida promptlar
    if getattr(question, 'question_type', None) == 'short_answer':
        sa = (getattr(question, 'options_json', None) or {}).get('short_answer_items') or []
        if isinstance(sa, list) and slot_index < len(sa) and isinstance(sa[slot_index], dict):
            prompt = (
                sa[slot_index].get('prompt')
                or sa[slot_index].get('text')
                or sa[slot_index].get('question')
                or ''
            ).strip()
            if prompt:
                return _slot_meta_result(
                    slot_label=slot_label,
                    slot_context=prompt,
                    placeholder='',
                    show_question_text=False,
                    review_layout='prompt',
                )

    text = getattr(question, 'question_text', None) or ''
    m = _nth_bracket_match(text, slot_index)
    if m:
        placeholder = m.group(0)
        if n_slots > 1:
            slot_label = placeholder
        slot_context = _line_around_span(text, m.start(), m.end())
        return _slot_meta_result(
            slot_label=slot_label,
            slot_context=slot_context,
            placeholder=placeholder,
            show_question_text=False if slot_context else (n_slots <= 1),
            review_layout='inline_blank' if slot_context else 'default',
        )

    # Bracket yo'q: faqat birinchi kartada to'liq matn
    show_question_text = n_slots <= 1 or slot_index == 0
    return _slot_meta_result(
        slot_label=slot_label,
        slot_context='',
        placeholder='',
        show_question_text=show_question_text,
        review_layout='default',
    )


def build_review_items(questions, user_answers):
    """
    Har bir gradable javob o'rni uchun alohida review qatori.
    Masalan: 9 ta savol, 18 ta slot → 18 ta review elementi.
    """
    from core.models import blank_answers_match

    items = []
    display_num = 0
    user_answers = user_answers or {}

    for question in questions:
        answer = user_answers.get(question.pk)
        ua = (getattr(answer, 'user_answer', None) or '') if answer else ''
        qt = question.question_type

        if qt == 'essay':
            display_num += 1
            items.append({
                'display_num': display_num,
                'question': question,
                'answer': answer,
                'slot_label': '',
                'show_question_text': True,
                'user_part': ua,
                'correct_part': '',
                'state': 'pending' if str(ua).strip() else 'empty',
            })
            continue

        n_slots = question.gradable_answer_slots() or 1

        if qt in MATCHING_SCORE_TYPES:
            correct = question.correct_answer_json if isinstance(question.correct_answer_json, dict) else {}
            keys = _sorted_dict_keys(list(correct.keys())) if correct else [str(i + 1) for i in range(n_slots)]
            parsed = _parse_answer_value(ua)
            user_map = parsed if isinstance(parsed, dict) else {}
            any_answer = bool(user_map and any(str(v).strip() for v in user_map.values()))

            for i, k in enumerate(keys):
                display_num += 1
                sk = str(k)
                cv = correct.get(k, correct.get(sk, ''))
                uv = user_map.get(sk, user_map.get(k, ''))
                up = str(uv).strip()
                cp = str(cv).strip()
                if not up:
                    st = 'empty' if not any_answer else 'wrong'
                else:
                    st = 'correct' if blank_answers_match(uv, cv) else 'wrong'
                paper_num = None
                slot_context = _matching_slot_context(question, sk)
                paper_num = _matching_paper_num(question, sk, slot_context=slot_context)
                items.append({
                    'display_num': display_num,
                    'question': question,
                    'answer': answer,
                    'slot_label': f'#{sk}',
                    'slot_context': slot_context,
                    'paper_num': paper_num,
                    'show_question_text': (not slot_context) and i == 0,
                    'user_part': up,
                    'correct_part': cp,
                    'state': st,
                })
            continue

        if qt in FILL_TYPES:
            from core.models import format_fill_correct_display

            correct_list = list(question.get_correct_answers_list())
            while len(correct_list) < n_slots:
                correct_list.append('')
            correct_list = correct_list[:n_slots]
            parsed = _parse_answer_value(ua)
            if isinstance(parsed, dict):
                user_list = [parsed.get(str(i + 1), parsed.get(i + 1, '')) for i in range(n_slots)]
            elif isinstance(parsed, list):
                user_list = (list(parsed) + [''] * n_slots)[:n_slots]
            elif parsed is not None and n_slots == 1:
                user_list = [parsed]
            else:
                user_list = [''] * n_slots
            any_answer = any(str(x).strip() for x in user_list)

            for i in range(n_slots):
                display_num += 1
                uv = user_list[i] if i < len(user_list) else ''
                cv = correct_list[i] if i < len(correct_list) else ''
                up = str(uv).strip()
                cp = format_fill_correct_display(cv)
                if not up:
                    st = 'empty' if not any_answer else 'wrong'
                else:
                    st = 'correct' if blank_answers_match(uv, cv) else 'wrong'
                meta = fill_review_slot_meta(question, i, n_slots)
                items.append({
                    'display_num': display_num,
                    'question': question,
                    'answer': answer,
                    'slot_label': meta['slot_label'],
                    'slot_context': meta['slot_context'],
                    'slot_context_html': meta['slot_context_html'],
                    'slot_before': meta['slot_before'],
                    'slot_after': meta['slot_after'],
                    'slot_placeholder': meta['slot_placeholder'],
                    'paper_num': meta.get('paper_num'),
                    'review_layout': meta['review_layout'],
                    'show_question_text': meta['show_question_text'],
                    'user_part': up,
                    'correct_part': cp,
                    'state': st,
                })
            continue

        if qt == 'list_selection':
            letters = []
            if isinstance(question.correct_answer_json, list):
                seen = set()
                for x in question.correct_answer_json:
                    lx = str(x).strip().lower()
                    if lx and lx not in seen:
                        seen.add(lx)
                        letters.append(lx)
            if not letters:
                letters = ['']
            user_set = question._parse_letter_list(ua)
            any_answer = bool(user_set)

            for i, letter in enumerate(letters):
                display_num += 1
                cp = _list_selection_letter_display(question, letter)
                got = letter in user_set
                up = cp if got else ''
                if got:
                    st = 'correct'
                elif any_answer:
                    st = 'wrong'
                else:
                    st = 'empty'
                items.append({
                    'display_num': display_num,
                    'question': question,
                    'answer': answer,
                    'slot_label': f'Variant {letter.upper()}' if len(letters) > 1 else '',
                    'show_question_text': i == 0,
                    'user_part': up,
                    'correct_part': cp,
                    'state': st,
                })
            continue

        if question.uses_choose_two_letter_scoring():
            n = int(getattr(question, 'max_choices', 2) or 2)
            c_letters = sorted(question.multi_letter_correct_set())
            while len(c_letters) < n:
                c_letters.append('')
            c_letters = c_letters[:n]
            user_set = question._parse_letter_list(ua)
            any_answer = bool(user_set)

            for i, letter in enumerate(c_letters):
                display_num += 1
                cp = _mcq_letter_display(question, letter) if letter else ''
                got = letter and letter in user_set
                up = cp if got else ''
                if got:
                    st = 'correct'
                elif any_answer:
                    st = 'wrong'
                else:
                    st = 'empty'
                items.append({
                    'display_num': display_num,
                    'question': question,
                    'answer': answer,
                    'slot_label': f'Javob {i + 1}' if n > 1 else '',
                    'show_question_text': i == 0,
                    'user_part': up,
                    'correct_part': cp,
                    'state': st,
                })
            continue

        display_num += 1
        any_answer = bool(str(ua).strip())
        if not any_answer:
            st = 'empty'
        else:
            try:
                st = 'correct' if question.check_user_answer(ua) else 'wrong'
            except Exception:
                st = 'wrong'

        if qt in SINGLE_CHOICE:
            up = question.get_user_answer_display(ua) or ''
            cp = question.get_correct_answer_display_for_review() or ''
        else:
            up = str(ua).strip()
            cp = question.get_correct_answer_review_text()
        if cp == '—':
            cp = ''

        items.append({
            'display_num': display_num,
            'question': question,
            'answer': answer,
            'slot_label': '',
            'show_question_text': True,
            'user_part': up,
            'correct_part': cp,
            'state': st,
        })

    question_parent = {q.pk: i + 1 for i, q in enumerate(questions)}
    for item in items:
        item['parent_num'] = question_parent.get(item['question'].pk, 0)
        # IELTS qog'oz raqami: fill [20] yoki matchingda allaqachon qo'yilgan paper_num
        paper = item.get('paper_num')
        if paper is None:
            # Faqat [N] placeholder — '#1' matching labelini qayta paper deb olmaslik
            ph = (item.get('slot_placeholder') or '').strip()
            if ph.startswith('[') and ph.endswith(']'):
                paper = _paper_num_from_placeholder(ph)
        if paper is not None:
            item['paper_num'] = int(paper)
            item['ui_num'] = int(paper)
        else:
            item['paper_num'] = None
            item['ui_num'] = int(item.get('display_num') or 0)

    return items
