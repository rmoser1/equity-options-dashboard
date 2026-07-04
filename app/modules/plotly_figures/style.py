"""Shared Plotly styling helpers."""

import plotly.graph_objects as go

from config import DEFAULT_FONT_SIZES, FontSizeConfig


def apply_readable_style(
    fig: go.Figure,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> go.Figure:
    """Apply readable dashboard font sizes to a Plotly figure."""
    fig.update_layout(
        font={"size": font_sizes.chart, "color": "#3d4652"},
        title_font={"size": font_sizes.chart_title},
        legend={"font": {"size": font_sizes.chart}},
        hoverlabel={"font": {"size": font_sizes.chart_hover}},
    )
    fig.update_xaxes(
        title_font={"size": font_sizes.chart_axis_title},
        tickfont={"size": font_sizes.chart},
    )
    fig.update_yaxes(
        title_font={"size": font_sizes.chart_axis_title},
        tickfont={"size": font_sizes.chart},
    )
    fig.update_annotations(font_size=font_sizes.chart_annotation)
    fig.update_traces(
        colorbar={
            "tickfont": {"size": font_sizes.chart},
            "title": {"font": {"size": font_sizes.chart_axis_title}},
        },
        selector={"type": "heatmap"},
    )
    return fig
