"""Tests for :mod:`dashboard_data.transformer`."""

from datetime import date

import polars as pl
import pytest

from dashboard_data.transformer import DashboardTransformer


def test_transform_options_last_enriches_latest_options():
    """Verify latest option rows are enriched with dashboard metrics."""
    stock_info = pl.DataFrame(
        {
            "stockSymbol": ["AAPL", "AAPL"],
            "itemName": ["sector", "Dividend Yield"],
            "itemValue": ['"Tech"', "0.012"],
        }
    )
    interest_rates = pl.DataFrame(
        {
            "ticker": ["^IRX", "^FVX"],
            "name": ["13 Week Treasury Bill", "5 Year Treasury Note"],
            "date": [date(2026, 1, 2), date(2026, 1, 2)],
            "rate": [0.04, 0.05],
        }
    )
    options = pl.DataFrame(
        {
            "contractSymbol": ["NEW_SHORT", "NEW_LONG"],
            "stockSymbol": ["AAPL", "AAPL"],
            "lastTradeDate": [date(2026, 1, 2), date(2026, 1, 2)],
            "expirationDate": [date(2026, 1, 16), date(2027, 1, 2)],
            "strike": [110.0, 120.0],
            "ask": [2.5, 3.0],
            "volume": [20, 30],
            "openInterest": [200, 300],
            "contractSize": ["REGULAR", "REGULAR"],
            "direction": ["CALL", "CALL"],
        }
    )
    last_stock_price = pl.DataFrame({"symbol": ["AAPL"], "lastStockPrice": [100.0]})

    result = DashboardTransformer.transform_options_last(
        options=options,
        last_stock_price=last_stock_price,
        stock_info=stock_info,
        interest_rates=interest_rates,
    )

    latest = {
        row["contractSymbol"]: row
        for row in result.sort("contractSymbol").to_dicts()
    }
    short_option = latest["NEW_SHORT"]
    long_option = latest["NEW_LONG"]
    assert short_option["lastStockPrice"] == 100.0
    assert short_option["timeToExpiryYears"] == round(14 / 365, 6)
    assert short_option["riskFreeRate"] == 0.04
    assert short_option["dividendYield"] == 0.012
    assert short_option["relativeStrikePrice"] == 1.1
    assert short_option["relativeOptionPrice"] == 0.025
    assert short_option["costPerContract"] == 250.0
    assert short_option["nominalPerContract"] == 10000.0
    assert long_option["timeToExpiryYears"] == 1.0
    assert long_option["riskFreeRate"] == 0.041579


def test_risk_free_rate_expr_requires_short_rate():
    """Verify risk-free-rate interpolation requires the 13-week anchor."""
    interest_rates = pl.DataFrame(
        {
            "ticker": ["^FVX"],
            "name": ["5 Year Treasury Note"],
            "date": [date(2026, 1, 2)],
            "rate": [0.05],
        }
    )

    with pytest.raises(ValueError, match=r"\^IRX"):
        DashboardTransformer._risk_free_rate_expr(
            interest_rates,
            pl.col("timeToExpiryYears"),
        )


def test_risk_free_rate_expr_requires_long_rate():
    """Verify risk-free-rate interpolation requires the 5-year anchor."""
    interest_rates = pl.DataFrame(
        {
            "ticker": ["^IRX"],
            "name": ["13 Week Treasury Bill"],
            "date": [date(2026, 1, 2)],
            "rate": [0.04],
        }
    )

    with pytest.raises(ValueError, match=r"\^FVX"):
        DashboardTransformer._risk_free_rate_expr(
            interest_rates,
            pl.col("timeToExpiryYears"),
        )
