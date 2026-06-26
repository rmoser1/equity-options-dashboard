"""Layout section for stock price history views."""

from dash import dcc, html

from modules.components import ComponentGroups


def stock_prices_layout(components: ComponentGroups):
    """Create the stock-price layout section."""
    return html.Div(
        [
            html.Aside(
                [
                    html.H2("Filters"),
                    html.Div(
                        [
                            html.Label("Stock"),
                            components.filters.stock_price_stock_selection,
                        ],
                        className="field-group",
                    ),
                    html.Div(
                        [
                            html.Label("Range"),
                            components.filters.stock_price_range,
                        ],
                        className="field-group",
                    ),
                ],
                className="filter-band stock-price-filters",
            ),
            html.Section(
                [
                    html.H2("Stock price history"),
                    dcc.Loading(components.charts.stock_time_series, type="circle"),
                ],
                className="dashboard-section",
            ),
        ],
        className="page-stack",
    )
