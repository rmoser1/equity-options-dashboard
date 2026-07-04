"""Tests for :mod:`etl.pipelines.stock_info_pipeline`."""

from etl.pipelines.stock_info_pipeline import StockInfoPipeline


class ClientStub:
    """YFinance client stub recording stock-info requests."""

    def __init__(self):
        """Initialize the client stub."""
        self.calls = []
        self.info = {"sector": "Technology"}

    def get_info(self, symbol):
        """Record a stock-info request."""
        self.calls.append(("get_info", symbol))
        return {"symbol": symbol, "info": self.info}


class DatabaseStub:
    """Database stub recording inserted rows."""

    def insert_many_overwrite_duplicates(self, rows):
        """Record upserted rows."""
        self.inserted = rows
        return len(rows)


def test_process_symbol_fetches_transforms_and_inserts(monkeypatch):
    """Verify fetched stock info is transformed and inserted for one symbol."""
    rows = [object()]
    transformed = []

    def fake_transform(symbol, info):
        transformed.append((symbol, info))
        return rows

    monkeypatch.setattr(
        "etl.pipelines.stock_info_pipeline.StockInfoTransformer.transform",
        fake_transform,
    )
    client = ClientStub()
    db = DatabaseStub()

    StockInfoPipeline(client=client, database=db).process_symbol("AAPL")

    assert client.calls == [("get_info", "AAPL")]
    assert transformed == [("AAPL", client.info)]
    assert db.inserted is rows
