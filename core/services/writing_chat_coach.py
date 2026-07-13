"""IELTS Writing AI chat coach — natija sahifasida savol-javob."""

from __future__ import annotations

import json
import os
import time
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.utils import timezone

from core.services.ai_writing_feedback import _gemini_model_chain, _task_meta

COACH_CHAT_DAILY_LIMIT = 25
MAX_HISTORY_TURNS = 6
MAX_MESSAGE_LEN = 800
MAX_REPLY_LEN = 2500

CRITERIA_FIELDS = (
    ('task_achievement', 'Task Achievement'),
    ('coherence_cohesion', 'Coherence'),
    ('lexical_resource', 'Lexical Resource'),
    ('grammar_range_accuracy', 'Grammar'),
)


def build_coach_panel_context(feedback):
    """Chat panel uchun task va tez savollar konteksti."""
    from core.services.ai_writing_feedback import _task_meta

    question = feedback.question
    meta = _task_meta(question) if question else {}
    task_type = meta.get('task_type', 'task2')
    task_label = meta.get('task_label', 'Writing')

    scored = []
    for key, label in CRITERIA_FIELDS:
        val = getattr(feedback, key, None)
        if val is not None:
            scored.append({'key': key, 'label': label, 'value': val})
    weakest = min(scored, key=lambda item: item['value']) if scored else None

    prompts = [
        {'label': 'Eng katta muammo', 'text': 'Eng katta muammo nimada?'},
        {'label': 'Band oshirish', 'text': 'Bandimni qanday oshirsam bo\'ladi?'},
    ]
    if weakest:
        prompts.append({
            'label': weakest['label'],
            'text': (
                f"{weakest['label']} mezonini qanday yaxshilayman? "
                f"(hozirgi ball: {weakest['value']})"
            ),
        })
    if task_type == 'task1':
        prompts.append({'label': 'Overview', 'text': 'Overview qanday yoziladi va misol bering?'})
        prompts.append({'label': 'Taqqoslash', 'text': 'Diagramdagi asosiy trendlarni qanday taqqoslayman?'})
    else:
        prompts.append({'label': 'Pozitsiya', 'text': 'Pozitsiyani qanday aniqroq bildirsam?'})
        prompts.append({'label': 'Body paragraf', 'text': 'Body paragraf strukturasini qanday yozaman?'})

    return {
        'task_label': task_label,
        'task_type': task_type,
        'weakest_criterion': weakest,
        'coach_quick_prompts': prompts[:6],
    }


def coach_chat_remaining(user):
    from django.core.cache import cache

    key = f'wf_chat:{user.pk}:{timezone.localdate().isoformat()}'
    used = int(cache.get(key, 0) or 0)
    return max(0, COACH_CHAT_DAILY_LIMIT - used)


def record_coach_chat(user):
    from django.core.cache import cache

    key = f'wf_chat:{user.pk}:{timezone.localdate().isoformat()}'
    used = int(cache.get(key, 0) or 0)
    cache.set(key, used + 1, timeout=86400)


def _normalize_history(history):
    cleaned = []
    if not isinstance(history, list):
        return cleaned
    for item in history[-MAX_HISTORY_TURNS * 2 :]:
        if not isinstance(item, dict):
            continue
        role = str(item.get('role') or '').strip().lower()
        content = str(item.get('content') or '').strip()[:MAX_MESSAGE_LEN]
        if role not in {'user', 'assistant', 'model'} or not content:
            continue
        if role == 'model':
            role = 'assistant'
        cleaned.append({'role': role, 'content': content})
    return cleaned


def build_coach_context(*, feedback, essay_text):
    question = feedback.question
    meta = _task_meta(question) if question else {'task_label': 'Writing', 'min_words': 250}
    corrections = feedback.sentence_corrections if isinstance(feedback.sentence_corrections, list) else []
    upgrades = feedback.vocabulary_upgrades if isinstance(feedback.vocabulary_upgrades, list) else []
    return {
        'task_label': meta.get('task_label', 'Writing'),
        'min_words': meta.get('min_words', 250),
        'essay_text': (essay_text or '')[:4000],
        'summary': (feedback.summary or '')[:1200],
        'estimated_band': feedback.estimated_band,
        'task_achievement': feedback.task_achievement,
        'coherence_cohesion': feedback.coherence_cohesion,
        'lexical_resource': feedback.lexical_resource,
        'grammar_range_accuracy': feedback.grammar_range_accuracy,
        'improvements': (feedback.improvements or [])[:5],
        'sentence_corrections': corrections[:4],
        'vocabulary_upgrades': upgrades[:5],
        'question_text': (question.question_text or '')[:1500] if question else '',
    }


