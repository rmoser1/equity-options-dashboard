"""Callbacks for option metric views."""

from io import StringIO

from dash import Dash, Input, Output
import pandas as pd

from config import DEFAULT_FONT_SIZES, FontSizeConfig
from modules.components import ComponentGroups
from modules.plotly_figures.option_metrics import metric_heatmaps


def register_option_metric_callbacks(
    app: Dash,
    components: ComponentGroups,
    data: dict,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> None:
    """Register option-metric callbacks.

    :param app: Dash app instance.
    :param components: Named dashboard component groups.
    :param data: Dashboard app data.
    :param font_sizes: Dashboard font-size scale.
    """
    _register_metric_heatmaps_callback(app, components, font_sizes)


def _register_metric_heatmaps_callback(
    app: Dash,
    components: ComponentGroups,
    font_sizes: FontSizeConfig,
) -> None:
    """Register the option metric heatmap callback."""

    @app.callback(
        output=dict(
            implied_volatility=Output(
                components.charts.implied_volatility_metric,
                "figure",
            ),
            delta=Output(components.charts.delta_metric, "figure"),
            gamma=Output(components.charts.gamma_metric, "figure"),
            theta=Output(components.charts.theta_metric, "figure"),
            vega=Output(components.charts.vega_metric, "figure"),
            rho=Output(components.charts.rho_metric, "figure"),
        ),
        inputs=dict(
            df=Input(components.store.filtered_options_single_stock, "data"),
            axis_mode=Input(components.filters.metric_axis_mode, "value"),
        ),
    )
    def option_metric_heatmaps_callback(df, axis_mode):
        df = _read_store(df)
        stock = df.loc[0, "stockSymbol"] if not df.empty else ""
        figures = metric_heatmaps(df, stock, axis_mode, font_sizes)
        return dict(
            implied_volatility=figures[0],
            delta=figures[1],
            gamma=figures[2],
            theta=figures[3],
            vega=figures[4],
            rho=figures[5],
        )


def _read_store(data: str | None) -> pd.DataFrame:
    """Read a JSON store payload into a DataFrame."""
    if not data:
        return pd.DataFrame()
    df = pd.read_json(StringIO(data), orient="split")
    for column in ["expirationDate", "lastTradeDate"]:
        if column in df:
            unit = "ms" if pd.api.types.is_numeric_dtype(df[column]) else None
            df[column] = pd.to_datetime(df[column], unit=unit)
    return df
