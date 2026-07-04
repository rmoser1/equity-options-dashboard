"""Live contract tests for yfinance market data responses.

These tests validate the external shape returned by
:class:`etl.client.yfinance_client.YFinanceClient`. They are marked as
``contract`` and ``network`` so normal test runs can skip live provider calls.
"""

import pandas as pd
import pytest

from etl.client.yfinance_client import YFinanceClient
from etl.config.interest_rates import INTEREST_RATE_TICKERS, INTEREST_RATES
from etl.transformers.historical_transformer import HistoricalTransformer
from etl.transformers.interest_rate_transformer import InterestRateTransformer
from etl.transformers.options_transformer import OptionsTransformer
from etl.transformers.stock_info_transformer import StockInfoTransformer
from schemas.historical_price import HistoricalPrice
from schemas.interest_rate import InterestRate
from schemas.option_contract import OptionContract
from schemas.stock_info import StockInfoItem


pytestmark = [pytest.mark.contract, pytest.mark.network]

YFINANCE_CONTRACT_SYMBOL = "AAPL"
YFINANCE_CONTRACT_HISTORY_START = (
    pd.Timestamp.today() - pd.Timedelta(days=30)
).strftime("%Y-%m-%d")
YFINANCE_EXPIRATION_FORMAT = r"\d{4}-\d{2}-\d{2}"


def yfinance_contract_symbol():
    """Return the ticker symbol used by live yfinance contract tests.

    :returns: Ticker symbol.
    :rtype: str
    """
    return YFINANCE_CONTRACT_SYMBOL


def yfinance_contract_history_start():
    """Return the start date used by ``get_history_since`` contract tests.

    :returns: Start date formatted as ``YYYY-MM-DD``.
    :rtype: str
    """
    return YFINANCE_CONTRACT_HISTORY_START


def yfinance_contract_expiration(client, symbol):
    """Return the option expiration used by option-chain contract tests.

    Assumes live yfinance expirations are formatted as ``YYYY-MM-DD`` and uses
    the first expiration returned by ``get_options``.

    :param client: yfinance client wrapper under test.
    :param str symbol: Ticker symbol.
    :returns: Option expiration formatted as ``YYYY-MM-DD``.
    :rtype: str
    """
    options = client.get_options(symbol)
    if not options["expirations"]:
        pytest.skip(f"No live option expirations returned for {symbol}")

    return options["expirations"][0]


def assert_historical_rows(rows, symbol):
    """Assert transformed history rows match the ``HistoricalPrice`` schema.

    :param rows: Transformed historical price rows.
    :param str symbol: Expected ticker symbol.
    """
    assert rows
    assert all(isinstance(row, HistoricalPrice) for row in rows)
    assert all(row.symbol == symbol for row in rows)
    assert all(row.open >= 0 for row in rows)
    assert all(row.high >= 0 for row in rows)
    assert all(row.low >= 0 for row in rows)
    assert all(row.close >= 0 for row in rows)
    assert all(row.volume >= 0 for row in rows)


def test_get_options_returns_expiration_shape():
    """Verify ``get_options`` returns formatted expiration strings."""
    symbol = yfinance_contract_symbol()
    result = YFinanceClient().get_options(symbol)

    assert result["symbol"] == symbol
    assert isinstance(result["expirations"], tuple)
    assert result["expirations"]
    assert all(isinstance(expiration, str) for expiration in result["expirations"])
    assert all(
        pd.Series(result["expirations"]).str.fullmatch(YFINANCE_EXPIRATION_FORMAT)
    )


def test_get_option_chain_returns_schema_compatible_contract_rows():
    """Verify option-chain data can become ``OptionContract`` rows."""
    client = YFinanceClient()
    symbol = yfinance_contract_symbol()
    expiration = yfinance_contract_expiration(client, symbol)
    result = client.get_option_chain(symbol, expiration)
    rows = OptionsTransformer.transform(
        symbol=result["symbol"],
        expiration=result["expiration"],
        calls_df=result["calls"],
        puts_df=result["puts"],
    )

    assert result["symbol"] == symbol
    assert result["expiration"] == expiration
    assert isinstance(result["calls"], pd.DataFrame)
    assert isinstance(result["puts"], pd.DataFrame)
    assert not result["calls"].empty or not result["puts"].empty
    assert rows
    assert all(isinstance(row, OptionContract) for row in rows)
    assert all(row.stockSymbol == symbol for row in rows)
    assert all(row.contractSymbol for row in rows)
    assert all(row.strike >= 0 for row in rows)


def test_get_info_returns_schema_compatible_stock_info_rows():
    """Verify stock metadata can become ``StockInfoItem`` rows."""
    symbol = yfinance_contract_symbol()
    result = YFinanceClient().get_info(symbol)
    rows = StockInfoTransformer.transform(result["symbol"], result["info"])

    assert result["symbol"] == symbol
    assert isinstance(result["info"], dict)
    assert result["info"]
    assert rows
    assert all(isinstance(row, StockInfoItem) for row in rows)
    assert all(row.stockSymbol == symbol for row in rows)
    assert all(row.itemName for row in rows)
    assert all(isinstance(row.itemValue, str) for row in rows)


def test_get_history_returns_schema_compatible_historical_price_rows():
    """Verify period history can become ``HistoricalPrice`` rows."""
    symbol = yfinance_contract_symbol()
    result = YFinanceClient().get_history(symbol, period="1mo")
    rows = HistoricalTransformer.transform(result["data"], result["symbol"])

    assert result["symbol"] == symbol
    assert isinstance(result["data"], pd.DataFrame)
    assert not result["data"].empty
    assert_historical_rows(rows, symbol)


def test_get_history_since_returns_schema_compatible_historical_price_rows():
    """Verify date-bounded history can become ``HistoricalPrice`` rows."""
    symbol = yfinance_contract_symbol()
    result = YFinanceClient().get_history_since(symbol, yfinance_contract_history_start())
    rows = HistoricalTransformer.transform(result["data"], result["symbol"])

    assert result["symbol"] == symbol
    assert isinstance(result["data"], pd.DataFrame)
    assert not result["data"].empty
    assert_historical_rows(rows, symbol)


def test_get_interest_rates_returns_schema_compatible_interest_rate_rows():
    """Verify Treasury yield data can become ``InterestRate`` rows."""
    result = YFinanceClient().get_interest_rates()
    rows = InterestRateTransformer.transform(result)

    assert result["tickers"] == INTEREST_RATE_TICKERS
    assert isinstance(result["data"], pd.DataFrame)
    assert not result["data"].empty
    assert rows
    assert {row.ticker for row in rows} == set(INTEREST_RATE_TICKERS)
    assert all(isinstance(row, InterestRate) for row in rows)
    assert all(row.name == INTEREST_RATES[row.ticker] for row in rows)
    assert all(row.rate >= 0 for row in rows)
