"""Tests for option and stock price Plotly figure builders."""

import pandas as pd

from config import DEFAULT_FONT_SIZES
from modules.parquet_contract import load_dataset
from modules.plotly_figures.option_prices import (
    heatmaps_options_single_stock,
    option_time_series,
    scatter_relativeOptionPrice_vs_expirationDate,
    scatter_relativeOptionPrice_vs_relativeStrikePrice,
)
from modules.plotly_figures.stock_prices import stock_time_series


def test_option_scatter_figures_use_expected_axes(dashboard_parquet_dir):
    """Verify option scatter figures preserve the expected chart contracts."""
    options = load_dataset(dashboard_parquet_dir, "options_last")

    strike_fig = scatter_relativeOptionPrice_vs_relativeStrikePrice(options)
    expiration_fig = scatter_relativeOptionPrice_vs_expirationDate(options)

    assert strike_fig.layout.xaxis.title.text == "relativeStrikePrice"
    assert strike_fig.layout.yaxis.title.text == "relativeOptionPrice"
    assert expiration_fig.layout.xaxis.title.text == "expirationDate"
    assert expiration_fig.layout.yaxis.title.text == "relativeOptionPrice"
    assert strike_fig.layout.showlegend is False
    assert strike_fig.layout.font.size == DEFAULT_FONT_SIZES.chart
    assert strike_fig.layout.xaxis.tickfont.size == DEFAULT_FONT_SIZES.chart
    assert strike_fig.layout.hoverlabel.font.size == DEFAULT_FONT_SIZES.chart_hover
    assert "SPY260717C00500000" in {
        row[0] for trace in strike_fig.data for row in trace.customdata
    }
    assert "Open interest" in strike_fig.data[0].hovertemplate


def test_single_stock_option_heatmaps_use_cost_and_volume_values(
    dashboard_parquet_dir,
):
    """Verify single-stock heatmaps pivot by expiration and relative strike."""
    options = load_dataset(dashboard_parquet_dir, "options_last")
    spy_calls = options[
        (options["stockSymbol"] == "SPY") & (options["direction"] == "CALL")
    ].copy()
    spy_calls["relativeStrikePrice"] = spy_calls["relativeStrikePrice"].round(4)

    cost_fig, volume_fig = heatmaps_options_single_stock(spy_calls, "SPY", "CALL")

    assert cost_fig.layout.title.text == "Cost per Contract for SPY CALL Options"
    assert volume_fig.layout.title.text == "Volume for SPY CALL Options"
    assert cost_fig.layout.xaxis.title.text == "Expiration"
    assert cost_fig.layout.yaxis.title.text == "Relative strike"
    assert list(cost_fig.data[0].x) == ["2026-07-17", "2026-08-21"]
    assert list(cost_fig.data[0].y) == [0.9615, 0.9808]
    assert cost_fig.data[0].z[0][0] == 500.0


def test_single_stock_option_heatmaps_can_display_cell_values(
    dashboard_parquet_dir,
):
    """Verify optional heatmap cell labels use the pivoted values."""
    options = load_dataset(dashboard_parquet_dir, "options_last")
    spy_calls = options[
        (options["stockSymbol"] == "SPY") & (options["direction"] == "CALL")
    ].copy()
    spy_calls["relativeStrikePrice"] = spy_calls["relativeStrikePrice"].round(4)

    cost_fig, volume_fig = heatmaps_options_single_stock(
        spy_calls,
        "SPY",
        "CALL",
        display_values=True,
    )

    assert cost_fig.data[0].text[0][0] == 500.0
    assert volume_fig.data[0].texttemplate == "%{text}"


def test_time_series_figures_use_dual_traces():
    """Verify stock and option time-series figures include value and volume traces."""
    dates = pd.to_datetime(["2026-06-19", "2026-06-20"])
    stock_fig = stock_time_series(
        pd.DataFrame(
            {"date": dates, "close": [520.0, 522.0], "volume": [1000, 1200]}
        ),
        "SPY",
    )
    option_fig = option_time_series(
        pd.DataFrame(
            {
                "lastTradeDate": dates,
                "ask": [5.0, 5.5],
                "openInterest": [20, 22],
            }
        ),
        "SPY260717C00500000",
    )

    assert [trace.name for trace in stock_fig.data] == ["close", "volume"]
    assert [trace.name for trace in option_fig.data] == ["ask", "openInterest"]
    assert stock_fig.layout.yaxis.title.text == "Price"
    assert option_fig.layout.yaxis.title.text == "Ask"
    assert stock_fig.layout.legend.font.size == DEFAULT_FONT_SIZES.chart
    assert option_fig.layout.yaxis.title.font.size == DEFAULT_FONT_SIZES.chart_axis_title
    assert option_fig.layout.hoverlabel.font.size == DEFAULT_FONT_SIZES.chart_hover
    assert "Close" in stock_fig.data[0].hovertemplate
    assert "Open interest" in option_fig.data[1].hovertemplate


def test_empty_figures_show_status_messages():
    """Verify empty chart builders return readable empty states."""
    empty = pd.DataFrame()

    strike_fig = scatter_relativeOptionPrice_vs_relativeStrikePrice(empty)
    cost_fig, volume_fig = heatmaps_options_single_stock(empty, "SPY", "CALL")
    stock_fig = stock_time_series(empty, "SPY")
    option_fig = option_time_series(empty, None)

    assert strike_fig.layout.annotations[0].text == "No matching option contracts"
    assert cost_fig.layout.annotations[0].text == "No matching option contracts"
    assert volume_fig.layout.annotations[0].text == "No matching option contracts"
    assert stock_fig.layout.annotations[0].text == (
        "No stock price history for the selected stock"
    )
    assert option_fig.layout.annotations[0].text == "No option contract selected"
