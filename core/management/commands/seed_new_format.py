"""
Bazadagi barcha testlarni o'chirib, yangi formatda testlar qo'shish.
- Reading: 3 passage (ReadingPassage), Part 1/2/3
- Listening: 4 part, har testda 40 savol
- Writing: Task 1 + Task 2 (2 ta essay)

Ishlatish:
  python manage.py seed_new_format
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Category, Test, Question, ReadingPassage, UserTestAnswer, UserTestResult

from core.management.commands.refresh_reading_tests import build_reading_tests_full


def ensure_categories():
    """Kategoriyalar mavjudligini ta'minlash."""
    defaults = [
        {"slug": "reading", "name": "Reading", "icon": "fas fa-book", "color": "#3b82f6", "order": 1},
        {"slug": "listening", "name": "Listening", "icon": "fas fa-headphones", "color": "#10b981", "order": 2},
        {"slug": "writing", "name": "Writing", "icon": "fas fa-pen", "color": "#f59e0b", "order": 3},
        {"slug": "grammar", "name": "Grammar", "icon": "fas fa-language", "color": "#8b5cf6", "order": 4},
    ]
    result = {}
    for d in defaults:
        cat, _ = Category.objects.get_or_create(
            slug=d["slug"],
            defaults={
                "name": d["name"],
                "icon": d["icon"],
                "color": d["color"],
                "order": d["order"],
                "description": f"{d['name']} testlari",
                "is_active": True,
            },
        )
        result[d["slug"]] = cat
    return result


def create_reading_tests(categories):
    """Reading testlarni yangi formatda (ReadingPassage) yaratish."""
    cat = categories["reading"]
    tests_data = build_reading_tests_full()
    created = 0
    for tdata in tests_data:
        test = Test.objects.create(
            title=tdata["title"],
            category=cat,
            test_type="reading",
            difficulty=tdata["difficulty"],
            description=tdata.get("description", ""),
            duration_minutes=tdata.get("duration_minutes", 60),
            passing_score=tdata.get("passing_score", 60),
            reading_text="",
            is_active=True,
        )
        for p in tdata["passages"]:
            ReadingPassage.objects.create(
                test=test,
                order=p["order"],
                title=p["title"],
                text=p["text"],
            )
        for idx, q in enumerate(tdata["questions"], start=1):
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
                points=1,
            )
        created += 1
    return created


def _listening_notes_q(order, part, text, answers, inst="ONE WORD AND/OR A NUMBER"):
    return {
        "order": order,
        "question_type": "notes_completion",
        "question_text": text,
        "options_json": {"part": part, "instruction": inst, "blanks_count": len(answers)},
        "correct_answer_json": answers,
    }


def _listening_mcq(order, part, text, a, b, c, correct, d=""):
    opts = [{"letter": "a", "text": a}, {"letter": "b", "text": b}, {"letter": "c", "text": c}]
    if d:
        opts.append({"letter": "d", "text": d})
    return {
        "order": order,
        "question_type": "mcq",
        "question_text": text,
        "option_a": a, "option_b": b, "option_c": c, "option_d": d,
        "correct_answer": correct,
        "options_json": {"part": part, "options": opts},
    }


