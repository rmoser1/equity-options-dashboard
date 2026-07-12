"""Dashboard data transformation utilities."""

import json
from datetime import datetime

import polars as pl

from dashboard_data.info_item_fields import (
    DIVIDEND_YIELD_NAMES,
    FIELDS_BY_CATEGORY,
    FIELDS_DATE,
    FIELDS_NUMERIC,
    FIELDS_STRING,
    INFO_ITEM_NAMES,
)


class DashboardTransformer:
    """Build derived dashboard datasets from narrowed repository output."""

    @staticmethod
    def transform_info_items(stock_info: pl.DataFrame) -> pl.DataFrame:
        """Select, categorize, and display-format configured stock information."""
        categories = pl.DataFrame(
            {
                "itemName": INFO_ITEM_NAMES,
                "itemCategory": [
                    category
                    for category, item_names in FIELDS_BY_CATEGORY.items()
                    for _ in item_names
                ],
            }
        )
        return (
            stock_info
            .join(
                categories,
                on="itemName",
                how="inner",
                maintain_order="left",
            )
            .with_columns(
                pl.struct(["itemName", "itemValue"])
                .map_elements(
                    DashboardTransformer._format_info_item_value,
                    return_dtype=pl.String,
                )
                .alias("itemValue")
            )
            .select("stockSymbol", "itemName", "itemValue", "itemCategory")
        )

    @staticmethod
    def transform_options_last(
        options: pl.DataFrame,
        last_stock_price: pl.DataFrame,
        stock_info: pl.DataFrame,
        interest_rates: pl.DataFrame,
    ) -> pl.DataFrame:
        """Build the enriched latest-options export.

        Joins each latest option row to its underlying close price and
        dividend yield, then adds:

        - ``lastStockPrice``: underlying close price on the option trade date.
        - ``timeToExpiryYears``: calendar days from trade date to expiration,
          expressed in years.
        - ``riskFreeRate``: interpolated decimal Treasury rate for the option's
          time to expiry.
        - ``dividendYield``: decimal dividend yield from stock metadata,
          defaulting to ``0.0`` when unavailable.
        - ``relativeStrikePrice``: strike divided by latest underlying price.
        - ``relativeOptionPrice``: ask divided by latest underlying price.
        - ``costPerContract``: ask price multiplied by 100 for regular contracts.
        - ``nominalPerContract``: underlying notional value for regular contracts.

        :param options: Latest option rows for the current trade date.
        :param last_stock_price: Underlying close prices aligned to that trade date.
        :param stock_info: Key-value stock metadata containing optional dividend yields.
        :param interest_rates: Latest Treasury yield anchors used for risk-free rates.
        :returns: Enriched latest option rows for dashboard and metrics exports.
        """
        regular_contract = pl.col("contractSize") == "REGULAR"
        time_to_expiry_years = (
            (pl.col("expirationDate") - pl.col("lastTradeDate"))
            .dt.total_days()
            / 365.0
        ).round(6)
        dividend_yields = DashboardTransformer._dividend_yields(stock_info)

        return (
            options
            .join(
                last_stock_price,
                left_on="stockSymbol",
                right_on="symbol",
                how="left",
            )
            .join(
                dividend_yields,
                on="stockSymbol",
                how="left",
            )
            .with_columns(
                time_to_expiry_years.alias("timeToExpiryYears")
            )
            .with_columns(
                [
                    DashboardTransformer._risk_free_rate_expr(
                        interest_rates,
                        pl.col("timeToExpiryYears"),
                    ).alias("riskFreeRate"),
                    pl.col("dividendYield").fill_null(0.0),
                    (pl.col("strike") / pl.col("lastStockPrice"))
                    .round(4)
                    .alias("relativeStrikePrice"),
                    (pl.col("ask") / pl.col("lastStockPrice"))
                    .round(4)
                    .alias("relativeOptionPrice"),
                    pl.when(regular_contract)
                    .then((pl.col("ask") * 100).round(0))
                    .otherwise(None)
                    .alias("costPerContract"),
                    pl.when(regular_contract)
                    .then((pl.col("lastStockPrice") * 100).round(0))
                    .otherwise(None)
                    .alias("nominalPerContract"),
                    pl.col("lastStockPrice").round(2),
                ]
            )
        )

    @staticmethod
    def _dividend_yields(stock_info: pl.DataFrame) -> pl.DataFrame:
        """Return per-symbol dividend yields from stock-info rows."""
        return (
            stock_info
            .filter(pl.col("itemName").is_in(DIVIDEND_YIELD_NAMES))
            .with_columns(
                pl.col("itemValue")
                .cast(pl.Utf8)
                .str.strip_chars('"')
                .cast(pl.Float64, strict=False)
                .fill_null(0.0)
                .alias("dividendYield")
            )
            .select([pl.col("stockSymbol"), pl.col("dividendYield")])
            .unique(subset=["stockSymbol"], keep="last")
        )

    @staticmethod
    def _format_info_item_value(item: dict) -> str | None:
        """Decode and display-format one serialized stock-info value."""
        value = json.loads(item["itemValue"])
        if value is None:
            return None
        if item["itemName"] in FIELDS_NUMERIC:
            return f"{float(value):,.2f}".rstrip("0").rstrip(".")
        if item["itemName"] in FIELDS_DATE:
            return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
        if item["itemName"] in FIELDS_STRING:
            return str(value)
        raise ValueError(f"Missing stock-info field type: {item['itemName']}")

    @staticmethod
    def _risk_free_rate_expr(
        interest_rates: pl.DataFrame,
        time_to_expiry_years: pl.Expr,
    ) -> pl.Expr:
        """Return vectorized risk-free-rate interpolation expression.

        :param interest_rates: Latest Treasury yield anchors.
        :param time_to_expiry_years: Per-row option maturity expression in years.
        :returns: Per-row decimal risk-free rate expression.
        """
        short_rate = DashboardTransformer._rate_for_ticker(interest_rates, "^IRX")
        long_rate = DashboardTransformer._rate_for_ticker(interest_rates, "^FVX")

        if short_rate is None:
            raise ValueError("Missing required interest rate: ^IRX")
        if long_rate is None:
            raise ValueError("Missing required interest rate: ^FVX")

        short_maturity = 13 / 52
        long_maturity = 5.0
        maturity = time_to_expiry_years.clip(short_maturity, long_maturity)
        slope = (long_rate - short_rate) / (long_maturity - short_maturity)
        return (pl.lit(short_rate) + (maturity - short_maturity) * slope).round(6)

    @staticmethod
    def _rate_for_ticker(interest_rates: pl.DataFrame, ticker: str) -> float | None:
        """Return one interest rate for ``ticker`` if available."""
        row = interest_rates.filter(pl.col("ticker") == ticker).select("rate").head(1)
        if row.is_empty():
            return None
        return row.item()
