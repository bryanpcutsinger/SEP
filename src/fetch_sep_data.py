"""
fetch_sep_data.py — Download SEP data from the Federal Reserve website.

Scrapes the most recent Summary of Economic Projections (SEP) HTML page from
federalreserve.gov. Extracts Table 1 (median, central tendency, range),
Figure 2 (fed funds dot plot), and Figures 3.A-3.E (participant distributions).

Usage:
    python src/fetch_sep_data.py

    # Use a local fixture instead of fetching from the web:
    python src/fetch_sep_data.py --fixture tests/fixtures/fomcprojtabl20241218.htm

Output:
    data/raw/sep_table1.csv
    data/raw/sep_table1_prev.csv
    data/raw/sep_dotplot.csv
    data/raw/sep_distributions.csv
    data/raw/sep_metadata.json
"""

import argparse
import json
import os
import re
import sys
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.federalreserve.gov"
CALENDAR_URL = f"{BASE_URL}/monetarypolicy/fomccalendars.htm"
RAW_DIR = os.path.join("data", "raw")

# Expected variables in Table 1
EXPECTED_VARIABLES = [
    "Change in real GDP",
    "Unemployment rate",
    "PCE inflation",
    "Core PCE inflation",
    "Federal funds rate",
]

# Plausible value ranges for validation
VALID_RANGES = {
    "Change in real GDP": (-10, 15),
    "Unemployment rate": (0, 25),
    "PCE inflation": (-5, 15),
    "Core PCE inflation": (-5, 15),
    "Federal funds rate": (0, 20),
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _get_session():
    """Create a requests session with polite headers."""
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def find_latest_sep_url(session=None):
    """Scrape the FOMC calendar page to find the most recent SEP URL."""
    s = session or _get_session()
    resp = s.get(CALENDAR_URL, timeout=30)
    resp.raise_for_status()
    time.sleep(1)  # polite delay

    soup = BeautifulSoup(resp.text, "html.parser")
    # Find all links to projection tables
    pattern = re.compile(r"fomcprojtabl(\d{8})\.htm")
    dates_urls = []
    for a in soup.find_all("a", href=pattern):
        match = pattern.search(a["href"])
        if match:
            date_str = match.group(1)
            url = a["href"]
            if not url.startswith("http"):
                url = BASE_URL + url
            dates_urls.append((date_str, url))

    if not dates_urls:
        print("Error: No SEP projection table links found on calendar page.",
              file=sys.stderr)
        sys.exit(1)

    # Sort by date, take most recent
    dates_urls.sort(key=lambda x: x[0], reverse=True)
    latest_date, latest_url = dates_urls[0]

    # Also find the previous SEP for context
    prev_date, prev_url = (None, None)
    if len(dates_urls) > 1:
        prev_date, prev_url = dates_urls[1]

    return latest_date, latest_url, prev_date, prev_url


def fetch_html(url, session=None):
    """Fetch an SEP HTML page."""
    s = session or _get_session()
    resp = s.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"  # Fed pages are UTF-8 but server omits charset header
    time.sleep(1)  # polite delay
    return resp.text


def _parse_range_value(val):
    """Parse 'X.X-X.Y' or 'X.X' into (low, high). Returns (None, None) if empty."""
    val = val.strip()
    if not val:
        return None, None
    # Handle en-dash, em-dash, and hyphen separators
    for sep in ["\u2013", "\u2014", "-"]:
        if sep in val:
            parts = val.split(sep)
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except (ValueError, IndexError):
                return None, None
    # Single value (e.g., "2.0" means both low and high are the same)
    try:
        v = float(val)
        return v, v
    except ValueError:
        return None, None


def parse_table1(soup):
    """Extract Table 1: median, central tendency, and range projections.

    Returns (current_df, prev_df) — DataFrames for current and previous SEP.
    """
    tables = soup.find_all("table")
    # Table 1 is the first table with 'Variable' header and 'Median' in headers
    table = None
    for t in tables:
        header_cells = [th.get_text(strip=True) for th in t.find_all("th")]
        if "Variable" in header_cells and any("Median" in h for h in header_cells):
            table = t
            break

    if table is None:
        print("Error: Could not find Table 1 in SEP HTML.", file=sys.stderr)
        sys.exit(1)

    rows = table.find_all("tr")
    # Row 0: Variable | Median | Central Tendency | Range (column group headers)
    # Row 1: year columns (2024, 2025, ..., Longer run) repeated 3 times
    year_cells = [td.get_text(strip=True) for td in rows[1].find_all(["th", "td"])]
    # There are 5 year columns per measure (median, CT, range) = 15 columns
    n_horizons = len(year_cells) // 3
    horizons = year_cells[:n_horizons]

    current_rows = []
    prev_rows = []

    for row in rows[2:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
        if not cells or len(cells) < 2:
            continue

        # Skip memo rows
        if any("memo" in c.lower() for c in cells):
            continue

        first_cell = cells[0]

        # Determine if this is a "September projection" row (previous SEP)
        is_prev = "projection" in first_cell.lower()

        if is_prev:
            # Previous projection row — use the variable from the row above
            variable = current_rows[-1]["variable"] if current_rows else None
            if variable is None:
                continue
            data_cells = cells[1:] if len(cells) > 1 else []
        else:
            # Clean variable name (remove footnote markers like superscript numbers)
            variable = re.sub(r"\d+$", "", first_cell).strip()
            if variable not in EXPECTED_VARIABLES:
                continue
            data_cells = cells[1:]

        if len(data_cells) < n_horizons * 3:
            # Pad with empty strings if row is short
            data_cells.extend([""] * (n_horizons * 3 - len(data_cells)))

        for i, horizon in enumerate(horizons):
            median_val = data_cells[i] if i < len(data_cells) else ""
            ct_val = data_cells[n_horizons + i] if (n_horizons + i) < len(data_cells) else ""
            range_val = data_cells[2 * n_horizons + i] if (2 * n_horizons + i) < len(data_cells) else ""

            median = None
            try:
                median = float(median_val) if median_val else None
            except ValueError:
                pass

            ct_low, ct_high = _parse_range_value(ct_val)
            range_low, range_high = _parse_range_value(range_val)

            # Normalize horizon label
            h = "Longer Run" if "longer" in horizon.lower() else horizon

            entry = {
                "variable": variable,
                "horizon": h,
                "median": median,
                "ct_low": ct_low,
                "ct_high": ct_high,
                "range_low": range_low,
                "range_high": range_high,
            }

            if is_prev:
                prev_rows.append(entry)
            else:
                current_rows.append(entry)

    current_df = pd.DataFrame(current_rows)
    prev_df = pd.DataFrame(prev_rows)

    # Validate
    _validate_table1(current_df, "current")
    if not prev_df.empty:
        _validate_table1(prev_df, "previous")

    return current_df, prev_df


def _validate_table1(df, label):
    """Validate parsed Table 1 data."""
    variables = df["variable"].unique()
    missing = [v for v in EXPECTED_VARIABLES if v not in variables]
    if missing:
        print(f"Warning: {label} SEP missing variables: {missing}", file=sys.stderr)

    for var, (lo, hi) in VALID_RANGES.items():
        var_data = df[df["variable"] == var]
        for col in ["median", "ct_low", "ct_high", "range_low", "range_high"]:
            vals = var_data[col].dropna()
            out_of_range = vals[(vals < lo) | (vals > hi)]
            if not out_of_range.empty:
                print(f"Warning: {label} {var} has out-of-range values in {col}: "
                      f"{out_of_range.tolist()}", file=sys.stderr)


def parse_dotplot(soup):
    """Extract Figure 2: fed funds rate dot plot data.

    Returns DataFrame with columns: rate, horizon, n_participants.
    """
    tables = soup.find_all("table")
    # Figure 2 table has "Midpoint of target range" in first header cell
    table = None
    for t in tables:
        first_th = t.find("th")
        if first_th and "midpoint" in first_th.get_text(strip=True).lower():
            table = t
            break

    if table is None:
        print("Error: Could not find Figure 2 (dot plot) table.", file=sys.stderr)
        sys.exit(1)

    rows = table.find_all("tr")
    # First row is header with year columns
    header_cells = [td.get_text(strip=True) for td in rows[0].find_all(["th", "td"])]
    horizons = header_cells[1:]  # Skip "Midpoint..." column

    dot_rows = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
        if not cells:
            continue
        try:
            rate = float(cells[0])
        except ValueError:
            continue

        for i, horizon in enumerate(horizons):
            val = cells[i + 1] if (i + 1) < len(cells) else ""
            n = 0
            try:
                n = int(val) if val else 0
            except ValueError:
                pass
            if n > 0:
                h = "Longer Run" if "longer" in horizon.lower() else horizon
                dot_rows.append({
                    "rate": rate,
                    "horizon": h,
                    "n_participants": n,
                })

    df = pd.DataFrame(dot_rows)

    if df.empty:
        print("Warning: No dot plot data extracted.", file=sys.stderr)
    else:
        # Validate: rates should be between 0 and 20
        bad = df[(df["rate"] < 0) | (df["rate"] > 20)]
        if not bad.empty:
            print(f"Warning: Dot plot has implausible rates: {bad['rate'].tolist()}",
                  file=sys.stderr)

    return df


def parse_distributions(soup):
    """Extract Figures 3.A-3.E: participant distribution histograms.

    Returns DataFrame with columns: variable, horizon, bin_low, bin_high,
    n_participants, sep_vintage ('current' or 'previous').
    """
    # Distribution tables follow headings containing "Figure 3."
    # They have "Percent Range" as first header
    DIST_VARIABLES = [
        "Change in real GDP",
        "Unemployment rate",
        "PCE inflation",
        "Core PCE inflation",
        "Federal funds rate",
    ]

    # Find all h4 headings for Figure 3.x
    headings = soup.find_all("h4")
    fig3_headings = [h for h in headings if "Figure 3." in h.get_text()]

    dist_rows = []

    for fig_idx, heading in enumerate(fig3_headings):
        variable = DIST_VARIABLES[fig_idx] if fig_idx < len(DIST_VARIABLES) else f"Unknown_{fig_idx}"

        # Find the next table after this heading
        table = heading.find_next("table")
        if table is None:
            continue

        rows = table.find_all("tr")
        if len(rows) < 3:
            continue

        # Row 0: "Percent Range" + year columns (each year spans 2 sub-columns)
        header_cells = [td.get_text(strip=True) for td in rows[0].find_all(["th", "td"])]
        # Row 1: "September projections" / "December projections" sub-headers
        # The year columns from row 0, excluding "Percent Range"
        year_headers = header_cells[1:]

        # Determine horizons — each year has 2 columns (Sept, Dec)
        # For core PCE, there's no "Longer Run" column
        horizons = []
        for yh in year_headers:
            h = "Longer Run" if "longer" in yh.lower() else yh
            horizons.append(h)

        # Data rows start at row 2
        for row in rows[2:]:
            cells = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
            if not cells or len(cells) < 2:
                continue

            bin_str = cells[0]
            # Parse bin range "X.X - X.Y" or "X.XX - X.YY"
            bin_match = re.match(r"([\d.]+)\s*[-–—]\s*([\d.]+)", bin_str)
            if not bin_match:
                continue
            bin_low = float(bin_match.group(1))
            bin_high = float(bin_match.group(2))

            data_cells = cells[1:]
            # Each horizon has 2 columns: September, December
            for h_idx, horizon in enumerate(horizons):
                sept_idx = h_idx * 2
                dec_idx = h_idx * 2 + 1

                for col_idx, vintage in [(sept_idx, "previous"), (dec_idx, "current")]:
                    if col_idx < len(data_cells):
                        val = data_cells[col_idx]
                        try:
                            n = int(val) if val else 0
                        except ValueError:
                            n = 0
                        if n > 0:
                            dist_rows.append({
                                "variable": variable,
                                "horizon": horizon,
                                "bin_low": bin_low,
                                "bin_high": bin_high,
                                "n_participants": n,
                                "sep_vintage": vintage,
                            })

    df = pd.DataFrame(dist_rows)

    if df.empty:
        print("Warning: No distribution data extracted.", file=sys.stderr)

    return df


def extract_meeting_date(soup):
    """Extract the FOMC meeting date from the page heading."""
    h3 = soup.find("h3")
    if h3:
        text = h3.get_text(strip=True)
        # Look for date pattern like "December 18, 2024"
        match = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", text)
        if match:
            return match.group(1)
    return None


def fetch(fixture_path=None):
    """Main fetch pipeline: discover URL -> download -> parse -> save."""
    session = _get_session()

    if fixture_path:
        # Use local fixture instead of fetching from web
        print(f"Using local fixture: {fixture_path}")
        with open(fixture_path) as f:
            html = f.read()
        # Extract date from fixture filename (e.g., fomcprojtabl20251210.htm)
        date_match = re.search(r"(\d{8})", os.path.basename(fixture_path))
        sep_date = date_match.group(1) if date_match else "20241218"
        prev_date = None
    else:
        print("Finding most recent SEP...")
        sep_date, sep_url, prev_date, _ = find_latest_sep_url(session)
        print(f"Latest SEP: {sep_date} ({sep_url})")
        print("Downloading SEP page...")
        html = fetch_html(sep_url, session)

        # Cache raw HTML
        os.makedirs(RAW_DIR, exist_ok=True)
        cache_path = os.path.join(RAW_DIR, f"fomcprojtabl{sep_date}.htm")
        with open(cache_path, "w") as f:
            f.write(html)
        print(f"Cached HTML to {cache_path}")

    soup = BeautifulSoup(html, "html.parser")

    # Extract meeting date
    meeting_date = extract_meeting_date(soup)
    print(f"Meeting date: {meeting_date}")

    # Parse all data sources
    print("Parsing Table 1 (projections)...")
    current_df, prev_df = parse_table1(soup)
    print(f"  Current: {len(current_df)} rows, Previous: {len(prev_df)} rows")

    print("Parsing Figure 2 (dot plot)...")
    dotplot_df = parse_dotplot(soup)
    print(f"  {len(dotplot_df)} dot plot entries")

    print("Parsing Figures 3.A-3.E (distributions)...")
    dist_df = parse_distributions(soup)
    print(f"  {len(dist_df)} distribution entries")

    # Save outputs
    os.makedirs(RAW_DIR, exist_ok=True)

    current_df.to_csv(os.path.join(RAW_DIR, "sep_table1.csv"), index=False)
    prev_df.to_csv(os.path.join(RAW_DIR, "sep_table1_prev.csv"), index=False)
    dotplot_df.to_csv(os.path.join(RAW_DIR, "sep_dotplot.csv"), index=False)
    dist_df.to_csv(os.path.join(RAW_DIR, "sep_distributions.csv"), index=False)

    # Save metadata
    metadata = {
        "sep_date": sep_date,
        "meeting_date": meeting_date,
        "previous_sep_date": prev_date,
        "n_table1_rows": len(current_df),
        "n_dotplot_entries": len(dotplot_df),
        "n_distribution_entries": len(dist_df),
    }
    with open(os.path.join(RAW_DIR, "sep_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nAll data saved to {RAW_DIR}/")
    print(f"  sep_table1.csv ({len(current_df)} rows)")
    print(f"  sep_table1_prev.csv ({len(prev_df)} rows)")
    print(f"  sep_dotplot.csv ({len(dotplot_df)} rows)")
    print(f"  sep_distributions.csv ({len(dist_df)} rows)")
    print(f"  sep_metadata.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch SEP data from Federal Reserve")
    parser.add_argument("--fixture", help="Path to local HTML fixture file")
    args = parser.parse_args()
    fetch(fixture_path=args.fixture)
