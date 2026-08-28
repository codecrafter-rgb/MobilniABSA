import unittest

from calibration.adjudicate import Explicit, choose_boundary, choose_label, majority_threshold


class AdjudicationRulesTest(unittest.TestCase):
    def test_strict_majority_threshold(self):
        self.assertEqual(majority_threshold(3), 2)
        self.assertEqual(majority_threshold(4), 3)
        self.assertEqual(majority_threshold(5), 3)

    def test_label_majority_has_priority(self):
        value, audit = choose_label(
            [("A1", "Softver"), ("A2", "Softver"), ("A5", "Performanse")],
            ["Softver", "Performanse"],
        )
        self.assertEqual(value, "Softver")
        self.assertFalse(audit["manual_review_required"])

    def test_label_tie_is_flagged_for_manual_review(self):
        value, audit = choose_label(
            [("A1", "Softver"), ("A5", "Performanse")],
            ["Softver", "Performanse"],
        )
        self.assertEqual(value, "Softver")
        self.assertTrue(audit["manual_review_required"])

    def test_boundary_tie_is_flagged_for_manual_review(self):
        group = [
            Explicit("A1", 3, 10, "baterija", "Baterija", "Pozitivan"),
            Explicit("A5", 3, 18, "trajanje baterije", "Baterija", "Pozitivan"),
        ]
        span, audit = choose_boundary(group)
        self.assertEqual(span, (3, 10))
        self.assertTrue(audit["manual_review_required"])


if __name__ == "__main__":
    unittest.main()
