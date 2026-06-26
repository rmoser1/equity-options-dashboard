"""SQLModel schema for aggregated option volume rows.

Defines :class:`OptionVolume`, which maps to the ``aggOptionVolume`` table.
"""

from datetime import date as DateType

from sqlmodel import Field, SQLModel


class OptionVolume(SQLModel, table=True):
    """Aggregated option volume for an underlying.

    :param symbol: Underlying ticker symbol.
    :param date: Report date for the volume value.
    :param volume: Aggregated option volume.
    """

    __tablename__ = "aggOptionVolume"

    symbol: str = Field(primary_key=True)
    date: DateType
    volume: int
