"""Tests for :mod:`etl.config.interest_rates`."""

from etl.config.interest_rates import INTEREST_RATE_TICKERS, INTEREST_RATES


def test_interest_rate_tickers_match_configured_rate_names():
    """Ensure ticker iteration is derived from the shared rate config."""
    assert INTEREST_RATE_TICKERS == tuple(INTEREST_RATES)
