"""Tests for :mod:`etl.pipelines.historical_pipeline`."""

from datetime import date

import pandas as pd

from etl.pipelines.historical_pipeline import HistoricalPipeline


class DatabaseStub:
    """Database stub recording scalar queries and inserted rows."""

    def __init__(self, scalar_value=None):
        """Initialize the database stub."""
        self.scalar_value = scalar_value
        self.inserted = None

    def scalar(self, statement):
        """Return the configured scalar value."""
        self.statement = statement
        return self.scalar_value

    def insert_many_ignore_duplicates(self, rows):
        """Record inserted rows."""
        self.inserted = rows
        return len(rows)


class ClientStub:
    """YFinance client stub recording historical fetch calls."""

    def __init__(self):
        """Initialize the client stub."""
        self.calls = []
        self.df = pd.DataFrame()

    def get_history(self, symbol, period):
        """Record a full-period history request."""
        self.calls.append(("history", symbol, period))
        return {"symbol": symbol, "data": self.df}

    def get_history_since(self, symbol, start_date):
        """Record an incremental history request."""
        self.calls.append(("history_since", symbol, start_date))
        return {"symbol": symbol, "data": self.df}


def test_fetch_history_uses_full_period_when_no_stored_date():
    """Verify missing stored history triggers a full-period fetch."""
    client = ClientStub()
    pipeline = HistoricalPipeline(client=client, database=DatabaseStub(), period="1y")

    pipeline._fetch_history("AAPL")

    assert client.calls == [("history", "AAPL", "1y")]


def test_fetch_history_uses_next_day_after_stored_date():
    """Verify stored history triggers an incremental fetch from the next day."""
    client = ClientStub()
    pipeline = HistoricalPipeline(client=client, database=DatabaseStub(date(2026, 1, 2)))

    pipeline._fetch_history("AAPL")

    assert client.calls == [("history_since", "AAPL", "2026-01-03")]


def test_process_symbol_fetches_transforms_and_inserts(monkeypatch):
    """Verify fetched history is transformed and inserted for one symbol."""
    client = ClientStub()
    db = DatabaseStub()
    rows = [object()]
    transformed = []

    def fake_transform(df, symbol):
        transformed.append((df, symbol))
        return rows

    monkeypatch.setattr(
        "etl.pipelines.historical_pipeline.HistoricalTransformer.transform",
        fake_transform,
    )

    HistoricalPipeline(client=client, database=db).process_symbol("AAPL")

    assert client.calls == [("history", "AAPL", "max")]
    assert transformed == [(client.df, "AAPL")]
    assert db.inserted is rows
