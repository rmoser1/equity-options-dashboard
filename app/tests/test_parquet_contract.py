"""Tests for dashboard parquet dataset contracts."""

import pandas as pd
import pytest

from modules.parquet_contract import DATASETS, load_dataset


def test_load_dataset_returns_valid_parquet(dashboard_parquet_dir):
    """Verify a dataset with the required columns loads successfully."""
    data = load_dataset(dashboard_parquet_dir, "options_last")

    assert set(DATASETS["options_last"].required_columns).issubset(data.columns)
    assert data["contractSymbol"].tolist() == [
        "SPY260717C00500000",
        "SPY260821C00510000",
        "SPY260717P00490000",
        "MSFT260717C00350000",
    ]


def test_load_dataset_reports_missing_required_columns(dashboard_parquet_dir):
    """Verify missing parquet columns fail with the dataset filename."""
    pd.DataFrame({"contractSymbol": ["SPY260717C00500000"]}).to_parquet(
        dashboard_parquet_dir / "options_last.parquet",
        index=False,
    )

    with pytest.raises(ValueError, match="options_last.parquet is missing columns"):
        load_dataset(dashboard_parquet_dir, "options_last")


def test_options_last_contract_requires_metric_columns():
    """Verify the app contract includes downstream option metric fields."""
    required_columns = DATASETS["options_last"].required_columns

    assert {
        "timeToExpiryYears",
        "riskFreeRate",
        "dividendYield",
        "calculatedImpliedVolatility",
        "delta",
        "gamma",
        "theta",
        "vega",
        "rho",
    }.issubset(required_columns)


def test_stock_info_contract_requires_selector_metadata():
    """Require category metadata in the stock-info dataset."""
    assert "itemCategory" in DATASETS["stock_info"].required_columns
