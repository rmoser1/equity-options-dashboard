"""Shared option dashboard workspace layout."""

from dash import dcc, html

from modules.components import ComponentGroups
from modules.layout.option_metrics import option_metrics_layout
from modules.layout.option_prices import option_prices_layout


def options_layout(components: ComponentGroups):
    """Create the shared option workspace layout."""
    return html.Div(
        [
            option_filter_layout(components),
            dcc.Tabs(
                id="APP_OptionTabs",
                className="nested-tabs",
                parent_className="nested-tabs-wrap",
                content_className="nested-tab-content",
                value="option_prices",
                children=[
                    dcc.Tab(
                        label="Option prices",
                        value="option_prices",
                        children=option_prices_layout(components),
                    ),
                    dcc.Tab(
                        label="Option metrics",
                        value="option_metrics",
                        children=option_metrics_layout(components),
                    ),
                ],
            ),
        ],
        className="page-stack",
    )


def option_filter_layout(components: ComponentGroups):
    """Create option filters shared by option prices and metrics."""
    return html.Aside(
        [
            html.H2("Option filters"),
            _field(
                "Option type",
                components.filters.direction,
                className="field-group field-compact",
            ),
            _field(
                "Expiration dates",
                components.filters.expiration_dates,
                className="field-group field-medium",
            ),
            _field(
                "Relative strike price",
                components.filters.relative_strike_price_range,
                className="field-group field-fill",
            ),
        ],
        id="PANEL_OptionFilters",
        className="filter-band",
    )


def _field(label: str, control, className: str = "field-group"):
    """Create a labelled option filter control."""
    return html.Div([html.Label(label), control], className=className)