def build_listening_questions():
    """Bitta listening test uchun 40 savol (Part 1: 1-10, Part 2: 11-20, Part 3: 21-30, Part 4: 31-40)."""
    questions = []
    # Part 1 (1-10): notes 5 blanks + 5 MCQ
    questions.append(_listening_notes_q(1, 1,
        "Complete the notes. Write ONE WORD AND/OR A NUMBER.\n\n"
        "Student Accommodation\n"
        "Type: [1] room\n"
        "Rent: £ [2] per week\n"
        "Bills: [3]\n"
        "Contract: [4] months\n"
        "Available: [5] September",
        ["single", "120", "included", "12", "15th"]))
    for i in range(5):
        questions.append(_listening_mcq(2 + i, 1,
            f"Part 1 MCQ question {i+1}. What is the main topic?",
            "Option A", "Option B", "Option C", "b"))
    # Part 2 (11-20): notes 4 blanks + 6 MCQ
    questions.append(_listening_notes_q(11, 2,
        "Complete the notes. ONE WORD ONLY.\n\n"
        "Museum Visit\n"
        "Opening: [1] am\n"
        "Closing: [2] pm\n"
        "Ticket price: £ [3]\n"
        "Guide: [4] only on weekends",
        ["9", "5", "8", "available"]))
    for i in range(6):
        questions.append(_listening_mcq(12 + i, 2,
            f"Part 2 question {i+1}. Choose the best answer.",
            "A", "B", "C", "a"))
    # Part 3 (21-30): 10 MCQ
    for i in range(10):
        questions.append(_listening_mcq(21 + i, 3,
            f"Part 3 discussion question {i+1}. What do the speakers agree on?",
            "First option", "Second option", "Third option", "b"))
    # Part 4 (31-40): notes 6 blanks + 4 MCQ
    questions.append(_listening_notes_q(31, 4,
        "Lecture notes. ONE WORD AND/OR A NUMBER.\n\n"
        "Climate Change\n"
        "Cause: [1] emissions\n"
        "Effect: [2] temperatures\n"
        "Solution: [3] energy\n"
        "Target year: [4]\n"
        "Key agreement: [5]\n"
        "Funding: [6] countries",
        ["greenhouse", "rising", "renewable", "2030", "Paris", "developing"]))
    for i in range(4):
        questions.append(_listening_mcq(37 + i, 4,
            f"Part 4 lecture question {i+1}.",
            "A", "B", "C", "c"))
    # Part 1 had 1+5=6, need 10 -> add 4 MCQ
    for i in range(4):
        questions.insert(6 + i, _listening_mcq(7 + i, 1,
            f"Part 1 extra MCQ {i+1}. Select the correct answer.",
            "A", "B", "C", "a"))
    # Part 2 had 1+6=7, need 10 -> add 3 MCQ
    for i in range(3):
        questions.insert(17 + i, _listening_mcq(18 + i, 2,
            f"Part 2 extra question {i+1}. Choose A, B or C.",
            "A", "B", "C", "b"))
    # Re-number orders 1..40
    for i, q in enumerate(questions, start=1):
        q["order"] = i
    return questions


def create_listening_tests(categories):
    """3 ta listening test (har biri 4 part, 40 savol)."""
    cat = categories["listening"]
    titles = [
        ("IELTS Listening Practice Test 1", "easy", "Part 1-4: Accommodation, Museum, Discussion, Lecture."),
        ("IELTS Listening Practice Test 2", "medium", "Part 1-4: Form filling, Map, Assignment, Science."),
        ("IELTS Listening Practice Test 3", "medium", "Part 1-4: Booking, Tour, Project, History."),
    ]
    base_questions = build_listening_questions()
    created = 0
    for title, difficulty, desc in titles:
        test = Test.objects.create(
            title=title,
            category=cat,
            test_type="listening",
            difficulty=difficulty,
            description=desc,
            duration_minutes=30,
            passing_score=60,
            is_active=True,
        )
        for q in base_questions:
            Question.objects.create(
                test=test,
                order=q["order"],
                question_type=q["question_type"],
                question_text=q["question_text"],
                option_a=q.get("option_a", ""),
                option_b=q.get("option_b", ""),
                option_c=q.get("option_c", ""),
                option_d=q.get("option_d", ""),
                correct_answer=q.get("correct_answer", ""),
                correct_answer_json=q.get("correct_answer_json", []),
                options_json=q.get("options_json", {}),
                points=1,
            )
        created += 1
    return created


