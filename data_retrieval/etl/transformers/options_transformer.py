"""Transform yfinance option-chain data into SQLModel rows."""

from datetime import date

from etl.transformers.yfinance_frame_utils import (
    date_value,
    optional_bool,
    optional_float,
    optional_int,
    optional_str,
    required_float,
    row_value,
)
from schemas.option_contract import OptionContract, OptionDirection


class OptionsTransformer:
    """Convert yfinance call and put DataFrames to :class:`OptionContract` rows."""

    @staticmethod
    def transform(symbol: str, expiration: str, calls_df, puts_df) -> list[OptionContract]:
        """Transform call and put option chains for one symbol and expiration.

        :param symbol: Underlying ticker symbol.
        :param expiration: Option expiration date in ``YYYY-MM-DD`` format.
        :param calls_df: yfinance calls DataFrame.
        :param puts_df: yfinance puts DataFrame.
        :returns: List of :class:`OptionContract` rows.
        """
        calls = OptionsTransformer._convert_df(
            calls_df,
            symbol,
            expiration,
            OptionDirection.CALL,
        )
        puts = OptionsTransformer._convert_df(
            puts_df,
            symbol,
            expiration,
            OptionDirection.PUT,
        )
        return calls + puts

    @staticmethod
    def _convert_df(df, symbol: str, expiration: str, direction: OptionDirection):
        """Convert one yfinance option-chain side to contract rows.

        :param df: yfinance calls or puts DataFrame.
        :param symbol: Underlying ticker symbol.
        :param expiration: Option expiration date in ``YYYY-MM-DD`` format.
        :param direction: Option contract direction for all rows.
        :returns: List of :class:`OptionContract` rows.
        """
        if df.empty:
            return []

        expiration_date = date.fromisoformat(expiration)
        return [
            OptionContract(
                contractSymbol=row.contractSymbol,
                stockSymbol=symbol,
                expirationDate=expiration_date,
                lastTradeDate=date_value(
                    row.lastTradeDate,
                    required=True,
                ),
                strike=float(row.strike),
                direction=direction,
                lastPrice=optional_float(row_value(row, "lastPrice")),
                volume=optional_int(row.volume),
                openInterest=optional_int(row.openInterest),
                bid=optional_float(row.bid),
                ask=required_float(row_value(row, "ask")),
                change=optional_float(row_value(row, "change")),
                percentChange=optional_float(row_value(row, "percentChange")),
                impliedVolatility=optional_float(row_value(row, "impliedVolatility")),
                inTheMoney=optional_bool(row_value(row, "inTheMoney")),
                contractSize=optional_str(row_value(row, "contractSize")),
                currency=optional_str(row_value(row, "currency")),
            )
            for row in df.itertuples()
        ]
