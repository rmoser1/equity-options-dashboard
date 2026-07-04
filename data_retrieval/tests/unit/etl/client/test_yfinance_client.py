"""Unit tests for the yfinance client wrapper.

These tests keep yfinance calls deterministic and offline while checking that
the wrapper preserves the response shape expected by downstream ETL code.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from etl.client.yfinance_client import YFinanceClient


def install_mock_ticker(monkeypatch):
    """Install a mocked ``yf.Ticker`` factory.

    :param monkeypatch: Pytest monkeypatch fixture.
    :returns: Mock ticker factory and ticker object returned by the factory.
    """
    chain = SimpleNamespace(
        calls=pd.DataFrame({"contractSymbol": ["AAPL260116C00100000"]}),
        puts=pd.DataFrame({"contractSymbol": ["AAPL260116P00100000"]}),
    )
    ticker = SimpleNamespace(
        options=("2026-01-16", "2026-02-20"),
        info={"sector": "Technology"},
        option_chain=Mock(return_value=chain),
    )
    ticker_factory = Mock(return_value=ticker)

    monkeypatch.setattr("etl.client.yfinance_client.yf.Ticker", ticker_factory)
    return ticker_factory, ticker


def install_fake_download(monkeypatch):
    """Install a fake ``yf.download`` function.

    :param monkeypatch: Pytest monkeypatch fixture.
    :returns: DataFrame returned by the fake and captured call arguments.
    """
    calls = []
    df = pd.DataFrame({"Close": [1.0]})

    def fake_download(*args, **kwargs):
        calls.append((args, kwargs))
        return df

    monkeypatch.setattr("etl.client.yfinance_client.yf.download", fake_download)
    return df, calls


def test_get_options_returns_symbol_and_expirations(monkeypatch):
    """Verify ``get_options`` returns expirations for the requested symbol."""
    ticker_factory, _ = install_mock_ticker(monkeypatch)

    assert YFinanceClient().get_options("AAPL") == {
        "symbol": "AAPL",
        "expirations": ("2026-01-16", "2026-02-20"),
    }
    ticker_factory.assert_called_once_with("AAPL")


def test_get_option_chain_returns_chain_parts(monkeypatch):
    """Verify ``get_option_chain`` returns calls and puts for an expiration."""
    ticker_factory, ticker = install_mock_ticker(monkeypatch)

    result = YFinanceClient().get_option_chain("AAPL", "2026-01-16")

    assert result["symbol"] == "AAPL"
    assert result["expiration"] == "2026-01-16"
    assert result["calls"]["contractSymbol"].to_list() == ["AAPL260116C00100000"]
    assert result["puts"]["contractSymbol"].to_list() == ["AAPL260116P00100000"]
    ticker_factory.assert_called_once_with("AAPL")
    ticker.option_chain.assert_called_once_with("2026-01-16")


def test_get_info_returns_symbol_and_info(monkeypatch):
    """Verify ``get_info`` returns metadata for the requested symbol."""
    ticker_factory, _ = install_mock_ticker(monkeypatch)

    assert YFinanceClient().get_info("AAPL") == {
        "symbol": "AAPL",
        "info": {"sector": "Technology"},
    }
    ticker_factory.assert_called_once_with("AAPL")


def test_get_history_delegates_to_yfinance_download_with_default_period(monkeypatch):
    """Verify ``get_history`` delegates to ``yf.download`` with ``max`` period."""
    df, calls = install_fake_download(monkeypatch)

    result = YFinanceClient().get_history("AAPL")

    assert result == {"symbol": "AAPL", "data": df}
    assert calls == [(("AAPL",), {"period": "max", "auto_adjust": True, "progress": False})]


def test_get_history_delegates_to_yfinance_download_with_period(monkeypatch):
    """Verify ``get_history`` forwards an explicit yfinance period."""
    df, calls = install_fake_download(monkeypatch)

    result = YFinanceClient().get_history("AAPL", period="1y")

    assert result == {"symbol": "AAPL", "data": df}
    assert calls == [(("AAPL",), {"period": "1y", "auto_adjust": True, "progress": False})]


def test_get_history_since_delegates_to_yfinance_download(monkeypatch):
    """Verify ``get_history_since`` forwards the requested start date."""
    df, calls = install_fake_download(monkeypatch)

    result = YFinanceClient().get_history_since("AAPL", "2026-01-02")

    assert result == {"symbol": "AAPL", "data": df}
    assert calls == [(("AAPL",), {"start": "2026-01-02", "auto_adjust": True, "progress": False})]


def test_get_interest_rates_delegates_to_yfinance_download(monkeypatch):
    """Verify ``get_interest_rates`` requests configured Treasury tickers."""
    df, calls = install_fake_download(monkeypatch)

    result = YFinanceClient().get_interest_rates()

    assert result == {"tickers": ("^IRX", "^FVX"), "data": df}
    assert calls == [
        (
            (["^IRX", "^FVX"],),
            {"period": "5d", "auto_adjust": True, "progress": False},
        )
    ]
