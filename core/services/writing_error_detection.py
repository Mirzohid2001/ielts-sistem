"""Writing essaydagi aniq xatolarni topish, tekshirish va boyitish."""

from __future__ import annotations

import difflib
import re
from typing import Any

ERROR_TYPES = frozenset({
    'grammar', 'spelling', 'punctuation', 'article', 'tense', 'preposition',
    'subject_verb', 'word_choice', 'plural', 'capitalization', 'word_form',
})

# (pattern, correct_replacement_or_None, type, why)
# correct=None → wrong = match, faqat ogohlantirish; enrich da qo'shilmaydi
_HEURISTIC_RULES: tuple[tuple[str, str | None, str, str], ...] = (
  # Uncountable / plural
    (r'\bpeoples\b', 'people', 'plural', "People ko'plikda s qo'shilmaydi"),
    (r'\binformations\b', 'information', 'grammar', 'Information sanalmaydi'),
    (r'\badvices\b', 'advice', 'grammar', 'Advice sanalmaydi'),
    (r'\bequipments\b', 'equipment', 'grammar', 'Equipment sanalmaydi'),
    (r'\bfurnitures\b', 'furniture', 'grammar', 'Furniture sanalmaydi'),
    (r'\bchilds\b', 'children', 'plural', 'Child → children'),
    (r'\bmans\b', 'men', 'plural', 'Man → men'),
    (r'\bwomans\b', 'women', 'plural', 'Woman → women'),
    # Apostrophe / spelling
    (r"\bdont\b", "don't", 'spelling', "don't — apostrof kerak"),
    (r"\bcant\b", "can't", 'spelling', "can't — apostrof kerak"),
    (r"\bwont\b", "won't", 'spelling', "won't — apostrof kerak"),
    (r"\bdoesnt\b", "doesn't", 'spelling', "doesn't — apostrof kerak"),
    (r"\bdidnt\b", "didn't", 'spelling', "didn't — apostrof kerak"),
    (r"\bisnt\b", "isn't", 'spelling', "isn't — apostrof kerak"),
    (r"\barent\b", "aren't", 'spelling', "aren't — apostrof kerak"),
    (r"\bwasnt\b", "wasn't", 'spelling', "wasn't — apostrof kerak"),
    (r"\bwerent\b", "weren't", 'spelling', "weren't — apostrof kerak"),
    (r"\bhasnt\b", "hasn't", 'spelling', "hasn't — apostrof kerak"),
    (r"\bhavent\b", "haven't", 'spelling', "haven't — apostrof kerak"),
    (r"\bcouldnt\b", "couldn't", 'spelling', "couldn't — apostrof kerak"),
    (r"\bwouldnt\b", "wouldn't", 'spelling', "wouldn't — apostrof kerak"),
    (r"\bshouldnt\b", "shouldn't", 'spelling', "shouldn't — apostrof kerak"),
    (r"\bim\b", "I'm", 'capitalization', "I'm — katta I"),
    (r"\bive\b", "I've", 'capitalization', "I've — katta I"),
    (r"\bthats\b", "that's", 'spelling', "that's — apostrof kerak"),
    (r"\bits\b(?=\s+(?:a|an|the|very|so|too)\b)", "it's", 'grammar', "it's (it is) vs its (egalik)"),
    (r'\balot\b', 'a lot', 'spelling', "Ikki so'z: a lot"),
    (r'\beverytime\b', 'every time', 'spelling', "every time — ikki so'z"),
    (r'\binspite\b', 'in spite', 'spelling', "in spite of — ikki so'z"),
    # Common misspellings
    (r'\brecieve\b', 'receive', 'spelling', 'receive — i before e'),
    (r'\boccured\b', 'occurred', 'spelling', 'occurred — ikki r'),
    (r'\benviroment\b', 'environment', 'spelling', 'environment — n qo\'shiladi'),
    (r'\bgoverment\b', 'government', 'spelling', 'government — n qo\'shiladi'),
    (r'\bdefinately\b', 'definitely', 'spelling', 'definitely'),
    (r'\bseperate\b', 'separate', 'spelling', 'separate'),
    (r'\boccassion\b', 'occasion', 'spelling', 'occasion'),
    (r'\bwich\b', 'which', 'spelling', 'which'),
    (r'\bthier\b', 'their', 'spelling', 'their / there / they\'re'),
    (r'\bteh\b', 'the', 'spelling', 'the'),
    (r'\buntill\b', 'until', 'spelling', 'until — bitta l'),
    (r'\busefull\b', 'useful', 'spelling', 'useful — bitta l'),
    (r'\bbeleive\b', 'believe', 'spelling', 'believe — ie'),
    (r'\baccomodate\b', 'accommodate', 'spelling', 'accommodate — ikki m'),
    (r'\barguement\b', 'argument', 'spelling', 'argument — e yo\'q'),
    # Grammar collocations
    (r'\bmore\s+(?:better|worse|easier|harder|faster|slower|higher|lower)\b', None, 'grammar', 'Ikki comparative birga ishlatilmaydi'),
    (r'\bvery\s+unique\b', 'unique', 'word_choice', 'unique — very kerak emas'),
    (r'\bless\s+(?:people|students|children|cars|jobs|years)\b', None, 'grammar', 'Sanaladigan uchun fewer ishlating'),
    (r'\bamount\s+of\s+(?:people|students|children|cars)\b', None, 'word_choice', 'number of — sanaladigan otlar uchun'),
    (r'\bdepend\s+of\b', 'depend on', 'preposition', 'depend on'),
    (r'\bdiscuss\s+about\b', 'discuss', 'grammar', 'discuss — about kerak emas'),
    (r'\breturn\s+back\b', 'return', 'word_choice', 'return back — ortiqcha'),
    (r'\bbecause\s+of\s+that\s+reason\b', 'because', 'word_choice', 'because of that reason — ortiqcha'),
    (r'\btheir\s+is\b', 'there is', 'grammar', 'there is — joy uchun there'),
    (r'\btheir\s+are\b', 'there are', 'grammar', 'there are — joy uchun there'),
    (r'\bin\s+the\s+other\s+hand\b', 'on the other hand', 'preposition', 'on the other hand'),
    (r'\bcomparing\s+to\b', 'compared to', 'preposition', 'compared to'),
    (r'\bas\s+well\s+than\b', 'as well as', 'grammar', 'as well as — than emas'),
    (r'\bgo\s+to\s+home\b', 'go home', 'preposition', 'go home — to kerak emas'),
    (r'\bin\s+weekend\b', 'at the weekend', 'preposition', 'at/on the weekend'),
    (r'\bon\s+the\s+conclusion\b', 'in conclusion', 'preposition', 'in conclusion'),
    (r'\baccording\s+me\b', 'according to me', 'preposition', 'according to'),
    # Articles with uncountable
    (r'\ba\s+(?:information|advice|equipment|furniture|news|research|knowledge|evidence|traffic|pollution|water|money)\b', None, 'article', 'Bu otlar oldidan a/an ishlatilmaydi'),
    (r'\ban\s+(?:student|university|European|unique)\b', None, 'article', 'a/an tanlovi noto\'g\'ri bo\'lishi mumkin'),
    # Subject-verb
    (r'\b(people|children|students|citizens|workers|police|staff)\s+is\b', None, 'subject_verb', "Ko'plik ot + are"),
    (r'\b(everyone|everybody|someone|nobody|each)\s+are\b', None, 'subject_verb', 'Yakka ot + is'),
    (r'\b(they|we|you)\s+is\b', None, 'subject_verb', 'they/we/you + are'),
    (r'\b(he|she|it)\s+are\b', None, 'subject_verb', 'he/she/it + is'),
    (r'\bthere\s+is\s+(many|several|various|numerous)\b', None, 'grammar', 'many/several bilan there are'),
)

