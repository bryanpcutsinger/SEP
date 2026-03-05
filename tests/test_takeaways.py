"""
test_takeaways.py — Unit tests for takeaway generation.
"""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from generate_takeaways import generate_takeaways

PROC_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


class TestGenerateTakeaways(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = pd.read_csv(os.path.join(PROC_DIR, "sep_summary.csv"))
        prev_path = os.path.join(PROC_DIR, "sep_summary_prev.csv")
        cls.prev = pd.read_csv(prev_path) if os.path.exists(prev_path) else None

    def test_returns_list(self):
        result = generate_takeaways(self.current, self.prev)
        self.assertIsInstance(result, list)

    def test_returns_4_to_5_bullets(self):
        result = generate_takeaways(self.current, self.prev)
        self.assertGreaterEqual(len(result), 3)
        self.assertLessEqual(len(result), 5)

    def test_all_strings(self):
        result = generate_takeaways(self.current, self.prev)
        for bullet in result:
            self.assertIsInstance(bullet, str)
            self.assertGreater(len(bullet), 20)

    def test_includes_fed_funds(self):
        result = generate_takeaways(self.current, self.prev)
        combined = " ".join(result).lower()
        self.assertTrue(
            "rate" in combined or "federal funds" in combined,
            "Takeaways should mention the federal funds rate"
        )

    def test_includes_inflation(self):
        result = generate_takeaways(self.current, self.prev)
        combined = " ".join(result).lower()
        self.assertTrue(
            "inflation" in combined or "pce" in combined,
            "Takeaways should mention inflation"
        )

    def test_works_without_prev(self):
        result = generate_takeaways(self.current, None)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_bullets_end_with_period(self):
        result = generate_takeaways(self.current, self.prev)
        for bullet in result:
            self.assertTrue(
                bullet.endswith("."),
                f"Takeaway should end with period: '{bullet[-30:]}'"
            )


if __name__ == "__main__":
    unittest.main()
