"""Configuration for Treasury yield inputs."""

INTEREST_RATES = {
    "^IRX": "13 Week Treasury Bill",
    "^FVX": "5 Year Treasury Note",
}

INTEREST_RATE_TICKERS = tuple(INTEREST_RATES)
