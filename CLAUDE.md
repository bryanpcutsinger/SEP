# SEP Project — CLAUDE.md

## Project Overview

Goal: Summarize the most recent FOMC Summary of Economic Projections (SEP) and publish the report as a GitHub Pages site. The GitHub repo serves as the source of truth for data, code, and the live report.

## Project Structure

```
SEP/
├── CLAUDE.md
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── .github/
│   └── workflows/
│       └── deploy.yml        # GitHub Actions: build and deploy to Pages
├── data/
│   ├── raw/                  # Original SEP data as downloaded
│   └── processed/            # Cleaned/transformed data ready for analysis
├── src/
│   ├── build_report.py       # Renders HTML report from template + data
│   └── templates/
│       └── base.html         # Jinja2 HTML template
├── output/                   # Intermediate output artifacts (charts, tables)
└── _site/                    # Built site (generated, gitignored)
```

## Data Sources

<!-- TODO: Identify and document SEP data sources -->
<!-- Likely candidates: Federal Reserve website, FRED API, official FOMC projection materials -->

## Report Specifications

- **Format:** Single-page HTML report with embedded charts (base64) and tables
- **Site URL:** https://bryanpcutsinger.github.io/SEP/
- **Publishing method:** GitHub Actions builds and deploys on push to main
- **Audience:** TODO
- **Tone:** TODO

## Workflow / Task Sequence

1. Download/fetch latest SEP data
2. Clean and process data
3. Generate visualizations (matplotlib/seaborn)
4. Build HTML report (`python src/build_report.py`)
5. Push to main → GitHub Actions deploys to Pages
6. **Local preview:** `python src/build_report.py && open _site/index.html`

## Conventions

- **Language:** Python
- **Data manipulation:** pandas
- **Visualization:** matplotlib, seaborn
- **Econometrics (if needed):** statsmodels, linearmodels
- **Code style:** Simple, readable, well-commented (explain what key steps do, not every line)
- **File naming:** lowercase with underscores (e.g., `fetch_sep_data.py`)

## Current Status

- GitHub Pages infrastructure set up
- Placeholder report deployed at https://bryanpcutsinger.github.io/SEP/
- Data collection and report content: TODO
