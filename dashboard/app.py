"""
Interactive Research Dashboard
Run with: streamlit run dashboard/app.py
Visualizes cost burden, disparity, and predicted distress by state.
"""
import json
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Economic Precarity & Wellbeing Dashboard", layout="wide")
st.title("Economic Precarity, Cultural Disparity & Psychological Wellbeing")
st.caption("Multi-Agent AI Research System — U.S. State-Level Findings")

cost_df = pd.read_csv("data/cost_burden.csv")
disparity_df = pd.read_csv("data/disparity_scores.csv")
training_df = pd.read_csv("data/training_frame.csv")
try:
    race_distress_df = pd.read_csv("data/race_distress.csv")
except FileNotFoundError:
    race_distress_df = None
try:
    income_distress_df = pd.read_csv("data/income_distress.csv")
except FileNotFoundError:
    income_distress_df = None

# HUD/USPS 2-letter codes -- Plotly's USA-states locationmode needs these,
# not full state names.
STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
for _df in (cost_df, disparity_df, training_df):
    if "state" in _df.columns:
        _df["state_code"] = _df["state"].map(STATE_ABBR)
if race_distress_df is not None:
    race_distress_df["state_code"] = race_distress_df["state"].map(STATE_ABBR)
if income_distress_df is not None:
    income_distress_df["state_code"] = income_distress_df["state"].map(STATE_ABBR)

with open("data/findings_report.json") as f:
    report = json.load(f)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Cost Burden Map", "Disparity Map", "Distress by Income", "Distress by Race",
     "Model Results", "Agent Findings"])

with tab1:
    st.subheader("Cost-Burden Index by State")
    fig = px.choropleth(cost_df, locations="state_code", locationmode="USA-states",
                         color="cost_burden_index", scope="usa",
                         color_continuous_scale="Reds", hover_name="state",
                         hover_data=["median_income", "rent_to_income_ratio", "gas_cpi", "grocery_cpi"])
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Racial/Ethnic Income Disparity Score by State")
    fig2 = px.choropleth(disparity_df, locations="state_code", locationmode="USA-states",
                          color="disparity_score", scope="usa",
                          color_continuous_scale="Purples", hover_name="state",
                          hover_data=["lowest_income_group", "highest_income_group"])
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("Frequent Mental Distress by Household Income Bracket")
    if income_distress_df is None:
        st.warning("Run `python main.py` to generate data/income_distress.csv.")
    else:
        brackets = ["<$25k", "$25k-$50k", "$50k-$75k", "$75k-$100k", "$100k-$150k", "$150k+"]
        brackets = [b for b in brackets if b in set(income_distress_df["income_bracket"])]
        sel_b = st.selectbox("Household income bracket", brackets,
                             index=0)
        sub_i = income_distress_df[income_distress_df["income_bracket"] == sel_b]
        fig_i = px.choropleth(sub_i, locations="state_code", locationmode="USA-states",
                              color="distress_pct", scope="usa",
                              color_continuous_scale="Reds", hover_name="state",
                              range_color=[income_distress_df["distress_pct"].min(),
                                           income_distress_df["distress_pct"].max()],
                              labels={"distress_pct": "Distress %"})
        st.plotly_chart(fig_i, use_container_width=True)
        st.caption(f"Frequent mental distress (14+ bad mental-health days/month), "
                   f"residents in the {sel_b} household-income bracket. Real CDC BRFSS "
                   f"state × income data.")

        st.markdown("**National distress gradient across income brackets**")
        grad = (income_distress_df.groupby("income_bracket")["distress_pct"].mean()
                .reindex(brackets).round(2).reset_index()
                .rename(columns={"distress_pct": "avg_state_distress_pct"}))
        st.bar_chart(grad, x="income_bracket", y="avg_state_distress_pct")

with tab4:
    st.subheader("Frequent Mental Distress by Race/Ethnicity")
    if race_distress_df is None:
        st.warning("Run `python main.py` to generate data/race_distress.csv.")
    else:
        groups = sorted(race_distress_df["race_group"].unique())
        sel = st.selectbox("Race/ethnicity group", groups,
                           index=groups.index("Black") if "Black" in groups else 0)
        sub = race_distress_df[race_distress_df["race_group"] == sel]
        fig_r = px.choropleth(sub, locations="state_code", locationmode="USA-states",
                              color="distress_pct", scope="usa",
                              color_continuous_scale="Oranges", hover_name="state",
                              range_color=[race_distress_df["distress_pct"].min(),
                                           race_distress_df["distress_pct"].max()],
                              labels={"distress_pct": "Distress %"})
        st.plotly_chart(fig_r, use_container_width=True)
        st.caption(f"Frequent mental distress (14+ bad mental-health days/month), "
                   f"{sel} residents, {report.get('brfss_year', 'latest')} BRFSS.")

        st.markdown("**Within-state distress gap across race/ethnicity groups**")
        pivot = (race_distress_df.groupby("state")["distress_pct"]
                 .agg(["min", "max"]).eval("gap = max - min")
                 .sort_values("gap", ascending=False).round(2).reset_index())
        st.dataframe(pivot.head(10), use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Linear Regression Diagnostics")
    diag = report["model_diagnostics"]
    ols = diag.get("ols_full_sample", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Out-of-sample R²", diag["r2_score"])
    col2.metric("RMSE", diag["rmse"])
    col3.metric("Full-sample OLS R²", ols.get("r2", "—"))
    col4.metric("Model F-test p-value", ols.get("f_pvalue", "—"))

    if ols.get("coefficients"):
        st.write("**OLS coefficients (full sample, with inference)**")
        coef_rows = [
            {"term": name, "coef": c["coef"], "p_value": c["p_value"],
             "ci_low": c["ci_95"][0], "ci_high": c["ci_95"][1]}
            for name, c in ols["coefficients"].items()
        ]
        st.dataframe(pd.DataFrame(coef_rows), use_container_width=True, hide_index=True)
        st.write("**Residual diagnostics**")
        st.json(ols["residual_diagnostics"])
    else:
        st.write("**Coefficients**")
        st.json(diag["coefficients"])

    if report.get("ols_summary"):
        with st.expander("Full statsmodels OLS summary"):
            st.code(report["ols_summary"])

    fig3 = px.scatter(training_df, x="cost_burden_index", y="distress_pct",
                       color="disparity_score", size="median_income",
                       hover_name="state", title="Cost Burden vs. Frequent Mental Distress (%)")
    st.plotly_chart(fig3, use_container_width=True)

with tab6:
    st.subheader("Agent-Generated Findings")
    st.markdown("**Economic Stress Agent**")
    st.info(report["economic_stress_summary"])
    st.markdown("**Culture Disparity Agent**")
    st.info(report["culture_disparity_summary"])
    st.markdown("**Wellbeing Agent**")
    st.info(report["wellbeing_summary"])
    st.markdown("**Web Search Agent (Policy Context)**")
    st.info(report["policy_context"])
    st.markdown("**Coordinator Agent — Unified Report**")
    st.success(report["coordinator_report"])

st.caption("Data sources: U.S. Census ACS, BLS CPI, HUD Fair Market Rents, CDC BRFSS/SAMHSA. "
           "Synthetic fallback data used where live API keys are not configured — see config.py.")
