"""SQLModel schema for historical stock price rows.

Defines :class:`HistoricalPrice`, which maps to the ``stockPrices`` table.
"""

from datetime import date as DateType

from sqlmodel import Field, SQLModel


class HistoricalPrice(SQLModel, table=True):
    """Historical OHLCV price row for an underlying.

    :param date: Price date.
    :param symbol: Underlying ticker symbol.
    :param open: Opening price.
    :param high: Highest price.
    :param low: Lowest price.
    :param close: Closing price.
    :param volume: Trading volume.
    """

    __tablename__ = "stockPrices"

    date: DateType = Field(primary_key=True)
    symbol: str = Field(primary_key=True, foreign_key="stocks.symbol")

    open: float
    high: float
    low: float
    close: float
    volume: int
