"""Tests for ETL and dashboard data entry points."""

import importlib
import logging
import sys


def test_configure_logging_writes_to_configured_file(tmp_path, monkeypatch):
    """Verify data retrieval logging can be directed to a bind-mounted file."""
    log_file = tmp_path / "logs" / "data_retrieval.log"
    monkeypatch.setenv("DATA_RETRIEVAL_LOG_FILE", str(log_file))
    etl_main = importlib.import_module("etl_main")

    try:
        etl_main.configure_logging()
        logging.getLogger("data_retrieval.tests").info("hello from data retrieval")
        logging.shutdown()
    finally:
        sys.modules.pop("etl_main", None)
        sys.modules.pop("config", None)

    assert "hello from data retrieval" in log_file.read_text()


def test_configure_logging_uses_local_default_file(tmp_path, monkeypatch):
    """Verify the default log file works outside Docker."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATA_RETRIEVAL_LOG_FILE", raising=False)
    monkeypatch.delenv("LOG_FILE", raising=False)
    etl_main = importlib.import_module("etl_main")

    try:
        etl_main.configure_logging()
        logging.getLogger("data_retrieval.tests").info("hello from local default")
        logging.shutdown()
    finally:
        sys.modules.pop("etl_main", None)
        sys.modules.pop("config", None)

    assert (
        "hello from local default"
        in (tmp_path / "logs" / "data_retrieval.log").read_text()
    )


def test_etl_main_runs_only_etl(monkeypatch):
    """Verify the ETL entry point stops after ETL."""
    events = []
    etl_main = importlib.import_module("etl_main")

    class ETLStub:
        def __init__(self, config):
            events.append(("etl_init", config))

        def initialize(self):
            events.append("etl_initialize")

        def run(self):
            events.append("etl_run")

    try:
        monkeypatch.setattr(
            etl_main,
            "configure_logging",
            lambda: events.append("logging"),
        )
        monkeypatch.setattr(etl_main, "AppConfig", lambda: "config")
        monkeypatch.setattr(etl_main, "ETLApp", ETLStub)

        etl_main.main()
    finally:
        sys.modules.pop("etl_main", None)
        sys.modules.pop("config", None)

    assert events == [
        "logging",
        ("etl_init", "config"),
        "etl_initialize",
        "etl_run",
    ]


def test_dashboard_data_main_runs_dashboard_export(monkeypatch):
    """Verify the dashboard entry point runs only parquet generation."""
    events = []
    dashboard_data_main = importlib.import_module("dashboard_data_main")

    class DashboardDataStub:
        def __init__(self, config):
            events.append(("dashboard_init", config))

        def run(self):
            events.append("dashboard_run")

    try:
        monkeypatch.setattr(
            dashboard_data_main,
            "configure_logging",
            lambda **kwargs: events.append(("logging", kwargs)),
        )
        monkeypatch.setattr(dashboard_data_main, "AppConfig", lambda: "config")
        monkeypatch.setattr(dashboard_data_main, "DashboardDataApp", DashboardDataStub)

        dashboard_data_main.main()
    finally:
        sys.modules.pop("dashboard_data_main", None)
        sys.modules.pop("etl_main", None)
        sys.modules.pop("config", None)

    assert events == [
        (
            "logging",
            {
                "default_log_file": "logs/dashboard_data.log",
                "log_file_env": "DASHBOARD_DATA_LOG_FILE",
            },
        ),
        ("dashboard_init", "config"),
        "dashboard_run",
    ]