_SUBJECT_VERB_FIXES = (
    (r'\b(people|children|students|citizens|workers|police|staff)\s+is\b', r'\1 are', 'subject_verb', "Ko'plik ot bilan are"),
    (r'\b(everyone|everybody|someone|nobody|each)\s+are\b', r'\1 is', 'subject_verb', 'Yakka ot bilan is'),
    (r'\b(they|we|you)\s+is\b', r'\1 are', 'subject_verb', 'they/we/you + are'),
    (r'\b(he|she|it)\s+are\b', r'\1 is', 'subject_verb', 'he/she/it + is'),
    (r'\bthere\s+is\s+(many|several|various|numerous)\b', r'there are \1', 'grammar', 'many/several + there are'),
)

_ARTICLE_FIXES = (
    (r'\ba\s+information\b', 'information', 'article', 'information — artiklsiz'),
    (r'\ba\s+advice\b', 'advice', 'article', 'advice — artiklsiz'),
    (r'\ba\s+equipment\b', 'equipment', 'article', 'equipment — artiklsiz'),
    (r'\ba\s+furniture\b', 'furniture', 'article', 'furniture — artiklsiz'),
    (r'\ba\s+news\b', 'news', 'article', 'news — artiklsiz'),
    (r'\ba\s+research\b', 'research', 'article', 'research — artiklsiz ya da "a piece of research"'),
    (r'\ba\s+knowledge\b', 'knowledge', 'article', 'knowledge — artiklsiz'),
    (r'\ba\s+evidence\b', 'evidence', 'article', 'evidence — artiklsiz yoki "a piece of evidence"'),
)


