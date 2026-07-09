"""
Bureau of Labor Statistics Connector
Pulls: gas prices (fuel CPI) and grocery CPI by Census region
Source: BLS Public Data API v2
Docs: https://www.bls.gov/developers/
"""
import random
import requests
import pandas as pd
from config import BLS_API_KEY, USE_SYNTHETIC_FALLBACK

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# CPI series IDs for regional gasoline and food-at-home indices
SERIES_IDS = {
    "Northeast": {"gas": "CUUR0100SETB01", "grocery": "CUUR0100SAF11"},
    "Midwest": {"gas": "CUUR0200SETB01", "grocery": "CUUR0200SAF11"},
    "South": {"gas": "CUUR0300SETB01", "grocery": "CUUR0300SAF11"},
    "West": {"gas": "CUUR0400SETB01", "grocery": "CUUR0400SAF11"},
}


def fetch_bls_data() -> pd.DataFrame:
    """Returns DataFrame: region, gas_cpi, grocery_cpi"""
    if not USE_SYNTHETIC_FALLBACK:
        return _fetch_real()
    return _fetch_synthetic()


def _fetch_real() -> pd.DataFrame:
    all_series = [sid for pair in SERIES_IDS.values() for sid in pair.values()]
    payload = {"seriesid": all_series, "startyear": "2024", "endyear": "2025"}
    if BLS_API_KEY:
        payload["registrationkey"] = BLS_API_KEY
    resp = requests.post(BLS_URL, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()["Results"]["series"]
    latest = {s["seriesID"]: float(s["data"][0]["value"]) for s in result if s["data"]}

    rows = []
    for region, ids in SERIES_IDS.items():
        rows.append({
            "region": region,
            "gas_cpi": latest.get(ids["gas"]),
            "grocery_cpi": latest.get(ids["grocery"]),
        })
    return pd.DataFrame(rows)


def _fetch_synthetic() -> pd.DataFrame:
    random.seed(7)
    rows = []
    for region in SERIES_IDS:
        rows.append({
            "region": region,
            "gas_cpi": round(random.uniform(280, 340), 1),
            "grocery_cpi": round(random.uniform(290, 350), 1),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(fetch_bls_data())
