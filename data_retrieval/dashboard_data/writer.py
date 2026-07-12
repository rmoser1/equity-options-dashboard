"""Dashboard parquet output writer.

This module provides :class:`ParquetWriter`, which writes transformed
dashboard datasets to parquet files.
"""

import logging
import os

import pyarrow.parquet as pq

from dashboard_data.memory import memory_usage


logger = logging.getLogger(__name__)


class ParquetWriter:
    """Write dashboard output datasets to a folder as parquet files."""

    FILES = {
        "stocks": "stocks.parquet",
        "options_hist": "options_hist.parquet",
        "options_last": "options_last.parquet",
        "stock_info": "stock_info.parquet",
        "stock_prices": "stock_prices.parquet",
    }

    def __init__(self, folder: str):
        """Initialize the writer.

        :param folder: Destination folder for parquet output files.
        """
        self.folder = folder

    def write_dataset(self, key: str, obj):
        """Write one dashboard dataset to its parquet file."""
        self._atomic_write(obj, self.FILES[key])

    def write_dataset_batches(self, key: str, batches, empty):
        """Write one dashboard dataset from DataFrame batches."""
        self._atomic_write_batches(batches, empty, self.FILES[key])

    def _atomic_write(self, obj, filename: str):
        """Write one parquet file through a temporary file."""
        target = f"{self.folder}/{filename}"
        tmp = target + ".tmp"
        obj.write_parquet(tmp)
        os.replace(tmp, target)

    def _atomic_write_batches(self, batches, empty, filename: str):
        """Write one parquet file incrementally through a temporary file."""
        target = f"{self.folder}/{filename}"
        tmp = target + ".tmp"
        writer = None
        try:
            for batch_number, batch in enumerate(batches, start=1):
                if batch.is_empty():
                    logger.info(
                        "Skipping empty parquet batch %s for %s %s",
                        batch_number,
                        filename,
                        memory_usage(),
                    )
                    continue
                table = batch.to_arrow()
                if writer is None:
                    writer = pq.ParquetWriter(tmp, table.schema)
                writer.write_table(table)
                logger.info(
                    "Wrote parquet batch %s for %s rows=%s %s",
                    batch_number,
                    filename,
                    batch.height,
                    memory_usage(),
                )
            if writer is None:
                empty.write_parquet(tmp)
                logger.info(
                    "Wrote empty parquet file %s %s",
                    filename,
                    memory_usage(),
                )
        finally:
            if writer is not None:
                writer.close()
        os.replace(tmp, target)
        logger.info("Finished parquet file %s %s", filename, memory_usage())
