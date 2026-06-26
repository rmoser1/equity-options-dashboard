"""Transform yfinance Treasury yield data into SQLModel rows."""

from etl.config.interest_rates import INTEREST_RATES
from etl.transformers.yfinance_frame_utils import date_value, normalize_download_rows
from schemas.interest_rate import InterestRate


class InterestRateTransformer:
    """Convert yfinance rate history into :class:`InterestRate` rows."""

    @classmethod
    def transform(cls, data: dict) -> list[InterestRate]:
        """Transform the latest available rate for each configured ticker.

        :param data: Dictionary containing yfinance ``data``.
        :returns: Latest non-null rate row for each ticker, with yfinance
            percent yields converted to decimal rates.
        """
        df = data["data"]
        if df.empty:
            return []

        normalized = normalize_download_rows(
            df,
            required_columns=("Close",),
            symbol=data.get("symbol"),
        )
        if normalized.empty:
            return []

        rows = []
        for ticker, group in normalized.dropna(subset=["Close"]).groupby("Ticker"):
            latest = group.sort_values("Date").iloc[-1]
            rows.append(
                InterestRate(
                    ticker=ticker,
                    name=INTEREST_RATES.get(ticker, ticker),
                    date=date_value(latest["Date"]),
                    rate=float(latest["Close"]) / 100.0,
                )
            )
        return rows
