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


def _single_choice(part, qtype, text, a, b, c, correct, d=""):
    options = [{"letter": "a", "text": a}, {"letter": "b", "text": b}, {"letter": "c", "text": c}]
    if d:
        options.append({"letter": "d", "text": d})
    return {
        "question_type": qtype,
        "question_text": text,
        "option_a": a,
        "option_b": b,
        "option_c": c,
        "option_d": d,
        "correct_answer": correct,
        "options_json": {"part": part, "options": options},
    }


def _fill(part, qtype, text, answers, instruction):
    return {
        "question_type": qtype,
        "question_text": text,
        "options_json": {"part": part, "instruction": instruction, "blanks_count": len(answers)},
        "correct_answer_json": answers,
    }


def _matching(part, text, items, options, correct):
    return {
        "question_type": "matching_headings",
        "question_text": text,
        "options_json": {"part": part, "instruction": "Match each item", "items": items, "headings": options},
        "correct_answer_json": correct,
    }


def _list_selection(part, text, options, correct):
    return {
        "question_type": "list_selection",
        "question_text": text,
        "options_json": {"part": part, "instruction": "Choose TWO answers", "options": options},
        "correct_answer_json": correct,
    }


def build_tests_payload():
    """Faqat skrinshot tarzidagi testlar (Cambridge IELTS 20 / Engnovate format)."""
    GEORGIA_PASSAGE = """Georgia O'Keeffe (1887-1986)

Georgia O'Keeffe is one of the most significant and intriguing artists of the twentieth century. Her works are immediately recognisable and her style has remained a major influence in the art world. She was known for her innovative approach to painting and her distinctive use of colour and form.

Born in Wisconsin, O'Keeffe studied art at the Art Institute of Chicago and the Art Students League in New York. After completing her studies, she worked as a teacher in various places across the USA, including Texas and South Carolina. During this period, she continued to develop her artistic vision and experimented with different mediums.

She created drawings using charcoal which attracted the attention of Alfred Stieglitz, a famous photographer and gallery owner. These drawings were exhibited in New York in 1916 and marked the beginning of her rise to fame. Stieglitz became her mentor and later her husband.

O'Keeffe moved to New York and became famous for her paintings of the city's skyscrapers, capturing their geometric forms and the interplay of light and shadow. She produced a series of innovative close-up paintings of flowers, magnifying their details to create bold, abstract compositions that challenged traditional representation.

In 1929, she visited New Mexico for the first time and was initially inspired to paint the many rocks and desert landscapes that could be found there. The vast, dramatic scenery captivated her, and she would eventually make the state her permanent home. She continued to paint various features that together formed the dramatic landscape of New Mexico for over forty years.

In her later years, O'Keeffe travelled widely by plane and painted pictures of clouds and sky seen from above, offering viewers a unique perspective on the natural world. Her work continues to inspire artists and art lovers around the globe."""

    reading_test_4 = [
        _fill(1, "summary_completion", (
            "Complete the notes below.\n"
            "Choose ONE WORD ONLY from the passage for each answer.\n"
            "Write your answers in boxes on your answer sheet.\n\n"
            "The Life and Work of Georgia O'Keefe\n"
            "- studied art, then worked as a [1] in various places in the USA\n"
            "- created drawings using [2] which were exhibited in New York\n"
            "City\n"
            "- moved to New York and became famous for her paintings of the city's [3]\n"
            "- produced a series of innovative close-up paintings of [4]\n"
            "- went to New Mexico and was initially inspired to paint the many [5] that could be found there\n"
            "- continued to paint various features that together formed the dramatic [6] of New Mexico for over forty years\n"
            "- travelled widely by plane in later years, and painted pictures of clouds and [7] seen from above."
        ), ["teacher", "charcoal", "skyscrapers", "flowers", "rocks", "landscape", "sky"], "ONE WORD ONLY"),
    ]

    listening_test_4 = [
        _fill(1, "notes_completion", (
            "Complete the notes below.\n"
            "Write ONE WORD AND/OR A NUMBER for each answer.\n\n"
            "Advice on Family Visit\n"
            "Accommodation: [1] Hotel on George Street\n"
            "Cost of family room per night: £ [2] (approx.)\n\n"
            "Recommended Trips\n"
            "A [3] tour of the city centre (starts in Carlton Square)\n"
            "A trip by [4] to the old fort\n\n"
            "Science Museum\n"
            "Best day to visit: [5]\n"
            "See the exhibition about [6] which opens soon\n\n"
            "Food (Clacton Market)\n"
            "- Good for [7] food\n"
            "- Need to have lunch before [8] p.m.\n\n"
            "Theatre Tickets\n"
            "Save up to [9] % on ticket prices at bargaintickets.com\n\n"
            "Free Activities (Blakewell Gardens)\n"
            "- Roots Music Festival\n"
            "- Climb Telegraph Hill to see a view of the [10]"
        ), ["central", "85", "walking", "boat", "Saturday", "space", "local", "8", "20", "coast"], "ONE WORD AND/OR A NUMBER"),
    ]

    def _essay(part, prompt):
        return {
            "question_type": "essay",
            "question_text": prompt,
            "options_json": {"part": part, "instruction": "Write your answer below."},
            "correct_answer_json": [],
        }

    writing_test_4 = [
        _essay(1, (
            "You should spend about 20 minutes on this task. Write at least 150 words.\n\n"
            "The diagram below shows how fabric is manufactured from bamboo. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.\n\n"
            "How bamboo fabric is made:\n"
            "1. Plant bamboo plants (Spring) → 2. Harvest (Autumn) → 3. Cut into strips → "
            "4. Crush strips (to make liquid pulp) → 5. Filter (separate long fibres) → 6. Soften fibres (add water and amine oxide)"
        )),
        _essay(2, (
            "You should spend about 40 minutes on this task. Write at least 250 words.\n\n"
            "Some people believe that technology has made life more complicated. Others argue that it has simplified our lives. Discuss both views and give your own opinion."
        )),
    ]

    # ========== READING TEST 2 ==========
    RAINFOREST_PASSAGE = """The Amazon Rainforest

The Amazon rainforest is the largest tropical rainforest in the world, covering approximately 5.5 million square kilometres across South America. It is home to an estimated 390 billion individual trees and millions of species of plants, insects, birds, and other animals.

The rainforest plays a crucial role in regulating the Earth's climate. Trees absorb carbon dioxide and produce oxygen, earning the Amazon the nickname 'the lungs of the Earth'. Deforestation, however, poses a serious threat. Large areas are cleared for cattle ranching, soybean farming, and timber extraction.

Indigenous peoples have lived in the Amazon for thousands of years, developing a deep understanding of the forest's medicinal plants. Many modern drugs have been derived from compounds first discovered in rainforest species. Conservation efforts are essential to protect both the biodiversity and the cultural heritage of the region."""

    reading_test_2 = [
        _fill(1, "summary_completion", (
            "Complete the summary below. Choose NO MORE THAN TWO WORDS from the passage for each answer.\n"
            "Write your answers in boxes 1-5 on your answer sheet.\n\n"
            "The Amazon rainforest is the world's largest [1] rainforest. It contains billions of trees and millions of [2]. "
            "The forest helps regulate climate by absorbing [3] and producing oxygen. "
            "Major threats include deforestation for [4] and farming. "
            "Indigenous communities have extensive knowledge of [5] plants found in the forest."
        ), ["tropical", "species", "carbon dioxide", "cattle ranching", "medicinal"], "NO MORE THAN TWO WORDS"),
    ]

    # ========== READING TEST 3 ==========
    COFFEE_PASSAGE = """The History of Coffee

Coffee originated in Ethiopia, where legend says a goat herder noticed his animals became more energetic after eating berries from a certain tree. By the 15th century, coffee was being cultivated in Yemen and traded across the Arabian Peninsula. The drink spread to Europe through Venetian merchants in the 1600s.

Coffee houses became popular meeting places for intellectuals and businessmen. The first coffee house in England opened in Oxford in 1650. Today, coffee is one of the most traded commodities globally. Brazil is the largest producer, followed by Vietnam and Colombia. The industry employs millions of people worldwide."""

    reading_test_3 = [
        _fill(1, "notes_completion", (
            "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.\n\n"
            "The History of Coffee\n"
            "- Originated in [1]\n"
            "- First cultivated in Yemen in the [2] century\n"
            "- Spread to Europe via [3] traders\n"
            "- First English coffee house opened in [4] in 1650\n"
            "- [5] is now the world's largest coffee producer"
        ), ["Ethiopia", "15th", "Venetian", "Oxford", "Brazil"], "ONE WORD ONLY"),
    ]

    # ========== LISTENING TEST 2 ==========
    listening_test_2 = [
        _fill(1, "notes_completion", (
            "Complete the notes below. Write ONE WORD AND/OR A NUMBER for each answer.\n\n"
            "Student Accommodation Enquiry\n"
            "Type of room: [1] room\n"
            "Rent per week: £ [2]\n"
            "Bills included: [3]\n"
            "Contract length: [4] months\n"
            "Available from: [5] September\n\n"
            "Facilities\n"
            "- Shared [6]\n"
            "- [7] in each room\n"
            "- [8] laundry on site"
        ), ["single", "120", "yes", "12", "15th", "kitchen", "wifi", "free"], "ONE WORD AND/OR A NUMBER"),
    ]

    # ========== LISTENING TEST 3 ==========
    listening_test_3 = [
        _fill(1, "notes_completion", (
            "Complete the notes below. Write NO MORE THAN TWO WORDS for each answer.\n\n"
            "Library Tour\n"
            "Opening hours: [1] to 8pm weekdays\n"
            "Weekend hours: 10am to [2]\n"
            "Maximum books: [3] at a time\n"
            "Renewal: online or by [4]\n"
            "Study rooms: book [5] in advance"
        ), ["9am", "4pm", "10", "phone", "24 hours"], "NO MORE THAN TWO WORDS"),
    ]

    # ========== WRITING TEST 2 ==========
    writing_test_2 = [
        _essay(1, (
            "You should spend about 20 minutes on this task. Write at least 150 words.\n\n"
            "The chart below shows the percentage of households in owned and rented accommodation in England and Wales between 1918 and 2011. Summarise the information by selecting and reporting the main features, and make comparisons where relevant."
        )),
        _essay(2, (
            "You should spend about 40 minutes on this task. Write at least 250 words.\n\n"
            "In some countries, young people are encouraged to work or travel for a year between finishing high school and starting university studies. Discuss the advantages and disadvantages for young people who decide to do this."
        )),
    ]

    # ========== WRITING TEST 3 ==========
    writing_test_3 = [
        _essay(1, (
            "You should spend about 20 minutes on this task. Write at least 150 words.\n\n"
            "The diagram below shows the water cycle, which is the continuous movement of water on, above and below the surface of the Earth. Summarise the information by selecting and reporting the main features."
        )),
        _essay(2, (
            "You should spend about 40 minutes on this task. Write at least 250 words.\n\n"
            "Some people think that the best way to reduce crime is to give longer prison sentences. Others, however, believe there are better alternative ways of reducing crime. Discuss both views and give your opinion."
        )),
    ]

    payload = [
        {
            "title": "Cambridge IELTS 20 Academic Reading Test 4",
            "test_type": "reading",
            "difficulty": "medium",
            "category_slug": "reading",
            "description": "Cambridge IELTS 20 - Georgia O'Keeffe, Questions 1-7 note completion.",
            "duration_minutes": 60,
            "passing_score": 60,
            "reading_text": GEORGIA_PASSAGE,
            "questions": reading_test_4,
        },
        {
            "title": "Cambridge IELTS 20 Academic Listening Test 4",
            "test_type": "listening",
            "difficulty": "medium",
            "category_slug": "listening",
            "description": "Part 1: Advice on Family Visit, Questions 1-10 notes completion.",
            "duration_minutes": 40,
            "passing_score": 60,
            "questions": listening_test_4,
        },
        {
            "title": "Cambridge IELTS 20 Academic Writing Test 4",
            "test_type": "writing",
            "difficulty": "medium",
            "category_slug": "writing",
            "description": "Part 1: Bamboo fabric diagram. Part 2: Technology essay.",
            "duration_minutes": 60,
            "passing_score": 60,
            "questions": writing_test_4,
        },
        # ===== 4 ta qo'shimcha test =====
        {
            "title": "IELTS Academic Reading - The Amazon Rainforest",
            "test_type": "reading",
            "difficulty": "medium",
            "category_slug": "reading",
            "description": "Summary completion - NO MORE THAN TWO WORDS.",
            "duration_minutes": 60,
            "passing_score": 60,
            "reading_text": RAINFOREST_PASSAGE,
            "questions": reading_test_2,
        },
        {
            "title": "IELTS Academic Reading - The History of Coffee",
            "test_type": "reading",
            "difficulty": "easy",
            "category_slug": "reading",
            "description": "Notes completion - ONE WORD ONLY.",
            "duration_minutes": 60,
            "passing_score": 60,
            "reading_text": COFFEE_PASSAGE,
            "questions": reading_test_3,
        },
        {
            "title": "IELTS Academic Listening - Student Accommodation",
            "test_type": "listening",
            "difficulty": "easy",
            "category_slug": "listening",
            "description": "Part 1: Student accommodation enquiry, notes completion.",
            "duration_minutes": 40,
            "passing_score": 60,
            "questions": listening_test_2,
        },
        {
            "title": "IELTS Academic Writing - Housing & Gap Year",
            "test_type": "writing",
            "difficulty": "medium",
            "category_slug": "writing",
            "description": "Part 1: Housing chart. Part 2: Gap year advantages/disadvantages.",
            "duration_minutes": 60,
            "passing_score": 60,
            "questions": writing_test_2,
        },
    ]
    return payload


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

        for test_data in build_tests_payload():
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
            "grammar": {"name": "Grammar", "icon": "fas fa-language", "color": "#8b5cf6", "order": 4},
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
