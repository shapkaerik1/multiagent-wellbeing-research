"""
Predictive Model
Linear regression predicting real per-state psychological distress
(CDC BRFSS frequent mental distress prevalence) from economic cost-burden
and disparity inputs, per the proposal's Objective 3.

Two fits on the same data:
  - sklearn LinearRegression with an 80/20 train/test split for out-of-sample
    R2/RMSE (honest generalization check on only 50 states)
  - statsmodels OLS on the full frame for inference: p-values, confidence
    intervals, and residual diagnostics
"""
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# rent_to_income_ratio is deliberately excluded: cost_burden_index is built
# partly from it (0.5 * normalized rent-to-income + gas + grocery), so including
# both makes them collinear and destabilizes the rent coefficient (earlier runs
# showed a large, non-significant rent term and a ~10^6 OLS condition number).
# cost_burden_index already carries the housing-cost signal.
FEATURES = ["cost_burden_index", "disparity_score", "median_income"]
TARGET = "distress_pct"


def _normalize_state_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["state"] = df["state"].astype(str).str.strip().str.title()
    return df


def build_training_frame(cost_df: pd.DataFrame, disparity_df: pd.DataFrame,
                          state_distress_df: pd.DataFrame) -> pd.DataFrame:
    """Joins state-level cost-burden, disparity, and real per-state frequent
    mental distress prevalence (CDC BRFSS) into one training frame.
    State names are normalized before joining so source-specific casing or
    whitespace doesn't silently drop states."""
    cost_df = _normalize_state_names(cost_df)
    disparity_df = _normalize_state_names(disparity_df)
    state_distress_df = _normalize_state_names(state_distress_df)
    merged = cost_df.merge(disparity_df, on="state", how="left")
    merged = merged.merge(state_distress_df, on="state", how="left")
    return merged.dropna(subset=["cost_burden_index", "disparity_score", TARGET])


def train_model(training_df: pd.DataFrame):
    X = training_df[FEATURES].fillna(training_df.mean(numeric_only=True)).copy()
    # median_income is in dollars (tens of thousands) while the other predictors
    # are 0-1 indices; that scale gap alone inflates the OLS condition number.
    # Express it in $10k units so the coefficient is readable (distress pp per
    # $10k of median income) and the condition number reflects real structure,
    # not units.
    if "median_income" in X.columns:
        X["median_income"] = X["median_income"] / 10000.0
        X = X.rename(columns={"median_income": "median_income_10k"})
    y = training_df[TARGET]

    # out-of-sample check (sklearn, 80/20)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    # inference fit (statsmodels OLS on the full frame)
    X_sm = sm.add_constant(X)
    ols = sm.OLS(y, X_sm).fit()
    conf = ols.conf_int(alpha=0.05)
    bp_lm, bp_pvalue, _, _ = het_breuschpagan(ols.resid, X_sm)
    jb_stat, jb_pvalue, _, _ = jarque_bera(ols.resid)

    diagnostics = {
        "out_of_sample": {
            "r2_score": round(r2_score(y_test, preds), 4),
            "rmse": round(np.sqrt(mean_squared_error(y_test, preds)), 4),
            "n_train": len(X_train),
            "n_test": len(X_test),
        },
        "ols_full_sample": {
            "r2": round(ols.rsquared, 4),
            "adj_r2": round(ols.rsquared_adj, 4),
            "f_pvalue": round(float(ols.f_pvalue), 5),
            "n": int(ols.nobs),
            "coefficients": {
                name: {
                    "coef": round(float(ols.params[name]), 5),
                    "p_value": round(float(ols.pvalues[name]), 5),
                    "ci_95": [round(float(conf.loc[name, 0]), 5),
                              round(float(conf.loc[name, 1]), 5)],
                }
                for name in ols.params.index
            },
            "residual_diagnostics": {
                "durbin_watson": round(float(durbin_watson(ols.resid)), 4),
                "breusch_pagan_pvalue": round(float(bp_pvalue), 5),
                "jarque_bera_pvalue": round(float(jb_pvalue), 5),
            },
        },
        # kept for backward compatibility with the dashboard
        "r2_score": round(r2_score(y_test, preds), 4),
        "rmse": round(np.sqrt(mean_squared_error(y_test, preds)), 4),
        "coefficients": dict(zip(X.columns, model.coef_.round(5))),
        "intercept": round(model.intercept_, 5),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    return model, diagnostics, ols.summary().as_text()


if __name__ == "__main__":
    from data_pipeline.census_agent import fetch_census_data
    from data_pipeline.bls_agent import fetch_bls_data
    from data_pipeline.hud_agent import fetch_hud_data
    from data_pipeline.samhsa_agent import fetch_state_distress_data
    from agents.economic_stress_agent import compute_cost_burden_index
    from agents.culture_disparity_agent import compute_disparity_scores

    census, bls = fetch_census_data(), fetch_bls_data()
    hud = fetch_hud_data(dict(zip(census["state"], census["state_median_income"])))
    state_distress_df = fetch_state_distress_data()
    cost_df = compute_cost_burden_index(census, bls, hud)
    disparity_df = compute_disparity_scores(census)

    train_df = build_training_frame(cost_df, disparity_df, state_distress_df)
    model, diagnostics, summary_text = train_model(train_df)
    import json
    print(json.dumps(diagnostics, indent=2))
    print(summary_text)
