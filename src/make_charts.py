"""
make_charts.py — Generate SEP visualizations.

Produces 6 charts:
  - 1 fed funds dot plot (Figure 2 style)
  - 5 band charts (median + central tendency + range for each variable)

Each chart is returned as {"data": base64_string, "caption": string}
matching the Jinja2 template interface.

Usage:
    from make_charts import make_all_charts
    charts = make_all_charts(summary_df, prev_df, dotplot_df)
"""

import base64
import io

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# Color palette
MEDIAN_COLOR = "#1f4e79"
CT_COLOR = "#4a86c8"
RANGE_COLOR = "#a3c4e8"
GRID_COLOR = "#e0e0e0"
BG_COLOR = "#fafafa"

# Chart dimensions
BAND_FIGSIZE = (8, 4)
DOT_FIGSIZE = (8, 6)
DPI = 150

HORIZON_ORDER = ["2024", "2025", "2026", "2027", "2028", "2029", "Longer Run"]

DISPLAY_NAMES = {
    "Change in real GDP": "Real GDP Growth Projections",
    "Unemployment rate": "Unemployment Rate Projections",
    "PCE inflation": "PCE Inflation Projections",
    "Core PCE inflation": "Core PCE Inflation Projections",
    "Federal funds rate": "Federal Funds Rate Projections",
}

UNITS = {
    "Change in real GDP": "",
    "Unemployment rate": "",
    "PCE inflation": "Percent change, Q4/Q4",
    "Core PCE inflation": "Percent change, Q4/Q4",
    "Federal funds rate": "",
}


