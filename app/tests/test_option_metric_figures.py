"""Tests for option metric Plotly figure builders."""

import pandas as pd


from config import DEFAULT_FONT_SIZES
from modules.plotly_figures.option_metrics import metric_heatmaps


def test_metric_heatmaps_use_expiration_and_strike_axes():
    """Metric heatmaps support expiration-date and strike axes."""
    figures = metric_heatmaps(_options_df(), "SPY", "expiration_strike")

    assert len(figures) == 6
    assert figures[0].layout.xaxis.title.text == "Expiration"
    assert figures[0].layout.yaxis.title.text == "Strike"
    assert figures[0].layout.height == 420
    assert figures[0].layout.font.size == DEFAULT_FONT_SIZES.chart
    assert figures[0].layout.hoverlabel.font.size == DEFAULT_FONT_SIZES.chart_hover
    assert list(figures[0].data[0].x) == ["2026-07-17", "2026-08-21"]
    assert list(figures[0].data[0].y) == [500.0, 510.0]
    assert figures[0].data[0].z[0][0] == 0.2


def test_metric_heatmaps_use_time_and_relative_strike_axes():
    """Metric heatmaps support time-to-expiry and relative-strike axes."""
    figures = metric_heatmaps(_options_df(), "SPY", "time_relative_strike")

    assert figures[1].layout.xaxis.title.text == "Years to expiry"
    assert figures[1].layout.yaxis.title.text == "Relative strike"
    assert list(figures[1].data[0].x) == [0.08, 0.17]
    assert list(figures[1].data[0].y) == [0.9615, 0.9808]
    assert figures[1].data[0].z[1][1] == 0.7
    assert "Delta" in figures[1].data[0].hovertemplate


def test_metric_heatmaps_default_unknown_axis_mode_to_expiration_and_strike():
    """Metric heatmaps fall back to the default axis mode."""
    figures = metric_heatmaps(_options_df(), "SPY", "unknown")

    assert figures[0].layout.xaxis.title.text == "Expiration"
    assert figures[0].layout.yaxis.title.text == "Strike"
    assert list(figures[0].data[0].x) == ["2026-07-17", "2026-08-21"]


def test_metric_heatmaps_show_empty_state():
    """Metric heatmaps render a readable empty state."""
    figures = metric_heatmaps(pd.DataFrame(), "SPY", "expiration_strike")

    assert len(figures) == 6
    assert figures[0].layout.annotations[0].text == (
        "No metric data for the selected filters"
    )


def _options_df() -> pd.DataFrame:
    """Create a small single-stock metric dataset."""
    return pd.DataFrame(
        [
            {
                "stockSymbol": "SPY",
                "expirationDate": pd.Timestamp("2026-07-17"),
                "strike": 500.0,
                "timeToExpiryYears": 0.08,
                "relativeStrikePrice": 0.9615,
                "calculatedImpliedVolatility": 0.2,
                "delta": 0.6,
                "gamma": 0.01,
                "theta": -0.02,
                "vega": 0.1,
                "rho": 0.05,
            },
            {
                "stockSymbol": "SPY",
                "expirationDate": pd.Timestamp("2026-08-21"),
                "strike": 510.0,
                "timeToExpiryYears": 0.17,
                "relativeStrikePrice": 0.9808,
                "calculatedImpliedVolatility": 0.25,
                "delta": 0.7,
                "gamma": 0.02,
                "theta": -0.03,
                "vega": 0.2,
                "rho": 0.06,
            },
        ]
    )
