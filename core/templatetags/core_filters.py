from django import template
import json

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

