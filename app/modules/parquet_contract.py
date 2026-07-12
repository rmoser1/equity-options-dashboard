"""Parquet dataset contract for the Dash application."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


OPTIONS_LAST_BASE_COLUMNS = frozenset(
    {
        "contractSymbol",
        "stockSymbol",
        "lastTradeDate",
        "expirationDate",
        "strike",
        "ask",
        "volume",
        "openInterest",
        "direction",
        "lastStockPrice",
        "relativeStrikePrice",
        "relativeOptionPrice",
        "costPerContract",
        "nominalPerContract",
    }
)
OPTION_METRIC_INPUT_COLUMNS = frozenset(
    {
        "timeToExpiryYears",
        "riskFreeRate",
        "dividendYield",
    }
)
OPTION_METRIC_COLUMNS = frozenset(
    {
        "calculatedImpliedVolatility",
        "delta",
        "gamma",
        "theta",
        "vega",
        "rho",
    }
)


@dataclass(frozen=True)
class ParquetDataset:
    """Expected parquet dataset file and required columns."""

    filename: str
    required_columns: frozenset[str]


DATASETS = {
    "stocks": ParquetDataset(
        filename="stocks.parquet",
        required_columns=frozenset({"symbol", "name"}),
    ),
    "options_hist": ParquetDataset(
        filename="options_hist.parquet",
        required_columns=frozenset(
            {"contractSymbol", "lastTradeDate", "ask", "volume", "openInterest"}
        ),
    ),
    "options_last": ParquetDataset(
        filename="options_last.parquet",
        required_columns=OPTIONS_LAST_BASE_COLUMNS
        | OPTION_METRIC_INPUT_COLUMNS
        | OPTION_METRIC_COLUMNS,
    ),
    "stock_info": ParquetDataset(
        filename="stock_info.parquet",
        required_columns=frozenset(
            {"stockSymbol", "itemName", "itemValue", "itemCategory"}
        ),
    ),
    "stock_prices": ParquetDataset(
        filename="stock_prices.parquet",
        required_columns=frozenset({"symbol", "date", "close", "volume"}),
    ),
}


def load_dataset(folder: str | Path, name: str) -> pd.DataFrame:
    """Load and validate one dashboard parquet dataset.

    :param folder: Folder containing dashboard parquet files.
    :param name: Dataset key from ``DATASETS``.
    :returns: Loaded pandas DataFrame.
    :raises ValueError: If the dataset is missing required columns.
    """
    dataset = DATASETS[name]
    data = pd.read_parquet(Path(folder) / dataset.filename)
    missing = dataset.required_columns.difference(data.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"{dataset.filename} is missing columns: {missing_text}")
    return data
