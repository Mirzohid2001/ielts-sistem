"""Vocabulary Lab page + account API."""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from core.services.vocabulary_lab_i18n import vocabulary_lab_js_strings
from core.services.vocabulary_lab_store import account_key_for, read_progress, write_progress
from core.services.vocabulary_lab_validate import validate_document


def _no_store(response: JsonResponse) -> JsonResponse:
    response['Cache-Control'] = 'private, no-store'
    response['Vary'] = 'Cookie'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@ensure_csrf_cookie
def vocabulary_lab(request):
    return render(request, 'core/vocabulary/index.html', {
        'vocab_boot': {
            'apiUrl': reverse('core:vocabulary_lab_api'),
            'dashboardUrl': reverse('core:dashboard'),
            'plannerUrl': reverse('core:study_planner'),
            'writingUrl': reverse('core:practice_skill', kwargs={'skill': 'writing'}),
        },
        'vocab_i18n': vocabulary_lab_js_strings(),
    })


@login_required
@require_http_methods(['GET', 'PUT'])
def vocabulary_lab_api(request):
    if request.method == 'GET':
        return _no_store(JsonResponse(read_progress(request.user)))

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

    new_revision = write_progress(request.user, base_revision, document)
    if new_revision is None:
        return _no_store(JsonResponse({'error': 'REVISION_CONFLICT'}, status=409))

    return _no_store(JsonResponse({
        'accountKey': expected_key,
        'revision': new_revision,
    }))
