import hashlib
import json
import os
import re
import threading
import time
import base64
import mimetypes
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.db import connection
from django.db import transaction

from django.conf import settings

from core.models import AIWritingFeedback, UserTestAnswer

FEEDBACK_ENGINE_VERSION = 9

# Prefer free/stable flash models; skip exhausted ones automatically.
GEMINI_MODEL_FALLBACKS = (
    'gemini-2.5-flash',
    'gemini-flash-lite-latest',
    'gemini-2.0-flash-lite',
    'gemini-2.0-flash',
    'gemini-2.5-flash-lite',
)


def _task_meta(question):
    opts = question.options_json or {}
    part = str(opts.get('part') or opts.get('part_label') or '').strip()
    prompt = (question.question_text or '') + ' ' + (question.question_instruction or '')
    prompt_lower = prompt.lower()
    if part == '1' or 'task 1' in prompt_lower or 'diagram' in prompt_lower or 'chart' in prompt_lower or 'graph' in prompt_lower or 'map' in prompt_lower or 'table' in prompt_lower or 'process' in prompt_lower:
        return {
            'task_type': 'task1',
            'task_label': 'Task 1',
            'min_words': 150,
            'target_words': 170,
        }
    if part == '2' or 'task 2' in prompt_lower or 'discuss' in prompt_lower or 'opinion' in prompt_lower or 'to what extent' in prompt_lower or 'advantage' in prompt_lower:
        return {
            'task_type': 'task2',
            'task_label': 'Task 2',
            'min_words': 250,
            'target_words': 280,
        }
    return {
        'task_type': 'task2',
        'task_label': 'Writing',
        'min_words': 250,
        'target_words': 280,
    }


def build_writing_feedback_prompt(*, test, question, essay_text, has_diagram=False):
    meta = _task_meta(question)
    topic = _extract_topic_hint(question)
    word_count = _word_count(essay_text)
    issue = _classify_essay_issue(essay_text, question, meta=meta)
    opening = _essay_snippet(essay_text, 90)
    starter_pack = _topic_starter_pack(question, meta)

    if meta['task_type'] == 'task1':
        rubric = """Task 1 examiner checklist:
- Overview (overall / in general) bormi?
- Key features tanlanganmi (hamma mayda detallarni sanamay)?
- Comparison/data language: increase, decrease, compared to, respectively?
- Shaxsiy fikr yo'qmi?
- Kamida 150 so'z, 3-4 paragraf?"""
        if has_diagram:
            rubric += """
DIAGRAM MODE: Task diagram/chart image is attached. Use REAL data from the image.
- Check whether overview matches the main trend in the diagram.
- Penalise missing key stages/numbers visible in the image.
- Mention specific figures or stages from the diagram when relevant."""
        weak_mode = """WEAK / SHORT / NONSENSE MODE (issue_hint != ok):
Ball past bo'lishi mumkin, LEKIN feedback boy mini-dars bo'lishi SHART.
- strengths: 2-3 ta (hatto "boshlashga urinish", "savolni ochish" kabi pozitiv)
- improvements: 4-5 ta aniq kamchilik + nima yozish kerak
- next_steps: 4-5 ta amaliy mashq (starter gaplar, vocabulary, timer plan)
- rewrite_suggestion: to'liq 4-paragrafli ENGLISH starter template (ready-to-fill), mavzuga mos
- summary: 3-4 gap — muammo + nima yozishi kerakligi + birinchi 10 daqiqa rejasi"""
    else:
        rubric = """Task 2 examiner checklist:
- Introductionda aniq pozitsiya bormi?
- Har body paragraphda bitta asosiy fikr + izoh + example?
- Counter-argument / balance (agar kerak bo'lsa)?
- Formal academic tone?
- Kamida 250 so'z, 4-5 paragraf?"""
        weak_mode = """WEAK / SHORT / NONSENSE MODE (issue_hint != ok):
Ball past bo'lishi mumkin, LEKIN feedback boy mini-dars bo'lishi SHART.
- strengths: 2-3 ta ijobiy boshlang'ich
- improvements: 4-5 ta
- next_steps: 4-5 ta (pozitsiya formula, argument skeleton, example prompts)
- rewrite_suggestion: 4-5 paragraf ENGLISH fill-in template (Thesis / Body1 / Body2 / Conclusion)
- summary: 3-4 gap, mavzu + birinchi qadam aniq"""

    system = f"""You are a senior IELTS Writing examiner + personal writing coach for Uzbek learners.

Your feedback must feel UNIQUE to THIS essay — quote the learner's exact phrases.
Never give template-only advice that could fit any essay.

GOAL: Raise the learner's band with concrete before→after corrections from THEIR text.

HARD RULES:
1) Return ONLY valid JSON (no markdown fences).
2) Learner-facing text = clear Uzbek (Latin). Criterion keys stay English.
   sentence_corrections.original/corrected and vocabulary_upgrades from/to = English.
3) Always mention topic «{topic}» and quote learner text («{opening}») in summary.
4) Minimum counts:
   - strengths: >= 2
   - improvements: >= 4
   - next_steps: >= 4
   - vocabulary_upgrades: >= 5
   - sentence_corrections: >= 3 (even if essay is weak: invent THE BEST next sentence(s) they should write)
5) estimated_band realistic (weak 2.0–4.5; solid 5.0–7.5). Never inflate.
6) strengths/improvements MUST reference something specific from THIS essay when possible.
7) sentence_corrections:
   - original = exact phrase/sentence from learner (or if empty/nonsense: what they wrote)
   - corrected = improved academic version for THIS topic
   - type = one of: grammar | vocabulary | task | coherence | tone
   - why = short Uzbek explanation
8) writing_errors — ANIQ xatolar (essay ichidagi noto'g'ri qismlar):
   - wrong = aynan essaydagi noto'g'ri so'z yoki qisqa fraza (1–6 so'z), COPY-PASTE from essay_text
   - correct = to'g'ri variant
   - type = grammar | spelling | punctuation | article | tense | preposition | subject_verb | word_choice | plural | capitalization
   - why = qisqa o'zbek tushuntirish (qoida)
   - Minimum 8 ta (150+ so'z essay); kamida 3 ta grammar, 2 ta spelling
   - Scan checklist: articles (a/an/the), subject-verb agreement, apostrophes (don't), uncountable nouns, prepositions, common misspellings, plural -s, capitalization of I
   - NEVER invent errors not present in essay — if unsure, skip
   - Prefer WORD-level errors over full-sentence (wrong="peoples" not whole sentence)
9) If issue_hint != "ok": still give rich coaching + starter corrections for the real topic.
10) rewrite_suggestion = fill-in paragraph plan for THIS topic (English starters OK).
11) Never reply with only "yozing" / generic empty coaching.

{rubric}

{weak_mode}

JSON schema:
{{
  "summary": "3-4 gap: holat + muammo + essay iqtibosi + birinchi qadam",
  "estimated_band": number,
  "task_achievement": number,
  "coherence_cohesion": number,
  "lexical_resource": number,
  "grammar_range_accuracy": number,
  "strengths": ["...", "..."],
  "improvements": ["...", "...", "...", "..."],
  "next_steps": ["...", "...", "...", "..."],
  "vocabulary_upgrades": [
    {{"from": "good", "to": "significant / substantial", "why": "academic tone kuchayadi"}}
  ],
  "sentence_corrections": [
    {{
      "original": "I think cities are very good",
      "corrected": "In my view, urban living offers substantial advantages",
      "type": "vocabulary",
      "why": "Stance va lexis band-friendly"
    }}
  ],
  "writing_errors": [
    {{
      "wrong": "peoples",
      "correct": "people",
      "type": "grammar",
      "why": "People odatda plural; s qo'shilmaydi"
    }},
    {{
      "wrong": "a informations",
      "correct": "information",
      "type": "grammar",
      "why": "Information sanalmaydi (uncountable)"
    }}
  ],
  "rewrite_suggestion": "Paragraf-ready ENGLISH template + qisqa o'zbek izoh"
}}"""

    content = {
        'test_title': test.title,
        'task_label': meta['task_label'],
        'task_type': meta['task_type'],
        'minimum_words': meta['min_words'],
        'target_words': meta['target_words'],
        'topic_hint': topic,
        'issue_hint': issue,
        'essay_word_count': word_count,
        'essay_opening': opening,
        'starter_pack': starter_pack,
        'question_text': question.question_text,
        'question_instruction': question.question_instruction or '',
        'essay_text': essay_text,
        'has_diagram_image': has_diagram,
        'coach_priority': (
            'ENG MUHIM: writing_errors = essaydagi HAR BIR aniq grammatika/imlo xatosi (so\'z darajasida). '
            'wrong matn essay_text dan AYNAN ko\'chirilsin. sentence_corrections alohida (gap tuzatish). '
            'Checklist: peoples/informations, dont/can\'t, their/there, less/fewer, discuss about, subject-verb, articles. '
            'Zaif essay bo\'lsa ham real xatolarni toping.'
        ),
        'error_scan_checklist': [
            'articles a/an/the with countable/uncountable',
            'subject-verb agreement (people is → are)',
            'missing apostrophes (dont → don\'t)',
            'uncountable nouns (informations → information)',
            'preposition errors (depend of → on)',
            'spelling (recieve, enviroment, thier)',
            'capitalization (i → I)',
            'redundant phrases (return back, discuss about)',
        ],
        'scoring_note': 'Ballar IELTS 0–9 half-band. Rasmiy IELTS balli emas — training feedback.',
    }
    return {
        'system': system,
        'user': json.dumps(content, ensure_ascii=False),
    }


