"""AI Reading/Writing mashq (practice) generator — daraja + tur bo'yicha."""
from __future__ import annotations

import json
import os
import re
import time
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings

from core.services.ai_language import learner_language_rules, normalize_ai_lang, t

# Gunicorn default timeout ~30s — Gemini shu ichida tugamasa 502.
PRACTICE_GEMINI_BUDGET_SEC = 22.0
PRACTICE_GEMINI_CALL_TIMEOUT = 18.0
PRACTICE_GEMINI_MAX_MODELS = 2

LEVELS = ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')
READING_QUESTION_COUNT = 10
WRITING_EXERCISE_COUNT = 4

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


def _number_questions(rows):
    out = []
    for i, row in enumerate(rows[:READING_QUESTION_COUNT], start=1):
        item = dict(row)
        item['id'] = i
        out.append(item)
    return out


def _local_reading(level: str, rtype: str, lang: str) -> dict:
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
    else:
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
        'passage': passage,
        'instruction': 'ONE WORD ONLY' if rtype == 'gap_fill' else 'Choose the correct option.',
        'questions': _number_questions(questions),
        'tip': tip,
        'provider_name': 'local',
        'model_name': 'practice-local-v1',
    }


def _local_writing(level: str, focus: str, lang: str) -> dict:
    meta = WRITING_FOCUSES[focus]
    tasks = {
        'A1': 'Write about your favourite place. Say where it is and why you like it. (80–100 words)',
        'A2': 'Some people prefer living in a city. Do you agree or disagree? Give reasons. (120–150 words)',
        'B1': 'Many students use smartphones for study. Discuss the advantages and disadvantages. (150–180 words)',
        'B2': 'Some people believe public parks improve city life more than shopping centres. Discuss both views and give your opinion. (220–260 words)',
        'C1': 'Governments should invest more in public libraries than in new sports stadiums. To what extent do you agree or disagree? (250–280 words)',
        'C2': 'In an age of digital media, is the traditional essay still the best way to assess academic writing ability? Discuss. (280–320 words)',
    }
    samples = {
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

    focus_exercises = {
        'lexical_resource': [
            {
                'id': 1,
                'kind': 'rewrite',
                'prompt': 'Replace the basic word with a stronger academic synonym: "good idea" →',
                'correct': 'sound approach|valuable approach|effective strategy',
                'hint': t(lang, 'Academic synonym tanlang.', 'Выберите академический синоним.'),
            },
            {
                'id': 2,
                'kind': 'gap',
                'prompt': 'Collocation: make a ______ decision (careful / carefully)',
                'correct': 'careful',
                'hint': t(lang, 'Adjective + noun.', 'Adjective + noun.'),
            },
            {
                'id': 3,
                'kind': 'rewrite',
                'prompt': 'Upgrade: "a lot of people think" →',
                'correct': 'many people believe|a large number of people argue|numerous commentators suggest',
                'hint': t(lang, 'Formalroq ibora yozing.', 'Напишите более формальную фразу.'),
            },
        ],
        'grammar': [
            {
                'id': 1,
                'kind': 'rewrite',
                'prompt': 'Correct the sentence: "People is happy in parks."',
                'correct': 'People are happy in parks.',
                'hint': t(lang, 'Subject–verb agreement.', 'Согласование подлежащего и сказуемого.'),
            },
            {
                'id': 2,
                'kind': 'gap',
                'prompt': 'If cities ______ more parks, residents would feel healthier. (build)',
                'correct': 'built',
                'hint': t(lang, 'Second conditional.', 'Second conditional.'),
            },
            {
                'id': 3,
                'kind': 'rewrite',
                'prompt': 'Fix article use: "Park is important for the children."',
                'correct': 'Parks are important for children.|A park is important for children.',
                'hint': t(lang, 'Article / plural.', 'Артикль / множественное число.'),
            },
        ],
        'paraphrasing': [
            {
                'id': 1,
                'kind': 'rewrite',
                'prompt': 'Paraphrase: "Parks help people relax."',
                'correct': 'Green spaces enable people to unwind.|Parks allow residents to reduce stress.',
                'hint': t(lang, 'Same meaning, new words.', 'Тот же смысл, другие слова.'),
            },
            {
                'id': 2,
                'kind': 'rewrite',
                'prompt': 'Paraphrase: "Many students use phones in class."',
                'correct': 'A large number of learners rely on mobile devices during lessons.',
                'hint': t(lang, 'Change structure + vocabulary.', 'Измените структуру и лексику.'),
            },
            {
                'id': 3,
                'kind': 'rewrite',
                'prompt': 'Paraphrase: "I think libraries are useful."',
                'correct': 'In my view, libraries provide significant educational value.',
                'hint': t(lang, 'More academic tone.', 'Более академичный тон.'),
            },
        ],
        'sentence_construction': [
            {
                'id': 1,
                'kind': 'rewrite',
                'prompt': 'Combine with although: "Parks are free. Malls create jobs."',
                'correct': 'Although malls create jobs, parks are free.|Although parks are free, malls create jobs.',
                'hint': t(lang, 'Complex sentence.', 'Сложное предложение.'),
            },
            {
                'id': 2,
                'kind': 'rewrite',
                'prompt': 'Use which: "Libraries offer Wi-Fi. This helps students."',
                'correct': 'Libraries offer Wi-Fi, which helps students.',
                'hint': t(lang, 'Relative clause.', 'Relative clause.'),
            },
            {
                'id': 3,
                'kind': 'gap',
                'prompt': 'Not only do parks improve air quality, ______ they also support community life.',
                'correct': 'but',
                'hint': t(lang, 'not only … but also', 'not only … but also'),
            },
        ],
        'support_sentences': [
            {
                'id': 1,
                'kind': 'mcq',
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
                'id': 2,
                'kind': 'rewrite',
                'prompt': 'Add a support sentence after: "Libraries help students."',
                'correct': 'They provide quiet study rooms and free internet access.',
                'hint': t(lang, 'Concrete detail.', 'Конкретная деталь.'),
            },
            {
                'id': 3,
                'kind': 'mcq',
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
        'argument_development': [
            {
                'id': 1,
                'kind': 'mcq',
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
                'id': 2,
                'kind': 'rewrite',
                'prompt': 'Improve this weak argument: "Parks are good because they are good."',
                'correct': 'Parks are beneficial because they provide free recreation and improve air quality.',
                'hint': t(lang, 'Reason + concrete benefit.', 'Причина + конкретная польза.'),
            },
            {
                'id': 3,
                'kind': 'gap',
                'prompt': 'Linking: Parks improve wellbeing; ______, malls mainly serve commercial interests.',
                'correct': 'by contrast|in contrast|however',
                'hint': t(lang, 'Contrast linker.', 'Контрастный союз.'),
            },
        ],
    }

    exercises = focus_exercises.get(focus, focus_exercises['lexical_resource'])
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
            for o in opts[:6]:
                if isinstance(o, dict):
                    clean_opts.append({
                        'letter': str(o.get('letter') or '').strip().lower()[:1],
                        'text': str(o.get('text') or '').strip()[:200],
                    })
                elif o:
                    clean_opts.append({'letter': '', 'text': str(o).strip()[:200]})
        out_q.append({
            'id': int(row.get('id') or i),
            'prompt': str(row.get('prompt') or row.get('question') or '').strip()[:500],
            'options': [o for o in clean_opts if o.get('text')],
            'correct': str(row.get('correct') or row.get('answer') or '').strip().lower()[:80],
            'explanation': str(row.get('explanation') or '').strip()[:400],
        })
    if len(out_q) < max(7, READING_QUESTION_COUNT - 3):
        return _local_reading(level, rtype, lang)
    # AI ba'zan 7–9 ta qaytaradi — local bilan 10 tagacha to'ldiramiz
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
    return {
        'skill': 'reading',
        'level': level,
        'practice_type': rtype,
        'practice_label': meta['label_uz'] if normalize_ai_lang(lang) == 'uz' else meta['label_ru'],
        'title': str(data.get('title') or 'Reading Practice').strip()[:160],
        'passage': str(data.get('passage') or data.get('text') or '').strip()[:6000],
        'instruction': str(data.get('instruction') or '').strip()[:200],
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


def _reading_prompt(level: str, rtype: str, lang: str) -> str:
    meta = READING_TYPES[rtype]
    return f"""You are an IELTS Academic Reading materials writer.
Create ONE short practice set for CEFR/IELTS level {level}.
Question type focus: {meta['label_uz']} ({READING_TYPES[rtype]['qtype']}).

{learner_language_rules(lang)}
- Passage and question prompts MUST be in English.
- tip and each question explanation MUST be in the learner language.

Return ONLY JSON:
{{
  "title": "short English title",
  "passage": "280-450 words English academic-style passage suitable for level {level}",
  "instruction": "short English instruction",
  "tip": "1 short tip in learner language",
  "questions": [
    {{
      "id": 1,
      "prompt": "English question/statement",
      "options": [{{"letter":"a","text":"..."}}, {{"letter":"b","text":"..."}}],
      "correct": "a",
      "explanation": "short learner-language explanation"
    }}
  ]
}}

Rules:
- Exactly {READING_QUESTION_COUNT} questions (ids 1–{READING_QUESTION_COUNT}).
- Cover different parts of the passage; do not repeat the same idea.
- For tfng: options TRUE/FALSE/NOT GIVEN with letters a/b/c; correct is letter.
- For mcq: 4 options a-d; correct is letter.
- For gap_fill: options can be []; correct is the ONE WORD answer (lowercase ok).
- For matching_headings: options are headings with roman or letter keys; correct matches option letter.
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


def generate_reading_practice(*, level='B1', practice_type='tfng', lang='uz') -> dict:
    level = normalize_level(level)
    rtype = normalize_reading_type(practice_type)
    lang = normalize_ai_lang(lang)
    local = _local_reading(level, rtype, lang)
    provider = _provider()
    if provider in ('', 'local', 'heuristic', 'fallback'):
        return local
    if provider != 'gemini':
        return local

    errors = []
    prompt = _reading_prompt(level, rtype, lang)
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


def generate_writing_practice(*, level='B1', practice_type='lexical_resource', lang='uz') -> dict:
    level = normalize_level(level)
    focus = normalize_writing_focus(practice_type)
    lang = normalize_ai_lang(lang)
    local = _local_writing(level, focus, lang)
    provider = _provider()
    if provider in ('', 'local', 'heuristic', 'fallback'):
        return local
    if provider != 'gemini':
        return local

    errors = []
    prompt = _writing_prompt(level, focus, lang)
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


def generate_practice(*, skill='reading', level='B1', practice_type='', lang='uz') -> dict:
    skill = (skill or 'reading').strip().lower()
    if skill == 'writing':
        return generate_writing_practice(level=level, practice_type=practice_type, lang=lang)
    return generate_reading_practice(level=level, practice_type=practice_type, lang=lang)


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
