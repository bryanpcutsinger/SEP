"""
fetch_sep_data.py — Download SEP median projections from FRED.

Usage:
    export FRED_API_KEY=your_key
    python src/fetch_sep_data.py

Output:
    data/raw/sep_median_projections.csv

Requires a free FRED API key: https://fred.stlouisfed.org/docs/api/api_key.html
"""

import os
import sys

import pandas as pd
from fredapi import Fred

# FRED series IDs for SEP median projections
# "current" series have one observation per SEP meeting, indexed by forecast year
# "longer_run" series have one observation per meeting (no year dimension)
SERIES = {
    "Real GDP Growth":    {"current": "GDPC1MD",    "longer_run": "GDPC1MDLR"},
    "Unemployment Rate":  {"current": "UNRATEMD",   "longer_run": "UNRATEMDLR"},
    "PCE Inflation":      {"current": "PCECTPIMD",  "longer_run": "PCECTPIMDLR"},
    "Core PCE Inflation": {"current": "JCXFEMD",    "longer_run": None},
    "Federal Funds Rate": {"current": "FEDTARMD",   "longer_run": "FEDTARMDLR"},
}

OUTPUT_PATH = os.path.join("data", "raw", "sep_median_projections.csv")


def fetch():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("Error: Set FRED_API_KEY environment variable.", file=sys.stderr)
        print("Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html",
              file=sys.stderr)
        sys.exit(1)

    fred = Fred(api_key=api_key)
    rows = []

    for variable, ids in SERIES.items():
        # Fetch current-year projections (e.g., 2025, 2026, 2027, 2028)
        print(f"Fetching {variable} ({ids['current']})...")
        series = fred.get_series(ids["current"])
        # Each observation date represents a forecast-target year
        # The most recent SEP's projections share the same "realtime" vintage
        # FRED indexes these by the target year (Jan 1 of that year)
        for date, value in series.items():
            if pd.notna(value):
                rows.append({
                    "variable": variable,
                    "horizon": str(date.year),
                    "value": value,
                    "series_id": ids["current"],
                })

        # Fetch longer-run projection
        if ids["longer_run"]:
            print(f"Fetching {variable} longer run ({ids['longer_run']})...")
            lr_series = fred.get_series(ids["longer_run"])
            for date, value in lr_series.items():
                if pd.notna(value):
                    rows.append({
                        "variable": variable,
                        "horizon": "Longer Run",
                        "value": value,
                        "series_id": ids["longer_run"],
                    })

    df = pd.DataFrame(rows)

    # Keep only the most recent SEP meeting's projections
    # For current projections, FRED stores multiple vintages; we want the latest
    # Group by variable+horizon and take the last observation
    df = df.groupby(["variable", "horizon"], as_index=False).last()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(df)} rows to {OUTPUT_PATH}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    fetch()
