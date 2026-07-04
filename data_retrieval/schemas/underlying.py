"""SQLModel schema for stock and ETF underlyings.

Defines :class:`Underlying`, which maps to the ``stocks`` table.
"""

from sqlmodel import Field, SQLModel


class Underlying(SQLModel, table=True):
    """Tradable stock or ETF underlying.

    :param symbol: Unique ticker symbol.
    :param name: Display name for the underlying.
    """

    __tablename__ = "stocks"

    symbol: str = Field(primary_key=True)
    name: str
