"""Tests for the :mod:`schemas.option_contract` module."""

from datetime import date

from schemas.option_contract import OptionContract, OptionDirection


def test_option_contract_table_enum_and_fields():
    """Ensure option contract table metadata, enums, and fields are mapped."""

    row = OptionContract(
        contractSymbol="AAPL260116C00100000",
        lastTradeDate=date(2026, 1, 2),
        stockSymbol="AAPL",
        expirationDate=date(2026, 1, 16),
        strike=100.0,
        direction=OptionDirection.CALL,
        ask=1.2,
    )

    assert OptionContract.__tablename__ == "options"
    assert OptionDirection.CALL.value == "CALL"
    assert OptionDirection.PUT.value == "PUT"
    assert row.direction == OptionDirection.CALL
    assert row.ask == 1.2
