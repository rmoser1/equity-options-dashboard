"""Top-level dashboard layout shell."""

from dash import dcc, html

from config import DEFAULT_FONT_SIZES, FontSizeConfig, font_size_css_variables
from modules.components import ComponentGroups
from modules.layout.options import options_layout
from modules.layout.stock_info import stock_info_layout
from modules.layout.stock_prices import stock_prices_layout


def create_layout(
    components: ComponentGroups,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
):
    """Create the dashboard layout.

    :param components: Named dashboard component groups.
    :param font_sizes: Dashboard font-size scale.
    :returns: Dash application layout.
    """
    return html.Div(
        [
            html.Div(
                [
                    components.store.filtered_options_single_stock,
                    components.store.filtered_options_multiple_stocks,
                    components.store.selected_single_stock,
                ],
                className="app-stores",
            ),
            html.Header(
                [
                    html.Div(
                        [
                            html.H1("Equity Options Dashboard"),
                            html.Div(
                                "Option prices, stock info, stock prices, and option metrics",
                                className="app-subtitle",
                            ),
                            components.text.last_trade_date,
                        ],
                    ),
                ],
                className="app-header",
            ),
            dcc.Tabs(
                id="APP_Tabs",
                className="dashboard-tabs",
                parent_className="dashboard-tabs-wrap",
                content_className="tab-content",
                value="options",
                children=[
                    dcc.Tab(
                        label="Options",
                        value="options",
                        children=options_layout(components),
                    ),
                    dcc.Tab(
                        label="Stock info",
                        value="stock_info",
                        children=stock_info_layout(components),
                    ),
                    dcc.Tab(
                        label="Stock prices",
                        value="stock_prices",
                        children=stock_prices_layout(components),
                    ),
                ],
            ),
        ],
        id="APP_Shell",
        className="app-shell",
        style=font_size_css_variables(font_sizes),
    )


def create_missing_data_layout(font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES):
    """Create the layout shown when dashboard data files are unavailable."""
    return _message_layout(
        "Data unavailable",
        [
            "The required parquet files are missing.",
            "Upload or generate the dataset, then restart the app.",
        ],
        font_sizes,
    )


def create_other_exception_layout(
    exc: Exception,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
):
    """Create the layout shown when app initialization fails."""
    return _message_layout(
        "An exception occurred",
        ["The app could not finish initialization.", html.Pre(str(exc))],
        font_sizes,
    )


def _message_layout(
    title: str,
    body: list,
    font_sizes: FontSizeConfig,
):
    """Create a framed startup-state layout."""
    return html.Div(
        [
            html.Header(
                [
                    html.H1("Equity Options Dashboard"),
                    html.Div("Startup status", className="app-subtitle"),
                ],
                className="app-header",
            ),
            html.Main(
                html.Section(
                    [
                        html.H2(title),
                        *[
                            item if hasattr(item, "children") else html.P(item)
                            for item in body
                        ],
                    ],
                    className="message-panel",
                ),
                className="tab-content",
            ),
        ],
        className="app-shell",
        style=font_size_css_variables(font_sizes),
    )
