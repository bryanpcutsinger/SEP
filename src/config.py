"""
config.py — Shared constants for the SEP pipeline.

Canonical definitions of variable names, display names, and ordering.
Imported by process_data.py, make_charts.py, and build_report.py.
"""

# Internal variable names (must match what the parser produces)
VARIABLE_ORDER = [
    "Change in real GDP",
    "Unemployment rate",
    "PCE inflation",
    "Core PCE inflation",
    "Federal funds rate",
]

# Friendly display names for tables and text
DISPLAY_NAMES = {
    "Change in real GDP": "Real GDP Growth",
    "Unemployment rate": "Unemployment Rate",
    "PCE inflation": "PCE Inflation",
    "Core PCE inflation": "Core PCE Inflation",
    "Federal funds rate": "Federal Funds Rate",
}

# Chart titles (appends "Projections" for chart context)
CHART_TITLES = {
    "Change in real GDP": "Real GDP Growth Projections",
    "Unemployment rate": "Unemployment Rate Projections",
    "PCE inflation": "PCE Inflation Projections",
    "Core PCE inflation": "Core PCE Inflation Projections",
    "Federal funds rate": "Federal Funds Rate Projections",
}

# Horizon sort order — year list is extended dynamically by _build_horizon_order()
_BASE_YEARS = list(range(2024, 2030))
HORIZON_ORDER = [str(y) for y in _BASE_YEARS] + ["Longer Run"]
