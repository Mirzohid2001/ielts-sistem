"""
Reading testlarni o'chirib, yangi formatda (3 passage, ReadingPassage model) qayta yaratish.

Ishlatish:
  python manage.py refresh_reading_tests
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Category, Test, Question, ReadingPassage


def build_test1():
    """TEST1: 3 passage, 40 savol — skrinshotdagi format (Part 1: 1-13, Part 2: 14-26, Part 3: 27-40)."""
    P1 = """Georgia O'Keeffe (1887-1986)

Georgia O'Keeffe is one of the most significant and intriguing artists of the twentieth century. Her works are immediately recognisable and her style has remained a major influence in the art world. She was known for her innovative approach to painting and her distinctive use of colour and form.

Born in Wisconsin, O'Keeffe studied art at the Art Institute of Chicago and the Art Students League in New York. After completing her studies, she worked as a teacher in various places across the USA, including Texas and South Carolina. During this period, she continued to develop her artistic vision and experimented with different mediums.

She created drawings using charcoal which attracted the attention of Alfred Stieglitz, a famous photographer and gallery owner. These drawings were exhibited in New York in 1916 and marked the beginning of her rise to fame. Stieglitz became her mentor and later her husband.

O'Keeffe moved to New York and became famous for her paintings of the city's skyscrapers, capturing their geometric forms and the interplay of light and shadow. She produced a series of innovative close-up paintings of flowers, magnifying their details to create bold, abstract compositions that challenged traditional representation.

In 1929, she visited New Mexico for the first time and was initially inspired to paint the many rocks and desert landscapes that could be found there. The vast, dramatic scenery captivated her, and she would eventually make the state her permanent home. She continued to paint various features that together formed the dramatic landscape of New Mexico for over forty years.

In 1965 she completed a monumental canvas that remains one of her best-known works. O'Keeffe's paintings of the patio of her house in Abiquiu became among the artist's favourite works. She produced a greater quantity of work during the 1950s to 1970s than at any other time in her life.

