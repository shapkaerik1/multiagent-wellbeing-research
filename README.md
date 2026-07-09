# Economic Precarity, Cultural Disparity & Psychological Wellbeing
### Multi-Agent AI Research System — Working Prototype (Phases 1–4)

This is a runnable implementation of the proposal: a 4-agent pipeline (+ coordinator)
that pulls public economic/demographic/health data, computes cost-burden and disparity
indices, trains a regression model predicting a distress proxy, and renders results in
an interactive Streamlit dashboard.

## Status
- **Phase 1 (data infrastructure): done.** All 4 connectors (Census, BLS, HUD, SAMHSA/CDC)
  are implemented with real API code paths.
- **Phase 2 (agents): done.** 4 specialized agents + coordinator, powered by the Claude API.
- **Phase 3 (regression model): done and validated.** 80/20 split, R² and RMSE reported.
- **Phase 4 (dashboard): done.** Choropleth maps + model diagnostics + agent findings, all in Streamlit.

## Status: running on LIVE data
As of the latest run, `USE_SYNTHETIC_FALLBACK = False` and all connectors hit their real
endpoints: Census ACS 2023, BLS CPI v2, HUD FMR 2026, and CDC BRFSS. All four Claude
agents + the coordinator run live via the Anthropic API (real prose, not placeholders).
See **RESULTS.md** for the model numbers and an honest assessment of the fit.

Each connector still keeps a `_fetch_synthetic()` fallback with the same schema, so the
pipeline degrades gracefully if a key is missing or an endpoint is down — but that path
is **off** in the current configuration.

**To reproduce the live run** you need four keys (all free):
1. Census: https://api.census.gov/data/key_signup.html
2. BLS (optional, raises rate limit): https://data.bls.gov/registrationEngine/
3. HUD: https://www.huduser.gov/hudapi/public/register
4. Anthropic: https://console.anthropic.com/settings/keys

```bash
export CENSUS_API_KEY=... BLS_API_KEY=... HUD_API_TOKEN=... ANTHROPIC_API_KEY=...
python main.py
```

To fall back to synthetic data (no keys, offline demo), set `USE_SYNTHETIC_FALLBACK = True`
in `config.py`.

## Run it
```bash
pip install -r requirements.txt
python main.py                        # runs full pipeline, writes results to /data
streamlit run dashboard/app.py        # opens interactive dashboard
```

## Structure
```
config.py                    # API keys + constants (states, income brackets, etc.)
data_pipeline/
  census_agent.py            # ACS income + race/ethnicity by state
  bls_agent.py                # gas + grocery CPI by region
  hud_agent.py                 # Fair Market Rent + rent-to-income ratio by state
  samhsa_agent.py               # CDC BRFSS mental distress by income bracket
agents/
  claude_client.py            # shared Claude API wrapper (+ web search variant)
  economic_stress_agent.py    # cost-burden index + Claude interpretation
  culture_disparity_agent.py  # income disparity scores across racial groups
  wellbeing_agent.py          # distress proxy scores
  web_search_agent.py         # live policy/news context via Claude web search
  coordinator_agent.py        # synthesizes all 4 into one findings report
model/
  regression_model.py         # sklearn 80/20 split + statsmodels OLS (p-values, CIs, residual diagnostics)
dashboard/
  app.py                      # Streamlit: cost-burden map, disparity map, distress-by-income map (filterable),
                              #   distress-by-race map (filterable), model diagnostics tab, agent findings tab
data/                         # pipeline outputs (CSVs + findings_report.json)
RESULTS.md                    # headline model numbers + honest fit assessment + limitations
```

## Known limitations (worth noting in your submission)
See **RESULTS.md** for the full write-up. The honest headline: the model explains ~33% of
state distress variance (F-test p ≈ 4×10⁻⁴), driven mainly by median income; cost burden is
not individually significant once income is in the model — a finding worth reporting, and a
motivation for a county-level extension where cost-burden variation is larger. Remaining
caveats:
- Small N (50 states) makes any single train/test holdout unstable; cross-validation or a
  county-level dataset would firm up the out-of-sample estimate.
- Race groups pool BRFSS's AIAN / NHPI / Multiracial / Other into "Other/Multiracial" to
  match the Census-side grouping; the smaller groups carry wider BRFSS CIs.
- CDC publishes a single $50k–$99,999 income bucket, so the $50–75k and $75–100k brackets
  share the same distress value (documented in `samhsa_agent._BRACKET_MAP`).

These are the kind of "close but needs refinement" details worth flagging to your advisor
as next steps.
