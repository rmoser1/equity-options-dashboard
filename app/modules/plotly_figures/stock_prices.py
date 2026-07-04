"""Plotly figure builders for stock price views."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import DEFAULT_FONT_SIZES, FontSizeConfig
from modules.plotly_figures.style import apply_readable_style


def stock_time_series(
    df: pd.DataFrame,
    symbol: str,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> go.Figure:
    """Create a stock close and volume time-series chart."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No stock price history for the selected stock",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"size": font_sizes.chart_annotation, "color": "#66717e"},
        )
        fig.update_layout(
            title=symbol,
            height=520,
            margin={"l": 56, "r": 56, "t": 54, "b": 48},
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return apply_readable_style(fig, font_sizes)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close"],
            name="close",
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Close: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["volume"],
            name="volume",
            opacity=0.5,
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Volume: %{y:,}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Price", secondary_y=False)
    fig.update_yaxes(title_text="Volume", secondary_y=True)
    fig.update_layout(
        title=symbol,
        height=520,
        margin={"l": 56, "r": 56, "t": 54, "b": 48},
        hovermode="x unified",
    )
    return apply_readable_style(fig, font_sizes)
