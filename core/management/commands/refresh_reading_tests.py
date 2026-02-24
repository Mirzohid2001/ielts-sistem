"""
Reading testlarni o'chirib, yangi formatda (3 passage, ReadingPassage model) qayta yaratish.

Ishlatish:
  python manage.py refresh_reading_tests
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Category, Test, Question, ReadingPassage


def build_reading_tests_full():
    """To'liq 3 ta reading test - har birida 3 passage, 40 savol."""
    P1_GEORGIA = """Georgia O'Keeffe (1887-1986)

Georgia O'Keeffe is one of the most significant artists of the twentieth century. Born in Wisconsin, she worked as a teacher across the USA. She created charcoal drawings that attracted Alfred Stieglitz, who became her mentor and husband. She became famous for paintings of New York skyscrapers and close-up flower compositions. In 1929 she visited New Mexico and eventually made it her permanent home, painting its landscape for over forty years. In her later years she painted clouds and sky seen from above."""

    P2_AMAZON = """The Amazon Rainforest

The Amazon is the largest tropical rainforest, covering 5.5 million square kilometres. It contains billions of trees and millions of species. The forest regulates climate by absorbing carbon dioxide and producing oxygen. Deforestation threatens the region through cattle ranching, farming, and timber extraction. Indigenous peoples have extensive knowledge of medicinal plants. Many modern drugs derive from rainforest species."""

    P3_COFFEE = """The History of Coffee

Coffee originated in Ethiopia. By the 15th century it was cultivated in Yemen and traded across Arabia. Venetian merchants brought it to Europe in the 1600s. The first English coffee house opened in Oxford in 1650. Today Brazil is the largest producer, followed by Vietnam and Colombia. The industry employs millions worldwide."""

    def q_fill(part, text, answers, inst="ONE WORD ONLY"):
        return {"question_type": "summary_completion", "question_text": text,
                "options_json": {"part": part, "instruction": inst, "blanks_count": len(answers)},
                "correct_answer_json": answers, "explanation": ""}

    def q_tfng(part, text, ans):
        return {"question_type": "true_false_not_given", "question_text": text,
                "correct_answer": ans,
                "options_json": {"part": part, "options": [
                    {"letter": "true", "text": "True"}, {"letter": "false", "text": "False"},
                    {"letter": "not_given", "text": "Not Given"}]}}

    def q_mcq(part, text, a, b, c, corr, d=""):
        opts = [{"letter": "a", "text": a}, {"letter": "b", "text": b}, {"letter": "c", "text": c}]
        if d:
            opts.append({"letter": "d", "text": d})
        return {"question_type": "mcq", "question_text": text,
                "option_a": a, "option_b": b, "option_c": c, "option_d": d,
                "correct_answer": corr, "options_json": {"part": part, "options": opts}}

    return [
        {
            "title": "IELTS Academic Reading Test 1",
            "difficulty": "medium",
            "description": "3 passage: Georgia O'Keeffe, Amazon Rainforest, Coffee. 13+13+14 savol.",
            "duration_minutes": 60,
            "passing_score": 60,
            "passages": [
                {"order": 1, "title": "Passage 1: Georgia O'Keeffe", "text": P1_GEORGIA},
                {"order": 2, "title": "Passage 2: The Amazon Rainforest", "text": P2_AMAZON},
                {"order": 3, "title": "Passage 3: The History of Coffee", "text": P3_COFFEE},
            ],
            "questions": (
                # Passage 1 (part 1): Q1-13 - gap fill 1-7, T/F/NG 8-10, MCQ 11-13
                [
                    q_fill(1,
                        "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.\n\n"
                        "The Life and Work of Georgia O'Keeffe\n"
                        "- worked as a [1] in various places in the USA\n"
                        "- created drawings using [2] which attracted Stieglitz\n"
                        "- became famous for paintings of New York [3]\n"
                        "- produced close-up paintings of [4]\n"
                        "- moved to New Mexico, inspired by [5] and desert landscapes\n"
                        "- painted the dramatic [6] of New Mexico for over forty years\n"
                        "- in later years painted clouds and [7] seen from above.",
                        ["teacher", "charcoal", "skyscrapers", "flowers", "rocks", "landscape", "sky"]),
                    q_tfng(1, "O'Keeffe was born in New York.", "false"),
                    q_tfng(1, "Stieglitz was a photographer.", "true"),
                    q_tfng(1, "O'Keeffe painted underwater scenes.", "not_given"),
                    q_mcq(1, "What attracted Stieglitz to O'Keeffe's work?", "Her flowers", "Her charcoal drawings", "Her landscapes", "b"),
                    q_mcq(1, "Where did O'Keeffe eventually live permanently?", "New York", "New Mexico", "Wisconsin", "b"),
                    q_mcq(1, "What did she paint in her later years?", "Portraits", "Clouds and sky", "Flowers only", "b"),
                ]
                # Passage 2 (part 2): Q14-26
                + [
                    q_fill(2, "The Amazon covers about [1] million sq km. It absorbs [2] and produces oxygen. Threats include [3] ranching.",
                           ["5.5", "carbon dioxide", "cattle"], "ONE WORD AND/OR A NUMBER"),
                    q_tfng(2, "The Amazon is called the lungs of the Earth.", "true"),
                    q_tfng(2, "Indigenous people have no knowledge of the forest.", "false"),
                    q_mcq(2, "What is the main threat to the Amazon?", "Tourism", "Deforestation", "Flooding", "b"),
                    q_mcq(2, "Where have many modern drugs been derived from?", "Laboratories", "Rainforest species", "Oceans", "b"),
                ]
                # Passage 3 (part 3): Q27-40
                + [
                    q_fill(3, "Coffee originated in [1]. First cultivated in Yemen in the [2] century. First English coffee house in [3] in 1650.",
                           ["Ethiopia", "15th", "Oxford"]),
                    q_tfng(3, "Coffee spread to Europe through Venetian traders.", "true"),
                    q_tfng(3, "Colombia is the largest coffee producer.", "false"),
                    q_mcq(3, "Where did coffee originate?", "Yemen", "Ethiopia", "Brazil", "b"),
                    q_mcq(3, "Which country produces the most coffee today?", "Vietnam", "Brazil", "Colombia", "b"),
                ]
            ),
        },
        {
            "title": "IELTS Academic Reading Test 2 - Climate & Technology",
            "difficulty": "medium",
            "description": "Iqlim o'zgarishi, texnologiya va jamiyat. 3 passage.",
            "duration_minutes": 60,
            "passing_score": 60,
            "passages": [
                {
                    "order": 1,
                    "title": "Passage 1: Climate Change",
                    "text": """Climate Change: A Global Challenge

Climate change refers to long-term shifts in global temperatures. Human activities have been the main driver since the mid-20th century, primarily due to burning fossil fuels. The greenhouse effect warms the Earth's surface. Main greenhouse gases include carbon dioxide, methane, and nitrous oxide. Consequences include melting ice caps, rising sea levels, and extreme weather. The Paris Agreement aims to limit warming to below 2°C. Individual actions like reducing energy use and supporting renewable energy can help.""",
                },
                {
                    "order": 2,
                    "title": "Passage 2: Renewable Energy",
                    "text": """Renewable Energy Sources

Solar, wind, and hydroelectric power are increasingly replacing fossil fuels. Solar panels convert sunlight into electricity. Wind turbines harness wind energy. Hydroelectric dams use flowing water. These sources produce little or no greenhouse gas emissions. Costs have fallen dramatically in recent decades. Many countries now generate over 20% of their electricity from renewables. Battery storage is improving, helping to address intermittency issues.""",
                },
                {
                    "order": 3,
                    "title": "Passage 3: Technology in Education",
                    "text": """Technology in Education

Digital tools have transformed learning. Students use laptops, tablets, and online platforms. Virtual classrooms enable remote education. However, screen time concerns and the digital divide remain challenges. Educators balance technology with traditional methods. Adaptive learning software personalises instruction. Research suggests blended approaches work best.""",
                },
            ],
            "questions": (
                [q_fill(1, "Human activities drive climate change since the mid-[1] century. Main gases: [2], methane, nitrous oxide. Paris Agreement limits warming to below [3]°C.",
                       ["20th", "carbon dioxide", "2"]),
                 q_tfng(1, "Climate change is solely natural.", "false"),
                 q_tfng(1, "The Paris Agreement was adopted in 2015.", "true"),
                 q_mcq(1, "What is the main cause of recent climate change?", "Volcanoes", "Human activities", "Solar activity", "b"),
                 q_mcq(1, "What does the Paris Agreement aim to limit?", "Population", "Global warming", "Trade", "b"),
                ]
                + [q_fill(2, "Renewable sources include solar, [4], and hydroelectric. They produce little [5] gas. Costs have [6] in recent decades.",
                         ["wind", "greenhouse", "fallen"]),
                   q_tfng(2, "Battery storage is improving.", "true"),
                   q_mcq(2, "What do solar panels convert?", "Wind", "Sunlight", "Water", "b"),
                  ]
                + [q_fill(3, "Digital tools have [7] learning. Concerns include [8] time. [9] approaches work best.",
                         ["transformed", "screen", "Blended"]),
                   q_tfng(3, "Technology has only positive effects on education.", "false"),
                   q_mcq(3, "What enables remote education?", "Books", "Virtual classrooms", "Blackboards", "b"),
                  ]
            ),
        },
    ]


class Command(BaseCommand):
    help = "Reading testlarni o'chirib, yangi formatda (ReadingPassage) qayta yaratadi."

    @transaction.atomic
    def handle(self, *args, **options):
        reading_tests = Test.objects.filter(test_type="reading")
        count = reading_tests.count()
        reading_tests.delete()
        self.stdout.write(self.style.WARNING(f"O'chirildi: {count} ta reading test."))

        cat_reading, _ = Category.objects.get_or_create(
            slug="reading",
            defaults={
                "name": "Reading",
                "icon": "fas fa-book",
                "color": "#3b82f6",
                "order": 1,
                "description": "IELTS Reading testlari",
                "is_active": True,
            },
        )

        tests_data = build_reading_tests_full()
        created = 0
        for tdata in tests_data:
            test = Test.objects.create(
                title=tdata["title"],
                category=cat_reading,
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

        self.stdout.write(self.style.SUCCESS(f"Yaratildi: {created} ta yangi reading test (3 passage har birida)."))
