"""Tests for :mod:`dashboard_data.transformer`."""

from datetime import date

import polars as pl
import pytest

from dashboard_data.transformer import DashboardTransformer


def test_transform_builds_history_and_enriched_latest_options():
    """Verify dashboard transformation builds history and latest option metrics."""
    data = {
        "stocks": pl.DataFrame({"symbol": ["AAPL"], "name": ["Apple"]}),
        "stock_info": pl.DataFrame(
            {
                "stockSymbol": ["AAPL", "AAPL"],
                "itemName": ["sector", "Dividend Yield"],
                "itemValue": ['"Tech"', "0.012"],
            }
        ),
        "interest_rates": pl.DataFrame(
            {
                "ticker": ["^IRX", "^FVX"],
                "name": ["13 Week Treasury Bill", "5 Year Treasury Note"],
                "date": [date(2026, 1, 2), date(2026, 1, 2)],
                "rate": [0.04, 0.05],
            }
        ),
        "options": pl.DataFrame(
            {
                "contractSymbol": ["OLD", "NEW_SHORT", "NEW_LONG"],
                "stockSymbol": ["AAPL", "AAPL", "AAPL"],
                "lastTradeDate": [
                    date(2026, 1, 1),
                    date(2026, 1, 2),
                    date(2026, 1, 2),
                ],
                "expirationDate": [
                    date(2026, 1, 16),
                    date(2026, 1, 16),
                    date(2027, 1, 2),
                ],
                "strike": [90.0, 110.0, 120.0],
                "ask": [1.0, 2.5, 3.0],
                "volume": [10, 20, 30],
                "openInterest": [100, 200, 300],
                "contractSize": ["REGULAR", "REGULAR", "REGULAR"],
                "direction": ["CALL", "CALL", "CALL"],
            }
        ),
        "stock_prices": pl.DataFrame(
            {
                "symbol": ["AAPL"],
                "date": [date(2026, 1, 2)],
                "close": [100.0],
                "volume": [1_000],
            }
        ),
    }

    result = DashboardTransformer.transform(data)

    assert set(result) == {"stocks", "stock_info", "options_hist", "options_last", "stock_prices"}
    assert result["options_hist"].columns == [
        "contractSymbol",
        "lastTradeDate",
        "ask",
        "volume",
        "openInterest",
    ]
    latest = {
        row["contractSymbol"]: row
        for row in result["options_last"].sort("contractSymbol").to_dicts()
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
