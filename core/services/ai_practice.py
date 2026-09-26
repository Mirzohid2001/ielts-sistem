"""AI Reading/Writing mashq (practice) generator — daraja + tur bo'yicha."""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings

from core.services.ai_language import learner_language_rules, normalize_ai_lang, t
from core.services.passage_expansions import MIN_PASSAGE_WORDS, ensure_min_words, word_count as passage_word_count

# Gunicorn default timeout ~30s — Gemini shu ichida tugamasa 502.
PRACTICE_GEMINI_BUDGET_SEC = 14.0
PRACTICE_GEMINI_CALL_TIMEOUT = 12.0
PRACTICE_GEMINI_MAX_MODELS = 1

LEVELS = ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')
READING_VARIANT_COUNT = 2
READING_QUESTION_COUNT = 10
WRITING_EXERCISE_COUNT = 4

_ROMAN_LETTERS = (
    'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
)
_ALPHA_LETTERS = tuple('abcdefgh')

READING_TYPES = {
    'tfng': {
        'label_uz': 'True / False / Not Given',
        'label_ru': 'True / False / Not Given',
        'qtype': 'true_false_not_given',
    },
    'mcq': {
        'label_uz': 'Multiple Choice',
        'label_ru': 'Multiple Choice',
        'qtype': 'mcq',
    },
    'gap_fill': {
        'label_uz': 'Gap Filling',
        'label_ru': 'Gap Filling',
        'qtype': 'fill_blank',
    },
    'matching_headings': {
        'label_uz': 'Heading Matching',
        'label_ru': 'Heading Matching',
        'qtype': 'matching_headings',
    },
    'matching_endings': {
        'label_uz': 'Matching Endings',
        'label_ru': 'Matching Endings',
        'qtype': 'matching_sentences',
    },
    'matching_names': {
        'label_uz': 'Matching Names',
        'label_ru': 'Matching Names',
        'qtype': 'matching_features',
    },
}

WRITING_FOCUSES = {
    'lexical_resource': {
        'label_uz': 'Lexical Resource',
        'label_ru': 'Lexical Resource',
    },
    'grammar': {
        'label_uz': 'Grammar',
        'label_ru': 'Grammar',
    },
    'paraphrasing': {
        'label_uz': 'Paraphrasing',
        'label_ru': 'Paraphrasing',
    },
    'sentence_construction': {
        'label_uz': 'Sentence Construction',
        'label_ru': 'Sentence Construction',
    },
    'support_sentences': {
        'label_uz': 'Support Sentences',
        'label_ru': 'Support Sentences',
    },
    'argument_development': {
        'label_uz': 'Argument Development',
        'label_ru': 'Argument Development',
    },
}

GEMINI_MODEL_FALLBACKS = (
    'gemini-2.5-flash',
    'gemini-flash-lite-latest',
    'gemini-2.0-flash-lite',
    'gemini-2.0-flash',
)


def normalize_level(value) -> str:
    raw = (value or 'B1').strip().upper()
    return raw if raw in LEVELS else 'B1'


def normalize_reading_type(value) -> str:
    raw = (value or 'tfng').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'true_false_not_given': 'tfng',
        'true_false': 'tfng',
        'multiple_choice': 'mcq',
        'gap': 'gap_fill',
        'gapfilling': 'gap_fill',
        'fill_blank': 'gap_fill',
        'heading_matching': 'matching_headings',
        'headings': 'matching_headings',
        'matching_sentences': 'matching_endings',
        'sentence_endings': 'matching_endings',
        'matching_ending': 'matching_endings',
        'endings': 'matching_endings',
        'matching_features': 'matching_names',
        'matching_name': 'matching_names',
        'names': 'matching_names',
        'people': 'matching_names',
    }
    raw = aliases.get(raw, raw)
    return raw if raw in READING_TYPES else 'tfng'


def normalize_writing_focus(value) -> str:
    raw = (value or 'lexical_resource').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'lr': 'lexical_resource',
        'vocab': 'lexical_resource',
        'vocabulary': 'lexical_resource',
        'gra': 'grammar',
        'paraphrase': 'paraphrasing',
        'sentences': 'sentence_construction',
        'support': 'support_sentences',
        'argument': 'argument_development',
    }
    raw = aliases.get(raw, raw)
    return raw if raw in WRITING_FOCUSES else 'lexical_resource'


