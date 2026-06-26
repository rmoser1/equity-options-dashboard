"""Callbacks for stock information controls and tables."""

from dash import Dash, Input, Output
import pandas as pd

from modules.components import ComponentGroups
from modules.dashboard_filter_state import DEFAULT_MULTIPLE_STOCKS


def register_stock_info_callbacks(
    app: Dash,
    components: ComponentGroups,
    data: dict,
) -> None:
    """Register stock-info callbacks.

    :param app: Dash app instance.
    :param components: Named dashboard component groups.
    :param data: Dashboard app data.
    """
    stock_info = data["stock_info_df"]
    info_items_by_category = data["info_items_by_category"]

    _register_info_item_selection_callback(app, components, info_items_by_category)
    _register_stock_info_grid_callback(app, components, stock_info)


def _register_info_item_selection_callback(
    app: Dash,
    components: ComponentGroups,
    info_items_by_category: dict,
) -> None:
    """Register the info-item selection callback."""

    @app.callback(
        output=dict(
            info_items_options=Output(
                components.filters.info_item_selection,
                "options",
            ),
            info_items_value=Output(
                components.filters.info_item_selection,
                "value",
            ),
        ),
        inputs=dict(
            selected_groups=Input(components.filters.info_item_group, "value"),
        ),
    )
    def update_items(selected_groups):
        if not selected_groups:
            return dict(info_items_options=dict(), info_items_value=[])
        selected_info_items = []
        for group in selected_groups:
            selected_info_items.extend(info_items_by_category.get(group, []))
        return dict(
            info_items_options=selected_info_items,
            info_items_value=selected_info_items,
        )


def _register_stock_info_grid_callback(
    app: Dash,
    components: ComponentGroups,
    stock_info: pd.DataFrame,
) -> None:
    """Register the stock-info grid callback."""

    @app.callback(
        output=dict(
            grid_columns=Output(components.table.stock_info_grid, "columnDefs"),
            grid_rows=Output(components.table.stock_info_grid, "rowData"),
            info_status=Output(components.text.stock_info_status, "children"),
        ),
        inputs=dict(
            selected_stocks=Input(
                components.filters.stock_info_stock_selection,
                "value",
            ),
            selected_info_items=Input(
                components.filters.info_item_selection,
                "value",
            ),
        ),
    )
    def stock_info_callback(selected_stocks, selected_info_items):
        selected_stocks = selected_stocks or DEFAULT_MULTIPLE_STOCKS
        selected_info_items = selected_info_items or []
        missing_stocks = _stocks_without_info(stock_info, selected_stocks)
        missing_item_stocks = _stocks_without_selected_items(
            stock_info,
            selected_stocks,
            selected_info_items,
            missing_stocks,
        )

        df = stock_info[
            stock_info["stockSymbol"].isin(selected_stocks)
            & stock_info["itemName"].isin(selected_info_items)
        ]
        df = df.pivot(
            columns="itemName",
            index="stockSymbol",
            values="itemValue",
        ).reset_index()

        grid_columns = (
            [{"field": column, "rowDrag": True} for column in df.columns[0:1]]
            + [
                {
                    "field": column,
                    "wrapText": True,
                    "autoHeight": True,
                    "cellStyle": {
                        "wordBreak": "normal",
                        "lineHeight": "unset",
                    },
                }
                for column in df.columns[1:]
            ]
        )
        return dict(
            grid_rows=df.to_dict("records"),
            grid_columns=grid_columns,
            info_status=_stock_info_status(missing_stocks, missing_item_stocks),
        )


def _stocks_without_info(stock_info: pd.DataFrame, selected_stocks: list[str]) -> list[str]:
    """Return selected stocks with no stock-info rows."""
    stocks_with_info = set(stock_info["stockSymbol"].dropna().unique())
    return [stock for stock in selected_stocks if stock not in stocks_with_info]


def _stocks_without_selected_items(
    stock_info: pd.DataFrame,
    selected_stocks: list[str],
    selected_info_items: list[str],
    missing_stocks: list[str],
) -> list[str]:
    """Return selected stocks with no rows for the selected info items."""
    if not selected_info_items:
        return []

    missing_stock_set = set(missing_stocks)
    matching_info = stock_info[
        stock_info["stockSymbol"].isin(selected_stocks)
        & stock_info["itemName"].isin(selected_info_items)
    ]
    stocks_with_selected_items = set(matching_info["stockSymbol"].dropna().unique())
    return [
        stock
        for stock in selected_stocks
        if stock not in missing_stock_set and stock not in stocks_with_selected_items
    ]


def _stock_info_status(
    missing_stocks: list[str],
    missing_item_stocks: list[str],
) -> str:
    """Create the stock-info status message."""
    messages = []
    if missing_stocks:
        stocks = ", ".join(missing_stocks)
        messages.append(f"No stock info items are available for: {stocks}.")
    if missing_item_stocks:
        stocks = ", ".join(missing_item_stocks)
        messages.append(f"No selected stock info items are available for: {stocks}.")
    return " ".join(messages)
