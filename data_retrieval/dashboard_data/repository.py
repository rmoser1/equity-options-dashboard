"""Repository for loading dashboard input data.

This module provides :class:`DashboardRepository`, which reads the dashboard
tables from SQLite as Polars DataFrames through the shared database helper.
"""

from database import Database
from sqlalchemy import func
from schemas.historical_price import HistoricalPrice
from schemas.interest_rate import InterestRate
from schemas.option_contract import OptionContract
from schemas.stock_info import StockInfoItem
from schemas.underlying import Underlying
from sqlmodel import select


class DashboardRepository:
    """Load dashboard datasets from the application database."""

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

    def __init__(self, db_path: str):
        """Initialize the repository.

        :param db_path: Path to the SQLite database file.
        """
        self.db = Database(db_path)

    def load_stocks(self):
        """Load underlying rows for the dashboard export."""
        return self.db.read_polars(Underlying)

    def load_stock_info(self):
        """Load stock metadata rows for the dashboard export."""
        return self.db.read_polars(StockInfoItem)

    def load_options_history(self):
        """Load the narrowed option history export columns."""
        return self.db.read_polars(OptionContract, columns=self.OPTION_HISTORY_COLUMNS)

    def latest_option_trade_date(self):
        """Return the most recent option trade date in SQLite."""
        return self.db.scalar(select(func.max(OptionContract.lastTradeDate)))

    def load_latest_options(self, last_trade_date):
        """Load option rows for one option trade date."""
        selected = [getattr(OptionContract, column) for column in self.OPTION_COLUMNS]
        return self.db.query_polars(
            select(*selected).where(OptionContract.lastTradeDate == last_trade_date)
        )

    def load_stock_prices(self):
        """Load stock price rows for the dashboard export."""
        return self.db.read_polars(HistoricalPrice, columns=self.STOCK_PRICE_COLUMNS)

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
