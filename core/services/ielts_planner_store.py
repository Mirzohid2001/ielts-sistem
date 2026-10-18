"""IELTS Study Planner persistence with compare-and-swap revision."""
from __future__ import annotations

from typing import Any, Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import IELTSStudyPlan


def account_key_for(user) -> str:
    return f"user-{user.pk}"


def read_plan(user) -> dict[str, Any]:
    row = IELTSStudyPlan.objects.filter(user=user).only('revision', 'document').first()
    if row is None:
        return {'accountKey': account_key_for(user), 'revision': 0, 'document': None}
    return {
        'accountKey': account_key_for(user),
        'revision': int(row.revision),
        'document': row.document if isinstance(row.document, dict) else None,
    }


def write_plan(user, base_revision: int, document: dict) -> Optional[int]:
    """Atomically write document. Returns new revision or None on conflict."""
    if base_revision == 0:
        try:
            with transaction.atomic():
                IELTSStudyPlan.objects.create(
                    user=user,
                    revision=1,
                    document=document,
                )
            return 1
        except IntegrityError:
            return None

    with transaction.atomic():
        updated = IELTSStudyPlan.objects.filter(user=user, revision=base_revision).update(
            revision=base_revision + 1,
            document=document,
            updated_at=timezone.now(),
        )
        if updated == 1:
            return base_revision + 1
    return None
