"""Dashboard pipeline orchestration.

This module provides :class:`DashboardPipeline`, which loads narrowed dashboard
datasets and writes them incrementally.
"""

import logging

from dashboard_data.info_item_fields import DIVIDEND_YIELD_NAMES, INFO_ITEM_NAMES
from dashboard_data.memory import memory_usage


logger = logging.getLogger(__name__)


class DashboardPipeline:
    """Coordinate the dashboard repository, transformer, and writer."""

    DATASET_BATCH_SIZE = 50_000
    STOCK_INFO_BATCH_SIZE = 50_000

    def __init__(self, repository, transformer, writer):
        """Initialize the dashboard pipeline.

        :param repository: Object that provides dashboard dataset loaders.
        :param transformer: Object that transforms stock info and latest options.
        :param writer: Object that provides ``write_dataset(key, data)``.
        """
        self.repository = repository
        self.transformer = transformer
        self.writer = writer

    def run(self):
        """Run the dashboard pipeline."""
        self._write_dataset_batches(
            "stocks",
            self.repository.iter_stocks(self.DATASET_BATCH_SIZE),
            self.repository.empty_stocks(),
        )
        self._write_stock_info()
        self._write_dataset_batches(
            "stock_prices",
            self.repository.iter_stock_prices(self.DATASET_BATCH_SIZE),
            self.repository.empty_stock_prices(),
        )
        self._write_dataset_batches(
            "options_hist",
            self.repository.iter_options_history(self.DATASET_BATCH_SIZE),
            self.repository.empty_options_history(),
        )
        self._write_options_last()

    def _write_dataset(self, key: str, data):
        """Write one dataset immediately after loading it."""
        logger.info("Writing dashboard dataset %s with %s rows", key, data.height)
        self.writer.write_dataset(key, data)

    def _write_dataset_batches(self, key: str, batches, empty):
        """Write one dataset from batches."""
        logger.info(
            "Writing dashboard dataset %s in batches batch_size=%s %s",
            key,
            self.DATASET_BATCH_SIZE,
            memory_usage(),
        )
        self.writer.write_dataset_batches(key, batches, empty)

    def _write_stock_info(self):
        """Load, transform, and write stock information items in batches."""
        logger.info(
            "Writing dashboard dataset stock_info in batches batch_size=%s %s",
            self.STOCK_INFO_BATCH_SIZE,
            memory_usage(),
        )
        empty = self.transformer.transform_info_items(self.repository.empty_stock_info())
        self.writer.write_dataset_batches(
            "stock_info",
            self._stock_info_batches(),
            empty,
        )

    def _stock_info_batches(self):
        """Yield transformed stock-info batches with memory diagnostics."""
        for batch_number, batch in enumerate(
            self.repository.iter_stock_info(
                INFO_ITEM_NAMES,
                batch_size=self.STOCK_INFO_BATCH_SIZE,
            ),
            start=1,
        ):
            logger.info(
                "Transforming stock_info batch %s rows=%s %s",
                batch_number,
                batch.height,
                memory_usage(),
            )
            transformed = self.transformer.transform_info_items(batch)
            logger.info(
                "Transformed stock_info batch %s rows=%s %s",
                batch_number,
                transformed.height,
                memory_usage(),
            )
            yield transformed

    def _write_options_last(self):
        """Load, enrich, and write the latest option snapshot."""
        last_trade_date = self.repository.latest_option_trade_date()
        last_stock_price = self.repository.load_latest_stock_prices(last_trade_date)
        stock_info = self.repository.load_stock_info(DIVIDEND_YIELD_NAMES)
        interest_rates = self.repository.load_interest_rates()
        empty = self.transformer.transform_options_last(
            options=self.repository.empty_latest_options(),
            last_stock_price=last_stock_price,
            stock_info=stock_info,
            interest_rates=interest_rates,
        )
        self.writer.write_dataset_batches(
            "options_last",
            self._options_last_batches(
                last_trade_date,
                last_stock_price,
                stock_info,
                interest_rates,
            ),
            empty,
        )

    def _options_last_batches(
        self,
        last_trade_date,
        last_stock_price,
        stock_info,
        interest_rates,
    ):
        """Yield transformed latest-option batches with memory diagnostics."""
        for batch_number, options in enumerate(
            self.repository.iter_latest_options(
                last_trade_date,
                batch_size=self.DATASET_BATCH_SIZE,
            ),
            start=1,
        ):
            logger.info(
                "Transforming options_last batch %s rows=%s %s",
                batch_number,
                options.height,
                memory_usage(),
            )
            transformed = self.transformer.transform_options_last(
                options=options,
                last_stock_price=last_stock_price,
                stock_info=stock_info,
                interest_rates=interest_rates,
            )
            logger.info(
                "Transformed options_last batch %s rows=%s %s",
                batch_number,
                transformed.height,
                memory_usage(),
            )
            yield transformed
