"""Transform stock metadata dictionaries into SQLModel rows."""

import json

from schemas.stock_info import StockInfoItem


class StockInfoTransformer:
    """Convert yfinance stock info dictionaries to :class:`StockInfoItem` rows."""

    @staticmethod
    def transform(symbol: str, info: dict) -> list[StockInfoItem]:
        """Transform stock metadata into key-value rows.

        :param symbol: Ticker symbol.
        :param info: Stock metadata dictionary from yfinance.
        :returns: List of :class:`StockInfoItem` rows.
        """
        return [
            StockInfoItem(
                stockSymbol=symbol,
                itemName=str(key),
                itemValue=json.dumps(value),
            )
            for key, value in info.items()
        ]
