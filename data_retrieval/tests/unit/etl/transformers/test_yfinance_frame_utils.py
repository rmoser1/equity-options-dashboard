"""Tests for :mod:`etl.transformers.yfinance_frame_utils`."""

from datetime import date, datetime

import pandas as pd
import pytest

from etl.transformers.yfinance_frame_utils import (
    date_value,
    normalize_download_rows,
    optional_float,
    optional_int,
    required_float,
)


def test_normalize_download_rows_stacks_multiindex_ticker_columns():
    """Verify yfinance download frames become Date/Ticker rows."""
    df = pd.DataFrame(
        [[150.0, 250.0]],
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        columns=pd.MultiIndex.from_tuples(
            [("Close", "AAPL"), ("Close", "MSFT")],
            names=["Price", "Ticker"],
        ),
    )

    result = normalize_download_rows(df, required_columns=("Close",))

    assert result.to_dict("records") == [
        {"Date": pd.Timestamp("2026-01-02"), "Ticker": "AAPL", "Close": 150.0},
        {"Date": pd.Timestamp("2026-01-02"), "Ticker": "MSFT", "Close": 250.0},
    ]


def test_normalize_download_rows_uses_symbol_for_flat_frames():
    """Verify flat single-symbol frames receive the supplied ticker."""
    df = pd.DataFrame(
        [[150.0]],
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
        columns=["Close"],
    )

    result = normalize_download_rows(df, required_columns=("Close",), symbol="AAPL")

    assert result.to_dict("records") == [
        {"Date": pd.Timestamp("2026-01-02"), "Ticker": "AAPL", "Close": 150.0}
    ]


def test_normalize_download_rows_requires_symbol_for_flat_frames():
    """Verify flat frames fail clearly without a symbol."""
    df = pd.DataFrame({"Close": [150.0]})

    with pytest.raises(ValueError, match="symbol is required"):
        normalize_download_rows(df, required_columns=("Close",))


def test_normalize_download_rows_reports_missing_columns():
    """Verify malformed frames report missing columns."""
    df = pd.DataFrame({"Close": [150.0]})

    with pytest.raises(ValueError, match="yfinance download DataFrame missing columns"):
        normalize_download_rows(
            df,
            required_columns=("Close", "Volume"),
            symbol="AAPL",
        )


def test_date_value_accepts_supported_date_like_values():
    """Verify date conversion handles common yfinance date shapes."""
    assert date_value(pd.Timestamp("2026-01-02 15:30:00")) == date(2026, 1, 2)
    assert date_value(datetime(2026, 1, 2, 15, 30)) == date(2026, 1, 2)
    assert date_value(date(2026, 1, 2)) == date(2026, 1, 2)
    assert date_value("2026-01-02 15:30:00") == date(2026, 1, 2)


def test_date_value_raises_for_required_missing_values():
    """Verify required missing dates fail clearly."""
    with pytest.raises(ValueError, match="date is required"):
        date_value(pd.NA, required=True)


def test_date_value_raises_for_required_invalid_values():
    """Verify required non-date values fail clearly."""
    with pytest.raises(ValueError, match="date value cannot be converted"):
        date_value(123, required=True)


def test_optional_converters_preserve_none():
    """Verify optional numeric converters handle missing and present values."""
    assert optional_float(None) is None
    assert optional_int(None) is None
    assert optional_float(float("nan")) is None
    assert optional_int(pd.NA) is None
    assert optional_float(1) == 1.0
    assert optional_int(1.9) == 1


def test_required_float_rejects_missing_values():
    """Verify required floats fail when provider values are missing."""
    with pytest.raises(ValueError, match="float value is required"):
        required_float(pd.NA)


def test_required_float_converts_present_values():
    """Verify required floats convert numeric values."""
    assert required_float(1) == 1.0
