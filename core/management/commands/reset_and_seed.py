"""
Bazadagi barcha test ma'lumotlarini to'liq o'chirib, yangi ideal testlarni qo'shadi.
- Testlar, savollar, passage'lar, natijalar, javoblar o'chiriladi.
- Kategoriyalar qayta yaratiladi (yoki mavjud bo'lsa saqlanadi).
- Ideal Reading (3 ta), Listening (3 ta), Writing (3 ta) testlar qo'shiladi.

Ishlatish:
  python manage.py reset_and_seed
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.management import call_command

from core.models import (
    Category,
    Test,
    Question,
    ReadingPassage,
    UserTestAnswer,
    UserTestResult,
)

# seed_new_format dan funksiyalarni import qilamiz
from core.management.commands.seed_new_format import (
    ensure_categories,
    create_reading_tests,
    create_listening_tests,
    create_writing_tests,
)


class Command(BaseCommand):
    help = (
        "Bazadagi barcha test ma'lumotlarini to'liq o'chirib, "
        "yangi ideal Reading, Listening, Writing testlarni qo'shadi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-seed",
            action="store_true",
            help="Faqat test ma'lumotlarini o'chirish, testlar qo'shilmasin.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        no_seed = options.get("no_seed", False)

        # 1) Bog'liqlik tartibida o'chirish
        self.stdout.write("Test ma'lumotlari o'chirilmoqda...")

        deleted_answers = UserTestAnswer.objects.count()
        UserTestAnswer.objects.all().delete()

        deleted_results = UserTestResult.objects.count()
        UserTestResult.objects.all().delete()

        deleted_questions = Question.objects.count()
        Question.objects.all().delete()

        deleted_passages = ReadingPassage.objects.count()
        ReadingPassage.objects.all().delete()

        deleted_tests = Test.objects.count()
        Test.objects.all().delete()

        self.stdout.write(
            self.style.WARNING(
                f"O'chirildi: {deleted_tests} ta test, {deleted_questions} ta savol, "
                f"{deleted_passages} ta passage, {deleted_results} ta natija, {deleted_answers} ta javob."
            )
        )

        if no_seed:
            self.stdout.write(self.style.SUCCESS("Baza tozalandi. --no-seed berilgani uchun testlar qo'shilmadi."))
            return

        # 2) Kategoriyalar
        categories = ensure_categories()
        self.stdout.write("Kategoriyalar tekshirildi / yaratildi.")

        # 3) Ideal Reading testlar (3 ta: TEST1, TEST2, qisqa)
        n_reading = create_reading_tests(categories)
        self.stdout.write(self.style.SUCCESS(f"Reading: {n_reading} ta ideal test qo'shildi."))

        # 4) Ideal Listening testlar (3 ta, har biri 4 part, 40 savol)
        n_listening = create_listening_tests(categories)
        self.stdout.write(self.style.SUCCESS(f"Listening: {n_listening} ta ideal test qo'shildi."))

        # 5) Ideal Writing testlar (3 ta, har biri Task 1 + Task 2)
        n_writing = create_writing_tests(categories)
        self.stdout.write(self.style.SUCCESS(f"Writing: {n_writing} ta ideal test qo'shildi."))

        total = n_reading + n_listening + n_writing
        self.stdout.write(self.style.SUCCESS(f"Jami: {total} ta ideal test bazaga qo'shildi."))

        # 6) Qo'shimcha "coverage" testlar (bitta savol turi bo'yicha namuna)
        #    — list_selection, matching_headings, sentence_completion va b. tiplar bo'sh qolmasin.
        self.stdout.write("Qo'shimcha: seed_tests_by_question_type (no-delete) ishlayapti...")
        call_command("seed_tests_by_question_type", "--no-delete", verbosity=0)
        self.stdout.write(self.style.SUCCESS("Qo'shimcha coverage testlar qo'shildi (seed_tests_by_question_type)."))
