"""
SAMHSA / CDC BRFSS Connector
Pulls: mental health distress indicators by income bracket
Source: CDC BRFSS via the Socrata Open Data API (no key required)
Docs: https://dev.socrata.com/foundry/data.cdc.gov/dttw-5yxu
"""
import random
import requests
import pandas as pd
from config import INCOME_BRACKETS, STATES, USE_SYNTHETIC_FALLBACK

CDC_BRFSS_URL = "https://data.cdc.gov/resource/dttw-5yxu.json"

# Fixed survey year for every BRFSS pull. 2022 is the most recent year whose
# published results cover all 50 states for both the Overall and the
# Household-Income and Race/Ethnicity breakouts (2023 and 2024 are each missing
# 1-2 late-reporting states, e.g. Tennessee in 2024, Kentucky/Pennsylvania in
# 2023). Using one uniform year keeps every state on the same vintage instead of
# silently mixing years across states.
BRFSS_YEAR = "2022"

# CDC's own Household Income breakout uses 7 buckets topping out at $200k+,
# coarser than our 6 brackets above $50k -- no finer public breakdown exists,
# so the $50k-$99,999 and $100k-$199,999 CDC buckets are each reused across
# two of our brackets.
_BRACKET_MAP = {
    "<$25k": ["Less than $15,000", "$15,000-$24,999"],
    "$25k-$50k": ["$25,000-$34,999", "$35,000-$49,999"],
    "$50k-$75k": ["$50,000-$99,999"],
    "$75k-$100k": ["$50,000-$99,999"],
    "$100k-$150k": ["$100,000-$199,999"],
    "$150k+": ["$200,000+"],
}


def fetch_wellbeing_data() -> pd.DataFrame:
    """Returns DataFrame: income_bracket, distress_pct (frequent mental distress %)"""
    if not USE_SYNTHETIC_FALLBACK:
        return _fetch_real()
    return _fetch_synthetic()


