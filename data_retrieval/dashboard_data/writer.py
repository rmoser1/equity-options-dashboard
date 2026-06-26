"""Dashboard parquet output writer.

This module provides :class:`ParquetWriter`, which writes transformed
dashboard datasets to parquet files.
"""

import os


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

    def write(self, data: dict):
        """Write dashboard datasets to parquet files.

        :param data: Dictionary of Polars DataFrames keyed by dataset name.
        """
        for key, filename in self.FILES.items():
            self._atomic_write(data[key], filename)

    def _atomic_write(self, obj, filename: str):
        """Write one parquet file through a temporary file."""
        target = f"{self.folder}/{filename}"
        tmp = target + ".tmp"
        obj.write_parquet(tmp)
        os.replace(tmp, target)
