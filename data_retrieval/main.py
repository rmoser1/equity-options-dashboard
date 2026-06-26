"""Data retrieval entry point.

This module configures logging, loads application configuration, runs the ETL
workflow, and then builds dashboard data outputs.
"""

import logging
import os
from pathlib import Path

from config import AppConfig
from dashboard_data.dashboard_data_app import App as DashboardDataApp
from etl.etl_app import App as ETLApp


DEFAULT_LOG_FILE = "logs/data_retrieval.log"


def configure_logging(default_log_file: str = DEFAULT_LOG_FILE) -> None:
    """Configure console logging and the data retrieval log file."""

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_file = (
        os.getenv("DATA_RETRIEVAL_LOG_FILE")
        or os.getenv("LOG_FILE")
        or default_log_file
    )
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )


def main():
    """Run ETL first, then generate dashboard data."""
    configure_logging()
    config = AppConfig()

    etl_app = ETLApp(config)
    etl_app.initialize()
    etl_app.run()

    dashboard_data_app = DashboardDataApp(config)
    dashboard_data_app.run()


if __name__ == "__main__":
    main()
