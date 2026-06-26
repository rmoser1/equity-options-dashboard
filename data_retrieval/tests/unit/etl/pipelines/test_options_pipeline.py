"""Tests for :mod:`etl.pipelines.options_pipeline`."""

import pandas as pd
import pytest

from etl.pipelines.options_pipeline import MissingOptionAskQuotes, OptionsPipeline


class ClientStub:
    """YFinance client stub recording option metadata and chain requests."""

    def __init__(self):
        """Initialize the client stub."""
        self.calls = []

    def get_options(self, symbol):
        """Record an option metadata request."""
        self.calls.append(("get_options", symbol))
        return {"symbol": symbol, "expirations": ["2026-01-16", "2026-02-20"]}

    def get_option_chain(self, symbol, expiration):
        """Record an option-chain request."""
        self.calls.append(("get_option_chain", symbol, expiration))
        return {
            "calls": option_chain_frame(ask=1.2),
            "puts": option_chain_frame(ask=0.0),
        }


class DatabaseStub:
    """Database stub recording inserted rows."""

    def insert_many_ignore_duplicates(self, rows):
        """Record inserted rows."""
        self.inserted = rows
        return len(rows)


def test_process_symbol_loads_all_expirations(monkeypatch):
    """Verify every expiration is fetched, transformed, and inserted."""
    transformed = []

    def fake_transform(symbol, expiration, calls_df, puts_df):
        row = (symbol, expiration, calls_df, puts_df)
        transformed.append(row)
        return [row]

    monkeypatch.setattr("etl.pipelines.options_pipeline.OptionsTransformer.transform", fake_transform)
    client = ClientStub()
    db = DatabaseStub()

    OptionsPipeline(client=client, database=db).process_symbol("AAPL")

    assert client.calls == [
        ("get_options", "AAPL"),
        ("get_option_chain", "AAPL", "2026-01-16"),
        ("get_option_chain", "AAPL", "2026-02-20"),
    ]
    assert db.inserted == transformed


def option_chain_frame(ask):
    """Build a minimal yfinance-like option-chain frame."""
    return pd.DataFrame([{"contractSymbol": "AAPL260116C00100000", "ask": ask}])


def test_process_symbol_fails_when_all_expirations_have_zero_asks():
    """Verify symbols with no positive ask quotes are rejected."""

    class ZeroAskClient(ClientStub):
        """Client returning only zero-ask option chains."""

        def get_option_chain(self, symbol, expiration):
            """Record an option-chain request and return unusable quotes."""
            self.calls.append(("get_option_chain", symbol, expiration))
            return {
                "calls": option_chain_frame(ask=0.0),
                "puts": option_chain_frame(ask=0.0),
            }

    client = ZeroAskClient()

    with pytest.raises(MissingOptionAskQuotes, match="No positive ask quotes for AAPL"):
        OptionsPipeline(client=client, database=DatabaseStub()).process_symbol("AAPL")


def test_run_stops_before_other_symbols_when_first_symbol_has_zero_asks():
    """Verify a zero-ask first symbol aborts option loading for later symbols."""

    class ZeroAskClient(ClientStub):
        """Client returning only zero-ask option chains."""

        def get_option_chain(self, symbol, expiration):
            """Record an option-chain request and return unusable quotes."""
            self.calls.append(("get_option_chain", symbol, expiration))
            return {
                "calls": option_chain_frame(ask=0.0),
                "puts": option_chain_frame(ask=0.0),
            }

    client = ZeroAskClient()
    db = DatabaseStub()

    OptionsPipeline(client=client, database=db).run(["AAPL", "MSFT"])

    assert client.calls == [
        ("get_options", "AAPL"),
        ("get_option_chain", "AAPL", "2026-01-16"),
        ("get_option_chain", "AAPL", "2026-02-20"),
    ]
    assert not hasattr(db, "inserted")
