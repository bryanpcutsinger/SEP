"""
process_data.py — Transform raw SEP data into chart-ready format.

Usage:
    python src/process_data.py

Input:
    data/raw/sep_table1.csv
    data/raw/sep_table1_prev.csv
    data/raw/sep_dotplot.csv
    data/raw/sep_distributions.csv

Output:
    data/processed/sep_summary.csv
    data/processed/sep_summary_prev.csv
    data/processed/sep_dotplot.csv
    data/processed/sep_distributions.csv
"""

import os
import sys

import pandas as pd

RAW_DIR = os.path.join("data", "raw")
PROC_DIR = os.path.join("data", "processed")

# Display order for variables
VARIABLE_ORDER = [
    "Change in real GDP",
    "Unemployment rate",
    "PCE inflation",
    "Core PCE inflation",
    "Federal funds rate",
]

# Friendly display names
DISPLAY_NAMES = {
    "Change in real GDP": "Real GDP Growth",
    "Unemployment rate": "Unemployment Rate",
    "PCE inflation": "PCE Inflation",
    "Core PCE inflation": "Core PCE Inflation",
    "Federal funds rate": "Federal Funds Rate",
}

# Horizon sort order
HORIZON_ORDER = ["2024", "2025", "2026", "2027", "2028", "2029", "Longer Run"]


def _sort_horizons(df):
    """Sort DataFrame rows by horizon in chronological order."""
    order_map = {h: i for i, h in enumerate(HORIZON_ORDER)}
    df = df.copy()
    df["_sort"] = df["horizon"].map(order_map).fillna(99)
    df = df.sort_values("_sort").drop(columns="_sort")
    return df


def _sort_variables(df):
    """Sort DataFrame rows by variable display order."""
    order_map = {v: i for i, v in enumerate(VARIABLE_ORDER)}
    df = df.copy()
    df["_sort"] = df["variable"].map(order_map).fillna(99)
    df = df.sort_values(["_sort", "horizon"]).drop(columns="_sort")
    return df


def process():
    # Check raw data exists
    required = ["sep_table1.csv", "sep_dotplot.csv", "sep_distributions.csv"]
    for f in required:
        path = os.path.join(RAW_DIR, f)
        if not os.path.exists(path):
            print(f"Error: {path} not found. Run fetch_sep_data.py first.",
                  file=sys.stderr)
            sys.exit(1)

    os.makedirs(PROC_DIR, exist_ok=True)

    # Process Table 1 — current SEP
    current = pd.read_csv(os.path.join(RAW_DIR, "sep_table1.csv"))
    current["display_name"] = current["variable"].map(DISPLAY_NAMES)
    current = _sort_variables(current)
    current = current.groupby("variable", sort=False).apply(
        _sort_horizons, include_groups=False
    ).reset_index(drop=True)
    # Re-add variable column if lost
    if "variable" not in current.columns:
        current = pd.read_csv(os.path.join(RAW_DIR, "sep_table1.csv"))
        current["display_name"] = current["variable"].map(DISPLAY_NAMES)
    current.to_csv(os.path.join(PROC_DIR, "sep_summary.csv"), index=False)
    print(f"Saved {len(current)} rows to {PROC_DIR}/sep_summary.csv")

    # Process Table 1 — previous SEP
    prev_path = os.path.join(RAW_DIR, "sep_table1_prev.csv")
    if os.path.exists(prev_path):
        prev_df = pd.read_csv(prev_path)
        if not prev_df.empty:
            prev_df["display_name"] = prev_df["variable"].map(DISPLAY_NAMES)
            prev_df.to_csv(os.path.join(PROC_DIR, "sep_summary_prev.csv"), index=False)
            print(f"Saved {len(prev_df)} rows to {PROC_DIR}/sep_summary_prev.csv")

    # Process dot plot — just copy with sorting
    dotplot = pd.read_csv(os.path.join(RAW_DIR, "sep_dotplot.csv"))
    dotplot = _sort_horizons(dotplot)
    dotplot.to_csv(os.path.join(PROC_DIR, "sep_dotplot.csv"), index=False)
    print(f"Saved {len(dotplot)} rows to {PROC_DIR}/sep_dotplot.csv")

    # Process distributions — just copy with sorting
    dist = pd.read_csv(os.path.join(RAW_DIR, "sep_distributions.csv"))
    dist.to_csv(os.path.join(PROC_DIR, "sep_distributions.csv"), index=False)
    print(f"Saved {len(dist)} rows to {PROC_DIR}/sep_distributions.csv")


if __name__ == "__main__":
    process()
