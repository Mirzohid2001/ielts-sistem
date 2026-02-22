"""
New formatdagi IELTS testlarni bazaga yuklash.

Ishlatish:
  python manage.py load_new_format_tests
  python manage.py load_new_format_tests --wipe
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Category,
    Test,
    Question,
    UserTestAnswer,
    UserTestResult,
)


TESTS_PAYLOAD = [
    {
        "title": "Mixed Format - IELTS Reading Test 01",
        "test_type": "reading",
        "difficulty": "medium",
        "category_slug": "reading",
        "description": "Reading bo'limi uchun yangi formatdagi test (MCQ + TFNG + Summary + Matching).",
        "duration_minutes": 35,
        "passing_score": 60,
        "reading_text": (
            "Cities are introducing smart transport systems to reduce congestion and pollution. "
            "In the pilot program, buses were equipped with AI-based routing software. "
            "The first 6 months showed a reduction in fuel usage and average waiting time."
        ),
        "questions": [
            {
                "question_type": "mcq",
                "question_text": "What is the main purpose of the pilot program?",
                "option_a": "Increase ticket prices",
                "option_b": "Reduce congestion and pollution",
                "option_c": "Replace all buses",
                "option_d": "Build new roads",
                "correct_answer": "b",
            },
            {
                "question_type": "true_false_not_given",
                "question_text": "The passage states that all city buses were replaced.",
                "option_a": "True",
                "option_b": "False",
                "option_c": "Not Given",
                "correct_answer": "b",
            },
            {
                "question_type": "summary_completion",
                "question_text": "Complete the summary. Blanks: [1] [2] [3].",
                "options_json": {"instruction": "ONE WORD ONLY", "blanks_count": 3},
                "correct_answer_json": ["smart", "fuel", "waiting"],
            },
            {
                "question_type": "matching_headings",
                "question_text": "Match each section to the best heading.",
                "options_json": {
                    "instruction": "Match paragraph to heading",
                    "items": [
                        {"num": 1, "label": "Paragraph A"},
                        {"num": 2, "label": "Paragraph B"},
                        {"num": 3, "label": "Paragraph C"},
                    ],
                    "headings": [
                        {"letter": "i", "text": "Project background"},
                        {"letter": "ii", "text": "Technology details"},
                        {"letter": "iii", "text": "Measured outcomes"},
                    ],
                },
                "correct_answer_json": {"1": "i", "2": "ii", "3": "iii"},
            },
        ],
    },
    {
        "title": "Mixed Format - IELTS Listening Test 01",
        "test_type": "listening",
        "difficulty": "medium",
        "category_slug": "listening",
        "description": "Listening format: Notes + Table + List selection + Y/N/NG.",
        "duration_minutes": 30,
        "passing_score": 60,
        "questions": [
            {
                "question_type": "notes_completion",
                "question_text": "Fill the notes: [1] [2] [3]",
                "options_json": {"instruction": "ONE WORD ONLY", "blanks_count": 3},
                "correct_answer_json": ["library", "Monday", "passport"],
            },
            {
                "question_type": "table_completion",
                "question_text": "Complete the table: [1] [2]",
                "options_json": {"instruction": "NO MORE THAN ONE WORD", "blanks_count": 2},
                "correct_answer_json": ["north", "terminal"],
            },
            {
                "question_type": "list_selection",
                "question_text": "Choose TWO facilities available in the center.",
                "options_json": {
                    "instruction": "Choose TWO answers",
                    "options": [
                        {"letter": "A", "text": "Free Wi-Fi"},
                        {"letter": "B", "text": "Indoor pool"},
                        {"letter": "C", "text": "Study room"},
                        {"letter": "D", "text": "Cinema"},
                    ],
                },
                "correct_answer_json": ["A", "C"],
            },
            {
                "question_type": "yes_no_not_given",
                "question_text": "The speaker recommends arriving 30 minutes earlier.",
                "option_a": "Yes",
                "option_b": "No",
                "option_c": "Not Given",
                "correct_answer": "a",
            },
        ],
    },
    {
        "title": "Mixed Format - IELTS Writing Test 01",
        "test_type": "writing",
        "difficulty": "medium",
        "category_slug": "writing",
        "description": "Writing task with inline blanks ([1], [2], [3]).",
        "duration_minutes": 20,
        "passing_score": 60,
        "questions": [
            {
                "question_type": "summary_completion",
                "question_text": (
                    "Complete the summary. Blanks: "
                    "The report shows [1] growth in online sales, while [2] stores saw a slight decline in [3]."
                ),
                "options_json": {"instruction": "ONE WORD ONLY", "blanks_count": 3},
                "correct_answer_json": ["steady", "physical", "footfall"],
            }
        ],
    },
    {
        "title": "Mixed Format - IELTS Reading Test 02",
        "test_type": "reading",
        "difficulty": "easy",
        "category_slug": "reading",
        "description": "Reading easy set: MCQ + Fill blank + Yes/No/Not Given.",
        "duration_minutes": 28,
        "passing_score": 60,
        "reading_text": (
            "Local communities introduced bicycle lanes in central districts. "
            "As a result, daily car usage declined and public health indicators improved."
        ),
        "questions": [
            {
                "question_type": "mcq",
                "question_text": "What was introduced in central districts?",
                "option_a": "New airports",
                "option_b": "Bicycle lanes",
                "option_c": "Underground tunnels",
                "option_d": "Railway stations",
                "correct_answer": "b",
            },
            {
                "question_type": "fill_blank",
                "question_text": "Daily _____ usage declined after the new lanes.",
                "options_json": {"instruction": "ONE WORD ONLY", "blanks_count": 1},
                "correct_answer_json": ["car"],
            },
            {
                "question_type": "yes_no_not_given",
                "question_text": "The report says public health improved.",
                "option_a": "Yes",
                "option_b": "No",
                "option_c": "Not Given",
                "correct_answer": "a",
            },
        ],
    },
    {
        "title": "Mixed Format - IELTS Listening Test 02",
        "test_type": "listening",
        "difficulty": "hard",
        "category_slug": "listening",
        "description": "Listening hard set: sentence completion + matching + list selection.",
        "duration_minutes": 32,
        "passing_score": 65,
        "questions": [
            {
                "question_type": "sentence_completion",
                "question_text": "The meeting will start at [1] and finish at [2].",
                "options_json": {"instruction": "NO MORE THAN ONE WORD/NUMBER", "blanks_count": 2},
                "correct_answer_json": ["9", "noon"],
            },
            {
                "question_type": "matching_features",
                "question_text": "Match each speaker with the correct opinion.",
                "options_json": {
                    "instruction": "Match speakers to opinions",
                    "items": [
                        {"num": 1, "label": "Speaker A"},
                        {"num": 2, "label": "Speaker B"},
                        {"num": 3, "label": "Speaker C"},
                    ],
                    "headings": [
                        {"letter": "A", "text": "Supports online classes"},
                        {"letter": "B", "text": "Prefers face-to-face"},
                        {"letter": "C", "text": "Undecided"},
                    ],
                },
                "correct_answer_json": {"1": "A", "2": "B", "3": "C"},
            },
            {
                "question_type": "list_selection",
                "question_text": "Choose TWO required documents.",
                "options_json": {
                    "instruction": "Choose TWO answers",
                    "options": [
                        {"letter": "A", "text": "Passport"},
                        {"letter": "B", "text": "ID card"},
                        {"letter": "C", "text": "Library card"},
                        {"letter": "D", "text": "Utility bill"},
                    ],
                },
                "correct_answer_json": ["A", "B"],
            },
        ],
    },
    {
        "title": "Mixed Format - IELTS Writing Test 02",
        "test_type": "writing",
        "difficulty": "medium",
        "category_slug": "writing",
        "description": "Writing second set: inline blanks and short answer style.",
        "duration_minutes": 22,
        "passing_score": 60,
        "questions": [
            {
                "question_type": "summary_completion",
                "question_text": "Complete: The chart indicates [1] demand during [2], followed by [3] in winter.",
                "options_json": {"instruction": "ONE WORD ONLY", "blanks_count": 3},
                "correct_answer_json": ["higher", "summer", "decline"],
            },
            {
                "question_type": "short_answer",
                "question_text": "Write one word: What is the main trend described in the report?",
                "options_json": {"instruction": "ONE WORD ONLY", "blanks_count": 1},
                "correct_answer_json": ["growth"],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Yangi formatdagi testlarni yuklaydi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Oldin mavjud test/result/savollarni tozalaydi.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["wipe"]:
            self.stdout.write("Old test ma'lumotlari tozalanmoqda...")
            UserTestAnswer.objects.all().delete()
            UserTestResult.objects.all().delete()
            Question.objects.all().delete()
            Test.objects.all().delete()
            self.stdout.write(self.style.WARNING("Test ma'lumotlari tozalandi."))

        categories = self._ensure_categories()
        created_tests = 0
        updated_tests = 0
        created_questions = 0

        for test_data in TESTS_PAYLOAD:
            category = categories[test_data["category_slug"]]
            test, created = Test.objects.update_or_create(
                title=test_data["title"],
                category=category,
                defaults={
                    "test_type": test_data["test_type"],
                    "difficulty": test_data["difficulty"],
                    "description": test_data.get("description", ""),
                    "duration_minutes": test_data.get("duration_minutes"),
                    "passing_score": test_data.get("passing_score", 60),
                    "reading_text": test_data.get("reading_text", ""),
                    "is_active": True,
                },
            )
            if created:
                created_tests += 1
            else:
                updated_tests += 1
                test.questions.all().delete()

            for idx, q in enumerate(test_data.get("questions", []), start=1):
                Question.objects.create(
                    test=test,
                    order=idx,
                    question_type=q.get("question_type", "mcq"),
                    question_text=q.get("question_text", ""),
                    option_a=q.get("option_a", ""),
                    option_b=q.get("option_b", ""),
                    option_c=q.get("option_c", ""),
                    option_d=q.get("option_d", ""),
                    correct_answer=q.get("correct_answer", ""),
                    correct_answer_json=q.get("correct_answer_json", []),
                    options_json=q.get("options_json", {}),
                    explanation=q.get("explanation", ""),
                    points=q.get("points", 1),
                )
                created_questions += 1

        self.stdout.write(self.style.SUCCESS("Yuklash yakunlandi."))
        self.stdout.write(self.style.SUCCESS(f"  Testlar: {created_tests}"))
        self.stdout.write(self.style.SUCCESS(f"  Yangilangan testlar: {updated_tests}"))
        self.stdout.write(self.style.SUCCESS(f"  Savollar: {created_questions}"))

    def _ensure_categories(self):
        defaults = {
            "reading": {"name": "Reading", "icon": "fas fa-book", "color": "#3b82f6", "order": 1},
            "listening": {"name": "Listening", "icon": "fas fa-headphones", "color": "#10b981", "order": 2},
            "writing": {"name": "Writing", "icon": "fas fa-pen", "color": "#f59e0b", "order": 3},
        }
        result = {}
        for slug, cfg in defaults.items():
            cat, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": cfg["name"],
                    "icon": cfg["icon"],
                    "color": cfg["color"],
                    "order": cfg["order"],
                    "description": f"{cfg['name']} testlari",
                    "is_active": True,
                },
            )
            result[slug] = cat
        return result
