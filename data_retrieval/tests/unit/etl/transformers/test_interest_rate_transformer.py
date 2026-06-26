"""Tests for :mod:`etl.transformers.interest_rate_transformer`."""

from datetime import date

import pandas as pd

from etl.transformers.interest_rate_transformer import InterestRateTransformer


def test_transform_returns_latest_decimal_rate_for_each_ticker():
    """Verify latest non-null percent yields become decimal rate rows."""
    columns = pd.MultiIndex.from_product(
        [["Close"], ["^IRX", "^FVX"]],
        names=["Price", "Ticker"],
    )
    df = pd.DataFrame(
        [
            [4.0, 4.5],
            [4.2, 4.7],
        ],
        index=pd.DatetimeIndex(["2026-01-02", "2026-01-05"], name="Date"),
        columns=columns,
    )

    rows = sorted(
        InterestRateTransformer.transform({"data": df}),
        key=lambda row: row.ticker,
    )

    assert [
        {"ticker": row.ticker, "name": row.name, "date": row.date, "rate": row.rate}
        for row in rows
    ] == [
        {
            "ticker": "^FVX",
            "name": "5 Year Treasury Note",
            "date": date(2026, 1, 5),
            "rate": 0.047,
        },
        {
            "ticker": "^IRX",
            "name": "13 Week Treasury Bill",
            "date": date(2026, 1, 5),
            "rate": 0.042,
        },
    ]


def test_transform_returns_empty_for_empty_frame():
    """Verify empty provider data produces no rows."""
    assert InterestRateTransformer.transform({"data": pd.DataFrame()}) == []
