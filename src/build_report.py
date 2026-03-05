"""
build_report.py — Render the SEP report as a single-page HTML file.

Usage:
    python src/build_report.py

Output:
    _site/index.html   — the rendered report
    _site/.nojekyll    — prevents GitHub Pages from running Jekyll
"""

import datetime
import os
import sys

import pandas as pd
from jinja2 import Environment, FileSystemLoader

# Paths (relative to repo root)
TEMPLATE_DIR = os.path.join("src", "templates")
TEMPLATE_FILE = "base.html"
OUTPUT_DIR = "_site"
DATA_PATH = os.path.join("data", "processed", "sep_current.csv")


def build():
    # Validate that the template exists
    template_path = os.path.join(TEMPLATE_DIR, TEMPLATE_FILE)
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    # Load processed data if available
    tables = []
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH, index_col="Variable")
        table_html = df.to_html(
            classes="sep-table",
            float_format=lambda x: f"{x:.1f}",
            na_rep="—",
        )
        tables.append(table_html)
        body = (
            "The table below shows the median projections from the most recent "
            "FOMC Summary of Economic Projections (SEP). Values represent the "
            "median forecast across all participants for each variable and horizon."
        )
    else:
        body = "No data available. Run fetch_sep_data.py and process_data.py first."

    # Load and render template
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(TEMPLATE_FILE)

    html = template.render(
        title="Summary of Economic Projections",
        date=datetime.date.today().isoformat(),
        body=body,
        charts=[],
        tables=tables,
    )

    # Write output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
        f.write(html)

    # Prevent Jekyll processing on GitHub Pages
    with open(os.path.join(OUTPUT_DIR, ".nojekyll"), "w") as f:
        pass

    print(f"Report built: {os.path.join(OUTPUT_DIR, 'index.html')}")


if __name__ == "__main__":
    build()