def _to_base64(fig):
    """Convert matplotlib figure to base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
                facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _get_ordered_horizons(df):
    """Get horizons in display order from the data."""
    available = df["horizon"].unique()
    ordered = [h for h in HORIZON_ORDER if h in available]
    return ordered


def make_band_chart(summary_df, prev_df, variable):
    """Create a band chart for a single variable.

    Shows full range (lightest), central tendency (medium), and median (dots).
    """
    var_data = summary_df[summary_df["variable"] == variable].copy()
    horizons = _get_ordered_horizons(var_data)

    if not horizons:
        return None

    # Separate year horizons from "Longer Run"
    year_horizons = [h for h in horizons if h != "Longer Run"]
    has_lr = "Longer Run" in horizons

    # Build x positions: years get consecutive integers, Longer Run gets a gap
    x_positions = list(range(len(year_horizons)))
    x_labels = list(year_horizons)
    if has_lr:
        lr_x = len(year_horizons) + 0.7  # gap before Longer Run
        x_positions.append(lr_x)
        x_labels.append("Longer\nRun")

    # Extract values in order
    medians, ct_lows, ct_highs, range_lows, range_highs = [], [], [], [], []
    for h in (year_horizons + (["Longer Run"] if has_lr else [])):
        row = var_data[var_data["horizon"] == h]
        if row.empty:
            medians.append(np.nan)
            ct_lows.append(np.nan)
            ct_highs.append(np.nan)
            range_lows.append(np.nan)
            range_highs.append(np.nan)
        else:
            medians.append(row["median"].iloc[0])
            ct_lows.append(row["ct_low"].iloc[0])
            ct_highs.append(row["ct_high"].iloc[0])
            range_lows.append(row["range_low"].iloc[0])
            range_highs.append(row["range_high"].iloc[0])

    x = np.array(x_positions)
    prev_lookup = {}  # filled later if previous SEP exists
    medians = np.array(medians, dtype=float)
    ct_lows = np.array(ct_lows, dtype=float)
    ct_highs = np.array(ct_highs, dtype=float)
    range_lows = np.array(range_lows, dtype=float)
    range_highs = np.array(range_highs, dtype=float)

    fig, ax = plt.subplots(figsize=BAND_FIGSIZE)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Full range band
    valid = ~(np.isnan(range_lows) | np.isnan(range_highs))
    if valid.any():
        ax.fill_between(x[valid], range_lows[valid], range_highs[valid],
                        color=RANGE_COLOR, alpha=0.4, label="Full range")

    # Central tendency band
    valid = ~(np.isnan(ct_lows) | np.isnan(ct_highs))
    if valid.any():
        ax.fill_between(x[valid], ct_lows[valid], ct_highs[valid],
                        color=CT_COLOR, alpha=0.4, label="Central tendency")

    # Previous SEP median (if available) — must come before data labels
    if prev_df is not None and not prev_df.empty:
        prev_var = prev_df[prev_df["variable"] == variable]
        if not prev_var.empty:
            prev_x, prev_y = [], []
            for i, h in enumerate(year_horizons + (["Longer Run"] if has_lr else [])):
                prev_row = prev_var[prev_var["horizon"] == h]
                if not prev_row.empty:
                    prev_med = prev_row["median"].iloc[0]
                    if pd.notna(prev_med):
                        prev_x.append(x[i])
                        prev_y.append(prev_med)
            if prev_x:
                ax.plot(prev_x, prev_y, color='red', linestyle='--',
                        linewidth=1.5, zorder=4, label="Prior Median")
                prev_lookup = dict(zip(prev_x, prev_y))

    # Median line + dots
    valid = ~np.isnan(medians)
    if valid.any():
        ax.plot(x[valid], medians[valid], color=MEDIAN_COLOR, linewidth=2,
                zorder=5)
        ax.scatter(x[valid], medians[valid], color=MEDIAN_COLOR, s=60,
                   zorder=6, label="Median")
        # Data labels — shift below dot when prior-SEP line is just above,
        # but always label above for the last year to avoid x-axis overlap
        last_year_x = len(year_horizons) - 1 if year_horizons else -1
        for xi, mi in zip(x[valid], medians[valid]):
            offset_y = 10
            if xi == last_year_x:
                offset_y = 10  # always above for last year before Longer Run
            elif xi in prev_lookup:
                prev_val = prev_lookup[xi]
                # If previous SEP is above (or equal) and within ~0.4pp, label below
                if prev_val >= mi and (prev_val - mi) < 0.4:
                    offset_y = -14
            ax.annotate(f"{mi:.1f}", (xi, mi), textcoords="offset points",
                        xytext=(0, offset_y), ha="center", fontsize=8,
                        color=MEDIAN_COLOR, fontweight="bold",
                        va="top" if offset_y < 0 else "bottom")

    # 2% target line for PCE inflation only
    if variable == "PCE inflation":
        ax.axhline(y=2.0, color="black", linestyle=":", linewidth=1,
                   alpha=0.7, label="2% target")

    # Separator line before Longer Run
    if has_lr and len(year_horizons) > 0:
        sep_x = len(year_horizons) - 0.35
        ax.axvline(x=sep_x, color=GRID_COLOR, linestyle=":", linewidth=1)

    # Formatting
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=9)
    ax.set_ylabel("Percent", fontsize=10)
    ax.set_title(DISPLAY_NAMES.get(variable, variable), fontsize=13,
                 fontweight="bold", pad=12)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    handles, labels = ax.get_legend_handles_labels()
    # Deduplicate
    by_label = dict(zip(labels, handles))
    legend_loc = "lower right" if variable == "Federal funds rate" else "lower left" if variable == "Unemployment rate" else "upper right"
    ax.legend(by_label.values(), by_label.keys(), loc=legend_loc,
              fontsize=8, framealpha=0.9)

    subtitle = UNITS.get(variable, "")
    if subtitle:
        ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, ha="center",
                fontsize=8, color="#666666")

    caption = DISPLAY_NAMES.get(variable, variable)
    return {"data": _to_base64(fig), "caption": caption}


def make_dotplot(dotplot_df):
    """Create the fed funds rate dot plot (Figure 2 style).

    Each dot represents one FOMC participant's projection.
    """
    if dotplot_df.empty:
        return None

    horizons = _get_ordered_horizons(dotplot_df)
    # For the dot plot, skip the current year if its data looks like a single point
    # (all participants agree on current policy)

    fig, ax = plt.subplots(figsize=DOT_FIGSIZE)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Separate year horizons from Longer Run
    year_horizons = [h for h in horizons if h != "Longer Run"]
    has_lr = "Longer Run" in horizons

    x_positions = {}
    x_labels = []
    for i, h in enumerate(year_horizons):
        x_positions[h] = i
        x_labels.append(h)
    if has_lr:
        lr_x = len(year_horizons) + 0.7
        x_positions["Longer Run"] = lr_x
        x_labels.append("Longer\nRun")

    # Get all unique rates for y-axis
    all_rates = sorted(dotplot_df["rate"].unique())
    rate_min = min(all_rates) - 0.125
    rate_max = max(all_rates) + 0.125

    # Plot dots
    for _, row in dotplot_df.iterrows():
        h = row["horizon"]
        if h not in x_positions:
            continue
        base_x = x_positions[h]
        rate = row["rate"]
        n = int(row["n_participants"])

        # Place dots with horizontal jitter
        if n == 1:
            offsets = [0]
        else:
            # Spread dots evenly around center
            spread = min(0.35, 0.08 * n)
            offsets = np.linspace(-spread, spread, n)

        for offset in offsets:
            ax.scatter(base_x + offset, rate, color=MEDIAN_COLOR, s=30,
                       zorder=5, edgecolors="white", linewidths=0.3)

    # Separator before Longer Run
    if has_lr and len(year_horizons) > 0:
        sep_x = len(year_horizons) - 0.35
        ax.axvline(x=sep_x, color=GRID_COLOR, linestyle=":", linewidth=1)

    # Formatting
    all_x = list(range(len(year_horizons)))
    if has_lr:
        all_x.append(lr_x)
    ax.set_xticks(all_x)
    ax.set_xticklabels(x_labels, fontsize=10)

    # Y-axis: 0.25pp grid lines
    ax.yaxis.set_major_locator(mticker.MultipleLocator(0.25))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    ax.set_ylim(rate_min, rate_max)
    ax.set_title("Federal Funds Rate — Dot Plot", fontsize=13,
                 fontweight="bold", pad=16)
    ax.text(0.5, 1.01, "Each dot represents one participant\u2019s projection",
            transform=ax.transAxes, ha="center", fontsize=8, color="#666666")

    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.7)
    ax.grid(axis="x", visible=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return {"data": _to_base64(fig), "caption": "Federal Funds Rate — Dot Plot"}


def make_all_charts(summary_df, prev_df=None, dotplot_df=None):
    """Generate all charts and return as list of {data, caption} dicts."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.titlesize": 13,
    })

    charts = []

    # Chart 1: Dot plot (leads the report)
    if dotplot_df is not None and not dotplot_df.empty:
        dp_chart = make_dotplot(dotplot_df)
        if dp_chart:
            charts.append(dp_chart)

    # Charts 2-6: Band charts for each variable
    variables = [
        "Change in real GDP",
        "Unemployment rate",
        "PCE inflation",
        "Core PCE inflation",
        "Federal funds rate",
    ]

    for var in variables:
        chart = make_band_chart(summary_df, prev_df, var)
        if chart:
            charts.append(chart)

    return charts