def create_writing_tests(categories):
    """3 ta writing test (har biri Task 1 + Task 2)."""
    cat = categories["writing"]
    tests_data = [
        (
            "IELTS Writing Practice Test 1",
            "medium",
            "Task 1: Diagram. Task 2: Opinion essay.",
            [
                ("You should spend about 20 minutes on this task. Write at least 150 words.\n\n"
                 "The diagram below shows how bamboo fabric is made. Summarise the information by selecting and reporting the main features.",
                 {"part": 1}),
                ("You should spend about 40 minutes on this task. Write at least 250 words.\n\n"
                 "Some people believe that technology has made life more complicated. Others argue that it has simplified our lives. Discuss both views and give your own opinion.",
                 {"part": 2}),
            ],
        ),
        (
            "IELTS Writing Practice Test 2",
            "medium",
            "Task 1: Graph. Task 2: Discussion.",
            [
                ("You should spend about 20 minutes on this task. Write at least 150 words.\n\n"
                 "The graph below shows the number of tourists visiting a particular Caribbean island between 2010 and 2017. Summarise the information by selecting and reporting the main features.",
                 {"part": 1}),
                ("You should spend about 40 minutes on this task. Write at least 250 words.\n\n"
                 "In some countries, the number of people living alone is increasing. Is this a positive or negative development? Give reasons and examples.",
                 {"part": 2}),
            ],
        ),
        (
            "IELTS Writing Practice Test 3",
            "hard",
            "Task 1: Process. Task 2: Argument.",
            [
                ("You should spend about 20 minutes on this task. Write at least 150 words.\n\n"
                 "The diagram illustrates the process of producing olive oil. Summarise the information by selecting and reporting the main features.",
                 {"part": 1}),
                ("You should spend about 40 minutes on this task. Write at least 250 words.\n\n"
                 "Governments should spend money on measures to save languages with few speakers from dying out. To what extent do you agree or disagree?",
                 {"part": 2}),
            ],
        ),
    ]
    created = 0
    for title, difficulty, description, tasks in tests_data:
        test = Test.objects.create(
            title=title,
            category=cat,
            test_type="writing",
            difficulty=difficulty,
            description=description,
            duration_minutes=60,
            passing_score=60,
            is_active=True,
        )
        for idx, (prompt, opts) in enumerate(tasks, start=1):
            Question.objects.create(
                test=test,
                order=idx,
                question_type="essay",
                question_text=prompt,
                options_json=opts,
                correct_answer_json=[],
                points=1,
            )
        created += 1
    return created


class Command(BaseCommand):
    help = "Bazadagi barcha testlarni o'chirib, yangi formatda (Reading, Listening, Writing) to'ldiradi."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1) Testga bog'liq barcha ma'lumotlarni o'chirish
        UserTestAnswer.objects.all().delete()
        UserTestResult.objects.all().delete()
        Question.objects.all().delete()
        ReadingPassage.objects.all().delete()
        deleted_tests = Test.objects.count()
        Test.objects.all().delete()

        self.stdout.write(self.style.WARNING(
            f"O'chirildi: {deleted_tests} ta test, savollar, passage'lar, natijalar."
        ))

        # 2) Kategoriyalar
        categories = ensure_categories()
        self.stdout.write("Kategoriyalar tekshirildi.")

        # 3) Reading (3 ta: TEST1, TEST2, qisqa)
        n_reading = create_reading_tests(categories)
        self.stdout.write(self.style.SUCCESS(f"Reading: {n_reading} ta test qo'shildi."))

        # 4) Listening (3 ta, har biri 4 part, 40 savol)
        n_listening = create_listening_tests(categories)
        self.stdout.write(self.style.SUCCESS(f"Listening: {n_listening} ta test qo'shildi."))

        # 5) Writing (3 ta, har biri Task 1 + Task 2)
        n_writing = create_writing_tests(categories)
        self.stdout.write(self.style.SUCCESS(f"Writing: {n_writing} ta test qo'shildi."))

        total = n_reading + n_listening + n_writing
        self.stdout.write(self.style.SUCCESS(f"Jami: {total} ta test yangi formatda."))