def _extract_json_object(raw_text):
    text = (raw_text or '').strip()
    if not text:
        raise ValueError("AI response is empty")
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def parse_feedback_response(raw_text):
    payload = _extract_json_object(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("AI response must be a JSON object")
    return normalize_feedback_payload(payload)


def normalize_feedback_payload(payload):
    def _float_or_none(value):
        if value in (None, ''):
            return None
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        # Round to nearest 0.5 band like IELTS half-bands when close
        return round(max(0.0, min(9.0, num)) * 2) / 2

    def _listify(value):
        if isinstance(value, list):
            items = value
        elif value:
            items = [value]
        else:
            items = []
        cleaned = []
        seen = set()
        for item in items:
            text = str(item).strip().lstrip('-•').strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text[:360])
        return cleaned[:5]

    def _vocab_listify(value):
        items = value if isinstance(value, list) else []
        cleaned = []
        seen = set()
        for item in items:
            if isinstance(item, dict):
                frm = str(item.get('from') or item.get('old') or item.get('basic') or '').strip()
                to = str(item.get('to') or item.get('new') or item.get('upgrade') or '').strip()
                why = str(item.get('why') or item.get('reason') or item.get('note') or '').strip()
            elif isinstance(item, str) and '→' in item:
                left, right = item.split('→', 1)
                frm, to, why = left.strip(), right.strip(), ''
            elif isinstance(item, str) and '->' in item:
                left, right = item.split('->', 1)
                frm, to, why = left.strip(), right.strip(), ''
            else:
                continue
            if not frm or not to:
                continue
            key = f'{frm.lower()}=>{to.lower()}'
            if key in seen:
                continue
            seen.add(key)
            cleaned.append({
                'from': frm[:80],
                'to': to[:120],
                'why': why[:220],
            })
            if len(cleaned) >= 8:
                break
        return cleaned

    def _corrections_listify(value):
        items = value if isinstance(value, list) else []
        cleaned = []
        seen = set()
        allowed_types = {'grammar', 'vocabulary', 'task', 'coherence', 'tone'}
        for item in items:
            if not isinstance(item, dict):
                continue
            original = str(
                item.get('original') or item.get('from') or item.get('before') or ''
            ).strip()
            corrected = str(
                item.get('corrected') or item.get('to') or item.get('after') or ''
            ).strip()
            why = str(item.get('why') or item.get('reason') or item.get('note') or '').strip()
            ctype = str(item.get('type') or item.get('category') or 'vocabulary').strip().lower()
            if ctype not in allowed_types:
                ctype = 'vocabulary'
            if not original or not corrected:
                continue
            key = f'{original.lower()}=>{corrected.lower()}'
            if key in seen:
                continue
            seen.add(key)
            cleaned.append({
                'original': original[:220],
                'corrected': corrected[:260],
                'type': ctype,
                'why': why[:220],
            })
            if len(cleaned) >= 6:
                break
        return cleaned

    def _errors_listify(value):
        items = value if isinstance(value, list) else []
        cleaned = []
        seen = set()
        allowed_types = {
            'grammar', 'spelling', 'punctuation', 'article', 'tense', 'preposition',
            'subject_verb', 'word_choice', 'plural', 'capitalization', 'word_form',
        }
        for item in items:
            if not isinstance(item, dict):
                continue
            wrong = str(
                item.get('wrong') or item.get('error') or item.get('original') or item.get('from') or ''
            ).strip()
            correct = str(
                item.get('correct') or item.get('fixed') or item.get('corrected') or item.get('to') or ''
            ).strip()
            why = str(item.get('why') or item.get('reason') or item.get('note') or '').strip()
            etype = str(item.get('type') or item.get('category') or 'grammar').strip().lower()
            if etype not in allowed_types:
                etype = 'grammar'
            if not wrong or not correct or wrong.lower() == correct.lower():
                continue
            key = f'{wrong.lower()}=>{correct.lower()}'
            if key in seen:
                continue
            seen.add(key)
            cleaned.append({
                'wrong': wrong[:120],
                'correct': correct[:120],
                'type': etype,
                'why': why[:220],
            })
            if len(cleaned) >= 12:
                break
        return cleaned

    normalized = {
        'summary': str(payload.get('summary', '') or '').strip()[:2000],
        'estimated_band': _float_or_none(payload.get('estimated_band')),
        'task_achievement': _float_or_none(payload.get('task_achievement')),
        'coherence_cohesion': _float_or_none(payload.get('coherence_cohesion')),
        'lexical_resource': _float_or_none(payload.get('lexical_resource')),
        'grammar_range_accuracy': _float_or_none(payload.get('grammar_range_accuracy')),
        'strengths': _listify(payload.get('strengths')),
        'improvements': _listify(payload.get('improvements')),
        'next_steps': _listify(payload.get('next_steps')),
        'vocabulary_upgrades': _vocab_listify(
            payload.get('vocabulary_upgrades')
            or payload.get('word_upgrades')
            or payload.get('lexical_upgrades')
            or []
        ),
        'sentence_corrections': _corrections_listify(
            payload.get('sentence_corrections')
            or payload.get('corrections')
            or payload.get('error_corrections')
            or []
        ),
        'writing_errors': _errors_listify(
            payload.get('writing_errors')
            or payload.get('grammar_errors')
            or payload.get('errors')
            or payload.get('mistakes')
            or []
        ),
        'rewrite_suggestion': str(payload.get('rewrite_suggestion', '') or '').strip()[:4000],
        'raw_response_json': payload if isinstance(payload, dict) else {},
    }
    if not normalized['summary']:
        normalized['summary'] = "Essay bo'yicha umumiy tahlil tayyorlandi."
    return normalized


def generate_writing_feedback(*, test, question, essay_text):
    provider = getattr(settings, 'AI_WRITING_FEEDBACK_PROVIDER', os.environ.get('AI_WRITING_FEEDBACK_PROVIDER', 'local')).strip().lower()
    model_name = getattr(settings, 'AI_WRITING_FEEDBACK_MODEL', os.environ.get('AI_WRITING_FEEDBACK_MODEL', '')).strip()
    image_parts = _load_question_image_parts(question)
    has_diagram = bool(image_parts)
    if provider in ('', 'local', 'heuristic', 'fallback'):
        feedback = _generate_local_feedback(test=test, question=question, essay_text=essay_text)
        feedback = _enrich_feedback_payload(feedback, test=test, question=question, essay_text=essay_text)
        feedback['provider_name'] = 'local'
        feedback['model_name'] = model_name or 'heuristic-v7'
        raw = feedback.get('raw_response_json') if isinstance(feedback.get('raw_response_json'), dict) else {}
        raw['vision_used'] = False
        raw['diagram_available'] = has_diagram
        feedback['raw_response_json'] = raw
        return feedback
    if provider == 'openai':
        prompt = build_writing_feedback_prompt(
            test=test, question=question, essay_text=essay_text, has_diagram=has_diagram,
        )
        feedback = _call_openai_compatible(prompt, model_name=model_name)
        feedback = _enrich_feedback_payload(feedback, test=test, question=question, essay_text=essay_text)
        feedback['provider_name'] = 'openai'
        feedback['model_name'] = model_name or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        return feedback
    if provider == 'gemini':
        prompt = build_writing_feedback_prompt(
            test=test, question=question, essay_text=essay_text, has_diagram=has_diagram,
        )
        try:
            feedback, used_model = _call_gemini_with_fallback(
                prompt, model_name=model_name, image_parts=image_parts,
            )
            feedback = _enrich_feedback_payload(feedback, test=test, question=question, essay_text=essay_text)
            feedback['provider_name'] = 'gemini'
            feedback['model_name'] = used_model
            raw = feedback.get('raw_response_json') if isinstance(feedback.get('raw_response_json'), dict) else {}
            raw['vision_used'] = bool(image_parts)
            raw['diagram_available'] = has_diagram
            feedback['raw_response_json'] = raw
            return feedback
        except Exception as exc:
            fallback = _generate_local_feedback(test=test, question=question, essay_text=essay_text)
            fallback = _enrich_feedback_payload(fallback, test=test, question=question, essay_text=essay_text)
            fallback['provider_name'] = 'local'
            fallback['model_name'] = 'heuristic-fallback-v7'
            fallback['raw_response_json'] = {
                **(fallback.get('raw_response_json') or {}),
                'gemini_error': str(exc)[:500],
                'vision_used': False,
                'diagram_available': has_diagram,
            }
            return fallback
    raise ValueError(f"Unsupported AI_WRITING_FEEDBACK_PROVIDER: {provider}")


def _feedback_needs_refresh(feedback, *, force=False, essay_text=''):
    if force:
        return True
    if feedback.status in (
        AIWritingFeedback.STATUS_PENDING,
        AIWritingFeedback.STATUS_FAILED,
    ):
        return True
    if not feedback.summary:
        return True
    raw = feedback.raw_response_json if isinstance(feedback.raw_response_json, dict) else {}
    if raw.get('engine_version') != FEEDBACK_ENGINE_VERSION:
        return True
    if essay_text:
        fingerprint = _essay_fingerprint(essay_text)
        if raw.get('essay_fingerprint') and raw.get('essay_fingerprint') != fingerprint:
            return True
    if 'Gemini vaqtincha ishlamadi' in (feedback.summary or ''):
        return True
    # Prefer regenerating old local-fallback when Gemini becomes available again? Skip for now.
    return False


