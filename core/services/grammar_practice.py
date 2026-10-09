"""Grammar Practice Lab — goal areas, local bank, Gemini generation, checks."""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

from core.services.ai_language import normalize_ai_lang

GRAMMAR_LEVELS = ('B1', 'B2', 'C1', 'C2')

SKILL_CODES = {
    'AGR-SV': 'Subject–Verb Agreement',
    'ART': 'Articles',
    'CLAUSE': 'Complex Sentences',
    'RUNON': 'Sentence Boundaries',
    'REL': 'Relative Clauses',
    'COND': 'Conditionals',
    'PREP': 'Prepositions',
    'VF': 'Verb Forms',
    'TENSE': 'Tense Control',
    'PUNC': 'Punctuation',
    'COUNT': 'Countability',
    'WO': 'Word Order',
    'MOD': 'Modal Control',
    'STRUCT': 'Clause Structure',
    'VAR': 'Sentence Variety',
    'PASS': 'Passive Voice',
    'DET': 'Determiners',
    'COMP': 'Comparatives',
}

GRAMMAR_AREAS = {
    'better_sentences': {
        'label_uz': 'Yaxshiroq jumlalar',
        'label_ru': 'Лучшие предложения',
        'label_en': 'Build Better Sentences',
        'blurb_uz': 'Aniq, xilma-xil va to‘g‘ri jumlalar quring.',
        'blurb_ru': 'Стройте ясные, разнообразные и точные предложения.',
        'codes': ('WO', 'RUNON', 'STRUCT', 'VAR'),
        'types': ('repair', 'expand', 'surgery', 'combine'),
        'icon': 'fa-layer-group',
    },
    'complex': {
        'label_uz': 'Murakkab jumlalar',
        'label_ru': 'Сложные предложения',
        'label_en': 'Complex Sentences',
        'blurb_uz': 'Bog‘lovchi, nisbiy va shartli gaplar.',
        'blurb_ru': 'Связки, относительные и условные конструкции.',
        'codes': ('CLAUSE', 'REL', 'COND'),
        'types': ('why', 'combine', 'clause', 'choice'),
        'icon': 'fa-project-diagram',
    },
    'verb_control': {
        'label_uz': 'Fe’l nazorati',
        'label_ru': 'Контроль глаголов',
        'label_en': 'Verb Control',
        'blurb_uz': 'Zamon, modal, passive va fe’l shakllari.',
        'blurb_ru': 'Времена, модальные, пассив и формы глагола.',
        'codes': ('VF', 'TENSE', 'MOD', 'PASS'),
        'types': ('find', 'transform', 'contrast', 'clause'),
        'icon': 'fa-bolt',
    },
    'articles_nouns': {
        'label_uz': 'Artikllar va otlar',
        'label_ru': 'Артикли и существительные',
        'label_en': 'Articles & Nouns',
        'blurb_uz': 'Artikl, hisoblanuvchi otlar va determiner.',
        'blurb_ru': 'Артикли, исчисляемость и определители.',
        'codes': ('ART', 'COUNT', 'DET'),
        'types': ('contrast', 'repair', 'choice', 'find'),
        'icon': 'fa-font',
    },
    'fix_grammar': {
        'label_uz': 'Grammatikamni tuzat',
        'label_ru': 'Исправить грамматику',
        'label_en': 'Fix My Grammar',
        'blurb_uz': 'Xatolarni toping, tuzating va qayta yozing.',
        'blurb_ru': 'Находите, исправляйте и переписывайте ошибки.',
        'codes': ('AGR-SV', 'RUNON', 'PREP'),
        'types': ('repair', 'find', 'why', 'free'),
        'icon': 'fa-wrench',
    },
    'ielts_writing': {
        'label_uz': 'IELTS Writing uchun',
        'label_ru': 'Для IELTS Writing',
        'label_en': 'Grammar for IELTS Writing',
        'blurb_uz': 'Inshoda ishlatiladigan strukturalarni mashq qiling.',
        'blurb_ru': 'Практикуйте структуры для эссе.',
        'codes': ('CLAUSE', 'VAR', 'MOD'),
        'types': ('combine', 'expand', 'clause', 'transform'),
        'icon': 'fa-pen-fancy',
    },
}

