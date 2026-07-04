"""Entry point for option metric calculations."""

import logging
import os
from pathlib import Path

from option_metrics.app import OptionMetricsApp


DEFAULT_LOG_FILE = "../logs/option_metrics.log"


def configure_logging(default_log_file: str = DEFAULT_LOG_FILE) -> None:
    """Configure console logging and the option metrics log file."""

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_file = (
        os.getenv("OPTION_METRICS_LOG_FILE")
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


def main() -> None:
    """Run the option metrics parquet pipeline."""

    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting option metrics pipeline")
    try:
        OptionMetricsApp().run()
    except Exception:
        logger.exception("Option metrics pipeline failed")
        raise
    logger.info("Finished option metrics pipeline")


if __name__ == "__main__":
    main()
