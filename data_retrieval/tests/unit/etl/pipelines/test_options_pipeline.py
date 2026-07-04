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


def options_pipeline(client, db, **kwargs):
    """Build an options pipeline without real test sleeps."""
    return OptionsPipeline(
        client=client,
        database=db,
        sleep_func=lambda _: None,
        **kwargs,
    )


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

    options_pipeline(client=client, db=db).process_symbol("AAPL")

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
        options_pipeline(client=client, db=DatabaseStub()).process_symbol("AAPL")


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

    options_pipeline(client=client, db=db).run(["AAPL", "MSFT"])

    assert client.calls == [
        ("get_options", "AAPL"),
        ("get_option_chain", "AAPL", "2026-01-16"),
        ("get_option_chain", "AAPL", "2026-02-20"),
    ]
    assert not hasattr(db, "inserted")


def test_process_symbol_retries_rate_limited_option_request(monkeypatch):
    """Retry yfinance rate limits with configured exponential backoff."""

    class YFRateLimitError(Exception):
        """Test double matching yfinance's rate-limit exception name."""

    class RateLimitedClient(ClientStub):
        """Client rate-limited once before succeeding."""

        def __init__(self):
            """Initialize the rate-limited client."""
            super().__init__()
            self.metadata_attempts = 0

        def get_options(self, symbol):
            """Raise one rate-limit error before returning metadata."""
            self.metadata_attempts += 1
            self.calls.append(("get_options", symbol, self.metadata_attempts))
            if self.metadata_attempts == 1:
                raise YFRateLimitError("Too Many Requests")
            return {"symbol": symbol, "expirations": ["2026-01-16"]}

    transformed = []

    def fake_transform(symbol, expiration, calls_df, puts_df):
        row = (symbol, expiration, len(calls_df), len(puts_df))
        transformed.append(row)
        return [row]

    monkeypatch.setattr("etl.pipelines.options_pipeline.OptionsTransformer.transform", fake_transform)
    sleeps = []
    client = RateLimitedClient()
    db = DatabaseStub()

    OptionsPipeline(
        client=client,
        database=db,
        rate_limit_max_attempts=3,
        rate_limit_backoff_seconds=5,
        rate_limit_backoff_multiplier=2,
        sleep_func=sleeps.append,
    ).process_symbol("AAPL")

    assert client.calls == [
        ("get_options", "AAPL", 1),
        ("get_options", "AAPL", 2),
        ("get_option_chain", "AAPL", "2026-01-16"),
    ]
    assert sleeps == [5]
    assert db.inserted == transformed


def test_process_symbol_raises_after_rate_limit_retries_are_exhausted():
    """Raise the rate-limit error after the configured attempts are exhausted."""

    class YFRateLimitError(Exception):
        """Test double matching yfinance's rate-limit exception name."""

    class AlwaysRateLimitedClient(ClientStub):
        """Client that never gets past Yahoo rate limiting."""

        def get_options(self, symbol):
            """Always raise a rate-limit error."""
            self.calls.append(("get_options", symbol))
            raise YFRateLimitError("Too Many Requests")

    sleeps = []
    client = AlwaysRateLimitedClient()

    with pytest.raises(YFRateLimitError):
        OptionsPipeline(
            client=client,
            database=DatabaseStub(),
            rate_limit_max_attempts=2,
            rate_limit_backoff_seconds=5,
            sleep_func=sleeps.append,
        ).process_symbol("AAPL")

    assert client.calls == [
        ("get_options", "AAPL"),
        ("get_options", "AAPL"),
    ]
    assert sleeps == [5]


def test_process_symbol_does_not_retry_non_rate_limit_errors():
    """Raise non-rate-limit errors immediately without backoff retries."""

    class BrokenClient(ClientStub):
        """Client failing with a non-rate-limit error."""

        def get_options(self, symbol):
            """Always raise a generic provider error."""
            self.calls.append(("get_options", symbol))
            raise RuntimeError("provider response was invalid")

    sleeps = []
    client = BrokenClient()

    with pytest.raises(RuntimeError, match="provider response was invalid"):
        OptionsPipeline(
            client=client,
            database=DatabaseStub(),
            rate_limit_max_attempts=3,
            rate_limit_backoff_seconds=5,
            sleep_func=sleeps.append,
        ).process_symbol("AAPL")

    assert client.calls == [("get_options", "AAPL")]
    assert sleeps == []


def test_process_symbol_does_not_retry_generic_too_many_requests_errors():
    """Only the yfinance rate-limit exception type triggers retry behavior."""

    class BrokenClient(ClientStub):
        """Client failing with a generic error containing rate-limit text."""

        def get_options(self, symbol):
            """Always raise a generic error."""
            self.calls.append(("get_options", symbol))
            raise RuntimeError("Too Many Requests")

    sleeps = []
    client = BrokenClient()

    with pytest.raises(RuntimeError, match="Too Many Requests"):
        OptionsPipeline(
            client=client,
            database=DatabaseStub(),
            rate_limit_max_attempts=3,
            rate_limit_backoff_seconds=5,
            sleep_func=sleeps.append,
        ).process_symbol("AAPL")

    assert client.calls == [("get_options", "AAPL")]
    assert sleeps == []
