"""
process_data.py — Reshape raw SEP data into a table ready for the report.

Usage:
    python src/process_data.py

Input:
    data/raw/sep_median_projections.csv

Output:
    data/processed/sep_current.csv
"""

import os
import sys

import pandas as pd

RAW_PATH = os.path.join("data", "raw", "sep_median_projections.csv")
OUTPUT_PATH = os.path.join("data", "processed", "sep_current.csv")

# Display order for variables
VARIABLE_ORDER = [
    "Real GDP Growth",
    "Unemployment Rate",
    "PCE Inflation",
    "Core PCE Inflation",
    "Federal Funds Rate",
]


def process():
    if not os.path.exists(RAW_PATH):
        print(f"Error: {RAW_PATH} not found. Run fetch_sep_data.py first.",
              file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(RAW_PATH)

    # Pivot: rows = variables, columns = horizons (years + Longer Run)
    table = df.pivot(index="variable", columns="horizon", values="value")

    # Sort columns: numeric years first, then "Longer Run"
    year_cols = sorted([c for c in table.columns if c != "Longer Run"])
    all_cols = year_cols + (["Longer Run"] if "Longer Run" in table.columns else [])
    table = table[all_cols]

    # Sort rows by the defined order
    table.index = pd.CategoricalIndex(table.index, categories=VARIABLE_ORDER, ordered=True)
    table = table.sort_index()
    table.index.name = "Variable"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    table.to_csv(OUTPUT_PATH)
    print(f"Processed table saved to {OUTPUT_PATH}")
    print(table.to_string())


if __name__ == "__main__":
    process()
