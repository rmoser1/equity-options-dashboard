"""SQLModel schema for stock information key-value rows.

Defines :class:`StockInfoItem`, which maps to the ``stockInfo`` table.
"""

from sqlmodel import Field, SQLModel


class StockInfoItem(SQLModel, table=True):
    """Single key-value stock information item.

    :param stockSymbol: Ticker symbol for the related stock.
    :param itemName: Name of the stock information item.
    :param itemValue: Serialized value for the stock information item.
    """

    __tablename__ = "stockInfo"

    stockSymbol: str = Field(primary_key=True, foreign_key="stocks.symbol")
    itemName: str = Field(primary_key=True)
    itemValue: str
