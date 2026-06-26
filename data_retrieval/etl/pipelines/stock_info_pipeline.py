"""Pipeline for loading stock metadata."""

import logging

from etl.pipelines.base_pipeline import BasePipeline
from etl.transformers.stock_info_transformer import StockInfoTransformer


logger = logging.getLogger(__name__)


class StockInfoPipeline(BasePipeline):
    """Load stock info key-value rows for each symbol.

    :param client: Market data client with ``get_info(symbol)``.
    :param database: Shared database helper.
    """

    def __init__(self, client, database, **kwargs):
        """Initialize the pipeline."""
        super().__init__(database, **kwargs)
        self.client = client

    def process_symbol(self, symbol: str):
        """Load and insert stock info for one symbol.

        :param symbol: Ticker symbol to process.
        """
        result = self.client.get_info(symbol)
        rows = StockInfoTransformer.transform(symbol, result["info"])
        inserted = self.database.insert_many_ignore_duplicates(rows)
        logger.info("Inserted %s/%s stock info rows for %s", inserted, len(rows), symbol)