# result_id -> monotonic start time. TTL clears zombie locks when worker/thread dies.
_GENERATION_IN_FLIGHT = {}
_GENERATION_LOCK_TTL_SEC = 180  # 3 daqiqa — undan keyin qayta urinish mumkin
_STALE_PENDING_SEC = 120  # 2 daqiqa pending qolsa — qayta ishga tushirish


def _essay_answers_for_result(test_result):
    return (
        UserTestAnswer.objects
        .select_related('question', 'test_result', 'ai_feedback')
        .filter(test_result=test_result, question__question_type='essay')
    )


def prepare_writing_feedback_placeholders(test_result):
    for answer in _essay_answers_for_result(test_result):
        essay_text = (answer.user_answer or '').strip()
        if not essay_text:
            continue
        AIWritingFeedback.objects.get_or_create(
            test_result=test_result,
            test_answer=answer,
            defaults={'question': answer.question, 'status': AIWritingFeedback.STATUS_PENDING},
        )


def writing_feedback_needs_generation(test_result, *, force=False):
    for answer in _essay_answers_for_result(test_result):
        essay_text = (answer.user_answer or '').strip()
        if not essay_text:
            continue
        try:
            feedback = answer.ai_feedback
        except AIWritingFeedback.DoesNotExist:
            return True
        if _feedback_needs_refresh(feedback, force=force, essay_text=essay_text):
            return True
    return False


def writing_feedback_is_stale_pending(test_result, *, stale_after_sec=_STALE_PENDING_SEC):
    """Pending holatda uzoq qolib ketgan feedbackni aniqlash (o'lik fon thread)."""
    from django.utils import timezone

    now = timezone.now()
    for item in load_writing_feedback_for_result(test_result):
        if item.status != AIWritingFeedback.STATUS_PENDING:
            continue
        stamp = item.updated_at or item.created_at
        if not stamp:
            return True
        if (now - stamp).total_seconds() >= stale_after_sec:
            return True
    return False


def generate_writing_feedback_for_result(test_result, *, force=False):
    generated = []
    for answer in _essay_answers_for_result(test_result):
        essay_text = (answer.user_answer or '').strip()
        if not essay_text:
            continue
        feedback, _ = AIWritingFeedback.objects.get_or_create(
            test_result=test_result,
            test_answer=answer,
            defaults={'question': answer.question, 'status': AIWritingFeedback.STATUS_PENDING},
        )
        if not _feedback_needs_refresh(feedback, force=force, essay_text=essay_text):
            generated.append(feedback)
            continue
        feedback.question = answer.question
        feedback.status = AIWritingFeedback.STATUS_PENDING
        feedback.save(update_fields=['question', 'status', 'updated_at'])
        try:
            payload = generate_writing_feedback(
                test=test_result.test,
                question=answer.question,
                essay_text=essay_text,
            )
            raw = payload.get('raw_response_json') or {}
            if isinstance(raw, dict):
                raw['engine_version'] = FEEDBACK_ENGINE_VERSION
                raw['essay_fingerprint'] = _essay_fingerprint(essay_text)
                payload['raw_response_json'] = raw
            feedback.apply_completed_feedback(payload)
        except Exception as exc:
            feedback.mark_failed(str(exc))
        generated.append(feedback)
    return generated


def load_writing_feedback_for_result(test_result):
    return list(
        AIWritingFeedback.objects
        .filter(test_result=test_result)
        .select_related('test_answer', 'question')
        .order_by('test_answer__question__order', 'id')
    )


def _generation_lock_held(key):
    started = _GENERATION_IN_FLIGHT.get(key)
    if started is None:
        return False
    if (time.monotonic() - started) > _GENERATION_LOCK_TTL_SEC:
        _GENERATION_IN_FLIGHT.pop(key, None)
        return False
    return True


def schedule_writing_feedback_generation(test_result_id, *, force=False):
    key = int(test_result_id)
    if _generation_lock_held(key):
        return False

    _GENERATION_IN_FLIGHT[key] = time.monotonic()

    def _run():
        try:
            from core.models import UserTestResult

            test_result = UserTestResult.objects.select_related('test').get(pk=test_result_id)
            generate_writing_feedback_for_result(test_result, force=force)
        except Exception:
            # Thread o'lishi mumkin — status failed/pending qoladi; stale recovery qayta urinadi.
            raise
        finally:
            _GENERATION_IN_FLIGHT.pop(key, None)
            connection.close()

    def _start():
        threading.Thread(target=_run, daemon=True, name=f'wf-gen-{key}').start()

    try:
        transaction.on_commit(_start)
    except Exception:
        _start()
    return True


def ensure_writing_feedback_for_result(test_result, *, force=False, sync=False):
    prepare_writing_feedback_placeholders(test_result)
    if sync:
        return generate_writing_feedback_for_result(test_result, force=force)

    needs = writing_feedback_needs_generation(test_result, force=force)
    stale = writing_feedback_is_stale_pending(test_result)
    if needs or stale:
        # Stale pending = fon thread o'lib ketgan (gunicorn worker recycle). Qayta ishga tushirish.
        schedule_writing_feedback_generation(test_result.pk, force=force or stale)
    return load_writing_feedback_for_result(test_result)


