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
from core.services.ai_language import language_for_result, language_still_matches, learner_language_rules, normalize_ai_lang, t
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
    """Reading/Listening va essay bo'lmagan mixed writing testlar."""
    test_type = getattr(test, 'test_type', '') or ''
    if test_type in ('reading', 'listening'):
        return True
    if test_type != 'writing':
        return False
    questions = getattr(test, 'questions', None)
    if questions is None or not hasattr(questions, 'exclude'):
        return False
    try:
        return questions.exclude(question_type='essay').exists()
    except Exception:
        return False


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


def _item_blank_context(item) -> str:
    """FILL/notes/short_answer uchun haqiqiy kontekst qatori."""
    # Bo'sh joy atrofidagi spacelarni saqlaymiz (£ [2] → £[2] bo'lib ketmasin)
    before = (item.get('slot_before') or '').replace('\r\n', '\n')
    after = (item.get('slot_after') or '').replace('\r\n', '\n')
    placeholder = (item.get('slot_placeholder') or '').strip()
    ctx = (item.get('slot_context') or '').strip()

    # Inline blank: "Rent per week: £ [2]"
    if before or after:
        mid = placeholder or (item.get('slot_label') or '').strip() or '___'
        return f'{before}{mid}{after}'.strip()[:240]

    # Prompt / notes qatori — "Bo'sh joy 1" labelidan ustun
    if ctx:
        return ctx[:240]
    if placeholder:
        return placeholder[:240]
    return ((item.get('slot_label') or '').strip())[:240]


