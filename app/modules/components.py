"""Dash component declarations for the equity options dashboard."""

from dataclasses import dataclass

from dash import html, dcc
import dash_ag_grid as dag

from modules.dashboard_filter_state import (
    DEFAULT_DIRECTION,
    DEFAULT_MULTIPLE_STOCKS,
    DEFAULT_SINGLE_STOCK,
    default_relative_strike_range,
)


@dataclass(frozen=True)
class StoreComponents:
    """Dash stores shared between callbacks."""

    filtered_options_single_stock: dcc.Store
    filtered_options_multiple_stocks: dcc.Store
    selected_single_stock: dcc.Store


@dataclass(frozen=True)
class FilterComponents:
    """Dashboard filter components."""

    direction: dcc.RadioItems
    expiration_dates: dcc.Dropdown
    relative_strike_price_range: dcc.RangeSlider
    multiple_stock_selection: dcc.Dropdown
    single_stock_selection: dcc.Dropdown
    contract_single_stock_selection: dcc.Dropdown
    metric_single_stock_selection: dcc.Dropdown
    stock_info_stock_selection: dcc.Dropdown
    stock_price_stock_selection: dcc.Dropdown
    stock_price_range: dcc.RadioItems
    info_item_group: dcc.Dropdown
    info_item_selection: dcc.Dropdown
    contract_selection: dcc.Dropdown
    metric_axis_mode: dcc.RadioItems


@dataclass(frozen=True)
class ChartComponents:
    """Dashboard chart components."""

    strike_price_multiple_stocks: dcc.Graph
    expiration_date_multiple_stocks: dcc.Graph
    cost_per_contract_single_stock: dcc.Graph
    volume_single_stock: dcc.Graph
    stock_time_series: dcc.Graph
    options_time_series: dcc.Graph
    implied_volatility_metric: dcc.Graph
    delta_metric: dcc.Graph
    gamma_metric: dcc.Graph
    theta_metric: dcc.Graph
    vega_metric: dcc.Graph
    rho_metric: dcc.Graph


@dataclass(frozen=True)
class TableComponents:
    """Dashboard table components."""

    stock_info_grid: dag.AgGrid


@dataclass(frozen=True)
class TextComponents:
    """Dashboard text components."""

    multiple_stock_filter_summary: html.Div
    single_stock_filter_summary: html.Div
    contract_filter_summary: html.Div
    metric_filter_summary: html.Div
    stock_info_status: html.Div
    last_trade_date: html.Div
    nominal_per_contract: html.Div


@dataclass(frozen=True)
class ComponentGroups:
    """Named groups of Dash components."""

    store: StoreComponents
    filters: FilterComponents
    charts: ChartComponents
    table: TableComponents
    text: TextComponents


def declare_components(data: dict) -> ComponentGroups:
    """Declare Dash components grouped by dashboard area.

    :param data: Dashboard app data used to initialize component options.
    :returns: Named groups of Dash components.
    """
    return ComponentGroups(
        store=_store_components(),
        filters=_filter_components(data),
        charts=_chart_components(),
        table=_table_components(),
        text=_text_components(data),
    )


def _store_components() -> StoreComponents:
    """Declare shared Dash stores."""
    return StoreComponents(
        filtered_options_single_stock=dcc.Store(
            id="STORE_FilteredOptionsSingleStock"
        ),
        filtered_options_multiple_stocks=dcc.Store(
            id="STORE_FilteredOptionsMultipleStocks"
        ),
        selected_single_stock=dcc.Store(
            data=DEFAULT_SINGLE_STOCK,
            id="STORE_SelectedSingleStock",
        ),
    )


