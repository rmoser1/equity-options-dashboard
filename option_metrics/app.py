"""Application service for enriching the latest options parquet with metrics."""

import logging
import os
from pathlib import Path

import pandas as pd

from option_metrics.transformer import OptionMetricsTransformer


logger = logging.getLogger(__name__)


class OptionMetricsApp:
    """Calculate option metrics from dashboard parquet data."""

    def __init__(
        self,
        parquet_dir: str | Path | None = None,
        filename: str = "options_last.parquet",
    ) -> None:
        """Initialize the parquet metric application.

        :param parquet_dir: Directory containing dashboard parquet files.
        :param filename: Options parquet filename to read and overwrite.
        """

        self.parquet_dir = Path(
            parquet_dir or os.getenv("DASHBOARD_DATA_DIR", "data/parquet")
        )
        self.path = self.parquet_dir / filename

    def run(self) -> pd.DataFrame:
        """Read options parquet, calculate metrics, and overwrite it atomically.

        :returns: The enriched options DataFrame that was written to disk.
        """

        logger.info("Reading option metrics input from %s", self.path)
        options = pd.read_parquet(self.path)
        logger.info("Loaded %s option rows", f"{len(options):,}")

        logger.info("Calculating option metrics")
        metrics = OptionMetricsTransformer.transform(options)
        logger.info("Calculated metrics for %s option rows", f"{len(metrics):,}")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(f"{self.path.name}.tmp")
        metrics.to_parquet(tmp_path, index=False)
        os.replace(tmp_path, self.path)
        logger.info("Wrote enriched options output to %s", self.path)
        return metrics
