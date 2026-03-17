from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Category, Test, Question, ReadingPassage


class Command(BaseCommand):
    help = "Demo uchun ideal namuna IELTS testlarini yaratadi (Listening, Reading, Writing)."

    def handle(self, *args, **options):
        with transaction.atomic():
            cat, _ = Category.objects.get_or_create(
                name="Demo IELTS",
                defaults={
                    "order": 1,
                    "description": "Admin uchun namunaviy IELTS testlar (Listening, Reading, Writing).",
                    "show_on_site": False,
                },
            )

            self.stdout.write(self.style.SUCCESS(f"Kategoriya: {cat.name}"))

            self._create_listening_demo(cat)
            self._create_reading_demo(cat)
            self._create_writing_demo(cat)

        self.stdout.write(self.style.SUCCESS("Demo testlar muvaffaqiyatli yaratildi."))

    # --- Helpers ---

    def _create_listening_demo(self, cat: Category):
        """
        Listening: 1 ta test, Part 1 uchun 10 ta MCQ (Questions 1–10).
        Audio fayl keyin admin orqali biriktiriladi.
        """
        test, created = Test.objects.get_or_create(
            title="Demo Listening Test 1",
            category=cat,
            test_type="listening",
            defaults={
                "difficulty": "medium",
                "description": "Namuna: Listening Part 1–4, Questions 1–40 (har partda 10 ta savol, MCQ).",
                "duration_minutes": 30,
                "passing_score": 60,
                "is_active": True,
            },
        )
        if not created:
            self.stdout.write(self.style.WARNING("Listening demo allaqachon mavjud – o‘tkazib yuborildi."))
            return

        # 40 ta MCQ: Part 1–4, har birida 10 ta savol (1–10, 11–20, 21–30, 31–40)
        questions = []
        current_order = 1
        for part in range(1, 5):
            for i in range(10):
                q_number = current_order
                q = Question(
                    test=test,
                    order=q_number,
                    question_type="mcq",
                    question_text=f"Question {q_number}: Example listening question matni (Part {part}).",
                    option_a="Option A",
                    option_b="Option B",
                    option_c="Option C",
                    option_d="Option D",
                    correct_answer="a",
                    options_json={
                        "instruction": "ONE WORD AND/OR A NUMBER (Listening uchun namuna).",
                        "part": part,
                    },
                    points=1,
                )
                questions.append(q)
                current_order += 1

        Question.objects.bulk_create(questions)
        self.stdout.write(self.style.SUCCESS("Listening demo testi yaratildi (40 ta savol, Part 1–4: har birida 10 tadan)."))

    def _create_reading_demo(self, cat: Category):
        """
        Reading: 1 ta test, 1 ta passage va 5 ta savol (Questions 1–5).
        """
        test, created = Test.objects.get_or_create(
            title="Demo Reading Test 1",
            category=cat,
            test_type="reading",
            defaults={
                "difficulty": "medium",
                "description": "Namuna: Reading – bitta passage va 5 ta savol (MCQ + True/False/Not Given).",
                "duration_minutes": 60,
                "passing_score": 60,
                "is_active": True,
            },
        )
        if not created:
            self.stdout.write(self.style.WARNING("Reading demo allaqachon mavjud – o‘tkazib yuborildi."))
            return

        passage = ReadingPassage.objects.create(
            test=test,
            order=1,
            title="Passage 1 – Family Visits",
            text=(
                "Many families enjoy visiting relatives who live in other cities. "
                "These visits can be short weekend trips or longer holidays. "
                "Planning the journey carefully helps everyone feel relaxed and prepared."
            ),
        )

        Question.objects.bulk_create(
            [
                Question(
                    test=test,
                    order=1,
                    question_type="mcq",
                    question_text="According to the passage, family visits can be:",
                    option_a="only long holidays",
                    option_b="only one-day trips",
                    option_c="both short trips and longer holidays",
                    option_d="only business trips",
                    correct_answer="c",
                    options_json={"part": 1},
                    points=1,
                ),
                Question(
                    test=test,
                    order=2,
                    question_type="true_false_not_given",
                    question_text="Families never visit relatives who live in other cities.",
                    correct_answer="b",  # FALSE
                    options_json={"part": 1},
                    points=1,
                ),
                Question(
                    test=test,
                    order=3,
                    question_type="true_false_not_given",
                    question_text="Planning the journey can help people feel relaxed.",
                    correct_answer="a",  # TRUE
                    options_json={"part": 1},
                    points=1,
                ),
                Question(
                    test=test,
                    order=4,
                    question_type="fill_blank",
                    question_text="Many families enjoy visiting ______ who live in other cities.",
                    correct_answer_json=["relatives"],
                    options_json={
                        "instruction": "ONE WORD ONLY",
                        "blanks_count": 1,
                        "part": 1,
                    },
                    points=1,
                ),
                Question(
                    test=test,
                    order=5,
                    question_type="short_answer",
                    question_text="What helps everyone feel relaxed and prepared?",
                    correct_answer_json=["planning the journey", "planning the trip"],
                    options_json={
                        "instruction": "Write NO MORE THAN THREE WORDS.",
                        "blanks_count": 1,
                        "part": 1,
                    },
                    points=1,
                ),
            ]
        )

        self.stdout.write(self.style.SUCCESS("Reading demo testi yaratildi (1 passage, 5 ta savol, Part 1: 1–5)."))

    def _create_writing_demo(self, cat: Category):
        """
        Writing: 1 ta test, Task 1 va Task 2 (ikki essay savol).
        """
        test, created = Test.objects.get_or_create(
            title="Demo Writing Test 1",
            category=cat,
            test_type="writing",
            defaults={
                "difficulty": "medium",
                "description": "Namuna: Writing Task 1 va Task 2 uchun namunaviy savollar.",
                "duration_minutes": 60,
                "passing_score": 0,  # Writing odatda qo‘l bilan baholanadi
                "is_active": True,
            },
        )
        if not created:
            self.stdout.write(self.style.WARNING("Writing demo allaqachon mavjud – o‘tkazib yuborildi."))
            return

        Question.objects.bulk_create(
            [
                Question(
                    test=test,
                    order=1,
                    question_type="essay",
                    question_text=(
                        "Task 1\n\n"
                        "You should spend about 20 minutes on this task.\n\n"
                        "The graph below shows how many students used three different study methods "
                        "over a ten-year period.\n\n"
                        "Summarise the information by selecting and reporting the main features, "
                        "and make comparisons where relevant."
                    ),
                    options_json={"part": 1},
                    points=0,
                ),
                Question(
                    test=test,
                    order=2,
                    question_type="essay",
                    question_text=(
                        "Task 2\n\n"
                        "You should spend about 40 minutes on this task.\n\n"
                        "Some people think that studying online is as effective as studying in a "
                        "traditional classroom, while others disagree.\n\n"
                        "Discuss both these views and give your own opinion."
                    ),
                    options_json={"part": 2},
                    points=0,
                ),
            ]
        )

        self.stdout.write(self.style.SUCCESS("Writing demo testi yaratildi (Task 1 va Task 2)."))

