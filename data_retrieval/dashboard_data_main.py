"""Dashboard data export entry point."""

from config import AppConfig
from dashboard_data.dashboard_data_app import App as DashboardDataApp
from etl_main import configure_logging


DEFAULT_LOG_FILE = "logs/dashboard_data.log"


def main():
    """Run dashboard parquet generation from the existing SQLite database."""
    configure_logging(
        default_log_file=DEFAULT_LOG_FILE,
        log_file_env="DASHBOARD_DATA_LOG_FILE",
    )
    DashboardDataApp(AppConfig()).run()


if __name__ == "__main__":
    main()
