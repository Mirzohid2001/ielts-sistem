"""
100+ xil formatdagi testlarni bazaga qo'shish.
Ishlatish: python manage.py seed_100_tests
"""
import random
from django.core.management.base import BaseCommand
from django.db.models import Max
from core.models import Category, Test, Question


# Savol shablonlari - turli formatlar uchun
MCQ_TEMPLATES = [
    ("What is the main idea of the passage?", "a", ["The central theme", "A minor detail", "Background info", "Author opinion"]),
    ("According to the text, when did this happen?", "b", ["In 1990", "In 2005", "In 2010", "In 2020"]),
    ("The author suggests that...", "c", ["Option A is wrong", "Option B is wrong", "Change is necessary", "Nothing matters"]),
    ("Which statement best describes the process?", "a", ["Step by step", "Random order", "Reverse order", "No process"]),
    ("What can be inferred from paragraph 3?", "d", ["Nothing", "Little", "Some", "The conclusion"]),
    ("The purpose of the passage is to...", "b", ["Entertain", "Inform readers", "Advertise", "Complain"]),
    ("Which of the following is NOT mentioned?", "c", ["First thing", "Second thing", "Third option", "Fourth item"]),
    ("How does the writer feel about the topic?", "a", ["Positive", "Negative", "Neutral", "Confused"]),
]

TRUE_FALSE_TEMPLATES = [
    ("The passage states that technology improves education.", "a", "The text clearly supports this."),
    ("All experts agree on this matter.", "b", "The text indicates some disagreement."),
    ("The process takes approximately 30 minutes.", "a", "This is stated in the passage."),
    ("Historical records confirm this event.", "b", "Records are incomplete."),
    ("The study was conducted in 2020.", "a", "The year is explicitly mentioned."),
]

TRUE_FALSE_NOT_GIVEN = [
    ("The author believes that climate change can be reversed.", "a"),  # True
    ("The research was funded by the government.", "b"),  # False
    ("The participants were all under 25 years old.", "c"),  # Not Given
]

YES_NO_NOT_GIVEN = [
    ("Does the passage mention renewable energy?", "a"),  # Yes
    ("Were the results published in 2019?", "b"),  # No
    ("Did the study involve 500 participants?", "c"),  # Not Given
]

FILL_BLANK_TEMPLATES = [
    ("The _____ of the project was successful.", ["outcome"], "Fill the blank with one word from the passage."),
    ("Researchers found that _____ plays a key role.", ["temperature"], "Use ONE WORD ONLY."),
    ("The main _____ was identified in the study.", ["factor"], "Choose from the text."),
]

SUMMARY_TEMPLATES = [
    (["ecological", "balance", "species", "ecosystem"], "Summary about environmental impact. Use ONE WORD ONLY for each blank."),
    (["research", "conducted", "findings", "concluded"], "Complete the summary of the research. ONE WORD per blank."),
    (["process", "begins", "ends", "result"], "Fill in the summary. ONE WORD ONLY from the passage."),
]

SENTENCE_COMPLETION = [
    (["renewable"], "The main source of energy in the future will be _____ .", "ONE WORD ONLY."),
    (["sustainable"], "Cities need _____ development to protect the environment.", "ONE WORD ONLY."),
    (["biodiversity"], "_____ is essential for ecosystem health.", "ONE WORD ONLY."),
]

TABLE_COMPLETION = [
    (["solar", "wind", "hydro"], "Complete the table. Energy types: [1]_____, [2]_____, [3]_____", "ONE WORD per cell."),
    (["2020", "2050", "reduction"], "Year [1]_____, Target [2]_____, Goal [3]_____", "From the passage."),
]

# Matching Headings: items = paragraphs, headings = options, correct = {1:ii, 2:v, ...}
MATCHING_HEADINGS = [
    {
        'items': [{'num': 1, 'label': 'Paragraph A'}, {'num': 2, 'label': 'Paragraph B'}, {'num': 3, 'label': 'Paragraph C'}],
        'headings': [{'letter': 'i', 'text': 'Introduction to the topic'}, {'letter': 'ii', 'text': 'Main findings'}, {'letter': 'iii', 'text': 'Conclusion and recommendations'}],
        'correct': {'1': 'i', '2': 'ii', '3': 'iii'},
    },
    {
        'items': [{'num': 1, 'label': 'Section 1'}, {'num': 2, 'label': 'Section 2'}],
        'headings': [{'letter': 'i', 'text': 'Historical background'}, {'letter': 'ii', 'text': 'Current situation'}],
        'correct': {'1': 'i', '2': 'ii'},
    },
]

