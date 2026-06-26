"""Callbacks for stock price history charts."""

from dash import Dash, Input, Output
import pandas as pd

from config import DEFAULT_FONT_SIZES, FontSizeConfig
from modules.components import ComponentGroups
from modules.plotly_figures.stock_prices import stock_time_series


def register_stock_price_callbacks(
    app: Dash,
    components: ComponentGroups,
    data: dict,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> None:
    """Register stock-price callbacks.

    :param app: Dash app instance.
    :param components: Named dashboard component groups.
    :param data: Dashboard app data.
    :param font_sizes: Dashboard font-size scale.
    """
    stock_prices = data["stock_prices_df"]

    @app.callback(
        output=dict(
            stockPriceVolumeGraph=Output(
                components.charts.stock_time_series,
                "figure",
            ),
        ),
        inputs=dict(
            selected_stock=Input(
                components.filters.stock_price_stock_selection,
                "value",
            ),
            selected_range=Input(
                components.filters.stock_price_range,
                "value",
            ),
        ),
    )
    def stockPriceVolumeGraph_callback(selected_stock, selected_range):
        plot_data = stock_prices.loc[stock_prices["symbol"] == selected_stock, :]
        plot_data = _filter_price_range(plot_data, selected_range)
        return dict(
            stockPriceVolumeGraph=stock_time_series(
                df=plot_data,
                symbol=selected_stock,
                font_sizes=font_sizes,
            )
        )


def _filter_price_range(df: pd.DataFrame, selected_range: str) -> pd.DataFrame:
    """Return stock prices inside the selected lookback window."""
    if df.empty or selected_range == "max":
        return df

    offsets = {
        "1m": pd.DateOffset(months=1),
        "1y": pd.DateOffset(years=1),
        "5y": pd.DateOffset(years=5),
    }
    offset = offsets.get(selected_range)
    if offset is None:
        return df

    dates = pd.to_datetime(df["date"])
    start = dates.max() - offset
    return df.loc[dates >= start, :]
