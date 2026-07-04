"""ETL application wiring and orchestration."""

import logging

from sqlmodel import select

from etl.client.occ_client import OCCClient
from etl.client.yfinance_client import YFinanceClient
from etl.pipelines.historical_pipeline import HistoricalPipeline
from etl.pipelines.interest_rate_pipeline import InterestRatePipeline
from etl.pipelines.occ_pipeline import OCCPipeline
from etl.pipelines.options_pipeline import OptionsPipeline
from etl.pipelines.stock_info_pipeline import StockInfoPipeline
from etl.services.volume_service import VolumeService
from database import Database
from schemas.underlying import Underlying


logger = logging.getLogger(__name__)


class App:
    """Wire and run the ETL application.

    :param config: Application configuration object.
    """

    def __init__(self, config):
        """Initialize infrastructure, clients, services, and pipelines."""
        self.config = config
        self.database = Database(config.db_path, model_package="schemas")
        self.occ_client = OCCClient()
        self.yfinance_client = YFinanceClient()
        self.volume_service = VolumeService(
            occ_client=self.occ_client,
            concurrency=config.volume_concurrency,
        )
        self.occ_pipeline = OCCPipeline(
            occ_client=self.occ_client,
            volume_service=self.volume_service,
            database=self.database,
            volume_threshold=config.volume_threshold,
        )
        self.options_pipeline = OptionsPipeline(
            client=self.yfinance_client,
            database=self.database,
            avg_batch_size=getattr(config, "option_avg_batch_size", 2),
            rate_limit_max_attempts=getattr(config, "option_rate_limit_max_attempts", 4),
            rate_limit_backoff_seconds=getattr(config, "option_rate_limit_backoff_seconds", 60.0),
            rate_limit_backoff_multiplier=getattr(config, "option_rate_limit_backoff_multiplier", 2.0),
        )
        self.stock_info_pipeline = StockInfoPipeline(
            client=self.yfinance_client,
            database=self.database,
        )
        self.historical_pipeline = HistoricalPipeline(
            client=self.yfinance_client,
            database=self.database,
            period=config.historical_period,
        )
        self.interest_rate_pipeline = InterestRatePipeline(
            client=self.yfinance_client,
            database=self.database,
        )

    def initialize(self):
        """Create database tables for all SQLModel schemas."""
        self.database.create_all_tables()

    def run(self):
        """Run the full ETL workflow."""
        if getattr(self.config, "run_occ_pipeline", True):
            logger.info("Running OCC pipeline")
            self.occ_pipeline.run()
        else:
            logger.info("Skipping OCC pipeline")

        symbols = self.database.scalars(select(Underlying.symbol))
        logger.info("Retrieved %s symbols", len(symbols))

        logger.info("Running options pipeline")
        self._run_symbol_pipeline(self.options_pipeline, symbols)
        logger.info("Running stock info pipeline")
        self._run_symbol_pipeline(self.stock_info_pipeline, symbols)
        logger.info("Running historical pipeline")
        self._run_symbol_pipeline(self.historical_pipeline, symbols)
        logger.info("Running interest rate pipeline")
        self.interest_rate_pipeline.run()
        logger.info("All pipelines complete")

    @staticmethod
    def _run_symbol_pipeline(pipeline, symbols: list[str]):
        """Run a symbol-oriented pipeline."""
        pipeline.run(symbols)
