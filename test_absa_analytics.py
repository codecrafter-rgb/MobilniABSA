import json
import tempfile
import unittest
from pathlib import Path

from absa_analytics import (
    Annotation,
    CATEGORIES,
    Review,
    _bipolar_weighted_kappa,
    _cohen,
    _f1,
    _fleiss_noise,
    _gwet_ac1,
    align_annotations,
    calculate_iaa,
    generate_dataset_statistics,
    load_annotations,
    render_markdown,
)


class MetricTests(unittest.TestCase):
    def test_hungarian_alignment_maximizes_iou(self):
        a = [
            Annotation("abcd", 0, 4, "Kamera", "Pozitivan"),
            Annotation("efgh", 5, 9, "Ekran", "Negativan"),
        ]
        b = [
            Annotation("efg", 5, 8, "Ekran", "Negativan"),
            Annotation("abc", 0, 3, "Kamera", "Pozitivan"),
        ]
        alignment = align_annotations(a, b)
        self.assertEqual([(left.category, right.category) for left, right, _ in alignment], [("Kamera", "Kamera"), ("Ekran", "Ekran")])
        self.assertAlmostEqual(sum(iou for _, _, iou in alignment), 1.5)

    def test_null_annotations_are_aligned_by_category(self):
        a = [Annotation(None, None, None, "Baterija", "Pozitivan")]
        b = [Annotation("NULL", None, None, "Baterija", "Negativan")]
        self.assertEqual(len(align_annotations(a, b)), 1)

    def test_null_annotation_order_does_not_affect_alignment(self):
        a = [
            Annotation(None, None, None, "Baterija", "Pozitivan"),
            Annotation(None, None, None, "Kamera", "Negativan"),
        ]
        b = [
            Annotation(None, None, None, "Kamera", "Negativan"),
            Annotation(None, None, None, "Baterija", "Pozitivan"),
        ]
        alignment = align_annotations(a, b)
        self.assertEqual(
            {(left.category, right.category) for left, right, _ in alignment},
            {("Baterija", "Baterija"), ("Kamera", "Kamera")},
        )

    def test_f1_and_gwet_edge_cases(self):
        self.assertEqual(_f1(0, 0, 0), 1.0)
        self.assertEqual(_gwet_ac1([False], [False], [False, True]), 1.0)
        self.assertIsNone(_gwet_ac1([], [], [False, True]))

    def test_cohen_matches_published_reference_example(self):
        first = ["negative", "positive", "negative", "neutral", "positive"]
        second = ["negative", "positive", "negative", "neutral", "negative"]
        self.assertEqual(_cohen(first, second), 0.6875)

    def test_cohen_is_undefined_for_identical_single_class(self):
        self.assertIsNone(_cohen([False, False], [False, False]))

    def test_gwet_uses_full_rating_scale(self):
        first = ["Baterija", "Baterija", "Kamera", "Kamera"]
        second = ["Baterija", "Kamera", "Kamera", "Kamera"]
        self.assertAlmostEqual(_gwet_ac1(first, second, CATEGORIES), 0.7377049180327869)

    def test_fleiss_matches_hand_calculated_binary_example(self):
        keys = [("u1", "t1"), ("u2", "t2"), ("u3", "t3")]
        rating_columns = [
            [False, True, False],
            [False, True, False],
            [False, True, True],
            [False, True, True],
        ]
        datasets = []
        for rater, ratings in enumerate(rating_columns):
            datasets.append({
                key: Review(str(rater), key[0], key[1], rating, ())
                for key, rating in zip(keys, ratings)
            })
        self.assertAlmostEqual(_fleiss_noise(datasets), 5 / 9)

    def test_bipolar_weighted_kappa_uses_component_distance(self):
        self.assertEqual(
            _bipolar_weighted_kappa(
                ["Pozitivan", "Negativan", "Neutralan", "Konflikt"],
                ["Pozitivan", "Negativan", "Neutralan", "Konflikt"],
            ),
            1.0,
        )
        self.assertLess(
            _bipolar_weighted_kappa(
                ["Pozitivan", "Negativan", "Neutralan", "Konflikt"],
                ["Negativan", "Pozitivan", "Konflikt", "Neutralan"],
            ),
            0.0,
        )


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.rows = [
            {
                "review_id": "R1",
                "url": "https://example.test/reviews/1",
                "text": "Baterija je dobra.",
                "is_noise": False,
                "annotations": [
                    {
                        "target": "Baterija",
                        "start_char": 0,
                        "end_char": 8,
                        "category": "Baterija",
                        "sentiment": "Pozitivan",
                    },
                    {
                        "target": "NULL",
                        "start_char": None,
                        "end_char": None,
                        "category": "Opšta ocena",
                        "sentiment": "Negativan",
                    },
                ],
            },
            {"review_id": "R2", "url": "https://example.test/reviews/2", "text": "Prodajem telefon.", "is_noise": True, "annotations": []},
        ]

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, name, rows=None):
        path = self.directory / name
        path.write_text(json.dumps(self.rows if rows is None else rows, ensure_ascii=False), encoding="utf-8")
        return path

    def test_five_annotator_report_is_perfect_and_serializable(self):
        paths = [self._write(f"annotator_{index}.json") for index in range(1, 6)]
        report = calculate_iaa(paths)
        self.assertEqual(report["pair_count"], 10)
        self.assertEqual(report["noise_fleiss_kappa"], 1.0)
        self.assertTrue(all(value == 1.0 for value in report["group_means"].values()))
        json.dumps(report, allow_nan=False)
        markdown = render_markdown(report)
        self.assertIn("A4-A5", markdown)
        self.assertIn("10 Pairs", markdown)

    def test_dataset_statistics(self):
        final_path = self._write("final.json")
        stats = generate_dataset_statistics(final_path)
        self.assertEqual(stats["total_reviews"], 2)
        self.assertEqual(stats["valid_reviews"], 1)
        self.assertEqual(stats["noise_percentage"], 50.0)
        self.assertEqual(stats["total_annotations"], 2)
        self.assertEqual(stats["explicit"]["count"], 1)
        self.assertEqual(stats["implicit"]["count"], 1)
        self.assertEqual(stats["annotation_density"], 2.0)

    def test_legacy_sentiment_aliases_are_normalized(self):
        rows = [{
            "id": 1,
            "url": "https://example.test/legacy/1",
            "comment": "Dobra baterija",
            "review_status": "DA",
            "aspects": [{"text": "baterija", "start": 6, "end": 14, "category": "Baterija", "sentiment": "P"}],
        }]
        path = self._write("legacy.json", rows)
        annotation = next(iter(load_annotations(path).values())).annotations[0]
        self.assertEqual(annotation.sentiment, "Pozitivan")

    def test_conflict_alias_is_normalized_to_dataset_label(self):
        rows = [{
            "review_id": "R1",
            "url": "https://example.test/reviews/conflict",
            "text": "Kamera je dobra, ali noću loša.",
            "is_noise": False,
            "annotations": [{
                "target": "Kamera",
                "start_char": 0,
                "end_char": 6,
                "category": "Kamera",
                "sentiment": "Konfliktan",
            }],
        }]
        path = self._write("conflict_alias.json", rows)
        annotation = next(iter(load_annotations(path).values())).annotations[0]
        self.assertEqual(annotation.sentiment, "Konflikt")

    def test_mismatched_review_sets_are_rejected(self):
        first = self._write("first.json")
        second = self._write("second.json", self.rows[:1])
        with self.assertRaisesRegex(ValueError, "review keys"):
            calculate_iaa([first, second])

    def test_same_url_and_text_align_despite_different_ids(self):
        first_rows = [dict(self.rows[0], review_id="ANNOTATOR_A_17")]
        second_rows = [dict(self.rows[0], review_id="ANNOTATOR_B_903")]
        first = self._write("different_id_a.json", first_rows)
        second = self._write("different_id_b.json", second_rows)
        report = calculate_iaa([first, second])
        self.assertEqual(report["review_count"], 1)
        self.assertEqual(report["pairs"]["A1-A2"]["full_tuple_micro_f1"], 1.0)

    def test_acsa_tuple_f1_ignores_targets_and_consolidates_duplicates(self):
        first_rows = [dict(self.rows[0], annotations=[
            {
                "target": "Baterija",
                "start_char": 0,
                "end_char": 8,
                "category": "Baterija",
                "sentiment": "Pozitivan",
            },
            {
                "target": "NULL",
                "start_char": None,
                "end_char": None,
                "category": "Baterija",
                "sentiment": "Pozitivan",
            },
        ])]
        second_rows = [dict(self.rows[0], annotations=[{
            "target": "traje",
            "start_char": 9,
            "end_char": 14,
            "category": "Baterija",
            "sentiment": "Pozitivan",
        }])]
        first = self._write("acsa_a.json", first_rows)
        second = self._write("acsa_b.json", second_rows)

        metrics = calculate_iaa([first, second])["pairs"]["A1-A2"]

        self.assertEqual(metrics["acsa_tuple_micro_f1"], 1.0)
        self.assertEqual(metrics["full_tuple_micro_f1"], 0.0)

    def test_acsa_tuple_f1_requires_both_category_and_sentiment(self):
        first_rows = [self.rows[0]]
        annotations = [dict(item) for item in self.rows[0]["annotations"]]
        annotations[0]["sentiment"] = "Negativan"
        second_rows = [dict(self.rows[0], annotations=annotations)]
        first = self._write("acsa_sentiment_a.json", first_rows)
        second = self._write("acsa_sentiment_b.json", second_rows)

        score = calculate_iaa([first, second])["pairs"]["A1-A2"]["acsa_tuple_micro_f1"]

        self.assertEqual(score, 0.5)

    def test_same_url_with_different_comments_stays_separate(self):
        shared_url = "https://example.test/phone/model"
        rows = [
            dict(self.rows[0], review_id="1", url=shared_url, text="Prvi komentar."),
            dict(self.rows[1], review_id="2", url=shared_url, text="Drugi komentar."),
        ]
        path = self._write("shared_url.json", rows)
        self.assertEqual(len(load_annotations(path)), 2)

    def test_raw_label_studio_export_is_loaded_without_dropping_noise(self):
        rows = [
            {
                "id": 17,
                "url": "https://example.test/raw/phone",
                "comment": "Baterija je dobra i telefon radi brzo.",
                "review_status": "DA",
                "categories": [{
                    "start": 0,
                    "end": 8,
                    "text": "Baterija",
                    "labels": ["Baterija"],
                }],
                "sentiment": ["Pozitivan"],
                "implicit_aspects": [{"taxonomy": [["Performanse", "Pozitivan"]]}],
            },
            {
                "id": 18,
                "url": "https://example.test/raw/noise",
                "comment": "Prodajem telefon.",
                "review_status": "NE",
            },
        ]
        path = self._write("raw_export.json", rows)
        reviews = list(load_annotations(path).values())
        self.assertEqual(len(reviews), 2)
        self.assertEqual(len(reviews[0].annotations), 2)
        self.assertEqual(reviews[0].annotations[0].span, (0, 8))
        self.assertTrue(reviews[0].annotations[1].implicit)
        self.assertTrue(reviews[1].is_noise)
        self.assertEqual(reviews[1].annotations, ())

    def test_raw_export_rejects_unpaired_categories_and_sentiments(self):
        rows = [{
            "url": "https://example.test/raw/invalid",
            "comment": "Baterija je dobra.",
            "review_status": "DA",
            "categories": [{"start": 0, "end": 8, "text": "Baterija", "labels": ["Baterija"]}],
            "sentiment": [],
        }]
        path = self._write("invalid_raw_export.json", rows)
        with self.assertRaisesRegex(ValueError, "explicit categories"):
            load_annotations(path)

    def test_raw_export_accepts_scalar_sentiment_for_one_category(self):
        rows = [{
            "url": "https://example.test/raw/scalar",
            "comment": "Kamera je loša.",
            "review_status": "DA",
            "categories": [{"start": 0, "end": 6, "text": "Kamera", "labels": ["Kamera"]}],
            "sentiment": "Negativan",
        }]
        path = self._write("scalar_sentiment.json", rows)
        annotation = next(iter(load_annotations(path).values())).annotations[0]
        self.assertEqual(annotation.sentiment, "Negativan")

    def test_invalid_json_error_names_source_file(self):
        path = self.directory / "empty_final.json"
        path.write_text("", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, r"empty_final\.json: invalid JSON"):
            load_annotations(path)

    def test_extra_implicit_category_reduces_category_agreement(self):
        first_rows = [dict(self.rows[0], annotations=[self.rows[0]["annotations"][1]])]
        extra = {
            "target": None,
            "start_char": None,
            "end_char": None,
            "category": "Kamera",
            "sentiment": "Negativan",
        }
        second_rows = [dict(first_rows[0], annotations=first_rows[0]["annotations"] + [extra])]
        first = self._write("implicit_a.json", first_rows)
        second = self._write("implicit_b.json", second_rows)
        result = calculate_iaa([first, second])["pairs"]["A1-A2"]
        self.assertLess(result["category_cohen_kappa"], 1.0)
        self.assertLess(result["category_gwet_ac1"], 1.0)

    def test_single_class_noise_kappas_are_undefined(self):
        first = self._write("single_noise_a.json", self.rows[:1])
        second = self._write("single_noise_b.json", self.rows[:1])
        report = calculate_iaa([first, second])
        self.assertIsNone(report["pairs"]["A1-A2"]["noise_cohen_kappa"])
        self.assertIsNone(report["noise_fleiss_kappa"])

    def test_duplicate_implicit_category_is_excluded_from_sentiment_kappa(self):
        base = dict(self.rows[0], annotations=[
            {
                "target": None,
                "start_char": None,
                "end_char": None,
                "category": "Softver",
                "sentiment": "Pozitivan",
            },
            {
                "target": None,
                "start_char": None,
                "end_char": None,
                "category": "Softver",
                "sentiment": "Negativan",
            },
        ])
        first = self._write("duplicate_implicit_a.json", [base])
        second = self._write("duplicate_implicit_b.json", [base])
        result = calculate_iaa([first, second])["pairs"]["A1-A2"]
        self.assertIsNone(result["sentiment_cohen_kappa"])
        self.assertIsNone(result["sentiment_bipolar_weighted_kappa"])
        self.assertEqual(result["full_tuple_micro_f1"], 1.0)

    def test_unknown_taxonomy_values_are_rejected(self):
        rows = [dict(self.rows[0], annotations=[dict(self.rows[0]["annotations"][0], category="Kamra")])]
        path = self._write("unknown_category.json", rows)
        with self.assertRaisesRegex(ValueError, "unknown category"):
            load_annotations(path)

        rows = [dict(self.rows[0], annotations=[dict(self.rows[0]["annotations"][0], sentiment="Positivan")])]
        path = self._write("unknown_sentiment.json", rows)
        with self.assertRaisesRegex(ValueError, "unknown sentiment"):
            load_annotations(path)


if __name__ == "__main__":
    unittest.main()
