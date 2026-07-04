"""Client wrapper for yfinance market data access.

This module provides :class:`YFinanceClient`, which fetches stock metadata,
option chains, and historical prices from yfinance.
"""

import logging

import yfinance as yf

from etl.config.interest_rates import INTEREST_RATE_TICKERS


logger = logging.getLogger(__name__)


class YFinanceClient:
    """Fetch equity, option, and historical price data from yfinance."""

    def get_options(self, symbol: str):
        """Fetch available option expiration dates for a symbol.

        :param symbol: Ticker symbol.
        :returns: Dictionary containing ``symbol`` and ``expirations``.
        """
        logger.debug("Fetching options %s", symbol)
        ticker = yf.Ticker(symbol)
        return {
            "symbol": symbol,
            "expirations": ticker.options,
        }

    def get_option_chain(self, symbol: str, expiration: str):
        """Fetch the call and put option chains for one expiration.

        :param symbol: Ticker symbol.
        :param expiration: Option expiration date accepted by yfinance.
        :returns: Dictionary containing ``symbol``, ``expiration``, ``calls``,
            and ``puts``.
        """
        ticker = yf.Ticker(symbol)
        chain = ticker.option_chain(expiration)
        return {
            "symbol": symbol,
            "expiration": expiration,
            "calls": chain.calls,
            "puts": chain.puts,
        }

    def get_info(self, symbol: str):
        """Fetch yfinance metadata for a symbol.

        :param symbol: Ticker symbol.
        :returns: Dictionary containing ``symbol`` and ``info``.
        """
        logger.debug("Fetching info %s", symbol)
        ticker = yf.Ticker(symbol)
        return {
            "symbol": symbol,
            "info": ticker.info,
        }

    def get_history(self, symbol: str, period: str = "max"):
        """Fetch historical prices for a symbol over a yfinance period.

        :param symbol: Ticker symbol.
        :param period: Optional yfinance period string, such as ``"1y"`` or
            ``"max"``.
        :default period: ``"max"``
        :returns: Dictionary containing ``symbol`` and historical ``data``.
        """
        logger.debug("Fetching history %s", symbol)
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        return {
            "symbol": symbol,
            "data": df,
        }

    def get_history_since(self, symbol: str, start_date: str):
        """Fetch historical prices starting at a date.

        :param symbol: Ticker symbol.
        :param start_date: Start date in ``YYYY-MM-DD`` format.
        :returns: Dictionary containing ``symbol`` and historical ``data``.
        """
        logger.debug("Fetching history since %s %s", symbol, start_date)
        df = yf.download(symbol, start=start_date, auto_adjust=True, progress=False)
        return {
            "symbol": symbol,
            "data": df,
        }

    def get_interest_rates(self):
        """Fetch recent Treasury yields used as risk-free-rate anchors.

        :returns: Dictionary containing ``tickers`` and historical ``data`` for
            configured Treasury yield tickers.
        """
        logger.debug("Fetching interest rates %s", INTEREST_RATE_TICKERS)
        df = yf.download(
            list(INTEREST_RATE_TICKERS),
            period="5d",
            auto_adjust=True,
            progress=False,
        )
        return {
            "tickers": INTEREST_RATE_TICKERS,
            "data": df,
        }
