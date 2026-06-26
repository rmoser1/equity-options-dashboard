"""Shared helpers for yfinance DataFrame transformers."""

from datetime import date, datetime

import pandas as pd


def normalize_download_rows(
    df: pd.DataFrame,
    required_columns: tuple[str, ...],
    symbol: str | None = None,
) -> pd.DataFrame:
    """Return rows with Date, Ticker, and selected provider columns.

    :param df: Raw yfinance download DataFrame.
    :param required_columns: Provider columns that must be present.
    :param symbol: Ticker symbol for flat single-symbol DataFrames.
    :returns: DataFrame with Date, Ticker, and required columns.
    :raises ValueError: If a flat DataFrame has no symbol or required columns are missing.
    """
    if isinstance(df.columns, pd.MultiIndex):
        df = _stack_ticker_columns(df)
    else:
        if symbol is None:
            raise ValueError("symbol is required for flat yfinance download DataFrames")
        df = df.reset_index()
        df["Ticker"] = symbol

    output_columns = ("Date", "Ticker", *required_columns)
    missing_columns = [column for column in output_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"yfinance download DataFrame missing columns: {missing_columns}")

    return df[list(output_columns)]


def _stack_ticker_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Stack yfinance MultiIndex columns into rows with a Ticker column."""
    ticker_level = "Ticker" if "Ticker" in df.columns.names else -1
    df = df.stack(level=ticker_level, future_stack=True).reset_index()
    ticker_column = "Ticker" if "Ticker" in df.columns else df.columns[1]
    return df.rename(columns={ticker_column: "Ticker"})


def date_value(value, required: bool = False):
    """Return a ``date`` value from a date-like value.

    :param value: ISO date string, pandas timestamp, datetime, or date value.
    :param required: Whether missing values should raise ``ValueError``.
    :returns: Python ``date`` value.
    :raises ValueError: If ``required`` is true and the value is missing or invalid.
    """
    if is_missing(value):
        if required:
            raise ValueError("date is required")
        return None
    if isinstance(value, str):
        converted = date.fromisoformat(value[:10])
    elif isinstance(value, datetime):
        converted = value.date()
    elif isinstance(value, date):
        converted = value
    elif hasattr(value, "date"):
        converted = value.date()
    else:
        converted = value

    if required and not isinstance(converted, date):
        raise ValueError(f"date value cannot be converted: {value!r}")

    return converted


def row_value(row, field_name: str):
    """Return a row field value when present."""
    return getattr(row, field_name, None)


def optional_float(value):
    """Return ``None`` or a float value."""
    return None if is_missing(value) else float(value)


def required_float(value):
    """Return a float value or raise when it is missing."""
    if is_missing(value):
        raise ValueError("float value is required")
    return float(value)


def optional_int(value):
    """Return ``None`` or an integer value."""
    return None if is_missing(value) else int(value)


def optional_bool(value):
    """Return ``None`` or a boolean value."""
    return None if is_missing(value) else bool(value)


def optional_str(value):
    """Return ``None`` or a string value."""
    return None if is_missing(value) else str(value)


def is_missing(value):
    """Return whether a pandas/yfinance value is missing."""
    return value is None or bool(pd.isna(value))
