"""Tests for the :mod:`schemas.option_volume` module."""

from datetime import date

from schemas.option_volume import OptionVolume


def test_option_volume_table_and_fields():
    """Ensure :class:`OptionVolume` maps table metadata and fields."""

    row = OptionVolume(symbol="AAPL", date=date(2026, 1, 2), volume=1000)

    assert OptionVolume.__tablename__ == "aggOptionVolume"
    assert row.symbol == "AAPL"
    assert row.volume == 1000
