"""Tests for the :mod:`schemas.historical_price` module."""

from datetime import date

from schemas.historical_price import HistoricalPrice


def test_historical_price_table_and_fields():
    """Ensure :class:`HistoricalPrice` maps table metadata and fields."""

    row = HistoricalPrice(
        date=date(2026, 1, 2),
        symbol="AAPL",
        open=1.0,
        high=2.0,
        low=0.5,
        close=1.5,
        volume=100,
    )

    assert HistoricalPrice.__tablename__ == "stockPrices"
    assert row.symbol == "AAPL"
    assert row.volume == 100
