"""Layout section for stock information views."""

from dash import html

from modules.components import ComponentGroups


def stock_info_layout(components: ComponentGroups):
    """Create the stock-info layout section."""
    return html.Div(
        [
            html.Aside(
                [
                    html.H2("Filters"),
                    _field("Stocks", components.filters.stock_info_stock_selection),
                    _field("Info categories", components.filters.info_item_group),
                    _field("Info items", components.filters.info_item_selection),
                ],
                className="filter-band stock-info-filters",
            ),
            html.Section(
                [
                    html.H2("Stock info"),
                    components.text.stock_info_status,
                    html.Div(
                        components.table.stock_info_grid,
                        className="table-panel",
                    ),
                ],
                className="dashboard-section",
            ),
        ],
        className="page-stack",
    )


def _field(label: str, control):
    """Create a labelled filter control."""
    return html.Div([html.Label(label), control], className="field-group")
