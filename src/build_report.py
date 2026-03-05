"""
build_report.py — Render the SEP report as a single-page HTML file.

Orchestrates the full pipeline: process data, generate charts and takeaways,
render the Jinja2 template, and write _site/index.html.

Usage:
    python src/build_report.py

Output:
    _site/index.html
    _site/.nojekyll
"""

import datetime
import json
import os
import sys

import pandas as pd
from jinja2 import Environment, FileSystemLoader

# Add src to path so we can import sibling modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from generate_takeaways import generate_takeaways
from make_charts import make_all_charts

# Paths (relative to repo root)
TEMPLATE_DIR = os.path.join("src", "templates")
TEMPLATE_FILE = "base.html"
OUTPUT_DIR = "_site"
PROC_DIR = os.path.join("data", "processed")
RAW_DIR = os.path.join("data", "raw")

DISPLAY_NAMES = {
    "Change in real GDP": "Real GDP Growth",
    "Unemployment rate": "Unemployment Rate",
    "PCE inflation": "PCE Inflation",
    "Core PCE inflation": "Core PCE Inflation",
    "Federal funds rate": "Federal Funds Rate",
}

VARIABLE_ORDER = [
    "Change in real GDP",
    "Unemployment rate",
    "PCE inflation",
    "Core PCE inflation",
    "Federal funds rate",
]


def _build_summary_table(current_df, prev_df=None):
    """Build an HTML summary table with median, CT, and range columns."""
    horizons = []
    for h in ["2024", "2025", "2026", "2027", "2028", "2029", "Longer Run"]:
        if h in current_df["horizon"].values:
            horizons.append(h)

    has_prev = prev_df is not None and not prev_df.empty

    # Build header
    h_labels = [h if h != "Longer Run" else "Longer Run" for h in horizons]
    header = "<thead><tr><th>Variable</th>"
    for h in h_labels:
        header += f"<th>{h}</th>"
    header += "</tr></thead>"

    # Build rows grouped by variable
    body = "<tbody>"
    for var in VARIABLE_ORDER:
        var_data = current_df[current_df["variable"] == var]
        if var_data.empty:
            continue

        display = DISPLAY_NAMES.get(var, var)

        # Median row
        body += f'<tr class="var-header"><td>{display}</td>'
        for h in horizons:
            row = var_data[var_data["horizon"] == h]
            if row.empty or pd.isna(row["median"].iloc[0]):
                body += "<td>&mdash;</td>"
            else:
                val = row["median"].iloc[0]
                cell = f"{val:.1f}"
                # Add change arrow if previous data exists
                if has_prev:
                    prev_row = prev_df[
                        (prev_df["variable"] == var) & (prev_df["horizon"] == h)
                    ]
                    if not prev_row.empty and pd.notna(prev_row["median"].iloc[0]):
                        prev_val = prev_row["median"].iloc[0]
                        diff = val - prev_val
                        if abs(diff) >= 0.05:
                            arrow = "&uarr;" if diff > 0 else "&darr;"
                            color = "#cc3333" if diff > 0 else "#228B22"
                            cell += f' <span style="color:{color};font-size:0.8em">{arrow}</span>'
                body += f"<td>{cell}</td>"
        body += "</tr>"

        # Central tendency row
        body += f"<tr><td style='padding-left:1.5em;color:#666;font-size:0.85em'>Central tendency</td>"
        for h in horizons:
            row = var_data[var_data["horizon"] == h]
            if row.empty or pd.isna(row["ct_low"].iloc[0]):
                body += "<td>&mdash;</td>"
            else:
                lo, hi = row["ct_low"].iloc[0], row["ct_high"].iloc[0]
                if abs(lo - hi) < 0.01:
                    body += f"<td style='color:#666;font-size:0.85em'>{lo:.1f}</td>"
                else:
                    body += f"<td style='color:#666;font-size:0.85em'>{lo:.1f}&ndash;{hi:.1f}</td>"
        body += "</tr>"

        # Range row
        body += f"<tr><td style='padding-left:1.5em;color:#999;font-size:0.85em'>Range</td>"
        for h in horizons:
            row = var_data[var_data["horizon"] == h]
            if row.empty or pd.isna(row["range_low"].iloc[0]):
                body += "<td>&mdash;</td>"
            else:
                lo, hi = row["range_low"].iloc[0], row["range_high"].iloc[0]
                if abs(lo - hi) < 0.01:
                    body += f"<td style='color:#999;font-size:0.85em'>{lo:.1f}</td>"
                else:
                    body += f"<td style='color:#999;font-size:0.85em'>{lo:.1f}&ndash;{hi:.1f}</td>"
        body += "</tr>"

    body += "</tbody>"
    return f"<table>{header}{body}</table>"


