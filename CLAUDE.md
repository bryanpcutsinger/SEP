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
│       └── deploy.yml        # GitHub Actions: fetch → process → build → deploy
├── data/
│   ├── raw/                  # Scraped SEP HTML and parsed CSVs
│   └── processed/            # Chart-ready data
├── src/
│   ├── fetch_sep_data.py     # Scrapes SEP from federalreserve.gov
│   ├── fetch_sep_fred.py     # FRED API fallback (medians only)
│   ├── process_data.py       # Transforms raw data for charts/tables
│   ├── generate_takeaways.py # Template-based key takeaway bullets
│   ├── make_charts.py        # Generates all matplotlib charts
│   ├── build_report.py       # Orchestrates pipeline, renders HTML
│   └── templates/
│       └── base.html         # Jinja2 HTML template
├── tests/
│   ├── fixtures/             # Cached SEP HTML for offline testing
│   ├── test_parsers.py       # Parser unit tests
│   └── test_takeaways.py     # Takeaway generation tests
└── _site/                    # Built site (generated, gitignored)
```

## Data Sources

- **Primary: Federal Reserve website** — SEP data is scraped directly from the accessible HTML version of the projection materials at `federalreserve.gov/monetarypolicy/fomcprojtabl{YYYYMMDD}.htm`. The script auto-discovers the most recent SEP from the FOMC calendar page.

  Data extracted:
  | Source | Contents | Output |
  |--------|----------|--------|
  | Table 1 | Median, central tendency, range (current + previous SEP) | `data/raw/sep_table1.csv`, `sep_table1_prev.csv` |
  | Figure 2 | Fed funds dot plot (participant counts by rate level) | `data/raw/sep_dotplot.csv` |
  | Figures 3.A-3.E | Participant distribution histograms | `data/raw/sep_distributions.csv` |
  | Metadata | Meeting date, SEP URL | `data/raw/sep_metadata.json` |

- **Fallback: FRED API** — `src/fetch_sep_fred.py` fetches median-only projections via the `fredapi` package. Requires `FRED_API_KEY` env var. Used if the Fed changes their HTML format.

## Report Specifications

- **Format:** Single-page HTML report with 6 embedded charts (base64 PNGs) and a summary table
- **Charts:** 1 dot plot + 5 band charts (median/central tendency/range for each variable)
- **Key takeaways:** Auto-generated from data using template-based rules (no LLM dependency)
- **Site URL:** https://bryanpcutsinger.github.io/SEP/
- **Publishing method:** GitHub Actions builds and deploys on push to main
- **Audience:** Media, political leaders, business leaders, educated non-economists
- **Tone:** Light analytical commentary — interprets patterns, not just restates numbers

## Workflow / Task Sequence

1. `python src/fetch_sep_data.py` — scrape latest SEP from Fed website
2. `python src/process_data.py` — transform raw data for charts
3. `python src/build_report.py` — generate charts, takeaways, render HTML
4. Push to main → GitHub Actions deploys to Pages
5. **Local preview:** `python src/fetch_sep_data.py && python src/process_data.py && python src/build_report.py && open _site/index.html`
6. **Offline dev (uses cached fixture):** `python src/fetch_sep_data.py --fixture tests/fixtures/fomcprojtabl20251210.htm && python src/process_data.py && python src/build_report.py && open _site/index.html`
7. **Run tests:** `python -m unittest discover -s tests -v`

## Conventions

- **Language:** Python
- **Data manipulation:** pandas
- **Visualization:** matplotlib
- **HTML templating:** Jinja2
- **Web scraping:** BeautifulSoup + requests (with polite delays and User-Agent)
- **Code style:** Simple, readable, well-commented (explain what key steps do, not every line)
- **File naming:** lowercase with underscores (e.g., `fetch_sep_data.py`)

## Current Status

- Full pipeline operational: fetch → process → charts → takeaways → HTML report
- 6 charts: dot plot + 5 band charts (GDP, unemployment, PCE, core PCE, fed funds)
- Auto-generated takeaways with previous-SEP comparison
- 27 unit tests passing
- GitHub Pages deployment configured
- Cleanup audit completed (dead code, stale files, HTML table fix)
- FOMC inter-meeting context feature: deferred (TODO)
