"""Dashboard pipeline orchestration.

This module provides :class:`DashboardPipeline`, which loads narrowed dashboard
datasets and writes them incrementally.
"""

import logging


logger = logging.getLogger(__name__)


class DashboardPipeline:
    """Coordinate the dashboard repository, transformer, and writer."""

    def __init__(self, repository, transformer, writer):
        """Initialize the dashboard pipeline.

        :param repository: Object that provides dashboard dataset loaders.
        :param transformer: Object that provides ``transform_options_last(...)``.
        :param writer: Object that provides ``write_dataset(key, data)``.
        """
        self.repository = repository
        self.transformer = transformer
        self.writer = writer

    def run(self):
        """Run the dashboard pipeline."""
        self._write_dataset("stocks", self.repository.load_stocks())
        self._write_dataset("stock_info", self.repository.load_stock_info())
        self._write_dataset("stock_prices", self.repository.load_stock_prices())
        self._write_dataset("options_hist", self.repository.load_options_history())
        self._write_options_last()

    def _write_dataset(self, key: str, data):
        """Write one dataset immediately after loading it."""
        logger.info("Writing dashboard dataset %s with %s rows", key, data.height)
        self.writer.write_dataset(key, data)

    def _write_options_last(self):
        """Load, enrich, and write the latest option snapshot."""
        last_trade_date = self.repository.latest_option_trade_date()
        options = self.repository.load_latest_options(last_trade_date)
        last_stock_price = self.repository.load_latest_stock_prices(last_trade_date)
        stock_info = self.repository.load_stock_info()
        interest_rates = self.repository.load_interest_rates()
        options_last = self.transformer.transform_options_last(
            options=options,
            last_stock_price=last_stock_price,
            stock_info=stock_info,
            interest_rates=interest_rates,
        )
        self._write_dataset("options_last", options_last)
