"""Tests for :mod:`dashboard_data.transformer`."""

from datetime import date

import polars as pl
import pytest

from dashboard_data.info_item_fields import (
    FIELDS_DATE,
    FIELDS_NUMERIC,
    FIELDS_STRING,
    INFO_ITEM_NAMES,
)
from dashboard_data.transformer import DashboardTransformer


def test_info_item_fields_are_unique_and_typed():
    """Keep every configured stock-info item uniquely classified."""
    assert len(INFO_ITEM_NAMES) == len(set(INFO_ITEM_NAMES))
    assert set(INFO_ITEM_NAMES) == set(FIELDS_NUMERIC + FIELDS_DATE + FIELDS_STRING)


def test_transform_info_items_filters_and_formats():
    """Prepare only configured stock-info values for dashboard display."""
    stock_info = pl.DataFrame(
        {
            "stockSymbol": ["SPY"] * 6,
            "itemName": [
                "longName",
                "marketCap",
                "lastFiscalYearEnd",
                "fiftyTwoWeekRange",
                "lastSplitFactor",
                "website",
            ],
            "itemValue": [
                '"SPDR S&P 500 ETF Trust"',
                "1000000",
                "1784246400",
                '"108.35 - 160.27"',
                '"3:2"',
                '"https://example.com"',
            ],
        }
    )

    result = DashboardTransformer.transform_info_items(stock_info)

    assert result.select("itemName", "itemValue", "itemCategory").to_dicts() == [
        {
            "itemName": "longName",
            "itemValue": "SPDR S&P 500 ETF Trust",
            "itemCategory": "company_profile",
        },
        {
            "itemName": "marketCap",
            "itemValue": "1,000,000",
            "itemCategory": "valuation",
        },
        {
            "itemName": "lastFiscalYearEnd",
            "itemValue": "2026-07-17",
            "itemCategory": "dividends_corporate_events",
        },
        {
            "itemName": "fiftyTwoWeekRange",
            "itemValue": "108.35 - 160.27",
            "itemCategory": "market_data",
        },
        {
            "itemName": "lastSplitFactor",
            "itemValue": "3:2",
            "itemCategory": "dividends_corporate_events",
        },
    ]


def test_transform_info_items_preserves_null_values():
    """Keep unavailable configured values from aborting the dashboard export."""
    stock_info = pl.DataFrame(
        {
            "stockSymbol": ["SPY", "SPY"],
            "itemName": ["marketCap", "lastFiscalYearEnd"],
            "itemValue": ["null", "null"],
        }
    )

    result = DashboardTransformer.transform_info_items(stock_info)

    assert result.get_column("itemValue").to_list() == [None, None]


def test_transform_info_items_handles_empty_input():
    """Return a typed empty export when no configured values exist."""
    stock_info = pl.DataFrame(
        schema={
            "stockSymbol": pl.String,
            "itemName": pl.String,
            "itemValue": pl.String,
        }
    )

    result = DashboardTransformer.transform_info_items(stock_info)

    assert result.is_empty()
    assert result.schema == {
        **stock_info.schema,
        "itemCategory": pl.String,
    }


def test_transform_options_last_enriches_latest_options():
    """Verify latest option rows are enriched with dashboard metrics."""
    stock_info = pl.DataFrame(
        {
            "stockSymbol": ["AAPL", "AAPL"],
            "itemName": ["sector", "Dividend Yield"],
            "itemValue": ['"Tech"', "0.98"],
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
            "contractSymbol": ["NEW_SHORT", "NEW_LONG", "NO_STOCK_PRICE"],
            "stockSymbol": ["AAPL", "AAPL", "MSFT"],
            "lastTradeDate": [date(2026, 1, 2)] * 3,
            "expirationDate": [
                date(2026, 1, 16),
                date(2027, 1, 2),
                date(2026, 1, 16),
            ],
            "strike": [110.0, 120.0, 100.0],
            "ask": [2.5, 3.0, 1.0],
            "volume": [20, 30, 10],
            "openInterest": [200, 300, 100],
            "contractSize": ["REGULAR"] * 3,
            "direction": ["CALL"] * 3,
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
    assert set(latest) == {"NEW_SHORT", "NEW_LONG"}
    short_option = latest["NEW_SHORT"]
    long_option = latest["NEW_LONG"]
    assert short_option["lastStockPrice"] == 100.0
    assert short_option["timeToExpiryYears"] == round(14 / 365, 6)
    assert short_option["riskFreeRate"] == 0.04
    assert short_option["dividendYield"] == 0.0098
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