def build():
    # Check template exists
    template_path = os.path.join(TEMPLATE_DIR, TEMPLATE_FILE)
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    # Load processed data
    summary_path = os.path.join(PROC_DIR, "sep_summary.csv")
    if not os.path.exists(summary_path):
        print(f"Error: {summary_path} not found. Run fetch and process first.",
              file=sys.stderr)
        sys.exit(1)

    current_df = pd.read_csv(summary_path)

    # Load previous SEP if available
    prev_path = os.path.join(PROC_DIR, "sep_summary_prev.csv")
    prev_df = None
    if os.path.exists(prev_path):
        prev_df = pd.read_csv(prev_path)
        if prev_df.empty:
            prev_df = None

    # Load dot plot data
    dotplot_path = os.path.join(PROC_DIR, "sep_dotplot.csv")
    dotplot_df = None
    if os.path.exists(dotplot_path):
        dotplot_df = pd.read_csv(dotplot_path)

    # Load metadata
    metadata_path = os.path.join(RAW_DIR, "sep_metadata.json")
    metadata = {}
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)

    meeting_date = metadata.get("meeting_date", "Unknown date")

    # Generate charts
    print("Generating charts...")
    charts = make_all_charts(current_df, prev_df, dotplot_df)
    print(f"  Generated {len(charts)} charts")

    # Map charts to template variables by caption
    chart_map = {}
    for c in charts:
        cap = c["caption"]
        if "Dot Plot" in cap:
            chart_map["dotplot"] = c
        elif "GDP" in cap:
            chart_map["gdp"] = c
        elif "Unemployment" in cap:
            chart_map["unemp"] = c
        elif "Core PCE" in cap:
            chart_map["core_pce"] = c
        elif "PCE" in cap:
            chart_map["pce"] = c
        elif "Federal Funds" in cap:
            chart_map["ffr"] = c

    # Generate takeaways
    print("Generating takeaways...")
    takeaways = generate_takeaways(current_df, prev_df, meeting_date)
    print(f"  Generated {len(takeaways)} takeaways")
    for t in takeaways:
        print(f"    - {t[:80]}...")

    # Build summary table
    summary_table = _build_summary_table(current_df, prev_df)

    # Render template
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(TEMPLATE_FILE)

    html = template.render(
        title="Summary of Economic Projections",
        subtitle="A visual guide to the Federal Reserve's latest economic forecasts",
        meeting_label=f"FOMC Meeting: {meeting_date}",
        generated_date=datetime.date.today().strftime("%B %d, %Y"),
        takeaways=takeaways,
        fomc_context=None,  # TODO: FOMC context feature (future enhancement)
        dotplot_chart=chart_map.get("dotplot"),
        gdp_chart=chart_map.get("gdp"),
        unemp_chart=chart_map.get("unemp"),
        pce_chart=chart_map.get("pce"),
        core_pce_chart=chart_map.get("core_pce"),
        ffr_chart=chart_map.get("ffr"),
        has_prev=prev_df is not None,
        summary_table=summary_table,
    )

    # Write output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(output_path, "w") as f:
        f.write(html)

    # Prevent Jekyll processing on GitHub Pages
    with open(os.path.join(OUTPUT_DIR, ".nojekyll"), "w") as f:
        pass

    print(f"\nReport built: {output_path}")


if __name__ == "__main__":
    build()
