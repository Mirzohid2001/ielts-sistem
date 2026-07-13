from django.test import TestCase

from core.services.writing_error_detection import (
    detect_heuristic_errors,
    extract_diff_errors,
    merge_writing_errors,
    validate_errors_in_essay,
)


class WritingErrorDetectionTests(TestCase):
    def test_extract_diff_errors_word_level(self):
        out = extract_diff_errors(
            'Many peoples dont like informations',
            "Many people don't like information",
        )
        wrongs = {e['wrong'].lower() for e in out}
        self.assertTrue(any('peoples' in w for w in wrongs))
        self.assertTrue(any('dont' in w or "don't" in e['correct'] for e in out for w in [e['wrong'].lower()]))

    def test_validate_rejects_hallucinated_errors(self):
        essay = 'Cities are good for people.'
        cleaned = validate_errors_in_essay(essay, [
            {'wrong': 'peoples', 'correct': 'people', 'type': 'plural'},
            {'wrong': 'people', 'correct': 'citizens', 'type': 'word_choice'},
        ])
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]['wrong'], 'people')

    def test_detect_subject_verb_and_spelling(self):
        essay = 'Many peoples is living in citys and they dont have time.'
        errors = detect_heuristic_errors(essay)
        wrongs = ' '.join(e['wrong'] for e in errors).lower()
        self.assertIn('peoples', wrongs)
        self.assertIn('dont', wrongs)

    def test_merge_combines_sources(self):
        essay = (
            'I think peoples dont like informations. '
            'People is very important for society.'
        )
        merged = merge_writing_errors(
            essay,
            ai_errors=[{'wrong': 'fake error', 'correct': 'x', 'type': 'grammar'}],
            sentence_corrections=[
                {
                    'original': 'I think peoples dont like informations',
                    'corrected': "I believe people don't like information",
                    'type': 'grammar',
                    'why': 'tone',
                },
            ],
            vocabulary_upgrades=[
                {'from': 'think', 'to': 'believe', 'why': 'academic'},
            ],
        )
        self.assertGreaterEqual(len(merged), 3)
        wrongs = ' '.join(e['wrong'] for e in merged).lower()
        self.assertIn('peoples', wrongs)
        self.assertNotIn('fake', wrongs)