GRAMMAR_TYPES = {
    'repair': {
        'label_uz': 'Xatoni tuzatish',
        'label_ru': 'Исправить ошибку',
        'label_en': 'Correct the Mistake',
    },
    'find': {
        'label_uz': 'Xatolarni topish',
        'label_ru': 'Найти ошибки',
        'label_en': 'Find the Mistakes',
    },
    'combine': {
        'label_uz': 'Jumlalarni birlashtirish',
        'label_ru': 'Объединить предложения',
        'label_en': 'Sentence Combining',
    },
    'expand': {
        'label_uz': 'Jumla kengaytirish',
        'label_ru': 'Расширить предложение',
        'label_en': 'Sentence Expansion',
    },
    'transform': {
        'label_uz': 'Qayta shakllantirish',
        'label_ru': 'Трансформация',
        'label_en': 'Sentence Transformation',
    },
    'choice': {
        'label_uz': 'Eng yaxshi jumla',
        'label_ru': 'Лучшее предложение',
        'label_en': 'Choose the Best Sentence',
    },
    'contrast': {
        'label_uz': 'Grammatik kontrast',
        'label_ru': 'Грамматический контраст',
        'label_en': 'Grammar Contrast',
    },
    'surgery': {
        'label_uz': 'Jumla jarrohligi',
        'label_ru': 'Редактирование предложения',
        'label_en': 'Sentence Surgery',
    },
    'clause': {
        'label_uz': 'Band qurish',
        'label_ru': 'Построить придаточное',
        'label_en': 'Clause Builder',
    },
    'why': {
        'label_uz': 'Nima uchun xato?',
        'label_ru': 'Почему это неверно?',
        'label_en': 'Why Is This Wrong?',
    },
    'free': {
        'label_uz': 'Jumlani tuzat',
        'label_ru': 'Исправьте предложение',
        'label_en': 'Fix My Sentence',
    },
    'transfer': {
        'label_uz': 'Writingga ko‘chirish',
        'label_ru': 'Перенос в Writing',
        'label_en': 'Writing Transfer',
    },
    'mixed': {
        'label_uz': 'Aralash mashq',
        'label_ru': 'Смешанная практика',
        'label_en': 'Mixed practice',
    },
}

_DETECT = (
    (re.compile(r'\bin nowadays\b', re.I), 'PREP', 'Nowadays normally does not need a preposition.'),
    (re.compile(r'\bpeople (?:is prefer|are prefer)\b', re.I), 'AGR-SV', 'People is plural. Prefer is the main verb.'),
    (re.compile(r'\bprefer work\b', re.I), 'VF', 'Use prefer working or prefer to work.'),
    (re.compile(r'\bit give\b', re.I), 'AGR-SV', 'It is singular: check the present-tense verb ending.'),
    (re.compile(r'\b(?:facilities|students) helps\b', re.I), 'AGR-SV', 'A plural subject takes help.'),
    (re.compile(r'\bshould invests\b', re.I), 'MOD', 'A modal such as should takes a base verb.'),
    (re.compile(r'\bit reduce\b', re.I), 'AGR-SV', 'The singular subject it takes reduces.'),
    (re.compile(r'\b(?:informations|advices)\b', re.I), 'COUNT', 'Check the countability of this noun.'),
    (re.compile(r'\binvest on\b', re.I), 'PREP', 'Use invest in.'),
    (re.compile(r'\bprovide solution\b', re.I), 'ART', 'A singular countable noun needs a determiner.'),
    (re.compile(r'\bGovernment should\b'), 'ART', 'Specify the government or use plural governments.'),
    (re.compile(r'\balthough\b[^.!?]*\bbut\b', re.I), 'CLAUSE', 'Use although or but, not both.'),
    (re.compile(r'\bbecause\b[^.!?]*\bso\b', re.I), 'CLAUSE', 'Use because or so, not both.'),
    (re.compile(r'\bdespite of\b', re.I), 'PREP', 'Use despite without of, or in spite of.'),
    (re.compile(r'\bdespite (?:many people prefer|technology has)\b', re.I), 'CLAUSE', 'Despite needs a noun phrase or -ing form.'),
    (re.compile(r'\bwhich it began\b', re.I), 'REL', 'Which already acts as the subject: remove it.'),
    (re.compile(r'\b(?:might|may|should|must) (?:improves|is)\b', re.I), 'MOD', 'A modal takes a base verb.'),
    (re.compile(r'\bexpensive, many graduates\b', re.I), 'RUNON', 'Use a full stop, semicolon, or conjunction.'),
)

