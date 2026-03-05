# SEP Project — CLAUDE.md

## Project Overview

Goal: Summarize the most recent FOMC Summary of Economic Projections (SEP) and publish the report on Substack. The GitHub repo will serve as the source of truth for data, code, and output.

## Project Structure

<!-- TODO: Update as files are added -->

```
SEP/
├── CLAUDE.md
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/          # Original SEP data as downloaded
│   └── processed/    # Cleaned/transformed data ready for analysis
├── src/              # Python scripts for data collection, processing, visualization
└── output/           # Final report artifacts (charts, tables, markdown)
```

## Data Sources

<!-- TODO: Identify and document SEP data sources -->
<!-- Likely candidates: Federal Reserve website, FRED API, official FOMC projection materials -->

## Report Specifications

<!-- TODO: Define report format, sections, audience, and Substack publishing details -->
<!-- Key questions:
  - What sections should the report include?
  - What charts/tables are needed?
  - What is the target audience and tone?
  - How will the report be published to Substack? (no native GitHub integration — needs research)
-->

## Workflow / Task Sequence

<!-- TODO: Define the pipeline from data collection to publication -->
<!-- Rough sequence:
  1. Download/fetch latest SEP data
  2. Clean and process data
  3. Generate visualizations and tables
  4. Assemble report (markdown or HTML)
  5. Publish to Substack
-->

## Conventions

- **Language:** Python
- **Data manipulation:** pandas
- **Visualization:** matplotlib, seaborn
- **Econometrics (if needed):** statsmodels, linearmodels
- **Code style:** Simple, readable, well-commented (explain what key steps do, not every line)
- **File naming:** lowercase with underscores (e.g., `fetch_sep_data.py`)

## Current Status

- CLAUDE.md skeleton created
- Project directory scaffolded with placeholder directories
- Initial commit pushed to GitHub
