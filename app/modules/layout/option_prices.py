"""Layout section for option price views."""

from dash import dcc, html

from modules.components import ComponentGroups


def option_prices_layout(components: ComponentGroups):
    """Create the option-prices layout section."""
    return html.Div(
        [
            dcc.Tabs(
                id="APP_OptionPriceTabs",
                className="nested-tabs workflow-tabs",
                parent_className="nested-tabs-wrap workflow-tabs-wrap",
                content_className="nested-tab-content workflow-tab-content",
                value="multiple_stocks",
                children=[
                    dcc.Tab(
                        label="Multiple stocks",
                        value="multiple_stocks",
                        children=_multiple_stocks_layout(components),
                    ),
                    dcc.Tab(
                        label="Single stock",
                        value="single_stock",
                        children=_single_stock_layout(components),
                    ),
                    dcc.Tab(
                        label="Single contract",
                        value="option_contract",
                        children=_option_contract_layout(components),
                    ),
                ],
            ),
        ],
        className="dashboard-main",
    )


def _multiple_stocks_layout(components: ComponentGroups):
    """Create the multiple-stock option price workflow."""
    return _section(
        "Multiple stocks",
        [
            _field(
                "Select multiple stocks",
                components.filters.multiple_stock_selection,
                components.text.multiple_stock_filter_summary,
            ),
            _chart_panel(
                "Strike price as x-axis",
                components.charts.strike_price_multiple_stocks,
            ),
            _chart_panel(
                "Expiration date as x-axis",
                components.charts.expiration_date_multiple_stocks,
            ),
        ],
    )


def _single_stock_layout(components: ComponentGroups):
    """Create the single-stock option price workflow."""
    return _section(
        "Single stock",
        [
            _field(
                "Select single stock",
                components.filters.single_stock_selection,
                components.text.single_stock_filter_summary,
            ),
            html.Div(
                components.text.nominal_per_contract,
                className="metric-note",
            ),
            dcc.Loading(
                components.charts.cost_per_contract_single_stock,
                type="circle",
            ),
            dcc.Loading(
                components.charts.volume_single_stock,
                type="circle",
            ),
        ],
    )


def _option_contract_layout(components: ComponentGroups):
    """Create the selected-contract option price workflow."""
    return _section(
        "Option contract",
        [
            _field(
                "Select single stock",
                components.filters.contract_single_stock_selection,
                components.text.contract_filter_summary,
            ),
            _field("Contract", components.filters.contract_selection),
            dcc.Loading(components.charts.options_time_series, type="circle"),
        ],
    )


def _section(title: str, children: list):
    """Create a dashboard content section."""
    return html.Section([html.H2(title), *children], className="dashboard-section")


def _chart_panel(title: str, chart):
    """Create a titled chart panel."""
    return html.Div(
        [html.H3(title), dcc.Loading(chart, type="circle")],
        className="chart-panel",
    )


def _field(label: str, control, *extra_children, hint: str | None = None):
    """Create a labelled filter control."""
    children = [html.Label(label)]
    if hint:
        children.append(html.Div(hint, className="field-hint"))
    children.append(control)
    children.extend(extra_children)
    return html.Div(children, className="field-group")
