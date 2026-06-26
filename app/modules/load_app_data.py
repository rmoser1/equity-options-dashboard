"""Load and prepare parquet-backed data for the Dash application."""

import json
import logging
from datetime import datetime

import pandas as pd

from modules.info_item_fields import (
    FIELDS_BY_CATEGORY,
    FIELDS_DATE,
    FIELDS_NUMERIC,
    FIELDS_STRING,
)
from modules.parquet_contract import load_dataset


logger = logging.getLogger(__name__)


def load_app_data(parquet_folder: str = "data/parquet") -> dict:
    """Load parquet-backed data and derive dashboard component inputs."""
    logger.info("Loading dataframes from parquet")

    stocks = load_dataset(parquet_folder, "stocks")
    options_hist = load_dataset(parquet_folder, "options_hist")
    options_last = load_dataset(parquet_folder, "options_last")
    stock_info = load_dataset(parquet_folder, "stock_info")
    stock_prices = load_dataset(parquet_folder, "stock_prices")

    logger.info("Transforming stock info data")

    info_items = FIELDS_NUMERIC + FIELDS_DATE + FIELDS_STRING
    stock_info["itemValue"] = stock_info["itemValue"].apply(json.loads)
    stock_info = stock_info[stock_info["itemName"].isin(info_items)]
    numeric_mask = stock_info["itemName"].isin(FIELDS_NUMERIC)
    date_mask = stock_info["itemName"].isin(FIELDS_DATE)
    stock_info.loc[numeric_mask, "itemValue"] = stock_info.loc[
        numeric_mask,
        "itemValue",
    ].map(_format_numeric_info_value)
    stock_info.loc[date_mask, "itemValue"] = stock_info.loc[
        date_mask,
        "itemValue",
    ].map(_format_date_info_value)

    logger.info("Creating custom data for components and callbacks")

    expiration_dates = pd.to_datetime(options_last["expirationDate"])
    expiration_dates = expiration_dates.drop_duplicates().sort_values()
    expiration_options = [
        {"label": date.strftime("%Y-%m-%d"), "value": date}
        for date in expiration_dates
    ]

    stocks_sorted = stocks.sort_values("name")
    stock_options = [
        {"label": row.name, "value": row.symbol}
        for row in stocks_sorted.itertuples(index=False)
    ]

    relative_strike_price_range = [
        options_last["relativeStrikePrice"].min(),
        options_last["relativeStrikePrice"].max(),
    ]

    logger.info("Returning dashboard app data")

    return {
        "options_hist_df": options_hist,
        "options_last_df": options_last,
        "stock_info_df": stock_info,
        "stock_prices_df": stock_prices,
        "last_trade_date": pd.to_datetime(options_last.loc[0, "lastTradeDate"]).strftime(
            "%Y-%m-%d"
        ),
        "expiration_dates_datetime": [
            option["value"] for option in expiration_options
        ],
        "expiration_dates_dict": expiration_options,
        "stock_tickers_dict": stock_options,
        "relative_strike_price_range": relative_strike_price_range,
        "info_items_by_category": FIELDS_BY_CATEGORY,
        "info_items_categories": list(FIELDS_BY_CATEGORY.keys()),
    }


def _format_numeric_info_value(value) -> str:
    """Format a numeric stock-info value for display."""
    return f"{float(value):,.2f}".rstrip("0").rstrip(".")


def _format_date_info_value(value) -> str:
    """Format a Unix timestamp stock-info value for display."""
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
