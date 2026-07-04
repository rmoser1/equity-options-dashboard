"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path.cwd() if PACKAGE_DIR.parent == Path("/") else PACKAGE_DIR.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for ETL and dashboard data generation.

    Values are read from environment variables at import time and fall back to
    local development defaults.
    """

    db_path: str = os.getenv("DB_PATH", str(DATA_DIR / "DB.db"))
    dashboard_data_dir: str = os.getenv("DASHBOARD_DATA_DIR", str(DATA_DIR / "parquet"))

    volume_threshold: int = int(os.getenv("VOLUME_THRESHOLD", 1000))
    volume_concurrency: int = int(os.getenv("VOLUME_CONCURRENCY", 5))
    run_occ_pipeline: bool = os.getenv("RUN_OCC_PIPELINE", "true").lower() == "true"

    option_avg_batch_size: int = int(os.getenv("OPTION_AVG_BATCH_SIZE", 2))
    option_rate_limit_max_attempts: int = int(os.getenv("OPTION_RATE_LIMIT_MAX_ATTEMPTS", 4))
    option_rate_limit_backoff_seconds: float = float(os.getenv("OPTION_RATE_LIMIT_BACKOFF_SECONDS", 60.0))
    option_rate_limit_backoff_multiplier: float = float(os.getenv("OPTION_RATE_LIMIT_BACKOFF_MULTIPLIER", 2.0))

    historical_period: str = os.getenv("HISTORICAL_PERIOD", "max")
