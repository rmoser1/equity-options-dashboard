"""ETL entry point.

This module configures logging, loads application configuration, and runs the
ETL workflow.
"""

import logging
import os
from pathlib import Path

from config import AppConfig
from etl.etl_app import App as ETLApp


DEFAULT_LOG_FILE = "logs/data_retrieval.log"


def configure_logging(
    default_log_file: str = DEFAULT_LOG_FILE,
    log_file_env: str = "DATA_RETRIEVAL_LOG_FILE",
) -> None:
    """Configure console logging and the service log file."""

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_file = (
        os.getenv(log_file_env)
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
    """Run the ETL workflow."""
    configure_logging()
    config = AppConfig()

    etl_app = ETLApp(config)
    etl_app.initialize()
    etl_app.run()


if __name__ == "__main__":
    main()
