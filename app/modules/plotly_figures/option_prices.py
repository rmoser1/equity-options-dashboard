"""Plotly figure builders for option price views."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import DEFAULT_FONT_SIZES, FontSizeConfig
from modules.plotly_figures.style import apply_readable_style


def empty_figure(
    message: str,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> go.Figure:
    """Create an empty chart with a centered status message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": font_sizes.chart_annotation, "color": "#66717e"},
    )
    fig.update_layout(
        margin={"l": 40, "r": 24, "t": 48, "b": 40},
        height=420,
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return apply_readable_style(fig, font_sizes)


def scatter_relativeOptionPrice_vs_relativeStrikePrice(
    df: pd.DataFrame,
    show_legend: bool = False,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> px.scatter:
    """Create a relative option-price versus relative strike scatter plot."""
    if df.empty:
        return empty_figure("No matching option contracts", font_sizes)

    fig = px.scatter(
        df,
        x="relativeStrikePrice",
        y="relativeOptionPrice",
        color="stockSymbol",
        custom_data=[
            "contractSymbol",
            "stockSymbol",
            "expirationDate",
            "strike",
            "lastStockPrice",
            "ask",
            "volume",
            "openInterest",
        ],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Stock: %{customdata[1]}<br>"
            "Expiration: %{customdata[2]|%Y-%m-%d}<br>"
            "Strike: %{customdata[3]:,.2f}<br>"
            "Last stock: %{customdata[4]:,.2f}<br>"
            "Ask: %{customdata[5]:,.2f}<br>"
            "Volume: %{customdata[6]:,}<br>"
            "Open interest: %{customdata[7]:,}<br>"
            "Relative strike: %{x:.4f}<br>"
            "Relative option price: %{y:.4f}<extra></extra>"
        )
    )
    fig.update_layout(showlegend=show_legend)
    fig.update_layout(height=480, margin={"l": 56, "r": 24, "t": 40, "b": 54})
    return apply_readable_style(fig, font_sizes)


def scatter_relativeOptionPrice_vs_expirationDate(
    df: pd.DataFrame,
    show_legend: bool = False,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> px.scatter:
    """Create a relative option-price versus expiration-date scatter plot."""
    if df.empty:
        return empty_figure("No matching option contracts", font_sizes)

    fig = px.scatter(
        df,
        x="expirationDate",
        y="relativeOptionPrice",
        color="stockSymbol",
        custom_data=[
            "contractSymbol",
            "stockSymbol",
            "strike",
            "lastStockPrice",
            "ask",
            "volume",
            "openInterest",
            "relativeStrikePrice",
        ],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Stock: %{customdata[1]}<br>"
            "Expiration: %{x|%Y-%m-%d}<br>"
            "Strike: %{customdata[2]:,.2f}<br>"
            "Last stock: %{customdata[3]:,.2f}<br>"
            "Ask: %{customdata[4]:,.2f}<br>"
            "Volume: %{customdata[5]:,}<br>"
            "Open interest: %{customdata[6]:,}<br>"
            "Relative strike: %{customdata[7]:.4f}<br>"
            "Relative option price: %{y:.4f}<extra></extra>"
        )
    )
    fig.update_layout(showlegend=show_legend)
    fig.update_layout(height=480, margin={"l": 56, "r": 24, "t": 40, "b": 54})
    return apply_readable_style(fig, font_sizes)


def heatmaps_options_single_stock(
    df: pd.DataFrame,
    stock: str,
    direction: str,
    display_values: bool = False,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> tuple[go.Figure, go.Figure]:
    """Create cost and volume heatmaps for a single stock's options."""
    if df.empty:
        empty = empty_figure("No matching option contracts", font_sizes)
        return empty, empty

    def make_heatmap(data: pd.DataFrame, value_col: str, title_prefix: str):
        data = data[["expirationDate", "relativeStrikePrice", value_col]].copy()
        data["expirationDate"] = pd.to_datetime(data["expirationDate"]).dt.strftime(
            "%Y-%m-%d"
        )
        data = data.set_index(["expirationDate", "relativeStrikePrice"]).unstack(
            level=0
        )
        data.columns = data.columns.droplevel(0)

        fig = go.Figure(
            data=go.Heatmap(
                z=data.values,
                x=data.columns,
                y=data.index,
                colorscale=["blue", "green", "red"],
                xgap=1,
                ygap=1,
                hovertemplate=(
                    "Expiration: %{x}<br>"
                    "Relative strike: %{y:.4f}<br>"
                    f"{title_prefix}: "
                    "%{z:,.2f}<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            title=f"{title_prefix} for {stock} {direction} Options",
            xaxis_title="Expiration",
            yaxis_title="Relative strike",
            height=480,
            margin={"l": 72, "r": 28, "t": 56, "b": 72},
        )
        fig.update_xaxes(type="category", tickangle=-45, nticks=10)
        fig.update_yaxes(type="category", nticks=14)
        if display_values:
            fig.update_traces(
                text=data.values,
                texttemplate="%{text}",
                textfont={
                    "size": font_sizes.chart_heatmap_text,
                    "color": "black",
                },
            )

        return apply_readable_style(fig, font_sizes)

    fig_cost_per_contract = make_heatmap(
        df,
        value_col="costPerContract",
        title_prefix="Cost per Contract",
    )
    fig_volume = make_heatmap(df, value_col="volume", title_prefix="Volume")
    return fig_cost_per_contract, fig_volume


def option_time_series(
    df: pd.DataFrame,
    contractSymbol: str,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> go.Figure:
    """Create an option ask and open-interest time-series chart."""
    if df.empty or contractSymbol is None:
        return empty_figure("No option contract selected", font_sizes)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=df["lastTradeDate"],
            y=df["ask"],
            name="ask",
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Ask: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["lastTradeDate"],
            y=df["openInterest"],
            name="openInterest",
            opacity=0.5,
            hovertemplate=(
                "Date: %{x|%Y-%m-%d}<br>"
                "Open interest: %{y:,}<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Ask", secondary_y=False)
    fig.update_yaxes(title_text="Open Interest", secondary_y=True)
    fig.update_layout(
        title=contractSymbol,
        height=480,
        margin={"l": 56, "r": 56, "t": 54, "b": 48},
        hovermode="x unified",
    )
    return apply_readable_style(fig, font_sizes)