_TARGET_RE = {
    'although': re.compile(r'\b(although|though|even though|whereas|while|despite|however|but)\b', re.I),
    'despite': re.compile(r'\b(despite|although|in spite of)\b', re.I),
    'cause': re.compile(r'\b(because|since|as|so)\b', re.I),
    'passive': re.compile(r'\b(be|is|are|was|were|been)\s+\w+', re.I),
    'relative': re.compile(r'\b(who|which|that|whom|whose)\b', re.I),
    'condition': re.compile(r'\b(if|unless|provided|were)\b', re.I),
    'modal': re.compile(r'\b(may|might|could|should|must|can|would)\b', re.I),
    'boundary': re.compile(r'[.!?;]\s*[A-Z]'),
    'determiner': re.compile(r'\b(a|an|the|this|these|some|many|another)\b', re.I),
    'agreement': re.compile(r'\b\w+\b'),
    'expansion': re.compile(r'\b(because|since|although|which)\b', re.I),
    'count': re.compile(r'\b(fewer|less|much|many)\b', re.I),
    'preposition': re.compile(r'\b(in|on|at|for|to)\b', re.I),
    'free': re.compile(r'\b\w+\b'),
}


def normalize_grammar_level(value: str) -> str:
    raw = (value or 'B2').strip().upper()
    return raw if raw in GRAMMAR_LEVELS else 'B2'


def normalize_grammar_area(value: str) -> str:
    raw = (value or 'better_sentences').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'build_better_sentences': 'better_sentences',
        'sentences': 'better_sentences',
        'complex_sentences': 'complex',
        'verbs': 'verb_control',
        'articles': 'articles_nouns',
        'fix': 'fix_grammar',
        'writing': 'ielts_writing',
        'ielts': 'ielts_writing',
    }
    raw = aliases.get(raw, raw)
    return raw if raw in GRAMMAR_AREAS else 'better_sentences'


def normalize_grammar_type(value: str) -> str:
    raw = (value or 'mixed').strip().lower().replace('-', '_').replace(' ', '_')
    if raw in GRAMMAR_TYPES:
        return raw
    if raw in GRAMMAR_AREAS:
        return 'mixed'
    return 'mixed'


def grammar_page_catalog(lang: str = 'uz') -> dict:
    ru = normalize_ai_lang(lang) == 'ru'
    notes = {
        'B1': 'Asosiy aniqlik' if not ru else 'Базовая точность',
        'B2': 'Nazorat va moslashuv' if not ru else 'Контроль и гибкость',
        'C1': 'Aniqlik va diapazon' if not ru else 'Точность и диапазон',
        'C2': 'Nozik nazorat' if not ru else 'Тонкий контроль',
    }
    categories = []
    for key, meta in GRAMMAR_AREAS.items():
        types = []
        for tkey in meta['types']:
            tmeta = GRAMMAR_TYPES.get(tkey) or {}
            types.append({
                'key': tkey,
                'label': (tmeta.get('label_ru') if ru else tmeta.get('label_uz')) or tkey,
                'blurb': '',
                'example': '',
                'minutes': 12,
                'questions': 5,
            })
        categories.append({
            'key': key,
            'label': meta.get('label_ru') if ru else meta['label_uz'],
            'official': meta.get('label_en') or meta['label_uz'],
            'hint': meta.get('blurb_ru') if ru else meta['blurb_uz'],
            'icon': meta.get('icon') or 'fa-pen',
            'types': types,
        })
    return {
        'levels': [{'key': lv, 'label': f'{lv} · {notes[lv]}'} for lv in GRAMMAR_LEVELS],
        'categories': categories,
        'areas': categories,
        'exercise_types': [
            {
                'key': key,
                'label': (meta.get('label_ru') if ru else meta.get('label_uz')) or key,
            }
            for key, meta in GRAMMAR_TYPES.items()
            if key != 'mixed'
        ],
        'skill_codes': SKILL_CODES,
    }


