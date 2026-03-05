"""
test_parsers.py — Unit tests for SEP HTML parsers.

Runs against the Dec 2025 fixture to verify parsing correctness.
"""

import os
import sys
import unittest

from bs4 import BeautifulSoup

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fetch_sep_data import parse_table1, parse_dotplot, parse_distributions

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "fomcprojtabl20251210.htm"
)


def _load_fixture():
    with open(FIXTURE_PATH) as f:
        return BeautifulSoup(f, "html.parser")


class TestParseTable1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soup = _load_fixture()
        cls.current, cls.prev = parse_table1(soup)

    def test_current_has_5_variables(self):
        variables = self.current["variable"].unique()
        self.assertEqual(len(variables), 5)

    def test_current_has_expected_variables(self):
        expected = {
            "Change in real GDP", "Unemployment rate", "PCE inflation",
            "Core PCE inflation", "Federal funds rate",
        }
        self.assertEqual(set(self.current["variable"].unique()), expected)

    def test_current_row_count(self):
        # 5 variables x 5 horizons = 25 rows
        self.assertEqual(len(self.current), 25)

    def test_prev_row_count(self):
        self.assertEqual(len(self.prev), 25)

    def test_gdp_median_2026(self):
        row = self.current[
            (self.current["variable"] == "Change in real GDP") &
            (self.current["horizon"] == "2026")
        ]
        self.assertAlmostEqual(row["median"].iloc[0], 2.3)

    def test_ffr_median_2026(self):
        row = self.current[
            (self.current["variable"] == "Federal funds rate") &
            (self.current["horizon"] == "2026")
        ]
        self.assertAlmostEqual(row["median"].iloc[0], 3.4)

    def test_central_tendency_parsed(self):
        row = self.current[
            (self.current["variable"] == "Federal funds rate") &
            (self.current["horizon"] == "2026")
        ]
        self.assertAlmostEqual(row["ct_low"].iloc[0], 2.9)
        self.assertAlmostEqual(row["ct_high"].iloc[0], 3.6)

    def test_range_parsed(self):
        row = self.current[
            (self.current["variable"] == "Federal funds rate") &
            (self.current["horizon"] == "2026")
        ]
        self.assertAlmostEqual(row["range_low"].iloc[0], 2.1)
        self.assertAlmostEqual(row["range_high"].iloc[0], 3.9)

    def test_core_pce_longer_run_is_nan(self):
        row = self.current[
            (self.current["variable"] == "Core PCE inflation") &
            (self.current["horizon"] == "Longer Run")
        ]
        self.assertTrue(row["median"].isna().iloc[0])

    def test_prev_gdp_median_2026(self):
        row = self.prev[
            (self.prev["variable"] == "Change in real GDP") &
            (self.prev["horizon"] == "2026")
        ]
        self.assertAlmostEqual(row["median"].iloc[0], 1.8)

    def test_values_in_plausible_range(self):
        for _, row in self.current.iterrows():
            if row["variable"] == "Core PCE inflation" and row["horizon"] == "Longer Run":
                continue  # NaN is expected
            self.assertTrue(
                -10 <= row["median"] <= 20,
                f"Implausible median {row['median']} for {row['variable']} {row['horizon']}"
            )


class TestParseDotplot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soup = _load_fixture()
        cls.df = parse_dotplot(soup)

    def test_has_data(self):
        self.assertGreater(len(self.df), 0)

    def test_total_dots_reasonable(self):
        # 19 participants x 5 horizons = 95 dots
        total = self.df["n_participants"].sum()
        self.assertGreaterEqual(total, 80)
        self.assertLessEqual(total, 120)

    def test_rates_in_range(self):
        self.assertTrue((self.df["rate"] >= 0).all())
        self.assertTrue((self.df["rate"] <= 10).all())

    def test_has_multiple_horizons(self):
        self.assertGreaterEqual(self.df["horizon"].nunique(), 3)

    def test_2025_dominant_rate(self):
        # In Dec 2025, 12 participants projected 3.625%
        data_2025 = self.df[self.df["horizon"] == "2025"]
        top = data_2025.sort_values("n_participants", ascending=False).iloc[0]
        self.assertEqual(top["n_participants"], 12)
        self.assertAlmostEqual(top["rate"], 3.625)


class TestParseDistributions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        soup = _load_fixture()
        cls.df = parse_distributions(soup)

    def test_has_data(self):
        self.assertGreater(len(self.df), 0)

    def test_has_5_variables(self):
        self.assertEqual(self.df["variable"].nunique(), 5)

    def test_has_current_and_previous(self):
        vintages = self.df["sep_vintage"].unique()
        self.assertIn("current", vintages)
        self.assertIn("previous", vintages)

    def test_bins_are_numeric(self):
        self.assertTrue((self.df["bin_low"] >= 0).all())
        self.assertTrue((self.df["bin_high"] > self.df["bin_low"]).all())


if __name__ == "__main__":
    unittest.main()
