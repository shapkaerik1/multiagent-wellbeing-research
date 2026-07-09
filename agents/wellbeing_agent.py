"""
Wellbeing Agent
Maps mental health distress indicators to income brackets and produces
distress proxy scores usable by the regression model.
"""
import pandas as pd
from agents.claude_client import ask_claude


def compute_distress_scores(wellbeing_df: pd.DataFrame) -> pd.DataFrame:
    df = wellbeing_df.copy()
    df["distress_proxy_score"] = (df["distress_pct"] / df["distress_pct"].max()).round(4)
    return df


def interpret_with_claude(distress_df: pd.DataFrame) -> str:
    prompt = f"""You are the Wellbeing Agent in a research pipeline.
Frequent mental distress rates by income bracket:
{distress_df.to_string(index=False)}

In 3-4 sentences, describe the relationship between income bracket and psychological distress shown here, staying strictly factual."""
    return ask_claude(prompt)


if __name__ == "__main__":
    from data_pipeline.samhsa_agent import fetch_wellbeing_data
    wb = fetch_wellbeing_data()
    print(compute_distress_scores(wb))
