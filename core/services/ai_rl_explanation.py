"""Reading / Listening noto'g'ri javoblar uchun AI tushuntirish."""
from __future__ import annotations

import json
import os
import threading
import time
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.db import connection, transaction
from django.template.loader import render_to_string

from core.models import AIAnswerExplanation, AITestInsight
from core.test_session_helpers import build_review_items

MAX_EXPLANATIONS_PER_RESULT = 25
_STALE_PENDING_SEC = 120
_GENERATION_IN_FLIGHT = {}
# 25 × Gemini + insight — uzoq ish; TTL qisqa bo'lsa parallel worker ochiladi.
_GENERATION_LOCK_TTL_SEC = 45 * 60
_ORPHAN_SKIP_STATUS = 'skipped'

GEMINI_MODEL_FALLBACKS = (
    'gemini-2.5-flash',
    'gemini-flash-lite-latest',
    'gemini-2.0-flash-lite',
    'gemini-2.0-flash',
)


def supports_answer_explanations(test) -> bool:
    return getattr(test, 'test_type', '') in ('reading', 'listening')


def explanation_slot_key(item) -> str:
    """HTML/CSS safe unique key — display_num natija ichida unique."""
    q = item['question']
    num = int(item.get('display_num') or 0)
    return f'q{q.pk}-n{num}'


def _options_blurb(question) -> str:
    parts = []
    for letter in 'abcd':
        val = (getattr(question, f'option_{letter}', None) or '').strip()
        if val:
            parts.append(f'{letter.upper()}) {val}')
    opts = question.options_json if isinstance(question.options_json, dict) else {}
    extra = opts.get('options') or opts.get('choices')
    if isinstance(extra, list):
        for i, row in enumerate(extra[:12]):
            parts.append(f'{i + 1}) {row}')
    elif isinstance(extra, dict):
        for k, v in list(extra.items())[:12]:
            parts.append(f'{k}) {v}')
    return '\n'.join(parts)[:800]


