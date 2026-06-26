"""Layout section for option metric views."""

from dash import dcc, html

from modules.components import ComponentGroups


METRIC_DESCRIPTIONS = {
    "Implied volatility": "Market-implied annualized volatility from the option ask price.",
    "Delta": "Estimated option price change for a one-dollar stock price move.",
    "Gamma": "Estimated delta change for a one-dollar stock price move.",
    "Theta": "Estimated option price change from one day passing.",
    "Vega": "Estimated option price change from a one-point volatility move.",
    "Rho": "Estimated option price change from a one-point rate move.",
}


def option_metrics_layout(components: ComponentGroups):
    """Create the option-metrics layout section."""
    return html.Div(
        [
            html.Section(
                [
                    html.H2("Metric view"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Select single stock"),
                                    components.filters.metric_single_stock_selection,
                                    components.text.metric_filter_summary,
                                ],
                                className="field-group",
                            ),
                            html.Div(
                                [
                                    html.Label("Heatmap axes"),
                                    components.filters.metric_axis_mode,
                                ],
                                className="field-group",
                            ),
                        ],
                        className="metric-toolbar",
                    ),
                ],
                className="dashboard-section",
            ),
            html.Section(
                [
                    html.H2("Option metrics"),
                    html.Div(
                        [
                            _metric_panel(
                                "Implied volatility",
                                components.charts.implied_volatility_metric,
                            ),
                            _metric_panel("Delta", components.charts.delta_metric),
                            _metric_panel("Gamma", components.charts.gamma_metric),
                            _metric_panel("Theta", components.charts.theta_metric),
                            _metric_panel("Vega", components.charts.vega_metric),
                            _metric_panel("Rho", components.charts.rho_metric),
                        ],
                        className="metrics-grid",
                    ),
                ],
                className="dashboard-section",
            ),
        ],
        className="dashboard-main",
    )


def _metric_panel(title: str, chart):
    """Create a metric chart panel with a compact info marker."""
    return html.Div(
        [
            html.Div(
                [
                    html.H3(title),
                    html.Details(
                        [
                            html.Summary("i", className="info-dot"),
                            html.Div(
                                METRIC_DESCRIPTIONS[title],
                                className="info-popover",
                            ),
                        ],
                        className="info-details",
                    ),
                ],
                className="metric-chart-heading",
            ),
            dcc.Loading(chart, type="circle"),
        ],
        className="metric-chart-panel",
    )
