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


def _listening_mcq_choose_two(order, part, text, a, b, c, d, e, correct_letters):
    """
    Listening MCQ (Choose TWO letters, A-E) variant.
    - max_choices=2 => checkbox dual
    - correct_answer_json => 2 ta harf (masalan ['b','e'])
    """
    opts = [
        {"letter": "a", "text": a},
        {"letter": "b", "text": b},
        {"letter": "c", "text": c},
        {"letter": "d", "text": d},
        {"letter": "e", "text": e},
    ]
    correct_letters = [str(x).strip().lower() for x in (correct_letters or []) if str(x).strip()]
    if len(correct_letters) < 2:
        # Seedda xato bo'lmasligi uchun: kamida 2 ta harf bo'lishi kerak
        correct_letters = (correct_letters + ["b", "e"])[:2]

    # UI banner A–E ko'rinishi uchun options A..E bo'lishi muhim.
    return {
        "order": order,
        "question_type": "mcq",
        "question_text": text,
        "max_choices": 2,
        # model option_a..option_d faqat 4 ta maydonni saqlaydi; ammo rendering options_json.dan bo'ladi
        "option_a": a,
        "option_b": b,
        "option_c": c,
        "option_d": d,
        "correct_answer": ",".join(correct_letters[:2]),
        "correct_answer_json": correct_letters[:2],
        "options_json": {"part": part, "options": opts},
    }


def _listening_matching(order, part, text, items, options, correct_map, q_type):
    """Listening uchun matching (matching_info / matching_features)."""
    return {
        "order": order,
        "question_type": q_type,
        "question_text": text,
        "options_json": {"part": part, "items": items, "options": options},
        "correct_answer_json": correct_map,
    }


def build_listening_questions():
    """Bitta listening test uchun 40 savol slot (Part 1: 1-10, Part 2: 11-20, Part 3: 21-30, Part 4: 31-40)."""
    questions = []

    # Slots hisoblash (views.py):
    # - notes_completion => blanks_count = slot soni
    # - mcq (max_choices=2) => 2 ta slot
    # - matching_* => items soni slot soni
    # Maqsad: 4 part bo'yicha 10+10+10+10 = 40 slot.

    # Part 1 (Q1-10): notes completion (10 blanks)
    questions.append(_listening_notes_q(
        1, 1,
        "Complete the notes. Write ONE WORD AND/OR A NUMBER.\n\n"
        "Student Accommodation\n"
        "Type: [1]\n"
        "Rent per week: £ [2]\n"
        "Bills included: [3]\n"
        "Contract length: [4] months\n"
        "Available from: [5]\n"
        "Recommended tour: [6] tour\n"
        "Trip to the fort by: [7]\n"
        "Best day to visit: [8]\n"
        "Exhibition about: [9]\n"
        "Climb Telegraph Hill to see the view of: [10]",
        ["room", "150", "yes", "12", "September", "walking", "boat", "Tuesday", "space", "port"],
        inst="ONE WORD AND/OR A NUMBER",
    ))

    # Part 2 (Q11-20)
    # Q11-12: choose TWO letters (2 slots)
    questions.append(_listening_mcq_choose_two(
        2, 2,
        "Which TWO things does the speaker say about visiting the football stadium with children?",
        "Children get photo taken",
        "There is a competition",
        "Parents must stay",
        "Children need sunhats",
        "Café has special offer",
        correct_letters=["b", "e"],
    ))

    # Q13-14: choose TWO letters (2 slots)
    questions.append(_listening_mcq_choose_two(
        3, 2,
        "Which TWO features of the stadium tour are new this year?",
        "VIP tour",
        "360 cinema experience",
        "Audio guide",
        "Dressing room tour",
        "Tours in other languages",
        correct_letters=["a", "c"],
    ))

    # Q15-20: matching A-H for 6 years (6 slots)
    years_items = [{"num": n, "label": str(n)} for n in range(15, 21)]
    events_options = [
        {"letter": "A", "text": "introduction of pay for the players"},
        {"letter": "B", "text": "change to the design of the goal"},
        {"letter": "C", "text": "first use of lights for matches"},
        {"letter": "D", "text": "introduction of goalkeepers"},
        {"letter": "E", "text": "first international match"},
        {"letter": "F", "text": "two changes to the rules of the game"},
        {"letter": "G", "text": "introduction of a fee for spectators"},
        {"letter": "H", "text": "agreement on the length of a game"},
    ]
    years_correct = {"15": "F", "16": "H", "17": "B", "18": "D", "19": "C", "20": "A"}
    questions.append(_listening_matching(
        4, 2,
        "Which event in the history of football in the UK took place in each of the following years? "
        "Write the correct letter, A–H, next to Questions 15–20.",
        items=years_items,
        options=events_options,
        correct_map=years_correct,
        q_type="matching_info",
    ))

    # Part 3 (Q21-30): matching A-E for 10 statements (10 slots)
    people_items = [{"num": n, "label": f"Statement {n}"} for n in range(21, 31)]
    people_options = [
        {"letter": "A", "text": "Yanira Pineda"},
        {"letter": "B", "text": "Susanna Tol"},
        {"letter": "C", "text": "Elizabeth English"},
        {"letter": "D", "text": "Raisa Chowdhury"},
        {"letter": "E", "text": "Greg Spotts"},
    ]
    people_correct = {str(n): ["A", "B", "C", "D", "E"][(n - 21) % 5] for n in range(21, 31)}
    questions.append(_listening_matching(
        5, 3,
        "Look at the following statements and the list of people below. "
        "Match each statement with the correct person. "
        "Write the correct letter in boxes next to Questions 21–30.",
        items=people_items,
        options=people_options,
        correct_map=people_correct,
        q_type="matching_features",
    ))

    # Part 4 (Q31-40): notes completion (10 blanks)
    questions.append(_listening_notes_q(
        6, 4,
        "Complete the notes below. Write ONE WORD ONLY.\n\n"
        "Research in the Area Around the Chembe Bird Sanctuary\n"
        "They destroy [1] and other rodents.\n"
        "They help prevent farmers from being bitten by [2].\n"
        "Important part of local culture for many years.\n"
        "Now support the economy by encouraging [3].\n"
        "Accidentally killed by [4] when hunting or sleeping.\n"
        "Electrocution from power lines during times of high [5].\n"
        "Farmers may shoot them or [6].\n"
        "Providing a [7] for chickens is expensive.\n"
        "Frightening birds of prey by keeping a [8].\n"
        "Making a [9] (e.g., with metal objects).\n"
        "A [10] of methods is usually most effective.",
        ["jackals", "snakes", "tourism", "roads", "rain", "poison", "building", "dog", "noise", "combination"],
        inst="ONE WORD ONLY",
    ))

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
                max_choices=q.get("max_choices", 1),
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
