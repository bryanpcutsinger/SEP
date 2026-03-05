"""
generate_takeaways.py — Auto-generate key takeaway bullets from SEP data.

Uses template-based rules with conditional logic. No LLM dependency — fully
deterministic output from the same input data.

Usage:
    from generate_takeaways import generate_takeaways
    bullets = generate_takeaways(current_df, prev_df, meeting_date)
"""

import pandas as pd


def _get_val(df, variable, horizon, col="median"):
    """Get a single value from the summary DataFrame."""
    row = df[(df["variable"] == variable) & (df["horizon"] == horizon)]
    if row.empty:
        return None
    val = row[col].iloc[0]
    return val if pd.notna(val) else None


def _direction(curr, prev):
    """Return directional word based on change."""
    if curr is None or prev is None:
        return None, None
    diff = curr - prev
    if abs(diff) < 0.05:
        return "unchanged", 0
    elif diff > 0:
        return "up", diff
    else:
        return "down", diff


def _fmt(val):
    """Format a number to 1 decimal place."""
    if val is None:
        return "N/A"
    return f"{val:.1f}"


def _next_forecast_year(df):
    """Find the first forecast year (not current year, not Longer Run)."""
    horizons = df["horizon"].unique()
    years = sorted([h for h in horizons if h != "Longer Run" and h.isdigit()])
    # Return second year if available (next year), else first
    if len(years) >= 2:
        return years[1]
    elif years:
        return years[0]
    return None


def generate_takeaways(current_df, prev_df=None, meeting_date=None):
    """Generate 4-5 key takeaway bullets from SEP data.

    Args:
        current_df: Current SEP summary DataFrame
        prev_df: Previous SEP summary DataFrame (optional)
        meeting_date: String like "December 18, 2024" (optional)

    Returns:
        List of takeaway strings
    """
    bullets = []
    has_prev = prev_df is not None and not prev_df.empty
    year = _next_forecast_year(current_df)
    if year is None:
        return ["SEP data could not be interpreted for takeaways."]

    # 1. Fed funds rate — always included (highest media interest)
    ffr_curr = _get_val(current_df, "Federal funds rate", year)
    ffr_prev = _get_val(prev_df, "Federal funds rate", year) if has_prev else None
    ffr_curr_yr = _get_val(current_df, "Federal funds rate",
                           str(int(year) - 1)) if year.isdigit() else None

    if ffr_curr is not None:
        # Calculate implied rate moves
        if ffr_curr_yr is not None:
            diff_bps = round((ffr_curr - ffr_curr_yr) * 100 / 25) * 25
            n_moves = abs(int(diff_bps / 25))
            if diff_bps < 0:
                move_word = "cut" if n_moves == 1 else "cuts"
                bullet = (f"The median participant projects {n_moves} rate "
                          f"{move_word} in {year}, bringing the federal funds "
                          f"rate to {_fmt(ffr_curr)}%")
            elif diff_bps > 0:
                move_word = "hike" if n_moves == 1 else "hikes"
                bullet = (f"The median participant projects {n_moves} rate "
                          f"{move_word} in {year}, raising the federal funds "
                          f"rate to {_fmt(ffr_curr)}%")
            else:
                bullet = (f"The median projection holds rates steady at "
                          f"{_fmt(ffr_curr)}% through {year}")

            if has_prev and ffr_prev is not None:
                direction, _ = _direction(ffr_curr, ffr_prev)
                if direction == "up":
                    bullet += f", a higher path than projected in the previous SEP ({_fmt(ffr_prev)}%)"
                elif direction == "down":
                    bullet += f", a lower path than projected in the previous SEP ({_fmt(ffr_prev)}%)"
            bullet += "."
            bullets.append(bullet)
        else:
            bullets.append(
                f"The median federal funds rate projection for {year} is {_fmt(ffr_curr)}%."
            )

    # 2. Inflation — always included
    pce_curr = _get_val(current_df, "PCE inflation", year)
    pce_prev = _get_val(prev_df, "PCE inflation", year) if has_prev else None

    if pce_curr is not None:
        # Find when inflation reaches 2%
        horizons = sorted([h for h in current_df[current_df["variable"] == "PCE inflation"]["horizon"].unique()
                          if h != "Longer Run" and h.isdigit()])
        target_year = None
        for h in horizons:
            val = _get_val(current_df, "PCE inflation", h)
            if val is not None and val <= 2.05:
                target_year = h
                break

        if target_year:
            bullet = f"PCE inflation is projected to reach the 2% target by {target_year}"
        else:
            bullet = f"PCE inflation is not expected to reach the 2% target within the projection window"

        if has_prev and pce_prev is not None:
            direction, _ = _direction(pce_curr, pce_prev)
            if direction == "up":
                bullet += (f" — the {year} projection shifted higher to "
                           f"{_fmt(pce_curr)}% from {_fmt(pce_prev)}%")
            elif direction == "down":
                bullet += (f" — the {year} projection eased to "
                           f"{_fmt(pce_curr)}% from {_fmt(pce_prev)}%")
        bullet += "."
        bullets.append(bullet)

    # 3. GDP growth — include if changed or noteworthy
    gdp_curr = _get_val(current_df, "Change in real GDP", year)
    gdp_prev = _get_val(prev_df, "Change in real GDP", year) if has_prev else None

    if gdp_curr is not None:
        direction, _ = _direction(gdp_curr, gdp_prev)
        if has_prev and direction in ("up", "down"):
            strength = "stronger" if direction == "up" else "weaker"
            bullet = (f"Real GDP growth for {year} revised {direction} to "
                      f"{_fmt(gdp_curr)}% from {_fmt(gdp_prev)}%, "
                      f"suggesting participants see a {strength} near-term outlook.")
        else:
            bullet = (f"Participants project real GDP growth of {_fmt(gdp_curr)}% "
                      f"in {year}.")
        bullets.append(bullet)

    # 4. Unemployment — include if changed
    unemp_curr = _get_val(current_df, "Unemployment rate", year)
    unemp_prev = _get_val(prev_df, "Unemployment rate", year) if has_prev else None

    if unemp_curr is not None:
        direction, _ = _direction(unemp_curr, unemp_prev)
        if has_prev and direction in ("up", "down"):
            verb = "rise to" if direction == "up" else "fall to"
            bullet = (f"The unemployment rate is expected to {verb} "
                      f"{_fmt(unemp_curr)}% in {year}, "
                      f"{'up' if direction == 'up' else 'down'} from "
                      f"{_fmt(unemp_prev)}% in the previous projection.")
        else:
            bullet = (f"The unemployment rate is projected at "
                      f"{_fmt(unemp_curr)}% for {year}.")
        bullets.append(bullet)

    # 5. Disagreement — include if fed funds range is wide
    ffr_range_low = _get_val(current_df, "Federal funds rate", year, "range_low")
    ffr_range_high = _get_val(current_df, "Federal funds rate", year, "range_high")
    if ffr_range_low is not None and ffr_range_high is not None:
        spread = ffr_range_high - ffr_range_low
        if spread > 1.0:
            bullet = (f"The dot plot reveals significant disagreement on the "
                      f"{year} rate path, with projections spanning "
                      f"{_fmt(spread)} percentage points.")
            bullets.append(bullet)

    # Cap at 5 bullets
    return bullets[:5]
