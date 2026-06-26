"""Transform yfinance historical price data into SQLModel rows."""

from etl.transformers.yfinance_frame_utils import date_value, normalize_download_rows
from schemas.historical_price import (
    HistoricalPrice,
)


class HistoricalTransformer:
    """Convert yfinance history DataFrames to :class:`HistoricalPrice` rows."""

    REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")

    @staticmethod
    def transform(df, symbol: str | None = None):
        """Transform a yfinance historical price DataFrame.

        :param df: yfinance history DataFrame with price fields by ticker.
        :param symbol: Ticker symbol for flat single-symbol DataFrames.
        :returns: List of :class:`HistoricalPrice` rows.
        """
        if df.empty:
            return []

        df = normalize_download_rows(
            df,
            required_columns=HistoricalTransformer.REQUIRED_COLUMNS,
            symbol=symbol,
        )
        df = df.dropna(subset=HistoricalTransformer.REQUIRED_COLUMNS)

        return [
            HistoricalPrice(
                date=date_value(row.Date),
                symbol=row.Ticker,
                open=float(row.Open),
                high=float(row.High),
                low=float(row.Low),
                close=float(row.Close),
                volume=int(row.Volume),
            )
            for row in df.itertuples()
        ]
