"""Tests for the :mod:`schemas.stock_info` module."""

from schemas.stock_info import StockInfoItem


def test_stock_info_table_and_fields():
    """Ensure :class:`StockInfoItem` maps table metadata and fields."""

    row = StockInfoItem(stockSymbol="AAPL", itemName="sector", itemValue='"Technology"')

    assert StockInfoItem.__tablename__ == "stockInfo"
    assert row.stockSymbol == "AAPL"
    assert row.itemName == "sector"
