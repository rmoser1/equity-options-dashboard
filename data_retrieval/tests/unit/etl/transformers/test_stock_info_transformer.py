"""Tests for :mod:`etl.transformers.stock_info_transformer`."""

import json

from etl.transformers.stock_info_transformer import StockInfoTransformer
from schemas.stock_info import StockInfoItem


def test_transform_serializes_stock_info_items():
    """Verify stock metadata is serialized into key-value rows."""
    rows = StockInfoTransformer.transform("AAPL", {"sector": "Technology", "employees": 100})

    assert all(isinstance(row, StockInfoItem) for row in rows)
    assert [(row.stockSymbol, row.itemName, json.loads(row.itemValue)) for row in rows] == [
        ("AAPL", "sector", "Technology"),
        ("AAPL", "employees", 100),
    ]


def test_transform_returns_empty_list_for_empty_info():
    """Verify empty stock metadata produces no rows."""
    assert StockInfoTransformer.transform("AAPL", {}) == []


def test_transform_json_serializes_nested_and_optional_values():
    """Verify yfinance metadata shapes round-trip through JSON serialization."""
    info = {
        "hasOptions": True,
        "website": None,
        "officers": [{"name": "Jane Example", "age": 42}],
        "metrics": {"beta": 1.2, "shares": 1000},
        123: "numeric key",
    }

    rows = StockInfoTransformer.transform("AAPL", info)

    values = {row.itemName: json.loads(row.itemValue) for row in rows}
    assert values == {
        "hasOptions": True,
        "website": None,
        "officers": [{"name": "Jane Example", "age": 42}],
        "metrics": {"beta": 1.2, "shares": 1000},
        "123": "numeric key",
    }