In her later years, O'Keeffe travelled widely by plane and painted pictures of clouds and sky seen from above, offering viewers a unique perspective on the natural world. She died in Santa Fe in 1986. Her work continues to inspire artists and art lovers around the globe."""

    P2 = """Adapting to the effects of climate change

A. All around the world, communities are having to adapt to the effects of climate change. Rising sea levels, more frequent extreme weather events, and shifting patterns of rainfall and drought are forcing governments and local authorities to rethink how they build and protect infrastructure.

B. In Miami Beach, Florida, USA, the city is raising roads and installing pumps to cope with regular flooding. Property values have been affected, and insurance costs have risen sharply. Similar adaptation measures are being considered in other coastal cities, from Venice to Jakarta.

C. In agricultural regions, farmers are switching to drought-resistant crops and improving water storage. In parts of Africa and Asia, traditional knowledge is being combined with modern technology to predict and respond to changing seasons. Research into new crop varieties is essential for food security.

D. Some countries are investing heavily in early warning systems for storms, floods, and heatwaves. These systems save lives by giving people time to evacuate or take shelter. International cooperation has improved the sharing of data and best practice.

E. In northern latitudes, thawing permafrost is damaging buildings and roads. Engineers are trialling new foundations and materials that can withstand ground movement. Indigenous communities who depend on frozen land for travel and hunting are having to change long-established ways of life.

F. Adaptation alone cannot solve climate change; reducing greenhouse gas emissions remains critical. However, adaptation can reduce harm and protect the most vulnerable. Funding for adaptation in developing countries is still insufficient, and this is a major focus of international climate negotiations."""

    P3 = """A new role for livestock guard dogs

A. Livestock guard dogs have been used for centuries to protect sheep and other animals from predators such as wolves and coyotes. Traditionally, they are raised with the flock from puppyhood so that they bond with the animals and see them as their family to protect.

B. In recent years, however, researchers and conservationists have begun to use these dogs in a new way: to protect endangered wild species. By placing guard dogs with herds of wild antelope or other prey species, they have reduced attacks by predators and allowed populations to recover.

C. One notable success has been the protection of the Ethiopian wolf, one of the world's rarest carnivores. Farmers had sometimes killed wolves to protect their livestock. Conservation programmes that introduced guard dogs to protect sheep have reduced conflict and given wolves a chance to thrive in their remaining habitat.

D. The dogs are selected for temperament and trained to stay with the herd and deter predators without attacking them. They bark and display aggressive postures, which is usually enough to drive off wolves or coyotes. This non-lethal approach is preferred by conservationists.

E. Funding for such programmes often comes from conservation organisations and sometimes from government grants. Farmers who take part may receive support for the cost of feeding and caring for the dogs. In return, they agree to avoid poisoning or shooting predators.

F. Not every introduction of guard dogs has been successful. In some areas, dogs have failed to bond with wild herds or have been injured by predators. Careful planning and ongoing monitoring are essential.

G. Despite these challenges, the use of livestock guard dogs in conservation is growing. An example of how one predator has been protected by the introduction of livestock guard dogs is the case of the Ethiopian wolf mentioned above. Scientists hope that similar approaches can help other threatened species worldwide."""

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

    def q_match(part, instruction, items_list, letters, correct_dict):
        # items_list: list of statement strings; letters: e.g. ["A","B","C","D","E","F"]; correct_dict: {"1":"A", "2":"B"}
        items = [{"num": i + 1, "label": s} for i, s in enumerate(items_list)]
        options = [{"letter": L, "text": L} for L in letters]
        return {"question_type": "matching_info", "question_text": instruction,
                "options_json": {"part": part, "items": items, "options": options},
                "correct_answer_json": correct_dict, "explanation": ""}

    # Part 1: Q1-13 (O'Keeffe) — 7 gap fill, 3 T/F/NG, 3 MCQ
    part1 = [
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
        q_tfng(1, "O'Keeffe's paintings of the patio of her house in Abiquiu were among the artist's favourite works.", "true"),
        q_tfng(1, "O'Keeffe produced a greater quantity of work during the 1950s to 1970s than at any other time in her life.", "true"),
        q_tfng(1, "O'Keeffe painted underwater scenes.", "not_given"),
        q_mcq(1, "What attracted Stieglitz to O'Keeffe's work?", "Her flowers", "Her charcoal drawings", "Her landscapes", "b"),
        q_mcq(1, "Where did O'Keeffe eventually live permanently?", "New York", "New Mexico", "Wisconsin", "b"),
        q_mcq(1, "What did she paint in her later years?", "Portraits", "Clouds and sky", "Flowers only", "b"),
    ]
    # 1+5+3=9, need 13 → add 4 more
    part1.extend([
        q_mcq(1, "When did O'Keeffe first visit New Mexico?", "1920", "1929", "1935", "b"),
        q_tfng(1, "O'Keeffe died in Santa Fe.", "true"),
        q_mcq(1, "What marked the beginning of her rise to fame?", "Her teaching", "Her charcoal drawings exhibited in New York", "Her marriage", "b"),
        q_tfng(1, "She completed a monumental canvas in 1965.", "true"),
    ])

    # Part 2: Q14-26 (Climate change) — 13 savol: 14-17 Matching, 18-26 boshqa
    part2_match_instruction = (
        "The reading passage has six paragraphs, A–F. Which paragraph contains the following information? "
        "Write the correct letter, A–F, in boxes 14–17 on your answer sheet."
    )
    part2 = [
        q_match(2, part2_match_instruction,
            [
                "A description of flooding problems in a specific city.",
                "The role of farmers and crop research in adaptation.",
                "Examples of international cooperation on early warning systems.",
                "The limits of adaptation and the need for emission reductions.",
            ],
            ["A", "B", "C", "D", "E", "F"],
            {"1": "B", "2": "C", "3": "D", "4": "F"}),
        q_tfng(2, "Miami Beach has raised roads to cope with flooding.", "true"),
        q_tfng(2, "Adaptation alone can solve climate change.", "false"),
        q_tfng(2, "Funding for adaptation in developing countries is sufficient.", "false"),
        q_mcq(2, "What is Miami Beach doing to cope with flooding?", "Building walls only", "Raising roads and installing pumps", "Relocating the city", "b"),
        q_mcq(2, "What is essential for food security according to the passage?", "More factories", "Research into new crop varieties", "Reducing population", "b"),
    ]
    while len(part2) < 13:
        part2.append(q_tfng(2, "Thawing permafrost affects only buildings.", "false"))

    # Part 3: Q27-40 (Livestock guard dogs) — 14 savol: 27-31 Matching, 32-40 boshqa
    part3_match_instruction = (
        "Which paragraph contains the following information? Write the correct letter, A–G, in boxes 27–31 on your answer sheet. "
        "NB You may use any letter more than once."
    )
    part3 = [
        q_match(3, part3_match_instruction,
            [
                "An example of how one predator has been protected by the introduction of livestock guard dogs.",
                "The traditional way in which guard dogs are raised with the flock.",
                "A non-lethal method used by the dogs to deter predators.",
                "The fact that not every introduction of guard dogs has been successful.",
                "A source of funding for guard dog programmes.",
            ],
            ["A", "B", "C", "D", "E", "F", "G"],
            {"1": "G", "2": "A", "3": "D", "4": "F", "5": "E"}),
    ]
    while len(part3) < 14:
        part3.append(q_tfng(3, "Guard dogs are raised with the flock from puppyhood.", "true"))

    return {
        "title": "TEST1",
        "difficulty": "medium",
        "description": "Reading: 3 passage, 40 savol. Part 1 (1-13), Part 2 (14-26), Part 3 (27-40).",
        "duration_minutes": 60,
        "passing_score": 60,
        "passages": [
            {"order": 1, "title": "Passage 1", "text": P1},
            {"order": 2, "title": "Adapting to the effects of climate change", "text": P2},
            {"order": 3, "title": "A new role for livestock guard dogs", "text": P3},
        ],
        "questions": part1 + part2 + part3,
    }


