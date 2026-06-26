"""Tests for :mod:`etl.transformers.options_transformer`."""

from datetime import date

import pandas as pd
import pytest

from etl.transformers.options_transformer import OptionsTransformer
from schemas.option_contract import OptionDirection


def option_row(symbol, trade_date):
    """Return a minimal yfinance-like option-chain row.

    :param symbol: Option contract symbol.
    :param trade_date: Last trade date value.
    :returns: Dictionary suitable for a pandas DataFrame row.
    """
    return {
        "contractSymbol": symbol,
        "lastTradeDate": pd.Timestamp(trade_date),
        "strike": 100.0,
        "volume": 10,
        "openInterest": 20,
        "bid": 1.1,
        "ask": 1.2,
    }


def test_transform_converts_calls_and_puts():
    """Verify call and put rows are mapped to option contracts."""
    calls = pd.DataFrame([option_row("AAPL260116C00100000", "2026-01-02")])
    puts = pd.DataFrame([option_row("AAPL260116P00100000", "2026-01-02")])

    rows = OptionsTransformer.transform("AAPL", "2026-01-16", calls, puts)

    assert [row.direction for row in rows] == [OptionDirection.CALL, OptionDirection.PUT]
    assert rows[0].contractSymbol == "AAPL260116C00100000"
    assert rows[0].stockSymbol == "AAPL"
    assert rows[0].expirationDate == date(2026, 1, 16)
    assert rows[0].lastTradeDate == date(2026, 1, 2)
    assert rows[0].volume == 10
    assert rows[0].openInterest == 20
    assert rows[0].bid == 1.1
    assert rows[0].ask == 1.2
    assert rows[1].contractSymbol == "AAPL260116P00100000"
    assert rows[1].stockSymbol == "AAPL"
    assert rows[1].expirationDate == date(2026, 1, 16)
    assert rows[1].lastTradeDate == date(2026, 1, 2)
    assert rows[1].strike == 100.0
    assert rows[1].volume == 10
    assert rows[1].openInterest == 20
    assert rows[1].bid == 1.1
    assert rows[1].ask == 1.2


def test_transform_returns_puts_when_calls_are_empty():
    """Verify public transform handles empty calls with non-empty puts."""
    calls = pd.DataFrame()
    puts = pd.DataFrame([option_row("AAPL260116P00100000", "2026-01-02")])

    rows = OptionsTransformer.transform("AAPL", "2026-01-16", calls, puts)

    assert len(rows) == 1
    assert rows[0].direction == OptionDirection.PUT


def test_transform_returns_calls_when_puts_are_empty():
    """Verify public transform handles non-empty calls with empty puts."""
    calls = pd.DataFrame([option_row("AAPL260116C00100000", "2026-01-02")])
    puts = pd.DataFrame()

    rows = OptionsTransformer.transform("AAPL", "2026-01-16", calls, puts)

    assert len(rows) == 1
    assert rows[0].direction == OptionDirection.CALL


def test_transform_returns_empty_list_when_both_sides_are_empty():
    """Verify public transform handles empty call and put DataFrames."""
    rows = OptionsTransformer.transform(
        "AAPL",
        "2026-01-16",
        pd.DataFrame(),
        pd.DataFrame(),
    )

    assert rows == []


def test_transform_maps_optional_quote_fields_when_present():
    """Verify optional yfinance fields are preserved when present."""
    row = option_row("AAPL260116C00100000", "2026-01-02")
    row.update(
        {
            "lastPrice": 1.25,
            "change": -0.05,
            "percentChange": -3.85,
            "impliedVolatility": 0.42,
            "inTheMoney": True,
            "contractSize": "REGULAR",
            "currency": "USD",
        }
    )

    rows = OptionsTransformer.transform(
        "AAPL",
        "2026-01-16",
        pd.DataFrame([row]),
        pd.DataFrame(),
    )

    assert rows[0].lastPrice == 1.25
    assert rows[0].change == -0.05
    assert rows[0].percentChange == -3.85
    assert rows[0].impliedVolatility == 0.42
    assert rows[0].inTheMoney is True
    assert rows[0].contractSize == "REGULAR"
    assert rows[0].currency == "USD"


def test_transform_converts_missing_optional_values_to_none():
    """Verify pandas missing values do not leak into optional model fields."""
    row = option_row("AAPL260116C00100000", "2026-01-02")
    row.update(
        {
            "volume": pd.NA,
            "openInterest": pd.NA,
            "bid": float("nan"),
            "lastPrice": pd.NA,
            "change": float("nan"),
            "percentChange": pd.NA,
            "impliedVolatility": float("nan"),
            "inTheMoney": pd.NA,
            "contractSize": pd.NA,
            "currency": pd.NA,
        }
    )

    rows = OptionsTransformer.transform(
        "AAPL",
        "2026-01-16",
        pd.DataFrame([row]),
        pd.DataFrame(),
    )

    assert rows[0].volume is None
    assert rows[0].openInterest is None
    assert rows[0].bid is None
    assert rows[0].lastPrice is None
    assert rows[0].change is None
    assert rows[0].percentChange is None
    assert rows[0].impliedVolatility is None
    assert rows[0].inTheMoney is None
    assert rows[0].contractSize is None
    assert rows[0].currency is None


def test_transform_raises_when_required_ask_is_missing():
    """Verify missing ask prices fail before schema insertion."""
    row = option_row("AAPL260116C00100000", "2026-01-02")
    row["ask"] = float("nan")

    with pytest.raises(ValueError, match="float value is required"):
        OptionsTransformer.transform(
            "AAPL",
            "2026-01-16",
            pd.DataFrame([row]),
            pd.DataFrame(),
        )


def test_transform_raises_when_required_ask_column_is_absent():
    """Verify option-chain rows must include the ask column."""
    row = option_row("AAPL260116C00100000", "2026-01-02")
    del row["ask"]

    with pytest.raises(ValueError, match="float value is required"):
        OptionsTransformer.transform(
            "AAPL",
            "2026-01-16",
            pd.DataFrame([row]),
            pd.DataFrame(),
        )


def test_convert_df_returns_empty_list_for_empty_dataframe():
    """Verify a single empty option-chain side produces no rows."""
    assert OptionsTransformer._convert_df(
        pd.DataFrame(),
        "AAPL",
        "2026-01-16",
        OptionDirection.CALL,
    ) == []
