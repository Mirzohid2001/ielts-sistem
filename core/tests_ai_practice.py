from django.test import SimpleTestCase

from core.services import ai_practice as ap


class ReadingTypeGenerationTests(SimpleTestCase):
    def test_local_reading_differs_by_type(self):
        shapes = {}
        for rtype in ap.READING_TYPES:
            payload = ap._local_reading('B1', rtype, 'uz')
            self.assertEqual(payload['practice_type'], rtype)
            qs = payload['questions']
            self.assertEqual(len(qs), ap.READING_QUESTION_COUNT)
            sample = qs[0]
            if rtype == 'tfng':
                texts = {o['text'].upper() for o in sample['options']}
                self.assertIn('TRUE', texts)
                self.assertIn('FALSE', texts)
            elif rtype == 'gap_fill':
                self.assertEqual(sample['options'], [])
                self.assertTrue(sample['correct'])
                self.assertNotIn(sample['correct'].lower(), ('a', 'b', 'c'))
            elif rtype == 'matching_headings':
                letters = {o['letter'] for o in sample['options']}
                self.assertTrue(letters & set(ap._ROMAN_LETTERS))
            else:
                self.assertGreaterEqual(len(sample['options']), 3)
                texts = {o['text'].upper() for o in sample['options']}
                self.assertNotIn('TRUE', texts)
            shapes[rtype] = (
                len(sample.get('options') or []),
                (sample.get('options') or [{}])[0].get('text', '')[:20] if sample.get('options') else sample.get('correct'),
            )
        self.assertNotEqual(shapes['tfng'], shapes['gap_fill'])
        self.assertNotEqual(shapes['mcq'][0], shapes['gap_fill'][0])

    def test_normalize_rejects_tfng_for_mcq(self):
        fake = {
            'title': 'X',
            'passage': 'Some passage about parks and trees and wellbeing in cities. ' * 8,
            'instruction': 'Choose TRUE FALSE NOT GIVEN',
            'questions': [
                {
                    'id': i,
                    'prompt': f'Statement {i}',
                    'options': [
                        {'letter': 'a', 'text': 'TRUE'},
                        {'letter': 'b', 'text': 'FALSE'},
                        {'letter': 'c', 'text': 'NOT GIVEN'},
                    ],
                    'correct': 'a',
                }
                for i in range(1, 11)
            ],
            'provider_name': 'gemini',
            'model_name': 'test',
        }
        out = ap._normalize_reading_payload(fake, level='B1', rtype='mcq', lang='uz')
        self.assertEqual(out['practice_type'], 'mcq')
        self.assertEqual(out['provider_name'], 'local')
        sample_opts = out['questions'][0]['options']
        texts = {o['text'].upper() for o in sample_opts}
        self.assertNotIn('TRUE', texts)

    def test_normalize_keeps_roman_letters(self):
        fake = {
            'title': 'Headings',
            'passage': 'Urban green spaces help cities. ' * 20,
            'instruction': 'Choose the correct heading.',
            'questions': [
                {
                    'id': i,
                    'prompt': f'Section idea {i}',
                    'options': [
                        {'letter': 'i', 'text': 'Green benefits'},
                        {'letter': 'ii', 'text': 'Ocean cables'},
                        {'letter': 'iii', 'text': 'Airport costs'},
                    ],
                    'correct': 'ii',
                }
                for i in range(1, 11)
            ],
            'provider_name': 'gemini',
            'model_name': 'test',
        }
        out = ap._normalize_reading_payload(fake, level='B1', rtype='matching_headings', lang='uz')
        self.assertEqual(out['practice_type'], 'matching_headings')
        letters = [o['letter'] for o in out['questions'][0]['options']]
        self.assertIn('ii', letters)
        self.assertIn('iii', letters)
        self.assertEqual(out['questions'][0]['correct'], 'ii')

    def test_normalize_accepts_gap_fill(self):
        fake = {
            'title': 'Gaps',
            'passage': 'Research links nature access to lower stress in cities. ' * 15,
            'instruction': 'ONE WORD ONLY',
            'questions': [
                {
                    'id': i,
                    'prompt': f'Research links nature access to lower ______ {i}.',
                    'options': [],
                    'correct': 'stress',
                }
                for i in range(1, 11)
            ],
            'provider_name': 'gemini',
            'model_name': 'test',
        }
        out = ap._normalize_reading_payload(fake, level='B1', rtype='gap_fill', lang='uz')
        self.assertEqual(out['provider_name'], 'gemini')
        self.assertEqual(out['questions'][0]['options'], [])
        self.assertEqual(out['questions'][0]['correct'], 'stress')

    def test_passages_are_at_least_500_words(self):
        from core.services.passage_expansions import word_count
        for level in ap.LEVELS:
            for rtype in ap.READING_TYPES:
                for variant in (0, 1):
                    payload = ap._local_reading(level, rtype, 'uz', variant=variant)
                    count = word_count(payload['passage'])
                    self.assertGreaterEqual(
                        count,
                        500,
                        msg=f'{level}/{rtype}/v{variant} {payload["title"]} has {count} words',
                    )
        for focus in ap.WRITING_FOCUSES:
            a = ap._local_writing('A1', focus, 'uz')
            b = ap._local_writing('B1', focus, 'uz')
            c = ap._local_writing('C1', focus, 'uz')
            self.assertEqual(a['practice_type'], focus)
            self.assertNotEqual(a['task'], c['task'])
            self.assertNotEqual(a['exercises'][0]['prompt'], b['exercises'][0]['prompt'])
            self.assertNotEqual(b['exercises'][0]['prompt'], c['exercises'][0]['prompt'])

    def test_high_levels_match_passage_topic(self):
        checks = {
            'B2': ('cable', 'copper', 'atlantic'),
            'C1': ('bilingual', 'executive', 'language'),
            'C2': ('uncertainty', 'ensemble', 'climate'),
        }
        for level, keywords in checks.items():
            for rtype in ap.READING_TYPES:
                payload = ap._local_reading(level, rtype, 'uz')
                blob = (
                    payload['passage']
                    + ' '
                    + ' '.join(q['prompt'] for q in payload['questions'])
                ).lower()
                self.assertTrue(
                    any(k in blob for k in keywords),
                    msg=f'{level}/{rtype} still looks like parks content',
                )
                park_hits = sum(
                    1 for q in payload['questions']
                    if 'park' in q['prompt'].lower() and 'nature access' in q['prompt'].lower()
                )
                self.assertEqual(park_hits, 0, msg=f'{level}/{rtype} has old park prompts')

                answers = {
                    str(q['id']): (q['correct'].split('|')[0] if rtype == 'gap_fill' else q['correct'])
                    for q in payload['questions']
                }
                result = ap.check_practice_answers(payload, answers)
                self.assertEqual(result['correct'], result['total'])
