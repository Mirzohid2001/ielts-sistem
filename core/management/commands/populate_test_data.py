"""
Management command to populate database with test data
"""
from django.core.management.base import BaseCommand
from core.models import Category, Test, Question


class Command(BaseCommand):
    help = 'Populate database with test data (categories, tests, questions)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Ma\'lumotlar bazasini to\'ldirish boshlandi...'))
        
        # Kategoriyalar yaratish
        categories_data = [
            {'name': 'Listening', 'slug': 'listening', 'description': 'IELTS Listening testlari', 'icon': 'fas fa-headphones', 'color': '#10b981'},
            {'name': 'Reading', 'slug': 'reading', 'description': 'IELTS Reading testlari', 'icon': 'fas fa-book', 'color': '#3b82f6'},
            {'name': 'Writing', 'slug': 'writing', 'description': 'IELTS Writing testlari', 'icon': 'fas fa-pen', 'color': '#f59e0b'},
            {'name': 'Grammar', 'slug': 'grammar', 'description': 'Grammar testlari', 'icon': 'fas fa-language', 'color': '#8b5cf6'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            categories[cat_data['slug']] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Kategoriya yaratildi: {category.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  Kategoriya mavjud: {category.name}'))
        
        # Listening testlar
        listening_tests = [
            {
                'title': 'IELTS Listening Practice Test 1 - Basic',
                'description': 'IELTS Listening bo\'yicha asosiy darajadagi amaliy test. 5 ta savol.',
                'difficulty': 'easy',
                'duration_minutes': 20,
                'questions': [
                    {
                        'question_text': 'What is the main topic of the conversation?',
                        'option_a': 'University courses',
                        'option_b': 'Travel arrangements',
                        'option_c': 'Job opportunities',
                        'option_d': 'Housing options',
                        'correct_answer': 'a',
                        'audio_timestamp': 5.0,
                        'explanation': 'The conversation is primarily about university courses.'
                    },
                    {
                        'question_text': 'When does the library close on weekends?',
                        'option_a': '5 PM',
                        'option_b': '6 PM',
                        'option_c': '7 PM',
                        'option_d': '8 PM',
                        'correct_answer': 'b',
                        'audio_timestamp': 25.0,
                        'explanation': 'The library closes at 6 PM on weekends.'
                    },
                    {
                        'question_text': 'What is the student\'s ID number?',
                        'option_a': 'ST-1234',
                        'option_b': 'ST-2345',
                        'option_c': 'ST-3456',
                        'option_d': 'ST-4567',
                        'correct_answer': 'c',
                        'audio_timestamp': 45.0,
                        'explanation': 'The student\'s ID number is ST-3456.'
                    },
                    {
                        'question_text': 'Where should the student go to submit the form?',
                        'option_a': 'Room 101',
                        'option_b': 'Room 202',
                        'option_c': 'Room 303',
                        'option_d': 'Room 404',
                        'correct_answer': 'b',
                        'audio_timestamp': 65.0,
                        'explanation': 'The form should be submitted in Room 202.'
                    },
                    {
                        'question_text': 'What is the deadline for submission?',
                        'option_a': 'Next Monday',
                        'option_b': 'Next Tuesday',
                        'option_c': 'Next Wednesday',
                        'option_d': 'Next Thursday',
                        'correct_answer': 'd',
                        'audio_timestamp': 85.0,
                        'explanation': 'The deadline is next Thursday.'
                    },
                ]
            },
            {
                'title': 'IELTS Listening Practice Test 2 - Intermediate',
                'description': 'IELTS Listening bo\'yicha o\'rta darajadagi amaliy test. 7 ta savol.',
                'difficulty': 'medium',
                'duration_minutes': 30,
                'questions': [
                    {
                        'question_text': 'What type of accommodation is being discussed?',
                        'option_a': 'Student dormitory',
                        'option_b': 'Private apartment',
                        'option_c': 'Shared house',
                        'option_d': 'Host family',
                        'correct_answer': 'c',
                        'audio_timestamp': 10.0,
                        'explanation': 'They are discussing a shared house.'
                    },
                    {
                        'question_text': 'How many bedrooms does the accommodation have?',
                        'option_a': 'Two',
                        'option_b': 'Three',
                        'option_c': 'Four',
                        'option_d': 'Five',
                        'correct_answer': 'b',
                        'audio_timestamp': 30.0,
                        'explanation': 'The accommodation has three bedrooms.'
                    },
                    {
                        'question_text': 'What is the monthly rent?',
                        'option_a': '£500',
                        'option_b': '£600',
                        'option_c': '£700',
                        'option_d': '£800',
                        'correct_answer': 'c',
                        'audio_timestamp': 50.0,
                        'explanation': 'The monthly rent is £700.'
                    },
                    {
                        'question_text': 'What utilities are included?',
                        'option_a': 'Water and electricity',
                        'option_b': 'Water and gas',
                        'option_c': 'Electricity and internet',
                        'option_d': 'All utilities',
                        'correct_answer': 'a',
                        'audio_timestamp': 70.0,
                        'explanation': 'Water and electricity are included.'
                    },
                    {
                        'question_text': 'When can the person move in?',
                        'option_a': 'Immediately',
                        'option_b': 'Next week',
                        'option_c': 'Next month',
                        'option_d': 'In two months',
                        'correct_answer': 'b',
                        'audio_timestamp': 90.0,
                        'explanation': 'The person can move in next week.'
                    },
                    {
                        'question_text': 'What is the contact phone number?',
                        'option_a': '07123456789',
                        'option_b': '07123456790',
                        'option_c': '07123456791',
                        'option_d': '07123456792',
                        'correct_answer': 'a',
                        'audio_timestamp': 110.0,
                        'explanation': 'The contact number is 07123456789.'
                    },
                    {
                        'question_text': 'What documents are required?',
                        'option_a': 'ID and references',
                        'option_b': 'ID and bank statement',
                        'option_c': 'References and deposit',
                        'option_d': 'All of the above',
                        'correct_answer': 'd',
                        'audio_timestamp': 130.0,
                        'explanation': 'All documents are required: ID, references, and deposit.'
                    },
                ]
            },
        ]
        
        # Reading testlar
        reading_tests = [
            {
                'title': 'IELTS Reading Practice Test 1 - Academic',
                'description': 'IELTS Reading bo\'yicha akademik darajadagi amaliy test. 6 ta savol.',
                'difficulty': 'medium',
                'duration_minutes': 30,
                'reading_text': '''The History of Coffee

Coffee is one of the most popular beverages in the world today. Its history dates back to the 9th century, when it was first discovered in Ethiopia. According to legend, a goat herder named Kaldi noticed that his goats became very energetic after eating berries from a certain tree. He tried the berries himself and experienced the same effect.

From Ethiopia, coffee spread to Yemen, where it was first cultivated. By the 15th century, coffee had reached the rest of the Middle East, Persia, Turkey, and northern Africa. Coffee houses began to appear in cities across the region, becoming centers of social activity and intellectual discussion.

The first coffee house in Europe opened in Venice in 1645. Coffee quickly became popular throughout Europe, and by the 17th century, coffee houses had become important meeting places for merchants, artists, and intellectuals. In England, coffee houses were called "penny universities" because for the price of a penny, one could purchase a cup of coffee and engage in stimulating conversation.

Coffee was introduced to the Americas in the 18th century. Today, Brazil is the world's largest producer of coffee, followed by Vietnam and Colombia. The global coffee industry employs millions of people and is a major source of income for many developing countries.

Modern coffee culture has evolved significantly. Specialty coffee shops, fair trade practices, and sustainable farming methods have become increasingly important. Coffee continues to be a vital part of daily life for billions of people around the world.''',
                'questions': [
                    {
                        'question_text': 'Where was coffee first discovered?',
                        'option_a': 'Yemen',
                        'option_b': 'Ethiopia',
                        'option_c': 'Turkey',
                        'option_d': 'Venice',
                        'correct_answer': 'b',
                        'explanation': 'Coffee was first discovered in Ethiopia in the 9th century.'
                    },
                    {
                        'question_text': 'What did Kaldi notice about his goats?',
                        'option_a': 'They became sleepy',
                        'option_b': 'They became very energetic',
                        'option_c': 'They stopped eating',
                        'option_d': 'They became sick',
                        'correct_answer': 'b',
                        'explanation': 'Kaldi noticed that his goats became very energetic after eating coffee berries.'
                    },
                    {
                        'question_text': 'Where was coffee first cultivated?',
                        'option_a': 'Ethiopia',
                        'option_b': 'Yemen',
                        'option_c': 'Turkey',
                        'option_d': 'Venice',
                        'correct_answer': 'b',
                        'explanation': 'Coffee was first cultivated in Yemen.'
                    },
                    {
                        'question_text': 'Why were English coffee houses called "penny universities"?',
                        'option_a': 'They were expensive',
                        'option_b': 'They were only for students',
                        'option_c': 'For a penny, one could learn through conversation',
                        'option_d': 'They were located near universities',
                        'correct_answer': 'c',
                        'explanation': 'They were called "penny universities" because for a penny, one could engage in stimulating conversation.'
                    },
                    {
                        'question_text': 'Which country is the largest producer of coffee today?',
                        'option_a': 'Vietnam',
                        'option_b': 'Colombia',
                        'option_c': 'Brazil',
                        'option_d': 'Ethiopia',
                        'correct_answer': 'c',
                        'explanation': 'Brazil is the world\'s largest producer of coffee.'
                    },
                    {
                        'question_text': 'What has become increasingly important in modern coffee culture?',
                        'option_a': 'Cheap prices',
                        'option_b': 'Specialty shops, fair trade, and sustainable farming',
                        'option_c': 'Fast service',
                        'option_d': 'Large quantities',
                        'correct_answer': 'b',
                        'explanation': 'Specialty coffee shops, fair trade practices, and sustainable farming methods have become increasingly important.'
                    },
                ]
            },
            {
                'title': 'IELTS Reading Practice Test 2 - Climate Change',
                'description': 'IELTS Reading bo\'yicha iqlim o\'zgarishi haqidagi test. 8 ta savol.',
                'difficulty': 'hard',
                'duration_minutes': 40,
                'reading_text': '''Climate Change: A Global Challenge

Climate change refers to long-term shifts in global temperatures and weather patterns. While climate variations are natural, scientific evidence shows that human activities have been the main driver of climate change since the mid-20th century, primarily due to the burning of fossil fuels.

The greenhouse effect is a natural process that warms the Earth's surface. When the Sun's energy reaches the Earth's atmosphere, some of it is reflected back to space and the rest is absorbed and re-radiated by greenhouse gases. However, human activities have increased the concentration of greenhouse gases in the atmosphere, enhancing the greenhouse effect and causing global warming.

The main greenhouse gases include carbon dioxide (CO2), methane (CH4), and nitrous oxide (N2O). These gases are released through various human activities such as burning fossil fuels for energy, deforestation, agriculture, and industrial processes.

The consequences of climate change are far-reaching. Rising global temperatures lead to melting ice caps, rising sea levels, and extreme weather events. Ecosystems are being disrupted, and many species face extinction. Human communities, especially those in vulnerable regions, are experiencing increased risks from floods, droughts, and heatwaves.

Addressing climate change requires global cooperation. The Paris Agreement, adopted in 2015, aims to limit global warming to well below 2 degrees Celsius above pre-industrial levels. Countries are working to reduce greenhouse gas emissions through renewable energy, energy efficiency, and sustainable practices.

Individual actions also matter. Reducing energy consumption, using public transportation, supporting renewable energy, and making sustainable lifestyle choices can all contribute to mitigating climate change.''',
                'questions': [
                    {
                        'question_text': 'What has been the main driver of climate change since the mid-20th century?',
                        'option_a': 'Natural variations',
                        'option_b': 'Human activities',
                        'option_c': 'Solar activity',
                        'option_d': 'Volcanic eruptions',
                        'correct_answer': 'b',
                        'explanation': 'Human activities have been the main driver of climate change since the mid-20th century.'
                    },
                    {
                        'question_text': 'What is the greenhouse effect?',
                        'option_a': 'A process that cools the Earth',
                        'option_b': 'A natural process that warms the Earth\'s surface',
                        'option_c': 'A man-made phenomenon',
                        'option_d': 'A type of pollution',
                        'correct_answer': 'b',
                        'explanation': 'The greenhouse effect is a natural process that warms the Earth\'s surface.'
                    },
                    {
                        'question_text': 'Which of the following is NOT mentioned as a main greenhouse gas?',
                        'option_a': 'Carbon dioxide',
                        'option_b': 'Methane',
                        'option_c': 'Nitrous oxide',
                        'option_d': 'Oxygen',
                        'correct_answer': 'd',
                        'explanation': 'Oxygen is not a greenhouse gas. The main greenhouse gases mentioned are CO2, CH4, and N2O.'
                    },
                    {
                        'question_text': 'What is the goal of the Paris Agreement?',
                        'option_a': 'To eliminate all greenhouse gases',
                        'option_b': 'To limit global warming to below 2°C',
                        'option_c': 'To stop all industrial activities',
                        'option_d': 'To increase fossil fuel use',
                        'correct_answer': 'b',
                        'explanation': 'The Paris Agreement aims to limit global warming to well below 2 degrees Celsius.'
                    },
                    {
                        'question_text': 'What are some consequences of climate change mentioned in the text?',
                        'option_a': 'Only economic impacts',
                        'option_b': 'Melting ice caps, rising sea levels, and extreme weather',
                        'option_c': 'Only environmental impacts',
                        'option_d': 'Only social impacts',
                        'correct_answer': 'b',
                        'explanation': 'Consequences include melting ice caps, rising sea levels, and extreme weather events.'
                    },
                    {
                        'question_text': 'How can individuals contribute to mitigating climate change?',
                        'option_a': 'By doing nothing',
                        'option_b': 'By increasing energy consumption',
                        'option_c': 'By reducing energy consumption and using sustainable practices',
                        'option_d': 'By ignoring the problem',
                        'correct_answer': 'c',
                        'explanation': 'Individuals can contribute by reducing energy consumption, using public transport, and making sustainable choices.'
                    },
                    {
                        'question_text': 'What percentage of species face extinction due to climate change?',
                        'option_a': 'The text does not specify a percentage',
                        'option_b': '50%',
                        'option_c': '75%',
                        'option_d': '100%',
                        'correct_answer': 'a',
                        'explanation': 'The text mentions that many species face extinction but does not specify a percentage.'
                    },
                    {
                        'question_text': 'When was the Paris Agreement adopted?',
                        'option_a': '2010',
                        'option_b': '2015',
                        'option_c': '2020',
                        'option_d': '2025',
                        'correct_answer': 'b',
                        'explanation': 'The Paris Agreement was adopted in 2015.'
                    },
                ]
            },
        ]
        
        # Grammar testlar
        grammar_tests = [
            {
                'title': 'Grammar Test 1 - Tenses',
                'description': 'Zamonlar (Tenses) bo\'yicha grammatika testi. 10 ta savol.',
                'difficulty': 'medium',
                'duration_minutes': 25,
                'questions': [
                    {
                        'question_text': 'I _____ to the store yesterday.',
                        'option_a': 'go',
                        'option_b': 'went',
                        'option_c': 'gone',
                        'option_d': 'going',
                        'correct_answer': 'b',
                        'explanation': 'Past simple tense is used for actions completed in the past.'
                    },
                    {
                        'question_text': 'She _____ English for five years.',
                        'option_a': 'studies',
                        'option_b': 'is studying',
                        'option_c': 'has been studying',
                        'option_d': 'study',
                        'correct_answer': 'c',
                        'explanation': 'Present perfect continuous is used for actions that started in the past and continue to the present.'
                    },
                    {
                        'question_text': 'By next year, I _____ my degree.',
                        'option_a': 'will complete',
                        'option_b': 'will have completed',
                        'option_c': 'complete',
                        'option_d': 'completed',
                        'correct_answer': 'b',
                        'explanation': 'Future perfect tense is used for actions that will be completed before a specific time in the future.'
                    },
                    {
                        'question_text': 'They _____ when I arrived.',
                        'option_a': 'are eating',
                        'option_b': 'were eating',
                        'option_c': 'eat',
                        'option_d': 'eaten',
                        'correct_answer': 'b',
                        'explanation': 'Past continuous is used for actions in progress at a specific time in the past.'
                    },
                    {
                        'question_text': 'I _____ my homework before dinner.',
                        'option_a': 'finish',
                        'option_b': 'finished',
                        'option_c': 'will finish',
                        'option_d': 'finishing',
                        'correct_answer': 'b',
                        'explanation': 'Past simple is used for completed actions in the past.'
                    },
                    {
                        'question_text': 'He _____ here since 2010.',
                        'option_a': 'lives',
                        'option_b': 'lived',
                        'option_c': 'has lived',
                        'option_d': 'is living',
                        'correct_answer': 'c',
                        'explanation': 'Present perfect is used for actions that started in the past and continue to the present.'
                    },
                    {
                        'question_text': 'We _____ to London next month.',
                        'option_a': 'travel',
                        'option_b': 'traveled',
                        'option_c': 'will travel',
                        'option_d': 'traveling',
                        'correct_answer': 'c',
                        'explanation': 'Future simple is used for future plans and predictions.'
                    },
                    {
                        'question_text': 'She _____ the piano when I called.',
                        'option_a': 'plays',
                        'option_b': 'was playing',
                        'option_c': 'played',
                        'option_d': 'play',
                        'correct_answer': 'b',
                        'explanation': 'Past continuous is used for actions in progress when another action occurred.'
                    },
                    {
                        'question_text': 'I _____ never _____ to Japan.',
                        'option_a': 'have, been',
                        'option_b': 'has, been',
                        'option_c': 'had, been',
                        'option_d': 'will, be',
                        'correct_answer': 'a',
                        'explanation': 'Present perfect with "never" is used for experiences in life.'
                    },
                    {
                        'question_text': 'By the time you arrive, I _____ dinner.',
                        'option_a': 'will cook',
                        'option_b': 'will have cooked',
                        'option_c': 'cook',
                        'option_d': 'cooked',
                        'correct_answer': 'b',
                        'explanation': 'Future perfect is used for actions that will be completed before another future action.'
                    },
                ]
            },
        ]
        
        # Testlarni yaratish
        all_tests = [
            ('listening', listening_tests),
            ('reading', reading_tests),
            ('grammar', grammar_tests),
        ]
        
        total_tests = 0
        total_questions = 0
        
        for category_slug, tests_data in all_tests:
            category = categories[category_slug]
            
            for test_data in tests_data:
                # Test yaratish
                test_type = 'listening' if category_slug == 'listening' else 'reading' if category_slug == 'reading' else 'reading'
                
                test, created = Test.objects.get_or_create(
                    title=test_data['title'],
                    defaults={
                        'category': category,
                        'test_type': test_type,
                        'difficulty': test_data['difficulty'],
                        'description': test_data['description'],
                        'duration_minutes': test_data['duration_minutes'],
                        'passing_score': 60,
                        'is_active': True,
                        'reading_text': test_data.get('reading_text', ''),
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✓ Test yaratildi: {test.title}'))
                    total_tests += 1
                else:
                    self.stdout.write(self.style.WARNING(f'  Test mavjud: {test.title}'))
                
                # Savollarni yaratish
                for idx, question_data in enumerate(test_data['questions'], 1):
                    question, q_created = Question.objects.get_or_create(
                        test=test,
                        order=idx,
                        defaults={
                            'question_text': question_data['question_text'],
                            'option_a': question_data['option_a'],
                            'option_b': question_data['option_b'],
                            'option_c': question_data['option_c'],
                            'option_d': question_data['option_d'],
                            'correct_answer': question_data['correct_answer'],
                            'explanation': question_data.get('explanation', ''),
                            'audio_timestamp': question_data.get('audio_timestamp'),
                            'points': 1,
                        }
                    )
                    if q_created:
                        total_questions += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Barcha ma\'lumotlar yaratildi!'))
        self.stdout.write(self.style.SUCCESS(f'  Jami testlar: {total_tests}'))
        self.stdout.write(self.style.SUCCESS(f'  Jami savollar: {total_questions}'))
        self.stdout.write(self.style.SUCCESS('\nMa\'lumotlar bazasi to\'ldirildi!'))