def _passage_excerpt_for_question(test, question, limit=1200) -> str:
    try:
        passages = test.get_reading_passages() or []
    except Exception:
        passages = []
    if not passages:
        text = (getattr(test, 'reading_text', None) or '').strip()
        return text[:limit]

    # Flat list of passage dicts or variant buckets
    flat = []
    for p in passages:
        if isinstance(p, list):
            flat.extend(p)
        elif isinstance(p, dict):
            flat.append(p)
    if not flat:
        return ''

    # Approx: map question order into thirds of passages
    order = int(getattr(question, 'order', 0) or 0)
    total_q = max(1, test.questions.count())
    idx = min(len(flat) - 1, max(0, (order - 1) * len(flat) // total_q))
    chosen = flat[idx]
    title = (chosen.get('title') or '').strip()
    body = (chosen.get('text') or '').strip()
    combined = f"{title}\n{body}".strip() if title else body
    return combined[:limit]


def _local_explanation(item, *, skill='reading') -> dict:
    user = (item.get('user_part') or '').strip()
    correct = (item.get('correct_part') or '').strip() or '—'
    qtype = getattr(item['question'], 'question_type', '') or 'question'
    tip_map = {
        'true_false_not_given': 'True/False/NG da matnda aniq dalil bo‘lishi kerak. NG = matnda hech narsa yo‘q.',
        'yes_no_not_given': 'Yes/No/NG — muallif fikri. Dalil bo‘lmasa NG.',
        'true_false': 'True/False da faqat matnda aytilgan faktni tanlang.',
        'matching_headings': 'Sarlavhani tanlashda paragrafning ASOSIY g‘oyasiga qarang, bitta so‘zga emas.',
        'matching_sentences': 'Gap oxirini moslashtirishda synonym va mantiqiy bog‘lanishni qidiring.',
        'matching_features': 'Har bir elementning xos belgisini matndan toping.',
        'matching_info': 'Paragrafdagi asosiy ma’lumotni qidiring, bitta misolga emas.',
        'fill_blank': 'Bo‘sh joyga grammar (article, plural) va spelling muhim.',
        'summary_completion': 'Summary’da gap grammatikasi va passage synonymlariga e’tibor bering.',
        'notes_completion': 'Notes’da odatda ONE WORD AND/OR A NUMBER — spelling muhim.',
        'sentence_completion': 'Gapni to‘ldirishda so‘z soni chegarasiga rioya qiling.',
        'table_completion': 'Jadvaldagi qator/ustun kontekstini o‘qing.',
        'short_answer': 'Qisqa va aniq yozing; ortiqcha so‘z qo‘shmang.',
        'mcq': 'Variantlarni matndan isbot bilan tekshiring; distractorlarni chiqarib tashlang.',
        'list_selection': 'Ro‘yxatdan faqat so‘ralgan soncha variantni tanlang.',
        'classification': 'Har kategoriya uchun aniq belgini toping.',
        'summary_box': 'Har bir qavs uchun boxdagi to‘g‘ri harfni tanlang.',
    }
    tip = tip_map.get(qtype, 'Savol turiga qarab matndan (yoki audiodan) aniq dalil toping.')
    if skill == 'listening':
        tip = tip_map.get(qtype) or tip
        if qtype in ('notes_completion', 'fill_blank', 'table_completion', 'sentence_completion'):
            tip = 'Listeningda keywordlar eshitilganda yozib boring; distractorlarga aldanning.'
    user_disp = user if user else '(javob bermadingiz)'
    trap = ''
    if user and correct and user.lower() != correct.lower():
        trap = f"«{user_disp}» ko‘pincha chalg‘ituvchi variant — uni matndan tasdiqlamasdan tanlamang."
    elif not user:
        trap = "Bo‘sh qoldirish ham ball yo‘qotadi — noaniq bo‘lsa ham eng yaxshi taxminni yozing."
    evidence = ''
    qtext = (getattr(item['question'], 'question_text', '') or '').strip()
    if qtext:
        evidence = qtext[:120] + ('…' if len(qtext) > 120 else '')
    return {
        'explanation': (
            f"To‘g‘ri javob: «{correct}». Sizning javobingiz: «{user_disp}». "
            f"Bu {qtype.replace('_', ' ')} tipida kalitni matn/audio bilan solishtiring — "
            f"faqat o‘xshash so‘z emas, ma’no mosligi muhim."
        ),
        'why_wrong': (
            f"«{user_disp}» noto‘g‘ri, chunki to‘g‘ri kalit «{correct}». "
            "Synonym yoki distractorni haqiqiy dalil deb o‘ylagan bo‘lishingiz mumkin."
        ),
        'tip': tip,
        'evidence_quote': evidence,
        'trap': trap,
        'provider_name': 'local',
        'model_name': 'heuristic-rl-v2',
        'raw_response_json': {'provider': 'local'},
    }


def _normalize_gemini_model(model_name):
    model = (model_name or os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')).strip()
    if model.startswith('models/'):
        model = model.split('/', 1)[1]
    return model or 'gemini-2.5-flash'


def _gemini_model_chain(preferred=''):
    preferred = _normalize_gemini_model(preferred) if preferred else ''
    chain = []
    if preferred:
        chain.append(preferred)
    for model in GEMINI_MODEL_FALLBACKS:
        if model not in chain:
            chain.append(model)
    return chain


def _call_gemini_json(prompt: str, *, model: str) -> dict:
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise ValueError('GEMINI_API_KEY topilmadi')
    base_url = os.environ.get(
        'GEMINI_API_URL',
        'https://generativelanguage.googleapis.com/v1beta/models',
    ).rstrip('/')
    endpoint = f'{base_url}/{model}:generateContent?key={api_key}'
    body = {
        'generationConfig': {
            'temperature': 0.3,
            'responseMimeType': 'application/json',
        },
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
    }
    req = urllib_request.Request(
        endpoint,
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib_request.urlopen(req, timeout=45) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise ValueError(f'Gemini HTTP {exc.code}: {detail[:300]}') from exc
    except urllib_error.URLError as exc:
        raise ValueError(f'Gemini aloqa: {exc.reason}') from exc
    try:
        parts = raw['candidates'][0]['content']['parts']
        content = ''.join(str(p.get('text', '') or '') for p in parts if isinstance(p, dict)).strip()
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Gemini response format noto‘g‘ri') from exc
    if not isinstance(parsed, dict):
        raise ValueError('Gemini JSON object emas')
    parsed['_raw'] = raw
    return parsed


def _build_prompt(item, *, skill, passage_excerpt='') -> str:
    q = item['question']
    options = _options_blurb(q)
    user = (item.get('user_part') or '').strip() or '(no answer)'
    correct = (item.get('correct_part') or '').strip() or '—'
    return f"""You are an expert IELTS {skill} tutor. Explain ONE wrong student answer in Uzbek (Latin script).

Return ONLY JSON:
{{
  "explanation": "3-5 jumla: to'g'ri javob nima, qayerdan keladi, qisqa mini-dars",
  "why_wrong": "1-3 jumla: foydalanuvchi javobi / tuzoq nega noto'g'ri",
  "tip": "1 amaliy maslahat (keyingi test uchun)",
  "evidence_quote": "matndan/savoldan qisqa iqtibos (max 15 so'z) yoki bo'sh",
  "trap": "bu savolda odatiy distractor/tuzoq (1 jumla)"
}}

Skill: {skill}
Question type: {q.question_type}
Question text: {(q.question_text or '')[:700]}
Instruction: {(q.question_instruction or '')[:400]}
Options:
{options or '—'}
User answer: {user}
Correct answer: {correct}
Passage excerpt (may be empty for listening):
{(passage_excerpt or '—')[:1400]}

Rules:
- Be specific to THIS item; no generic filler.
- Prefer quoting a short evidence cue from the passage when available.
- Mention the trap (paraphrase / absolute word / opposite meaning) if relevant.
- Keep Uzbek clear for B1–B2 students.
"""


def generate_explanation_for_item(item, *, test) -> dict:
    skill = getattr(test, 'test_type', 'reading') or 'reading'
    provider = getattr(
        settings,
        'AI_WRITING_FEEDBACK_PROVIDER',
        os.environ.get('AI_WRITING_FEEDBACK_PROVIDER', 'local'),
    ).strip().lower()
    model_name = getattr(
        settings,
        'AI_WRITING_FEEDBACK_MODEL',
        os.environ.get('AI_WRITING_FEEDBACK_MODEL', 'gemini-2.5-flash'),
    ).strip()

    if provider in ('', 'local', 'heuristic', 'fallback'):
        return _local_explanation(item, skill=skill)

    passage = ''
    if skill == 'reading':
        passage = _passage_excerpt_for_question(test, item['question'])

    prompt = _build_prompt(item, skill=skill, passage_excerpt=passage)
    if provider == 'gemini':
        errors = []
        for model in _gemini_model_chain(model_name):
            try:
                data = _call_gemini_json(prompt, model=model)
                return {
                    'explanation': (data.get('explanation') or '').strip(),
                    'why_wrong': (data.get('why_wrong') or '').strip(),
                    'tip': (data.get('tip') or '').strip(),
                    'evidence_quote': (data.get('evidence_quote') or '').strip()[:400],
                    'trap': (data.get('trap') or '').strip()[:500],
                    'provider_name': 'gemini',
                    'model_name': model,
                    'raw_response_json': data.get('_raw') or data,
                }
            except Exception as exc:
                errors.append(str(exc)[:200])
                continue
        fallback = _local_explanation(item, skill=skill)
        fallback['raw_response_json'] = {
            **(fallback.get('raw_response_json') or {}),
            'gemini_errors': errors,
        }
        return fallback

    return _local_explanation(item, skill=skill)


def collect_wrong_review_items(test_result, *, user_answers=None, limit=MAX_EXPLANATIONS_PER_RESULT):
    from core.test_session_helpers import exam_variant_from_answers, filter_questions_by_exam_variant

    if user_answers is None:
        user_answers = {a.question_id: a for a in test_result.answers.all()}
    variant = exam_variant_from_answers(test_result.answers_json)
    questions = filter_questions_by_exam_variant(test_result.test, variant)
    items = build_review_items(questions, user_answers)
    wrong = [it for it in items if it.get('state') == 'wrong']
    return wrong[:limit]


def prepare_answer_explanation_placeholders(test_result, *, wrong_items=None):
    if not supports_answer_explanations(test_result.test):
        return []
    wrong_items = wrong_items if wrong_items is not None else collect_wrong_review_items(test_result)
    created = []
    for item in wrong_items:
        key = explanation_slot_key(item)
        obj, _ = AIAnswerExplanation.objects.get_or_create(
            test_result=test_result,
            slot_key=key,
            defaults={
                'test_answer': item.get('answer'),
                'question': item['question'],
                'display_num': int(item.get('display_num') or 0),
                'user_part': (item.get('user_part') or '')[:500],
                'correct_part': (item.get('correct_part') or '')[:500],
                'status': AIAnswerExplanation.STATUS_PENDING,
            },
        )
        created.append(obj)
    return created


def load_answer_explanations(test_result):
    return list(
        AIAnswerExplanation.objects
        .filter(test_result=test_result)
        .select_related('question', 'test_answer')
        .order_by('display_num', 'id')
    )


def ensure_insight_placeholder(test_result):
    """Insight satrini darhol yaratish — UI pending ko'rsatishi uchun."""
    insight, _ = AITestInsight.objects.get_or_create(
        test_result=test_result,
        defaults={'status': AITestInsight.STATUS_PENDING},
    )
    return insight


def explanations_pending(items, insight=None) -> bool:
    active = [
        i for i in items
        if getattr(i, 'status', '') != _ORPHAN_SKIP_STATUS
    ]
    pending_items = any(
        i.status in (AIAnswerExplanation.STATUS_PENDING, AIAnswerExplanation.STATUS_FAILED)
        for i in active
    )
    # Insight yo'q yoki hali tayyor emas — polling davom etsin
    if insight is None:
        return True
    insight_pending = insight.status in (
        AITestInsight.STATUS_PENDING,
        AITestInsight.STATUS_FAILED,
    ) or not (insight.summary or '').strip()
    return pending_items or insight_pending


def explanations_is_stale_pending(test_result, *, stale_after_sec=_STALE_PENDING_SEC) -> bool:
    from django.utils import timezone

    now = timezone.now()
    for item in load_answer_explanations(test_result):
        if item.status != AIAnswerExplanation.STATUS_PENDING:
            continue
        stamp = item.updated_at or item.created_at
        if not stamp or (now - stamp).total_seconds() >= stale_after_sec:
            return True
    insight = load_test_insight(test_result)
    if insight and insight.status == AITestInsight.STATUS_PENDING:
        stamp = insight.updated_at or insight.created_at
        if not stamp or (now - stamp).total_seconds() >= stale_after_sec:
            return True
    if insight is None:
        return True
    return False


def generate_single_explanation(explanation_obj, *, force=True):
    """Faqat bitta slotni qayta generatsiya qilish (force-all emas)."""
    test_result = explanation_obj.test_result
    wrong_items = collect_wrong_review_items(test_result)
    by_key = {explanation_slot_key(it): it for it in wrong_items}
    item = by_key.get(explanation_obj.slot_key)
    if not item:
        explanation_obj.mark_failed('Bu xato endi review ro\'yxatida yo\'q.')
        return explanation_obj

    explanation_obj.status = AIAnswerExplanation.STATUS_PENDING
    explanation_obj.user_part = (item.get('user_part') or '')[:500]
    explanation_obj.correct_part = (item.get('correct_part') or '')[:500]
    explanation_obj.display_num = int(item.get('display_num') or explanation_obj.display_num or 0)
    explanation_obj.test_answer = item.get('answer')
    explanation_obj.save(update_fields=[
        'status', 'user_part', 'correct_part', 'display_num', 'test_answer', 'updated_at',
    ])
    try:
        payload = generate_explanation_for_item(item, test=test_result.test)
        if not (payload.get('explanation') or '').strip():
            payload = _local_explanation(item, skill=test_result.test.test_type)
        explanation_obj.apply_completed(payload)
    except Exception as exc:
        try:
            explanation_obj.apply_completed(
                _local_explanation(item, skill=test_result.test.test_type)
            )
        except Exception:
            explanation_obj.mark_failed(str(exc))
    return explanation_obj


def schedule_single_explanation(explanation_id):
    key = f'single-{int(explanation_id)}'
    if _generation_lock_held(key):
        return False
    _GENERATION_IN_FLIGHT[key] = time.monotonic()

    def _run():
        try:
            obj = AIAnswerExplanation.objects.select_related(
                'test_result', 'test_result__test', 'question',
            ).get(pk=explanation_id)
            generate_single_explanation(obj)
        finally:
            _GENERATION_IN_FLIGHT.pop(key, None)
            connection.close()

    def _start():
        threading.Thread(target=_run, daemon=True, name=f'rl-one-{explanation_id}').start()

    try:
        transaction.on_commit(_start)
    except Exception:
        _start()
    return True


def generate_answer_explanations_for_result(test_result, *, force=False, only_slot_keys=None):
    wrong_items = collect_wrong_review_items(test_result)
    by_key = {explanation_slot_key(it): it for it in wrong_items}
    prepare_answer_explanation_placeholders(test_result, wrong_items=wrong_items)
    ensure_insight_placeholder(test_result)
    only = set(only_slot_keys) if only_slot_keys else None
    results = []
    for obj in load_answer_explanations(test_result):
        item = by_key.get(obj.slot_key)
        if not item:
            # Orphan — completionni bloklamasligi uchun completed qilib belgilaymiz
            if obj.status == AIAnswerExplanation.STATUS_PENDING or not (obj.explanation or '').strip():
                obj.status = AIAnswerExplanation.STATUS_COMPLETED
                obj.explanation = obj.explanation or 'Bu savol endi reviewda yo\'q.'
                obj.error_message = 'orphan-skipped'
                obj.save(update_fields=['status', 'explanation', 'error_message', 'updated_at'])
            results.append(obj)
            continue
        if only is not None and obj.slot_key not in only:
            results.append(obj)
            continue
        needs = force or obj.status in (
            AIAnswerExplanation.STATUS_PENDING,
            AIAnswerExplanation.STATUS_FAILED,
        ) or not (obj.explanation or '').strip()
        if not needs:
            results.append(obj)
            continue
        obj.status = AIAnswerExplanation.STATUS_PENDING
        obj.user_part = (item.get('user_part') or '')[:500]
        obj.correct_part = (item.get('correct_part') or '')[:500]
        obj.display_num = int(item.get('display_num') or obj.display_num or 0)
        obj.test_answer = item.get('answer')
        obj.save(update_fields=[
            'status', 'user_part', 'correct_part', 'display_num', 'test_answer', 'updated_at',
        ])
        try:
            payload = generate_explanation_for_item(item, test=test_result.test)
            if not (payload.get('explanation') or '').strip():
                payload = _local_explanation(item, skill=test_result.test.test_type)
            obj.apply_completed(payload)
        except Exception as exc:
            try:
                obj.apply_completed(_local_explanation(item, skill=test_result.test.test_type))
            except Exception:
                obj.mark_failed(str(exc))
        results.append(obj)

    # Umumiy skill xulosa (single-slot regen emas)
    if only is None:
        try:
            generate_test_insight(test_result, wrong_items=wrong_items, force=force)
        except Exception:
            ensure_insight_placeholder(test_result)
    return results


def _generation_lock_held(key) -> bool:
    started = _GENERATION_IN_FLIGHT.get(key)
    if started is None:
        return False
    if (time.monotonic() - started) > _GENERATION_LOCK_TTL_SEC:
        _GENERATION_IN_FLIGHT.pop(key, None)
        return False
    return True


def schedule_answer_explanations(test_result_id, *, force=False):
    key = int(test_result_id)
    # Ishlayotgan workerni o'chirmaymiz — parallel Gemini batch oldini olish
    if _generation_lock_held(key):
        return False

    _GENERATION_IN_FLIGHT[key] = time.monotonic()

    def _run():
        try:
            from core.models import UserTestResult

            test_result = UserTestResult.objects.select_related('test').get(pk=test_result_id)
            if supports_answer_explanations(test_result.test):
                generate_answer_explanations_for_result(test_result, force=force)
        finally:
            _GENERATION_IN_FLIGHT.pop(key, None)
            connection.close()

    def _start():
        threading.Thread(target=_run, daemon=True, name=f'rl-explain-{key}').start()

    try:
        transaction.on_commit(_start)
    except Exception:
        _start()
    return True


def ensure_answer_explanations_for_result(test_result, *, force=False):
    if not supports_answer_explanations(test_result.test):
        return []
    prepare_answer_explanation_placeholders(test_result)
    ensure_insight_placeholder(test_result)
    items = load_answer_explanations(test_result)
    insight = load_test_insight(test_result)
    needs = force or any(
        i.status in (AIAnswerExplanation.STATUS_PENDING, AIAnswerExplanation.STATUS_FAILED)
        or not (i.explanation or '').strip()
        for i in items
    ) or explanations_is_stale_pending(test_result)
    if not items:
        wrong = collect_wrong_review_items(test_result)
        if wrong:
            prepare_answer_explanation_placeholders(test_result, wrong_items=wrong)
            needs = True
    if insight is None or insight.status in (
        AITestInsight.STATUS_PENDING,
        AITestInsight.STATUS_FAILED,
    ) or not (insight.summary or '').strip():
        needs = True
    if needs:
        schedule_answer_explanations(
            test_result.pk,
            force=force,
        )
    return load_answer_explanations(test_result)


def explanations_by_slot_key(items):
    return {i.slot_key: i for i in items}


def render_explanation_fragments(items, *, request=None):
    fragments = {}
    for obj in items:
        fragments[obj.slot_key] = render_to_string(
            'core/tests/partials/answer_ai_explanation.html',
            {'explanation': obj, 'show_regen': True},
            request=request,
        )
    return fragments


def _type_label(qtype: str) -> str:
    labels = {
        'mcq': 'Multiple Choice',
        'true_false_not_given': 'True/False/NG',
        'yes_no_not_given': 'Yes/No/NG',
        'fill_blank': 'Gap fill',
        'notes_completion': 'Notes completion',
        'summary_completion': 'Summary completion',
        'matching_headings': 'Matching headings',
        'matching_info': 'Matching information',
        'list_selection': 'List selection',
        'short_answer': 'Short answer',
    }
    return labels.get(qtype, (qtype or 'other').replace('_', ' '))


def _local_insight(test_result, wrong_items) -> dict:
    skill = test_result.test.test_type
    counts = {}
    for it in wrong_items:
        qt = getattr(it['question'], 'question_type', '') or 'other'
        counts[qt] = counts.get(qt, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    weak = [{
        'type': t,
        'label': _type_label(t),
        'count': c,
        'note': f'{c} ta xato — bu turda ko‘proq mashq qiling.',
    } for t, c in ranked[:5]]
    pct = float(getattr(test_result, 'percentage', 0) or 0)
    strengths = []
    if pct >= 70:
        strengths.append('Umumiy natija yaxshi — endi aniq zaif turlar ustida ishlang.')
    elif pct >= 40:
        strengths.append('Baza bor; xatolarni tahlil qilib ballni tez oshirishingiz mumkin.')
    else:
        strengths.append('Hozir asosiy strategiyani mustahkamlash vaqti.')
    if not wrong_items:
        strengths = ['Barcha javoblar to‘g‘ri — ajoyib!']
        weak = []
    next_steps = [
        'Har bir AI tushuntirishdagi «tuzoq»ni eslab qoling.',
        'Zaif tur bo‘yicha 2–3 ta qo‘shimcha test ishlang.',
        'Keyword + synonym jadvalini o‘zingiz yozib boring.',
    ]
    if skill == 'listening':
        next_steps[0] = 'Listeningda distractor eshitilganda darhol chiqarib tashlashni mashq qiling.'
    summary = (
        f"{skill.title()} natijangiz: {pct:.0f}%. "
        f"Jami {len(wrong_items)} ta tahlil qilingan xato. "
        + (f"Eng zaif: {_type_label(ranked[0][0])}." if ranked else 'Xato yo‘q.')
    )
    focus = (
        f"Keyingi 3 kunda asosan «{_type_label(ranked[0][0])}» ustida ishlang."
        if ranked else 'Keyingi testda tezlikni saqlab, diqqatni chalg‘itmang.'
    )
    return {
        'summary': summary,
        'weak_types': weak,
        'strengths': strengths[:4],
        'next_steps': next_steps[:5],
        'focus_tip': focus,
        'provider_name': 'local',
        'model_name': 'heuristic-insight-v1',
        'raw_response_json': {'provider': 'local', 'wrong_counts': counts},
    }


def _build_insight_prompt(test_result, wrong_items) -> str:
    skill = test_result.test.test_type
    lines = []
    for it in wrong_items[:15]:
        q = it['question']
        lines.append(
            f"- #{it.get('display_num')} type={q.question_type} "
            f"user={it.get('user_part') or '—'} correct={it.get('correct_part') or '—'}"
        )
    return f"""You are an IELTS {skill} coach. Summarize this student's result in Uzbek (Latin).

Return ONLY JSON:
{{
  "summary": "3-5 jumla umumiy xulosa",
  "weak_types": [{{"type":"mcq","label":"Multiple Choice","count":3,"note":"qisqa izoh"}}],
  "strengths": ["1-3 kuchli tomon"],
  "next_steps": ["3-5 amaliy qadam"],
  "focus_tip": "1 asosiy e'tibor nuqtasi"
}}

Score: {getattr(test_result, 'percentage', 0)}%
Wrong items ({len(wrong_items)}):
{chr(10).join(lines) or 'None'}

Be concrete and motivating. Avoid generic advice.
"""


def generate_test_insight(test_result, *, wrong_items=None, force=False) -> AITestInsight:
    wrong_items = wrong_items if wrong_items is not None else collect_wrong_review_items(test_result, limit=40)
    insight, _ = AITestInsight.objects.get_or_create(
        test_result=test_result,
        defaults={'status': AITestInsight.STATUS_PENDING},
    )
    if (
        not force
        and insight.status == AITestInsight.STATUS_COMPLETED
        and (insight.summary or '').strip()
    ):
        return insight

    insight.status = AITestInsight.STATUS_PENDING
    insight.save(update_fields=['status', 'updated_at'])

    provider = getattr(
        settings,
        'AI_WRITING_FEEDBACK_PROVIDER',
        os.environ.get('AI_WRITING_FEEDBACK_PROVIDER', 'local'),
    ).strip().lower()
    model_name = getattr(
        settings,
        'AI_WRITING_FEEDBACK_MODEL',
        os.environ.get('AI_WRITING_FEEDBACK_MODEL', 'gemini-2.5-flash'),
    ).strip()

    try:
        if provider == 'gemini':
            prompt = _build_insight_prompt(test_result, wrong_items)
            last_err = None
            for model in _gemini_model_chain(model_name):
                try:
                    data = _call_gemini_json(prompt, model=model)
                    weak = data.get('weak_types') or []
                    if not isinstance(weak, list):
                        weak = []
                    payload = {
                        'summary': (data.get('summary') or '').strip(),
                        'weak_types': weak[:6],
                        'strengths': list(data.get('strengths') or [])[:5],
                        'next_steps': list(data.get('next_steps') or [])[:6],
                        'focus_tip': (data.get('focus_tip') or '').strip(),
                        'provider_name': 'gemini',
                        'model_name': model,
                        'raw_response_json': data.get('_raw') or data,
                    }
                    if not payload['summary']:
                        raise ValueError('empty summary')
                    insight.apply_completed(payload)
                    return insight
                except Exception as exc:
                    last_err = exc
                    continue
            payload = _local_insight(test_result, wrong_items)
            payload['raw_response_json'] = {
                **(payload.get('raw_response_json') or {}),
                'gemini_error': str(last_err)[:300] if last_err else '',
            }
            insight.apply_completed(payload)
            return insight
        insight.apply_completed(_local_insight(test_result, wrong_items))
        return insight
    except Exception as exc:
        try:
            insight.apply_completed(_local_insight(test_result, wrong_items))
        except Exception:
            insight.mark_failed(str(exc))
        return insight


def load_test_insight(test_result):
    try:
        return test_result.ai_test_insight
    except AITestInsight.DoesNotExist:
        return None


def render_insight_html(insight, *, request=None):
    return render_to_string(
        'core/tests/partials/rl_ai_insight.html',
        {'insight': insight},
        request=request,
    )