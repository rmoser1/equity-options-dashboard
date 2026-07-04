"""Plotly figure builders for option metric views."""

import pandas as pd
import plotly.graph_objects as go

from config import DEFAULT_FONT_SIZES, FontSizeConfig
from modules.plotly_figures.style import apply_readable_style


METRIC_COLUMNS = (
    "calculatedImpliedVolatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "rho",
)
METRIC_TITLES = {
    "calculatedImpliedVolatility": "Implied Volatility",
    "delta": "Delta",
    "gamma": "Gamma",
    "theta": "Theta",
    "vega": "Vega",
    "rho": "Rho",
}
AXIS_MODES = {
    "expiration_strike": {
        "x": "expirationDate",
        "y": "strike",
        "x_title": "Expiration",
        "y_title": "Strike",
    },
    "time_relative_strike": {
        "x": "timeToExpiryYears",
        "y": "relativeStrikePrice",
        "x_title": "Years to expiry",
        "y_title": "Relative strike",
    },
}


def metric_heatmaps(
    df: pd.DataFrame,
    stock: str,
    axis_mode: str,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> tuple[go.Figure, ...]:
    """Create option metric heatmaps for one stock.

    :param df: Filtered single-stock options DataFrame.
    :param stock: Stock symbol shown in chart titles.
    :param axis_mode: Heatmap axis mode key from ``AXIS_MODES``.
    :param font_sizes: Dashboard font-size scale.
    :returns: Figures ordered as implied volatility, delta, gamma, theta, vega, rho.
    """
    axes = AXIS_MODES.get(axis_mode, AXIS_MODES["expiration_strike"])
    return tuple(
        _metric_heatmap(df, stock, metric, axes, font_sizes)
        for metric in METRIC_COLUMNS
    )


def _metric_heatmap(
    df: pd.DataFrame,
    stock: str,
    metric: str,
    axes: dict[str, str],
    font_sizes: FontSizeConfig,
) -> go.Figure:
    """Create one option metric heatmap."""
    if df.empty:
        return _empty_metric_figure(METRIC_TITLES[metric], font_sizes)

    plot_data = df[[axes["x"], axes["y"], metric]].copy()
    if axes["x"] == "expirationDate":
        plot_data[axes["x"]] = pd.to_datetime(plot_data[axes["x"]]).dt.strftime(
            "%Y-%m-%d"
        )
    else:
        plot_data[axes["x"]] = plot_data[axes["x"]].round(4)
    if axes["y"] == "relativeStrikePrice":
        plot_data[axes["y"]] = plot_data[axes["y"]].round(4)

    pivoted = plot_data.pivot_table(
        index=axes["y"],
        columns=axes["x"],
        values=metric,
        aggfunc="mean",
    ).sort_index()

    fig = go.Figure(
        data=go.Heatmap(
            z=pivoted.values,
            x=pivoted.columns,
            y=pivoted.index,
            colorscale="Viridis",
            xgap=1,
            ygap=1,
            colorbar={"title": METRIC_TITLES[metric]},
            hovertemplate=(
                f"{axes['x_title']}: "
                "%{x}<br>"
                f"{axes['y_title']}: "
                "%{y}<br>"
                f"{METRIC_TITLES[metric]}: "
                "%{z:.4f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=f"{METRIC_TITLES[metric]} - {stock}",
        xaxis_title=axes["x_title"],
        yaxis_title=axes["y_title"],
        height=420,
        margin={"l": 56, "r": 18, "t": 54, "b": 58},
    )
    fig.update_traces(
        colorbar={
            "title": {"text": METRIC_TITLES[metric], "side": "right"},
            "thickness": 12,
            "len": 0.78,
        }
    )
    fig.update_xaxes(type="category", tickangle=-45, nticks=8)
    fig.update_yaxes(type="category", nticks=12)
    return apply_readable_style(fig, font_sizes)


def _empty_metric_figure(
    title: str,
    font_sizes: FontSizeConfig,
) -> go.Figure:
    """Create an empty metric chart."""
    fig = go.Figure()
    fig.add_annotation(
        text="No metric data for the selected filters",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": font_sizes.chart_annotation, "color": "#66717e"},
    )
    fig.update_layout(
        title=title,
        height=420,
        margin={"l": 56, "r": 18, "t": 54, "b": 58},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return apply_readable_style(fig, font_sizes)
