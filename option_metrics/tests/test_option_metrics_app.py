"""Tests for :mod:`option_metrics.app`."""

import logging

import pandas as pd

from option_metrics.app import OptionMetricsApp
from option_metrics.main import configure_logging


def _options_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timeToExpiryYears": 30 / 365,
                "strike": 100.0,
                "ask": 2.898810513716974,
                "direction": "CALL",
                "lastStockPrice": 100.0,
                "riskFreeRate": 0.01,
                "dividendYield": 0.0,
            }
        ]
    )


def test_app_enriches_options_last_under_dashboard_data_dir(tmp_path, monkeypatch):
    """Verify the app overwrites ``options_last.parquet`` with metrics."""
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir()
    _options_frame().to_parquet(parquet_dir / "options_last.parquet", index=False)
    monkeypatch.setenv("DASHBOARD_DATA_DIR", str(parquet_dir))

    result = OptionMetricsApp().run()

    written = pd.read_parquet(parquet_dir / "options_last.parquet")
    assert result.loc[0, "calculatedImpliedVolatility"] > 0
    assert written["calculatedImpliedVolatility"].tolist() == result[
        "calculatedImpliedVolatility"
    ].tolist()
    assert not (parquet_dir / "options_last.parquet.tmp").exists()
    assert not (parquet_dir / "options_metrics.parquet").exists()


def test_configure_logging_writes_to_configured_file(tmp_path, monkeypatch):
    """Verify metrics logging can be directed to a bind-mounted file."""
    log_file = tmp_path / "logs" / "option_metrics.log"
    monkeypatch.setenv("OPTION_METRICS_LOG_FILE", str(log_file))

    configure_logging()
    logging.getLogger("option_metrics.tests").info("hello from option metrics")
    logging.shutdown()

    assert "hello from option metrics" in log_file.read_text()


def test_configure_logging_uses_local_default_file(tmp_path, monkeypatch):
    """Verify metrics logging always has a local file fallback."""
    work_dir = tmp_path / "option_metrics"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
    monkeypatch.delenv("OPTION_METRICS_LOG_FILE", raising=False)
    monkeypatch.delenv("LOG_FILE", raising=False)

    configure_logging()
    logging.getLogger("option_metrics.tests").info("hello from local default")
    logging.shutdown()

    assert (
        "hello from local default"
        in (tmp_path / "logs" / "option_metrics.log").read_text()
    )
