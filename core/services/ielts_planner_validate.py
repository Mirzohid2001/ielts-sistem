"""IELTS Study Planner document validation (IT package kontrakti bilan mos)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Optional

MAX_BYTES = 16 * 1024 * 1024
SKILLS = ('Listening', 'Reading', 'Writing', 'Speaking')
DAILY_MINUTES = (60, 90, 120, 150, 180, 210, 240)
TASK_DURATIONS = (15, 30, 45, 60, 90, 120)
PHASES = ('foundation', 'practice', 'mock', 'review')
RESOURCE_KEYS = frozenset({
    'speakingShadowing', 'speakingQuestions', 'speakingRecording',
    'readingVideo', 'writingVideo', 'listeningVideo', 'grammarVideo',
    'readingExercise', 'writingExercise',
    'cdiReading', 'cdiListening', 'cdiWriting',
    'video', 'reading', 'listening', 'platform', 'writing', 'live',
})
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TIME_RE = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')


def _is_str(value: Any, max_len: int = 5000) -> bool:
    return isinstance(value, str) and len(value) <= max_len


def _is_date(value: Any) -> bool:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        parsed = datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return False
    return parsed.isoformat() == value


def _is_time(value: Any) -> bool:
    return isinstance(value, str) and bool(TIME_RE.match(value))


def _is_band(value: Any, minimum: float = 0) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    if number < minimum or number > 9:
        return False
    return abs(number * 2 - round(number * 2)) < 1e-9


def _minutes(value: str) -> int:
    hours, mins = value.split(':')
    return int(hours) * 60 + int(mins)


def validate_document(doc: Any) -> Optional[str]:
    if not isinstance(doc, dict) or doc.get('version') != 1:
        return 'INVALID_DOCUMENT'
    if doc.get('view') not in ('list', 'calendar'):
        return 'INVALID_DOCUMENT'
    plan = doc.get('plan')
    if not isinstance(plan, dict):
        return 'INVALID_DOCUMENT'

    profile = plan.get('profile')
    if plan.get('contentVersion') != 3:
        return 'INVALID_PLAN'
    if not _is_date(plan.get('startDate')) or not _is_date(plan.get('generatedAt')):
        return 'INVALID_PLAN'
    if not isinstance(profile, dict) or not _is_date(profile.get('exam')):
        return 'INVALID_PLAN'
    if plan['startDate'] > profile['exam'] or plan['generatedAt'] >= profile['exam']:
        return 'INVALID_PLAN'
    start = date.fromisoformat(plan['startDate'])
    exam = date.fromisoformat(profile['exam'])
    if (exam - start).days > 3650:
        return 'PLAN_HISTORY_TOO_LONG'

    scores = profile.get('scores')
    if not isinstance(scores, dict) or any(not _is_band(scores.get(skill)) for skill in SKILLS):
        return 'INVALID_SCORES'
    if not _is_band(profile.get('target'), 1):
        return 'INVALID_SCORES'

    days = profile.get('days')
    if (
        not isinstance(days, list)
        or not days
        or any(not isinstance(day, int) or day < 0 or day > 6 for day in days)
        or len(set(days)) != len(days)
    ):
        return 'INVALID_DAYS'

    if profile.get('minutes') not in DAILY_MINUTES:
        return 'INVALID_DAILY_BUDGET'
    if not _is_time(profile.get('time')) or _minutes(profile['time']) + int(profile['minutes']) > 1440:
        return 'INVALID_DAILY_BUDGET'

    weak = profile.get('weak')
    if not isinstance(weak, list) or any(skill not in SKILLS for skill in weak):
        return 'INVALID_WEAK_SKILLS'

    tasks = plan.get('tasks')
    if not isinstance(tasks, list) or len(tasks) > 12000:
        return 'TOO_MANY_TASKS'

    seen_ids: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            return 'INVALID_TASK'
        task_id = task.get('id')
        if not _is_str(task_id, 160) or not task_id or task_id in seen_ids:
            return 'INVALID_TASK'
        seen_ids.add(task_id)
        if task.get('skill') not in SKILLS or task.get('resource') not in RESOURCE_KEYS:
            return 'INVALID_TASK'
        if not isinstance(task.get('done'), bool):
            return 'INVALID_TASK'
        if (
            not _is_date(task.get('date'))
            or not _is_time(task.get('time'))
            or task.get('duration') not in TASK_DURATIONS
            or _minutes(task['time']) + int(task['duration']) > 1440
        ):
            return 'INVALID_TASK_TIME'
        if not task['done'] and task['date'] >= profile['exam']:
            return 'TASK_AFTER_EXAM'
        if not _is_str(task.get('title'), 500) or not _is_str(task.get('description')) or not _is_str(task.get('source')):
            return 'INVALID_TASK_TEXT'
        steps = task.get('steps')
        if (
            not isinstance(steps, list)
            or len(steps) > 12
            or any(
                not isinstance(step, dict)
                or not isinstance(step.get('minutes'), int)
                or step['minutes'] <= 0
                or not _is_str(step.get('text'))
                for step in steps
            )
            or sum(step['minutes'] for step in steps) != task['duration']
        ):
            return 'INVALID_STEPS'
        for key in ('outcome', 'checkpoint', 'ifStuck', 'reviewNext'):
            if task.get(key) is not None and not _is_str(task.get(key)):
                return 'INVALID_TASK_TEXT'
        if not task['done']:
            if (
                not isinstance(task.get('lessonIndex'), int)
                or task['lessonIndex'] < 0
                or task.get('phaseKey') not in PHASES
                or task.get('contentVersion') != 3
            ):
                return 'INVALID_TASK_CONTENT'

    try:
        encoded = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError):
        return 'INVALID_DOCUMENT'
    if len(encoded) > MAX_BYTES:
        return 'DOCUMENT_TOO_LARGE'
    return None
