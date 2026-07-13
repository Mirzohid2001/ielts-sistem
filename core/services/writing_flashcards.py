"""AI vocabulary_upgrades dan flashcard yaratish."""

from __future__ import annotations

from core.models import Flashcard, FlashcardSet


def default_set_name(*, test_title='', task_label=''):
    title = (test_title or 'Writing').strip()[:60]
    task = (task_label or '').strip()
    if task:
        return f'IELTS Writing · {title} · {task}'[:120]
    return f'IELTS Writing · {title}'[:120]


def create_flashcards_from_feedback(user, feedback, *, test=None, question=None):
    """
    vocabulary_upgrades dan flashcard qo'shadi.
    Qaytaradi: {created, skipped, set_id, set_name}
    """
    upgrades = feedback.vocabulary_upgrades if isinstance(feedback.vocabulary_upgrades, list) else []
    if not upgrades:
        return {'created': 0, 'skipped': 0, 'set_id': None, 'set_name': ''}

    test = test or feedback.test_result.test
    question = question or feedback.question
    task_label = ''
    if question and question.options_json:
        task_label = str(question.options_json.get('part') or question.options_json.get('part_label') or '')
    if task_label == '1':
        task_label = 'Task 1'
    elif task_label == '2':
        task_label = 'Task 2'

    set_name = default_set_name(test_title=test.title, task_label=task_label)
    flashcard_set, _ = FlashcardSet.objects.get_or_create(user=user, name=set_name)

    existing_terms = set(
        Flashcard.objects
        .filter(user=user, flashcard_set=flashcard_set)
        .values_list('term', flat=True)
    )
    created = 0
    skipped = 0
    for item in upgrades:
        if not isinstance(item, dict):
            continue
        term = (item.get('from') or '').strip()
        upgraded = (item.get('to') or '').strip()
        why = (item.get('why') or '').strip()
        if not term or not upgraded:
            skipped += 1
            continue
        key = term.lower()
        if key in existing_terms:
            skipped += 1
            continue
        definition_parts = [f'→ {upgraded}']
        if why:
            definition_parts.append(why)
        Flashcard.objects.create(
            user=user,
            flashcard_set=flashcard_set,
            term=term[:255],
            definition=' · '.join(definition_parts)[:2000],
            source_test=test,
            source_question=question,
        )
        existing_terms.add(key)
        created += 1

    return {
        'created': created,
        'skipped': skipped,
        'set_id': flashcard_set.pk,
        'set_name': flashcard_set.name,
    }
