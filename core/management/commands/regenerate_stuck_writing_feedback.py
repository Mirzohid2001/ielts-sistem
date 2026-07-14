"""Stuck pending AI writing feedbackni qayta ishlash.

Usage:
  python manage.py regenerate_stuck_writing_feedback
  python manage.py regenerate_stuck_writing_feedback --result-id 434
  python manage.py regenerate_stuck_writing_feedback --minutes 5 --sync
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import AIWritingFeedback, UserTestResult
from core.services.ai_writing_feedback import generate_writing_feedback_for_result


class Command(BaseCommand):
    help = "Pending holatda qolib ketgan writing AI feedbacklarni qayta generatsiya qiladi."

    def add_arguments(self, parser):
        parser.add_argument('--result-id', type=int, help='Bitta UserTestResult id')
        parser.add_argument(
            '--minutes',
            type=int,
            default=2,
            help='Shu daqiqadan eski pendinglar (default: 2)',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Fon emas, darhol ishlash (tavsiya)',
        )

    def handle(self, *args, **options):
        result_id = options.get('result_id')
        minutes = options['minutes']
        cutoff = timezone.now() - timedelta(minutes=minutes)

        if result_id:
            qs = UserTestResult.objects.filter(pk=result_id, test__test_type='writing')
        else:
            pending_result_ids = (
                AIWritingFeedback.objects
                .filter(status=AIWritingFeedback.STATUS_PENDING, updated_at__lte=cutoff)
                .values_list('test_result_id', flat=True)
                .distinct()
            )
            qs = UserTestResult.objects.filter(pk__in=pending_result_ids).select_related('test')

        count = 0
        for result in qs.select_related('test'):
            self.stdout.write(f'Generating for result #{result.pk} ({result.test.title})...')
            generated = generate_writing_feedback_for_result(result, force=True)
            statuses = ', '.join(f'{f.pk}:{f.status}' for f in generated)
            self.stdout.write(self.style.SUCCESS(f'  OK → {statuses or "no essays"}'))
            count += 1

        if count == 0:
            self.stdout.write('Stuck pending topilmadi.')
        else:
            self.stdout.write(self.style.SUCCESS(f'Jami {count} ta natija qayta ishlandi.'))