def _call_openai_compatible(prompt, *, model_name=''):
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY topilmadi")
    endpoint = os.environ.get('OPENAI_API_URL', 'https://api.openai.com/v1/chat/completions').strip()
    model = model_name or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    body = {
        'model': model,
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': prompt['system']},
            {'role': 'user', 'content': prompt['user']},
        ],
        'temperature': 0.3,
    }
    req = urllib_request.Request(
        endpoint,
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        method='POST',
    )
    try:
        with urllib_request.urlopen(req, timeout=45) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise ValueError(f"OpenAI so'rovida xatolik: {detail or exc.reason}") from exc
    except urllib_error.URLError as exc:
        raise ValueError(f"AI provider bilan aloqa bo'lmadi: {exc.reason}") from exc

    try:
        content = raw['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("OpenAI response format noto'g'ri") from exc
    feedback = parse_feedback_response(content)
    feedback['raw_response_json'] = raw
    return feedback


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


def _collect_question_image_file_paths(question):
    paths = []
    if question.question_image:
        try:
            paths.append(question.question_image.path)
        except (ValueError, AttributeError, OSError):
            pass
    media_root = getattr(settings, 'MEDIA_ROOT', '') or ''
    for item in (question.options_json or {}).get('images', []):
        path = item if isinstance(item, str) else (item.get('path') or item.get('url', ''))
        if not path or str(path).startswith(('http://', 'https://')):
            continue
        normalized = str(path).lstrip('/')
        if normalized.startswith('media/'):
            normalized = normalized[6:]
        full_path = normalized if os.path.isabs(normalized) else os.path.join(media_root, normalized)
        paths.append(full_path)
    return paths


def _load_question_image_parts(question, *, max_images=2, max_bytes=4_000_000):
    parts = []
    for path in _collect_question_image_file_paths(question)[:max_images]:
        if not path or not os.path.isfile(path):
            continue
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if size > max_bytes:
            continue
        mime, _ = mimetypes.guess_type(path)
        if not mime or not mime.startswith('image/'):
            mime = 'image/jpeg'
        try:
            with open(path, 'rb') as handle:
                data = base64.b64encode(handle.read()).decode('ascii')
        except OSError:
            continue
        parts.append({'inline_data': {'mime_type': mime, 'data': data}})
    return parts


def _call_gemini_with_fallback(prompt, *, model_name='', image_parts=None):
    errors = []
    for idx, model in enumerate(_gemini_model_chain(model_name)):
        try:
            feedback = _call_gemini_once(prompt, model=model, image_parts=image_parts)
            raw = feedback.get('raw_response_json')
            if isinstance(raw, dict):
                raw['gemini_model_used'] = model
                raw['gemini_attempts'] = errors
                feedback['raw_response_json'] = raw
            return feedback, model
        except Exception as exc:
            msg = str(exc)
            errors.append({'model': model, 'error': msg[:300]})
            # Soft-retry once on transient overload
            if '503' in msg or 'high demand' in msg.lower() or 'UNAVAILABLE' in msg:
                time.sleep(0.8)
                try:
                    feedback = _call_gemini_once(prompt, model=model, image_parts=image_parts)
                    return feedback, model
                except Exception as retry_exc:
                    errors.append({'model': model, 'error': f'retry: {str(retry_exc)[:250]}'})
            # Continue to next model on quota/404/etc.
            if idx < len(_gemini_model_chain(model_name)) - 1:
                continue
            raise ValueError(f"Barcha Gemini modellar ishlamadi: {errors[-1]['error']}") from exc
    raise ValueError("Gemini model topilmadi")


def _call_gemini_once(prompt, *, model, image_parts=None):
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY topilmadi")
    base_url = os.environ.get('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models').rstrip('/')
    endpoint = f"{base_url}/{model}:generateContent?key={api_key}"
    content_parts = [
        {'text': prompt['system']},
        {'text': prompt['user']},
    ]
    if image_parts:
        content_parts.append({'text': 'Attached task diagram/chart image(s). Analyse them against the essay:'})
        content_parts.extend(image_parts)
    body = {
        'generationConfig': {
            'temperature': 0.4,
            'responseMimeType': 'application/json',
        },
        'contents': [
            {
                'role': 'user',
                'parts': content_parts,
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
        with urllib_request.urlopen(req, timeout=55) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise ValueError(f"Gemini so'rovida xatolik ({model}): {detail or exc.reason}") from exc
    except urllib_error.URLError as exc:
        raise ValueError(f"Gemini bilan aloqa bo'lmadi: {exc.reason}") from exc

    try:
        parts = raw['candidates'][0]['content']['parts']
        content = ''.join(str(part.get('text', '') or '') for part in parts if isinstance(part, dict)).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Gemini response format noto'g'ri") from exc
    feedback = parse_feedback_response(content)
    feedback['raw_response_json'] = raw
    return feedback


def _english_ratio(text):
    words = re.findall(r"[A-Za-z']+", text or '')
    if not words:
        return 0.0
    return len(words) / max(_word_count(text), 1)


def _essay_fingerprint(essay_text):
    return hashlib.sha256((essay_text or '').strip().encode('utf-8')).hexdigest()[:16]


def _normalize_compare(text):
    lowered = (text or '').lower()
    lowered = re.sub(r'[^\w\s]', ' ', lowered)
    return ' '.join(lowered.split())


def _essay_snippet(essay_text, limit=72):
    snippet = ' '.join((essay_text or '').split())
    if len(snippet) <= limit:
        return snippet
    return snippet[: limit - 1].rstrip() + '…'


def _pick_quote(essay_text, max_words=12):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', essay_text or '') if s.strip()]
    candidate = sentences[0] if sentences else (essay_text or '').strip()
    words = candidate.split()
    if len(words) > max_words:
        candidate = ' '.join(words[:max_words]) + '…'
    return candidate[:90]


def _extract_topic_hint(question):
    prompt = (question.question_text or '') + ' ' + (question.question_instruction or '')
    prompt = re.sub(r'You should spend about \d+ minutes.*?\n+', '', prompt, flags=re.IGNORECASE)
    prompt = re.sub(r'Write at least \d+ words\.?\s*', '', prompt, flags=re.IGNORECASE)
    for line in prompt.splitlines():
        line = line.strip()
        if len(line) >= 25:
            return line[:180]
    cleaned = ' '.join(prompt.split())
    return cleaned[:180] if cleaned else 'bu topshiriq'


def _is_greeting_only(essay_text):
    text = (essay_text or '').strip().lower()
    if not text:
        return True
    greeting_patterns = (
        'salom', 'hello', 'hi ', 'hi.', 'my name is', 'mening ismim', 'ismim ',
        'assalom', 'good morning', 'good afternoon',
    )
    wc = _word_count(essay_text)
    if wc <= 15 and any(p in text for p in greeting_patterns):
        return True
    return False


def _is_prompt_echo(essay_text, question):
    essay_n = _normalize_compare(essay_text)
    if len(essay_n) < 12:
        return False
    prompt_n = _normalize_compare(
        (question.question_text or '') + ' ' + (question.question_instruction or '')
    )
    if not prompt_n:
        return False
    if essay_n in prompt_n:
        return True
    essay_words = [w for w in essay_n.split() if len(w) > 2]
    if not essay_words:
        return False
    prompt_word_set = set(prompt_n.split())
    overlap = sum(1 for w in essay_words if w in prompt_word_set)
    return overlap / len(essay_words) >= 0.8


def _is_nonsense_text(essay_text):
    text = (essay_text or '').strip()
    if not text:
        return False
    words = re.findall(r"[A-Za-zА-Яа-яЁё'ʻʼ]+", text)
    if not words:
        # only digits/symbols
        return True
    if len(words) <= 20:
        vowel_re = re.compile(r'[aeiouаеиоуўяюё]', re.IGNORECASE)
        weird = 0
        for w in words:
            letters = re.findall(r'[A-Za-zА-Яа-яЁё]', w)
            if len(letters) < 2:
                continue
            vowel_ratio = len(vowel_re.findall(w)) / max(len(letters), 1)
            unique_ratio = len(set(letters)) / max(len(letters), 1)
            # keyboard smash / random: few vowels OR very few unique letters
            if vowel_ratio < 0.18 or unique_ratio <= 0.35:
                weird += 1
        if weird / max(len(words), 1) >= 0.55:
            return True
    # repeated same token spam
    lowered = [w.lower() for w in words]
    if len(lowered) >= 4 and len(set(lowered)) <= 2:
        return True
    return False


def _topic_keywords(question, limit=8):
    prompt = (question.question_text or '') + ' ' + (question.question_instruction or '')
    stop = {
        'should', 'spend', 'about', 'minutes', 'write', 'least', 'words', 'below', 'shows',
        'shown', 'graph', 'chart', 'diagram', 'table', 'map', 'summarise', 'summarize',
        'information', 'selecting', 'reporting', 'main', 'features', 'make', 'comparisons',
        'where', 'relevant', 'people', 'think', 'discuss', 'both', 'views', 'give', 'your',
        'opinion', 'extent', 'agree', 'disagree', 'following', 'question', 'this', 'that',
        'which', 'their', 'there', 'these', 'those', 'with', 'from', 'have', 'been',
    }
    words = []
    seen = set()
    for w in re.findall(r"[A-Za-z]{4,}", prompt.lower()):
        if w in stop or w in seen:
            continue
        seen.add(w)
        words.append(w)
        if len(words) >= limit:
            break
    return words


def _topic_starter_pack(question, meta):
    topic = _extract_topic_hint(question)
    keys = _topic_keywords(question)
    key_line = ', '.join(keys[:6]) if keys else 'key features'
    if meta['task_type'] == 'task1':
        return {
            'useful_vocab': [
                'overall', 'increase', 'decrease', 'peak', 'remain stable',
                'compared to', 'respectively', 'significant',
            ],
            'starter_sentences': [
                f"The diagram/graph illustrates {topic[:70]}.",
                "Overall, the most noticeable feature is ...",
                "In the first stage/period, ...",
                "By contrast, ... / Compared to ..., ...",
            ],
            'paragraph_plan': [
                'Introduction (paraphrase question)',
                'Overview (2 key trends)',
                'Body 1 (details + numbers/stages)',
                'Body 2 (comparison / later stages)',
            ],
            'focus_keys': key_line,
        }
    return {
        'useful_vocab': [
            'in my opinion', 'furthermore', 'however', 'for example',
            'as a result', 'on the other hand', 'to conclude',
        ],
        'starter_sentences': [
            f"Some people argue that {topic[:70]}.",
            "In my opinion, I believe that ...",
            "The main reason is that ..., for example ...",
            "Another important point is that ...",
            "In conclusion, I would argue that ...",
        ],
        'paragraph_plan': [
            'Introduction + clear position',
            'Body 1: argument + example',
            'Body 2: argument + example',
            'Conclusion: restate position',
        ],
        'focus_keys': key_line,
    }


def _rich_rewrite_template(meta, topic, starter_pack):
    starters = starter_pack.get('starter_sentences') or []
    if meta['task_type'] == 'task1':
        s0 = starters[0] if starters else f"The visual illustrates {topic[:70]}."
        s1 = starters[1] if len(starters) > 1 else "Overall, the main trend is ..."
        s2 = starters[2] if len(starters) > 2 else "In the first stage/period, ..."
        s3 = starters[3] if len(starters) > 3 else "By contrast, ..."
        return (
            f"1) Introduction: {s0}\n"
            f"2) Overview: {s1}\n"
            f"3) Body 1: {s2} (asosiy feature + detail).\n"
            f"4) Body 2: {s3} (taqqoslash / keyingi bosqich).\n"
            f"Eslatma: kamida {meta['min_words']} so'z, shaxsiy fikr yozmang. "
            f"Kalit so'zlar: {starter_pack.get('focus_keys', '')}."
        )
    s0 = starters[0] if starters else f"This essay discusses {topic[:70]}."
    s1 = starters[1] if len(starters) > 1 else "In my opinion, ..."
    s2 = starters[2] if len(starters) > 2 else "The main reason is that ..."
    s3 = starters[3] if len(starters) > 3 else "Another important point is that ..."
    s4 = starters[4] if len(starters) > 4 else "In conclusion, ..."
    return (
        f"1) Introduction: {s0} {s1}\n"
        f"2) Body 1: {s2}\n"
        f"3) Body 2: {s3}\n"
        f"4) Conclusion: {s4}\n"
        f"Eslatma: kamida {meta['min_words']} so'z, har bodyda 1 argument + example. "
        f"Kalit so'zlar: {starter_pack.get('focus_keys', '')}."
    )


def _classify_essay_issue(essay_text, question, *, meta):
    wc = _word_count(essay_text)
    eng_ratio = _english_ratio(essay_text)
    if not (essay_text or '').strip():
        return 'empty'
    if _is_greeting_only(essay_text):
        return 'greeting_only'
    if _is_nonsense_text(essay_text):
        return 'nonsense'
    if _is_prompt_echo(essay_text, question):
        return 'prompt_echo'
    if eng_ratio < 0.55:
        return 'wrong_language'
    if wc < max(25, int(meta['min_words'] * 0.15)):
        return 'too_short'
    if _looks_off_topic(essay_text, question):
        return 'off_topic'
    return 'ok'


def _looks_off_topic(essay_text, question):
    text = (essay_text or '').strip().lower()
    wc = _word_count(essay_text)
    if wc < 40:
        return False
    prompt_words = set(re.findall(r'[a-z]{5,}', (question.question_text or '').lower()))
    essay_words = set(re.findall(r'[a-z]{5,}', text))
    if prompt_words:
        overlap = len(prompt_words & essay_words)
        if overlap < 2 and _english_ratio(essay_text) < 0.55:
            return True
    return False


# Basic → higher-band upgrades (Lexical Resource). Ordered by priority.
_COMMON_VOCAB_UPGRADES = (
    ('a lot of', 'a significant number of / a considerable amount of', 'Academic tone va aniqlik oshadi'),
    ('lots of', 'numerous / a wide range of', 'Oddiy spoken til o\'rniga formal variant'),
    ('very big', 'substantial / considerable', 'Band 6+ uchun aniqroq sifat'),
    ('very good', 'highly effective / remarkably beneficial', 'Lexical precision yaxshilanadi'),
    ('very bad', 'highly detrimental / considerably harmful', 'Formal negative evaluation'),
    ('go up', 'increase / rise / climb', 'Task 1 trend vocabulary'),
    ('go down', 'decrease / decline / fall', 'Task 1 trend vocabulary'),
    ('get better', 'improve / enhance', 'Academic verb'),
    ('get worse', 'deteriorate / worsen', 'Academic verb'),
    ('make sure', 'ensure / guarantee', 'Formaler phrasing'),
    ('help', 'assist / facilitate / contribute to', 'Lexical resource kengayadi'),
    ('show', 'illustrate / demonstrate / indicate', 'Task 1/2 da kuchliroq'),
    ('say', 'argue / claim / suggest', 'Opinion essay uchun yaxshi'),
    ('think', 'believe / consider / maintain', 'Band oshiradigan stance verb'),
    ('important', 'crucial / essential / significant', 'Takrorlashni kamaytiradi'),
    ('big', 'significant / substantial / major', 'Aniqroq adjective'),
    ('small', 'minor / limited / modest', 'Academic adjective'),
    ('good', 'beneficial / advantageous / effective', 'Lexical upgrade'),
    ('bad', 'detrimental / adverse / harmful', 'Lexical upgrade'),
    ('people', 'individuals / the public / citizens', 'Formaler noun'),
    ('thing', 'factor / aspect / issue', 'Vague nounni aniqroq qiladi'),
    ('stuff', 'materials / content / items', 'Spoken tilni formal qiladi'),
    ('kids', 'children / young people', 'Academic register'),
    ('money', 'financial resources / funding / income', 'Topic-specific precision'),
    ('problem', 'issue / challenge / drawback', 'Variety uchun'),
    ('because', 'due to the fact that / owing to', 'Complex linker (ehtiyot bilan)'),
    ('so', 'therefore / consequently / as a result', 'Cohesive device'),
    ('but', 'however / nevertheless / on the other hand', 'Academic contrast'),
    ('also', 'furthermore / in addition / moreover', 'Formal addition'),
    ('nowadays', 'in contemporary society / in recent years', 'Band 7 opening uchun'),
    ('i think', 'in my view / i would argue that', 'Task 2 stance'),
    ('in my opinion', 'from my perspective / i firmly believe that', 'Variatsiya'),
    ('more and more', 'an increasing number of / increasingly', 'Less repetitive'),
    ('every day', 'on a daily basis / routinely', 'Formaler adverbial'),
    ('some people', 'a considerable proportion of society / many individuals', 'Paraphrase'),
)


_TASK1_TOPIC_UPGRADES = (
    ('increase', 'rise sharply / experience an upward trend', 'Trend tilini boyitadi'),
    ('decrease', 'decline steadily / drop significantly', 'Trend tilini boyitadi'),
    ('change', 'fluctuate / undergo a notable shift', 'Precise description'),
    ('same', 'remain stable / remain relatively unchanged', 'Overview vocabulary'),
    ('different', 'vary considerably / differ markedly', 'Comparison language'),
    ('highest', 'reach a peak / hit a high of', 'Data language'),
    ('lowest', 'hit a low of / reach a trough', 'Data language'),
)


_TASK2_TOPIC_UPGRADES = (
    ('agree', 'I firmly agree / I am convinced that', 'Clearer position'),
    ('disagree', 'I strongly disagree / I would contest the view that', 'Clearer position'),
    ('advantage', 'benefit / merit / positive aspect', 'Lexical range'),
    ('disadvantage', 'drawback / shortcoming / adverse effect', 'Lexical range'),
    ('reason', 'underlying factor / primary cause', 'Precision'),
    ('example', 'a clear illustration of this is / for instance', 'Better exemplification'),
    ('government', 'policymakers / the authorities', 'Academic register'),
    ('education', 'formal schooling / educational attainment', 'Topic paraphrase'),
)


def _build_vocabulary_upgrades(*, essay_text, meta, question, limit=6):
    text = f" {(essay_text or '').lower()} "
    upgrades = []
    seen_from = set()

    def _add(frm, to, why):
        key = frm.lower()
        if key in seen_from:
            return
        seen_from.add(key)
        upgrades.append({'from': frm, 'to': to, 'why': why})

    # Prefer words actually present in the learner essay
    for frm, to, why in _COMMON_VOCAB_UPGRADES:
        needle = f' {frm.lower()} '
        if needle in text or text.strip().startswith(frm.lower()) or f' {frm.lower()}.' in text:
            _add(frm, to, why)
        if len(upgrades) >= limit:
            return upgrades[:limit]

    topic_bank = _TASK1_TOPIC_UPGRADES if meta['task_type'] == 'task1' else _TASK2_TOPIC_UPGRADES
    for frm, to, why in topic_bank:
        if f' {frm.lower()} ' in text:
            _add(frm, to, f"{why} (mavzu: {_extract_topic_hint(question)[:40]})")
        if len(upgrades) >= limit:
            return upgrades[:limit]

    # If essay is too weak to contain basics, still teach high-value replacements
    teaching_defaults = list(_COMMON_VOCAB_UPGRADES[:4]) + list(topic_bank[:4])
    for frm, to, why in teaching_defaults:
        _add(frm, to, why)
        if len(upgrades) >= limit:
            break

    # Attach topic keyword tips
    keys = _topic_keywords(question, limit=4)
    if keys and len(upgrades) < limit:
        _add(
            'basic topic words',
            ' / '.join(keys),
            'Shu mavzu kalit so\'zlarini paraphraselab ishlating — Lexical Resource oshadi',
        )

    return upgrades[:limit]


def _build_sentence_corrections(*, essay_text, meta, question, issue='ok', limit=4):
    topic = _extract_topic_hint(question)
    pack = _topic_starter_pack(question, meta)
    starters = pack.get('starter_sentences') or []
    quote = _pick_quote(essay_text, max_words=16) or (essay_text or '').strip()[:80] or '—'
    corrections = []

    def _add(original, corrected, ctype, why):
        if not original or not corrected:
            return
        corrections.append({
            'original': original[:220],
            'corrected': corrected[:260],
            'type': ctype,
            'why': why[:220],
        })

    if issue in ('empty', 'greeting_only', 'nonsense'):
        _add(
            quote if quote != '—' else '(bo\'sh / ma\'nosiz matn)',
            starters[0] if starters else f"The visual / essay discusses {topic[:60]}.",
            'task',
            'Avval mavzuga mos academic kirish gapidan boshlang',
        )
        if len(starters) > 1:
            _add(
                'Overview / position yo\'q',
                starters[1],
                'coherence',
                'Ikkinchi gap overview yoki aniq pozitsiya bo\'lishi kerak',
            )
        if meta['task_type'] == 'task1':
            _add(
                'Details kam',
                'In the first stage/period, ... Then, ... Finally, ...',
                'task',
                'Asosiy bosqich/trendni ketma-ket yozing',
            )
            _add(
                'Comparison yo\'q',
                'By contrast / Compared to the earlier figure, ...',
                'vocabulary',
                'Taqqoslash tili Task 1 ballini oshiradi',
            )
        else:
            _add(
                'Argument zaif',
                'The main reason is that ..., for example ...',
                'task',
                'Har bodyda sabab + misol kerak',
            )
            _add(
                'Conclusion yo\'q',
                'In conclusion, I would argue that ...',
                'coherence',
                'Xulosa pozitsiyani qayta tasdiqlashi kerak',
            )
    elif issue == 'prompt_echo':
        _add(
            quote,
            starters[0] if starters else f"This response paraphrases and analyses {topic[:55]}.",
            'task',
            'Savolni ko\'chirmang — paraphrase + tahlil yozing',
        )
        if len(starters) > 1:
            _add('Overview kerak', starters[1], 'coherence', 'Overview/position bilan davom eting')
        if meta['task_type'] == 'task1':
            _add(
                'Faqat 1 gap',
                'Overall, the most significant feature is ... Additionally, ...',
                'task',
                'Kamida overview + 2 body detail kerak',
            )
        else:
            _add(
                'Faqat 1 gap',
                'In my opinion, ... The first supporting argument is that ...',
                'task',
                'Pozitsiya + argument bilan kengaytiring',
            )
    elif issue == 'too_short':
        _add(
            quote,
            f"{quote.rstrip('.')} , which is an important point that needs further development.",
            'coherence',
            'Boshlang\'ich fikrni 1-2 gap bilan kengaytiring',
        )
        if len(starters) > 1:
            _add('Keyingi paragraf', starters[1], 'task', 'Overview/position qo\'shing')
        _add(
            'Example yo\'q',
            'For example, ...',
            'task',
            'Har asosiy fikrga aniq misol qo\'ying',
        )
    elif issue == 'wrong_language':
        _add(
            quote,
            starters[0] if starters else f"This essay discusses {topic[:60]}.",
            'tone',
            'IELTS Writing faqat Englishda baholanadi',
        )
        _add(
            'O\'zbekcha g\'oya',
            'I would argue that ... because ... For example, ...',
            'vocabulary',
            'G\'oyangizni academic Englishga o\'tkazing',
        )
    else:
        # Decent essay: upgrade real sentences / phrases found in text
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', essay_text or '') if s.strip()]
        for sent in sentences[:3]:
            low = f' {sent.lower()} '
            upgraded = sent
            ctype = 'vocabulary'
            why = 'Academic lexis/aniqlik oshirildi'
            if 'i think' in low:
                upgraded = re.sub(r'\bi think\b', 'In my view,', sent, flags=re.IGNORECASE)
                ctype, why = 'vocabulary', 'Stance formalroq — Lexical/Task yaxshilanadi'
            elif 'a lot of' in low:
                upgraded = re.sub(r'\ba lot of\b', 'a significant number of', sent, flags=re.IGNORECASE)
                ctype, why = 'vocabulary', 'Academic quantifier'
            elif 'very good' in low:
                upgraded = re.sub(r'\bvery good\b', 'highly beneficial', sent, flags=re.IGNORECASE)
                ctype, why = 'vocabulary', 'Preciser adjective'
            elif 'go up' in low or ' went up' in low:
                upgraded = re.sub(r'\bgo(?:es|ing)? up\b', 'increase', sent, flags=re.IGNORECASE)
                upgraded = re.sub(r'\bwent up\b', 'increased', upgraded, flags=re.IGNORECASE)
                ctype, why = 'vocabulary', 'Task 1 trend vocabulary'
            elif 'but ' in low and not any(x in low for x in ('however', 'nevertheless')):
                upgraded = re.sub(r'\bbut\b', 'however,', sent, count=1, flags=re.IGNORECASE)
                ctype, why = 'coherence', 'Formal contrast linker'
            elif 'shows' in low and meta['task_type'] == 'task1':
                upgraded = re.sub(r'\bshows\b', 'illustrates', sent, count=1, flags=re.IGNORECASE)
                ctype, why = 'vocabulary', 'Task 1 uchun kuchliroq verb'
            if upgraded != sent:
                _add(sent, upgraded, ctype, why)
            if len(corrections) >= limit:
                break

        if len(corrections) < 2 and sentences:
            _add(
                sentences[0][:180],
                (starters[0] if starters else sentences[0])[:220],
                'task',
                'Kirishni mavzuga aniqroq bog\'lang',
            )
        if len(corrections) < 3:
            _add(
                'Weak development',
                'This can be further explained by ... For instance, ...',
                'coherence',
                'Fikrni example bilan mustahkamlang',
            )

    # Deduplicate
    uniq = []
    seen = set()
    for item in corrections:
        key = f"{item['original'].lower()}=>{item['corrected'].lower()}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
        if len(uniq) >= limit:
            break
    return uniq


def _generate_issue_feedback(*, issue, meta, question, essay_text, word_count, eng_ratio):
    topic = _extract_topic_hint(question)
    quote = _pick_quote(essay_text) or '—'
    min_words = meta['min_words']
    task_label = meta['task_label']
    task1 = meta['task_type'] == 'task1'
    pack = _topic_starter_pack(question, meta)
    vocab = ', '.join((pack.get('useful_vocab') or [])[:6])
    keys = pack.get('focus_keys') or 'asosiy mavzu'
    rewrite = _rich_rewrite_template(meta, topic, pack)
    missing = max(min_words - word_count, 0)

    if issue in ('empty', 'greeting_only'):
        band = 3.0
        label = 'bo\'sh' if issue == 'empty' else 'tanishuv'
        summary = (
            f"Hozirgi matn IELTS {task_label} emas — {label} («{quote}»). "
            f"Examiner «{topic}» bo'yicha kamida {min_words} so'zlik academic essay kutadi. "
            f"Yaxshi yangilik: pastdagi ready-to-fill template bilan 15 daqiqada to'liq draft yozishingiz mumkin."
        )
        strengths = [
            "Maydonga biror matn kiritgansiz — bu birinchi qadam.",
            f"Endi {task_label} formatiga o'tsangiz, ball tez oshadi.",
        ]
        improvements = [
            f"«{quote}» o'rniga to'g'ridan-to'g'ri mavzuga yozing: {topic}",
            f"Kamida {min_words} so'z yozing (hozir {word_count}).",
            "4 paragraf: Introduction → Overview/Body1 → Body2 → Conclusion.",
            f"Akademik lug'atdan boshlang: {vocab}.",
            f"Kalit so'zlarga e'tibor: {keys}.",
        ]
        next_steps = [
            "2 daqiqa: savolni o'qing va 4 ta point outline yozing.",
            "5 daqiqa: Introduction + Overview/position yozing.",
            "8 daqiqa: 2 ta body paragraph (har birida misol).",
            f"Oxirida so'z sanang — {min_words}+ bo'lishi shart.",
            f"Starter gaplardan foydalaning: {pack['starter_sentences'][0]}",
        ]
    elif issue == 'nonsense':
        band = 3.0
        summary = (
            f"Yozilgan matn («{quote}») ma'noli IELTS essay emas — random/harf aralashmasiga o'xshaydi. "
            f"Lekin bu ham fix bo'ladi: «{topic}» uchun pastdagi template’ni to'ldirsangiz, to'liq draft chiqadi. "
            f"Maqsad: {min_words}+ so'z, aniq struktura."
        )
        strengths = [
            "Savolni ochib, biror narsa yozishga urinib ko'rgansiz.",
            "Endi template bilan 'bo'sh sahifadan qo'rquv'ni aylanib o'tishingiz mumkin.",
        ]
        improvements = [
            f"Random matn («{quote}») ni to'liq o'chirib, English academic gaplar yozing.",
            f"Mavzuga qayting: {topic}",
            f"Hajm: {word_count} → kamida {min_words} so'z (+{missing}).",
            f"Har paragrafda bitta aniq fikr + bog'lovchi so'z ({vocab}).",
            "Imlo/grammar: faqat tushunarli English gaplar ishlating.",
        ]
        next_steps = [
            "Outline (4 qator) yozing: intro / main1 / main2 / conclusion.",
            f"Birinchi gapni tayyor starter bilan boshlang: {pack['starter_sentences'][0]}",
            f"Overview/position: {pack['starter_sentences'][1] if len(pack['starter_sentences'])>1 else 'Overall/In my opinion...'}",
            "Timer: 15 daqiqada faqat template’ni to'ldiring — mukammallikni keyinga qoldiring.",
            f"Yozib bo'lgach tekshiring: so'z soni, paragraf, {keys}.",
        ]
    elif issue == 'prompt_echo':
        band = 3.5
        summary = (
            f"Siz savol jumlasini ko'chirib qo'ygansiz («{quote}»). "
            f"Examiner «{topic}» bo'yicha o'z tahlilingizni kutadi. "
            f"Hozir {word_count} so'z; kerak {min_words}+. Pastdagi template bilan darhol kengaytiring."
        )
        strengths = [
            "Savolni o'qigansiz va to'g'ri maydonga yozgansiz.",
            "Mavzu bilan tanishuv boshlangan — endi o'z so'zlaringiz kerak.",
        ]
        improvements = [
            "Savol matnini qayta ko'chirmang — paraphrasing qiling.",
            f"Overview/position qo'shing (hozir yo'q): {pack['starter_sentences'][1] if len(pack['starter_sentences'])>1 else 'Overall/In my opinion...'}",
            f"+{missing} so'z qo'shing — har bodyga 3-4 gap.",
            "2 ta aniq detail/example yozing (raqam, bosqich, yoki hayotiy misol).",
            f"Linking + data/academic til: {vocab}.",
        ]
        next_steps = [
            "1-gap paraphrase, 2-gap overview/position.",
            "Body1: eng muhim feature/argument.",
            "Body2: taqqoslash yoki ikkinchi argument + example.",
            f"Self-check: {min_words}+ so'z? overview/position bormi? conclusion bormi?",
            f"Fokus kalitlar: {keys}.",
        ]
    elif issue == 'wrong_language':
        band = 3.5 if word_count < 40 else 4.0
        summary = (
            f"Matnda English ulushi past ({int(eng_ratio * 100)}%). "
            f"IELTS Writing faqat Englishda baholanadi. Mavzu: «{topic}». "
            f"O'zbekcha g'oyani saqlab, pastdagi English template’ga o'tkazing."
        )
        strengths = [
            "Fikr/matn bor — mazmun yo'qolmasin, faqat tilni almashtiramiz.",
            f"Mavzu aniq: {topic[:80]}{'…' if len(topic)>80 else ''}.",
        ]
        improvements = [
            f"«{quote}» ni academic Englishga aylantiring.",
            f"Butun draftni {min_words}+ so'zda Englishda yozing.",
            f"Formal vocabulary ishlating: {vocab}.",
            "Har paragrafda linking word qo'ying (However, Therefore, For example).",
            "O'zbekcha so'zlarni English equivalentga almashtiring.",
        ]
        next_steps = [
            "Avval 4 punktli o'zbekcha outline yozing.",
            "Har punktni 2-3 English gapga aylantiring.",
            f"Starter: {pack['starter_sentences'][0]}",
            "5 ta complex sentence mashq: although / which / because.",
            f"Oxirida {min_words} so'zni tekshiring.",
        ]
    elif issue == 'too_short':
        band = 4.0 if word_count >= 20 else 3.5
        summary = (
            f"Yaxshi tomoni: mavzuga yaqin boshlangansiz («{quote}»). "
            f"Muammo: juda qisqa — {word_count}/{min_words} so'z. "
            f"«{topic}» ni to'liq yoritish uchun +{missing} so'z va 2 ta body detail kerak."
        )
        strengths = [
            f"Boshlang'ich fikr bor («{quote}»).",
            "To'g'ri yo'nalishdasiz — endi hajm va tuzilmani kuchaytiramiz.",
        ]
        improvements = [
            f"+{missing} so'z qo'shing (har fikrga 2-3 tushuntiruvchi gap).",
            "Har paragrafda bitta asosiy fikr + example/detail.",
            f"{'Overview va comparison' if task1 else 'Aniq pozitsiya va 2 argument'} qo'shing.",
            f"Academic phrases: {vocab}.",
            f"Kalit elementlar: {keys}.",
        ]
        next_steps = [
            f"Hozirgi matnni intro qilib qoldiring, keyin overview/position yozing.",
            "Body1 ni 4-5 gapga kengaytiring.",
            "Body2 + conclusion qo'shing.",
            f"So'z sanagich bilan {min_words}+ ga yetkazing.",
            f"Starterlar: {pack['starter_sentences'][1] if len(pack['starter_sentences'])>1 else 'Overall/In my opinion...'}",
        ]
    else:  # off_topic / other
        band = 4.0
        summary = (
            f"Javob {task_label} savoliga to'liq mos emas. "
            f"Kerak bo'lgan mavzu: «{topic}». Siz yozgansiz: «{quote}». "
            f"Qayta yozish uchun pastdagi template’ni to'ldiring — {min_words}+ so'z."
        )
        strengths = [
            "Yozish jarayonini boshlagansiz — bu muhim.",
            "Endi faqat focusni savolga qaytarish kerak.",
        ]
        improvements = [
            f"Mavzuga qayting: {topic}",
            "Savolning barcha qismlariga javob bering.",
            f"Kamida {min_words} so'z va aniq 4 paragraf yozing.",
            f"Kerakli til: {vocab}.",
            f"Diqqat markazi: {keys}.",
        ]
        next_steps = [
            "Savolni 3 qismga bo'ling: nima so'ralgan / javobingiz / misol.",
            "4 punktli outline yozib, keyin to'ldiring.",
            f"Birinchi gap: {pack['starter_sentences'][0]}",
            "Checklist: topic match → structure → examples → word count.",
            "15 daqiqalik timed rewrite qiling.",
        ]

    # Guarantee rich coaching even for weakest texts
    strengths = strengths[:5]
    improvements = improvements[:5]
    next_steps = next_steps[:5]

    criterion_values = {
        'task_achievement': _clamp_score(band - 0.5),
        'coherence_cohesion': _clamp_score(band - 0.5),
        'lexical_resource': _clamp_score(band - 0.5),
        'grammar_range_accuracy': _clamp_score(band - 0.5),
    }
    vocab = _build_vocabulary_upgrades(
        essay_text=essay_text, meta=meta, question=question, limit=6,
    )
    sentence_corrections = _build_sentence_corrections(
        essay_text=essay_text, meta=meta, question=question, issue=issue, limit=4,
    )
    return _finalize_local_feedback(
        meta, essay_text, word_count, band, summary,
        strengths=strengths,
        improvements=improvements,
        next_steps=next_steps,
        rewrite_suggestion=rewrite,
        criterion_values=criterion_values,
        vocabulary_upgrades=vocab,
        sentence_corrections=sentence_corrections,
        extra={
            'issue_type': issue,
            'english_ratio': round(eng_ratio, 2),
            'topic_hint': topic[:200],
            'starter_pack': pack,
        },
    )


def _enrich_feedback_payload(feedback, *, test, question, essay_text):
    """Ensure even weak AI outputs become rich mini-lessons."""
    meta = _task_meta(question)
    issue = _classify_essay_issue(essay_text, question, meta=meta)
    topic = _extract_topic_hint(question)
    pack = _topic_starter_pack(question, meta)
    quote = _pick_quote(essay_text) or '—'
    word_count = _word_count(essay_text)

    strengths = list(feedback.get('strengths') or [])
    improvements = list(feedback.get('improvements') or [])
    next_steps = list(feedback.get('next_steps') or [])

    if len(strengths) < 2:
        strengths.extend([
            "Yozishga urinish bor — bu o'rganishning birinchi belgisi.",
            f"Mavzu aniq: «{topic[:90]}». Endi struktura bilan to'ldiring.",
        ])
    if len(improvements) < 4:
        improvements.extend([
            f"«{quote}» o'rniga/ustiga mavzu bo'yicha batafsil gaplar yozing.",
            f"Kamida {meta['min_words']} so'zga yetkazing (hozir {word_count}).",
            "Introduction + 2 body + conclusion formatini ushlang.",
            f"Foydali iboralar: {', '.join((pack.get('useful_vocab') or [])[:5])}.",
        ])
    if len(next_steps) < 4:
        starters = pack.get('starter_sentences') or []
        next_steps.extend([
            "Avval 4 punktli outline yozing.",
            f"Starter bilan boshlang: {starters[0] if starters else 'The essay discusses...'}",
            "Har bodyga bitta misol qo'shing.",
            f"15 daqiqada rewrite qilib, {meta['min_words']}+ so'zga yetkazing.",
        ])

    vocab_upgrades = list(feedback.get('vocabulary_upgrades') or [])
    if len(vocab_upgrades) < 5:
        fallback_vocab = _build_vocabulary_upgrades(
            essay_text=essay_text, meta=meta, question=question, limit=6,
        )
        existing = {
            f"{(v.get('from') or '').lower()}=>{(v.get('to') or '').lower()}"
            for v in vocab_upgrades if isinstance(v, dict)
        }
        for item in fallback_vocab:
            key = f"{item['from'].lower()}=>{item['to'].lower()}"
            if key in existing:
                continue
            vocab_upgrades.append(item)
            existing.add(key)
            if len(vocab_upgrades) >= 6:
                break

    sentence_corrections = list(feedback.get('sentence_corrections') or [])
    if len(sentence_corrections) < 3:
        fallback_corr = _build_sentence_corrections(
            essay_text=essay_text, meta=meta, question=question, issue=issue, limit=4,
        )
        existing_c = {
            f"{(c.get('original') or '').lower()}=>{(c.get('corrected') or '').lower()}"
            for c in sentence_corrections if isinstance(c, dict)
        }
        for item in fallback_corr:
            key = f"{item['original'].lower()}=>{item['corrected'].lower()}"
            if key in existing_c:
                continue
            sentence_corrections.append(item)
            existing_c.add(key)
            if len(sentence_corrections) >= 4:
                break

    rewrite = (feedback.get('rewrite_suggestion') or '').strip()
    if len(rewrite) < 80 or issue != 'ok':
        template = _rich_rewrite_template(meta, topic, pack)
        if rewrite and rewrite not in template:
            rewrite = f"{rewrite}\n\nReady template:\n{template}"
        else:
            rewrite = template

    summary = (feedback.get('summary') or '').strip()
    if len(summary) < 80:
        summary = (
            f"{meta['task_label']} feedback: matn («{quote}») hali to'liq emas. "
            f"Mavzu — «{topic}». Pastdagi template va next steps bilan qayta yozing."
        )

    feedback['summary'] = summary[:2000]
    feedback['strengths'] = strengths[:5]
    feedback['improvements'] = improvements[:5]
    feedback['next_steps'] = next_steps[:5]
    feedback['vocabulary_upgrades'] = vocab_upgrades[:8]
    feedback['sentence_corrections'] = sentence_corrections[:6]

    from core.services.writing_error_detection import merge_writing_errors

    feedback['writing_errors'] = merge_writing_errors(
        essay_text,
        ai_errors=feedback.get('writing_errors'),
        sentence_corrections=sentence_corrections,
        vocabulary_upgrades=vocab_upgrades,
        heuristic_limit=15,
        total_limit=16,
    )
    feedback['rewrite_suggestion'] = rewrite[:4000]
    raw = feedback.get('raw_response_json')
    if isinstance(raw, dict):
        raw['enriched'] = True
        raw['issue_type'] = issue
        feedback['raw_response_json'] = raw
    return feedback


def _generate_local_feedback(*, test, question, essay_text):
    meta = _task_meta(question)
    task1 = meta['task_type'] == 'task1'
    min_words = meta['min_words']
    target_words = meta['target_words']

    word_count = _word_count(essay_text)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', essay_text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in re.split(r'\n+', essay_text) if p.strip()]
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', essay_text) if s.strip()]
    unique_words = {w.lower() for w in re.findall(r"[A-Za-z']+", essay_text)}
    eng_ratio = _english_ratio(essay_text)
    topic = _extract_topic_hint(question)
    quote = _pick_quote(essay_text)
    issue = _classify_essay_issue(essay_text, question, meta=meta)

    if issue != 'ok':
        return _generate_issue_feedback(
            issue=issue,
            meta=meta,
            question=question,
            essay_text=essay_text,
            word_count=word_count,
            eng_ratio=eng_ratio,
        )

    linker_list = [
        'however', 'therefore', 'moreover', 'furthermore', 'for example',
        'in addition', 'on the other hand', 'in conclusion', 'firstly', 'secondly',
        'finally', 'while', 'whereas', 'although', 'because', 'overall',
    ]
    linking_words = _count_matches(essay_text, linker_list)
    task1_signals = _count_matches(essay_text, [
        'overall', 'in general', 'the chart', 'the graph', 'the diagram', 'the table',
        'increase', 'decrease', 'rose', 'fell', 'peak', 'respectively', 'compared to',
        'approximately', 'significant',
    ])
    task2_signals = _count_matches(essay_text, [
        'in my opinion', 'i believe', 'i think', 'agree', 'disagree', 'on the one hand',
        'on the other hand', 'for instance', 'this is because', 'to conclude',
    ])
    repeated = _top_repeated_words(essay_text)

    strengths = []
    improvements = []
    next_steps = []
    scores = {
        'task': 5.0,
        'coherence': 5.0,
        'lexical': 5.0,
        'grammar': 5.0,
    }

    if word_count >= target_words:
        scores['task'] += 1.0
        strengths.append(f"So'zlar soni yaxshi ({word_count}) — {meta['task_label']} hajmiga yaqin.")
    elif word_count >= min_words:
        scores['task'] += 0.5
        strengths.append(f"Minimal {min_words}+ so'z bajarilgan ({word_count}).")
        improvements.append(f"Band oshishi uchun ~{target_words} so'zgacha kengaytiring (har fikrga +1-2 gap).")
        next_steps.append("Har body oxiriga for example / for instance bilan misol qo'shing.")
    else:
        scores['task'] -= 1.0
        improvements.append(
            f"So'z yetarli emas: {word_count}/{min_words}. Bu Task Achievementni pasaytiradi "
            f"(siz: «{quote}»)."
        )
        next_steps.append(f"Yana ~{min_words - word_count} so'z qo'shing — har paragrafga 2-3 gap.")

    if len(paragraphs) >= 4:
        scores['coherence'] += 1.0
        strengths.append("Paragraf tuzilmasi aniq (kirish/body/xulosa ajralgan).")
    elif len(paragraphs) >= 3:
        scores['coherence'] += 0.5
        strengths.append("Asosiy paragraflar mavjud.")
        next_steps.append("Agar conclusion qisqa bo'lsa, 2 gap bilan mustahkamlang.")
    else:
        scores['coherence'] -= 0.5
        improvements.append("Matn deyarli bir blok — paragraflar bo'linmagan.")
        next_steps.append("Har yangi fikrni yangi paragrafda boshlang (Enter → Enter).")

    if linking_words >= 4:
        scores['coherence'] += 0.5
        strengths.append("Linking words oqimni yaxshilaydi.")
    elif linking_words >= 1:
        improvements.append("Linking words kam — gaplar orasidagi mantiq zaifroq.")
        next_steps.append("However / Moreover / For example / In conclusion dan 3-4 tasini joylang.")
    else:
        scores['coherence'] -= 0.5
        improvements.append("Linking word deyarli yo'q — o'qish oqimi uziladi.")
        next_steps.append("Har paragraf boshiga bitta linker qo'ying.")

    if len(unique_words) >= 120:
        scores['lexical'] += 1.0
        strengths.append("Lug'at xilma-xilligi yaxshi.")
    elif len(unique_words) >= 70:
        scores['lexical'] += 0.5
    else:
        scores['lexical'] -= 0.5
        if repeated:
            improvements.append(
                f"Lug'at cheklangan — «{repeated[0]}» kabi so'zlar ko'p takrorlanadi."
            )
        else:
            improvements.append("Lug'at cheklangan — bir xil so'zlar takrorlanadi.")
        next_steps.append(f"«{topic[:60]}» bo'yicha 8-10 academic synonym yozib ishlating.")

    avg_sent_len = (word_count / max(len(sentences), 1))
    if len(sentences) >= 12 and 12 <= avg_sent_len <= 22:
        scores['grammar'] += 0.5
        strengths.append("Gaplar soni va uzunligi muvozanatli.")
    elif len(sentences) < 6 or avg_sent_len < 8:
        scores['grammar'] -= 0.5
        improvements.append("Gaplar juda qisqa/kam — complex sentence (although/which/because) kam.")
        next_steps.append("Har kunda 5 ta complex sentence mashq qiling.")

    if task1:
        if task1_signals >= 3:
            scores['task'] += 0.5
            strengths.append("Task 1 tiliga urinish bor (overview/trend/comparison).")
        else:
            improvements.append(
                f"Task 1 da overview va comparison yetishmayapti (mavzu: {topic[:80]})."
            )
            next_steps.append("1-gap Overall... keyin 2 body: asosiy feature + taqqoslash.")
        rewrite = (
            f"Intro: visual nima ko'rsatadi («{topic[:70]}»). "
            "Overview: eng muhim xususiyat. Body1: asosiy o'zgarish. "
            "Body2: taqqoslash. Shaxsiy fikr yozmang."
        )
    else:
        if task2_signals >= 2:
            scores['task'] += 0.5
            strengths.append("Pozitsiya / fikr ifodalangan.")
        else:
            improvements.append("Task 2 da aniq pozitsiya (agree/opinion) ko'rinmayapti.")
            next_steps.append("Introduction oxirida: In my opinion / I believe that... deb yozing.")
        if 'for example' not in essay_text.lower() and 'for instance' not in essay_text.lower():
            improvements.append(f"Misollar kam — «{quote}» dan keyin aniq example qo'shing.")
        rewrite = (
            f"Intro: «{topic[:70]}» + aniq pozitsiya. "
            "Body1: argument + example. Body2: argument + example. "
            "Conclusion: pozitsiyani qisqa tasdiqlang."
        )

    criterion_values = {
        'task_achievement': _clamp_score(scores['task']),
        'coherence_cohesion': _clamp_score(scores['coherence']),
        'lexical_resource': _clamp_score(scores['lexical']),
        'grammar_range_accuracy': _clamp_score(scores['grammar']),
    }
    estimated_band = round(sum(criterion_values.values()) / 4 * 2) / 2

    weakest_key = min(criterion_values, key=criterion_values.get)
    weakest_labels = {
        'task_achievement': 'Task Achievement',
        'coherence_cohesion': 'Coherence & Cohesion',
        'lexical_resource': 'Lexical Resource',
        'grammar_range_accuracy': 'Grammar',
    }
    summary = (
        f"{meta['task_label']}: taxminiy {estimated_band} band. "
        f"Mavzu — {topic[:90]}{'…' if len(topic) > 90 else ''}. "
        f"Siz: «{quote}». Eng zaif tomon: {weakest_labels[weakest_key]} "
        f"({criterion_values[weakest_key]}). Focus shu yerda."
    )

    if not strengths:
        strengths.append(f"Essay topshirildi («{quote}») — structure va misollarni kuchaytiring.")
    if not improvements:
        improvements.append("Umumiy tuzilma yaxshi — accuracy va academic vocabulary ustida ishlang.")
    if not next_steps:
        next_steps.append("Keyingi essay: 40 daqiqa yozish + 5 daqiqa self-check checklist.")

    vocab_upgrades = _build_vocabulary_upgrades(
        essay_text=essay_text, meta=meta, question=question, limit=6,
    )
    sentence_corrections = _build_sentence_corrections(
        essay_text=essay_text, meta=meta, question=question, issue='ok', limit=4,
    )
    if repeated:
        improvements = list(improvements)
        improvements.append(
            f"«{repeated[0]}» ko'p takrorlanadi — synonym/academic alternative ishlating (Lexical Resource)."
        )

    return _finalize_local_feedback(
        meta, essay_text, word_count, estimated_band, summary,
        strengths=strengths[:4],
        improvements=improvements[:5],
        next_steps=next_steps[:4],
        rewrite_suggestion=rewrite,
        criterion_values=criterion_values,
        vocabulary_upgrades=vocab_upgrades,
        sentence_corrections=sentence_corrections,
        extra={
            'issue_type': 'ok',
            'english_ratio': round(eng_ratio, 2),
            'linking_words': linking_words,
            'topic_hint': topic[:200],
            'repeated_words': repeated[:5],
        },
    )


def _top_repeated_words(text, limit=3):
    stop = {
        'the', 'and', 'that', 'this', 'with', 'from', 'have', 'has', 'had', 'were', 'was',
        'are', 'for', 'they', 'their', 'them', 'there', 'which', 'while', 'when', 'what',
        'about', 'into', 'also', 'than', 'then', 'some', 'more', 'most', 'only', 'over',
        'such', 'can', 'will', 'would', 'could', 'should', 'been', 'being', 'people',
    }
    counts = {}
    for word in re.findall(r"[A-Za-z']{4,}", (text or '').lower()):
        if word in stop:
            continue
        counts[word] = counts.get(word, 0) + 1
    ranked = sorted(((w, c) for w, c in counts.items() if c >= 3), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in ranked[:limit]]


def _finalize_local_feedback(
    meta, essay_text, word_count, estimated_band, summary,
    *, strengths, improvements, next_steps, rewrite_suggestion,
    criterion_values=None, vocabulary_upgrades=None, sentence_corrections=None, extra=None,
):
    criterion_values = criterion_values or {}
    return normalize_feedback_payload({
        'summary': summary,
        'estimated_band': estimated_band,
        'task_achievement': criterion_values.get('task_achievement', max(4.0, estimated_band - 0.5)),
        'coherence_cohesion': criterion_values.get('coherence_cohesion', estimated_band),
        'lexical_resource': criterion_values.get('lexical_resource', estimated_band),
        'grammar_range_accuracy': criterion_values.get('grammar_range_accuracy', estimated_band),
        'strengths': strengths,
        'improvements': improvements,
        'next_steps': next_steps,
        'vocabulary_upgrades': vocabulary_upgrades or [],
        'sentence_corrections': sentence_corrections or [],
        'rewrite_suggestion': rewrite_suggestion,
        'raw_response_json': {
            'provider': 'local',
            'engine_version': FEEDBACK_ENGINE_VERSION,
            'task_label': meta['task_label'],
            'word_count': word_count,
            **(extra or {}),
        },
    })


def _clamp_score(value):
    return round(max(3.0, min(8.5, float(value))) * 2) / 2


def _word_count(text):
    return len(re.findall(r"\b[\w']+\b", text or ''))


def _count_matches(text, needles):
    lowered = f" {(text or '').lower()} "
    count = 0
    for needle in needles:
        if needle in lowered:
            count += 1
    return count
