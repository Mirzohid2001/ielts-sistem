from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
import json
import re

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Dictionary dan key bo'yicha qiymat olish"""
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def get_option(question, option_key):
    """Savol variantini olish (MCQ/True-False uchun)"""
    if not option_key:
        return ''
    opt = str(option_key).lower()
    if opt in ('a', 'b', 'c', 'd'):
        options = {
            'a': question.option_a,
            'b': question.option_b,
            'c': question.option_c,
            'd': question.option_d,
        }
        return options.get(opt, '')
    # Fill-in, summary, notes - to'g'ridan-to'g'ri qiymatni qaytarish
    return str(option_key)


@register.filter
def display_user_answer(question, user_answer):
    """Foydalanuvchi javobini savol turiga qarab to'g'ri ko'rsatish (1 yoki 2 ta variant, matn bilan)."""
    if not question:
        return format_user_answer(user_answer)
    return question.get_user_answer_display(user_answer) or ''


@register.filter
def format_instruction(text):
    """
    IELTS instruction matnida kalit so'z va oraliklarni qalin (bold) qiladi.
    Skrinshotlar bilan 1:1: TRUE/FALSE/NOT GIVEN, A-F, A E, ONE WORD ONLY.
    """
    if not text:
        return ''
    text = str(text).strip()
    escaped = escape(text)
    # Kalit so'zlar: TRUE, FALSE, NOT GIVEN, YES, NO
    for word in ('TRUE', 'FALSE', 'NOT GIVEN', 'YES', 'NO'):
        escaped = re.sub(r'\b' + re.escape(word) + r'\b', f'<strong>{word}</strong>', escaped, flags=re.IGNORECASE)
    # Instruction: ONE WORD ONLY, ONE WORD AND/OR A NUMBER
    for phrase in ('ONE WORD ONLY', 'ONE WORD AND/OR A NUMBER'):
        escaped = re.sub(r'\b' + re.escape(phrase) + r'\b', f'<strong>{phrase}</strong>', escaped, flags=re.IGNORECASE)
    # Matching: harf oraliklari A-F, A–F (en dash), A-E, A-G va "A E" (ikki harf orasida bo'shliq)
    escaped = re.sub(r'\b([A-Z])\s*[-–]\s*([A-Z])\b', r'<strong>\1–\2</strong>', escaped)
    escaped = re.sub(r'\b([A-Z])\s+([A-Z])\b', r'<strong>\1 \2</strong>', escaped)
    escaped = escaped.replace('\n', '<br>')
    return mark_safe(escaped)


@register.filter
def format_user_answer(value):
    """Foydalanuvchi javobini ko'rsatish uchun formatlash (JSON ro'yxat/dict bo'lsa)"""
    if value is None:
        return ''
    if isinstance(value, str):
        s = value.strip()
        if s.startswith('['):
            try:
                data = json.loads(s)
                if isinstance(data, list):
                    return ', '.join(str(x) for x in data)
                if isinstance(data, dict):
                    return '; '.join(f'{k}:{v}' for k, v in sorted(data.items()))
            except (json.JSONDecodeError, TypeError):
                pass
        return s
    if isinstance(value, list):
        return ', '.join(str(x) for x in value)
    if isinstance(value, dict):
        return '; '.join(f'{k}:{v}' for k, v in sorted(value.items()))
    return str(value)


@register.filter
def matching_slots_score(question, user_answer):
    """
    Matching turlari uchun qisman ball: (got, total) qaytaradi.
    Template’da ishlatish uchun got va total alohida filterlar bilan ham foydalanish mumkin.
    """
    if not question:
        return (0, 0)
    try:
        if getattr(question, 'question_type', None) not in (
            'matching_headings',
            'matching_features',
            'matching_info',
            'matching_sentences',
            'classification',
        ):
            return (0, 0)
        got, total = question.score_matching_answer(user_answer)
        return (int(got or 0), int(total or 0))
    except Exception:
        return (0, 0)


@register.filter
def matching_slots_correct(question, user_answer):
    got, total = matching_slots_score(question, user_answer)
    return got


@register.filter
def matching_slots_total(question, user_answer):
    got, total = matching_slots_score(question, user_answer)
    return total


@register.filter
def matching_review_state(question, user_answer):
    """
    Matching turlari uchun review holati:
    - 'correct'  : hamma slot to'g'ri
    - 'partial'  : ba'zi slot to'g'ri
    - 'wrong'     : hech bo'lmaganda slot noto'g'ri (yoki jami 0)
    - ''          : matching bo'lmasa
    """
    if not question:
        return ''

    matching_types = (
        'matching_headings',
        'matching_features',
        'matching_info',
        'matching_sentences',
        'classification',
    )
    if getattr(question, 'question_type', None) not in matching_types:
        return ''

    user_answer = (user_answer or '').strip()
    got, total = matching_slots_score(question, user_answer)
    if total and got >= total:
        return 'correct'
    if total and got > 0:
        return 'partial'
    return 'wrong'


@register.filter
def mcq_choose_two_score_label(question, user_answer):
    """Choose TWO: '1/2' kabi qisqa ball ko'rsatkich (natija sahifasi)."""
    if not question:
        return ''
    single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
    if getattr(question, 'question_type', None) not in single_choice:
        return ''
    if getattr(question, 'max_choices', 1) != 2:
        return ''
    try:
        pts, total = question.score_mcq_choose_two_dual(user_answer)
        return f'{pts}/{total}'
    except Exception:
        return ''


@register.filter
def answer_slot_review_state(question, user_answer):
    """
    Matching yoki ko'p bo'sh joyli fill (notes/summary/...) uchun review holati:
    'correct' | 'partial' | 'wrong' | '' (boshqa savol turlari).
    """
    if not question:
        return ''

    qt = getattr(question, 'question_type', None)
    matching_types = (
        'matching_headings',
        'matching_features',
        'matching_info',
        'matching_sentences',
        'classification',
    )
    fill_types = (
        'fill_blank',
        'summary_completion',
        'notes_completion',
        'sentence_completion',
        'table_completion',
        'short_answer',
    )
    if qt in matching_types:
        return matching_review_state(question, user_answer)
    if qt in fill_types:
        user_answer = (user_answer or '').strip()
        if not user_answer:
            return 'wrong'
        try:
            got, total = question.score_fill_answer(user_answer)
        except Exception:
            return 'wrong'
        if total and got >= total:
            return 'correct'
        if total and got > 0:
            return 'partial'
        return 'wrong'

    # MCQ / T-F / T-F-NG / Y-N-NG: 2 ta variant tanlash — qisman to'g'ri (masalan B+D kerak, B+C berilgan)
    single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
    if qt in single_choice and getattr(question, 'max_choices', 1) == 2:
        try:
            pts, total = question.score_mcq_choose_two_dual(user_answer)
        except Exception:
            return 'wrong'
        if not total:
            return 'wrong'
        if pts >= total:
            return 'correct'
        if pts > 0:
            return 'partial'
        return 'wrong'

    return ''

