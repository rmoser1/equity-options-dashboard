"""Load and prepare parquet-backed data for the Dash application."""

import logging

import pandas as pd

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

    logger.info("Preparing stock info controls")

    info_items = stock_info[["itemCategory", "itemName"]].drop_duplicates()
    info_items_by_category = {
        category: rows["itemName"].tolist()
        for category, rows in info_items.groupby("itemCategory", sort=False)
    }
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
    cost_per_contract_range = [
        options_last["costPerContract"].min(),
        options_last["costPerContract"].max(),
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
        "cost_per_contract_range": cost_per_contract_range,
        "info_items_by_category": info_items_by_category,
        "info_items_categories": list(info_items_by_category),
    }