def _find_evidence_in_text(text, needle, *, window=110) -> str:
    text = (text or '').strip()
    needle = (needle or '').strip()
    if not text or not needle or len(needle) < 2:
        return ''
    low = text.lower()
    key = needle.lower()
    idx = low.find(key)
    if idx < 0 and ' ' in key:
        # birinchi so'z bilan qidirish
        idx = low.find(key.split()[0])
    if idx < 0:
        return ''
    start = max(0, idx - window // 3)
    end = min(len(text), idx + len(needle) + window // 2)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = '…' + snippet
    if end < len(text):
        snippet = snippet + '…'
    return snippet[:220]


def _passage_excerpt_for_question(test, question, limit=1600) -> str:
    try:
        passages = test.get_reading_passages() or []
    except Exception:
        passages = []
    if not passages:
        text = (getattr(test, 'reading_text', None) or '').strip()
        return text[:limit]

    flat = []
    for p in passages:
        if isinstance(p, list):
            flat.extend(p)
        elif isinstance(p, dict):
            flat.append(p)
    if not flat:
        return ''

    order = int(getattr(question, 'order', 0) or 0)
    total_q = max(1, test.questions.count())
    idx = min(len(flat) - 1, max(0, (order - 1) * len(flat) // total_q))
    chosen = flat[idx]
    title = (chosen.get('title') or '').strip()
    body = (chosen.get('text') or '').strip()
    combined = f"{title}\n{body}".strip() if title else body
    return combined[:limit]


def _source_material_for_item(test, item, *, skill) -> str:
    q = item['question']
    chunks = []
    blank = _item_blank_context(item)
    if blank:
        chunks.append(f'Blank line: {blank}')
    qtext = (getattr(q, 'question_text', None) or '').strip()
    if qtext:
        chunks.append(qtext[:900])
    if skill == 'reading':
        passage = _passage_excerpt_for_question(test, q)
        if passage:
            chunks.append(passage)
    return '\n---\n'.join(chunks)[:2200]


_QTYPE_TIP_UZ = {
    'true_false_not_given': 'True/False/NG: matnda aniq dalil bo‘lishi kerak. NG = matnda hech narsa yo‘q.',
    'yes_no_not_given': 'Yes/No/NG — muallif fikri. Dalil bo‘lmasa NG.',
    'true_false': 'True/False da faqat matnda aytilgan faktni tanlang.',
    'matching_headings': 'Sarlavhada paragrafning ASOSIY g‘oyasiga qarang, bitta so‘zga emas.',
    'matching_sentences': 'Gap oxirini moslashtirishda synonym va mantiqiy bog‘lanishni qidiring.',
    'matching_features': 'Har bir elementning xos belgisini matndan toping.',
    'matching_info': 'Paragrafdagi asosiy ma’lumotni qidiring, bitta misolga emas.',
    'fill_blank': 'Bo‘sh joyda grammar (article/plural) va spelling muhim.',
    'summary_completion': 'Summary’da gap grammatikasi va passage synonymlariga e’tibor bering.',
    'notes_completion': 'Notes: odatda ONE WORD AND/OR A NUMBER — spelling va word form muhim.',
    'sentence_completion': 'Gapni to‘ldirishda so‘z soni chegarasiga rioya qiling.',
    'table_completion': 'Jadvaldagi qator/ustun kontekstini o‘qing.',
    'short_answer': 'Qisqa va aniq yozing; ortiqcha so‘z qo‘shmang.',
    'mcq': 'Variantlarni matndan isbot bilan tekshiring; distractorlarni chiqarib tashlang.',
    'list_selection': 'Ro‘yxatdan faqat so‘ralgan soncha variantni tanlang.',
    'classification': 'Har kategoriya uchun aniq belgini toping.',
    'summary_box': 'Har bir qavs uchun boxdagi to‘g‘ri harfni tanlang.',
}

_QTYPE_TIP_RU = {
    'true_false_not_given': 'True/False/NG: нужно точное доказательство в тексте. NG = в тексте ничего нет.',
    'yes_no_not_given': 'Yes/No/NG — мнение автора. Нет доказательства → NG.',
    'true_false': 'True/False: выбирайте только факт из текста.',
    'matching_headings': 'В заголовке ищите ГЛАВНУЮ идею абзаца, а не одно слово.',
    'matching_sentences': 'Ищите синонимы и логическую связь окончания предложения.',
    'matching_features': 'Найдите уникальный признак каждого элемента в тексте.',
    'matching_info': 'Ищите основную информацию абзаца, а не один пример.',
    'fill_blank': 'В пропуске важны грамматика (article/plural) и spelling.',
    'summary_completion': 'В summary следите за грамматикой и синонимами из пассажа.',
    'notes_completion': 'Notes: обычно ONE WORD AND/OR A NUMBER — важны spelling и форма слова.',
    'sentence_completion': 'Соблюдайте лимит слов в завершении предложения.',
    'table_completion': 'Читайте контекст строки/столбца таблицы.',
    'short_answer': 'Пишите кратко; не добавляйте лишние слова.',
    'mcq': 'Проверяйте варианты доказательством из текста; отсекайте дистракторы.',
    'list_selection': 'Выбирайте ровно столько вариантов, сколько просят.',
    'classification': 'Для каждой категории найдите чёткий признак.',
    'summary_box': 'Для каждой скобки выбирайте нужную букву из box.',
}


def _local_explanation(item, *, skill='reading', source_text='') -> dict:
    user = (item.get('user_part') or '').strip()
    correct = (item.get('correct_part') or '').strip() or '—'
    q = item['question']
    qtype = getattr(q, 'question_type', '') or 'question'
    tip = _QTYPE_TIP_UZ.get(qtype, 'Savol turiga qarab matndan (yoki audiodan) aniq dalil toping.')
    if skill == 'listening' and qtype in (
        'notes_completion', 'fill_blank', 'table_completion', 'sentence_completion', 'summary_completion',
    ):
        tip = 'Listeningda keyword eshitilganda yozib boring; oldin/keyin aytilgan distractorlarga aldanning.'

    user_disp = user if user else '(javob bermadingiz)'
    blank = _item_blank_context(item)
    evidence = _find_evidence_in_text(source_text, correct) if source_text else ''
    if not evidence and blank:
        evidence = blank[:180]
    if not evidence:
        qtext = (getattr(q, 'question_text', '') or '').strip()
        evidence = (qtext[:140] + ('…' if len(qtext) > 140 else '')) if qtext else ''

    if blank:
        if (item.get('review_layout') or '') == 'prompt':
            explanation = (
                f"Savol: «{blank}». "
                f"To‘g‘ri javob — «{correct}». "
                f"Sizning javobingiz: «{user_disp}». "
                f"Javob aynan so‘ralgan ma’lumotni qisqa va aniq berishi kerak; "
                f"ortiqcha so‘z yoki boshqa faktni yozmang."
            )
            why = (
                f"«{user_disp}» bu savolga mos kelmaydi; kutilgan kalit «{correct}»."
                if user
                else f"Javob berilmagan; savolga to‘g‘ri kalit «{correct}» edi."
            )
        else:
            explanation = (
                f"Bu bo‘sh joy konteksti: «{blank}». "
                f"To‘g‘ri javob — «{correct}», chunki aynan shu qator/gap shu ma’noni kutadi. "
                f"Siz yozgan «{user_disp}» bu joyga mos kelmaydi"
                + (
                    " (boshqa ma’no, noto‘g‘ri so‘z shakli yoki distractor)."
                    if user
                    else " — bo‘sh qoldirilgan."
                )
                + " Keyingi safar avval qatorni o‘qing, keyin kalit so‘zni matn/audiodan tasdiqlang."
            )
            why = (
                f"«{user_disp}» xato, chunki «{blank}» qatorida kerakli ma’no «{correct}»."
                if user
                else f"Javob berilmagan; «{blank}» uchun to‘g‘ri kalit «{correct}» edi."
            )
    else:
        explanation = (
            f"To‘g‘ri javob: «{correct}». Sizning javobingiz: «{user_disp}». "
            f"Bu {qtype.replace('_', ' ')} tipida faqat o‘xshash so‘z emas — "
            f"matn/audiodagi aniq ma’no va dalil muhim. "
            f"To‘g‘ri kalitni savol konteksti bilan solishtirib tekshiring."
        )
        why = (
            f"«{user_disp}» noto‘g‘ri, chunki to‘g‘ri kalit «{correct}». "
            "Synonym yoki distractorni haqiqiy dalil deb o‘ylagan bo‘lishingiz mumkin."
            if user
            else f"Javob berilmagan; to‘g‘ri kalit «{correct}» edi."
        )

    trap = ''
    if user and correct and user.lower() != correct.lower():
        trap = (
            f"«{user_disp}» ko‘pincha chalg‘ituvchi variant — uni «{blank or 'savol'}» "
            "kontekstida matndan tasdiqlamasdan tanlamang."
        )
    elif not user:
        trap = "Bo‘sh qoldirish ham ball yo‘qotadi — noaniq bo‘lsa ham eng yaxshi taxminni yozing."

    return {
        'explanation': explanation,
        'why_wrong': why,
        'tip': tip,
        'evidence_quote': evidence,
        'trap': trap,
        'provider_name': 'local',
        'model_name': 'heuristic-rl-v3',
        'raw_response_json': {'provider': 'local', 'ai_language': 'uz'},
    }


def _local_explanation_ru(item, *, skill='reading', base=None, source_text='') -> dict:
    payload = dict(base or {})
    user = (item.get('user_part') or '').strip()
    correct = (item.get('correct_part') or '').strip() or '—'
    user_disp = user if user else '(нет ответа)'
    q = item['question']
    qtype = getattr(q, 'question_type', '') or 'question'
    blank = _item_blank_context(item)
    tip = _QTYPE_TIP_RU.get(qtype, 'Найдите точное доказательство в тексте/аудио.')
    if skill == 'listening' and qtype in (
        'notes_completion', 'fill_blank', 'table_completion', 'sentence_completion', 'summary_completion',
    ):
        tip = 'На Listening сразу записывайте ключевые слова; не ведитесь на дистракторы до/после.'

    evidence = (payload.get('evidence_quote') or '').strip()
    if not evidence:
        evidence = _find_evidence_in_text(source_text, correct) if source_text else ''
    if not evidence and blank:
        evidence = blank[:180]

    if blank:
        if (item.get('review_layout') or '') == 'prompt':
            explanation = (
                f"Вопрос: «{blank}». "
                f"Правильный ответ — «{correct}». "
                f"Ваш ответ: «{user_disp}». "
                f"Ответ должен кратко и точно давать именно запрошенную информацию, "
                f"без лишних слов и других фактов."
            )
            why = (
                f"«{user_disp}» не подходит к этому вопросу; ожидаемый ключ — «{correct}»."
                if user
                else f"Ответа не было; правильный ключ к вопросу — «{correct}»."
            )
        else:
            explanation = (
                f"Контекст пропуска: «{blank}». "
                f"Правильный ответ — «{correct}», потому что именно эта строка/фраза требует такого значения. "
                f"Ваш ответ «{user_disp}» сюда не подходит"
                + (
                    " (другой смысл, неверная форма слова или дистрактор)."
                    if user
                    else " — поле оставлено пустым."
                )
                + " В следующий раз сначала читайте строку, затем подтверждайте ключ текстом/аудио."
            )
            why = (
                f"«{user_disp}» неверно: в «{blank}» нужен смысл «{correct}»."
                if user
                else f"Ответа не было; для «{blank}» ключ — «{correct}»."
            )
    else:
        explanation = (
            f"Правильный ответ: «{correct}». Ваш ответ: «{user_disp}». "
            f"В задании {qtype.replace('_', ' ')} важно совпадение смысла с текстом/аудио, "
            "а не похожих слов. Сверьте ключ с контекстом вопроса."
        )
        why = (
            f"«{user_disp}» неверно, потому что ключ — «{correct}». "
            "Возможно, синоним или дистрактор показались доказательством."
            if user
            else f"Ответа не было; правильный ключ — «{correct}»."
        )

    if user and correct and user.lower() != correct.lower():
        trap = (
            f"«{user_disp}» часто дистрактор — не выбирайте без подтверждения в контексте "
            f"«{blank or 'вопроса'}»."
        )
    elif not user:
        trap = "Пустой ответ тоже теряет балл — даже при сомнении напишите лучшую догадку."
    else:
        trap = (payload.get('trap') or '').strip()

    payload.update({
        'explanation': explanation,
        'why_wrong': why,
        'tip': tip,
        'evidence_quote': evidence or (payload.get('evidence_quote') or ''),
        'trap': trap,
        'provider_name': payload.get('provider_name') or 'local',
        'model_name': payload.get('model_name') or 'heuristic-rl-v3',
    })
    raw = payload.get('raw_response_json') if isinstance(payload.get('raw_response_json'), dict) else {}
    raw['ai_language'] = 'ru'
    payload['raw_response_json'] = raw
    return payload


def _stamp_ai_language(payload, lang='uz') -> dict:
    lang = normalize_ai_lang(lang)
    raw = payload.get('raw_response_json') if isinstance(payload.get('raw_response_json'), dict) else {}
    raw['ai_language'] = lang
    payload['raw_response_json'] = raw
    return payload


def _localize_rl_explanation(payload, item, *, skill, lang='uz', source_text=''):
    """
    Til belgisini qo'yadi.
    Local/heuristic payload uchun RU matnini yozadi.
    Gemini javobini HECH QACHON generic shablon bilan ustiga yozmaydi.
    """
    lang = normalize_ai_lang(lang)
    provider = (payload.get('provider_name') or '').strip().lower()
    if lang == 'ru' and provider in ('', 'local', 'heuristic'):
        return _local_explanation_ru(item, skill=skill, base=payload, source_text=source_text)
    return _stamp_ai_language(payload, lang)


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
            'temperature': 0.2,
            'topP': 0.9,
            'maxOutputTokens': 1024,
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
        with urllib_request.urlopen(req, timeout=50) as resp:
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


_TYPE_COACH = {
    'true_false_not_given': 'Teach the TRUE vs FALSE vs NOT GIVEN decision rule with THIS statement.',
    'yes_no_not_given': 'Teach YES/NO/NG using the writer\'s view in THIS item.',
    'notes_completion': 'Explain the exact blank line; focus on word form, spelling, and number vs word.',
    'fill_blank': 'Explain the blank grammar/meaning; mention word limit if relevant.',
    'summary_completion': 'Show how the summary paraphrase maps to the passage.',
    'sentence_completion': 'Show how the completed sentence must fit grammatically and semantically.',
    'table_completion': 'Use the table row/column labels as context for the blank.',
    'short_answer': 'Keep the answer short; explain what the question asks for.',
    'mcq': 'Eliminate distractors with evidence; say why the correct option wins.',
    'matching_headings': 'Link the paragraph main idea to the chosen heading.',
    'matching_info': 'Point to where the information sits in the passage.',
    'matching_features': 'Match the unique feature, not a shared detail.',
    'matching_sentences': 'Show the logical/synonym link for the sentence ending.',
}


def _build_prompt(item, *, skill, source_material='', lang='uz', stricter=False) -> str:
    q = item['question']
    options = _options_blurb(q)
    user = (item.get('user_part') or '').strip() or '(no answer)'
    correct = (item.get('correct_part') or '').strip() or '—'
    blank = _item_blank_context(item)
    slot_label = (item.get('slot_label') or item.get('slot_placeholder') or '').strip()
    coach = _TYPE_COACH.get(q.question_type, 'Be concrete for this exact item.')
    strict_block = ''
    if stricter:
        strict_block = """
STRICT RETRY:
- Previous output was too vague / incomplete.
- Do NOT write generic advice like "read carefully" or "check the text".
- You MUST mention the blank/question context and why THIS correct answer fits.
- why_wrong and tip are REQUIRED and must be specific.
"""
    return f"""You are a senior IELTS {skill} examiner-tutor. Explain ONE wrong student answer so the student learns and will not repeat the mistake.

{learner_language_rules(lang)}

Return ONLY valid JSON with these keys:
{{
  "explanation": "4-7 sentences. Must include: (1) the correct answer, (2) the exact place/context it comes from, (3) a mini-lesson for this question type, (4) how to think next time.",
  "why_wrong": "2-4 sentences. Explain why the student's answer fails for THIS item (meaning, form, distractor, or empty).",
  "tip": "1 concrete exam tip the student can apply on the next similar question.",
  "evidence_quote": "Short quote from question/notes/passage that supports the correct answer (max 20 words), or empty if unavailable.",
  "trap": "1 sentence naming the typical trap (paraphrase / absolute word / opposite meaning / wrong word form / number distractor)."
}}

Skill: {skill}
Question type: {q.question_type}
Coach focus: {coach}
Question number / blank: {slot_label or '—'}
Blank / line context: {blank or '—'}
Question text: {(q.question_text or '')[:800]}
Instruction: {(getattr(q, 'question_instruction', None) or '')[:400]}
Options:
{options or '—'}
Student answer: {user}
Correct answer: {correct}
Source material (question notes and/or passage excerpt):
{(source_material or '—')[:1800]}
{strict_block}
Quality rules:
- Be specific to THIS item only. No generic filler.
- Keep English answers, quotes, and keywords in English; explain in the learner language.
- If blank context exists, weave it into explanation (e.g. "Rent per week: £ ___").
- Prefer a real evidence_quote from the source material when possible.
- Never leave explanation or why_wrong empty.
- Do not invent passage facts that are not in the source material; if source is thin, reason from the blank/question text.
"""


def _field_len(payload, key) -> int:
    return len((payload.get(key) or '').strip())


def _payload_is_weak(payload) -> bool:
    """Yuzaki / bo'sh AI javobini aniqlash."""
    if _field_len(payload, 'explanation') < 90:
        return True
    if _field_len(payload, 'why_wrong') < 25:
        return True
    expl = (payload.get('explanation') or '').lower()
    weak_markers = (
        'kalitni matn/audio',
        'совпадение смысла, а не похожих',
        'read the text carefully',
        'check the passage',
        'matndan (yoki audiodan) aniq dalil',
        'be more careful',
    )
    if any(m in expl for m in weak_markers) and _field_len(payload, 'explanation') < 180:
        return True
    return False


def _merge_explanation_payload(ai_payload, local_payload) -> dict:
    """AI yaxshi bo'lsa saqlaydi; bo'sh/zaif maydonlarni local bilan to'ldiradi."""
    out = dict(local_payload)
    used_ai = False
    for key, min_len in (
        ('explanation', 90),
        ('why_wrong', 25),
        ('tip', 20),
        ('trap', 15),
        ('evidence_quote', 8),
    ):
        ai_val = (ai_payload.get(key) or '').strip()
        if len(ai_val) >= min_len:
            out[key] = ai_val
            if key in ('explanation', 'why_wrong'):
                used_ai = True
        elif ai_val and not (out.get(key) or '').strip():
            out[key] = ai_val

    if used_ai:
        out['provider_name'] = ai_payload.get('provider_name') or out.get('provider_name')
        out['model_name'] = ai_payload.get('model_name') or out.get('model_name')
        raw = {}
        if isinstance(local_payload.get('raw_response_json'), dict):
            raw.update(local_payload['raw_response_json'])
        if isinstance(ai_payload.get('raw_response_json'), dict):
            raw.update(ai_payload['raw_response_json'])
        raw['quality_merged'] = True
        out['raw_response_json'] = raw
    return out


def _gemini_payload_from_data(data, *, model, lang) -> dict:
    return {
        'explanation': (data.get('explanation') or '').strip(),
        'why_wrong': (data.get('why_wrong') or '').strip(),
        'tip': (data.get('tip') or '').strip(),
        'evidence_quote': (data.get('evidence_quote') or '').strip()[:400],
        'trap': (data.get('trap') or '').strip()[:500],
        'provider_name': 'gemini',
        'model_name': model,
        'raw_response_json': {
            **(data.get('_raw') or data if isinstance(data.get('_raw') or data, dict) else {}),
            'ai_language': lang,
        },
    }


def generate_explanation_for_item(item, *, test, lang='uz') -> dict:
    skill = getattr(test, 'test_type', 'reading') or 'reading'
    lang = normalize_ai_lang(lang)
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

    source = _source_material_for_item(test, item, skill=skill)
    local = _localize_rl_explanation(
        _local_explanation(item, skill=skill, source_text=source),
        item,
        skill=skill,
        lang=lang,
        source_text=source,
    )

    if provider in ('', 'local', 'heuristic', 'fallback'):
        return local

    if provider == 'gemini':
        errors = []
        best = None

        def _keep_best(candidate):
            nonlocal best
            if best is None:
                best = candidate
                return
            # Uzunroq explanation / to'liqroq why ni afzal ko'ramiz
            score = _field_len(candidate, 'explanation') + _field_len(candidate, 'why_wrong')
            best_score = _field_len(best, 'explanation') + _field_len(best, 'why_wrong')
            if score > best_score:
                best = candidate

        for attempt, stricter in enumerate((False, True)):
            prompt = _build_prompt(
                item,
                skill=skill,
                source_material=source,
                lang=lang,
                stricter=stricter,
            )
            for model in _gemini_model_chain(model_name):
                try:
                    data = _call_gemini_json(prompt, model=model)
                    candidate = _gemini_payload_from_data(data, model=model, lang=lang)
                    _keep_best(candidate)
                    if not _payload_is_weak(candidate):
                        merged = _merge_explanation_payload(candidate, local)
                        return _stamp_ai_language(merged, lang)
                    # zaif — keyingi modelni ham sinab ko'ramiz
                except Exception as exc:
                    errors.append(str(exc)[:200])
                    continue
            # Birinchi urinishda hech bo'lmasa zaif javob bo'lsa — stricter retry
            if attempt == 0 and best is not None:
                continue
            break

        if best:
            merged = _merge_explanation_payload(best, local)
            raw = merged.get('raw_response_json') if isinstance(merged.get('raw_response_json'), dict) else {}
            if errors:
                raw['gemini_errors'] = errors
            raw['quality_fallback'] = _payload_is_weak(best)
            merged['raw_response_json'] = raw
            return _stamp_ai_language(merged, lang)

        fallback = dict(local)
        fallback['raw_response_json'] = {
            **(fallback.get('raw_response_json') or {}),
            'gemini_errors': errors,
        }
        return fallback

    return local


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
    lang = language_for_result(test_result)
    try:
        payload = generate_explanation_for_item(
            item, test=test_result.test, lang=lang,
        )
        if not (payload.get('explanation') or '').strip():
            skill = test_result.test.test_type
            source = _source_material_for_item(test_result.test, item, skill=skill)
            payload = _localize_rl_explanation(
                _local_explanation(item, skill=skill, source_text=source),
                item, skill=skill, lang=lang, source_text=source,
            )
        if language_still_matches(test_result, lang):
            explanation_obj.apply_completed(payload)
    except Exception as exc:
        try:
            if language_still_matches(test_result, lang):
                skill = test_result.test.test_type
                source = _source_material_for_item(test_result.test, item, skill=skill)
                explanation_obj.apply_completed(
                    _localize_rl_explanation(
                        _local_explanation(item, skill=skill, source_text=source),
                        item, skill=skill, lang=lang, source_text=source,
                    )
                )
        except Exception:
            if language_still_matches(test_result, lang):
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
        lang = language_for_result(test_result)
        try:
            payload = generate_explanation_for_item(
                item, test=test_result.test, lang=lang,
            )
            if not (payload.get('explanation') or '').strip():
                skill = test_result.test.test_type
                source = _source_material_for_item(test_result.test, item, skill=skill)
                payload = _localize_rl_explanation(
                    _local_explanation(item, skill=skill, source_text=source),
                    item, skill=skill, lang=lang, source_text=source,
                )
            if language_still_matches(test_result, lang):
                obj.apply_completed(payload)
        except Exception as exc:
            try:
                if language_still_matches(test_result, lang):
                    skill = test_result.test.test_type
                    source = _source_material_for_item(test_result.test, item, skill=skill)
                    obj.apply_completed(_localize_rl_explanation(
                        _local_explanation(item, skill=skill, source_text=source),
                        item, skill=skill, lang=lang, source_text=source,
                    ))
            except Exception:
                if language_still_matches(test_result, lang):
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
    if _generation_lock_held(key):
        if force:
            _GENERATION_IN_FLIGHT.pop(key, None)
        else:
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
            {
                'explanation': obj,
                'show_regen': True,
                'ai_lang': language_for_result(getattr(obj, 'test_result', None)),
            },
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


def _local_insight(test_result, wrong_items, lang='uz') -> dict:
    skill = test_result.test.test_type
    counts = {}
    for it in wrong_items:
        qt = getattr(it['question'], 'question_type', '') or 'other'
        counts[qt] = counts.get(qt, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    weak = [{
        'type': qtype,
        'label': _type_label(qtype),
        'count': c,
        'note': t(lang, f'{c} ta xato — bu turda ko‘proq mashq qiling.', f'{c} ошибок — потренируйте этот тип заданий.'),
    } for qtype, c in ranked[:5]]
    pct = float(getattr(test_result, 'percentage', 0) or 0)
    strengths = []
    if pct >= 70:
        strengths.append(t(lang, 'Umumiy natija yaxshi — endi aniq zaif turlar ustida ishlang.', 'Общий результат хороший — теперь работайте над слабыми типами.'))
    elif pct >= 40:
        strengths.append(t(lang, 'Baza bor; xatolarni tahlil qilib ballni tez oshirishingiz mumkin.', 'База есть; разбор ошибок быстро поднимет балл.'))
    else:
        strengths.append(t(lang, 'Hozir asosiy strategiyani mustahkamlash vaqti.', 'Сейчас время закрепить базовую стратегию.'))
    if not wrong_items:
        strengths = [t(lang, 'Barcha javoblar to‘g‘ri — ajoyib!', 'Все ответы верны — отлично!')]
        weak = []
    next_steps = [
        t(lang, 'Har bir AI tushuntirishdagi «tuzoq»ni eslab qoling.', 'Запомните «ловушку» из каждого AI-разбора.'),
        t(lang, 'Zaif tur bo‘yicha 2–3 ta qo‘shimcha test ishlang.', 'Сделайте ещё 2–3 теста по слабому типу.'),
        t(lang, 'Keyword + synonym jadvalini o‘zingiz yozib boring.', 'Составьте свою таблицу keyword + synonym.'),
    ]
    if skill == 'listening':
        next_steps[0] = t(lang, 'Listeningda distractor eshitilganda darhol chiqarib tashlashni mashq qiling.', 'На Listening сразу отсекайте дистрактор, как только его услышали.')
    summary = t(
        lang,
        f"{skill.title()} natijangiz: {pct:.0f}%. Jami {len(wrong_items)} ta tahlil qilingan xato. "
        + (f"Eng zaif: {_type_label(ranked[0][0])}." if ranked else 'Xato yo‘q.'),
        f"Результат {skill.title()}: {pct:.0f}%. Разобрано ошибок: {len(wrong_items)}. "
        + (f"Самый слабый тип: {_type_label(ranked[0][0])}." if ranked else 'Ошибок нет.'),
    )
    focus = t(
        lang,
        f"Keyingi 3 kunda asosan «{_type_label(ranked[0][0])}» ustida ishlang."
        if ranked else 'Keyingi testda tezlikni saqlab, diqqatni chalg‘itmang.',
        f"В ближайшие 3 дня работайте в основном над «{_type_label(ranked[0][0])}»."
        if ranked else 'На следующем тесте держите темп и не теряйте концентрацию.',
    )
    return {
        'summary': summary,
        'weak_types': weak,
        'strengths': strengths[:4],
        'next_steps': next_steps[:5],
        'focus_tip': focus,
        'provider_name': 'local',
        'model_name': 'heuristic-insight-v1',
        'raw_response_json': {'provider': 'local', 'wrong_counts': counts, 'ai_language': lang},
    }


def _build_insight_prompt(test_result, wrong_items, lang='uz') -> str:
    skill = test_result.test.test_type
    lines = []
    for it in wrong_items[:15]:
        q = it['question']
        lines.append(
            f"- #{it.get('display_num')} type={q.question_type} "
            f"user={it.get('user_part') or '—'} correct={it.get('correct_part') or '—'}"
        )
    return f"""You are an IELTS {skill} coach. Summarize this student's result.

{learner_language_rules(lang)}

Return ONLY JSON:
{{
  "summary": "3-5 sentences overall summary",
  "weak_types": [{{"type":"mcq","label":"Multiple Choice","count":3,"note":"short note"}}],
  "strengths": ["1-3 strengths"],
  "next_steps": ["3-5 practical steps"],
  "focus_tip": "1 main focus point"
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

    lang = language_for_result(test_result)

    try:
        if provider == 'gemini':
            prompt = _build_insight_prompt(test_result, wrong_items, lang=lang)
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
                        'raw_response_json': {
                            **(data.get('_raw') or data if isinstance(data.get('_raw') or data, dict) else {}),
                            'ai_language': lang,
                        },
                    }
                    if not payload['summary']:
                        raise ValueError('empty summary')
                    if language_still_matches(test_result, lang):
                        insight.apply_completed(payload)
                    return insight
                except Exception as exc:
                    last_err = exc
                    continue
            payload = _local_insight(test_result, wrong_items, lang=lang)
            payload['raw_response_json'] = {
                **(payload.get('raw_response_json') or {}),
                'gemini_error': str(last_err)[:300] if last_err else '',
            }
            if language_still_matches(test_result, lang):
                insight.apply_completed(payload)
            return insight
        if language_still_matches(test_result, lang):
            insight.apply_completed(_local_insight(test_result, wrong_items, lang=lang))
        return insight
    except Exception as exc:
        try:
            if language_still_matches(test_result, lang):
                insight.apply_completed(_local_insight(test_result, wrong_items, lang=lang))
        except Exception:
            if language_still_matches(test_result, lang):
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
        {
            'insight': insight,
            'ai_lang': language_for_result(getattr(insight, 'test_result', None)),
        },
        request=request,
    )