"""Sayt tili (o'zbekcha / ruscha). Admin bu yerdan o'tmaydi."""

import json

from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.services.ai_language import attach_ai_lang_cookie, persist_ai_language


def _safe_next_url(request):
    candidate = request.POST.get('next') or request.GET.get('next') or ''
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        if not candidate.startswith('/lang'):
            return candidate
    referer = request.META.get('HTTP_REFERER') or ''
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return referer
    if request.user.is_authenticated:
        return '/'
    return '/accounts/login/'


@require_POST
def set_site_language(request):
    body = {}
    content_type = (request.content_type or '')
    if content_type.startswith('application/json'):
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            body = {}
    lang = persist_ai_language(
        request,
        lang=body.get('ai_lang') or request.POST.get('ai_lang'),
    )
    translation.activate(lang)
    wants_json = (
        'application/json' in (request.headers.get('Accept') or '')
        or (request.content_type or '').startswith('application/json')
    )
    if wants_json:
        response = JsonResponse({'ok': True, 'lang': lang})
    else:
        response = redirect(_safe_next_url(request))
    attach_ai_lang_cookie(response, lang)
    return response
