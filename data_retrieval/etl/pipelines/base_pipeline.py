"""Base class for symbol-oriented ETL pipelines."""

import logging
import random
import time
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class BasePipeline(ABC):
    """Run symbol processing in randomized batches.

    :param database: Shared database helper used by concrete pipelines.
    :param avg_batch_size: Average target batch size.
    :param random_module: Random module or compatible object for test injection.
    :param sleep_func: Sleep function for pacing and test injection.
    :default avg_batch_size: ``20``
    :default random_module: ``random``
    :default sleep_func: ``time.sleep``
    """

    def __init__(self, database, avg_batch_size: int = 20, random_module=random, sleep_func=time.sleep):
        """Initialize the pipeline."""
        self.database = database
        self.random = random_module
        self.sleep = sleep_func
        self.avg_batch_size = avg_batch_size

    def run(self, symbols: list[str]):
        """Process symbols in randomized batches.

        :param symbols: Ticker symbols to process.
        """
        i = 0
        total = len(symbols)
        processed = 0

        logger.info("Starting %s for %s symbols", self.__class__.__name__, total)

        while i < len(symbols):
            rand_batch_size = self.random.randrange(1, self.avg_batch_size * 2)
            batch_size = min(rand_batch_size, len(symbols) - i)
            batch = symbols[i : i + batch_size]

            logger.info(
                "Processing %s batch size=%s symbols=%s-%s/%s",
                self.__class__.__name__,
                batch_size,
                i + 1,
                i + batch_size,
                total,
            )

            for symbol in batch:
                try:
                    self.process_symbol(symbol)
                except Exception:
                    logger.exception("Failed %s", symbol)
                processed += 1
                if processed % 25 == 0 or processed == total:
                    logger.info(
                        "Processed %s symbols %s/%s",
                        self.__class__.__name__,
                        processed,
                        total,
                    )
                self.sleep(self.random.random())

            self.sleep(self.random.random() * 6)
            i += batch_size

        logger.info("Finished %s for %s symbols", self.__class__.__name__, total)

    @abstractmethod
    def process_symbol(self, symbol: str):
        """Process one symbol.

        :param symbol: Ticker symbol to process.
        """
        pass
