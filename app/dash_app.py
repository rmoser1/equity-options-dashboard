"""Dash application entry point."""

import logging
import os
from pathlib import Path

from dash import Dash

from config import AppConfig
from modules.callbacks import register_callbacks
from modules.components import declare_components
from modules.layout import (
    create_layout,
    create_missing_data_layout,
    create_other_exception_layout,
)
from modules.load_app_data import load_app_data


def configure_logging() -> None:
    """Configure dashboard app console logging and the app log file."""

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_file = os.getenv("APP_LOG_FILE") or os.getenv("LOG_FILE") or "logs/app.log"
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )


def create_app(
    config: AppConfig | None = None,
    parquet_folder: str | None = None,
) -> Dash:
    """Create and configure the Dash application.

    :param config: Optional runtime configuration.
    :param parquet_folder: Optional override for the dashboard parquet folder.
    :returns: Configured Dash application.
    """
    configure_logging()
    app = Dash(__name__)
    config = config or AppConfig.from_env()
    data_dir = parquet_folder or config.dashboard_data_dir
    font_sizes = config.resolved_font_sizes

    try:
        data = load_app_data(data_dir)
        components = declare_components(data)
        register_callbacks(app, components, data, font_sizes)
        app.layout = create_layout(components, font_sizes)
    except FileNotFoundError:
        app.layout = create_missing_data_layout(font_sizes)
    except Exception as exc:
        app.layout = create_other_exception_layout(exc, font_sizes)

    return app


app = create_app()
server = app.server


if __name__ == "__main__":
    app.run(debug=True)