def _fetch_real() -> pd.DataFrame:
    # questionid _MENT14D / responseid RESP224 = "14+ days when mental health
    # not good" -- the standard BRFSS "frequent mental distress" indicator.
    params = {
        "$limit": 5000,
        "$select": "break_out,data_value,sample_size",
        "$where": "questionid='_MENT14D' AND responseid='RESP224' "
                  f"AND break_out_category='Household Income' AND year='{BRFSS_YEAR}'",
    }
    resp = requests.get(CDC_BRFSS_URL, params=params, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data_value"] = pd.to_numeric(df.get("data_value"), errors="coerce")
    df["sample_size"] = pd.to_numeric(df.get("sample_size"), errors="coerce")
    df = df.dropna(subset=["data_value", "sample_size"])

    rows = []
    for bracket, cdc_labels in _BRACKET_MAP.items():
        subset = df[df["break_out"].isin(cdc_labels)]
        total_n = subset["sample_size"].sum()
        if total_n == 0:
            continue
        weighted_pct = (subset["data_value"] * subset["sample_size"]).sum() / total_n
        rows.append({"income_bracket": bracket, "distress_pct": round(weighted_pct, 2)})
    return pd.DataFrame(rows)


def _fetch_synthetic() -> pd.DataFrame:
    """Distress trends inversely with income - reflects real BRFSS patterns."""
    random.seed(3)
    base_rates = [22.5, 17.8, 14.2, 11.6, 9.4, 7.1]  # roughly matches published BRFSS gradients
    rows = []
    for bracket, base in zip(INCOME_BRACKETS, base_rates):
        noisy = round(base + random.uniform(-1.2, 1.2), 2)
        rows.append({"income_bracket": bracket, "distress_pct": noisy})
    return pd.DataFrame(rows)


def fetch_state_distress_data() -> pd.DataFrame:
    """Returns DataFrame: state, distress_pct -- real per-state (not income-
    stratified) frequent mental distress prevalence. Used as the regression
    target in model/regression_model.py instead of a synthetic proxy."""
    if not USE_SYNTHETIC_FALLBACK:
        return _fetch_state_real()
    return _fetch_state_synthetic()


def _fetch_state_real() -> pd.DataFrame:
    params = {
        "$limit": 5000,
        "$select": "locationdesc,data_value",
        "$where": "questionid='_MENT14D' AND responseid='RESP224' "
                  f"AND break_out_category='Overall' AND year='{BRFSS_YEAR}'",
    }
    resp = requests.get(CDC_BRFSS_URL, params=params, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df = df.rename(columns={"locationdesc": "state", "data_value": "distress_pct"})
    df["distress_pct"] = pd.to_numeric(df.get("distress_pct"), errors="coerce")
    df = df.dropna(subset=["distress_pct"])
    # drop DC/territories -- not in our fixed 50-state universe
    df = df[df["state"].isin(STATES)]
    return df[["state", "distress_pct"]].reset_index(drop=True)


def _fetch_state_synthetic() -> pd.DataFrame:
    random.seed(5)
    rows = [{"state": state, "distress_pct": round(random.uniform(10, 22), 2)} for state in STATES]
    return pd.DataFrame(rows)


# BRFSS race/ethnicity breakouts -> this project's 5 racial groups.
# The four smaller BRFSS categories are pooled (sample-size weighted) into
# Other/Multiracial to match the Census-side grouping.
_RACE_MAP = {
    "White, non-Hispanic": "White",
    "Black, non-Hispanic": "Black",
    "Hispanic": "Hispanic",
    "Asian, non-Hispanic": "Asian",
    "American Indian or Alaskan Native, non-Hispanic": "Other/Multiracial",
    "Multiracial, non-Hispanic": "Other/Multiracial",
    "Native Hawaiian or other Pacific Islander, non-Hispanic": "Other/Multiracial",
    "Other, non-Hispanic": "Other/Multiracial",
}


def fetch_race_distress_data() -> pd.DataFrame:
    """Returns DataFrame: state, race_group, distress_pct -- real per-state
    frequent mental distress prevalence stratified by race/ethnicity
    (proposal Objective 2: distress across cultural/racial groups)."""
    if not USE_SYNTHETIC_FALLBACK:
        return _fetch_race_real()
    return _fetch_race_synthetic()


def _fetch_race_real() -> pd.DataFrame:
    params = {
        "$limit": 5000,
        "$select": "locationdesc,break_out,data_value,sample_size",
        "$where": "questionid='_MENT14D' AND responseid='RESP224' "
                  f"AND break_out_category='Race/Ethnicity' AND year='{BRFSS_YEAR}'",
    }
    resp = requests.get(CDC_BRFSS_URL, params=params, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df = df.rename(columns={"locationdesc": "state"})
    df["data_value"] = pd.to_numeric(df.get("data_value"), errors="coerce")
    df["sample_size"] = pd.to_numeric(df.get("sample_size"), errors="coerce")
    df = df.dropna(subset=["data_value", "sample_size"])
    df = df[df["state"].isin(STATES)]
    df["race_group"] = df["break_out"].map(_RACE_MAP)
    df = df.dropna(subset=["race_group"])

    # pool the CDC breakouts into the project's 5 groups with a
    # sample-size-weighted average
    grouped = df.groupby(["state", "race_group"]).apply(
        lambda g: (g["data_value"] * g["sample_size"]).sum() / g["sample_size"].sum(),
        include_groups=False,
    ).reset_index(name="distress_pct")
    grouped["distress_pct"] = grouped["distress_pct"].round(2)
    return grouped


def _fetch_race_synthetic() -> pd.DataFrame:
    from config import RACIAL_GROUPS
    random.seed(13)
    rows = []
    for state in STATES:
        for group in RACIAL_GROUPS:
            rows.append({"state": state, "race_group": group,
                         "distress_pct": round(random.uniform(8, 26), 2)})
    return pd.DataFrame(rows)


def fetch_state_income_distress_data() -> pd.DataFrame:
    """Returns DataFrame: state, income_bracket, distress_pct -- real per-state
    frequent mental distress prevalence stratified by household income bracket.
    Powers the dashboard's income-bracket map filter (proposal section 5.4)."""
    if not USE_SYNTHETIC_FALLBACK:
        return _fetch_state_income_real()
    return _fetch_state_income_synthetic()


def _fetch_state_income_real() -> pd.DataFrame:
    params = {
        "$limit": 20000,
        "$select": "locationdesc,break_out,data_value,sample_size",
        "$where": "questionid='_MENT14D' AND responseid='RESP224' "
                  f"AND break_out_category='Household Income' AND year='{BRFSS_YEAR}'",
    }
    resp = requests.get(CDC_BRFSS_URL, params=params, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df = df.rename(columns={"locationdesc": "state"})
    df["data_value"] = pd.to_numeric(df.get("data_value"), errors="coerce")
    df["sample_size"] = pd.to_numeric(df.get("sample_size"), errors="coerce")
    df = df.dropna(subset=["data_value", "sample_size"])
    df = df[df["state"].isin(STATES)]

    # collapse CDC's 7 income buckets into the project's 6 brackets, sample-size
    # weighted, per state (same _BRACKET_MAP used for the national figure)
    rows = []
    for (state,), grp in df.groupby(["state"]):
        for bracket, cdc_labels in _BRACKET_MAP.items():
            subset = grp[grp["break_out"].isin(cdc_labels)]
            total_n = subset["sample_size"].sum()
            if total_n == 0:
                continue
            weighted = (subset["data_value"] * subset["sample_size"]).sum() / total_n
            rows.append({"state": state, "income_bracket": bracket,
                         "distress_pct": round(weighted, 2)})
    return pd.DataFrame(rows)


def _fetch_state_income_synthetic() -> pd.DataFrame:
    random.seed(17)
    base_rates = dict(zip(INCOME_BRACKETS, [22.5, 17.8, 14.2, 11.6, 9.4, 7.1]))
    rows = []
    for state in STATES:
        for bracket in INCOME_BRACKETS:
            noisy = round(base_rates[bracket] + random.uniform(-2.5, 2.5), 2)
            rows.append({"state": state, "income_bracket": bracket,
                         "distress_pct": max(3.0, noisy)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(fetch_wellbeing_data())
    print(fetch_state_distress_data())
    print(fetch_race_distress_data().head())
    print(fetch_state_income_distress_data().head())
