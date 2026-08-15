"""AI feedback tili: o'zbekcha (lotin) yoki ruscha."""

LANG_UZ = 'uz'
LANG_RU = 'ru'
SESSION_KEY = 'ai_lang'
COOKIE_NAME = 'ai_lang'
COOKIE_MAX_AGE = 365 * 24 * 60 * 60


def normalize_ai_lang(value) -> str:
    raw = (value or '').strip().lower().replace('_', '-')
    if raw in ('ru', 'rus', 'russian', 'ru-ru', 'рус', 'русский'):
        return LANG_RU
    return LANG_UZ


def learner_language_rules(lang: str) -> str:
    if normalize_ai_lang(lang) == LANG_RU:
        return (
            "LEARNER-FACING LANGUAGE = Russian.\n"
            "- All explanations, summaries, tips, why-texts, strengths, improvements, "
            "next_steps, coach replies, and trap notes MUST be in Russian.\n"
            "- Keep IELTS criterion names in English (TR, CC, LR, GRA, Task Achievement).\n"
            "- Keep the student's English answers, quotes, and vocabulary from/to in English.\n"
            "- Use clear Russian for B1–B2 learners. No Uzbek."
        )
    return (
        "LEARNER-FACING LANGUAGE = Uzbek (Latin script).\n"
        "- All explanations, summaries, tips, why-texts, strengths, improvements, "
        "next_steps, coach replies, and trap notes MUST be in Uzbek (Latin).\n"
        "- Keep IELTS criterion names in English (TR, CC, LR, GRA, Task Achievement).\n"
        "- Keep the student's English answers, quotes, and vocabulary from/to in English.\n"
        "- Use clear Uzbek for B1–B2 learners. No Russian."
    )


def t(lang: str, uz: str, ru: str) -> str:
    return ru if normalize_ai_lang(lang) == LANG_RU else uz


def get_ai_language(request=None, test_result=None) -> str:
    if request is not None:
        posted = getattr(request, 'POST', None)
        if posted:
            raw = posted.get('ai_lang')
            if raw:
                return normalize_ai_lang(raw)
        get = getattr(request, 'GET', None)
        if get:
            raw = get.get('ai_lang')
            if raw:
                return normalize_ai_lang(raw)
        session = getattr(request, 'session', None)
        if session is not None:
            raw = session.get(SESSION_KEY)
            if raw:
                return normalize_ai_lang(raw)
        cookies = getattr(request, 'COOKIES', None) or {}
        raw = cookies.get(COOKIE_NAME)
        if raw:
            return normalize_ai_lang(raw)
    if test_result is not None:
        raw = getattr(test_result, 'ai_language', None)
        if raw:
            return normalize_ai_lang(raw)
    return LANG_UZ


def language_for_result(test_result) -> str:
    return normalize_ai_lang(getattr(test_result, 'ai_language', None) or LANG_UZ)


def persist_ai_language(request, test_result=None, lang=None) -> str:
    """Session + natija yozuviga tilni yozish."""
    chosen = normalize_ai_lang(lang if lang is not None else get_ai_language(request, test_result))
    session = getattr(request, 'session', None) if request is not None else None
    if session is not None:
        session[SESSION_KEY] = chosen
        session.modified = True
    if test_result is not None and getattr(test_result, 'ai_language', None) != chosen:
        test_result.ai_language = chosen
        test_result.save(update_fields=['ai_language'])
    return chosen


def language_still_matches(test_result, lang: str) -> bool:
    """Fon thread eski tilni yangi til ustiga yozmasligi uchun."""
    if test_result is None:
        return True
    try:
        test_result.refresh_from_db(fields=['ai_language'])
    except Exception:
        return True
    return language_for_result(test_result) == normalize_ai_lang(lang)


def attach_ai_lang_cookie(response, lang: str):
    response.set_cookie(
        COOKIE_NAME,
        normalize_ai_lang(lang),
        max_age=COOKIE_MAX_AGE,
        samesite='Lax',
        httponly=False,
    )
    return response
