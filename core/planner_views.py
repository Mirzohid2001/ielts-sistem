"""IELTS Study Planner page + account API."""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from core.services.ielts_planner_i18n import planner_js_strings
from core.services.ielts_planner_store import account_key_for, read_plan, write_plan
from core.services.ielts_planner_validate import validate_document


def _no_store(response: JsonResponse) -> JsonResponse:
    response['Cache-Control'] = 'private, no-store'
    response['Vary'] = 'Cookie'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def _resource_routes() -> dict:
    """Ton platform ichidagi haqiqiy bo‘lim URLlari."""
    return {
        'readingVideo': f"{reverse('core:video_list')}?search=Reading",
        'writingVideo': f"{reverse('core:video_list')}?search=Writing",
        'listeningVideo': f"{reverse('core:video_list')}?search=Listening",
        'grammarVideo': reverse('core:practice_skill', kwargs={'skill': 'grammar'}),
        'readingExercise': reverse('core:practice_skill', kwargs={'skill': 'reading'}),
        'writingExercise': reverse('core:practice_skill', kwargs={'skill': 'writing'}),
        'cdiReading': reverse('core:test_collection_by_type', kwargs={'test_type': 'reading'}),
        'cdiListening': reverse('core:test_collection_by_type', kwargs={'test_type': 'listening'}),
        'cdiWriting': reverse('core:test_collection_by_type', kwargs={'test_type': 'writing'}),
    }


@login_required
@ensure_csrf_cookie
def study_planner(request):
    """Standalone planner UI (dizayn paketi bilan mos)."""
    return render(request, 'core/planner/index.html', {
        'planner_api_url': reverse('core:study_planner_api'),
        'dashboard_url': reverse('core:dashboard'),
        'planner_resource_routes': _resource_routes(),
        'planner_i18n': planner_js_strings(),
    })


@login_required
@require_http_methods(['GET', 'PUT'])
def study_planner_api(request):
    if request.method == 'GET':
        return _no_store(JsonResponse(read_plan(request.user)))

    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except (TypeError, ValueError, UnicodeDecodeError):
        return _no_store(JsonResponse({'error': 'INVALID_DOCUMENT'}, status=400))
    if not isinstance(body, dict):
        return _no_store(JsonResponse({'error': 'INVALID_DOCUMENT'}, status=400))

    expected_key = account_key_for(request.user)
    if body.get('accountKey') != expected_key:
        return _no_store(JsonResponse({'error': 'ACCOUNT_CHANGED'}, status=409))

    base_revision = body.get('baseRevision')
    if not isinstance(base_revision, int) or isinstance(base_revision, bool) or base_revision < 0:
        return _no_store(JsonResponse({'error': 'INVALID_REVISION'}, status=400))

    document = body.get('document')
    error = validate_document(document)
    if error:
        status = 413 if error == 'DOCUMENT_TOO_LARGE' else 422
        return _no_store(JsonResponse({'error': error}, status=status))

    new_revision = write_plan(request.user, base_revision, document)
    if new_revision is None:
        return _no_store(JsonResponse({'error': 'REVISION_CONFLICT'}, status=409))

    return _no_store(JsonResponse({
        'accountKey': expected_key,
        'revision': new_revision,
    }))