def _normalize_phrase(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').strip())


def find_phrase_in_essay(essay: str, phrase: str) -> tuple[int, int] | None:
    phrase = _normalize_phrase(phrase)
    if not phrase or len(phrase) < 1:
        return None
    match = re.search(re.escape(phrase), essay, flags=re.IGNORECASE)
    if match:
        return match.start(), match.end()
    words = phrase.split()
    if len(words) >= 2:
        loose = r'\s+'.join(re.escape(w) for w in words)
        match = re.search(loose, essay, flags=re.IGNORECASE)
        if match:
            return match.start(), match.end()
    return None


def phrase_in_essay(essay: str, phrase: str) -> bool:
    return find_phrase_in_essay(essay, phrase) is not None


def _error_key(wrong: str, correct: str) -> str:
    return f'{wrong.lower()}=>{correct.lower()}'


def _make_error(wrong: str, correct: str, etype: str, why: str) -> dict[str, str]:
    return {
        'wrong': wrong[:120],
        'correct': correct[:120],
        'type': etype if etype in ERROR_TYPES else 'grammar',
        'why': (why or '')[:220],
    }


def extract_diff_errors(original: str, corrected: str, *, why: str = '', default_type: str = 'grammar', limit: int = 6) -> list[dict[str, str]]:
    """Ikki matn orasidagi so'z darajasidagi farqlarni xato sifatida ajratish."""
    original = _normalize_phrase(original)
    corrected = _normalize_phrase(corrected)
    if not original or not corrected or original.lower() == corrected.lower():
        return []

    ow = original.split()
    cw = corrected.split()
    if not ow or not cw:
        return []

    out: list[dict[str, str]] = []
    seen: set[str] = set()
    matcher = difflib.SequenceMatcher(None, ow, cw)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag not in {'replace', 'delete', 'insert'}:
            continue
        wrong = ' '.join(ow[i1:i2]).strip()
        correct = ' '.join(cw[j1:j2]).strip()
        if tag == 'delete' and wrong and not correct:
            correct = '(o\'chirish)'
        if tag == 'insert' and correct and not wrong:
            wrong = '(qo\'shish kerak)'
        if not wrong or not correct or wrong.lower() == correct.lower():
            continue
        if len(wrong.split()) > 8:
            continue
        key = _error_key(wrong, correct)
        if key in seen:
            continue
        seen.add(key)
        out.append(_make_error(wrong, correct, default_type, why or 'Gap tuzatish'))
        if len(out) >= limit:
            break
    return out


def detect_heuristic_errors(essay_text: str, *, limit: int = 15) -> list[dict[str, str]]:
    essay = essay_text or ''
    if not essay.strip():
        return []

    errors: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(wrong: str, correct: str, etype: str, why: str):
        if not wrong or not correct or wrong.lower() == correct.lower():
            return
        if not phrase_in_essay(essay, wrong):
            return
        key = _error_key(wrong, correct)
        if key in seen:
            return
        seen.add(key)
        span = find_phrase_in_essay(essay, wrong)
        actual_wrong = essay[span[0]:span[1]] if span else wrong
        errors.append(_make_error(actual_wrong, correct, etype, why))

    for pattern, correct, etype, why in _HEURISTIC_RULES:
        if correct is None:
            continue
        for match in re.finditer(pattern, essay, flags=re.IGNORECASE):
            _add(match.group(0), correct, etype, why)
            if len(errors) >= limit:
                return errors[:limit]

    for pattern, replacement, etype, why in _SUBJECT_VERB_FIXES:
        for match in re.finditer(pattern, essay, flags=re.IGNORECASE):
            wrong = match.group(0)
            correct = re.sub(pattern, replacement, wrong, count=1, flags=re.IGNORECASE)
            _add(wrong, correct, etype, why)
            if len(errors) >= limit:
                return errors[:limit]

    for pattern, correct, etype, why in _ARTICLE_FIXES:
        for match in re.finditer(pattern, essay, flags=re.IGNORECASE):
            _add(match.group(0), correct, etype, why)
            if len(errors) >= limit:
                return errors[:limit]

    # Lowercase "i" pronoun (not in words like "in", "is")
    for match in re.finditer(r'(?<![A-Za-z])i(?![A-Za-z])', essay):
        if match.group(0) == 'i':
            _add('i', 'I', 'capitalization', 'Shaxs olmosh I katta harf bilan')
            break

    # Sentence start lowercase
    for match in re.finditer(r'(?:^|[.!?]\s+)([a-z])', essay):
        letter = match.group(1)
        _add(letter, letter.upper(), 'capitalization', 'Gap boshida katta harf')
        if len(errors) >= limit:
            break

    return errors[:limit]


def errors_from_sentence_corrections(sentence_corrections, essay_text: str = '', *, limit: int = 8) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    grammar_types = {'grammar', 'spelling', 'punctuation', 'article', 'tense', 'preposition', 'subject_verb', 'plural'}

    for item in sentence_corrections or []:
        if not isinstance(item, dict):
            continue
        original = (item.get('original') or '').strip()
        corrected = (item.get('corrected') or '').strip()
        why = (item.get('why') or '').strip()
        ctype = str(item.get('type') or 'grammar').lower()
        if not original or not corrected:
            continue

        diff_errors = extract_diff_errors(
            original, corrected, why=why,
            default_type=ctype if ctype in grammar_types else 'grammar',
            limit=4,
        )
        for err in diff_errors:
            key = _error_key(err['wrong'], err['correct'])
            if key in seen:
                continue
            if essay_text and err['wrong'] not in ('(qo\'shish kerak)',) and not phrase_in_essay(essay_text, err['wrong']):
                if not phrase_in_essay(essay_text, original):
                    continue
            seen.add(key)
            out.append(err)
            if len(out) >= limit:
                return out

        if ctype in grammar_types or len(original.split()) <= 8:
            if essay_text and not phrase_in_essay(essay_text, original):
                continue
            key = _error_key(original, corrected)
            if key not in seen:
                seen.add(key)
                out.append(_make_error(
                    original, corrected,
                    ctype if ctype in grammar_types else 'grammar',
                    why,
                ))
        if len(out) >= limit:
            break
    return out[:limit]


def errors_from_vocabulary_upgrades(vocabulary_upgrades, essay_text: str, *, limit: int = 5) -> list[dict[str, str]]:
    essay = essay_text or ''
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in vocabulary_upgrades or []:
        if not isinstance(item, dict):
            continue
        frm = (item.get('from') or '').strip()
        to = (item.get('to') or '').split('/')[0].strip()
        why = (item.get('why') or 'Academic so\'z tanlovi').strip()
        if not frm or not to or frm.lower() == to.lower():
            continue
        if not phrase_in_essay(essay, frm):
            continue
        key = _error_key(frm, to)
        if key in seen:
            continue
        seen.add(key)
        span = find_phrase_in_essay(essay, frm)
        wrong = essay[span[0]:span[1]] if span else frm
        out.append(_make_error(wrong, to, 'word_choice', why))
        if len(out) >= limit:
            break
    return out


def validate_errors_in_essay(essay_text: str, errors: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Essayda yo'q xatolarni olib tashlash; wrong matnini essaydan olish."""
    essay = essay_text or ''
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in errors or []:
        if not isinstance(item, dict):
            continue
        wrong = (item.get('wrong') or item.get('error') or item.get('original') or '').strip()
        correct = (item.get('correct') or item.get('fixed') or item.get('corrected') or '').strip()
        if not wrong or not correct or wrong.lower() == correct.lower():
            continue
        if wrong.startswith('('):
            continue
        span = find_phrase_in_essay(essay, wrong)
        if not span:
            continue
        actual_wrong = essay[span[0]:span[1]]
        key = _error_key(actual_wrong, correct)
        if key in seen:
            continue
        seen.add(key)
        etype = str(item.get('type') or 'grammar').lower()
        cleaned.append(_make_error(actual_wrong, correct, etype, item.get('why') or ''))
    return cleaned


def merge_writing_errors(
    essay_text: str,
    *,
    ai_errors=None,
    sentence_corrections=None,
    vocabulary_upgrades=None,
    heuristic_limit: int = 15,
    total_limit: int = 16,
) -> list[dict[str, str]]:
    """AI + heuristic + diff + vocab — essayda tasdiqlangan yakuniy xatolar."""
    essay = essay_text or ''
    merged: list[dict[str, str]] = []
    seen: set[str] = set()

    def _extend(items: list[dict[str, str]]):
        nonlocal merged
        for item in items:
            key = _error_key(item['wrong'], item['correct'])
            if key in seen:
                continue
            if not phrase_in_essay(essay, item['wrong']):
                continue
            seen.add(key)
            span = find_phrase_in_essay(essay, item['wrong'])
            if span:
                item = dict(item)
                item['wrong'] = essay[span[0]:span[1]]
            merged.append(item)
            if len(merged) >= total_limit:
                return

    # 1) AI xatolari (validatsiya bilan)
    _extend(validate_errors_in_essay(essay, ai_errors))

    # 2) Heuristic (yuqori aniqlik)
    _extend(detect_heuristic_errors(essay, limit=heuristic_limit))

    # 3) Sentence correction diff
    _extend(errors_from_sentence_corrections(sentence_corrections, essay, limit=8))

    # 4) Vocab — essayda ishlatilgan oddiy so'zlar
    _extend(errors_from_vocabulary_upgrades(vocabulary_upgrades, essay, limit=5))

    return merged[:total_limit]
