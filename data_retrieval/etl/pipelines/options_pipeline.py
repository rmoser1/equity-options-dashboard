"""Pipeline for loading option contracts."""

import logging
import pandas as pd
from yfinance.exceptions import YFRateLimitError

from etl.pipelines.base_pipeline import BasePipeline
from etl.transformers.options_transformer import OptionsTransformer


logger = logging.getLogger(__name__)


class MissingOptionAskQuotes(ValueError):
    """Raised when Yahoo returns no positive ask quotes for a symbol."""


class OptionsPipeline(BasePipeline):
    """Load option contracts for each symbol.

    :param client: Market data client with option-chain methods.
    :param database: Shared database helper.
    :param rate_limit_max_attempts: Total attempts for a rate-limited request.
    :param rate_limit_backoff_seconds: Initial wait before retrying a rate limit.
    :param rate_limit_backoff_multiplier: Multiplier applied after each retry.
    """

    def __init__(
        self,
        client,
        database,
        avg_batch_size: int = 2,
        rate_limit_max_attempts: int = 4,
        rate_limit_backoff_seconds: float = 60.0,
        rate_limit_backoff_multiplier: float = 2.0,
        **kwargs,
    ):
        """Initialize the pipeline."""
        super().__init__(database, avg_batch_size=avg_batch_size, **kwargs)
        self.client = client
        self.rate_limit_max_attempts = max(1, rate_limit_max_attempts)
        self.rate_limit_backoff_seconds = rate_limit_backoff_seconds
        self.rate_limit_backoff_multiplier = max(1.0, rate_limit_backoff_multiplier)

    def run(self, symbols: list[str]):
        """Run option loading, stopping early when the first symbol has no asks."""
        if not symbols:
            super().run(symbols)
            return

        first_symbol = symbols[0]
        try:
            self.process_symbol(first_symbol)
        except MissingOptionAskQuotes:
            logger.warning(
                "Skipping options pipeline because first symbol %s has no positive ask quotes",
                first_symbol,
            )
            return

        super().run(symbols[1:])

    def process_symbol(self, symbol: str):
        """Load and insert option contracts for one symbol.

        :param symbol: Ticker symbol to process.
        """
        contracts = self._contracts_for_symbol(symbol)
        inserted = self.database.insert_many_ignore_duplicates(contracts)
        logger.info("Inserted %s/%s option contract rows for %s", inserted, len(contracts), symbol)

    def _contracts_for_symbol(self, symbol: str):
        """Fetch and transform all usable option contracts for one symbol."""
        metadata = self._request_with_retry(
            f"option metadata for {symbol}",
            lambda: self.client.get_options(symbol),
        )
        contracts = []
        logger.info("Fetching %s option expirations for %s", len(metadata["expirations"]), symbol)

        for expiration in metadata["expirations"]:
            contracts.extend(self._contracts_for_expiration(symbol, expiration))

        if not contracts:
            raise MissingOptionAskQuotes(f"No positive ask quotes for {symbol}")
        return contracts

    def _contracts_for_expiration(self, symbol: str, expiration: str):
        """Fetch and transform option contracts for one expiration."""
        chain = self._request_with_retry(
            f"option chain for {symbol} {expiration}",
            lambda: self.client.get_option_chain(symbol, expiration),
        )
        calls = self._positive_ask_rows(chain["calls"])
        puts = self._positive_ask_rows(chain["puts"])
        if calls.empty and puts.empty:
            logger.info("Skipping %s %s because all option ask quotes are zero", symbol, expiration)
            return []

        contracts = OptionsTransformer.transform(
            symbol=symbol,
            expiration=expiration,
            calls_df=calls,
            puts_df=puts,
        )
        logger.info("Fetched %s option contract rows for %s %s", len(contracts), symbol, expiration)
        return contracts

    @staticmethod
    def _positive_ask_rows(df):
        """Return option-chain rows with positive ask quotes."""
        if df.empty or "ask" not in df:
            return df.iloc[0:0]
        asks = pd.to_numeric(df["ask"], errors="coerce")
        return df.loc[asks > 0].copy()

    def _request_with_retry(self, description: str, request_func):
        """Run one Yahoo option request with throttling and rate-limit backoff."""
        backoff = self.rate_limit_backoff_seconds

        for attempt in range(1, self.rate_limit_max_attempts + 1):
            try:
                return request_func()
            except Exception as exc:
                if not self._is_rate_limit_error(exc):
                    raise
                if attempt >= self.rate_limit_max_attempts:
                    logger.exception(
                        "Yahoo rate limit persisted for %s after %s attempts",
                        description,
                        attempt,
                    )
                    raise

                logger.warning(
                    "Yahoo rate limited %s on attempt %s/%s; retrying in %.1f seconds",
                    description,
                    attempt,
                    self.rate_limit_max_attempts,
                    backoff,
                )
                self.sleep(backoff)
                backoff *= self.rate_limit_backoff_multiplier

        raise RuntimeError(f"Unexpected retry exhaustion for {description}")

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        """Return whether an exception represents a Yahoo rate limit."""
        return (
            isinstance(exc, YFRateLimitError)
            or type(exc).__name__ == "YFRateLimitError"
        )