def _gemini_model_chain(preferred=''):
    model = (preferred or os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')).strip()
    if model.startswith('models/'):
        model = model.split('/', 1)[1]
    chain = []
    if model:
        chain.append(model)
    for m in GEMINI_MODEL_FALLBACKS:
        if m not in chain:
            chain.append(m)
    return chain


def _call_gemini_json(prompt: str, *, model: str, timeout: float = 70) -> dict:
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
            'temperature': 0.55,
            'topP': 0.92,
            'maxOutputTokens': 4096,
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
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise ValueError(f'Gemini HTTP {exc.code}: {detail[:300]}') from exc
    except urllib_error.URLError as exc:
        raise ValueError(f'Gemini aloqa: {exc.reason}') from exc
    except TimeoutError as exc:
        raise ValueError(f'Gemini timeout ({timeout}s)') from exc
    try:
        parts = raw['candidates'][0]['content']['parts']
        content = ''.join(str(p.get('text', '') or '') for p in parts if isinstance(p, dict)).strip()
        # strip markdown fences if any
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Gemini response format noto‘g‘ri') from exc
    if not isinstance(parsed, dict):
        raise ValueError('Gemini JSON object emas')
    parsed['_raw_meta'] = {'model': model}
    return parsed


def _provider() -> str:
    return getattr(
        settings,
        'AI_WRITING_FEEDBACK_PROVIDER',
        os.environ.get('AI_WRITING_FEEDBACK_PROVIDER', 'local'),
    ).strip().lower()


def _model_name() -> str:
    return getattr(
        settings,
        'AI_WRITING_FEEDBACK_MODEL',
        os.environ.get('AI_WRITING_FEEDBACK_MODEL', 'gemini-2.5-flash'),
    ).strip()


# ── Local fallbacks ──────────────────────────────────────────────


def _tfng_options():
    return [
        {'letter': 'a', 'text': 'TRUE'},
        {'letter': 'b', 'text': 'FALSE'},
        {'letter': 'c', 'text': 'NOT GIVEN'},
    ]


def _mcq(prompt, options, correct, explanation):
    letters = 'abcd'
    opts = [{'letter': letters[i], 'text': text} for i, text in enumerate(options[:4])]
    return {'id': 0, 'prompt': prompt, 'options': opts, 'correct': correct, 'explanation': explanation}


def _gap(prompt, correct, explanation):
    return {'id': 0, 'prompt': prompt, 'options': [], 'correct': correct, 'explanation': explanation}


def _heading(prompt, options, correct, explanation):
    romans = ('i', 'ii', 'iii', 'iv', 'v', 'vi')
    opts = [{'letter': romans[i], 'text': text} for i, text in enumerate(options[:6])]
    return {'id': 0, 'prompt': prompt, 'options': opts, 'correct': correct, 'explanation': explanation}


def _match(prompt, options, correct, explanation):
    """Matching endings / names — A–H harfli variantlar."""
    letters = 'abcdefgh'
    opts = [{'letter': letters[i], 'text': text} for i, text in enumerate(options[:8])]
    return {
        'id': 0,
        'prompt': prompt,
        'options': opts,
        'correct': str(correct).strip().lower()[:1],
        'explanation': explanation,
    }


def _number_questions(rows):
    out = []
    for i, row in enumerate(rows[:READING_QUESTION_COUNT], start=1):
        item = dict(row)
        item['id'] = i
        out.append(item)
    return out


def _practice_rng(seed: str | None = None) -> random.Random:
    raw = str(seed or '').strip() or f'{time.time_ns()}'
    digest = hashlib.sha256(raw.encode('utf-8', errors='ignore')).hexdigest()
    return random.Random(int(digest[:16], 16))


def _practice_fingerprint(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ''
    title = str(payload.get('title') or payload.get('task') or '').strip().lower()
    body = str(payload.get('passage') or payload.get('sample_essay') or '').strip().lower()[:180]
    ptype = str(payload.get('practice_type') or '').strip().lower()
    level = str(payload.get('level') or '').strip().upper()
    return f'{level}|{ptype}|{title}|{body}'


def _variant_index(seed: str, *, level: str, practice_type: str, n: int = READING_VARIANT_COUNT) -> int:
    n = max(1, int(n or 1))
    digest = hashlib.md5(f'{seed}|{level}|{practice_type}'.encode('utf-8', errors='ignore')).hexdigest()
    return int(digest[:8], 16) % n


def _shuffle_choice_options(row: dict, rng: random.Random) -> dict:
    """Variantlarni aralashtirib, correct harfini yangilaydi."""
    item = dict(row)
    opts = [dict(o) for o in (item.get('options') or []) if isinstance(o, dict) and o.get('text')]
    if len(opts) < 2:
        return item
    texts = {str(o.get('text') or '').strip().upper() for o in opts}
    if texts == {'TRUE', 'FALSE', 'NOT GIVEN'}:
        return item
    correct_raw = str(item.get('correct') or '').strip().lower()
    correct_text = ''
    for o in opts:
        letter = str(o.get('letter') or '').strip().lower()
        if letter and letter == correct_raw:
            correct_text = str(o.get('text') or '')
            break
    if not correct_text:
        return item
    use_roman = all(
        str(o.get('letter') or '').strip().lower() in _ROMAN_LETTERS
        for o in opts
    )
    rng.shuffle(opts)
    letters = list(_ROMAN_LETTERS[:len(opts)]) if use_roman else list(_ALPHA_LETTERS[:len(opts)])
    new_opts = []
    new_correct = correct_raw
    for i, o in enumerate(opts):
        letter = letters[i] if i < len(letters) else _ALPHA_LETTERS[i % len(_ALPHA_LETTERS)]
        text = str(o.get('text') or '')
        new_opts.append({'letter': letter, 'text': text})
        if text == correct_text:
            new_correct = letter
    item['options'] = new_opts
    item['correct'] = new_correct
    return item


def _freshen_reading_payload(payload: dict, seed: str) -> dict:
    out = dict(payload or {})
    rng = _practice_rng(seed)
    rows = [dict(q) for q in (out.get('questions') or []) if isinstance(q, dict)]
    if not rows:
        return out
    rng.shuffle(rows)
    fresh = []
    for i, row in enumerate(rows, start=1):
        item = _shuffle_choice_options(row, rng)
        item['id'] = i
        fresh.append(item)
    out['questions'] = fresh
    out['freshness_seed'] = str(seed)[:48]
    return out


def _freshen_writing_payload(payload: dict, seed: str) -> dict:
    out = dict(payload or {})
    rng = _practice_rng(seed)
    rows = [dict(e) for e in (out.get('exercises') or []) if isinstance(e, dict)]
    if not rows:
        return out
    rng.shuffle(rows)
    fresh = []
    for i, row in enumerate(rows, start=1):
        item = _shuffle_choice_options(row, rng) if row.get('options') else dict(row)
        item['id'] = i
        fresh.append(item)
    out['exercises'] = fresh
    out['freshness_seed'] = str(seed)[:48]
    return out


def _high_level_reading_pack(level: str, rtype: str, tip: str) -> dict:
    """B2/C1/C2: savollar shu daraja matniga mos (park savollari aralashmasin)."""
    if level == 'B2':
        title = 'The Atlantic Telegraph Cable'
        passage = None  # default passages['B2']
        names_title = 'Engineers of the Atlantic Cable'
        names_passage = (
            "Cyrus Field raised money for a new Atlantic cable company after early failures. "
            "Engineer Charles Bright supervised laying work from the ships. "
            "William Thomson advised on electrical signalling through the long copper core. "
            "Captain James Anderson commanded the Great Eastern on a later successful voyage. "
            "Investor John Pender backed stronger cable designs after breaks at sea. "
            "Reporter Emily Shaw wrote that messages crossed in minutes instead of weeks."
        )
        names = [
            'Cyrus Field', 'Charles Bright', 'William Thomson',
            'James Anderson', 'John Pender', 'Emily Shaw',
        ]
        if rtype == 'tfng':
            raw = [
                {'prompt': 'Early Atlantic cable attempts sometimes failed when the cable broke.', 'correct': 'a'},
                {'prompt': 'The cable core was made of iron only, with no copper.', 'correct': 'b'},
                {'prompt': 'Gutta-percha covered the central wires.', 'correct': 'a'},
                {'prompt': 'Two ships had to share the heavy cable.', 'correct': 'a'},
                {'prompt': 'The project made ocean mapping less important.', 'correct': 'b'},
                {'prompt': 'Cyrus Field formed another company to raise money.', 'correct': 'a'},
                {'prompt': 'Messages could travel in minutes instead of weeks by ship.', 'correct': 'a'},
                {'prompt': 'The cable had no effect on diplomacy or news.', 'correct': 'b'},
                {'prompt': 'Every voyage was ignored by investors.', 'correct': 'b'},
                {'prompt': 'The passage states the exact cost in today’s dollars.', 'correct': 'c'},
            ]
            return {'tfng_raw': raw}
        if rtype == 'mcq':
            return {'questions': [
                _mcq('What covered the copper wires?', ['Gutta-percha', 'Plastic paint', 'Only cloth', 'Dry sand'], 'a', tip),
                _mcq('Why was the cable shared between two ships?', ['Because of its weight', 'Because captains refused', 'Because copper was illegal', 'Because the ocean was shallow'], 'a', tip),
                _mcq('What happened in early attempts?', ['The cable broke', 'Ships never sailed', 'Copper vanished', 'News became slower'], 'a', tip),
                _mcq('Who formed another company to raise money?', ['Cyrus Field', 'A random sailor', 'Only newspaper editors', 'Airport builders'], 'a', tip),
                _mcq('How fast could messages travel after success?', ['In minutes', 'In decades', 'Only by horse', 'Never'], 'a', tip),
                _mcq('What else did the project push forward?', ['Ocean mapping and stronger ships', 'Closing all ports', 'Banning copper', 'Ending newspapers'], 'a', tip),
                _mcq('What material was in the central wires?', ['Copper', 'Glass only', 'Wood', 'Stone'], 'a', tip),
                _mcq('What changed between Europe and America?', ['Business, news, and diplomacy', 'Only fashion styles', 'Airport design', 'Park lighting'], 'a', tip),
                _mcq('How did investors behave?', ['They watched every voyage closely', 'They ignored the ships', 'They banned cables', 'They closed newspapers'], 'a', tip),
                _mcq('What was true of the successful cable?', ['It was expensive but transformative', 'It was free and unused', 'It only carried music', 'It never worked'], 'a', tip),
            ]}
        if rtype == 'gap_fill':
            return {'questions': [
                _gap('The central wires were made of ______.', 'copper', tip),
                _gap('The wires were covered with ______.', 'gutta-percha|gutta percha', tip),
                _gap('Because of its weight, the cable had to be shared between two ______.', 'ships', tip),
                _gap('Early attempts failed when the cable ______.', 'broke', tip),
                _gap('Cyrus Field formed another ______ to raise money.', 'company', tip),
                _gap('Operators could send messages in ______ instead of weeks.', 'minutes', tip),
                _gap('Investors watched every ______ closely.', 'voyage', tip),
                _gap('The project pushed better ocean ______.', 'mapping', tip),
                _gap('Stronger ______ were also needed.', 'ships', tip),
                _gap('The cable changed business, news, and ______.', 'diplomacy', tip),
            ]}
        if rtype == 'matching_headings':
            return {'questions': [
                _heading('Cable construction materials', ['Copper and gutta-percha', 'Airport runways', 'City parks'], 'i', tip),
                _heading('Why two ships were needed', ['The cable’s weight', 'Lack of captains', 'Shallow rivers only'], 'i', tip),
                _heading('Early failures at sea', ['Breaks during laying', 'Instant success', 'No ships available'], 'i', tip),
                _heading('Raising money again', ['Cyrus Field’s new company', 'Closing newspapers', 'Banning copper'], 'i', tip),
                _heading('Speed of communication', ['Minutes instead of weeks', 'Slower than ships', 'Only smoke signals'], 'i', tip),
                _heading('Wider technical gains', ['Ocean mapping and stronger ships', 'Park lighting', 'Library Wi-Fi'], 'i', tip),
                _heading('Investor attention', ['Every voyage watched closely', 'No interest at all', 'Only fashion news'], 'i', tip),
                _heading('Cost versus impact', ['Expensive but transformative', 'Free and useless', 'Only local gossip'], 'i', tip),
                _heading('What the cable changed', ['Business, news, diplomacy', 'Only sports scores', 'Tree planting'], 'i', tip),
                _heading('Mid-nineteenth century goal', ['Atlantic telegraph link', 'Building stadiums', 'Closing ports'], 'i', tip),
            ]}
        if rtype == 'matching_endings':
            endings = [
                'copper covered with gutta-percha.',
                'shared between two ships.',
                'when the cable broke.',
                'raise money for a new attempt.',
                'minutes instead of weeks.',
                'business, news, and diplomacy.',
            ]
            return {'questions': [
                _match('The central wires were', endings, 'a', tip),
                _match('Because of its weight, the cable had to be', endings, 'b', tip),
                _match('Early attempts failed', endings, 'c', tip),
                _match('Cyrus Field formed another company to', endings, 'd', tip),
                _match('Operators could send messages in', endings, 'e', tip),
                _match('Although expensive, the cable changed', endings, 'f', tip),
                _match('Further research improved', ['thickness and strength.', 'park lighting.', 'library clubs.'], 'a', tip),
                _match('Investors watched', ['every voyage closely.', 'only fashion shows.', 'tree planting.'], 'a', tip),
                _match('The project also pushed', ['better ocean mapping.', 'closing newspapers.', 'banning ships.'], 'a', tip),
                _match('Messages no longer needed', ['weeks by ship.', 'copper wires.', 'any ships.'], 'a', tip),
            ]}
        if rtype == 'matching_names':
            return {
                'title': names_title,
                'passage': names_passage,
                'questions': [
                    _match('Raised money for a new cable company', names, 'a', tip),
                    _match('Supervised laying work from the ships', names, 'b', tip),
                    _match('Advised on electrical signalling', names, 'c', tip),
                    _match('Commanded the Great Eastern', names, 'd', tip),
                    _match('Backed stronger cable designs', names, 'e', tip),
                    _match('Wrote that messages crossed in minutes', names, 'f', tip),
                    _match('Organised funding after early failures', names, 'a', tip),
                    _match('Led shipboard cable operations', names, 'b', tip),
                    _match('Focused on the copper core’s signals', names, 'c', tip),
                    _match('Reported the new communication speed', names, 'f', tip),
                ],
            }
    if level == 'C1':
        names_title = 'Researchers on Bilingualism'
        names_passage = (
            "Dr Lena Ortiz studies attentional control in bilingual adults. "
            "Professor Mark Ellis argues effect sizes shrink after SES controls. "
            "Psychologist Aisha Rahman links benefits to frequent language switching. "
            "Educator Tomoko Abe reports gains in metalinguistic awareness in class. "
            "Policy analyst Hugo Mendes warns against overselling a cognitive cure. "
            "Statistician Nora Klein calls for more longitudinal designs."
        )
        names = [
            'Dr Lena Ortiz', 'Professor Mark Ellis', 'Aisha Rahman',
            'Tomoko Abe', 'Hugo Mendes', 'Nora Klein',
        ]
        if rtype == 'tfng':
            return {'tfng_raw': [
                {'prompt': 'Some evidence links bilingualism to executive functions such as attentional control.', 'correct': 'a'},
                {'prompt': 'All large-scale studies show huge advantages with no debate.', 'correct': 'b'},
                {'prompt': 'Socioeconomic status and education are mentioned as control factors.', 'correct': 'a'},
                {'prompt': 'Researchers agree completely on why benefits appear.', 'correct': 'b'},
                {'prompt': 'Language switching is one proposed source of benefits.', 'correct': 'a'},
                {'prompt': 'Longitudinal designs are still rare.', 'correct': 'a'},
                {'prompt': 'Lab tasks always mirror everyday communication perfectly.', 'correct': 'b'},
                {'prompt': 'Teachers report practical gains in metalinguistic awareness.', 'correct': 'a'},
                {'prompt': 'Policy makers are told to treat bilingualism as a universal cognitive cure.', 'correct': 'b'},
                {'prompt': 'The passage gives the exact percentage of bilingual advantage worldwide.', 'correct': 'c'},
            ]}
        if rtype == 'mcq':
            return {'questions': [
                _mcq('Which executive functions are mentioned?', ['Attentional control and flexibility', 'Only handwriting speed', 'Airport design skills', 'Park maintenance'], 'a', tip),
                _mcq('What may shrink reported advantages?', ['Controls for SES and education', 'More copper cables', 'Closing schools', 'Banning reading'], 'a', tip),
                _mcq('What do researchers debate?', ['Switching vs lifestyle factors', 'Only cable thickness', 'Park ticket prices', 'Ocean depth'], 'a', tip),
                _mcq('What designs are still rare?', ['Longitudinal designs', 'One-day quizzes only', 'Ship voyages', 'Picnic plans'], 'a', tip),
                _mcq('What may lab tasks fail to mirror?', ['Everyday communication', 'Copper wiring', 'Ocean maps', 'Stadium lights'], 'a', tip),
                _mcq('What do teachers report?', ['Metalinguistic awareness gains', 'Free cars for students', 'Ended bilingualism', 'Closed libraries'], 'a', tip),
                _mcq('What should policy makers avoid?', ['Overselling a universal cognitive cure', 'Supporting language learning', 'Cultural reasons', 'Economic reasons'], 'a', tip),
                _mcq('Why still support early language learning?', ['Cultural and economic reasons', 'Only to raise park prices', 'To ban switching', 'To end schools'], 'a', tip),
                _mcq('What remains contested?', ['The size of the effects', 'Whether copper exists', 'Whether ships float', 'Whether parks have trees'], 'a', tip),
                _mcq('What is bilingualism linked to in the opening?', ['Certain executive functions', 'Building cables', 'Climate models only', 'Picnic food'], 'a', tip),
            ]}
        if rtype == 'gap_fill':
            return {'questions': [
                _gap('Bilingualism may enhance certain ______ functions.', 'executive', tip),
                _gap('One mentioned function is attentional ______.', 'control', tip),
                _gap('Effect sizes may look modest after controlling for socioeconomic ______.', 'status', tip),
                _gap('Another control factor mentioned is ______.', 'education', tip),
                _gap('Benefits may arise from frequent language ______.', 'switching', tip),
                _gap('______ designs are still rare.', 'Longitudinal|longitudinal', tip),
                _gap('Lab tasks may not mirror everyday ______.', 'communication', tip),
                _gap('Teachers report gains in metalinguistic ______.', 'awareness', tip),
                _gap('Policy makers should avoid ______ bilingualism as a universal cure.', 'overselling', tip),
                _gap('Early language learning still has cultural and ______ reasons.', 'economic', tip),
            ]}
        if rtype == 'matching_headings':
            return {'questions': [
                _heading('Possible cognitive gains', ['Executive functions', 'Ocean cables', 'Park benches'], 'i', tip),
                _heading('Modest effects after controls', ['SES and education', 'Ship weight', 'Picnic menus'], 'i', tip),
                _heading('Competing explanations', ['Switching vs lifestyle', 'Only copper quality', 'Only weather'], 'i', tip),
                _heading('Research design limits', ['Rare longitudinal studies', 'Too many oceans', 'No teachers'], 'i', tip),
                _heading('Lab versus real life', ['Tasks may not mirror communication', 'Ships never sail', 'Parks never open'], 'i', tip),
                _heading('Classroom reports', ['Metalinguistic awareness', 'Cable breaks', 'Grant neglect'], 'i', tip),
                _heading('Policy caution', ['Avoid overselling a cure', 'Ban all languages', 'Close schools'], 'i', tip),
                _heading('Why support learning anyway', ['Cultural and economic reasons', 'Only fashion', 'Only copper'], 'i', tip),
                _heading('What remains debated', ['Size of the advantages', 'Whether water is wet', 'Park closing times'], 'i', tip),
                _heading('Overall evidence picture', ['Growing but contested', 'Settled forever', 'Only about ships'], 'i', tip),
            ]}
        if rtype == 'matching_endings':
            endings = [
                'attentional control and cognitive flexibility.',
                'socioeconomic status and education.',
                'frequent language switching.',
                'longitudinal designs are still rare.',
                'metalinguistic awareness.',
                'a universal cognitive cure.',
            ]
            return {'questions': [
                _match('Bilingualism may enhance', endings, 'a', tip),
                _match('Some studies report modest advantages after controlling for', endings, 'b', tip),
                _match('Benefits may arise from', endings, 'c', tip),
                _match('Researchers note that', endings, 'd', tip),
                _match('Teachers report gains in', endings, 'e', tip),
                _match('Policy makers should avoid overselling bilingualism as', endings, 'f', tip),
                _match('Lab tasks may not mirror', ['everyday communication.', 'ocean cables.', 'park tickets.'], 'a', tip),
                _match('Lifestyle factors in multilingual communities are', ['another debated source.', 'proof cables fail.', 'park grants.'], 'a', tip),
                _match('Early language learning is still supported for', ['cultural and economic reasons.', 'closing schools.', 'banning books.'], 'a', tip),
                _match('The size of these effects', ['remains contested.', 'is exactly 100%.', 'only concerns ships.'], 'a', tip),
            ]}
        if rtype == 'matching_names':
            return {
                'title': names_title,
                'passage': names_passage,
                'questions': [
                    _match('Studies attentional control in bilingual adults', names, 'a', tip),
                    _match('Argues effect sizes shrink after SES controls', names, 'b', tip),
                    _match('Links benefits to language switching', names, 'c', tip),
                    _match('Reports classroom metalinguistic gains', names, 'd', tip),
                    _match('Warns against overselling a cognitive cure', names, 'e', tip),
                    _match('Calls for more longitudinal designs', names, 'f', tip),
                    _match('Focuses on executive attention research', names, 'a', tip),
                    _match('Emphasises statistical controls', names, 'b', tip),
                    _match('Highlights switching frequency', names, 'c', tip),
                    _match('Works on education policy caution', names, 'e', tip),
                ],
            }
    if level == 'C2':
        names_title = 'Experts on Climate Uncertainty'
        names_passage = (
            "Dr Farah Quinn models parameterisation choices in climate ensembles. "
            "Professor Ian Vogt warns that technical presentations can obscure thresholds. "
            "Communicator Sofia Berg promotes visual summaries for non-specialists. "
            "Ethicist David Okonkwo focuses on acting under ambiguity. "
            "Funding officer Mei Chen requires uncertainty statements in reports. "
            "Advisor Lars Holm argues probabilistic ensembles improve decisions."
        )
        names = [
            'Dr Farah Quinn', 'Professor Ian Vogt', 'Sofia Berg',
            'David Okonkwo', 'Mei Chen', 'Lars Holm',
        ]
        if rtype == 'tfng':
            return {'tfng_raw': [
                {'prompt': 'Climate projections include epistemic uncertainty from incomplete process understanding.', 'correct': 'a'},
                {'prompt': 'Parameterisation choices are irrelevant to uncertainty.', 'correct': 'b'},
                {'prompt': 'Chaotic sensitivity to initial conditions is mentioned.', 'correct': 'a'},
                {'prompt': 'Communicating uncertainty never challenges public trust.', 'correct': 'b'},
                {'prompt': 'Some scholars argue probabilistic ensembles improve decision quality.', 'correct': 'a'},
                {'prompt': 'Others warn technical presentations can obscure actionable thresholds.', 'correct': 'a'},
                {'prompt': 'Visual summaries may help non-specialists.', 'correct': 'a'},
                {'prompt': 'Funding agencies never ask for uncertainty statements.', 'correct': 'b'},
                {'prompt': 'The ethical issue includes whether decision makers can act under ambiguity.', 'correct': 'a'},
                {'prompt': 'The passage names the exact global temperature for 2100.', 'correct': 'c'},
            ]}
        if rtype == 'mcq':
            return {'questions': [
                _mcq('What kind of uncertainty is discussed?', ['Epistemic uncertainty', 'Only ticket prices', 'Park opening hours', 'Cable weight'], 'a', tip),
                _mcq('Which sources of uncertainty are listed?', ['Process gaps, parameterisation, chaos', 'Only picnic weather', 'Only Wi-Fi speed', 'Only ship names'], 'a', tip),
                _mcq('What communication challenge is raised?', ['Trust while explaining uncertainty', 'Closing all schools', 'Banning ensembles', 'Ending reports'], 'a', tip),
                _mcq('What may improve decision quality?', ['Probabilistic ensembles', 'Hiding all data', 'Removing visuals', 'Banning funding'], 'a', tip),
                _mcq('What can overly technical presentations obscure?', ['Actionable thresholds', 'Ocean copper', 'Park grass', 'Library cards'], 'a', tip),
                _mcq('What may help non-specialists?', ['Visual summaries and ranges', 'Longer jargon only', 'No numbers at all', 'Closed reports'], 'a', tip),
                _mcq('What do funding agencies increasingly require?', ['Uncertainty statements', 'Free cars', 'Park stadiums', 'Silent reports'], 'a', tip),
                _mcq('What ethical issue is highlighted?', ['Acting under ambiguity', 'Banning science', 'Closing ports', 'Ending schools'], 'a', tip),
                _mcq('What should decision makers not wait for?', ['Impossible certainty', 'Any ensemble', 'Any visual', 'Any funding'], 'a', tip),
                _mcq('Who faces a distinctive communication challenge?', ['Scientists and policymakers', 'Only cable engineers', 'Only librarians', 'Only park keepers'], 'a', tip),
            ]}
        if rtype == 'gap_fill':
            return {'questions': [
                _gap('Climate projections incorporate epistemic ______.', 'uncertainty', tip),
                _gap('Uncertainty arises from incomplete process ______.', 'understanding', tip),
                _gap('______ choices also contribute to uncertainty.', 'Parameterisation|Parameterization|parameterisation|parameterization', tip),
                _gap('There is chaotic sensitivity to initial ______.', 'conditions', tip),
                _gap('Communicating uncertainty without undermining public ______ is hard.', 'trust', tip),
                _gap('Probabilistic ______ may improve decision quality.', 'ensembles', tip),
                _gap('Technical presentations can obscure actionable ______.', 'thresholds', tip),
                _gap('Visual ______ may help non-specialists.', 'summaries', tip),
                _gap('Funding agencies require uncertainty ______ in reports.', 'statements', tip),
                _gap('Decision makers may need to act under ______.', 'ambiguity', tip),
            ]}
        if rtype == 'matching_headings':
            return {'questions': [
                _heading('Sources of model uncertainty', ['Process gaps and parameterisation', 'Park grants', 'Library Wi-Fi'], 'i', tip),
                _heading('Chaos and starting points', ['Sensitivity to initial conditions', 'Ship cable weight', 'Picnic menus'], 'i', tip),
                _heading('Public trust challenge', ['Communicating uncertainty carefully', 'Closing schools', 'Banning copper'], 'i', tip),
                _heading('Ensemble arguments', ['Better decision quality', 'Useless forever', 'Only fashion'], 'i', tip),
                _heading('Risk of jargon', ['Obscuring actionable thresholds', 'Planting trees', 'Borrowing books'], 'i', tip),
                _heading('Help for non-specialists', ['Visual summaries and ranges', 'More jargon only', 'No reports'], 'i', tip),
                _heading('Funding requirements', ['Uncertainty statements', 'Free stadiums', 'Silent science'], 'i', tip),
                _heading('Ethics of action', ['Acting under ambiguity', 'Waiting forever', 'Ignoring all data'], 'i', tip),
                _heading('Impossible standard', ['Waiting for perfect certainty', 'Banning ensembles', 'Ending visuals'], 'i', tip),
                _heading('Who must communicate', ['Scientists and policymakers', 'Only park keepers', 'Only captains'], 'i', tip),
            ]}
        if rtype == 'matching_endings':
            endings = [
                'incomplete process understanding.',
                'parameterisation choices.',
                'chaotic sensitivity to initial conditions.',
                'probabilistic ensembles.',
                'actionable thresholds for adaptation.',
                'uncertainty statements in reports.',
            ]
            return {'questions': [
                _match('Epistemic uncertainty arises from', endings, 'a', tip),
                _match('Further uncertainty comes from', endings, 'b', tip),
                _match('Models also show', endings, 'c', tip),
                _match('Some scholars argue for', endings, 'd', tip),
                _match('Technical talks may obscure', endings, 'e', tip),
                _match('Funding agencies increasingly require', endings, 'f', tip),
                _match('Visual summaries may help', ['non-specialists.', 'only ships.', 'only parks.'], 'a', tip),
                _match('The ethical issue includes whether leaders can', ['act under ambiguity.', 'ban all science.', 'close all ports.'], 'a', tip),
                _match('Decision makers should not wait for', ['impossible certainty.', 'any rainfall.', 'park tickets.'], 'a', tip),
                _match('Communicating uncertainty without harming', ['public trust is difficult.', 'copper cables.', 'library cards.'], 'a', tip),
            ]}
        if rtype == 'matching_names':
            return {
                'title': names_title,
                'passage': names_passage,
                'questions': [
                    _match('Models parameterisation in climate ensembles', names, 'a', tip),
                    _match('Warns technical talks obscure thresholds', names, 'b', tip),
                    _match('Promotes visual summaries for non-specialists', names, 'c', tip),
                    _match('Focuses on acting under ambiguity', names, 'd', tip),
                    _match('Requires uncertainty statements in reports', names, 'e', tip),
                    _match('Argues ensembles improve decisions', names, 'f', tip),
                    _match('Works on ensemble parameter choices', names, 'a', tip),
                    _match('Critiques overly technical presentation', names, 'b', tip),
                    _match('Designs accessible visual communication', names, 'c', tip),
                    _match('Sets funding rules on uncertainty', names, 'e', tip),
                ],
            }
    return {}


def _local_reading_b(level: str, rtype: str, lang: str) -> dict:
    """Ikkinchi matn/savol to'plami — qayta bosganda boshqa kontent."""
    meta = READING_TYPES[rtype]
    tip_common = t(lang, 'Matndan kalit so‘zlarni toping.', 'Ищите ключевые слова в тексте.')
    packs = {
        'A1': {
            'title': 'A Day at the Beach',
            'passage': (
                "Many families like the beach. The sand is soft and warm. Children build sandcastles. "
                "Some people swim in the sea. Others sit under umbrellas. Seagulls fly above the water. "
                "In the afternoon, friends buy ice cream. Lifeguards watch the swimmers. "
                "The beach shop sells water and fruit. In the evening the sun goes down. "
                "People collect their towels and go home. The beach is quiet at night."
            ),
        },
        'A2': {
            'title': 'City Sports Clubs',
            'passage': (
                "Sports clubs in cities are popular with young people. Many clubs offer football, swimming, "
                "and basketball. Members pay a monthly fee for training and equipment. Coaches help beginners "
                "learn basic skills. Some clubs also organise weekend matches between neighbourhoods. "
                "Parents often bring children on Saturday mornings. Changing rooms and showers are available. "
                "Healthy snacks are sold in the small café. Because of these activities, teenagers spend less "
                "time alone at home. Local councils sometimes support clubs with small grants."
            ),
        },
        'B1': {
            'title': 'Cycling in the City',
            'passage': (
                "Cycling has become a practical way to move through crowded cities. Bike lanes reduce travel "
                "time for short trips and cut local air pollution. However, drivers sometimes ignore painted "
                "lanes, which makes riders feel unsafe. Cities that add protected cycle tracks see higher "
                "weekday use. Bike-share schemes help tourists and residents without private bicycles. "
                "Storage at stations and workplaces remains a challenge. Helmet laws differ between countries. "
                "Employers who offer showers and lockers report more staff cycling to work. Overall, planners "
                "now treat cycling as transport, not only as a weekend hobby."
            ),
        },
        'B2': {
            'title': 'The Printing Press Revolution',
            'passage': (
                "In the fifteenth century, Johannes Gutenberg developed a movable-type printing press in Europe. "
                "Metal letters could be rearranged and reused, which made books far cheaper to produce. "
                "Workshops spread across cities as demand for religious and scholarly texts grew. Critics feared "
                "that wider literacy would weaken traditional authorities. Yet printers also created newspapers "
                "and pamphlets that shared news more quickly. Paper quality and ink chemistry improved over decades. "
                "The press changed education, science, and politics by multiplying identical copies. Although "
                "hand-copied manuscripts continued for luxury editions, mass reading culture had begun."
            ),
        },
        'C1': {
            'title': 'Sleep and Memory Consolidation',
            'passage': (
                "Sleep is no longer viewed as a passive shutdown of the brain. Research links slow-wave and REM "
                "stages to memory consolidation, emotional regulation, and creative problem solving. "
                "Nevertheless, laboratory findings do not always generalise: short naps help some tasks but not "
                "others, and individual chronotypes matter. Chronic restriction impairs attention more visibly "
                "than a single late night. Educators debate later school start times for adolescents. "
                "Pharmaceutical sleep aids may increase duration without restoring natural architecture. "
                "Public-health guidance therefore stresses regular schedules and light exposure rather than "
                "treating sleep as optional recovery time."
            ),
        },
        'C2': {
            'title': 'Algorithmic Bias in Hiring',
            'passage': (
                "Automated screening tools promise efficiency in recruitment, yet they can reproduce historical "
                "bias encoded in training data. Models trained on past hiring decisions may undervalue "
                "candidates from under-represented groups even when proxies for protected attributes are removed. "
                "Auditing frameworks recommend disparate-impact tests and human review of borderline cases. "
                "Vendors often claim neutrality while disclosing little about features or error rates. "
                "Regulators increasingly require explainability statements for high-stakes employment systems. "
                "The ethical tension is between scalable shortlisting and fair opportunity: optimisation for "
                "past 'success' can lock organisations into yesterday's workforce patterns."
            ),
        },
    }
    pack = packs.get(level, packs['B1'])
    title = pack['title']
    passage = pack['passage']

    if rtype == 'tfng':
        opts = _tfng_options()
        raw_by = {
            'A1': [
                {'prompt': 'Children build sandcastles at the beach.', 'correct': 'a'},
                {'prompt': 'The sand is cold and hard.', 'correct': 'b'},
                {'prompt': 'Some people swim in the sea.', 'correct': 'a'},
                {'prompt': 'Lifeguards watch the swimmers.', 'correct': 'a'},
                {'prompt': 'The beach shop sells cars.', 'correct': 'b'},
                {'prompt': 'Friends buy ice cream in the afternoon.', 'correct': 'a'},
                {'prompt': 'The beach has a large airport.', 'correct': 'c'},
                {'prompt': 'Seagulls fly above the water.', 'correct': 'a'},
                {'prompt': 'People never go home in the evening.', 'correct': 'b'},
                {'prompt': 'The beach is quiet at night.', 'correct': 'a'},
            ],
            'A2': [
                {'prompt': 'Sports clubs offer football and swimming.', 'correct': 'a'},
                {'prompt': 'Members never pay any fee.', 'correct': 'b'},
                {'prompt': 'Coaches help beginners learn skills.', 'correct': 'a'},
                {'prompt': 'Some clubs organise weekend matches.', 'correct': 'a'},
                {'prompt': 'Parents often bring children on Saturday mornings.', 'correct': 'a'},
                {'prompt': 'Clubs have no changing rooms.', 'correct': 'b'},
                {'prompt': 'Every club owns a professional stadium.', 'correct': 'c'},
                {'prompt': 'A café sells healthy snacks.', 'correct': 'a'},
                {'prompt': 'Councils sometimes support clubs with grants.', 'correct': 'a'},
                {'prompt': 'Teenagers only stay alone at home because of clubs.', 'correct': 'b'},
            ],
            'B1': [
                {'prompt': 'Cycling can cut local air pollution.', 'correct': 'a'},
                {'prompt': 'Drivers always respect bike lanes.', 'correct': 'b'},
                {'prompt': 'Protected cycle tracks raise weekday use.', 'correct': 'a'},
                {'prompt': 'Bike-share helps people without private bicycles.', 'correct': 'a'},
                {'prompt': 'Storage at workplaces is never a problem.', 'correct': 'b'},
                {'prompt': 'Helmet laws are the same in every country.', 'correct': 'b'},
                {'prompt': 'The passage gives the exact number of city bikes worldwide.', 'correct': 'c'},
                {'prompt': 'Showers and lockers encourage staff cycling.', 'correct': 'a'},
                {'prompt': 'Planners now treat cycling as transport.', 'correct': 'a'},
                {'prompt': 'Cycling is described only as a weekend hobby.', 'correct': 'b'},
            ],
            'B2': [
                {'prompt': 'Gutenberg developed a movable-type press in Europe.', 'correct': 'a'},
                {'prompt': 'Metal letters could not be reused.', 'correct': 'b'},
                {'prompt': 'Books became cheaper to produce.', 'correct': 'a'},
                {'prompt': 'Some critics feared wider literacy.', 'correct': 'a'},
                {'prompt': 'Printers also made newspapers and pamphlets.', 'correct': 'a'},
                {'prompt': 'Hand-copied manuscripts disappeared overnight.', 'correct': 'b'},
                {'prompt': 'The passage states the exact price of the first Bible.', 'correct': 'c'},
                {'prompt': 'The press affected education and science.', 'correct': 'a'},
                {'prompt': 'Paper and ink quality never improved.', 'correct': 'b'},
                {'prompt': 'Mass reading culture began after the press.', 'correct': 'a'},
            ],
            'C1': [
                {'prompt': 'Sleep is linked to memory consolidation.', 'correct': 'a'},
                {'prompt': 'All lab findings generalise perfectly to daily life.', 'correct': 'b'},
                {'prompt': 'Chronotypes can matter for sleep effects.', 'correct': 'a'},
                {'prompt': 'Chronic restriction impairs attention.', 'correct': 'a'},
                {'prompt': 'Educators debate later school start times.', 'correct': 'a'},
                {'prompt': 'Sleep aids always restore natural sleep architecture.', 'correct': 'b'},
                {'prompt': 'The passage names one universal nap length for all tasks.', 'correct': 'c'},
                {'prompt': 'Guidance stresses regular schedules and light exposure.', 'correct': 'a'},
                {'prompt': 'Sleep is presented as optional recovery only.', 'correct': 'b'},
                {'prompt': 'REM sleep is mentioned in relation to brain functions.', 'correct': 'a'},
            ],
            'C2': [
                {'prompt': 'Hiring algorithms can reproduce historical bias.', 'correct': 'a'},
                {'prompt': 'Removing obvious proxies always ends all bias.', 'correct': 'b'},
                {'prompt': 'Audits may include disparate-impact tests.', 'correct': 'a'},
                {'prompt': 'Vendors sometimes disclose little about error rates.', 'correct': 'a'},
                {'prompt': 'Regulators may require explainability statements.', 'correct': 'a'},
                {'prompt': 'Optimising for past success cannot lock in old patterns.', 'correct': 'b'},
                {'prompt': 'The passage quotes a single global accuracy percentage.', 'correct': 'c'},
                {'prompt': 'Human review of borderline cases is recommended.', 'correct': 'a'},
                {'prompt': 'Efficiency is the only ethical concern mentioned.', 'correct': 'b'},
                {'prompt': 'Training data can encode past hiring decisions.', 'correct': 'a'},
            ],
        }
        raw = raw_by.get(level, raw_by['B1'])
        questions = [
            {'prompt': row['prompt'], 'options': opts, 'correct': row['correct'], 'explanation': tip_common}
            for row in raw
        ]
    elif rtype == 'mcq':
        q_by = {
            'A1': [
                _mcq('What do children build?', ['Sandcastles', 'Airports', 'Trains', 'Factories'], 'a', tip_common),
                _mcq('Who watches the swimmers?', ['Lifeguards', 'Pilots', 'Teachers only', 'Nobody'], 'a', tip_common),
                _mcq('What do friends buy in the afternoon?', ['Ice cream', 'Cars', 'Tickets to space', 'Sand'], 'a', tip_common),
                _mcq('What does the beach shop sell?', ['Water and fruit', 'Airplanes', 'Computers only', 'Coal'], 'a', tip_common),
                _mcq('When is the beach quiet?', ['At night', 'Only at noon forever', 'Never', 'During storms only'], 'a', tip_common),
                _mcq('Where do people sit?', ['Under umbrellas', 'In submarines', 'On runways', 'In libraries'], 'a', tip_common),
                _mcq('What flies above the water?', ['Seagulls', 'Trains', 'Buses', 'Cables'], 'a', tip_common),
                _mcq('What is soft and warm?', ['The sand', 'The moon', 'Iron', 'Glass only'], 'a', tip_common),
                _mcq('What do people collect before going home?', ['Towels', 'Ships', 'Planes', 'Stadiums'], 'a', tip_common),
                _mcq('Who likes the beach?', ['Many families', 'Only robots', 'Only fish', 'Nobody'], 'a', tip_common),
            ],
            'A2': [
                _mcq('What sports can clubs offer?', ['Football, swimming, basketball', 'Only chess online', 'Ship building', 'Mining'], 'a', tip_common),
                _mcq('How do members usually pay?', ['A monthly fee', 'Nothing ever', 'Only gold', 'Free flights'], 'a', tip_common),
                _mcq('Who helps beginners?', ['Coaches', 'Pilots', 'Farmers only', 'Judges'], 'a', tip_common),
                _mcq('When do parents often bring children?', ['Saturday mornings', 'Only at midnight', 'Never', 'During exams only'], 'a', tip_common),
                _mcq('What is in the café?', ['Healthy snacks', 'Airplane fuel', 'Sand only', 'Cable wire'], 'a', tip_common),
                _mcq('What can councils give clubs?', ['Small grants', 'Airports', 'Oceans', 'Factories'], 'a', tip_common),
                _mcq('What facilities are available?', ['Changing rooms and showers', 'Runways', 'Submarines', 'Mines'], 'a', tip_common),
                _mcq('What do clubs organise on weekends?', ['Matches', 'Space launches', 'Bank audits', 'Ocean cables'], 'a', tip_common),
                _mcq('Why are clubs useful for teenagers?', ['They spend less time alone at home', 'They ban all sports', 'They close cafés', 'They remove coaches'], 'a', tip_common),
                _mcq('Who are clubs popular with?', ['Young people', 'Only ships', 'Only forests', 'Only museums'], 'a', tip_common),
            ],
            'B1': [
                _mcq('What do bike lanes help with?', ['Short trips and less pollution', 'Building airports', 'Closing parks', 'Banning walking'], 'a', tip_common),
                _mcq('What makes riders feel unsafe?', ['Drivers ignoring lanes', 'Too many showers', 'Free lockers', 'Bike-share apps'], 'a', tip_common),
                _mcq('What raises weekday cycling?', ['Protected cycle tracks', 'Removing all bikes', 'Banning helmets always', 'Closing stations'], 'a', tip_common),
                _mcq('Who can bike-share help?', ['Tourists and residents without private bikes', 'Only pilots', 'Only ships', 'Only miners'], 'a', tip_common),
                _mcq('What workplace features help?', ['Showers and lockers', 'Airport runways', 'Ocean maps', 'Silent grants'], 'a', tip_common),
                _mcq('How do planners view cycling now?', ['As transport', 'Only as a toy', 'As banned forever', 'As ocean sport only'], 'a', tip_common),
                _mcq('What remains a challenge?', ['Storage at stations and workplaces', 'Too much free space', 'No cities left', 'Endless helmet agreement'], 'a', tip_common),
                _mcq('What differs between countries?', ['Helmet laws', 'Whether wheels exist', 'Whether air exists', 'Whether roads exist'], 'a', tip_common),
                _mcq('What do painted lanes not always get?', ['Respect from drivers', 'Rain', 'Sunlight', 'Tourists'], 'a', tip_common),
                _mcq('What is cycling no longer only?', ['A weekend hobby', 'A form of transport', 'A city topic', 'A planning issue'], 'a', tip_common),
            ],
            'B2': [
                _mcq('Who developed movable-type printing in Europe?', ['Johannes Gutenberg', 'Cyrus Field', 'A random sailor', 'A park keeper'], 'a', tip_common),
                _mcq('Why did books become cheaper?', ['Reusable metal letters', 'Free gold ink', 'No paper needed', 'Banned reading'], 'a', tip_common),
                _mcq('What did critics fear?', ['Wider literacy weakening authorities', 'Too few books', 'Closed workshops', 'No pamphlets'], 'a', tip_common),
                _mcq('What else did printers create?', ['Newspapers and pamphlets', 'Only stone tablets', 'Only ships', 'Only stadiums'], 'a', tip_common),
                _mcq('What continued for luxury editions?', ['Hand-copied manuscripts', 'Only radio', 'Only airports', 'Only bike lanes'], 'a', tip_common),
                _mcq('What multiplied identical copies?', ['The printing press', 'Ocean cables only', 'Park grants', 'Helmet laws'], 'a', tip_common),
                _mcq('What improved over decades?', ['Paper quality and ink chemistry', 'Only horse speed', 'Only castle walls', 'Only sand'], 'a', tip_common),
                _mcq('Where did workshops spread?', ['Across cities', 'Only underwater', 'Only on the moon', 'Only in deserts'], 'a', tip_common),
                _mcq('What culture began?', ['Mass reading culture', 'Only silent films', 'Only bike-share', 'Only remote work'], 'a', tip_common),
                _mcq('Which fields did the press change?', ['Education, science, and politics', 'Only fishing', 'Only mining', 'Only cooking'], 'a', tip_common),
            ],
            'C1': [
                _mcq('What is sleep linked to?', ['Memory consolidation', 'Building cables', 'Park tickets', 'Sandcastles'], 'a', tip_common),
                _mcq('What may not always generalise?', ['Laboratory findings', 'That people sleep', 'That night exists', 'That schools exist'], 'a', tip_common),
                _mcq('What do chronotypes affect?', ['How sleep interventions work', 'Ocean depth', 'Cable weight', 'Sand colour'], 'a', tip_common),
                _mcq('What does chronic restriction impair?', ['Attention', 'Only printing', 'Only cycling lanes', 'Only hiring audits'], 'a', tip_common),
                _mcq('What do educators debate?', ['Later school start times', 'Banning sleep', 'Closing libraries', 'Removing REM'], 'a', tip_common),
                _mcq('What may sleep aids fail to restore?', ['Natural sleep architecture', 'Daylight', 'Paper ink', 'Bike lockers'], 'a', tip_common),
                _mcq('What does guidance emphasise?', ['Regular schedules and light', 'More caffeine only', 'Endless naps for all', 'Ignoring sleep'], 'a', tip_common),
                _mcq('How is sleep no longer viewed?', ['As a passive shutdown', 'As useful', 'As researched', 'As health-related'], 'a', tip_common),
                _mcq('What can short naps help?', ['Some tasks but not others', 'Every task equally', 'Only printing books', 'Only hiring'], 'a', tip_common),
                _mcq('Which stages are mentioned?', ['Slow-wave and REM', 'Only waking', 'Only sprinting', 'Only commuting'], 'a', tip_common),
            ],
            'C2': [
                _mcq('What can screening tools reproduce?', ['Historical bias', 'Perfect fairness always', 'Ocean maps', 'Sandcastles'], 'a', tip_common),
                _mcq('Where can bias be encoded?', ['Training data', 'Only printers', 'Only helmets', 'Only beaches'], 'a', tip_common),
                _mcq('What do audits recommend?', ['Disparate-impact tests and human review', 'No reviews ever', 'Secret scores only', 'Deleting all applicants'], 'a', tip_common),
                _mcq('What do vendors often disclose little about?', ['Features or error rates', 'That hiring exists', 'That computers exist', 'That jobs exist'], 'a', tip_common),
                _mcq('What may regulators require?', ['Explainability statements', 'Silent algorithms only', 'No humans ever', 'Random hiring only'], 'a', tip_common),
                _mcq('What ethical tension is described?', ['Scale vs fair opportunity', 'Beaches vs parks', 'Sleep vs cycling', 'Ink vs paper'], 'a', tip_common),
                _mcq('What can optimisation for past success do?', ['Lock in old workforce patterns', 'End all bias', 'Guarantee diversity', 'Remove all data'], 'a', tip_common),
                _mcq('What may still undervalue some candidates?', ['Models trained on past decisions', 'Human greetings', 'Office plants', 'Coffee machines'], 'a', tip_common),
                _mcq('What promise do tools make?', ['Efficiency', 'Endless holidays', 'Free degrees', 'Perfect sleep'], 'a', tip_common),
                _mcq('What is not enough alone?', ['Removing obvious proxies', 'Any audit', 'Any regulator', 'Any vendor claim'], 'a', tip_common),
            ],
        }
        questions = q_by.get(level, q_by['B1'])
    elif rtype == 'gap_fill':
        g_by = {
            'A1': [
                _gap('Children build ______.', 'sandcastles|sand castles', tip_common),
                _gap('Some people swim in the ______.', 'sea', tip_common),
                _gap('Lifeguards watch the ______.', 'swimmers', tip_common),
                _gap('Friends buy ______ in the afternoon.', 'ice cream|icecream', tip_common),
                _gap('The beach shop sells water and ______.', 'fruit', tip_common),
                _gap('Seagulls fly above the ______.', 'water', tip_common),
                _gap('The sand is soft and ______.', 'warm', tip_common),
                _gap('People sit under ______.', 'umbrellas', tip_common),
                _gap('People collect their ______ and go home.', 'towels', tip_common),
                _gap('The beach is quiet at ______.', 'night', tip_common),
            ],
            'A2': [
                _gap('Members pay a monthly ______.', 'fee', tip_common),
                _gap('______ help beginners learn skills.', 'Coaches|coaches', tip_common),
                _gap('Clubs organise weekend ______.', 'matches', tip_common),
                _gap('Parents bring children on Saturday ______.', 'mornings', tip_common),
                _gap('The café sells healthy ______.', 'snacks', tip_common),
                _gap('Councils may support clubs with ______.', 'grants', tip_common),
                _gap('Changing rooms and ______ are available.', 'showers', tip_common),
                _gap('Sports clubs are popular with ______ people.', 'young', tip_common),
                _gap('Teenagers spend less time alone at ______.', 'home', tip_common),
                _gap('Clubs offer football, swimming and ______.', 'basketball', tip_common),
            ],
            'B1': [
                _gap('Bike lanes can cut local air ______.', 'pollution', tip_common),
                _gap('Protected cycle ______ raise weekday use.', 'tracks', tip_common),
                _gap('Bike-share helps people without private ______.', 'bicycles|bikes', tip_common),
                _gap('Storage at workplaces remains a ______.', 'challenge', tip_common),
                _gap('______ laws differ between countries.', 'Helmet|helmet', tip_common),
                _gap('Showers and ______ encourage staff cycling.', 'lockers', tip_common),
                _gap('Planners treat cycling as ______.', 'transport', tip_common),
                _gap('Drivers sometimes ignore painted ______.', 'lanes', tip_common),
                _gap('Cycling reduces travel time for short ______.', 'trips', tip_common),
                _gap('Cycling is not only a weekend ______.', 'hobby', tip_common),
            ],
            'B2': [
                _gap('Gutenberg developed a movable-type printing ______.', 'press', tip_common),
                _gap('Metal ______ could be rearranged and reused.', 'letters', tip_common),
                _gap('Books became ______ to produce.', 'cheaper', tip_common),
                _gap('Workshops spread across ______.', 'cities', tip_common),
                _gap('Printers created newspapers and ______.', 'pamphlets', tip_common),
                _gap('Hand-copied ______ continued for luxury editions.', 'manuscripts', tip_common),
                _gap('The press multiplied identical ______.', 'copies', tip_common),
                _gap('Paper quality and ______ chemistry improved.', 'ink', tip_common),
                _gap('Mass ______ culture had begun.', 'reading', tip_common),
                _gap('Critics feared wider ______.', 'literacy', tip_common),
            ],
            'C1': [
                _gap('Sleep is linked to memory ______.', 'consolidation', tip_common),
                _gap('Lab findings do not always ______.', 'generalise|generalize', tip_common),
                _gap('Individual ______ matter.', 'chronotypes', tip_common),
                _gap('Chronic restriction impairs ______.', 'attention', tip_common),
                _gap('Educators debate later school start ______.', 'times', tip_common),
                _gap('Aids may not restore natural sleep ______.', 'architecture', tip_common),
                _gap('Guidance stresses regular ______.', 'schedules', tip_common),
                _gap('Light ______ is also recommended.', 'exposure', tip_common),
                _gap('REM stages relate to creative problem ______.', 'solving', tip_common),
                _gap('Sleep is not a passive ______ of the brain.', 'shutdown', tip_common),
            ],
            'C2': [
                _gap('Tools can reproduce historical ______.', 'bias', tip_common),
                _gap('Bias may be encoded in training ______.', 'data', tip_common),
                _gap('Audits use disparate-impact ______.', 'tests', tip_common),
                _gap('Borderline cases need human ______.', 'review', tip_common),
                _gap('Vendors disclose little about error ______.', 'rates', tip_common),
                _gap('Regulators require ______ statements.', 'explainability', tip_common),
                _gap('Optimisation can lock in old workforce ______.', 'patterns', tip_common),
                _gap('The promise of tools is ______.', 'efficiency', tip_common),
                _gap('Removing proxies may not end all ______.', 'bias', tip_common),
                _gap('High-stakes systems need fair ______.', 'opportunity', tip_common),
            ],
        }
        questions = g_by.get(level, g_by['B1'])
    elif rtype == 'matching_headings':
        h_by = {
            'A1': [
                _heading('What children build', ['Sandcastles', 'Airports', 'Factories'], 'i', tip_common),
                _heading('Who watches swimmers', ['Lifeguards', 'Pilots', 'Judges'], 'i', tip_common),
                _heading('Afternoon treat', ['Ice cream', 'Coal', 'Tickets'], 'i', tip_common),
                _heading('Shop products', ['Water and fruit', 'Planes', 'Cables'], 'i', tip_common),
                _heading('Birds above water', ['Seagulls', 'Trains', 'Buses'], 'i', tip_common),
                _heading('Shade on the beach', ['Umbrellas', 'Submarines', 'Mines'], 'i', tip_common),
                _heading('Evening departure', ['Collect towels and go home', 'Build an airport', 'Open a factory'], 'i', tip_common),
                _heading('Night atmosphere', ['Quiet beach', 'Loud stadium', 'Busy runway'], 'i', tip_common),
                _heading('Sand quality', ['Soft and warm', 'Made of glass', 'Frozen metal'], 'i', tip_common),
                _heading('Who enjoys beaches', ['Many families', 'Only robots', 'Only ships'], 'i', tip_common),
            ],
            'A2': [
                _heading('Popular city activities', ['Sports clubs for young people', 'Closing all parks', 'Banning coaches'], 'i', tip_common),
                _heading('How members pay', ['Monthly fee', 'Free gold', 'No payment ever'], 'i', tip_common),
                _heading('Beginner support', ['Coaches teach skills', 'No training', 'Only exams'], 'i', tip_common),
                _heading('Weekend events', ['Neighbourhood matches', 'Space launches', 'Mining trips'], 'i', tip_common),
                _heading('Saturday visitors', ['Parents with children', 'Only pilots', 'Only judges'], 'i', tip_common),
                _heading('Club facilities', ['Changing rooms and showers', 'Runways', 'Submarines'], 'i', tip_common),
                _heading('Café offer', ['Healthy snacks', 'Airplane fuel', 'Sand'], 'i', tip_common),
                _heading('Council help', ['Small grants', 'Airports', 'Oceans'], 'i', tip_common),
                _heading('Teen free time', ['Less time alone at home', 'More isolation', 'No sports'], 'i', tip_common),
                _heading('Sports on offer', ['Football, swimming, basketball', 'Only coding', 'Only chess online'], 'i', tip_common),
            ],
            'B1': [
                _heading('Benefits of bike lanes', ['Faster short trips, less pollution', 'More traffic jams', 'No cities'], 'i', tip_common),
                _heading('Safety problem', ['Drivers ignore lanes', 'Too many lockers', 'Free helmets'], 'i', tip_common),
                _heading('Protected tracks', ['Higher weekday use', 'Fewer cyclists', 'Closed cities'], 'i', tip_common),
                _heading('Shared bikes', ['Help without private bikes', 'Ban tourists', 'Remove stations'], 'i', tip_common),
                _heading('Workplace support', ['Showers and lockers', 'No bikes allowed', 'Only cars'], 'i', tip_common),
                _heading('Planning view', ['Cycling as transport', 'Only a hobby', 'Banned forever'], 'i', tip_common),
                _heading('Storage issue', ['Stations and workplaces', 'Too much space', 'Endless racks'], 'i', tip_common),
                _heading('Rule differences', ['Helmet laws vary', 'All laws identical', 'No laws exist'], 'i', tip_common),
                _heading('Short trips', ['Practical city travel', 'Only ocean travel', 'Only flights'], 'i', tip_common),
                _heading('Not only leisure', ['Transport role', 'Toy role only', 'No role'], 'i', tip_common),
            ],
            'B2': [
                _heading('Key inventor', ['Gutenberg and movable type', 'Only sailors', 'Park designers'], 'i', tip_common),
                _heading('Cheaper books', ['Reusable metal letters', 'No paper', 'Banned ink'], 'i', tip_common),
                _heading('Workshop growth', ['Spread across cities', 'Only underwater', 'Only deserts'], 'i', tip_common),
                _heading('Authority fears', ['Wider literacy risks', 'Too few readers', 'Closed presses'], 'i', tip_common),
                _heading('Fast news', ['Newspapers and pamphlets', 'Only stone', 'Only radio later'], 'i', tip_common),
                _heading('Luxury copies', ['Hand manuscripts remain', 'No books left', 'Only digital'], 'i', tip_common),
                _heading('Social impact', ['Education, science, politics', 'Only fishing', 'Only sport'], 'i', tip_common),
                _heading('Materials improve', ['Paper and ink chemistry', 'Only horses', 'Only sand'], 'i', tip_common),
                _heading('Reading culture', ['Mass reading begins', 'Reading ends', 'Only elites forever'], 'i', tip_common),
                _heading('Identical copies', ['Press multiplies texts', 'One copy only', 'No copying'], 'i', tip_common),
            ],
            'C1': [
                _heading('Active brain overnight', ['Memory consolidation in sleep', 'Sleep as useless', 'Only muscle rest'], 'i', tip_common),
                _heading('Limits of labs', ['Findings may not generalise', 'Labs always perfect', 'No research'], 'i', tip_common),
                _heading('Individual differences', ['Chronotypes matter', 'Everyone identical', 'No variation'], 'i', tip_common),
                _heading('Chronic loss', ['Attention suffers', 'Attention improves always', 'No effect'], 'i', tip_common),
                _heading('School timing', ['Later starts debated', 'Schools ban sleep talk', 'No debate'], 'i', tip_common),
                _heading('Medication limits', ['Architecture not restored', 'Perfect natural sleep', 'No drugs exist'], 'i', tip_common),
                _heading('Public advice', ['Schedules and light', 'Ignore routines', 'Endless caffeine'], 'i', tip_common),
                _heading('Creative links', ['REM and problem solving', 'Only printing', 'Only hiring'], 'i', tip_common),
                _heading('Nap nuance', ['Helps some tasks only', 'Helps every task', 'Helps nothing'], 'i', tip_common),
                _heading('Not optional recovery', ['Health priority', 'Optional luxury only', 'Ignore sleep'], 'i', tip_common),
            ],
            'C2': [
                _heading('Efficiency promise', ['Automated screening speed', 'Perfect fairness', 'No tools'], 'i', tip_common),
                _heading('Encoded history', ['Bias in training data', 'Bias-free data always', 'No data used'], 'i', tip_common),
                _heading('Proxy problem', ['Hidden attributes remain', 'Proxies end all bias', 'No candidates'], 'i', tip_common),
                _heading('Audit methods', ['Impact tests and review', 'No audits', 'Secret scores only'], 'i', tip_common),
                _heading('Vendor opacity', ['Little error disclosure', 'Full open models always', 'No vendors'], 'i', tip_common),
                _heading('Regulatory push', ['Explainability required', 'No rules', 'Ban all hiring'], 'i', tip_common),
                _heading('Ethical tension', ['Scale versus fairness', 'Only beaches', 'Only sleep'], 'i', tip_common),
                _heading('Past success trap', ['Old patterns locked in', 'Future guaranteed fair', 'No history'], 'i', tip_common),
                _heading('Borderline cases', ['Human review needed', 'Never review humans', 'Delete all'], 'i', tip_common),
                _heading('Fair opportunity', ['Core ethical goal', 'Ignore opportunity', 'Only speed'], 'i', tip_common),
            ],
        }
        questions = h_by.get(level, h_by['B1'])
    elif rtype == 'matching_endings':
        if level == 'A1':
            endings = ['sandcastles.', 'in the sea.', 'under umbrellas.', 'ice cream.', 'at night.', 'the swimmers.']
            questions = [
                _match('Children build', endings, 'a', tip_common),
                _match('Some people swim', endings, 'b', tip_common),
                _match('Others sit', endings, 'c', tip_common),
                _match('Friends buy', endings, 'd', tip_common),
                _match('The beach is quiet', endings, 'e', tip_common),
                _match('Lifeguards watch', endings, 'f', tip_common),
                _match('The shop sells', ['water and fruit.', 'airplanes.', 'cables.'], 'a', tip_common),
                _match('Seagulls fly', ['above the water.', 'inside mines.', 'in libraries.'], 'a', tip_common),
                _match('People collect', ['their towels.', 'runways.', 'stadiums.'], 'a', tip_common),
                _match('Families like', ['the beach.', 'only factories.', 'only airports.'], 'a', tip_common),
            ]
        elif level == 'A2':
            endings = ['a monthly fee.', 'basic skills.', 'weekend matches.', 'Saturday mornings.', 'healthy snacks.', 'small grants.']
            questions = [
                _match('Members pay', endings, 'a', tip_common),
                _match('Coaches teach', endings, 'b', tip_common),
                _match('Clubs organise', endings, 'c', tip_common),
                _match('Parents visit on', endings, 'd', tip_common),
                _match('The café sells', endings, 'e', tip_common),
                _match('Councils may give', endings, 'f', tip_common),
                _match('Clubs offer', ['football and swimming.', 'only mining.', 'only flights.'], 'a', tip_common),
                _match('Teenagers spend', ['less time alone at home.', 'more time in airports.', 'no time training.'], 'a', tip_common),
                _match('Changing rooms', ['and showers are available.', 'are banned.', 'are oceans.'], 'a', tip_common),
                _match('Sports clubs are popular with', ['young people.', 'only ships.', 'only forests.'], 'a', tip_common),
            ]
        elif level == 'B1':
            endings = [
                'local air pollution.',
                'feel unsafe.',
                'higher weekday use.',
                'without private bicycles.',
                'showers and lockers.',
                'as transport.',
            ]
            questions = [
                _match('Bike lanes can reduce', endings, 'a', tip_common),
                _match('Ignored lanes make riders', endings, 'b', tip_common),
                _match('Protected tracks bring', endings, 'c', tip_common),
                _match('Bike-share helps people', endings, 'd', tip_common),
                _match('Employers may offer', endings, 'e', tip_common),
                _match('Planners now treat cycling', endings, 'f', tip_common),
                _match('Storage remains', ['a challenge.', 'solved forever.', 'illegal.'], 'a', tip_common),
                _match('Helmet laws', ['differ between countries.', 'are identical everywhere.', 'do not exist.'], 'a', tip_common),
                _match('Short trips become', ['more practical by bike.', 'impossible.', 'only by ship.'], 'a', tip_common),
                _match('Cycling is no longer only', ['a weekend hobby.', 'a transport mode.', 'a planning topic.'], 'a', tip_common),
            ]
        elif level == 'B2':
            endings = [
                'a movable-type printing press.',
                'rearranged and reused.',
                'far cheaper to produce.',
                'newspapers and pamphlets.',
                'education, science, and politics.',
                'mass reading culture.',
            ]
            questions = [
                _match('Gutenberg developed', endings, 'a', tip_common),
                _match('Metal letters could be', endings, 'b', tip_common),
                _match('Books became', endings, 'c', tip_common),
                _match('Printers also created', endings, 'd', tip_common),
                _match('The press changed', endings, 'e', tip_common),
                _match('The era began a', endings, 'f', tip_common),
                _match('Critics feared', ['wider literacy.', 'too few books.', 'closed oceans.'], 'a', tip_common),
                _match('Luxury editions still used', ['hand-copied manuscripts.', 'only radio.', 'only sand.'], 'a', tip_common),
                _match('Workshops spread', ['across cities.', 'only underwater.', 'only on Mars.'], 'a', tip_common),
                _match('Paper and ink', ['improved over decades.', 'never changed.', 'disappeared.'], 'a', tip_common),
            ]
        elif level == 'C1':
            endings = [
                'memory consolidation.',
                'not always generalise.',
                'individual chronotypes.',
                'attention more visibly.',
                'later school start times.',
                'regular schedules and light.',
            ]
            questions = [
                _match('Sleep is linked to', endings, 'a', tip_common),
                _match('Lab findings do', endings, 'b', tip_common),
                _match('Outcomes can depend on', endings, 'c', tip_common),
                _match('Chronic restriction impairs', endings, 'd', tip_common),
                _match('Educators debate', endings, 'e', tip_common),
                _match('Guidance stresses', endings, 'f', tip_common),
                _match('Sleep aids may fail to restore', ['natural architecture.', 'daylight.', 'printing.'], 'a', tip_common),
                _match('Short naps help', ['some tasks but not others.', 'every task equally.', 'no tasks.'], 'a', tip_common),
                _match('REM relates to', ['creative problem solving.', 'only hiring bias.', 'only bike lanes.'], 'a', tip_common),
                _match('Sleep is not merely', ['passive shutdown.', 'useful research.', 'a schedule topic.'], 'a', tip_common),
            ]
        else:
            endings = [
                'historical bias.',
                'training data.',
                'disparate-impact tests.',
                'error rates.',
                'explainability statements.',
                'old workforce patterns.',
            ]
            questions = [
                _match('Screening tools can reproduce', endings, 'a', tip_common),
                _match('Bias may be encoded in', endings, 'b', tip_common),
                _match('Audits recommend', endings, 'c', tip_common),
                _match('Vendors disclose little about', endings, 'd', tip_common),
                _match('Regulators may require', endings, 'e', tip_common),
                _match('Optimising past success can lock in', endings, 'f', tip_common),
                _match('Borderline cases need', ['human review.', 'no humans.', 'random deletion.'], 'a', tip_common),
                _match('Removing proxies may not', ['end all bias.', 'use any data.', 'hire anyone.'], 'a', tip_common),
                _match('The ethical tension is between scale and', ['fair opportunity.', 'beach time.', 'sleep length.'], 'a', tip_common),
                _match('Tools promise', ['efficiency.', 'perfect fairness always.', 'no decisions.'], 'a', tip_common),
            ]
    else:
        # matching_names
        names_packs = {
            'A1': {
                'title': 'People at the Beach',
                'passage': (
                    "Lila builds sandcastles near the water. Omar swims with a bright float. "
                    "Mrs Park sits under a large umbrella and reads. Chef Rico sells ice cream from a small cart. "
                    "Tina watches seagulls with binoculars. Lifeguard Sam blows a whistle when waves grow strong."
                ),
                'names': ['Lila', 'Omar', 'Mrs Park', 'Chef Rico', 'Tina', 'Sam'],
                'rows': [
                    ('Builds sandcastles near the water', 'a'),
                    ('Swims with a bright float', 'b'),
                    ('Sits under an umbrella and reads', 'c'),
                    ('Sells ice cream from a cart', 'd'),
                    ('Watches seagulls with binoculars', 'e'),
                    ('Blows a whistle as lifeguard', 'f'),
                    ('Plays with sand on the shore', 'a'),
                    ('Is in the sea with a float', 'b'),
                    ('Works with ice cream', 'd'),
                    ('Keeps swimmers safer', 'f'),
                ],
            },
            'A2': {
                'title': 'Club Staff and Members',
                'passage': (
                    "Coach Dana teaches beginners basic football skills. Member Leo pays the monthly fee at the desk. "
                    "Parent Nora brings her child every Saturday morning. Manager Chris books weekend matches. "
                    "Barista Mia sells healthy snacks in the café. Officer Farid arranges a small council grant."
                ),
                'names': ['Coach Dana', 'Leo', 'Nora', 'Chris', 'Mia', 'Farid'],
                'rows': [
                    ('Teaches beginner football skills', 'a'),
                    ('Pays the monthly fee', 'b'),
                    ('Brings a child on Saturdays', 'c'),
                    ('Books weekend matches', 'd'),
                    ('Sells healthy snacks', 'e'),
                    ('Arranges a council grant', 'f'),
                    ('Works as a coach', 'a'),
                    ('Is a fee-paying member', 'b'),
                    ('Runs the café snacks', 'e'),
                    ('Supports funding for the club', 'f'),
                ],
            },
            'B1': {
                'title': 'Voices on City Cycling',
                'passage': (
                    "Planner Hana Voss designs protected cycle tracks for weekday riders. "
                    "Commuter Eli Park says ignored lanes make him feel unsafe. "
                    "Engineer Sofia Ruiz installs bike-share stations for tourists. "
                    "HR lead Tom Nguyen adds workplace showers and lockers. "
                    "Advocate Mira Cole argues cycling is transport, not only a hobby. "
                    "Researcher Ben Ortiz studies how lanes cut short-trip pollution."
                ),
                'names': [
                    'Hana Voss', 'Eli Park', 'Sofia Ruiz', 'Tom Nguyen', 'Mira Cole', 'Ben Ortiz',
                ],
                'rows': [
                    ('Designs protected cycle tracks', 'a'),
                    ('Feels unsafe when lanes are ignored', 'b'),
                    ('Installs bike-share stations', 'c'),
                    ('Adds showers and lockers at work', 'd'),
                    ('Calls cycling real transport', 'e'),
                    ('Studies pollution cuts from lanes', 'f'),
                    ('Focuses on weekday protected tracks', 'a'),
                    ('Is a worried bike commute', 'b'),
                    ('Supports workplace cycling facilities', 'd'),
                    ('Researches air-quality benefits', 'f'),
                ],
            },
            'B2': {
                'title': 'Figures of the Printing Age',
                'passage': (
                    "Johannes Gutenberg developed movable-type printing in Europe. "
                    "Merchant Klaus Weber funded a workshop for cheaper books. "
                    "Scholar Anna Vogel warned that literacy might weaken old authorities. "
                    "Printer Luca Romano produced pamphlets with faster news. "
                    "Chemist Piotr Kaminski improved ink formulas over years. "
                    "Historian Elise Brandt wrote that mass reading culture had begun."
                ),
                'names': [
                    'Johannes Gutenberg', 'Klaus Weber', 'Anna Vogel',
                    'Luca Romano', 'Piotr Kaminski', 'Elise Brandt',
                ],
                'rows': [
                    ('Developed movable-type printing', 'a'),
                    ('Funded a cheaper-book workshop', 'b'),
                    ('Warned about literacy and authority', 'c'),
                    ('Produced fast-news pamphlets', 'd'),
                    ('Improved ink formulas', 'e'),
                    ('Described mass reading culture', 'f'),
                    ('Invented reusable metal letters approach', 'a'),
                    ('Financed printing work', 'b'),
                    ('Worked on ink chemistry', 'e'),
                    ('Recorded the cultural shift to mass reading', 'f'),
                ],
            },
            'C1': {
                'title': 'Researchers on Sleep',
                'passage': (
                    "Dr Nina Hale links slow-wave sleep to memory consolidation. "
                    "Professor Carl Orth warns lab findings do not always generalise. "
                    "Psychologist Amira Sen studies how chronotypes change outcomes. "
                    "Educator Paul Ruiz argues for later adolescent school starts. "
                    "Pharmacologist Yuki Mori notes aids may miss natural architecture. "
                    "Advisor Lena Frost promotes regular schedules and morning light."
                ),
                'names': [
                    'Dr Nina Hale', 'Professor Carl Orth', 'Amira Sen',
                    'Paul Ruiz', 'Yuki Mori', 'Lena Frost',
                ],
                'rows': [
                    ('Links sleep stages to memory', 'a'),
                    ('Warns labs may not generalise', 'b'),
                    ('Studies chronotype differences', 'c'),
                    ('Argues for later school starts', 'd'),
                    ('Notes limits of sleep medication', 'e'),
                    ('Promotes schedules and light', 'f'),
                    ('Focuses on consolidation research', 'a'),
                    ('Questions lab-to-life transfer', 'b'),
                    ('Works on education timing policy', 'd'),
                    ('Gives public sleep hygiene advice', 'f'),
                ],
            },
            'C2': {
                'title': 'Experts on Hiring Algorithms',
                'passage': (
                    "Dr Omar Reed shows how training data encodes past bias. "
                    "Auditor Priya Shah runs disparate-impact tests on shortlists. "
                    "Engineer Mateo Cruz builds human-review queues for borderline scores. "
                    "Vendor liaison Helen Cho admits error rates are rarely published. "
                    "Regulator Igor Petrov requires explainability statements. "
                    "Ethicist Sara Blum warns optimisation can lock in old workforce patterns."
                ),
                'names': [
                    'Dr Omar Reed', 'Priya Shah', 'Mateo Cruz',
                    'Helen Cho', 'Igor Petrov', 'Sara Blum',
                ],
                'rows': [
                    ('Shows bias in training data', 'a'),
                    ('Runs disparate-impact audits', 'b'),
                    ('Builds human-review queues', 'c'),
                    ('Admits rare error-rate disclosure', 'd'),
                    ('Requires explainability statements', 'e'),
                    ('Warns about locked-in patterns', 'f'),
                    ('Researches encoded hiring history', 'a'),
                    ('Designs borderline case review', 'c'),
                    ('Sets regulatory explainability rules', 'e'),
                    ('Frames the fairness ethics problem', 'f'),
                ],
            },
        }
        np = names_packs.get(level, names_packs['B1'])
        title = np['title']
        passage = np['passage']
        names = np['names']
        questions = [_match(prompt, names, correct, tip_common) for prompt, correct in np['rows']]

    tip = t(
        lang,
        f"{level} daraja · {meta['label_uz']}. Matndan dalil topib javob bering.",
        f"Уровень {level} · {meta['label_ru']}. Ищите доказательство в тексте.",
    )
    return {
        'skill': 'reading',
        'level': level,
        'practice_type': rtype,
        'practice_label': meta['label_uz'] if normalize_ai_lang(lang) == 'uz' else meta['label_ru'],
        'title': title,
        'passage': ensure_min_words(title, passage),
        'instruction': _INSTRUCTION_BY_TYPE.get(rtype, 'Choose the correct option.'),
        'questions': _number_questions(questions),
        'tip': tip,
        'provider_name': 'local',
        'model_name': 'practice-local-v2',
        'content_variant': 1,
    }


def _local_reading(level: str, rtype: str, lang: str, *, variant: int = 0) -> dict:
    variant = int(variant or 0) % READING_VARIANT_COUNT
    if variant == 1:
        return _local_reading_b(level, rtype, lang)
    meta = READING_TYPES[rtype]
    title = {
        'A1': 'A Day at the Park',
        'A2': 'City Libraries Today',
        'B1': 'Urban Green Spaces',
        'B2': 'The Atlantic Telegraph Cable',
        'C1': 'Cognitive Benefits of Bilingualism',
        'C2': 'Epistemic Uncertainty in Climate Models',
    }.get(level, 'Urban Green Spaces')

    passages = {
        'A1': (
            "Many people like parks. Parks have trees and grass. Children play games. "
            "Families sit and talk. Some people walk dogs. Parks help people feel happy. "
            "In big cities, parks are important because there are many buildings. "
            "On Sunday, friends often meet near the playground. Old people sit on benches. "
            "Birds sing in the morning. The park is green in spring and summer. "
            "People bring water and bread for a small picnic. The park closes late at night."
        ),
        'A2': (
            "Public libraries are changing. In the past, people only borrowed books. "
            "Now many libraries offer free Wi-Fi, computers, and study rooms. "
            "Students often come after school to do homework. Some libraries also run "
            "language clubs and reading groups for adults. Because of these services, "
            "libraries remain useful even when people buy e-books. Librarians help visitors "
            "find information quickly. Quiet zones help people focus. In the evening, "
            "some libraries show educational films. Children can join story time on weekends. "
            "Membership is usually free for local residents."
        ),
        'B1': (
            "Urban green spaces have become a major theme in city planning. Research links "
            "access to nature with lower stress and higher wellbeing. However, critics warn "
            "that new parks can raise property prices and push out long-term residents. "
            "Ecologists also argue that connectivity between green areas helps wildlife move "
            "and mix. Funding is another challenge: one-off grants often lead to neglect after "
            "initial planting. Best practice includes ring-fenced budgets and community involvement. "
            "Some cities plant native trees to cut watering costs. Others create pocket parks "
            "on unused corners. Surveys show residents visit parks more when paths are safe "
            "and lighting is good. Planners now measure success by use, not only by size."
        ),
        'B2': (
            "In the mid-nineteenth century, engineers attempted to lay a telegraph cable across "
            "the Atlantic. The central wires were made of copper and covered with gutta-percha. "
            "Because of its weight, the cable had to be shared between two ships. Early attempts "
            "failed when the cable broke, but further research improved thickness and strength. "
            "Later, Cyrus Field formed another company to raise money for a new attempt, which "
            "finally succeeded and transformed long-distance communication. Operators could send "
            "messages in minutes instead of weeks by ship. Investors watched every voyage closely. "
            "The project also pushed better ocean mapping and stronger ships. Although expensive, "
            "the cable changed business, news, and diplomacy between Europe and America."
        ),
        'C1': (
            "A growing body of evidence suggests bilingualism may enhance certain executive "
            "functions, including attentional control and cognitive flexibility. Yet the size "
            "of these effects remains contested: some large-scale studies report only modest "
            "advantages after controlling for socioeconomic status and education. Researchers "
            "also debate whether benefits arise from frequent language switching itself or from "
            "broader lifestyle factors associated with multilingual communities. Longitudinal "
            "designs are still rare, and lab tasks may not mirror everyday communication. "
            "Teachers nevertheless report practical gains in metalinguistic awareness. "
            "Policy makers should avoid overselling bilingualism as a universal cognitive cure "
            "while still supporting early language learning for cultural and economic reasons."
        ),
        'C2': (
            "Climate projections necessarily incorporate epistemic uncertainty arising from "
            "incomplete process understanding, parameterisation choices, and chaotic sensitivity "
            "to initial conditions. Communicating this uncertainty without undermining public "
            "trust poses a distinctive challenge for scientists and policymakers. Some scholars "
            "argue that probabilistic ensembles improve decision quality; others warn that "
            "overly technical presentations can obscure actionable thresholds for adaptation. "
            "Visual summaries and decision-relevant ranges may help non-specialists. "
            "Meanwhile, funding agencies increasingly require uncertainty statements in reports. "
            "The ethical issue is not only accuracy, but whether decision makers can act under "
            "ambiguity without waiting for impossible certainty."
        ),
    }
    passage = passages.get(level, passages['B1'])
    tip_common = t(lang, 'Matndan kalit so‘zlarni toping.', 'Ищите ключевые слова в тексте.')

    if rtype == 'tfng':
        opts = _tfng_options()
        if level == 'A1':
            raw = [
                {'prompt': 'Parks can make people feel happy.', 'correct': 'a'},
                {'prompt': 'Parks have no trees.', 'correct': 'b'},
                {'prompt': 'Some people walk dogs in parks.', 'correct': 'a'},
                {'prompt': 'Children play games in parks.', 'correct': 'a'},
                {'prompt': 'Parks are only for old people.', 'correct': 'b'},
                {'prompt': 'Friends often meet near the playground on Sunday.', 'correct': 'a'},
                {'prompt': 'The park has a large swimming pool.', 'correct': 'c'},
                {'prompt': 'Birds sing in the morning.', 'correct': 'a'},
                {'prompt': 'People never bring food to the park.', 'correct': 'b'},
                {'prompt': 'The park closes late at night.', 'correct': 'a'},
            ]
        elif level == 'A2':
            raw = [
                {'prompt': 'In the past, people only borrowed books from libraries.', 'correct': 'a'},
                {'prompt': 'Libraries never offer Wi-Fi.', 'correct': 'b'},
                {'prompt': 'Students often come after school to do homework.', 'correct': 'a'},
                {'prompt': 'Some libraries run language clubs.', 'correct': 'a'},
                {'prompt': 'Membership is usually free for local residents.', 'correct': 'a'},
                {'prompt': 'Libraries are useless when people buy e-books.', 'correct': 'b'},
                {'prompt': 'All libraries show films every morning.', 'correct': 'c'},
                {'prompt': 'Quiet zones help people focus.', 'correct': 'a'},
                {'prompt': 'Librarians refuse to help visitors.', 'correct': 'b'},
                {'prompt': 'Children can join story time on weekends.', 'correct': 'a'},
            ]
        elif level in ('B2', 'C1', 'C2'):
            raw = _high_level_reading_pack(level, 'tfng', tip_common).get('tfng_raw') or []
        else:
            raw = [
                {'prompt': 'Research links nature access to lower stress.', 'correct': 'a'},
                {'prompt': 'All new parks are free for every resident forever.', 'correct': 'c'},
                {'prompt': 'Community involvement is mentioned as good practice.', 'correct': 'a'},
                {'prompt': 'One-off grants can lead to later neglect.', 'correct': 'a'},
                {'prompt': 'Connectivity between green areas helps wildlife.', 'correct': 'a'},
                {'prompt': 'Critics say new parks can raise property prices.', 'correct': 'a'},
                {'prompt': 'Every city must build a stadium inside each park.', 'correct': 'c'},
                {'prompt': 'Planners measure success only by park size.', 'correct': 'b'},
                {'prompt': 'Safe paths and lighting increase park visits.', 'correct': 'a'},
                {'prompt': 'Native trees can reduce watering costs.', 'correct': 'a'},
            ]
        questions = [
            {'prompt': row['prompt'], 'options': opts, 'correct': row['correct'], 'explanation': tip_common}
            for row in raw
        ]
    elif rtype == 'mcq':
        if level == 'A1':
            questions = [
                _mcq('What do parks have?', ['Trees and grass', 'Airports', 'Factories only', 'No people'], 'a', tip_common),
                _mcq('What do children do in parks?', ['Play games', 'Build ships', 'Fly planes', 'Sell cars'], 'a', tip_common),
                _mcq('Why are parks important in big cities?', ['There are many buildings', 'There is no grass', 'People hate parks', 'Cities have no families'], 'a', tip_common),
                _mcq('Who sits on benches?', ['Old people', 'Pilots only', 'Only dogs', 'Nobody'], 'a', tip_common),
                _mcq('When do friends often meet near the playground?', ['On Sunday', 'Only in winter nights', 'Never', 'At midnight only'], 'a', tip_common),
                _mcq('What do birds do in the morning?', ['Sing', 'Drive cars', 'Close the park', 'Sell bread'], 'a', tip_common),
                _mcq('What do people bring for a picnic?', ['Water and bread', 'Airplanes', 'Computers only', 'Sand'], 'a', tip_common),
                _mcq('When is the park green?', ['In spring and summer', 'Only in December', 'Never', 'Only at night'], 'a', tip_common),
                _mcq('What helps people feel happy?', ['Parks', 'Closed shops', 'No trees', 'Dark rooms only'], 'a', tip_common),
                _mcq('When does the park close?', ['Late at night', 'At sunrise only', 'Never opens', 'At noon forever'], 'a', tip_common),
            ]
        elif level == 'A2':
            questions = [
                _mcq('What did people mainly do in libraries in the past?', ['Borrowed books', 'Bought cars', 'Played football', 'Built houses'], 'a', tip_common),
                _mcq('What free service do many libraries offer now?', ['Wi-Fi', 'Free cars', 'Free flights', 'Free houses'], 'a', tip_common),
                _mcq('Why do students often come after school?', ['To do homework', 'To buy e-books only', 'To close the library', 'To ban Wi-Fi'], 'a', tip_common),
                _mcq('What do some libraries run for adults?', ['Language clubs', 'Airports', 'Car races', 'Ship building'], 'a', tip_common),
                _mcq('Who helps visitors find information?', ['Librarians', 'Pilots', 'Farmers only', 'Bus drivers'], 'a', tip_common),
                _mcq('What do quiet zones help people do?', ['Focus', 'Sing loudly', 'Sell tickets', 'Drive faster'], 'a', tip_common),
                _mcq('What may libraries show in the evening?', ['Educational films', 'Car adverts only', 'Sports betting', 'Nothing'], 'a', tip_common),
                _mcq('What can children join on weekends?', ['Story time', 'Flight school', 'Bank meetings', 'Road works'], 'a', tip_common),
                _mcq('Who usually gets free membership?', ['Local residents', 'Only tourists', 'Only pilots', 'Nobody'], 'a', tip_common),
                _mcq('Why do libraries remain useful with e-books?', ['Because of extra services', 'Because books are banned', 'Because Wi-Fi is illegal', 'Because students never study'], 'a', tip_common),
            ]
        elif level in ('B2', 'C1', 'C2'):
            questions = _high_level_reading_pack(level, 'mcq', tip_common).get('questions') or []
        else:
            questions = [
                _mcq('What is one benefit mentioned in the passage?', ['Lower stress / wellbeing', 'Free cars for residents', 'Closing all libraries', 'Banning pets outdoors'], 'a', tip_common),
                _mcq('What challenge is discussed?', ['Funding / long-term care', 'Too many airports', 'Lack of smartphones', 'Ocean fishing'], 'a', tip_common),
                _mcq('What does best practice include?', ['Community involvement', 'Removing all green areas', 'Ignoring residents', 'One-day festivals only'], 'a', tip_common),
                _mcq('What can new parks do to property prices?', ['Raise them', 'Delete money', 'Ban houses', 'Stop all buses'], 'a', tip_common),
                _mcq('Why does green connectivity matter?', ['It helps wildlife move', 'It closes parks', 'It bans trees', 'It removes paths'], 'a', tip_common),
                _mcq('What often follows one-off grants?', ['Neglect after planting', 'Free cars', 'Airport growth', 'Ocean cables'], 'a', tip_common),
                _mcq('What do ring-fenced budgets support?', ['Long-term park care', 'Closing parks', 'Building malls only', 'Removing lighting'], 'a', tip_common),
                _mcq('Why plant native trees?', ['To cut watering costs', 'To ban visitors', 'To raise noise', 'To remove grass'], 'a', tip_common),
                _mcq('When do residents visit parks more?', ['When paths are safe and lit', 'When parks are locked', 'When there is no grass', 'When wildlife is removed'], 'a', tip_common),
                _mcq('How do planners measure success now?', ['By use, not only size', 'By stadium tickets', 'By car sales', 'By ocean depth'], 'a', tip_common),
            ]
    elif rtype == 'gap_fill':
        if level == 'A1':
            questions = [
                _gap('Parks have trees and ______.', 'grass', tip_common),
                _gap('Children play ______.', 'games', tip_common),
                _gap('Some people walk ______ in parks.', 'dogs', tip_common),
                _gap('Parks help people feel ______.', 'happy', tip_common),
                _gap('Families sit and ______.', 'talk', tip_common),
                _gap('Old people sit on ______.', 'benches', tip_common),
                _gap('Birds sing in the ______.', 'morning', tip_common),
                _gap('Friends often meet near the ______.', 'playground', tip_common),
                _gap('People bring water and ______ for a picnic.', 'bread', tip_common),
                _gap('The park closes late at ______.', 'night', tip_common),
            ]
        elif level == 'A2':
            questions = [
                _gap('Many libraries offer free ______.', 'Wi-Fi|wifi|wi-fi', tip_common),
                _gap('Students often come after school to do ______.', 'homework', tip_common),
                _gap('Libraries remain useful even when people buy ______.', 'e-books|ebooks|e books', tip_common),
                _gap('In the past, people only borrowed ______.', 'books', tip_common),
                _gap('Some libraries run language ______.', 'clubs', tip_common),
                _gap('______ help visitors find information quickly.', 'Librarians|librarians', tip_common),
                _gap('Quiet zones help people ______.', 'focus', tip_common),
                _gap('In the evening, some libraries show educational ______.', 'films', tip_common),
                _gap('Children can join story time on ______.', 'weekends', tip_common),
                _gap('Membership is usually free for local ______.', 'residents', tip_common),
            ]
        elif level in ('B2', 'C1', 'C2'):
            questions = _high_level_reading_pack(level, 'gap_fill', tip_common).get('questions') or []
        else:
            questions = [
                _gap('Research links nature access to lower ______.', 'stress', tip_common),
                _gap('One-off ______ can lead to neglect later.', 'grants', tip_common),
                _gap('Best practice includes community ______.', 'involvement', tip_common),
                _gap('New parks can raise property ______.', 'prices', tip_common),
                _gap('Connectivity between green areas helps ______.', 'wildlife', tip_common),
                _gap('Ring-fenced ______ support long-term care.', 'budgets', tip_common),
                _gap('Some cities plant native ______.', 'trees', tip_common),
                _gap('Others create pocket ______ on unused corners.', 'parks', tip_common),
                _gap('Residents visit more when ______ are safe.', 'paths', tip_common),
                _gap('Planners measure success by ______, not only by size.', 'use', tip_common),
            ]
    elif rtype == 'matching_headings':
        if level == 'A1':
            questions = [
                _heading('What parks have', ['Trees, grass and play', 'Airport runways', 'Ocean cables'], 'i', tip_common),
                _heading('Why parks matter in cities', ['Because of many buildings', 'Because of space travel', 'Only shopping malls'], 'i', tip_common),
                _heading('How parks make people feel', ['Angry and tired', 'Happy', 'Hungry only'], 'ii', tip_common),
                _heading('Who plays games', ['Children', 'Only pilots', 'Ships'], 'i', tip_common),
                _heading('Who walks dogs', ['Some people', 'Nobody', 'Only birds'], 'i', tip_common),
                _heading('Sunday meetings', ['Near the playground', 'In airports', 'On the moon'], 'i', tip_common),
                _heading('Where old people sit', ['On benches', 'In planes', 'Under the sea'], 'i', tip_common),
                _heading('Morning sounds', ['Birds sing', 'Cars invent books', 'Parks close forever'], 'i', tip_common),
                _heading('Picnic items', ['Water and bread', 'Airplanes', 'Computers only'], 'i', tip_common),
                _heading('Park closing time', ['Late at night', 'Never', 'At sunrise only'], 'i', tip_common),
            ]
        elif level == 'A2':
            questions = [
                _heading('How libraries are changing', ['New digital and study services', 'Closing all books forever', 'Building stadiums'], 'i', tip_common),
                _heading('Who often visits after school', ['Pilots', 'Students', 'Farmers only'], 'ii', tip_common),
                _heading('Why libraries stay useful', ['Because of free services', 'Because e-books ban libraries', 'Because cities have no Wi-Fi'], 'i', tip_common),
                _heading('Past library use', ['Borrowing books', 'Buying cars', 'Flying planes'], 'i', tip_common),
                _heading('Adult activities', ['Language clubs and reading groups', 'Ship racing', 'Mining'], 'i', tip_common),
                _heading('Staff role', ['Helping visitors find information', 'Closing Wi-Fi forever', 'Selling houses'], 'i', tip_common),
                _heading('Quiet zones', ['Help people focus', 'Increase noise', 'Ban students'], 'i', tip_common),
                _heading('Evening programmes', ['Educational films', 'Car markets', 'Airport tours'], 'i', tip_common),
                _heading('Weekend for children', ['Story time', 'Bank exams', 'Road works'], 'i', tip_common),
                _heading('Membership', ['Often free for local residents', 'Only for tourists', 'Always paid in gold'], 'i', tip_common),
            ]
        elif level in ('B2', 'C1', 'C2'):
            questions = _high_level_reading_pack(level, 'matching_headings', tip_common).get('questions') or []
        else:
            questions = [
                _heading('Wellbeing and nature nearby', ['Benefits of green access', 'History of telegraph cables', 'Airport construction costs'], 'i', tip_common),
                _heading('Prices rising and residents leaving', ['Marine biology methods', 'Social risk of new parks', 'Cooking traditions'], 'ii', tip_common),
                _heading('Money and long-term care', ['Space travel plans', 'Music festivals', 'Funding and maintenance'], 'iii', tip_common),
                _heading('Wildlife movement', ['Green connectivity', 'Closing all parks', 'Banning trees'], 'i', tip_common),
                _heading('Budgets that last', ['Ring-fenced funding', 'One-day parties', 'Removing paths'], 'i', tip_common),
                _heading('Cheaper watering', ['Native trees', 'Ocean cables', 'Stadium tickets'], 'i', tip_common),
                _heading('Small unused corners', ['Pocket parks', 'Airports', 'Mines'], 'i', tip_common),
                _heading('Safer visits', ['Paths and lighting', 'No grass', 'Locked gates always'], 'i', tip_common),
                _heading('How success is measured', ['By use, not only size', 'By car sales', 'By ocean depth'], 'i', tip_common),
                _heading('City planning theme', ['Urban green spaces', 'Only shopping centres', 'Ship design'], 'i', tip_common),
            ]
    elif rtype == 'matching_endings':
        if level == 'A1':
            endings = [
                'trees and grass.',
                'feel happy.',
                'near the playground.',
                'on benches.',
                'late at night.',
                'in the morning.',
            ]
            questions = [
                _match('Parks have', endings, 'a', tip_common),
                _match('Parks help people', endings, 'b', tip_common),
                _match('On Sunday, friends often meet', endings, 'c', tip_common),
                _match('Old people sit', endings, 'd', tip_common),
                _match('The park closes', endings, 'e', tip_common),
                _match('Birds sing', endings, 'f', tip_common),
                _match('Children play games in places with', ['trees and grass.', 'airports only.', 'no families.'], 'a', tip_common),
                _match('Families sit and talk because parks make them', ['feel happy.', 'buy cars.', 'close shops.'], 'a', tip_common),
                _match('People bring water and bread', ['for a small picnic.', 'to build ships.', 'to fly planes.'], 'a', tip_common),
                _match('In big cities parks matter', ['because there are many buildings.', 'because birds hate parks.', 'because parks never open.'], 'a', tip_common),
            ]
        elif level == 'A2':
            endings = [
                'borrowed books.',
                'free Wi-Fi and study rooms.',
                'do homework.',
                'language clubs.',
                'find information quickly.',
                'local residents.',
            ]
            questions = [
                _match('In the past, people mainly', endings, 'a', tip_common),
                _match('Today many libraries offer', endings, 'b', tip_common),
                _match('Students often come after school to', endings, 'c', tip_common),
                _match('Some libraries also run', endings, 'd', tip_common),
                _match('Librarians help visitors', endings, 'e', tip_common),
                _match('Membership is usually free for', endings, 'f', tip_common),
                _match('Quiet zones help people', ['focus.', 'sing loudly.', 'close libraries.'], 'a', tip_common),
                _match('In the evening some libraries show', ['educational films.', 'car races.', 'airport maps.'], 'a', tip_common),
                _match('Children can join story time', ['on weekends.', 'only at midnight.', 'in airports.'], 'a', tip_common),
                _match('Libraries remain useful even when people buy', ['e-books.', 'houses.', 'planes.'], 'a', tip_common),
            ]
        elif level in ('B2', 'C1', 'C2'):
            questions = _high_level_reading_pack(level, 'matching_endings', tip_common).get('questions') or []
        else:
            endings = [
                'lower stress and higher wellbeing.',
                'raise property prices.',
                'helps wildlife move and mix.',
                'neglect after initial planting.',
                'ring-fenced budgets and community involvement.',
                'use, not only by size.',
            ]
            questions = [
                _match('Research links access to nature with', endings, 'a', tip_common),
                _match('Critics warn that new parks can', endings, 'b', tip_common),
                _match('Connectivity between green areas', endings, 'c', tip_common),
                _match('One-off grants often lead to', endings, 'd', tip_common),
                _match('Best practice includes', endings, 'e', tip_common),
                _match('Planners now measure success by', endings, 'f', tip_common),
                _match('Some cities plant native trees', ['to cut watering costs.', 'to ban visitors.', 'to close parks.'], 'a', tip_common),
                _match('Others create pocket parks', ['on unused corners.', 'inside airports.', 'under the ocean.'], 'a', tip_common),
                _match('Residents visit parks more when', ['paths are safe and lighting is good.', 'parks are locked.', 'wildlife is removed.'], 'a', tip_common),
                _match('Urban green spaces have become', ['a major theme in city planning.', 'a ban on libraries.', 'a type of ocean cable.'], 'a', tip_common),
            ]
    elif rtype == 'matching_names':
        # Odamlar ismlari bo'lgan maxsus matn
        title = {
            'A1': 'People at the Park',
            'A2': 'Library Staff and Visitors',
            'B1': 'Voices on Urban Parks',
            'B2': 'Engineers of the Atlantic Cable',
            'C1': 'Researchers on Bilingualism',
            'C2': 'Experts on Climate Uncertainty',
        }.get(level, 'Voices on Urban Parks')
        if level == 'A1':
            passage = (
                "Anna comes to the park every Sunday. She walks her dog near the playground. "
                "Tom is a child who plays games with friends. Mrs Lee sits on a bench and reads a book. "
                "Mr Karimov brings water and bread for a small picnic with his family. "
                "Sara listens to birds in the morning. The park keeper, Jamshid, closes the park late at night."
            )
            names = ['Anna', 'Tom', 'Mrs Lee', 'Mr Karimov', 'Sara', 'Jamshid']
            questions = [
                _match('Walks a dog near the playground', names, 'a', tip_common),
                _match('Plays games with friends', names, 'b', tip_common),
                _match('Sits on a bench and reads', names, 'c', tip_common),
                _match('Brings water and bread for a picnic', names, 'd', tip_common),
                _match('Listens to birds in the morning', names, 'e', tip_common),
                _match('Closes the park late at night', names, 'f', tip_common),
                _match('Comes to the park every Sunday', names, 'a', tip_common),
                _match('Is a child in the park', names, 'b', tip_common),
                _match('Has a family picnic', names, 'd', tip_common),
                _match('Is the park keeper', names, 'f', tip_common),
            ]
        elif level == 'A2':
            passage = (
                "Ms Rivera is a librarian who helps visitors find information quickly. "
                "Omar is a student who comes after school to do homework in a study room. "
                "Dr Patel runs a language club for adults on Wednesday evenings. "
                "Lina joins story time with children on weekends. "
                "Mr Brown manages quiet zones so people can focus. "
                "Helena organises educational films in the evening."
            )
            names = ['Ms Rivera', 'Omar', 'Dr Patel', 'Lina', 'Mr Brown', 'Helena']
            questions = [
                _match('Helps visitors find information', names, 'a', tip_common),
                _match('Does homework after school', names, 'b', tip_common),
                _match('Runs a language club for adults', names, 'c', tip_common),
                _match('Joins children\'s story time', names, 'd', tip_common),
                _match('Manages quiet zones', names, 'e', tip_common),
                _match('Organises evening educational films', names, 'f', tip_common),
                _match('Works as a librarian', names, 'a', tip_common),
                _match('Is a student visitor', names, 'b', tip_common),
                _match('Supports adult learning clubs', names, 'c', tip_common),
                _match('Helps people focus in quiet areas', names, 'e', tip_common),
            ]
        elif level in ('B2', 'C1', 'C2'):
            pack = _high_level_reading_pack(level, 'matching_names', tip_common)
            title = pack.get('title') or title
            passage = pack.get('passage') or passage
            questions = pack.get('questions') or []
        else:
            passage = (
                "Dr Maya Hassan studies how access to nature lowers stress in cities. "
                "Councillor James Ortega warns that new parks can raise property prices and displace residents. "
                "Ecologist Priya Nair argues that green corridors help wildlife move between parks. "
                "Budget officer Kenji Sato says one-off grants often lead to neglect after planting. "
                "Planner Sofia Almeida promotes ring-fenced budgets and community involvement. "
                "Engineer Luis Romero designs safer paths and lighting to increase evening visits."
            )
            names = [
                'Dr Maya Hassan',
                'Councillor James Ortega',
                'Ecologist Priya Nair',
                'Budget officer Kenji Sato',
                'Planner Sofia Almeida',
                'Engineer Luis Romero',
            ]
            questions = [
                _match('Links nature access to lower stress', names, 'a', tip_common),
                _match('Warns about rising property prices', names, 'b', tip_common),
                _match('Supports wildlife connectivity', names, 'c', tip_common),
                _match('Criticises one-off planting grants', names, 'd', tip_common),
                _match('Promotes ring-fenced budgets', names, 'e', tip_common),
                _match('Designs safer paths and lighting', names, 'f', tip_common),
                _match('Focuses on resident wellbeing research', names, 'a', tip_common),
                _match('Raises social concerns about new parks', names, 'b', tip_common),
                _match('Wants community involvement in parks', names, 'e', tip_common),
                _match('Works on evening visit safety', names, 'f', tip_common),
            ]
    else:
        # fallback — headings
        questions = [
            _heading('Main idea', ['Urban green spaces', 'Ocean fishing', 'Airport design'], 'i', tip_common),
            _heading('Extra detail', ['Wellbeing benefits', 'Space travel', 'Mining'], 'i', tip_common),
            _heading('Challenge', ['Funding', 'Cooking', 'Fashion'], 'i', tip_common),
            _heading('Wildlife', ['Connectivity', 'Airports', 'Stadiums'], 'i', tip_common),
            _heading('Practice', ['Community involvement', 'Closing parks', 'Banning trees'], 'i', tip_common),
            _heading('Trees', ['Native species', 'Ocean cables', 'Car sales'], 'i', tip_common),
            _heading('Small spaces', ['Pocket parks', 'Mines', 'Ships'], 'i', tip_common),
            _heading('Visits', ['Safe paths and lighting', 'No grass', 'Locked gates'], 'i', tip_common),
            _heading('Success', ['Measured by use', 'Measured by tickets', 'Measured by depth'], 'i', tip_common),
            _heading('Theme', ['City planning', 'Ship design', 'Fashion weeks'], 'i', tip_common),
        ]

    tip = t(
        lang,
        f"{level} daraja · {meta['label_uz']}. Matndan dalil topib javob bering.",
        f"Уровень {level} · {meta['label_ru']}. Ищите доказательство в тексте.",
    )
    return {
        'skill': 'reading',
        'level': level,
        'practice_type': rtype,
        'practice_label': meta['label_uz'] if normalize_ai_lang(lang) == 'uz' else meta['label_ru'],
        'title': title,
        'passage': ensure_min_words(title, passage),
        'instruction': _INSTRUCTION_BY_TYPE.get(rtype, 'Choose the correct option.'),
        'questions': _number_questions(questions),
        'tip': tip,
        'provider_name': 'local',
        'model_name': 'practice-local-v1',
        'content_variant': 0,
    }


def _local_writing(level: str, focus: str, lang: str, *, variant: int = 0) -> dict:
    meta = WRITING_FOCUSES[focus]
    variant = int(variant or 0) % READING_VARIANT_COUNT
    tasks_a = {
        'A1': 'Write about your favourite place. Say where it is and why you like it. (80–100 words)',
        'A2': 'Some people prefer living in a city. Do you agree or disagree? Give reasons. (120–150 words)',
        'B1': 'Many students use smartphones for study. Discuss the advantages and disadvantages. (150–180 words)',
        'B2': 'Some people believe public parks improve city life more than shopping centres. Discuss both views and give your opinion. (220–260 words)',
        'C1': 'Governments should invest more in public libraries than in new sports stadiums. To what extent do you agree or disagree? (250–280 words)',
        'C2': 'In an age of digital media, is the traditional essay still the best way to assess academic writing ability? Discuss. (280–320 words)',
    }
    tasks_b = {
        'A1': 'Write about your favourite food. Say what it is and when you eat it. (80–100 words)',
        'A2': 'Some students like online classes. Do you agree or disagree? Give reasons. (120–150 words)',
        'B1': 'More people work from home. Discuss the advantages and disadvantages. (150–180 words)',
        'B2': 'Some cities invest in bike lanes instead of new car parks. Discuss both views and give your opinion. (220–260 words)',
        'C1': 'Universities should teach digital literacy as seriously as traditional academic writing. To what extent do you agree or disagree? (250–280 words)',
        'C2': 'Should high-stakes hiring decisions ever be left to algorithms alone? Discuss. (280–320 words)',
    }
    samples_a = {
        'A1': (
            "My favourite place is a small park near my home. There are trees and a playground. "
            "I go there with my friends on Sunday. We walk and talk. I like this park because it is quiet and green."
        ),
        'A2': (
            "I agree that city life can be good. Cities have schools, hospitals, and jobs. "
            "However, cities are often noisy and expensive. For me, the best choice depends on work and family. "
            "If someone needs a job, a city is useful. If they want quiet, a small town is better."
        ),
        'B1': (
            "Smartphones help students find information quickly and practise languages with apps. "
            "On the other hand, they can distract learners during class and reduce deep reading. "
            "In my view, smartphones are useful when teachers set clear rules. Students should use them as tools, "
            "not as entertainment during study time."
        ),
        'B2': (
            "Public parks provide free space for exercise, rest, and community events, which shopping centres rarely offer. "
            "Supporters of malls argue they create jobs and convenience. Nevertheless, parks improve wellbeing and "
            "air quality in dense neighbourhoods. Overall, I believe parks deliver broader social benefits, "
            "although cities still need commercial areas for daily needs."
        ),
        'C1': (
            "Libraries cultivate literacy, lifelong learning, and equal access to knowledge, whereas stadiums mainly "
            "serve entertainment and seasonal events. While sports infrastructure can boost civic pride, the educational "
            "return on libraries is more inclusive and continuous. Therefore, I largely agree that governments should "
            "prioritise libraries, provided basic sports facilities remain available in schools and local clubs."
        ),
        'C2': (
            "The traditional essay still trains argumentation, synthesis, and stylistic control—skills that short "
            "digital posts rarely demand. Yet exclusive reliance on timed essays may undervalue multimodal literacy "
            "and collaborative drafting common in professional contexts. A balanced assessment regime would retain "
            "the essay as a core instrument while incorporating portfolios and research tasks that better mirror "
            "authentic academic work."
        ),
    }
    samples_b = {
        'A1': (
            "My favourite food is plov. My mother cooks it on weekends. It has rice, meat, and carrots. "
            "I eat it with my family. I like it because it is warm and delicious."
        ),
        'A2': (
            "Online classes are useful because students can study from home and save travel time. "
            "However, some learners lose focus without a classroom. In my opinion, online learning works best "
            "when teachers check progress every week."
        ),
        'B1': (
            "Working from home saves commuting time and can improve focus for quiet tasks. "
            "On the other hand, people may feel isolated and miss team discussions. "
            "I think a hybrid model is best: office days for meetings and home days for deep work."
        ),
        'B2': (
            "Bike lanes make short trips cleaner and often faster in congested centres, while car parks support drivers "
            "who need vehicles for work. Still, limited urban space means cities must prioritise high-capacity options. "
            "Overall I favour protected cycling networks, with some parking retained near hospitals and logistics hubs."
        ),
        'C1': (
            "Digital literacy underpins research, collaboration, and source evaluation in modern degrees. "
            "Traditional essays remain valuable for argumentation, yet ignoring digital skills leaves graduates "
            "underprepared. I therefore agree that universities should treat both as core competencies."
        ),
        'C2': (
            "Algorithms can rank applicants quickly, but training data often encodes historical bias. "
            "Leaving final decisions to opaque scores risks unfair exclusion. High-stakes hiring should combine "
            "audited tools with meaningful human review rather than full automation."
        ),
    }
    tasks = tasks_b if variant == 1 else tasks_a
    samples = samples_b if variant == 1 else samples_a

    band = 'A' if level in ('A1', 'A2') else ('C' if level in ('C1', 'C2') else 'B')
    # Har fokus uchun daraja bandiga mos mashqlar (A / B / C)
    focus_exercises = {
        'lexical_resource': {
            'A': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Better word for "good": "a good park" →',
                    'correct': 'a nice park|a lovely park|a pleasant park',
                    'hint': t(lang, 'Oddiy sinonim.', 'Простой синоним.'),
                },
                {
                    'id': 2, 'kind': 'gap',
                    'prompt': 'Collocation: ______ a decision (make / do)',
                    'correct': 'make',
                    'hint': t(lang, 'make a decision', 'make a decision'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Upgrade: "many people like parks" →',
                    'correct': 'many people enjoy parks|a lot of people like parks',
                    'hint': t(lang, 'Yaxshiroq fe’l.', 'Лучший глагол.'),
                },
            ],
            'B': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Replace the basic word with a stronger academic synonym: "good idea" →',
                    'correct': 'sound approach|valuable approach|effective strategy',
                    'hint': t(lang, 'Academic synonym tanlang.', 'Выберите академический синоним.'),
                },
                {
                    'id': 2, 'kind': 'gap',
                    'prompt': 'Collocation: make a ______ decision (careful / carefully)',
                    'correct': 'careful',
                    'hint': t(lang, 'Adjective + noun.', 'Adjective + noun.'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Upgrade: "a lot of people think" →',
                    'correct': 'many people believe|a large number of people argue|numerous commentators suggest',
                    'hint': t(lang, 'Formalroq ibora yozing.', 'Напишите более формальную фразу.'),
                },
            ],
            'C': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Upgrade hedging: "Parks are always good for everyone" →',
                    'correct': 'Parks tend to benefit most urban residents|Parks generally enhance wellbeing for many city dwellers',
                    'hint': t(lang, 'Aniqroq + ehtiyotkor ibora.', 'Точнее и осторожнее.'),
                },
                {
                    'id': 2, 'kind': 'gap',
                    'prompt': 'Academic collocation: ______ evidence (compelling / compel)',
                    'correct': 'compelling',
                    'hint': t(lang, 'Adjective + noun.', 'Adjective + noun.'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Nominalise: "People use libraries more when cities invest" →',
                    'correct': 'Greater municipal investment leads to higher library use|Increased city investment results in greater library usage',
                    'hint': t(lang, 'Nominalisation.', 'Номинализация.'),
                },
            ],
        },
        'grammar': {
            'A': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Correct: "She go to the park every Sunday."',
                    'correct': 'She goes to the park every Sunday.',
                    'hint': t(lang, 'Present simple -s.', 'Present simple -s.'),
                },
                {
                    'id': 2, 'kind': 'gap',
                    'prompt': 'There ______ many trees in the park. (is / are)',
                    'correct': 'are',
                    'hint': t(lang, 'There is / are', 'There is / are'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Fix: "I am like parks."',
                    'correct': 'I like parks.|I am fond of parks.',
                    'hint': t(lang, 'like = fe’l.', 'like = глагол.'),
                },
            ],
            'B': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Correct the sentence: "People is happy in parks."',
                    'correct': 'People are happy in parks.',
                    'hint': t(lang, 'Subject–verb agreement.', 'Согласование подлежащего и сказуемого.'),
                },
                {
                    'id': 2, 'kind': 'gap',
                    'prompt': 'If cities ______ more parks, residents would feel healthier. (build)',
                    'correct': 'built',
                    'hint': t(lang, 'Second conditional.', 'Second conditional.'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Fix article use: "Park is important for the children."',
                    'correct': 'Parks are important for children.|A park is important for children.',
                    'hint': t(lang, 'Article / plural.', 'Артикль / множественное число.'),
                },
            ],
            'C': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Fix: "Despite of the cost, the cable succeeded."',
                    'correct': 'Despite the cost, the cable succeeded.|In spite of the cost, the cable succeeded.',
                    'hint': t(lang, 'despite + noun (of yo‘q).', 'despite + noun.'),
                },
                {
                    'id': 2, 'kind': 'gap',
                    'prompt': 'Had the ensemble ______ clearer visuals, policymakers might have acted sooner. (include)',
                    'correct': 'included',
                    'hint': t(lang, 'Inversion / 3rd conditional feel.', 'Инверсия.'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Reduce relative clause: "Libraries which are funded by cities remain free."',
                    'correct': 'City-funded libraries remain free.|Libraries funded by cities remain free.',
                    'hint': t(lang, 'Reduced relative.', 'Сокращённый relative.'),
                },
            ],
        },
        'paraphrasing': {
            'A': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "I like the park."',
                    'correct': 'I enjoy the park.|The park is my favourite place.',
                    'hint': t(lang, 'Boshqa so‘zlar.', 'Другие слова.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "Students come after school."',
                    'correct': 'Learners arrive when school finishes.|Pupils visit after classes.',
                    'hint': t(lang, 'Same idea.', 'Тот же смысл.'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "Libraries are useful."',
                    'correct': 'Libraries help people.|Libraries are helpful places.',
                    'hint': t(lang, 'Oddiy paraphrasing.', 'Простой paraphrase.'),
                },
            ],
            'B': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "Parks help people relax."',
                    'correct': 'Green spaces enable people to unwind.|Parks allow residents to reduce stress.',
                    'hint': t(lang, 'Same meaning, new words.', 'Тот же смысл, другие слова.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "Many students use phones in class."',
                    'correct': 'A large number of learners rely on mobile devices during lessons.',
                    'hint': t(lang, 'Change structure + vocabulary.', 'Измените структуру и лексику.'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "I think libraries are useful."',
                    'correct': 'In my view, libraries provide significant educational value.',
                    'hint': t(lang, 'More academic tone.', 'Более академичный тон.'),
                },
            ],
            'C': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "Bilingualism may improve attention."',
                    'correct': 'Speaking two languages can enhance attentional control.|Bilingual experience is linked to gains in executive attention.',
                    'hint': t(lang, 'Academic paraphrase.', 'Академический paraphrase.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "Uncertainty makes decisions hard."',
                    'correct': 'Epistemic uncertainty complicates timely policy choices.|Incomplete certainty hinders decisive action.',
                    'hint': t(lang, 'Keep meaning, raise register.', 'Сохраните смысл, повысьте регистр.'),
                },
                {
                    'id': 3, 'kind': 'rewrite',
                    'prompt': 'Paraphrase: "Essays still matter in universities."',
                    'correct': 'The traditional essay remains a core tool for assessing academic writing.|Timed essays continue to play a central role in higher education assessment.',
                    'hint': t(lang, 'Formal rewording.', 'Формальная перефразировка.'),
                },
            ],
        },
        'sentence_construction': {
            'A': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Join with and: "I walk. I talk."',
                    'correct': 'I walk and talk.|I walk and I talk.',
                    'hint': t(lang, 'and bilan ulang.', 'Соедините and.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Use because: "I like parks. They are green."',
                    'correct': 'I like parks because they are green.',
                    'hint': t(lang, 'because', 'because'),
                },
                {
                    'id': 3, 'kind': 'gap',
                    'prompt': 'I go to the library ______ I can study. (so / because)',
                    'correct': 'so|because',
                    'hint': t(lang, 'Maqsad / sabab.', 'Цель / причина.'),
                },
            ],
            'B': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Combine with although: "Parks are free. Malls create jobs."',
                    'correct': 'Although malls create jobs, parks are free.|Although parks are free, malls create jobs.',
                    'hint': t(lang, 'Complex sentence.', 'Сложное предложение.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Use which: "Libraries offer Wi-Fi. This helps students."',
                    'correct': 'Libraries offer Wi-Fi, which helps students.',
                    'hint': t(lang, 'Relative clause.', 'Relative clause.'),
                },
                {
                    'id': 3, 'kind': 'gap',
                    'prompt': 'Not only do parks improve air quality, ______ they also support community life.',
                    'correct': 'but',
                    'hint': t(lang, 'not only … but also', 'not only … but also'),
                },
            ],
            'C': [
                {
                    'id': 1, 'kind': 'rewrite',
                    'prompt': 'Combine with whereas: "Ensembles clarify risk. Jargon obscures thresholds."',
                    'correct': 'Whereas ensembles clarify risk, jargon obscures actionable thresholds.|Ensembles clarify risk, whereas jargon obscures actionable thresholds.',
                    'hint': t(lang, 'whereas contrast.', 'whereas.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Use participle clause: "Libraries receive stable funding. They serve more learners."',
                    'correct': 'Receiving stable funding, libraries serve more learners.|Libraries, receiving stable funding, serve more learners.',
                    'hint': t(lang, 'Participle clause.', 'Причастный оборот.'),
                },
                {
                    'id': 3, 'kind': 'gap',
                    'prompt': '______ the essay remains useful, multimodal tasks better mirror authentic work.',
                    'correct': 'While|Whilst|Although',
                    'hint': t(lang, 'Concession linker.', 'Уступительный союз.'),
                },
            ],
        },
        'support_sentences': {
            'A': [
                {
                    'id': 1, 'kind': 'mcq',
                    'prompt': 'Best support for: "Parks are good for children."',
                    'options': [
                        {'letter': 'a', 'text': 'Children can play games there.'},
                        {'letter': 'b', 'text': 'Airplanes are fast.'},
                        {'letter': 'c', 'text': 'My phone is new.'},
                    ],
                    'correct': 'a',
                    'hint': t(lang, 'Mavzuga bog‘liq misol.', 'Связанный пример.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Add support after: "Libraries help students."',
                    'correct': 'They have quiet rooms for homework.|Students can use free Wi-Fi there.',
                    'hint': t(lang, 'Oddiy detail.', 'Простая деталь.'),
                },
                {
                    'id': 3, 'kind': 'mcq',
                    'prompt': 'Which does NOT support parks?',
                    'options': [
                        {'letter': 'a', 'text': 'People feel happy in green places.'},
                        {'letter': 'b', 'text': 'Families meet near the playground.'},
                        {'letter': 'c', 'text': 'Ships cross the ocean.'},
                    ],
                    'correct': 'c',
                    'hint': t(lang, 'Mavzuga aloqasi yo‘q.', 'Не по теме.'),
                },
            ],
            'B': [
                {
                    'id': 1, 'kind': 'mcq',
                    'prompt': 'Best supporting sentence for: "Parks improve wellbeing."',
                    'options': [
                        {'letter': 'a', 'text': 'For example, walking in green areas can lower stress levels.'},
                        {'letter': 'b', 'text': 'My uncle owns a car.'},
                        {'letter': 'c', 'text': 'Football is a sport.'},
                    ],
                    'correct': 'a',
                    'hint': t(lang, 'Example that proves the claim.', 'Пример, подтверждающий тезис.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Add a support sentence after: "Libraries help students."',
                    'correct': 'They provide quiet study rooms and free internet access.',
                    'hint': t(lang, 'Concrete detail.', 'Конкретная деталь.'),
                },
                {
                    'id': 3, 'kind': 'mcq',
                    'prompt': 'Which sentence does NOT support city parks?',
                    'options': [
                        {'letter': 'a', 'text': 'Children can play safely outdoors.'},
                        {'letter': 'b', 'text': 'Green areas cool dense neighbourhoods.'},
                        {'letter': 'c', 'text': 'Airports need longer runways.'},
                    ],
                    'correct': 'c',
                    'hint': t(lang, 'Irrelevant detail.', 'Нерелевантная деталь.'),
                },
            ],
            'C': [
                {
                    'id': 1, 'kind': 'mcq',
                    'prompt': 'Best support for: "Uncertainty statements improve trust."',
                    'options': [
                        {'letter': 'a', 'text': 'Clear ranges help non-specialists judge actionable thresholds.'},
                        {'letter': 'b', 'text': 'Copper cables were heavy.'},
                        {'letter': 'c', 'text': 'Children like swings.'},
                    ],
                    'correct': 'a',
                    'hint': t(lang, 'Claimga bog‘liq dalil.', 'Доказательство к тезису.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Support: "Longitudinal designs are still rare."',
                    'correct': 'Most studies remain cross-sectional and cannot track change over years.|Few projects follow the same bilingual cohort across time.',
                    'hint': t(lang, 'Izoh + misol.', 'Пояснение + пример.'),
                },
                {
                    'id': 3, 'kind': 'mcq',
                    'prompt': 'Which does NOT support investing in libraries?',
                    'options': [
                        {'letter': 'a', 'text': 'They expand equal access to knowledge.'},
                        {'letter': 'b', 'text': 'They support lifelong learning.'},
                        {'letter': 'c', 'text': 'Stadium concerts sell more merchandise.'},
                    ],
                    'correct': 'c',
                    'hint': t(lang, 'Irrelevant.', 'Нерелевантно.'),
                },
            ],
        },
        'argument_development': {
            'A': [
                {
                    'id': 1, 'kind': 'mcq',
                    'prompt': 'Best main idea for an essay about parks:',
                    'options': [
                        {'letter': 'a', 'text': 'Parks help people feel happy and healthy.'},
                        {'letter': 'b', 'text': 'I ate bread.'},
                        {'letter': 'c', 'text': 'Buses are yellow.'},
                    ],
                    'correct': 'a',
                    'hint': t(lang, 'Asosiy g‘oya.', 'Главная идея.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Improve: "Parks are good because they are good."',
                    'correct': 'Parks are good because people can walk and play there.',
                    'hint': t(lang, 'Sabab yozing.', 'Напишите причину.'),
                },
                {
                    'id': 3, 'kind': 'gap',
                    'prompt': 'First, parks are green. ______, they are quiet.',
                    'correct': 'Second|Also|Next',
                    'hint': t(lang, 'Ro‘yxat bog‘lovchisi.', 'Слово-связка.'),
                },
            ],
            'B': [
                {
                    'id': 1, 'kind': 'mcq',
                    'prompt': 'Strongest thesis for a discuss-both-views essay on parks vs malls:',
                    'options': [
                        {'letter': 'a', 'text': 'Parks are nice.'},
                        {'letter': 'b', 'text': 'While malls offer convenience and jobs, parks deliver broader public health benefits; overall I favour parks.'},
                        {'letter': 'c', 'text': 'I went shopping yesterday.'},
                    ],
                    'correct': 'b',
                    'hint': t(lang, 'Clear position + both sides.', 'Чёткая позиция + обе стороны.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Improve this weak argument: "Parks are good because they are good."',
                    'correct': 'Parks are beneficial because they provide free recreation and improve air quality.',
                    'hint': t(lang, 'Reason + concrete benefit.', 'Причина + конкретная польза.'),
                },
                {
                    'id': 3, 'kind': 'gap',
                    'prompt': 'Linking: Parks improve wellbeing; ______, malls mainly serve commercial interests.',
                    'correct': 'by contrast|in contrast|however',
                    'hint': t(lang, 'Contrast linker.', 'Контрастный союз.'),
                },
            ],
            'C': [
                {
                    'id': 1, 'kind': 'mcq',
                    'prompt': 'Strongest thesis on essays vs multimodal assessment:',
                    'options': [
                        {'letter': 'a', 'text': 'Essays are old.'},
                        {'letter': 'b', 'text': 'Although essays train argumentation, assessment should also include portfolios that mirror authentic academic work.'},
                        {'letter': 'c', 'text': 'I like videos.'},
                    ],
                    'correct': 'b',
                    'hint': t(lang, 'Nuanced thesis.', 'Нюансированный тезис.'),
                },
                {
                    'id': 2, 'kind': 'rewrite',
                    'prompt': 'Strengthen: "Uncertainty is bad so ignore it."',
                    'correct': 'Uncertainty should be communicated clearly so decision makers can act without demanding impossible certainty.',
                    'hint': t(lang, 'Sabab + yechim.', 'Причина + решение.'),
                },
                {
                    'id': 3, 'kind': 'gap',
                    'prompt': 'Libraries build literacy; ______, stadiums mainly deliver seasonal entertainment.',
                    'correct': 'by contrast|conversely|in contrast',
                    'hint': t(lang, 'Contrast.', 'Контраст.'),
                },
            ],
        },
    }

    bank = focus_exercises.get(focus, focus_exercises['lexical_resource'])
    exercises = bank.get(band, bank.get('B', []))
    tip = t(
        lang,
        f"{level} · {meta['label_uz']}. Avval taskni o‘qing, keyin namuna va mashqlarni bajaring.",
        f"{level} · {meta['label_ru']}. Сначала прочитайте задание, затем образец и упражнения.",
    )
    return {
        'skill': 'writing',
        'level': level,
        'practice_type': focus,
        'practice_label': meta['label_uz'] if normalize_ai_lang(lang) == 'uz' else meta['label_ru'],
        'task': tasks.get(level, tasks['B1']),
        'sample_essay': samples.get(level, samples['B1']),
        'exercises': exercises,
        'tip': tip,
        'provider_name': 'local',
        'model_name': 'practice-local-v1',
        'content_variant': variant,
    }


def _norm_option_letter(raw, *, rtype: str = 'mcq', index: int = 0) -> str:
    """Harf/roman raqamni saqlaydi — [:1] bilan ii→i buzilmasin."""
    s = str(raw or '').strip().lower().rstrip('.)]')
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1].strip()
    if s in _ROMAN_LETTERS:
        return s
    if len(s) == 1 and s in _ALPHA_LETTERS:
        return s
    m = re.match(r'^([a-h]|ix|iv|v?i{0,3}|x)\b', s)
    if m:
        return m.group(1)
    if rtype == 'matching_headings':
        return _ROMAN_LETTERS[index] if index < len(_ROMAN_LETTERS) else _ROMAN_LETTERS[0]
    return _ALPHA_LETTERS[index] if index < len(_ALPHA_LETTERS) else 'a'


def _option_texts_upper(opts) -> set:
    out = set()
    if not isinstance(opts, list):
        return out
    for o in opts:
        if isinstance(o, dict):
            text = str(o.get('text') or '').strip().upper()
        else:
            text = str(o or '').strip().upper()
        if text:
            out.add(text)
    return out


def _looks_like_tfng_options(opts) -> bool:
    texts = _option_texts_upper(opts)
    if not texts:
        return False
    tfng = {'TRUE', 'FALSE', 'NOT GIVEN', 'T', 'F', 'NG', 'YES', 'NO'}
    return len(texts & tfng) >= 2


def _questions_fit_rtype(questions: list, rtype: str) -> bool:
    """Gemini ba'zan har tip uchun TFNG qaytaradi — shaklni tekshiramiz."""
    if not questions:
        return False
    sample = [q for q in questions[:6] if isinstance(q, dict)]
    if not sample:
        return False
    need = max(1, (len(sample) + 1) // 2)

    if rtype == 'gap_fill':
        ok = 0
        for q in sample:
            opts = q.get('options') or []
            correct = str(q.get('correct') or '').strip()
            prompt = str(q.get('prompt') or '')
            if opts and _looks_like_tfng_options(opts):
                continue
            if not opts and correct and correct.lower() not in ('a', 'b', 'c'):
                ok += 1
            elif '_____' in prompt or '______' in prompt or '___' in prompt:
                ok += 1
        return ok >= need

    if rtype == 'tfng':
        return sum(1 for q in sample if _looks_like_tfng_options(q.get('options') or [])) >= need

    # Boshqa tiplar: TRUE/FALSE/NOT GIVEN bo'lmasin
    if sum(1 for q in sample if _looks_like_tfng_options(q.get('options') or [])) >= need:
        return False

    if rtype == 'mcq':
        return sum(
            1 for q in sample
            if len(q.get('options') or []) >= 3 and not _looks_like_tfng_options(q.get('options') or [])
        ) >= need

    if rtype == 'matching_headings':
        ok = 0
        for q in sample:
            opts = q.get('options') or []
            if len(opts) < 2 or _looks_like_tfng_options(opts):
                continue
            letters = {
                str(o.get('letter') or '').strip().lower()
                for o in opts if isinstance(o, dict)
            }
            # Roman harflar yoki heading matnlari (TFNG emas)
            if letters & set(_ROMAN_LETTERS):
                ok += 1
            elif len(opts) >= 3 and not _looks_like_tfng_options(opts):
                ok += 1
        return ok >= need

    if rtype in ('matching_endings', 'matching_names'):
        return sum(
            1 for q in sample
            if len(q.get('options') or []) >= 3 and not _looks_like_tfng_options(q.get('options') or [])
        ) >= need

    return True


_INSTRUCTION_BY_TYPE = {
    'tfng': (
        'Do the following statements agree with the information in the Reading Passage? '
        'Write TRUE if the statement agrees with the information, FALSE if the statement contradicts '
        'the information, or NOT GIVEN if there is no information on this.'
    ),
    'mcq': 'Choose the correct letter, A, B, C or D.',
    'gap_fill': (
        'Complete the sentences below. Choose NO MORE THAN TWO WORDS from the passage for each answer.'
    ),
    'matching_headings': (
        'Choose the correct heading for each question from the list of headings. '
        'There are more headings than you need.'
    ),
    'matching_endings': 'Complete each sentence with the correct ending from the list below.',
    'matching_names': (
        'Match each statement with the correct person from the list below. '
        'You may use any letter more than once.'
    ),
}


def _normalize_reading_payload(data: dict, *, level: str, rtype: str, lang: str) -> dict:
    meta = READING_TYPES[rtype]
    questions = data.get('questions') if isinstance(data.get('questions'), list) else []
    out_q = []
    for i, row in enumerate(questions[:READING_QUESTION_COUNT], start=1):
        if not isinstance(row, dict):
            continue
        opts = row.get('options') or []
        clean_opts = []
        if isinstance(opts, list):
            for idx, o in enumerate(opts[:8]):
                if isinstance(o, dict):
                    letter = _norm_option_letter(o.get('letter'), rtype=rtype, index=idx)
                    text = str(o.get('text') or '').strip()[:200]
                    if text:
                        clean_opts.append({'letter': letter, 'text': text})
                elif o:
                    text = str(o).strip()[:200]
                    if text:
                        clean_opts.append({
                            'letter': _norm_option_letter('', rtype=rtype, index=idx),
                            'text': text,
                        })
        correct_raw = str(row.get('correct') or row.get('answer') or '').strip().lower()[:80]
        if rtype == 'gap_fill':
            correct = correct_raw
        elif rtype == 'matching_headings':
            correct = _norm_option_letter(correct_raw, rtype=rtype, index=0) if correct_raw else ''
            # agar correct to'liq roman bo'lsa saqlaymiz
            if correct_raw in _ROMAN_LETTERS:
                correct = correct_raw
            elif correct_raw and correct_raw[0] in _ALPHA_LETTERS and correct_raw not in _ROMAN_LETTERS:
                correct = correct_raw[:1]
        else:
            correct = correct_raw[:1] if correct_raw and correct_raw[0] in _ALPHA_LETTERS else correct_raw
        out_q.append({
            'id': int(row.get('id') or i),
            'prompt': str(row.get('prompt') or row.get('question') or '').strip()[:500],
            'options': clean_opts if rtype != 'gap_fill' else [],
            'correct': correct,
            'explanation': str(row.get('explanation') or '').strip()[:400],
        })

    # Yetarli emas YOKI tipga mos emas → to'liq local (aralash TFNG+MCQ qoldirmaymiz)
    if len(out_q) < max(7, READING_QUESTION_COUNT - 3) or not _questions_fit_rtype(out_q, rtype):
        return _local_reading(level, rtype, lang)

    # AI ba'zan 7–9 ta qaytaradi — local bilan 10 tagacha to'ldiramiz (shu tipdan)
    if len(out_q) < READING_QUESTION_COUNT:
        local_qs = _local_reading(level, rtype, lang).get('questions') or []
        seen = {str(q.get('prompt') or '').strip().lower() for q in out_q}
        for row in local_qs:
            if len(out_q) >= READING_QUESTION_COUNT:
                break
            prompt = str(row.get('prompt') or '').strip()
            if not prompt or prompt.lower() in seen:
                continue
            seen.add(prompt.lower())
            item = dict(row)
            item['id'] = len(out_q) + 1
            out_q.append(item)

    instruction = _INSTRUCTION_BY_TYPE.get(
        rtype,
        str(data.get('instruction') or 'Choose the correct option.').strip()[:400],
    )

    return {
        'skill': 'reading',
        'level': level,
        'practice_type': rtype,
        'practice_label': meta['label_uz'] if normalize_ai_lang(lang) == 'uz' else meta['label_ru'],
        'title': str(data.get('title') or 'Reading Practice').strip()[:160],
        'passage': str(data.get('passage') or data.get('text') or '').strip()[:20000],
        'instruction': instruction,
        'questions': out_q,
        'tip': str(data.get('tip') or '').strip()[:300],
        'provider_name': data.get('provider_name') or 'gemini',
        'model_name': data.get('model_name') or '',
    }


def _normalize_writing_payload(data: dict, *, level: str, focus: str, lang: str) -> dict:
    meta = WRITING_FOCUSES[focus]
    exercises = data.get('exercises') if isinstance(data.get('exercises'), list) else []
    out_ex = []
    for i, row in enumerate(exercises[:8], start=1):
        if not isinstance(row, dict):
            continue
        opts = []
        raw_opts = row.get('options') or []
        if isinstance(raw_opts, list):
            for o in raw_opts[:6]:
                if isinstance(o, dict):
                    opts.append({
                        'letter': str(o.get('letter') or '').strip().lower()[:1],
                        'text': str(o.get('text') or '').strip()[:220],
                    })
        out_ex.append({
            'id': int(row.get('id') or i),
            'kind': str(row.get('kind') or 'rewrite').strip().lower()[:20],
            'prompt': str(row.get('prompt') or '').strip()[:500],
            'options': [o for o in opts if o.get('text')],
            'correct': str(row.get('correct') or row.get('answer') or '').strip()[:200],
            'hint': str(row.get('hint') or row.get('explanation') or '').strip()[:300],
        })
    if len(out_ex) < 2 or not str(data.get('task') or '').strip():
        return _local_writing(level, focus, lang)
    return {
        'skill': 'writing',
        'level': level,
        'practice_type': focus,
        'practice_label': meta['label_uz'] if normalize_ai_lang(lang) == 'uz' else meta['label_ru'],
        'task': str(data.get('task') or data.get('prompt') or '').strip()[:800],
        'sample_essay': str(data.get('sample_essay') or data.get('essay') or '').strip()[:5000],
        'exercises': out_ex,
        'tip': str(data.get('tip') or '').strip()[:300],
        'provider_name': data.get('provider_name') or 'gemini',
        'model_name': data.get('model_name') or '',
    }


def _reading_type_rules(rtype: str) -> str:
    """Faqat tanlangan tip — Gemini boshqa formatga o'tib ketmasin."""
    if rtype == 'tfng':
        return """REQUIRED question format (ONLY this — do not invent another type):
- Each prompt is a statement about the passage.
- options MUST be exactly: [{"letter":"a","text":"TRUE"},{"letter":"b","text":"FALSE"},{"letter":"c","text":"NOT GIVEN"}]
- correct MUST be "a", "b", or "c".
- instruction: "Choose TRUE, FALSE or NOT GIVEN." """
    if rtype == 'mcq':
        return """REQUIRED question format (ONLY this — NEVER use TRUE/FALSE/NOT GIVEN):
- Each prompt is a question with 4 distinct content options (not True/False).
- options: exactly 4 items with letters a,b,c,d and different answer texts from the passage.
- correct MUST be one of a/b/c/d.
- instruction: "Choose the correct option." """
    if rtype == 'gap_fill':
        return """REQUIRED question format (ONLY this — NEVER use multiple-choice or TRUE/FALSE):
- Each prompt has a blank like "______" taken from the passage.
- options MUST be an empty array [].
- correct MUST be the ONE WORD (or short phrase) that fills the blank — NOT a letter.
- instruction: "ONE WORD ONLY" """
    if rtype == 'matching_headings':
        return """REQUIRED question format (ONLY this — NEVER use TRUE/FALSE/NOT GIVEN):
- Each prompt is a short paragraph summary / section idea.
- options are candidate HEADINGS with roman letters i, ii, iii (at least 3).
- correct MUST be the matching roman letter (e.g. "i" or "ii").
- instruction: "Choose the correct heading." """
    if rtype == 'matching_endings':
        return """REQUIRED question format (ONLY this — NEVER use TRUE/FALSE/NOT GIVEN):
- Each prompt is an incomplete sentence BEGINNING (no full stop).
- options are possible ENDINGS (letters a–f); reuse the SAME endings bank for every question when possible.
- correct MUST be a letter a–f.
- instruction: "Match each beginning with the correct ending." """
    if rtype == 'matching_names':
        return """REQUIRED question format (ONLY this — NEVER use TRUE/FALSE/NOT GIVEN):
- Passage MUST name several different people (at least 4 full names).
- Each prompt is a statement/action from the passage (without the person's name).
- options are the people names (letters a–f); reuse the SAME name bank for every question.
- correct MUST be a letter a–f.
- instruction: "Match each statement with the correct person." """
    return 'Follow the requested IELTS question type strictly.'


def _reading_prompt(level: str, rtype: str, lang: str) -> str:
    meta = READING_TYPES[rtype]
    type_rules = _reading_type_rules(rtype)
    return f"""You are an IELTS Academic Reading materials writer.
Create ONE short practice set for CEFR/IELTS level {level}.
SELECTED question type (mandatory): {meta['label_uz']} / key={rtype} / qtype={meta['qtype']}.
You MUST generate ONLY this question type. Do NOT fall back to True/False/Not Given unless key=tfng.

{learner_language_rules(lang)}
- Passage and question prompts MUST be in English.
- tip and each question explanation MUST be in the learner language.

{type_rules}

Return ONLY JSON:
{{
  "title": "short English title",
  "passage": "500-650 words English academic-style passage suitable for level {level}. The passage MUST contain at least 500 words.",
  "instruction": "short English instruction matching the selected type",
  "tip": "1 short tip in learner language",
  "questions": [
    {{
      "id": 1,
      "prompt": "English question/statement",
      "options": [{{"letter":"a","text":"..."}}],
      "correct": "answer letter OR one word for gap_fill",
      "explanation": "short learner-language explanation"
    }}
  ]
}}

Rules:
- Exactly {READING_QUESTION_COUNT} questions (ids 1–{READING_QUESTION_COUNT}).
- Cover different parts of the passage; do not repeat the same idea.
- Content must be original, factual-sounding, level-appropriate.
- Do not mention that you are an AI.
"""


def _writing_prompt(level: str, focus: str, lang: str) -> str:
    meta = WRITING_FOCUSES[focus]
    return f"""You are an IELTS Academic Writing coach.
Create ONE practice set for level {level} focused on: {meta['label_uz']}.

{learner_language_rules(lang)}
- task and sample_essay MUST be in English.
- tip and exercise hints MUST be in the learner language.

Return ONLY JSON:
{{
  "task": "IELTS-style writing task prompt in English",
  "sample_essay": "level-appropriate model essay in English",
  "tip": "short tip in learner language about {meta['label_uz']}",
  "exercises": [
    {{
      "id": 1,
      "kind": "rewrite|gap|mcq",
      "prompt": "English exercise instruction",
      "options": [{{"letter":"a","text":"..."}}],
      "correct": "accepted answer or letter; alternatives separated by |",
      "hint": "short hint in learner language"
    }}
  ]
}}

Rules:
- Exactly 4 exercises tightly related to {meta['label_uz']}.
- sample_essay length suitable for {level}.
- Keep exercises practical and checkable.
- Do not mention that you are an AI.
"""


def generate_reading_practice(*, level='B1', practice_type='tfng', lang='uz', seed='', avoid_fingerprint='') -> dict:
    level = normalize_level(level)
    rtype = normalize_reading_type(practice_type)
    lang = normalize_ai_lang(lang)
    seed = str(seed or '').strip() or f'{time.time_ns()}'
    variant = _variant_index(seed, level=level, practice_type=rtype)
    local = _freshen_reading_payload(
        _local_reading(level, rtype, lang, variant=variant),
        seed,
    )
    if avoid_fingerprint and _practice_fingerprint(local) == avoid_fingerprint:
        variant = 1 - variant
        local = _freshen_reading_payload(
            _local_reading(level, rtype, lang, variant=variant),
            f'{seed}:alt',
        )
    local['content_variant'] = variant

    provider = _provider()
    if provider in ('', 'local', 'heuristic', 'fallback'):
        return local
    if provider != 'gemini':
        return local

    errors = []
    prompt = _reading_prompt(level, rtype, lang) + f"\nUnique request seed: {seed}. Produce a fresh passage (do not reuse a previous topic).\n"
    deadline = time.monotonic() + PRACTICE_GEMINI_BUDGET_SEC
    for model in _gemini_model_chain(_model_name())[:PRACTICE_GEMINI_MAX_MODELS]:
        remaining = deadline - time.monotonic()
        if remaining < 3:
            errors.append('budget_exhausted')
            break
        call_timeout = min(PRACTICE_GEMINI_CALL_TIMEOUT, max(3.0, remaining - 1.0))
        try:
            data = _call_gemini_json(prompt, model=model, timeout=call_timeout)
            data['provider_name'] = 'gemini'
            data['model_name'] = model
            payload = _normalize_reading_payload(data, level=level, rtype=rtype, lang=lang)
            if (payload.get('passage') or '').strip() and payload.get('questions'):
                payload = _freshen_reading_payload(payload, seed)
                payload['passage'] = ensure_min_words(
                    str(payload.get('title') or ''),
                    str(payload.get('passage') or ''),
                )
                if passage_word_count(payload.get('passage')) < MIN_PASSAGE_WORDS:
                    return local
                if avoid_fingerprint and _practice_fingerprint(payload) == avoid_fingerprint:
                    # AI same topic — local alternative
                    return local
                return payload
            errors.append(f'{model}: empty_payload')
        except Exception as exc:
            errors.append(str(exc)[:180])
            continue
    local = dict(local)
    local['raw_errors'] = errors
    local['provider_name'] = 'local'
    local['model_name'] = 'fallback'
    return local


def generate_writing_practice(*, level='B1', practice_type='lexical_resource', lang='uz', seed='', avoid_fingerprint='') -> dict:
    level = normalize_level(level)
    focus = normalize_writing_focus(practice_type)
    lang = normalize_ai_lang(lang)
    seed = str(seed or '').strip() or f'{time.time_ns()}'
    variant = _variant_index(seed, level=level, practice_type=focus)
    local = _freshen_writing_payload(
        _local_writing(level, focus, lang, variant=variant),
        seed,
    )
    if avoid_fingerprint and _practice_fingerprint(local) == avoid_fingerprint:
        variant = 1 - variant
        local = _freshen_writing_payload(
            _local_writing(level, focus, lang, variant=variant),
            f'{seed}:alt',
        )
    local['content_variant'] = variant

    provider = _provider()
    if provider in ('', 'local', 'heuristic', 'fallback'):
        return local
    if provider != 'gemini':
        return local

    errors = []
    prompt = _writing_prompt(level, focus, lang) + f"\nUnique request seed: {seed}. Create a fresh task (do not repeat a previous prompt).\n"
    deadline = time.monotonic() + PRACTICE_GEMINI_BUDGET_SEC
    for model in _gemini_model_chain(_model_name())[:PRACTICE_GEMINI_MAX_MODELS]:
        remaining = deadline - time.monotonic()
        if remaining < 3:
            errors.append('budget_exhausted')
            break
        call_timeout = min(PRACTICE_GEMINI_CALL_TIMEOUT, max(3.0, remaining - 1.0))
        try:
            data = _call_gemini_json(prompt, model=model, timeout=call_timeout)
            data['provider_name'] = 'gemini'
            data['model_name'] = model
            payload = _normalize_writing_payload(data, level=level, focus=focus, lang=lang)
            if (payload.get('task') or '').strip() and payload.get('exercises'):
                payload = _freshen_writing_payload(payload, seed)
                if avoid_fingerprint and _practice_fingerprint(payload) == avoid_fingerprint:
                    return local
                return payload
            errors.append(f'{model}: empty_payload')
        except Exception as exc:
            errors.append(str(exc)[:180])
            continue
    local = dict(local)
    local['raw_errors'] = errors
    local['provider_name'] = 'local'
    local['model_name'] = 'fallback'
    return local


def generate_practice(*, skill='reading', level='B1', practice_type='', lang='uz', seed='', avoid_fingerprint='') -> dict:
    skill = (skill or 'reading').strip().lower()
    if skill == 'writing':
        return generate_writing_practice(
            level=level,
            practice_type=practice_type,
            lang=lang,
            seed=seed,
            avoid_fingerprint=avoid_fingerprint,
        )
    return generate_reading_practice(
        level=level,
        practice_type=practice_type,
        lang=lang,
        seed=seed,
        avoid_fingerprint=avoid_fingerprint,
    )


def _format_correct_display(row: dict, expected: str) -> str:
    """UI uchun: 'a' → 'A. TRUE', 'x|y' → 'x / y'."""
    exp = (expected or '').strip()
    if not exp:
        return ''
    opts = row.get('options') if isinstance(row.get('options'), list) else []
    raw = exp.lower().rstrip('.')
    for o in opts:
        if not isinstance(o, dict):
            continue
        letter = str(o.get('letter') or '').strip().lower().rstrip('.')
        if letter and letter == raw:
            text = str(o.get('text') or '').strip()
            label = letter.upper()
            return f'{label}. {text}' if text else label
    if '|' in exp:
        parts = [p.strip() for p in exp.split('|') if p.strip()]
        # bir xil ma'noli variantlarni qisqartirish
        uniq = []
        seen = set()
        for p in parts:
            key = p.lower()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)
        return ' / '.join(uniq[:4])
    return exp


def _answers_match(user: str, correct: str) -> bool:
    from core.models import blank_answers_match
    u = (user or '').strip()
    c = (correct or '').strip()
    if not c:
        return False
    raw = c.lower().rstrip('.')
    # choice keys only (letters / roman numerals) — not short words like "but"
    choice_keys = {
        'a', 'b', 'c', 'd', 'e', 'f',
        'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
        'true', 'false', 'ng', 'not given',
    }
    if '|' not in c and ' ' not in c and raw in choice_keys:
        return u.lower().rstrip('.') == raw or u.lower().strip() == raw
    # alternatives a|b
    if '|' in c:
        return any(blank_answers_match(u, part) for part in c.split('|') if part.strip())
    return blank_answers_match(u, c)


def public_practice_payload(payload: dict) -> dict:
    """Clientga correct/hint maxfiy maydonlarini bermaslik."""
    if not isinstance(payload, dict):
        return {}
    out = dict(payload)
    for key in ('questions', 'exercises'):
        rows = out.get(key)
        if not isinstance(rows, list):
            continue
        cleaned = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item.pop('correct', None)
            item.pop('explanation', None)
            item.pop('hint', None)
            cleaned.append(item)
        out[key] = cleaned
    return out


def check_practice_answers(payload: dict, answers: dict) -> dict:
    """answers: { "1": "a", "2": "stress", ... }"""
    skill = (payload or {}).get('skill') or 'reading'
    items = payload.get('questions') if skill == 'reading' else payload.get('exercises')
    items = items if isinstance(items, list) else []
    results = []
    correct_n = 0
    for row in items:
        if not isinstance(row, dict):
            continue
        qid = str(row.get('id') or '')
        expected = str(row.get('correct') or '')
        user_raw = (answers or {}).get(qid)
        if user_raw is None and qid.isdigit():
            user_raw = (answers or {}).get(int(qid))
        user = str(user_raw or '').strip()
        ok = _answers_match(user, expected)
        if ok:
            correct_n += 1
        results.append({
            'id': row.get('id'),
            'user': user,
            'correct': expected,
            'correct_display': _format_correct_display(row, expected),
            'is_correct': ok,
            'explanation': row.get('explanation') or row.get('hint') or '',
            'answered': bool(user),
        })
    total = len(results) or 1
    return {
        'skill': skill,
        'correct': correct_n,
        'total': len(results),
        'percent': round(100 * correct_n / total) if results else 0,
        'items': results,
    }
