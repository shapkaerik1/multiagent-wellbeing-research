"""
Culture Disparity Agent
Computes income and cost-burden gaps across racial/ethnic groups per state.
"""
import pandas as pd
from agents.claude_client import ask_claude


def compute_disparity_scores(census_df: pd.DataFrame) -> pd.DataFrame:
    """Returns per-state disparity score = (max group income - min group income) / state avg income"""
    rows = []
    for state, grp in census_df.groupby("state"):
        avg_income = grp["median_income"].mean()
        gap = grp["median_income"].max() - grp["median_income"].min()
        disparity_score = round(gap / avg_income, 4) if avg_income else None
        lowest_group = grp.loc[grp["median_income"].idxmin(), "race_group"]
        highest_group = grp.loc[grp["median_income"].idxmax(), "race_group"]
        rows.append({
            "state": state,
            "disparity_score": disparity_score,
            "lowest_income_group": lowest_group,
            "highest_income_group": highest_group,
        })
    return pd.DataFrame(rows)


def interpret_with_claude(disparity_df: pd.DataFrame) -> str:
    top5 = disparity_df.sort_values("disparity_score", ascending=False).head(5)
    prompt = f"""You are the Culture Disparity Agent in a research pipeline.
States with the largest income disparity across racial/ethnic groups:
{top5.to_string(index=False)}

In 3-4 sentences, summarize this disparity pattern for a research report, staying strictly factual and avoiding causal claims not supported by the data."""
    return ask_claude(prompt)


if __name__ == "__main__":
    from data_pipeline.census_agent import fetch_census_data
    census = fetch_census_data()
    print(compute_disparity_scores(census).head(10))
