from django.test import TestCase

from core.models import Category, ReadingPassage, Test


class GetReadingPassagesTests(TestCase):
    """Test.get_reading_passages() — 1 / 2 / 3 variant va JSON / inline."""

    def setUp(self):
        self.category = Category.objects.create(name="Cat", slug="cat-reading-passages")

    def _reading_test(self, **kwargs):
        data = {
            "title": "R",
            "category": self.category,
            "test_type": "reading",
            "reading_passages_json": [],
            "reading_text": "",
        }
        data.update(kwargs)
        return Test.objects.create(**data)

    def test_one_variant_inline_flat_list(self):
        exam = self._reading_test(variants_to_select=1)
        ReadingPassage.objects.create(
            test=exam, order=2, title="P2", text="b", variant=1
        )
        ReadingPassage.objects.create(
            test=exam, order=1, title="P1", text="a", variant=2
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["title"], "P1")
        self.assertEqual(out[1]["title"], "P2")

    def test_two_variant_inline_buckets(self):
        exam = self._reading_test(variants_to_select=2)
        ReadingPassage.objects.create(test=exam, order=1, title="A1", text="a", variant=1)
        ReadingPassage.objects.create(test=exam, order=2, title="B1", text="b", variant=2)
        ReadingPassage.objects.create(test=exam, order=1, title="A2", text="c", variant=1)
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 2)
        self.assertEqual([r["title"] for r in out[0]], ["A1", "A2"])
        self.assertEqual([r["title"] for r in out[1]], ["B1"])

    def test_three_variant_inline_invalid_variant_falls_back_to_v1(self):
        exam = self._reading_test(variants_to_select=3)
        ReadingPassage.objects.create(test=exam, order=1, title="X", text="x", variant=99)
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 3)
        self.assertEqual(len(out[0]), 1)
        self.assertEqual(out[0][0]["title"], "X")
        self.assertEqual(out[1], [])
        self.assertEqual(out[2], [])

    def test_two_variant_json_half_split(self):
        exam = self._reading_test(
            variants_to_select=2,
            reading_passages_json=[
                {"title": "L1", "text": "a"},
                {"title": "L2", "text": "b"},
                {"title": "R1", "text": "c"},
                {"title": "R2", "text": "d"},
            ],
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 2)
        self.assertEqual([r["title"] for r in out[0]], ["L1", "L2"])
        self.assertEqual([r["title"] for r in out[1]], ["R1", "R2"])

    def test_three_variant_json_all_tagged(self):
        exam = self._reading_test(
            variants_to_select=3,
            reading_passages_json=[
                {"title": "V2a", "text": "", "variant": 2, "order": 2},
                {"title": "V1a", "text": "", "variant": 1, "order": 1},
                {"title": "V3a", "text": "", "variant": 3},
            ],
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 3)
        self.assertEqual([r["title"] for r in out[0]], ["V1a"])
        self.assertEqual([r["title"] for r in out[1]], ["V2a"])
        self.assertEqual([r["title"] for r in out[2]], ["V3a"])

    def test_three_variant_json_no_variant_thirds_order(self):
        exam = self._reading_test(
            variants_to_select=3,
            reading_passages_json=[
                {"title": "a", "text": ""},
                {"title": "b", "text": ""},
                {"title": "c", "text": ""},
                {"title": "d", "text": ""},
                {"title": "e", "text": ""},
                {"title": "f", "text": ""},
            ],
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 3)
        # (6+2)//3=2, (6-2+1)//2=2 → [0:2],[2:4],[4:6]
        self.assertEqual([r["title"] for r in out[0]], ["a", "b"])
        self.assertEqual([r["title"] for r in out[1]], ["c", "d"])
        self.assertEqual([r["title"] for r in out[2]], ["e", "f"])

    def test_three_variant_json_mixed_keeps_assigned_splits_unassigned(self):
        exam = self._reading_test(
            variants_to_select=3,
            reading_passages_json=[
                {"title": "u1", "text": ""},
                {"title": "V1", "text": "", "variant": 1},
                {"title": "u2", "text": ""},
            ],
        )
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 3)
        titles_v1 = [r["title"] for r in out[0]]
        self.assertIn("V1", titles_v1)
        all_titles = titles_v1 + [r["title"] for r in out[1]] + [r["title"] for r in out[2]]
        self.assertCountEqual(all_titles, ["u1", "V1", "u2"])

    def test_inline_takes_precedence_over_json(self):
        exam = self._reading_test(
            variants_to_select=1,
            reading_passages_json=[{"title": "json", "text": "j"}],
        )
        ReadingPassage.objects.create(test=exam, order=1, title="db", text="d", variant=None)
        out = exam.get_reading_passages()
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "db")
