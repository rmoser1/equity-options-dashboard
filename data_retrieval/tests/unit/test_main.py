"""Tests for the data retrieval entry point."""

import importlib
import logging
import sys


def test_configure_logging_writes_to_configured_file(tmp_path, monkeypatch):
    """Verify data retrieval logging can be directed to a bind-mounted file."""
    log_file = tmp_path / "logs" / "data_retrieval.log"
    monkeypatch.setenv("DATA_RETRIEVAL_LOG_FILE", str(log_file))
    main = importlib.import_module("main")

    try:
        main.configure_logging()
        logging.getLogger("data_retrieval.tests").info("hello from data retrieval")
        logging.shutdown()
    finally:
        sys.modules.pop("main", None)
        sys.modules.pop("config", None)

    assert "hello from data retrieval" in log_file.read_text()


def test_configure_logging_uses_local_default_file(tmp_path, monkeypatch):
    """Verify the default log file works outside Docker."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATA_RETRIEVAL_LOG_FILE", raising=False)
    monkeypatch.delenv("LOG_FILE", raising=False)
    main = importlib.import_module("main")

    try:
        main.configure_logging()
        logging.getLogger("data_retrieval.tests").info("hello from local default")
        logging.shutdown()
    finally:
        sys.modules.pop("main", None)
        sys.modules.pop("config", None)

    assert (
        "hello from local default"
        in (tmp_path / "logs" / "data_retrieval.log").read_text()
    )
