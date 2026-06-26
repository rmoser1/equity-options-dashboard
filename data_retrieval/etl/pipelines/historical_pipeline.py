"""Pipeline for loading historical stock prices."""

import logging

import pandas as pd
from sqlalchemy import func
from sqlmodel import select

from etl.pipelines.base_pipeline import BasePipeline
from etl.transformers.historical_transformer import HistoricalTransformer
from schemas.historical_price import HistoricalPrice


logger = logging.getLogger(__name__)


class HistoricalPipeline(BasePipeline):
    """Load historical prices incrementally for each symbol.

    :param client: Market data client with history methods.
    :param database: Shared database helper.
    :param period: yfinance period used when no prior history exists.
    :default period: ``"max"``
    """

    def __init__(self, client, database, period="max", **kwargs):
        """Initialize the pipeline."""
        super().__init__(database, **kwargs)
        self.client = client
        self.period = period

    def process_symbol(self, symbol: str):
        """Load and insert historical prices for one symbol.

        :param symbol: Ticker symbol to process.
        """
        result = self._fetch_history(symbol)
        rows = HistoricalTransformer.transform(result["data"], result["symbol"])
        inserted = self.database.insert_many_ignore_duplicates(rows)
        logger.info("Inserted %s/%s historical price rows for %s", inserted, len(rows), symbol)

    def _max_date(self, symbol: str):
        """Return latest stored historical price date for a symbol."""
        stmt = select(func.max(HistoricalPrice.date)).where(HistoricalPrice.symbol == symbol)
        value = self.database.scalar(stmt)
        return value.isoformat() if hasattr(value, "isoformat") else value

    def _fetch_history(self, symbol: str):
        """Fetch incremental or full history depending on stored state."""
        last_date = self._max_date(symbol)

        if last_date:
            start_date = (pd.Timestamp(last_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            return self.client.get_history_since(symbol, start_date)

        return self.client.get_history(symbol, self.period)
