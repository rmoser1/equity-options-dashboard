"""SQLModel schema for option contract rows.

Defines :class:`OptionContract`, which maps to the ``options`` table, and
:class:`OptionDirection`, which limits contract direction values.
"""

from datetime import date as DateType
from enum import Enum

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class OptionDirection(str, Enum):
    """Allowed option contract directions."""

    CALL = "CALL"
    PUT = "PUT"


class OptionContract(SQLModel, table=True):
    """Option contract quote and metadata.

    :param contractSymbol: Unique option contract symbol.
    :param stockSymbol: Ticker symbol for the related stock.
    :param expirationDate: Option expiration date.
    :param lastTradeDate: Last trade date for this quote.
    :param strike: Strike price.
    :param direction: Option direction, usually ``"CALL"`` or ``"PUT"``.
    :param lastPrice: Last traded option price.
    :param bid: Current bid price.
    :param ask: Required current ask price.
    :param change: Absolute price change.
    :param percentChange: Percentage price change.
    :param volume: Contract trading volume.
    :param openInterest: Open interest.
    :param impliedVolatility: Implied volatility.
    :param inTheMoney: Whether the option is in the money.
    :param contractSize: Contract size description.
    :param currency: Quote currency.
    """

    __tablename__ = "options"
    __table_args__ = (CheckConstraint("direction IN ('CALL', 'PUT')"),)

    contractSymbol: str = Field(primary_key=True)
    lastTradeDate: DateType = Field(primary_key=True)
    stockSymbol: str = Field(foreign_key="stocks.symbol")
    expirationDate: DateType
    strike: float
    direction: OptionDirection

    lastPrice: float | None = None
    bid: float | None = None
    ask: float
    change: float | None = None
    percentChange: float | None = None
    volume: int | None = None
    openInterest: int | None = None
    impliedVolatility: float | None = None
    inTheMoney: bool | None = None
    contractSize: str | None = None
    currency: str | None = None
