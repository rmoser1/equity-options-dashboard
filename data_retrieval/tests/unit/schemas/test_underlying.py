"""Tests for the :mod:`schemas.underlying` module."""

from schemas.underlying import Underlying


def test_underlying_table_and_fields():
    """Ensure :class:`Underlying` maps table metadata and fields."""

    row = Underlying(symbol="AAPL", name="Apple")

    assert Underlying.__tablename__ == "stocks"
    assert row.symbol == "AAPL"
    assert row.name == "Apple"
