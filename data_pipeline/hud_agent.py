"""
HUD Connector
Pulls: Fair Market Rent and rent-to-income ratio by state
Source: HUD USER API (Fair Market Rents)
Docs: https://www.huduser.gov/portal/dataset/fmr-api.html
"""
import time
import random
import requests
import pandas as pd
from config import HUD_API_TOKEN, STATES, USE_SYNTHETIC_FALLBACK

HUD_STATE_URL = "https://www.huduser.gov/hudapi/public/fmr/statedata/{state_code}"

# HUD's API requires 2-letter USPS state codes, not full names
STATE_TO_USPS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def fetch_hud_data(median_income_by_state: dict | None = None) -> pd.DataFrame:
    """Returns DataFrame: state, fair_market_rent, rent_to_income_ratio"""
    if HUD_API_TOKEN and not USE_SYNTHETIC_FALLBACK:
        return _fetch_real(median_income_by_state or {})
    return _fetch_synthetic(median_income_by_state or {})


def _fetch_state_2br_rent(state_code: str, headers: dict, retries: int = 3) -> float | None:
    """One state's average 2BR Fair Market Rent, with retry/backoff. Fetching
    all 50 states back-to-back occasionally drops a request (transient timeout /
    reset); without a retry those states silently become NaN and get dropped
    from the regression, so retry before giving up."""
    for attempt in range(retries):
        try:
            resp = requests.get(HUD_STATE_URL.format(state_code=state_code),
                                headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            # statedata returns separate county/metro-area arrays (no single
            # "basicdata" statewide row) -- average their 2BR FMRs.
            areas = data.get("counties", []) + data.get("metroareas", [])
            rents = [float(a["Two-Bedroom"]) for a in areas if a.get("Two-Bedroom") not in (None, "")]
            if rents:
                return sum(rents) / len(rents)
            return None
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))  # linear backoff: 1.5s, 3s
    return None


def _fetch_real(median_income_by_state: dict) -> pd.DataFrame:
    headers = {"Authorization": f"Bearer {HUD_API_TOKEN}"}
    rows = []
    for state in STATES:
        state_code = STATE_TO_USPS.get(state)
        avg_2br_rent = _fetch_state_2br_rent(state_code, headers)
        income = median_income_by_state.get(state, 65000)
        ratio = (avg_2br_rent * 12 / income) if avg_2br_rent and income else None
        rows.append({
            "state": state,
            "fair_market_rent": round(avg_2br_rent, 2) if avg_2br_rent else None,
            "rent_to_income_ratio": round(ratio, 3) if ratio else None,
        })
    return pd.DataFrame(rows)


def _fetch_synthetic(median_income_by_state: dict) -> pd.DataFrame:
    random.seed(11)
    rows = []
    for state in STATES:
        rent = round(random.uniform(900, 2600), 0)
        income = median_income_by_state.get(state, random.randint(48000, 92000))
        ratio = round((rent * 12) / income, 3)
        rows.append({"state": state, "fair_market_rent": rent, "rent_to_income_ratio": ratio})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(fetch_hud_data().head())