# Matching Features: match items to categories A, B, C
MATCHING_FEATURES = [
    {
        'items': [{'num': 1, 'label': 'Solar power is cheap'}, {'num': 2, 'label': 'Wind energy is variable'}, {'num': 3, 'label': 'Hydro needs dams'}],
        'headings': [{'letter': 'A', 'text': 'Advantage'}, {'letter': 'B', 'text': 'Disadvantage'}, {'letter': 'C', 'text': 'Neutral'}],
        'correct': {'1': 'A', '2': 'B', '3': 'B'},
    },
    {
        'items': [{'num': 1, 'label': 'Reading improves vocabulary'}, {'num': 2, 'label': 'Listening helps pronunciation'}],
        'headings': [{'letter': 'A', 'text': 'Reading skill'}, {'letter': 'B', 'text': 'Listening skill'}],
        'correct': {'1': 'A', '2': 'B'},
    },
]

# Classification: A, B, C
CLASSIFICATION = [
    {'items': [{'num': 1, 'label': 'Statement about benefits'}, {'num': 2, 'label': 'Statement about problems'}, {'num': 3, 'label': 'Statement about solutions'}], 'correct': {'1': 'A', '2': 'B', '3': 'C'}, 'headings': [{'letter': 'A', 'text': 'Benefits'}, {'letter': 'B', 'text': 'Problems'}, {'letter': 'C', 'text': 'Solutions'}]},
    {'items': [{'num': 1, 'label': 'Positive effect'}, {'num': 2, 'label': 'Negative effect'}], 'correct': {'1': 'A', '2': 'B'}, 'headings': [{'letter': 'A', 'text': 'Positive'}, {'letter': 'B', 'text': 'Negative'}]},
]

# List Selection: choose 2 from options
LIST_SELECTION = [
    {'options': [{'letter': 'A', 'text': 'First main point'}, {'letter': 'B', 'text': 'Second main point'}, {'letter': 'C', 'text': 'Minor detail'}, {'letter': 'D', 'text': 'Another main point'}], 'correct': ['A', 'B'], 'instruction': 'Choose TWO correct answers.'},
    {'options': [{'letter': 'A', 'text': 'Option one'}, {'letter': 'B', 'text': 'Option two'}, {'letter': 'C', 'text': 'Option three'}], 'correct': ['A', 'C'], 'instruction': 'Choose TWO answers from A, B, C.'},
]

# Matn shablonlari - Reading testlar uchun
READING_TEXTS = [
    """The Development of Renewable Energy

Renewable energy sources have grown significantly over the past decade. Solar power, wind energy, and hydropower now contribute to a substantial portion of global electricity production. Governments worldwide have implemented policies to encourage the adoption of clean energy technologies. The transition from fossil fuels to renewable sources is essential for reducing carbon emissions and combating climate change. Researchers continue to develop more efficient solar panels and wind turbines. The cost of renewable energy has decreased dramatically, making it competitive with traditional energy sources. Many countries have set ambitious targets to achieve carbon neutrality by 2050.""",
    """The Importance of Biodiversity

Biodiversity refers to the variety of life on Earth, including all species of plants, animals, and microorganisms. Ecosystems depend on biodiversity to function properly. When species disappear, the balance of nature is disrupted. Conservation efforts aim to protect endangered species and their habitats. Scientists have identified millions of species, but many more remain undiscovered. Human activities such as deforestation and pollution threaten biodiversity. Protecting natural habitats is crucial for future generations. International agreements have been established to preserve global biodiversity.""",
    """Urbanization and Modern Cities

Urbanization is the process by which rural areas transform into urban centers. More than half of the world's population now lives in cities. Urban areas offer employment opportunities, education, and healthcare. However, rapid urbanization presents challenges including traffic congestion and housing shortages. City planners work to create sustainable urban environments. Green spaces and public transportation improve quality of life in cities. Smart city technologies help manage resources more efficiently. The future of cities depends on balancing growth with sustainability.""",
]

# Test mavzulari va turlari
TEST_CONFIGS = []
difficulties = ['easy', 'medium', 'hard']
categories_data = [
    ('reading', 'reading', 'IELTS Reading'),
    ('listening', 'listening', 'IELTS Listening'),
    ('writing', 'writing', 'IELTS Writing'),
    ('grammar', 'reading', 'Grammar'),
]
topics = [
    'Vocabulary', 'Comprehension', 'Grammar', 'Strategies', 'Practice',
    'Academic', 'General', 'Skills', 'Techniques', 'Methods',
    'Part 1', 'Part 2', 'Part 3', 'Part 4', 'Advanced',
    'Basic', 'Intermediate', 'Expert', 'Foundation', 'Mastery',
]