def build_test2_short():
    """Qisqa reading test — 2 passage, 20 savol (gibkiy struktura namoyishi)."""
    P1 = """The History of Coffee

Coffee originated in Ethiopia. By the 15th century it was cultivated in Yemen and traded across Arabia. Venetian merchants brought it to Europe in the 1600s. The first English coffee house opened in Oxford in 1650. Today Brazil is the largest producer."""

    P2 = """The Amazon Rainforest

The Amazon is the largest tropical rainforest, covering 5.5 million square kilometres. It regulates climate by absorbing carbon dioxide and producing oxygen. Deforestation threatens the region. Indigenous peoples have extensive knowledge of medicinal plants."""

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

    def q_mcq(part, text, a, b, c, corr):
        return {"question_type": "mcq", "question_text": text,
                "option_a": a, "option_b": b, "option_c": c, "option_d": "",
                "correct_answer": corr, "options_json": {"part": part, "options": [
                    {"letter": "a", "text": a}, {"letter": "b", "text": b}, {"letter": "c", "text": c}]}}

    part1 = [
        q_fill(1, "Coffee originated in [1]. First cultivated in Yemen in the [2] century. First English coffee house in [3] in 1650.",
               ["Ethiopia", "15th", "Oxford"]),
        q_tfng(1, "Coffee spread to Europe through Venetian traders.", "true"),
        q_tfng(1, "Colombia is the largest coffee producer.", "false"),
        q_mcq(1, "Where did coffee originate?", "Yemen", "Ethiopia", "Brazil", "b"),
    ]
    part2 = [
        q_fill(2, "The Amazon covers about [1] million sq km. It absorbs [2] and produces oxygen.",
               ["5.5", "carbon dioxide"]),
        q_tfng(2, "The Amazon is called the lungs of the Earth.", "true"),
        q_mcq(2, "What is the main threat to the Amazon?", "Tourism", "Deforestation", "Flooding", "b"),
    ]
    # Part 1: 4 savol, Part 2: 3 savol = 7. 20 ga yetkazish
    while len(part1) < 10:
        part1.append(q_tfng(1, "Coffee houses became popular in Europe.", "true"))
    while len(part2) < 10:
        part2.append(q_mcq(2, "Indigenous people have knowledge of medicinal plants.", "True", "False", "Not given", "a"))

    return {
        "title": "Reading Practice (qisqa)",
        "difficulty": "easy",
        "description": "2 passage, 20 savol. Savollar va passage soni ixtiyoriy bo‘lishi mumkin.",
        "duration_minutes": 30,
        "passing_score": 60,
        "passages": [
            {"order": 1, "title": "Passage 1: Coffee", "text": P1},
            {"order": 2, "title": "Passage 2: Amazon", "text": P2},
        ],
        "questions": part1 + part2,
    }


def build_test2_full():
    """TEST2: TEST1 bilan bir xil struktura (3 passage, 40 savol), boshqa sarlavha."""
    data = build_test1()
    data["title"] = "TEST2"
    data["description"] = "Reading: 3 passage, 40 savol. Part 1 (1-13), Part 2 (14-26), Part 3 (27-40)."
    return data


def build_reading_tests_full():
    """Reading testlar ro‘yxati. Gibkiy: har bir testda passage va savol soni ixtiyoriy (40 emas, istalgan)."""
    return [build_test1(), build_test2_full(), build_test2_short()]


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

        self.stdout.write(self.style.SUCCESS(
            f"Yaratildi: {created} ta reading test. Savol va passage soni har test uchun gibkiy (bazadagi ma'lumotga qarab)."
        ))
