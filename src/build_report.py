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

from jinja2 import Environment, FileSystemLoader

# Paths (relative to repo root)
TEMPLATE_DIR = os.path.join("src", "templates")
TEMPLATE_FILE = "base.html"
OUTPUT_DIR = "_site"


def build():
    # Validate that the template exists
    template_path = os.path.join(TEMPLATE_DIR, TEMPLATE_FILE)
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    # Load and render template
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(TEMPLATE_FILE)

    html = template.render(
        title="Summary of Economic Projections",
        date=datetime.date.today().isoformat(),
        body="Placeholder report content. Data and charts will be added in a future update.",
        charts=[],
        tables=[],
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
