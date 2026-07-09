"""
Economic Stress Agent
Computes a composite cost-burden index (housing + gas + grocery as % of income)
per state, then asks Claude to interpret the pattern in plain language.
"""
import pandas as pd
from agents.claude_client import ask_claude


def compute_cost_burden_index(census_df: pd.DataFrame, bls_df: pd.DataFrame,
                               hud_df: pd.DataFrame) -> pd.DataFrame:
    income_by_state = (census_df.groupby("state")["state_median_income"].mean()
                       .reset_index().rename(columns={"state_median_income": "median_income"}))
    merged = income_by_state.merge(hud_df, on="state", how="left")

    # crude region mapping so state-level rows can join the 4 BLS regions
    region_map = _state_to_region_map()
    merged["region"] = merged["state"].map(region_map).fillna("West")
    merged = merged.merge(bls_df, on="region", how="left")

    # cost burden index = weighted combination of rent-to-income, gas & grocery CPI (normalized)
    merged["gas_norm"] = _normalize(merged["gas_cpi"])
    merged["grocery_norm"] = _normalize(merged["grocery_cpi"])
    merged["rent_norm"] = _normalize(merged["rent_to_income_ratio"])
    merged["cost_burden_index"] = (
        0.5 * merged["rent_norm"] + 0.25 * merged["gas_norm"] + 0.25 * merged["grocery_norm"]
    ).round(4)

    return merged[["state", "median_income", "rent_to_income_ratio", "gas_cpi",
                    "grocery_cpi", "cost_burden_index"]]


def _normalize(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    return (s - s.min()) / (s.max() - s.min() + 1e-9)


def _state_to_region_map() -> dict:
    northeast = {"Connecticut", "Maine", "Massachusetts", "New Hampshire", "New Jersey",
                 "New York", "Pennsylvania", "Rhode Island", "Vermont"}
    midwest = {"Illinois", "Indiana", "Iowa", "Kansas", "Michigan", "Minnesota", "Missouri",
               "Nebraska", "North Dakota", "Ohio", "South Dakota", "Wisconsin"}
    south = {"Alabama", "Arkansas", "Delaware", "Florida", "Georgia", "Kentucky", "Louisiana",
             "Maryland", "Mississippi", "North Carolina", "Oklahoma", "South Carolina",
             "Tennessee", "Texas", "Virginia", "West Virginia"}
    mapping = {}
    for s in northeast:
        mapping[s] = "Northeast"
    for s in midwest:
        mapping[s] = "Midwest"
    for s in south:
        mapping[s] = "South"
    # everything else -> West
    return mapping


def interpret_with_claude(cost_df: pd.DataFrame) -> str:
    top5 = cost_df.sort_values("cost_burden_index", ascending=False).head(5)
    bottom5 = cost_df.sort_values("cost_burden_index", ascending=True).head(5)
    prompt = f"""You are the Economic Stress Agent in a research pipeline.
Highest cost-burden states:
{top5.to_string(index=False)}

Lowest cost-burden states:
{bottom5.to_string(index=False)}

In 3-4 sentences, summarize the economic stress pattern across these states for a research report. Be factual and concise, no speculation beyond the data."""
    return ask_claude(prompt)


if __name__ == "__main__":
    from data_pipeline.census_agent import fetch_census_data
    from data_pipeline.bls_agent import fetch_bls_data
    from data_pipeline.hud_agent import fetch_hud_data

    census = fetch_census_data()
    bls = fetch_bls_data()
    hud = fetch_hud_data()
    result = compute_cost_burden_index(census, bls, hud)
    print(result.head(10))
