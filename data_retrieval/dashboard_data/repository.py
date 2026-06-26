"""Repository for loading dashboard input data.

This module provides :class:`DashboardRepository`, which reads the dashboard
tables from SQLite as Polars DataFrames through the shared database helper.
"""

from database import Database
from schemas.historical_price import HistoricalPrice
from schemas.interest_rate import InterestRate
from schemas.option_contract import OptionContract
from schemas.stock_info import StockInfoItem
from schemas.underlying import Underlying


class DashboardRepository:
    """Load dashboard datasets from the application database."""

    def __init__(self, db_path: str):
        """Initialize the repository.

        :param db_path: Path to the SQLite database file.
        """
        self.db = Database(db_path)

    def load_all(self):
        """Load all raw datasets required by the dashboard pipeline.

        :returns: Dictionary containing ``stocks``, ``stock_info``,
            ``options``, and ``stock_prices`` Polars DataFrames.
        """
        return {
            "stocks": self.db.read_polars(Underlying),
            "stock_info": self.db.read_polars(StockInfoItem),
            "interest_rates": self._latest_interest_rates(),
            "options": self.db.read_polars(
                OptionContract,
                columns=[
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
                ],
            ),
            "stock_prices": self.db.read_polars(
                HistoricalPrice,
                columns=[
                    "symbol",
                    "date",
                    "close",
                    "volume",
                ],
            ),
        }

    def _latest_interest_rates(self):
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
