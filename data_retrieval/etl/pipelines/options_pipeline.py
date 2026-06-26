"""Pipeline for loading option contracts."""

import logging
import pandas as pd

from etl.pipelines.base_pipeline import BasePipeline
from etl.transformers.options_transformer import OptionsTransformer


logger = logging.getLogger(__name__)


class MissingOptionAskQuotes(ValueError):
    """Raised when Yahoo returns no positive ask quotes for a symbol."""


class OptionsPipeline(BasePipeline):
    """Load option contracts for each symbol.

    :param client: Market data client with option-chain methods.
    :param database: Shared database helper.
    """

    def __init__(self, client, database, **kwargs):
        """Initialize the pipeline."""
        super().__init__(database, **kwargs)
        self.client = client

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
        metadata = self.client.get_options(symbol)
        contracts = []
        logger.info("Fetching %s option expirations for %s", len(metadata["expirations"]), symbol)

        for expiration in metadata["expirations"]:
            contracts.extend(self._contracts_for_expiration(symbol, expiration))

        if not contracts:
            raise MissingOptionAskQuotes(f"No positive ask quotes for {symbol}")
        return contracts

    def _contracts_for_expiration(self, symbol: str, expiration: str):
        """Fetch and transform option contracts for one expiration."""
        chain = self.client.get_option_chain(symbol, expiration)
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