def generate_tests(count=110, use_mixed_prefix=False):
    """Test konfiguratsiyasini generatsiya qilish"""
    configs = []
    used_titles = set()
    prefix = "Mixed Format - " if use_mixed_prefix else ""
    
    for idx in range(1, count + 1):
        cat_slug, test_type, cat_name = random.choice(categories_data)
        diff = random.choice(difficulties)
        topic = random.choice(topics)
        title = f"{prefix}{cat_name} Test {idx} - {topic}"
        while title in used_titles:
            idx += 1
            topic = random.choice(topics)
            title = f"{prefix}{cat_name} Test {idx} - {topic}"
        used_titles.add(title)
        configs.append({
            'title': title,
            'category_slug': cat_slug,
            'test_type': test_type,
            'difficulty': diff,
            'description': f"{cat_name} bo'yicha {diff} darajadagi test. Barcha savol turlarini o'z ichiga oladi.",
            'duration_minutes': random.choice([15, 20, 25, 30]),
            'passing_score': 60 if diff != 'hard' else 70,
            'reading_text': random.choice(READING_TEXTS) if test_type == 'reading' else '',
            'idx': idx,
        })
    return configs


class Command(BaseCommand):
    help = 'Bazaga 100+ xil formatdagi testlarni qo\'shish'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=50, help='Yaratiladigan testlar soni (default: 50)')

    def handle(self, *args, **options):
        count = min(options['count'], 150)
        self.stdout.write(self.style.SUCCESS(f'Test yaratish boshlandi: {count} ta (barcha savol turlari)...'))
        
        # Kategoriyalar
        cat_defaults = {
            'reading': {'name': 'Reading', 'icon': 'fas fa-book', 'color': '#3b82f6'},
            'listening': {'name': 'Listening', 'icon': 'fas fa-headphones', 'color': '#10b981'},
            'writing': {'name': 'Writing', 'icon': 'fas fa-pen', 'color': '#f59e0b'},
            'grammar': {'name': 'Grammar', 'icon': 'fas fa-language', 'color': '#8b5cf6'},
        }
        categories = {}
        for slug, defaults in cat_defaults.items():
            cat, _ = Category.objects.get_or_create(slug=slug, defaults={**defaults, 'description': f'{defaults["name"]} testlari'})
            categories[slug] = cat
        
        configs = generate_tests(count=count, use_mixed_prefix=True)
        total_tests = 0
        total_questions = 0
        
        question_types = [
            'mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given',
            'fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion', 'short_answer',
            'matching_headings', 'matching_features', 'classification', 'list_selection',
        ]
        
        for cfg in configs:
            cat = categories.get(cfg['category_slug'])
            if not cat:
                continue
                
            test, created = Test.objects.get_or_create(
                title=cfg['title'],
                category=cat,
                defaults={
                    'test_type': cfg['test_type'],
                    'difficulty': cfg['difficulty'],
                    'description': cfg['description'],
                    'duration_minutes': cfg['duration_minutes'],
                    'passing_score': cfg['passing_score'],
                    'reading_text': cfg.get('reading_text', ''),
                    'is_active': True,
                }
            )
            
            if not created:
                continue
                
            total_tests += 1
            q_count = random.randint(5, 10)
            agg = test.questions.aggregate(m=Max('order'))
            start_order = (agg.get('m') or 0) + 1
            
            for i in range(q_count):
                q_type = random.choice(question_types)
                order = start_order + i
                
                if q_type == 'mcq':
                    t = random.choice(MCQ_TEMPLATES)
                    opts = t[2]  # options list
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='mcq',
                        question_text=t[0],
                        option_a=opts[0], option_b=opts[1], option_c=opts[2], option_d=opts[3],
                        correct_answer=t[1],
                        explanation=f"To'g'ri javob: {opts[ord(t[1])-97]}",
                    )
                elif q_type == 'true_false':
                    t = random.choice(TRUE_FALSE_TEMPLATES)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='true_false',
                        question_text=t[0],
                        option_a='True', option_b='False', option_c='', option_d='',
                        correct_answer=t[1],
                        explanation=t[2],
                    )
                elif q_type == 'true_false_not_given':
                    t = random.choice(TRUE_FALSE_NOT_GIVEN)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='true_false_not_given',
                        question_text=t[0],
                        option_a='True', option_b='False', option_c='Not Given', option_d='',
                        correct_answer=t[1],
                        explanation="True/False/Not Given based on the passage.",
                    )
                elif q_type == 'yes_no_not_given':
                    t = random.choice(YES_NO_NOT_GIVEN)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='yes_no_not_given',
                        question_text=t[0],
                        option_a='Yes', option_b='No', option_c='Not Given', option_d='',
                        correct_answer=t[1],
                        explanation="Yes/No/Not Given based on the passage.",
                    )
                elif q_type == 'fill_blank':
                    t = random.choice(FILL_BLANK_TEMPLATES)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='fill_blank',
                        question_text=t[0],
                        correct_answer_json=t[1],
                        options_json={'instruction': t[2]},
                    )
                elif q_type == 'summary_completion':
                    t = random.choice(SUMMARY_TEMPLATES)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='summary_completion',
                        question_text=f"Complete the summary. Blanks: [1] [2] [3] [4]. Use ONE WORD ONLY from the passage for each answer.",
                        correct_answer_json=t[0],
                        options_json={'instruction': t[1], 'blanks_count': len(t[0])},
                    )
                elif q_type == 'notes_completion':
                    words = random.choice([['Monday', 'Tuesday'], ['first', 'second', 'third'], ['research', 'data', 'results']])
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='notes_completion',
                        question_text=f"Complete the notes below. Write ONE WORD ONLY for each answer. [1]_____ [2]_____" + (" [3]_____" if len(words)>2 else ""),
                        correct_answer_json=words,
                        options_json={'instruction': 'Write ONE WORD ONLY for each answer.', 'blanks_count': len(words)},
                    )
                elif q_type == 'sentence_completion':
                    t = random.choice(SENTENCE_COMPLETION)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='sentence_completion',
                        question_text=t[1],
                        correct_answer_json=t[0],
                        options_json={'instruction': t[2]},
                    )
                elif q_type == 'table_completion':
                    t = random.choice(TABLE_COMPLETION)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='table_completion',
                        question_text=t[1],
                        correct_answer_json=t[0],
                        options_json={'instruction': t[2], 'blanks_count': len(t[0])},
                    )
                elif q_type == 'matching_headings':
                    t = random.choice(MATCHING_HEADINGS)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='matching_headings',
                        question_text="Match the following paragraphs to the correct headings. Choose the right heading (i, ii, iii) for each paragraph.",
                        correct_answer_json=t['correct'],
                        options_json={'items': t['items'], 'headings': t['headings'], 'instruction': 'Choose the correct heading for each paragraph.'},
                    )
                elif q_type == 'matching_features':
                    t = random.choice(MATCHING_FEATURES)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='matching_features',
                        question_text="Match each statement to the correct category (A, B, or C).",
                        correct_answer_json=t['correct'],
                        options_json={'items': t['items'], 'headings': t['headings'], 'instruction': 'Match statements to categories.'},
                    )
                elif q_type == 'classification':
                    t = random.choice(CLASSIFICATION)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='classification',
                        question_text="Classify each statement into the correct category.",
                        correct_answer_json=t['correct'],
                        options_json={'items': t['items'], 'headings': t['headings'], 'instruction': 'Choose the correct category for each statement.'},
                    )
                elif q_type == 'list_selection':
                    t = random.choice(LIST_SELECTION)
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='list_selection',
                        question_text="Which of the following are mentioned in the passage? " + t['instruction'],
                        correct_answer_json=t['correct'],
                        options_json={'options': t['options'], 'instruction': t['instruction']},
                    )
                else:  # short_answer
                    ans = random.choice(['technology', 'environment', 'education', 'culture', 'economy'])
                    q = Question.objects.create(
                        test=test,
                        order=order,
                        question_type='short_answer',
                        question_text="What is the main topic discussed in the passage? Write your answer in ONE WORD.",
                        correct_answer_json=[ans],
                        options_json={'instruction': 'ONE WORD ONLY.'},
                    )
                total_questions += 1
            
            if total_tests % 20 == 0:
                self.stdout.write(f'  ... {total_tests} ta test yaratildi')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Tayyor!'))
        self.stdout.write(self.style.SUCCESS(f'   Yaratilgan testlar: {total_tests}'))
        self.stdout.write(self.style.SUCCESS(f'   Jami savollar: {total_questions}'))
