"""Tests for :mod:`etl.transformers.historical_transformer`."""

from datetime import date

import pandas as pd
import pytest

from etl.transformers.historical_transformer import HistoricalTransformer
from etl.transformers.yfinance_frame_utils import date_value


def test_transform_returns_empty_list_for_empty_dataframe():
    """Verify empty yfinance history produces no rows."""
    assert HistoricalTransformer.transform(pd.DataFrame()) == []


def test_transform_converts_yfinance_multiindex_dataframe_to_rows():
    """Verify a single-ticker yfinance ``MultiIndex`` frame becomes one row."""
    df = pd.DataFrame(
        [[150.0, 155.0, 145.0, 148.0, 1000]],
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        columns=pd.MultiIndex.from_tuples(
            [(field, "AAPL") for field in ["Close", "High", "Low", "Open", "Volume"]],
            names=["Price", "Ticker"],
        ),
    )

    rows = HistoricalTransformer.transform(df)

    assert len(rows) == 1
    assert rows[0].date == date(2026, 1, 2)
    assert rows[0].symbol == "AAPL"
    assert rows[0].open == 148.0
    assert rows[0].high == 155.0
    assert rows[0].low == 145.0
    assert rows[0].close == 150.0
    assert rows[0].volume == 1000


def test_transform_converts_flat_single_symbol_dataframe_to_rows():
    """Verify a flat single-symbol history frame uses the supplied symbol."""
    df = pd.DataFrame(
        [[148.0, 155.0, 145.0, 150.0, 1000]],
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        columns=["Open", "High", "Low", "Close", "Volume"],
    )

    rows = HistoricalTransformer.transform(df, "AAPL")

    assert len(rows) == 1
    assert rows[0].date == date(2026, 1, 2)
    assert rows[0].symbol == "AAPL"
    assert rows[0].open == 148.0
    assert rows[0].high == 155.0
    assert rows[0].low == 145.0
    assert rows[0].close == 150.0
    assert rows[0].volume == 1000


def test_transform_drops_incomplete_history_rows():
    """Verify rows missing OHLCV values are not persisted."""
    df = pd.DataFrame(
        [
            [148.0, 155.0, 145.0, 150.0, 1000],
            [None, None, None, None, 0],
        ],
        index=pd.DatetimeIndex(["2026-01-02", "2026-01-03"], name="Date"),
        columns=["Open", "High", "Low", "Close", "Volume"],
    )

    rows = HistoricalTransformer.transform(df, "AAPL")

    assert len(rows) == 1
    assert rows[0].date == date(2026, 1, 2)
    assert rows[0].open == 148.0
    assert rows[0].high == 155.0
    assert rows[0].low == 145.0
    assert rows[0].close == 150.0
    assert rows[0].volume == 1000


def test_transform_converts_multiple_tickers_to_rows():
    """Verify a multi-ticker yfinance frame becomes one row per ticker."""
    df = pd.DataFrame(
        [[150.0, 250.0, 155.0, 255.0, 145.0, 245.0, 148.0, 248.0, 1000, 2000]],
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        columns=pd.MultiIndex.from_tuples(
            [
                ("Close", "AAPL"),
                ("Close", "MSFT"),
                ("High", "AAPL"),
                ("High", "MSFT"),
                ("Low", "AAPL"),
                ("Low", "MSFT"),
                ("Open", "AAPL"),
                ("Open", "MSFT"),
                ("Volume", "AAPL"),
                ("Volume", "MSFT"),
            ],
            names=["Price", "Ticker"],
        ),
    )

    rows = HistoricalTransformer.transform(df)

    assert [row.symbol for row in rows] == ["AAPL", "MSFT"]
    assert [row.close for row in rows] == [150.0, 250.0]
    assert [row.volume for row in rows] == [1000, 2000]


def test_transform_selects_columns_by_name_when_reordered_with_extra_columns():
    """Verify OHLCV values are selected by name, not column position."""
    df = pd.DataFrame(
        [[1.23, 1000, 148.0, 145.0, 150.0, 155.0]],
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        columns=pd.MultiIndex.from_tuples(
            [
                ("Dividends", "AAPL"),
                ("Volume", "AAPL"),
                ("Open", "AAPL"),
                ("Low", "AAPL"),
                ("Close", "AAPL"),
                ("High", "AAPL"),
            ],
            names=["Price", "Ticker"],
        ),
    )

    rows = HistoricalTransformer.transform(df)

    assert len(rows) == 1
    assert rows[0].open == 148.0
    assert rows[0].high == 155.0
    assert rows[0].low == 145.0
    assert rows[0].close == 150.0
    assert rows[0].volume == 1000


def test_transform_requires_symbol_for_flat_dataframe():
    """Verify flat history frames fail clearly without a ticker symbol."""
    df = pd.DataFrame(
        [[148.0, 155.0, 145.0, 150.0, 1000]],
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        columns=["Open", "High", "Low", "Close", "Volume"],
    )

    with pytest.raises(ValueError, match="symbol is required"):
        HistoricalTransformer.transform(df)


def test_transform_reports_missing_required_columns():
    """Verify malformed history frames report missing OHLCV fields."""
    df = pd.DataFrame(
        [[148.0, 155.0, 150.0, 1000]],
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        columns=["Open", "High", "Close", "Volume"],
    )

    with pytest.raises(ValueError, match="Low"):
        HistoricalTransformer.transform(df, "AAPL")


def test_date_value_converts_iso_string():
    """Verify ISO date strings are converted to ``date`` values."""
    assert date_value("2026-01-02") == date(2026, 1, 2)
