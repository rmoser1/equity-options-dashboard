"""Dashboard data application wiring and orchestration."""

import logging
from pathlib import Path

from dashboard_data.pipeline import DashboardPipeline
from dashboard_data.repository import DashboardRepository
from dashboard_data.transformer import DashboardTransformer
from dashboard_data.writer import ParquetWriter


logger = logging.getLogger(__name__)


class App:
    """Wire and run the dashboard data application.

    :param config: Application configuration object.
    """

    def __init__(self, config):
        """Initialize repository, transformer, writer, and pipeline."""
        self.config = config
        self.repository = DashboardRepository(config.db_path)
        self.transformer = DashboardTransformer()
        self.writer = ParquetWriter(config.dashboard_data_dir)
        self.pipeline = DashboardPipeline(
            repository=self.repository,
            transformer=self.transformer,
            writer=self.writer,
        )

    def _initialize(self):
        """Create the dashboard data output folder when needed."""
        Path(self.config.dashboard_data_dir).mkdir(parents=True, exist_ok=True)

    def run(self):
        """Run the dashboard data pipeline."""
        self._initialize()
        logger.info("Running dashboard data pipeline")
        self.pipeline.run()
        logger.info("Dashboard data pipeline complete")
