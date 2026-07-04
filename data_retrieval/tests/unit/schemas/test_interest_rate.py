"""Tests for the :mod:`schemas.interest_rate` module."""

from datetime import date

from schemas.interest_rate import InterestRate


def test_interest_rate_table_and_fields():
    """Ensure :class:`InterestRate` maps table metadata and fields."""
    row = InterestRate(
        ticker="^IRX",
        name="13 Week Treasury Bill",
        date=date(2026, 1, 2),
        rate=0.0425,
    )

    assert InterestRate.__tablename__ == "interestRates"
    assert row.ticker == "^IRX"
    assert row.rate == 0.0425
