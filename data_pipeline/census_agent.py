"""
Census Data Connector
Pulls: median household income, race/ethnicity distribution, by state
Source: U.S. Census Bureau American Community Survey (ACS) 5-Year API
Docs: https://www.census.gov/data/developers/data-sets/acs-5year.html
"""
import random
import requests
import pandas as pd
from config import CENSUS_API_KEY, STATES, RACIAL_GROUPS, USE_SYNTHETIC_FALLBACK

ACS_URL = "https://api.census.gov/data/2023/acs/acs5"


def fetch_census_data() -> pd.DataFrame:
    """Returns DataFrame: state, race_group, median_income, population_share,
    state_median_income (overall state figure, repeated per race_group row --
    used downstream for cost-burden/rent-ratio calcs that need one number
    per state rather than a race-specific one)."""
    if CENSUS_API_KEY and not USE_SYNTHETIC_FALLBACK:
        return _fetch_real()
    return _fetch_synthetic()


def _fetch_real() -> pd.DataFrame:
    # B19013 = overall median household income.
    # B19013A/B/D/I/G = median household income by race/ethnicity of
    # householder (White, Black, Asian, Hispanic, Two-or-More-Races alone) --
    # these are separate ACS "race iteration" tables, distinct from B02001
    # (which only has population counts, not income).
    # B03002 = Hispanic-or-Latino-by-race cross tab, whose categories are
    # mutually exclusive (unlike combining B02001 race counts with B03003
    # Hispanic ethnicity, which double-counts White/Black/Asian Hispanics).
    params = {
        "get": ",".join([
            "NAME",
            "B19013_001E",
            "B19013A_001E", "B19013B_001E", "B19013D_001E", "B19013I_001E", "B19013G_001E",
            "B03002_001E", "B03002_003E", "B03002_004E", "B03002_006E", "B03002_012E",
        ]),
        "for": "state:*",
        "key": CENSUS_API_KEY,
    }
    resp = requests.get(ACS_URL, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    header, data = rows[0], rows[1:]
    df = pd.DataFrame(data, columns=header)
    # "for=state:*" appends a trailing FIPS "state" code column -- drop it
    # before renaming NAME to "state", or the DataFrame ends up with two
    # columns both named "state".
    df = df.drop(columns=["state"])
    df = df.rename(columns={
        "NAME": "state",
        "B19013_001E": "state_median_income",
        "B19013A_001E": "income_white",
        "B19013B_001E": "income_black",
        "B19013D_001E": "income_asian",
        "B19013I_001E": "income_hispanic",
        "B19013G_001E": "income_other",
        "B03002_001E": "total_pop",
        "B03002_003E": "white_pop",
        "B03002_004E": "black_pop",
        "B03002_006E": "asian_pop",
        "B03002_012E": "hispanic_pop",
    })
    numeric_cols = ["state_median_income", "income_white", "income_black", "income_asian",
                     "income_hispanic", "income_other", "total_pop", "white_pop",
                     "black_pop", "asian_pop", "hispanic_pop"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    # "for=state:*" also returns DC and Puerto Rico, which aren't in our
    # fixed 50-state universe (and have no HUD rent data to join against).
    df = df[df["state"].isin(STATES)]

    long_rows = []
    for _, r in df.iterrows():
        total = r["total_pop"] or 1
        named_shares = {
            "White": r["white_pop"] / total,
            "Black": r["black_pop"] / total,
            "Asian": r["asian_pop"] / total,
            "Hispanic": r["hispanic_pop"] / total,
        }
        # B03002 categories are mutually exclusive, so this residual is a
        # true "everyone else" share (AIAN, NHPI, some-other-race,
        # two-or-more-races, all non-Hispanic) rather than a double-counted
        # leftover.
        named_shares["Other/Multiracial"] = max(0, 1 - sum(named_shares.values()))
        group_income = {
            "White": r["income_white"],
            "Black": r["income_black"],
            "Asian": r["income_asian"],
            "Hispanic": r["income_hispanic"],
            "Other/Multiracial": r["income_other"],
        }
        for group, share in named_shares.items():
            long_rows.append({
                "state": r["state"],
                "race_group": group,
                "median_income": group_income[group],
                "population_share": share,
                "state_median_income": r["state_median_income"],
            })
    return pd.DataFrame(long_rows)


def _fetch_synthetic() -> pd.DataFrame:
    """Realistic synthetic fallback, same schema as the real API output."""
    random.seed(42)
    rows = []
    for state in STATES:
        base_income = random.randint(48000, 92000)
        shares = [random.random() for _ in RACIAL_GROUPS]
        total = sum(shares)
        shares = [s / total for s in shares]
        for group, share in zip(RACIAL_GROUPS, shares):
            income_adj = base_income * random.uniform(0.75, 1.15)
            rows.append({
                "state": state,
                "race_group": group,
                "median_income": round(income_adj, 2),
                "population_share": round(share, 4),
                "state_median_income": base_income,
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = fetch_census_data()
    print(df.head(10))
    print(f"\n{len(df)} rows total")