def _filter_components(data: dict) -> FilterComponents:
    """Declare dashboard filters."""
    expiration_dates = data["expiration_dates_datetime"]
    relative_strike_range = data["relative_strike_price_range"]

    return FilterComponents(
        direction=dcc.RadioItems(
            options=["PUT", "CALL"],
            value=DEFAULT_DIRECTION,
            inline=True,
            id="SELECTOR_DirectionRadioItems",
        ),
        expiration_dates=dcc.Dropdown(
            options=data["expiration_dates_dict"],
            value=expiration_dates[: min(10, len(expiration_dates))],
            multi=True,
            style={"maxHeight": "200px", "overflowY": "auto"},
            id="SELECTOR_ExpirationDateDropdown",
        ),
        relative_strike_price_range=dcc.RangeSlider(
            min=relative_strike_range[0],
            max=relative_strike_range[1],
            value=default_relative_strike_range(relative_strike_range),
            step=0.005,
            marks=None,
            updatemode="mouseup",
            tooltip={"placement": "bottom", "always_visible": True},
            id="SELECTOR_RelativeStrikePriceRangeSlider",
        ),
        multiple_stock_selection=dcc.Dropdown(
            options=data["stock_tickers_dict"],
            value=DEFAULT_MULTIPLE_STOCKS,
            multi=True,
            style={"maxHeight": "200px", "overflowY": "auto"},
            id="SELECTOR_StockSelectionDropdown_MultipleStocks",
        ),
        single_stock_selection=dcc.Dropdown(
            options=data["stock_tickers_dict"],
            value=DEFAULT_SINGLE_STOCK,
            multi=False,
            id="SELECTOR_StockSelectionDropdown_SingleStock",
        ),
        contract_single_stock_selection=dcc.Dropdown(
            options=data["stock_tickers_dict"],
            value=DEFAULT_SINGLE_STOCK,
            multi=False,
            id="SELECTOR_StockSelectionDropdown_Contract",
        ),
        metric_single_stock_selection=dcc.Dropdown(
            options=data["stock_tickers_dict"],
            value=DEFAULT_SINGLE_STOCK,
            multi=False,
            id="SELECTOR_StockSelectionDropdown_Metrics",
        ),
        stock_info_stock_selection=dcc.Dropdown(
            options=data["stock_tickers_dict"],
            value=DEFAULT_MULTIPLE_STOCKS,
            multi=True,
            style={"maxHeight": "200px", "overflowY": "auto"},
            id="SELECTOR_StockInfoStockSelectionDropdown",
        ),
        stock_price_stock_selection=dcc.Dropdown(
            options=data["stock_tickers_dict"],
            value=DEFAULT_SINGLE_STOCK,
            multi=False,
            id="SELECTOR_StockPriceStockSelectionDropdown",
        ),
        stock_price_range=dcc.RadioItems(
            options=[
                {"label": "1M", "value": "1m"},
                {"label": "1Y", "value": "1y"},
                {"label": "5Y", "value": "5y"},
                {"label": "Max", "value": "max"},
            ],
            value="1y",
            inline=True,
            id="SELECTOR_StockPriceRangeRadioItems",
        ),
        info_item_group=dcc.Dropdown(
            options=data["info_items_categories"],
            value=["valuation"],
            multi=True,
            id="SELECTOR_InfoItemGroup_Dropdown",
        ),
        info_item_selection=dcc.Dropdown(
            multi=True,
            id="SELECTOR_InfoItemSelectionDropdown",
        ),
        contract_selection=dcc.Dropdown(
            multi=False,
            id="SELECTOR_ContractSelectionDropdown",
        ),
        metric_axis_mode=dcc.RadioItems(
            options=[
                {
                    "label": "Expiration date x Strike",
                    "value": "expiration_strike",
                },
                {
                    "label": "Time to expiry x Relative strike",
                    "value": "time_relative_strike",
                },
            ],
            value="expiration_strike",
            inline=True,
            id="SELECTOR_MetricAxisModeRadioItems",
        ),
    )

def _chart_components() -> ChartComponents:
    """Declare dashboard charts."""
    return ChartComponents(
        strike_price_multiple_stocks=dcc.Graph(
            id="CHART_StrikePriceGraph_OptionsMultipleStocks"
        ),
        expiration_date_multiple_stocks=dcc.Graph(
            id="CHART_ExpirationDateGraph_OptionsMultipleStocks"
        ),
        cost_per_contract_single_stock=dcc.Graph(
            id="CHART_CostPerContractGraph_OptionsSingleStock"
        ),
        volume_single_stock=dcc.Graph(id="CHART_VolumeGraph_OptionsSingleStock"),
        stock_time_series=dcc.Graph(id="CHART_StockTimeSeriesGraph"),
        options_time_series=dcc.Graph(id="CHART_OptionsTimeSeriesGraph"),
        implied_volatility_metric=dcc.Graph(id="CHART_CalculatedImpliedVolatility"),
        delta_metric=dcc.Graph(id="CHART_Delta"),
        gamma_metric=dcc.Graph(id="CHART_Gamma"),
        theta_metric=dcc.Graph(id="CHART_Theta"),
        vega_metric=dcc.Graph(id="CHART_Vega"),
        rho_metric=dcc.Graph(id="CHART_Rho"),
    )


def _table_components() -> TableComponents:
    """Declare dashboard tables."""
    return TableComponents(
        stock_info_grid=dag.AgGrid(
            defaultColDef={"filter": True},
            dashGridOptions={"rowDragManaged": True, "domLayout": "normal"},
            style={"height": "520px", "width": "100%"},
            id="TABLE_StockInfoGrid",
        )
    )


def _text_components(data: dict) -> TextComponents:
    """Declare dashboard text elements."""
    return TextComponents(
        multiple_stock_filter_summary=html.Div(
            className="filter-summary",
            id="TEXT_MultipleStockFilterSummary",
        ),
        single_stock_filter_summary=html.Div(
            className="filter-summary",
            id="TEXT_SingleStockFilterSummary",
        ),
        contract_filter_summary=html.Div(
            className="filter-summary",
            id="TEXT_ContractFilterSummary",
        ),
        metric_filter_summary=html.Div(
            className="filter-summary",
            id="TEXT_MetricFilterSummary",
        ),
        stock_info_status=html.Div(
            className="table-status",
            id="TEXT_StockInfoStatus",
        ),
        last_trade_date=html.Div(
            f"Data as of {data['last_trade_date']}",
            className="dataset-status",
            id="TEXT_LastTradeDateDiv",
        ),
        nominal_per_contract=html.Div(id="TEXT_NominalPerContractDiv"),
    )
