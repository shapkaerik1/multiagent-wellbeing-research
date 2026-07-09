"""
Central configuration. All keys are read from environment variables so
nothing sensitive is hardcoded.

Get your keys here (all free, instant signup):
  CENSUS_API_KEY  -> https://api.census.gov/data/key_signup.html
  BLS_API_KEY     -> https://data.bls.gov/registrationEngine/  (optional, raises rate limit)
  HUD_API_TOKEN   -> https://www.huduser.gov/hudapi/public/register  (needed for FMR/rent data)
  ANTHROPIC_API_KEY -> https://console.anthropic.com/settings/keys
  (SAMHSA/CDC BRFSS data is pulled from the CDC Socrata API, which needs no key)

Set them before running, e.g.:
  export CENSUS_API_KEY="..."
  export ANTHROPIC_API_KEY="..."

If a key is missing, each data agent below automatically falls back to a
realistic synthetic dataset (same schema) so the whole pipeline still runs
end to end. Swap in real keys any time and nothing else changes.
"""

import os

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
BLS_API_KEY = os.environ.get("BLS_API_KEY", "")
HUD_API_TOKEN = os.environ.get("HUD_API_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

USE_SYNTHETIC_FALLBACK = False  # live data on: Census, BLS, HUD, CDC keys in place

STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]

RACIAL_GROUPS = ["White", "Black", "Hispanic", "Asian", "Other/Multiracial"]

INCOME_BRACKETS = [
    "<$25k", "$25k-$50k", "$50k-$75k", "$75k-$100k", "$100k-$150k", "$150k+"
]
