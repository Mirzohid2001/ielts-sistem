"""Vocabulary Lab document shape validation (prototype ton-vocabulary-v1)."""
from __future__ import annotations

import json
from typing import Any, Optional

MAX_BYTES = 8 * 1024 * 1024
LEVELS = frozenset({'B1', 'B2', 'C1', 'C2'})
MODES = frozenset({'Learn', 'Practice', 'Challenge'})
STATUSES = frozenset({'NEW', 'LEARNING', 'RECOGNISED', 'RECALLED', 'USED', 'MASTERED'})


def validate_document(doc: Any) -> Optional[str]:
    if not isinstance(doc, dict) or doc.get('version') != 1:
        return 'INVALID_DOCUMENT'
    try:
        raw = json.dumps(doc, ensure_ascii=False).encode('utf-8')
    except (TypeError, ValueError):
        return 'INVALID_DOCUMENT'
    if len(raw) > MAX_BYTES:
        return 'DOCUMENT_TOO_LARGE'

    if doc.get('level') not in LEVELS:
        return 'INVALID_DOCUMENT'
    if doc.get('mode') not in MODES:
        return 'INVALID_DOCUMENT'
    count = doc.get('count')
    if not isinstance(count, int) or isinstance(count, bool) or count < 5 or count > 8:
        return 'INVALID_DOCUMENT'

    items = doc.get('items')
    if not isinstance(items, dict):
        return 'INVALID_DOCUMENT'
    if len(items) > 500:
        return 'DOCUMENT_TOO_LARGE'
    for key, item in items.items():
        if not isinstance(key, str) or len(key) > 64 or not isinstance(item, dict):
            return 'INVALID_DOCUMENT'
        if item.get('status') not in STATUSES:
            return 'INVALID_DOCUMENT'

    metrics = doc.get('metrics')
    if not isinstance(metrics, dict):
        return 'INVALID_DOCUMENT'
    history = doc.get('history')
    if not isinstance(history, list) or len(history) > 200:
        return 'INVALID_DOCUMENT'
    plan = doc.get('plan')
    if not isinstance(plan, dict):
        return 'INVALID_DOCUMENT'
    if not isinstance(plan.get('budget'), int) or isinstance(plan.get('budget'), bool):
        return 'INVALID_DOCUMENT'
    if not isinstance(plan.get('done'), list):
        return 'INVALID_DOCUMENT'
    if not isinstance(doc.get('events'), list):
        return 'INVALID_DOCUMENT'
    return None
