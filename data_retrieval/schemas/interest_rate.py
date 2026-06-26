"""SQLModel schema for Treasury interest-rate rows.

Defines :class:`InterestRate`, which maps to the ``interestRates`` table.
"""

from datetime import date as DateType

from sqlmodel import Field, SQLModel


class InterestRate(SQLModel, table=True):
    """Treasury yield observation used for option-pricing inputs.

    :param ticker: Provider ticker for the rate.
    :param date: Observation date.
    :param name: Human-readable rate name.
    :param rate: Decimal rate, for example ``0.0525`` for ``5.25%``.
    """

    __tablename__ = "interestRates"

    ticker: str = Field(primary_key=True)
    date: DateType = Field(primary_key=True)
    name: str
    rate: float