def _normalize_text(value: str) -> str:
    text = (value or '').lower()
    text = text.replace('“', '"').replace('”', '"').replace('’', "'")
    text = re.sub(r"[^a-z0-9' ]", ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _detect_errors(text: str) -> list[dict]:
    out = []
    for pattern, code, hint in _DETECT:
        match = pattern.search(text or '')
        if match:
            out.append({'code': code, 'fragment': match.group(0), 'hint': hint})
    return out


def _has_target(target: str, answer: str) -> bool:
    pattern = _TARGET_RE.get((target or '').strip().lower())
    if not pattern:
        return bool((answer or '').strip())
    return bool(pattern.search(answer or ''))


def _letter_for_index(index: int) -> str:
    return chr(ord('a') + max(0, index))


def _options_from_list(options: list, correct_index: int = 0) -> tuple[list, str]:
    rows = []
    for i, text in enumerate(options[:6]):
        rows.append({'letter': _letter_for_index(i), 'text': str(text).strip()})
    correct = _letter_for_index(int(correct_index) if str(correct_index).isdigit() else 0)
    return rows, correct


def _base_bank(level: str = 'B2') -> list[dict]:
    """Handoffdan olingan curated mashqlar + daraja variantlari."""
    level = normalize_grammar_level(level)
    items = [
        {
            'type': 'repair', 'code': 'CLAUSE',
            'prompt': 'Correct the mistake. Keep the original meaning.',
            'source': ['Although online education is convenient but it cannot completely replace classroom learning.'],
            'model': 'Although online education is convenient, it cannot completely replace classroom learning.',
            'rule': 'Although already introduces contrast. Remove but, or keep but and remove although.',
            'target': 'although',
        },
        {
            'type': 'find', 'code': 'AGR-SV',
            'prompt': 'There are two grammar mistakes. Select the incorrect words, then correct the sentence.',
            'source': ['Governments should invests more money in public transportation because it reduce traffic congestion.'],
            'model': 'Governments should invest more money in public transportation because it reduces traffic congestion.',
            'rule': 'After should, use the base form invest. The singular pronoun it takes reduces.',
            'target': 'agreement',
            'wrong_words': ['invests', 'reduce'],
        },
        {
            'type': 'combine', 'code': 'CLAUSE',
            'prompt': 'Combine these ideas into one or two natural sentences.',
            'source': ['Public transport is inexpensive.', 'It reduces congestion.', 'Many people still prefer private cars.'],
            'model': 'Although public transport is inexpensive and reduces congestion, many people still prefer private cars.',
            'rule': 'Use a concessive structure to connect the benefits with the contrasting preference.',
            'target': 'although',
        },
        {
            'type': 'expand', 'code': 'VAR',
            'prompt': 'Build this sentence in three steps.',
            'source': ['Online education is useful.'],
            'model': 'Although it requires self-discipline, online education is useful because it offers flexible access to learning.',
            'rule': 'Add information that supports your meaning. A longer sentence is not automatically better.',
            'target': 'expansion',
            'steps': ['Add a reason.', 'Add a contrast.', 'Refine the sentence with a relative clause or clearer clause arrangement.'],
        },
        {
            'type': 'transform', 'code': 'PASS',
            'prompt': 'Rewrite using the passive.',
            'source': ['Governments should regulate advertising to children.'],
            'model': 'Advertising to children should be regulated by governments.',
            'rule': 'Use should + be + past participle. Preserve the original meaning.',
            'target': 'passive',
        },
        {
            'type': 'choice', 'code': 'CLAUSE',
            'prompt': 'Choose the grammatically accurate and most natural sentence.',
            'source': ['Consider the structure after despite.'],
            'model': 'Despite technological improvements, many issues remain.',
            'rule': 'Despite is followed by a noun phrase or -ing form, not a finite clause.',
            'target': 'despite',
            'options': [
                'Despite technology has improved, many issues remain.',
                'Despite technological improvements, many issues remain.',
                'Despite of technology improving, many issues remain.',
                'Despite technology improved, many issues remain.',
            ],
            'correct_index': 1,
        },
        {
            'type': 'contrast', 'code': 'COUNT',
            'prompt': 'Choose the best word for this context.',
            'source': ['Investment in public transport could mean _____ cars on the road.'],
            'model': 'fewer',
            'rule': 'Cars is a plural countable noun. Use fewer; use less with uncountable nouns.',
            'target': 'count',
            'options': ['less', 'fewer', 'much', 'little'],
            'correct_index': 1,
        },
        {
            'type': 'surgery', 'code': 'RUNON',
            'prompt': 'Build two accurate, natural sentences. Move the ideas, add connectors and punctuation, then edit.',
            'source': ['Nowadays, many people work from home, this saves time, and they can spend more time with their family which this is good for their mental health.'],
            'model': 'Nowadays, many people work from home, which saves commuting time. They can spend more time with their families, and this may improve their mental well-being.',
            'rule': 'Avoid joining complete sentences with only a comma. Use a full stop or an appropriate clause connection.',
            'target': 'boundary',
        },
        {
            'type': 'clause', 'code': 'REL',
            'prompt': 'Add a relative clause explaining a benefit of public transport.',
            'source': ['Governments should invest in public transport.'],
            'model': 'Governments should invest in public transport, which can reduce congestion.',
            'rule': 'Use which to add information about public transport. Keep the main clause complete.',
            'target': 'relative',
        },
        {
            'type': 'why', 'code': 'CLAUSE',
            'prompt': 'Explain the mistake, then correct the sentence yourself.',
            'source': ['Despite many people prefer cars, public transport is more efficient.'],
            'model': 'Although many people prefer cars, public transport is more efficient.',
            'rule': 'Despite cannot introduce this finite clause. Use although, or replace the clause with a noun phrase.',
            'target': 'despite',
            'options': [
                'Despite cannot introduce this finite clause.',
                'Prefer requires an infinitive.',
                'Public transport always needs an article.',
                'More efficient is incorrect.',
            ],
            'correct_index': 0,
        },
        {
            'type': 'free', 'code': 'VF',
            'prompt': 'Find and fix the grammar issues in this sentence.',
            'source': ['In nowadays many people is prefer work from home because it give them more freedom.'],
            'model': 'Nowadays many people prefer working from home because it gives them more freedom.',
            'rule': 'Work through each flagged pattern, then rewrite the complete sentence.',
            'target': 'free',
        },
        {
            'type': 'transfer', 'code': 'COND',
            'prompt': 'Write two natural sentences about this IELTS topic. Use a conditional to develop your position.',
            'source': ['Some people believe university education should be free.'],
            'model': 'If university education were free, more students could pursue a degree. However, governments would need to consider the cost.',
            'rule': 'Make the conditional relevant to the argument. Clarity matters more than complexity.',
            'target': 'condition',
        },
    ]
    # Level-specific source tweaks
    if level == 'B1':
        for row in items:
            if row['type'] == 'repair':
                row['source'] = ['Because the bus is cheap so I use it.']
                row['model'] = 'Because the bus is cheap, I use it.'
                row['rule'] = 'Use because or so, not both.'
                row['target'] = 'cause'
            elif row['type'] == 'combine':
                row['source'] = ['The bus is cheap.', 'I use it every day.']
                row['prompt'] = 'Combine these ideas using because.'
                row['model'] = 'I use the bus every day because it is cheap.'
                row['target'] = 'cause'
            elif row['type'] == 'transform':
                row['source'] = ['The council cleans the streets.']
                row['model'] = 'The streets are cleaned by the council.'
                row['rule'] = 'Use are + past participle.'
    elif level == 'C1':
        for row in items:
            if row['type'] == 'repair':
                row['source'] = ['Having reviewed the evidence, the policy was supported by the researchers.']
                row['model'] = 'Having reviewed the evidence, the researchers supported the policy.'
                row['rule'] = 'The implied subject of having reviewed should be the researchers, not the policy.'
                row['target'] = 'participle'
    elif level == 'C2':
        for row in items:
            if row['type'] == 'repair':
                row['source'] = ['Only after the review the committee did acknowledge the limitations.']
                row['model'] = 'Only after the review did the committee acknowledge the limitations.'
                row['rule'] = 'Fronted only after requires subject–auxiliary inversion here.'
                row['target'] = 'inversion'
    return items


def _pack_exercise(raw: dict, *, index: int, level: str) -> dict:
    etype = str(raw.get('type') or 'repair').strip().lower()
    source = raw.get('source')
    if isinstance(source, str):
        source = [source]
    if not isinstance(source, list):
        source = [str(source or '')]
    source = [str(s).strip() for s in source if str(s).strip()]
    options = raw.get('options')
    correct = str(raw.get('correct') or '').strip()
    model = str(raw.get('model') or '').strip()
    correct_index = raw.get('correct_index', 0)
    option_rows = []
    if isinstance(options, list) and options:
        if options and isinstance(options[0], dict):
            option_rows = [
                {
                    'letter': str(o.get('letter') or _letter_for_index(i)).lower(),
                    'text': str(o.get('text') or '').strip(),
                }
                for i, o in enumerate(options[:6])
                if isinstance(o, dict)
            ]
            if not correct:
                correct = str(option_rows[min(int(correct_index or 0), len(option_rows) - 1)]['letter'])
        else:
            option_rows, letter = _options_from_list([str(x) for x in options], correct_index)
            if not correct:
                correct = letter
            if not model and option_rows:
                model = next((o['text'] for o in option_rows if o['letter'] == correct), option_rows[0]['text'])
    if not correct and model:
        correct = model
    wrong = raw.get('wrong_words') or raw.get('wrongWords') or []
    if not isinstance(wrong, list):
        wrong = []
    wrong = [str(w).strip() for w in wrong if str(w).strip()]
    steps = raw.get('steps') if isinstance(raw.get('steps'), list) else []
    rule = str(raw.get('rule') or raw.get('explanation') or '').strip()
    target = str(raw.get('target') or '').strip() or 'structure'
    code = str(raw.get('code') or 'CLAUSE').strip().upper()
    prompt = str(raw.get('prompt') or '').strip() or 'Complete the grammar task.'
    hints = raw.get('hints') if isinstance(raw.get('hints'), list) else []
    hint = str((hints[0] if hints else '') or raw.get('hint') or f'Focus on {SKILL_CODES.get(code, code).lower()}.').strip()
    return {
        'id': index,
        'type': etype if etype in GRAMMAR_TYPES else 'repair',
        'code': code if code in SKILL_CODES else 'CLAUSE',
        'prompt': prompt,
        'source': source,
        'options': option_rows,
        'steps': [str(s) for s in steps[:5]],
        'wrong_words': wrong,
        'correct': correct,
        'model': model or correct,
        'explanation': rule,
        'hint': hint,
        'target': target,
        'level': level,
    }


def _local_grammar(level: str, area_or_type: str, lang: str = 'uz', *, count: int = 5, seed: str = '') -> dict:
    level = normalize_grammar_level(level)
    key = (area_or_type or 'better_sentences').strip().lower()
    area = normalize_grammar_area(key) if key in GRAMMAR_AREAS or key.replace('-', '_') in GRAMMAR_AREAS else ''
    etype = normalize_grammar_type(key) if key in GRAMMAR_TYPES else 'mixed'
    bank = _base_bank(level)
    if area:
        wanted = list(GRAMMAR_AREAS[area]['types'])
        label = GRAMMAR_AREAS[area]['label_en']
        practice_type = area
    elif etype != 'mixed':
        wanted = [etype]
        label = (GRAMMAR_TYPES.get(etype) or {}).get('label_en') or etype
        practice_type = etype
    else:
        area = 'better_sentences'
        wanted = list(GRAMMAR_AREAS[area]['types'])
        label = GRAMMAR_AREAS[area]['label_en']
        practice_type = area

    by_type = {row['type']: row for row in bank}
    picked = []
    for tkey in wanted:
        if tkey in by_type:
            picked.append(by_type[tkey])
    if not picked:
        picked = bank[:4]
    # Always end with transfer for writing loop when mixed area
    if practice_type in GRAMMAR_AREAS and by_type.get('transfer') and picked[-1].get('type') != 'transfer':
        transfer = dict(by_type['transfer'])
        prior = picked[-1]
        transfer['code'] = prior.get('code') or transfer['code']
        transfer['target'] = prior.get('target') or transfer['target']
        transfer['rule'] = prior.get('rule') or transfer['rule']
        skill_name = SKILL_CODES.get(transfer['code'], 'grammar').lower()
        transfer['prompt'] = (
            f'Write two natural sentences about education or transport. '
            f'Use {skill_name} to develop your argument.'
        )
        picked.append(transfer)

    seed_s = str(seed or time.time_ns())
    offset = int(hashlib.sha1(seed_s.encode()).hexdigest()[:6], 16) % max(1, len(picked))
    rotated = picked[offset:] + picked[:offset]
    exercises = [_pack_exercise(row, index=i + 1, level=level) for i, row in enumerate(rotated[: max(3, min(count, 6))])]
    ru = normalize_ai_lang(lang) == 'ru'
    title = f'{label} · {level}'
    return {
        'skill': 'grammar',
        'level': level,
        'practice_type': practice_type,
        'title': title,
        'practice_label': label,
        'instruction': (
            'Исправьте, перепишите или выберите точный вариант. Сначала попробуйте сами.'
            if ru else
            'Correct, rewrite, or choose the accurate option. Attempt before using help.'
        ),
        'exercises': exercises,
        'provider_name': 'local',
        'model_name': 'fallback',
    }


def _normalize_ai_grammar(data: dict, *, level: str, practice_type: str, lang: str) -> dict | None:
    rows = data.get('exercises') if isinstance(data, dict) else None
    if not isinstance(rows, list) or len(rows) < 3:
        return None
    exercises = []
    for i, row in enumerate(rows[:6]):
        if not isinstance(row, dict):
            continue
        packed = _pack_exercise(row, index=i + 1, level=level)
        if packed.get('source') and (packed.get('correct') or packed.get('model') or packed.get('options')):
            exercises.append(packed)
    if len(exercises) < 3:
        return None
    area = practice_type if practice_type in GRAMMAR_AREAS else normalize_grammar_area(practice_type)
    meta = GRAMMAR_AREAS.get(area) or GRAMMAR_TYPES.get(practice_type) or {}
    label = meta.get('label_en') or meta.get('label_uz') or practice_type
    return {
        'skill': 'grammar',
        'level': level,
        'practice_type': practice_type,
        'title': str(data.get('title') or f'{label} · {level}').strip()[:120],
        'practice_label': label,
        'instruction': str(data.get('instruction') or 'Attempt the task, then check.').strip()[:400],
        'exercises': exercises,
        'provider_name': 'gemini',
        'model_name': ((data.get('_raw_meta') or {}).get('model') if isinstance(data.get('_raw_meta'), dict) else '') or 'gemini',
    }


def generate_grammar_practice(
    *,
    level: str = 'B2',
    practice_type: str = 'better_sentences',
    lang: str = 'uz',
    seed: str = '',
    count: int = 5,
    avoid_fingerprint: str = '',
) -> dict:
    from core.services import ai_practice as ap

    level = normalize_grammar_level(level)
    key = (practice_type or 'better_sentences').strip().lower().replace('-', '_').replace(' ', '_')
    if key in GRAMMAR_AREAS:
        area = key
        etype = 'mixed'
        practice_key = area
    elif key in GRAMMAR_TYPES and key != 'mixed':
        area = ''
        etype = key
        practice_key = etype
    else:
        area = normalize_grammar_area(key)
        etype = 'mixed'
        practice_key = area

    local = _local_grammar(level, practice_key, lang, count=count, seed=seed or str(time.time_ns()))
    if ap._provider() != 'gemini':
        return local

    area_meta = GRAMMAR_AREAS.get(area or practice_key) or {}
    type_list = list(area_meta.get('types') or ([etype] if etype != 'mixed' else ['repair', 'choice', 'combine', 'transfer']))
    type_labels = ', '.join(type_list)
    topic_hint = (
        'IELTS Writing topics: education, public transport, housing, technology, environment. '
        'Each exercise must be NEW — do not reuse the same sample sentences from common textbooks.'
    )
    prompt = f"""You are an IELTS Grammar Practice Lab author. Create {count} NEW grammar exercises for level {level}.
Practice focus: {practice_key} ({area_meta.get('label_en') or practice_key}).
Include these exercise types in order when possible: {type_labels}.
{topic_hint}

Return ONLY JSON:
{{
  "title": "short title",
  "instruction": "one short instruction in English",
  "exercises": [
    {{
      "type": "repair|find|combine|expand|transform|choice|contrast|clause|why|transfer",
      "code": "one of ART,CLAUSE,AGR-SV,RUNON,REL,COND,PREP,VF,TENSE,PASS,MOD,VAR,COUNT,DET,STRUCT,WO",
      "prompt": "task instruction in English",
      "source": ["sentence or sentences for the learner"],
      "model": "one good model answer",
      "rule": "short accurate rule explanation",
      "target": "structure tag e.g. although, passive, relative",
      "options": ["only for choice/contrast/why — 3 or 4 strings"],
      "correct_index": 0,
      "wrong_words": ["only for find — exact incorrect tokens from source"],
      "steps": ["only for expand — 2 or 3 short steps"],
      "hint": "short hint without revealing the full answer"
    }}
  ]
}}

Rules:
- Constrained tasks (choice/contrast/why) must have exactly one best option.
- Open answers may have multiple valid paraphrases; put the best model answer in model.
- Never invent forbidden factual claims; keep IELTS-relevant natural English.
- No answer keys outside JSON fields model/correct_index/wrong_words/rule.
"""
    errors = []
    deadline = time.monotonic() + ap.PRACTICE_GEMINI_BUDGET_SEC
    for model in ap._gemini_model_chain(ap._model_name())[: ap.PRACTICE_GEMINI_MAX_MODELS]:
        if time.monotonic() >= deadline:
            break
        try:
            data = ap._call_gemini_json(
                prompt,
                model=model,
                timeout=min(ap.PRACTICE_GEMINI_CALL_TIMEOUT, max(8.0, deadline - time.monotonic())),
                temperature=0.85,
                max_output_tokens=4096,
            )
            payload = _normalize_ai_grammar(data, level=level, practice_type=practice_key, lang=lang)
            if payload:
                if avoid_fingerprint and ap._practice_fingerprint(payload) == avoid_fingerprint:
                    continue
                return payload
            errors.append(f'{model}: invalid_grammar_payload')
        except Exception as exc:  # noqa: BLE001 — collect and fall back
            msg = str(exc)[:180]
            errors.append(msg)
            if '429' in msg:
                break
            continue
    out = dict(local)
    out['raw_errors'] = errors
    return out


def evaluate_grammar_item(row: dict, user_raw: Any) -> dict:
    """Deterministic check for constrained tasks; heuristic + model match for open."""
    etype = str((row or {}).get('type') or '').strip().lower()
    user = str(user_raw or '').strip()
    expected = str((row or {}).get('correct') or (row or {}).get('model') or '').strip()
    model = str((row or {}).get('model') or expected).strip()
    explanation = str((row or {}).get('explanation') or (row or {}).get('rule') or '').strip()
    target = str((row or {}).get('target') or '').strip()
    selected_words: list[str] = []
    text_answer = user

    if user.startswith('{'):
        try:
            parsed = json.loads(user)
            if isinstance(parsed, dict):
                if isinstance(parsed.get('words'), list):
                    selected_words = [str(w).strip() for w in parsed['words'] if str(w).strip()]
                text_answer = str(parsed.get('text') or parsed.get('answer') or '').strip() or user
                if parsed.get('choice') is not None:
                    text_answer = str(parsed.get('choice')).strip()
        except json.JSONDecodeError:
            pass
    if '|' in user and etype == 'find':
        left, _, right = user.partition('|')
        selected_words = [w.strip() for w in left.split(',') if w.strip()]
        text_answer = right.strip()

    # Choice-like
    if etype in ('choice', 'contrast', 'why') or (row.get('options') and expected in 'abcdef'):
        opts = row.get('options') if isinstance(row.get('options'), list) else []
        letter = text_answer.lower().rstrip('.')
        if letter.isdigit() and opts:
            idx = int(letter)
            letter = str(opts[idx].get('letter') if isinstance(opts[idx], dict) else _letter_for_index(idx)).lower()
        ok = letter == expected.lower().rstrip('.') or _normalize_text(text_answer) == _normalize_text(model)
        return {
            'is_correct': ok,
            'answered': bool(text_answer),
            'user': text_answer,
            'correct': expected,
            'correct_display': _choice_display(row, expected) or model,
            'explanation': explanation,
            'verified': True,
        }

    if etype == 'find':
        wrong = [str(w) for w in (row.get('wrong_words') or [])]
        found = bool(wrong) and len(selected_words) == len(wrong) and all(w in selected_words for w in wrong)
        exact = _normalize_text(text_answer) == _normalize_text(model)
        errors = _detect_errors(text_answer)
        ok = found and exact and not errors
        return {
            'is_correct': ok,
            'answered': bool(selected_words or text_answer),
            'user': text_answer or ','.join(selected_words),
            'correct': model,
            'correct_display': model,
            'explanation': explanation if (found or text_answer) else 'Select the incorrect words, then write the corrected sentence.',
            'verified': True,
        }

    errors = _detect_errors(text_answer)
    exact = _normalize_text(text_answer) == _normalize_text(model)
    target_ok = _has_target(target, text_answer)
    tokens = _normalize_text(text_answer).split()
    sufficient = len(tokens) >= (8 if etype == 'transfer' else 4)
    if etype == 'transfer':
        sentences = len(re.findall(r'[.!?]', text_answer))
        if sentences < 2:
            sufficient = False

    if exact:
        ok = True
    elif errors or not sufficient:
        ok = False
    elif target_ok and sufficient and not errors:
        # Accept reasonable paraphrase when target structure is present
        ok = True
    else:
        ok = False

    return {
        'is_correct': ok,
        'answered': bool(text_answer),
        'user': text_answer,
        'correct': model or expected,
        'correct_display': model or expected,
        'explanation': explanation,
        'verified': exact or bool(errors) or not sufficient,
        'target_used': target_ok,
    }


def _choice_display(row: dict, expected: str) -> str:
    opts = row.get('options') if isinstance(row.get('options'), list) else []
    raw = (expected or '').lower().rstrip('.')
    for o in opts:
        if not isinstance(o, dict):
            continue
        if str(o.get('letter') or '').lower().rstrip('.') == raw:
            text = str(o.get('text') or '').strip()
            letter = str(o.get('letter') or '').upper()
            return f'{letter}. {text}' if text else letter
    return expected or ''


def public_grammar_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    out = dict(payload)
    out.pop('raw_errors', None)
    rows = out.get('exercises')
    if not isinstance(rows, list):
        return out
    cleaned = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        for key in ('correct', 'explanation', 'hint', 'model', 'wrong_words', 'wrongWords', 'rule', 'correct_index'):
            item.pop(key, None)
        cleaned.append(item)
    out['exercises'] = cleaned
    return out