def _local_coach_reply(message, context):
    lower = message.lower()
    essay_snip = (context.get('essay_text') or '').strip()[:120]
    band = context.get('estimated_band')
    band_txt = f"Taxminiy band: {band}." if band is not None else ''

    if any(w in lower for w in ('band', 'ball', 'score')):
        weak = []
        for key, label in (
            ('task_achievement', 'Task'),
            ('coherence_cohesion', 'Coherence'),
            ('lexical_resource', 'Lexical'),
            ('grammar_range_accuracy', 'Grammar'),
        ):
            val = context.get(key)
            if val is not None and val <= 5.5:
                weak.append(label)
        tip = f"Avval {', '.join(weak)} ustida ishlang." if weak else "Har bir paragrafda bitta asosiy fikr + misol yozing."
        return f"{band_txt} {tip} Keyingi urinishda overview/pozitsiyani aniqroq qiling."

    if any(w in lower for w in ('gap', 'sentence', 'jumla', 'tuzat')):
        corr = (context.get('sentence_corrections') or [])
        if corr:
            c = corr[0]
            return (
                f"Misol tuzatish: «{c.get('original', '')}» → «{c.get('corrected', '')}». "
                f"Sabab: {c.get('why', 'academic tone')}"
            )
        return "Essaydan bitta aniq gapni tanlang va uni academic strukturaga o'zgartiring: subject + verb + object + detail."

    if any(w in lower for w in ('so\'z', 'vocab', 'lexical', 'vocabulary')):
        ups = context.get('vocabulary_upgrades') or []
        if ups:
            u = ups[0]
            return f"«{u.get('from')}» o'rniga «{u.get('to')}» ishlating. {u.get('why', '')}"
        return "Oddiy so'zlarni academic sinonimlarga almashtiring: good→significant, a lot of→numerous, think→argue."

    if any(w in lower for w in ('overview', 'umumiy', 'trend', 'diagram', 'chart', 'graph')):
        return (
            "Task 1 overview uchun: 1) Umumiy trend (oshdi/kamaydi), 2) Eng katta farq, "
            "3) Hech qanday raqam bermasdan. Misol: «Overall, X increased steadily while Y remained stable.» "
            "Keyin body paragraflarda raqamlar bilan tafsilot bering."
        )

    if any(w in lower for w in ('pozitsiya', 'opinion', 'stance', 'fikr', 'body')):
        return (
            "Task 2 struktura: Intro (background + aniq thesis), 2 ta body (har biri bitta idea + misol), "
            "Conclusion (pozitsiyani qayta tasdiqlash). Har body: topic sentence → explanation → example."
        )

    if any(w in lower for w in ('muammo', 'problem', 'xato', 'error', 'improve')):
        improvements = context.get('improvements') or []
        if improvements:
            extra = improvements[1] if len(improvements) > 1 else 'bitta paragrafni qayta yozing.'
            return f"Asosiy muammo: {improvements[0]}. Keyingi qadam: {extra}"
        weak = []
        for key, label in CRITERIA_FIELDS:
            val = context.get(key)
            if val is not None and val <= 6.0:
                weak.append(f"{label} ({val})")
        if weak:
            return f"Avval shu mezonlarga e'tibor bering: {', '.join(weak)}."

    return (
        f"{band_txt} Essayingiz haqida aniqroq so'rang (masalan: overview, paragraf, yoki bitta gap). "
        f"Matn boshlanishi: «{essay_snip}…»"
    )


def _call_gemini_chat(system_prompt, user_payload, *, model_name=''):
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY topilmadi")

    preferred = model_name or getattr(settings, 'AI_WRITING_FEEDBACK_MODEL', '') or os.environ.get('AI_WRITING_FEEDBACK_MODEL', '')
    errors = []
    base_url = os.environ.get('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models').rstrip('/')

    for idx, model in enumerate(_gemini_model_chain(preferred)):
        endpoint = f"{base_url}/{model}:generateContent?key={api_key}"
        body = {
            'generationConfig': {'temperature': 0.45},
            'contents': [
                {
                    'role': 'user',
                    'parts': [
                        {'text': system_prompt},
                        {'text': json.dumps(user_payload, ensure_ascii=False)},
                    ],
                }
            ],
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
            parts = raw['candidates'][0]['content']['parts']
            text = ''.join(str(p.get('text', '') or '') for p in parts if isinstance(p, dict)).strip()
            if not text:
                raise ValueError("Bo'sh javob")
            return text[:MAX_REPLY_LEN], model
        except Exception as exc:
            msg = str(exc)
            errors.append({'model': model, 'error': msg[:300]})
            if '503' in msg or 'UNAVAILABLE' in msg:
                time.sleep(0.6)
            if idx < len(_gemini_model_chain(preferred)) - 1:
                continue
            raise ValueError(f"Gemini chat ishlamadi: {errors[-1]['error']}") from exc
    raise ValueError("Gemini model topilmadi")


def answer_writing_coach_question(*, feedback, essay_text, message, history=None):
    message = (message or '').strip()[:MAX_MESSAGE_LEN]
    if not message:
        raise ValueError("Savol bo'sh bo'lmasligi kerak")

    context = build_coach_context(feedback=feedback, essay_text=essay_text)
    history_clean = _normalize_history(history or [])

    provider = getattr(
        settings,
        'AI_WRITING_FEEDBACK_PROVIDER',
        os.environ.get('AI_WRITING_FEEDBACK_PROVIDER', 'local'),
    ).strip().lower()

    if provider == 'gemini' and os.environ.get('GEMINI_API_KEY', '').strip():
        system = """You are a friendly IELTS Writing coach for Uzbek learners.

Rules:
- Reply in clear Uzbek (Latin). English only for example phrases, corrections, or vocabulary.
- Use THIS essay and feedback context only — do not give generic advice.
- Be specific: quote learner phrases when helpful.
- Keep answers concise (3–6 short paragraphs or bullets max).
- You are NOT an official IELTS examiner; say training advice only if asked about scores.
- If user asks how to improve a sentence, give before→after with brief why."""

        payload = {
            'context': context,
            'conversation_history': history_clean,
            'user_question': message,
        }
        model_name = getattr(settings, 'AI_WRITING_FEEDBACK_MODEL', '') or os.environ.get('AI_WRITING_FEEDBACK_MODEL', '')
        reply, model = _call_gemini_chat(system, payload, model_name=model_name)
        return {
            'reply': reply,
            'provider': 'gemini',
            'model': model,
        }

    return {
        'reply': _local_coach_reply(message, context),
        'provider': 'local',
        'model': 'coach-heuristic',
    }
