"""
Main Orchestration Script
Runs the full pipeline end to end: data collection -> 4 agents ->
coordinator synthesis -> regression model -> saved outputs for the dashboard.

Usage:
    python main.py
"""
import json
import pandas as pd

from data_pipeline.census_agent import fetch_census_data
from data_pipeline.bls_agent import fetch_bls_data
from data_pipeline.hud_agent import fetch_hud_data
from data_pipeline.samhsa_agent import (fetch_wellbeing_data, fetch_state_distress_data,
                                        fetch_race_distress_data,
                                        fetch_state_income_distress_data, BRFSS_YEAR)

from agents.economic_stress_agent import compute_cost_burden_index, interpret_with_claude as econ_interpret
from agents.culture_disparity_agent import compute_disparity_scores, interpret_with_claude as disparity_interpret
from agents.wellbeing_agent import compute_distress_scores, interpret_with_claude as wellbeing_interpret
from agents.web_search_agent import get_policy_context
from agents.coordinator_agent import synthesize_report

from model.regression_model import build_training_frame, train_model


def run_pipeline():
    print("=== Phase 1: Data Collection ===")
    census_df = fetch_census_data()
    bls_df = fetch_bls_data()
    hud_df = fetch_hud_data(dict(zip(census_df["state"], census_df["state_median_income"])))
    wellbeing_raw = fetch_wellbeing_data()
    state_distress_df = fetch_state_distress_data()
    race_distress_df = fetch_race_distress_data()
    income_distress_df = fetch_state_income_distress_data()
    print(f"Census rows: {len(census_df)} | BLS rows: {len(bls_df)} | "
          f"HUD rows: {len(hud_df)} | SAMHSA rows: {len(wellbeing_raw)} | "
          f"State distress rows: {len(state_distress_df)} | "
          f"Race-stratified distress rows: {len(race_distress_df)} | "
          f"State x income distress rows: {len(income_distress_df)}")

    print("\n=== Phase 2: Agent Processing ===")
    cost_df = compute_cost_burden_index(census_df, bls_df, hud_df)
    disparity_df = compute_disparity_scores(census_df)
    distress_df = compute_distress_scores(wellbeing_raw)

    print("Running Economic Stress Agent...")
    econ_summary = econ_interpret(cost_df)
    print("Running Culture Disparity Agent...")
    disparity_summary = disparity_interpret(disparity_df)
    print("Running Wellbeing Agent...")
    wellbeing_summary = wellbeing_interpret(distress_df)
    print("Running Web Search Agent...")
    top_states = cost_df.sort_values("cost_burden_index", ascending=False)["state"].head(5).tolist()
    policy_context = get_policy_context(top_states)

    print("\n=== Phase 3: Coordinator Synthesis ===")
    final_report = synthesize_report(econ_summary, disparity_summary, wellbeing_summary, policy_context)

    print("\n=== Phase 4: Predictive Model ===")
    training_df = build_training_frame(cost_df, disparity_df, state_distress_df)
    model, diagnostics, ols_summary = train_model(training_df)
    print(json.dumps(diagnostics, indent=2))
    print(ols_summary)

    print("\n=== Saving outputs for dashboard ===")
    cost_df.to_csv("data/cost_burden.csv", index=False)
    disparity_df.to_csv("data/disparity_scores.csv", index=False)
    distress_df.to_csv("data/distress_scores.csv", index=False)
    race_distress_df.to_csv("data/race_distress.csv", index=False)
    income_distress_df.to_csv("data/income_distress.csv", index=False)
    training_df.to_csv("data/training_frame.csv", index=False)

    with open("data/findings_report.json", "w") as f:
        json.dump({
            "economic_stress_summary": econ_summary,
            "culture_disparity_summary": disparity_summary,
            "wellbeing_summary": wellbeing_summary,
            "policy_context": policy_context,
            "coordinator_report": final_report,
            "model_diagnostics": diagnostics,
            "ols_summary": ols_summary,
            "brfss_year": BRFSS_YEAR,
        }, f, indent=2)

    print("\nDone. Outputs saved to /data. Run `streamlit run dashboard/app.py` to view.")
    return final_report, diagnostics


if __name__ == "__main__":
    run_pipeline()
