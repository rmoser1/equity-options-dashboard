"""Repository for loading dashboard input data.

This module provides :class:`DashboardRepository`, which reads the dashboard
tables from SQLite as Polars DataFrames through the shared database helper.
"""

import logging

import polars as pl

from database import Database
from dashboard_data.memory import memory_usage
from sqlalchemy import case, func
from schemas.historical_price import HistoricalPrice
from schemas.interest_rate import InterestRate
from schemas.option_contract import OptionContract
from schemas.stock_info import StockInfoItem
from schemas.underlying import Underlying
from sqlmodel import select


logger = logging.getLogger(__name__)


class DashboardRepository:
    """Load dashboard datasets from the application database."""

    STOCK_SCHEMA = {
        "symbol": pl.String,
        "name": pl.String,
    }
    STOCK_INFO_SCHEMA = {
        "stockSymbol": pl.String,
        "itemName": pl.String,
        "itemValue": pl.String,
    }
    OPTION_COLUMNS = [
        "contractSymbol",
        "stockSymbol",
        "lastTradeDate",
        "expirationDate",
        "strike",
        "ask",
        "volume",
        "openInterest",
        "contractSize",
        "direction",
    ]
    OPTION_HISTORY_COLUMNS = [
        "contractSymbol",
        "lastTradeDate",
        "ask",
        "volume",
        "openInterest",
    ]
    STOCK_PRICE_COLUMNS = [
        "symbol",
        "date",
        "close",
        "volume",
    ]
    STOCK_PRICE_SCHEMA = {
        "symbol": pl.String,
        "date": pl.Date,
        "close": pl.Float64,
        "volume": pl.Int64,
    }
    OPTION_HISTORY_SCHEMA = {
        "contractSymbol": pl.String,
        "lastTradeDate": pl.Date,
        "ask": pl.Float64,
        "volume": pl.Int64,
        "openInterest": pl.Int64,
    }
    OPTION_SCHEMA = {
        "contractSymbol": pl.String,
        "stockSymbol": pl.String,
        "lastTradeDate": pl.Date,
        "expirationDate": pl.Date,
        "strike": pl.Float64,
        "ask": pl.Float64,
        "volume": pl.Int64,
        "openInterest": pl.Int64,
        "contractSize": pl.String,
        "direction": pl.String,
    }
    LATEST_STOCK_PRICE_SCHEMA = {
        "symbol": pl.String,
        "lastStockPrice": pl.Float64,
    }

    def __init__(self, db_path: str):
        """Initialize the repository.

        :param db_path: Path to the SQLite database file.
        """
        self.db = Database(db_path)

    def load_stocks(self):
        """Load underlying rows for the dashboard export."""
        return self.db.read_polars(Underlying)

    def iter_stocks(self, batch_size: int):
        """Yield underlying rows in database batches."""
        return self._iter_keyset_batches(
            "stocks",
            lambda after, limit: self._stocks_statement(after=after, limit=limit),
            batch_size,
            self.STOCK_SCHEMA,
            ["symbol"],
        )

    def load_stock_info(self, item_names: list[str]):
        """Load only the requested stock metadata rows."""
        stock_info = self.db.query_polars(
            self._stock_info_statement(item_names)
        )
        return stock_info.cast(self.STOCK_INFO_SCHEMA)

    def iter_stock_info(self, item_names: list[str], batch_size: int):
        """Yield requested stock metadata rows in database batches."""
        return self._iter_keyset_batches(
            "stock_info",
            lambda after, limit: self._stock_info_statement(
                item_names,
                after=after,
                limit=limit,
            ),
            batch_size,
            self.STOCK_INFO_SCHEMA,
            ["stockSymbol", "itemName"],
        )

    @staticmethod
    def empty_stocks() -> pl.DataFrame:
        """Return an empty stocks frame with the repository schema."""
        return pl.DataFrame(schema=DashboardRepository.STOCK_SCHEMA)

    @staticmethod
    def empty_stock_info() -> pl.DataFrame:
        """Return an empty stock-info frame with the repository schema."""
        return pl.DataFrame(schema=DashboardRepository.STOCK_INFO_SCHEMA)

    @staticmethod
    def empty_stock_prices() -> pl.DataFrame:
        """Return an empty stock-prices frame with the repository schema."""
        return pl.DataFrame(schema=DashboardRepository.STOCK_PRICE_SCHEMA)

    @staticmethod
    def empty_options_history() -> pl.DataFrame:
        """Return an empty option-history frame with the repository schema."""
        return pl.DataFrame(schema=DashboardRepository.OPTION_HISTORY_SCHEMA)

    @staticmethod
    def empty_latest_options() -> pl.DataFrame:
        """Return an empty latest-options frame with the repository schema."""
        return pl.DataFrame(schema=DashboardRepository.OPTION_SCHEMA)

    @staticmethod
    def empty_latest_stock_prices() -> pl.DataFrame:
        """Return an empty latest stock-price frame with the repository schema."""
        return pl.DataFrame(schema=DashboardRepository.LATEST_STOCK_PRICE_SCHEMA)

    @staticmethod
    def _stocks_statement(after: tuple[str] | None = None, limit: int | None = None):
        """Build a batched stocks select."""
        statement = select(Underlying.symbol, Underlying.name).order_by(Underlying.symbol)
        if after is not None:
            statement = statement.where(Underlying.symbol > after[0])
        if limit is not None:
            statement = statement.limit(limit)
        return statement

    @staticmethod
    def _stock_info_statement(
        item_names: list[str],
        after: tuple[str, str] | None = None,
        limit: int | None = None,
    ):
        """Build the stock-info select used by full and batched loaders."""
        item_order_map = {
            item_name: index
            for index, item_name in enumerate(item_names)
        }
        item_order = case(item_order_map, value=StockInfoItem.itemName)
        statement = (
            select(
                StockInfoItem.stockSymbol,
                StockInfoItem.itemName,
                StockInfoItem.itemValue,
            )
            .where(StockInfoItem.itemName.in_(item_names))
            .order_by(StockInfoItem.stockSymbol, item_order)
        )
        if after is not None:
            stock_symbol, item_name = after
            statement = statement.where(
                (StockInfoItem.stockSymbol > stock_symbol)
                | (
                    (StockInfoItem.stockSymbol == stock_symbol)
                    & (item_order > item_order_map[item_name])
                )
            )
        if limit is not None:
            statement = statement.limit(limit)
        return statement

    def load_options_history(self):
        """Load the narrowed option history export columns."""
        return self.db.read_polars(OptionContract, columns=self.OPTION_HISTORY_COLUMNS)

    def iter_options_history(self, batch_size: int):
        """Yield narrowed option history rows in database batches."""
        return self._iter_keyset_batches(
            "options_hist",
            lambda after, limit: self._options_history_statement(
                after=after,
                limit=limit,
            ),
            batch_size,
            self.OPTION_HISTORY_SCHEMA,
            ["lastTradeDate", "contractSymbol"],
        )

    def latest_option_trade_date(self):
        """Return the most recent option trade date in SQLite."""
        return self.db.scalar(select(func.max(OptionContract.lastTradeDate)))

    def load_latest_options(self, last_trade_date):
        """Load option rows for one option trade date."""
        selected = [getattr(OptionContract, column) for column in self.OPTION_COLUMNS]
        return self.db.query_polars(
            select(*selected).where(OptionContract.lastTradeDate == last_trade_date)
        )

    def iter_latest_options(self, last_trade_date, batch_size: int):
        """Yield option rows for one option trade date in database batches."""
        return self._iter_keyset_batches(
            "options_last",
            lambda after, limit: self._latest_options_statement(
                last_trade_date,
                after=after,
                limit=limit,
            ),
            batch_size,
            self.OPTION_SCHEMA,
            ["contractSymbol"],
        )

    def load_stock_prices(self):
        """Load stock price rows for the dashboard export."""
        return self.db.read_polars(HistoricalPrice, columns=self.STOCK_PRICE_COLUMNS)

    def iter_stock_prices(self, batch_size: int):
        """Yield stock price rows in database batches."""
        return self._iter_keyset_batches(
            "stock_prices",
            lambda after, limit: self._stock_prices_statement(after=after, limit=limit),
            batch_size,
            self.STOCK_PRICE_SCHEMA,
            ["date", "symbol"],
        )

    def load_latest_stock_prices(self, last_trade_date):
        """Load stock close prices for one trade date."""
        return self.db.query_polars(
            select(
                HistoricalPrice.symbol,
                HistoricalPrice.close.label("lastStockPrice"),
            ).where(HistoricalPrice.date == last_trade_date)
        )

    def load_interest_rates(self):
        """Load the latest available observation for each interest-rate ticker."""
        return self.db.query_polars(
            f"""
            SELECT ir.ticker, ir.name, ir.date, ir.rate
            FROM {InterestRate.__tablename__} AS ir
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM {InterestRate.__tablename__}
                GROUP BY ticker
            ) latest
                ON ir.ticker = latest.ticker
                AND ir.date = latest.max_date
            """
        )

    def _iter_keyset_batches(
        self,
        dataset_name: str,
        statement_factory,
        batch_size: int,
        schema: dict[str, pl.DataType],
        cursor_columns: list[str],
    ):
        """Yield query results in SQL-level keyset batches."""
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")

        batch_number = 0
        cursor = None
        while True:
            logger.info(
                "Loading %s batch %s after=%s limit=%s %s",
                dataset_name,
                batch_number + 1,
                cursor,
                batch_size,
                memory_usage(),
            )
            batch = self.db.query_polars(
                statement_factory(cursor, batch_size)
            ).cast(schema)
            if batch.is_empty():
                logger.info(
                    "No more %s batches after %s batches %s",
                    dataset_name,
                    batch_number,
                    memory_usage(),
                )
                break

            batch_number += 1
            last_row = batch.select(cursor_columns).tail(1).to_dicts()[0]
            cursor = tuple(last_row[column] for column in cursor_columns)
            logger.info(
                "Loaded %s batch %s rows=%s last=%s %s",
                dataset_name,
                batch_number,
                batch.height,
                cursor,
                memory_usage(),
            )
            yield batch

            if batch.height < batch_size:
                logger.info(
                    "Completed %s batches total_batches=%s %s",
                    dataset_name,
                    batch_number,
                    memory_usage(),
                )
                break

    @staticmethod
    def _options_history_statement(
        after: tuple | None = None,
        limit: int | None = None,
    ):
        """Build a batched option-history select."""
        selected = [
            getattr(OptionContract, column)
            for column in DashboardRepository.OPTION_HISTORY_COLUMNS
        ]
        statement = select(*selected).order_by(
            OptionContract.lastTradeDate,
            OptionContract.contractSymbol,
        )
        if after is not None:
            last_trade_date, contract_symbol = after
            statement = statement.where(
                (OptionContract.lastTradeDate > last_trade_date)
                | (
                    (OptionContract.lastTradeDate == last_trade_date)
                    & (OptionContract.contractSymbol > contract_symbol)
                )
            )
        if limit is not None:
            statement = statement.limit(limit)
        return statement

    @staticmethod
    def _latest_options_statement(
        last_trade_date,
        after: tuple[str] | None = None,
        limit: int | None = None,
    ):
        """Build a batched latest-options select."""
        selected = [
            getattr(OptionContract, column)
            for column in DashboardRepository.OPTION_COLUMNS
        ]
        statement = (
            select(*selected)
            .where(OptionContract.lastTradeDate == last_trade_date)
            .order_by(OptionContract.contractSymbol)
        )
        if after is not None:
            statement = statement.where(OptionContract.contractSymbol > after[0])
        if limit is not None:
            statement = statement.limit(limit)
        return statement

    @staticmethod
    def _stock_prices_statement(
        after: tuple | None = None,
        limit: int | None = None,
    ):
        """Build a batched stock-prices select."""
        selected = [
            getattr(HistoricalPrice, column)
            for column in DashboardRepository.STOCK_PRICE_COLUMNS
        ]
        statement = select(*selected).order_by(
            HistoricalPrice.date,
            HistoricalPrice.symbol,
        )
        if after is not None:
            price_date, symbol = after
            statement = statement.where(
                (HistoricalPrice.date > price_date)
                | (
                    (HistoricalPrice.date == price_date)
                    & (HistoricalPrice.symbol > symbol)
                )
            )
        if limit is not None:
            statement = statement.limit(limit)
        return statement
