"""Tests for registered Dash callback behavior."""

from io import StringIO

import pandas as pd
import pytest

from config import AppConfig, FontSizeConfig
from dash_app import create_app
from modules.callbacks.option_prices import _read_store, _synced_single_stock_value
from modules.callbacks.stock_prices import _filter_price_range


@pytest.fixture
def app(dashboard_parquet_dir):
    """Create an app with realistic callback data."""
    return create_app(AppConfig(dashboard_data_dir=str(dashboard_parquet_dir)))


def test_option_filter_callback_filters_and_serializes_matches(app):
    """Verify shared option filters populate single and multi-stock stores."""
    callback = _callback_by_name(app, "options_callback")

    result = callback(
        "SPY",
        ["SPY", "MSFT"],
        "CALL",
        ["2026-07-17T00:00:00"],
        [0.95, 0.98],
    )

    single_stock = pd.read_json(
        StringIO(result["filtered_options_single_stock"]),
        orient="split",
    )
    multiple_stocks = pd.read_json(
        StringIO(result["filtered_options_multiple_stocks"]),
        orient="split",
    )
    assert single_stock["contractSymbol"].tolist() == ["SPY260717C00500000"]
    assert multiple_stocks["contractSymbol"].tolist() == [
        "SPY260717C00500000",
        "MSFT260717C00350000",
    ]
    assert [chip.children for chip in result["multiple_stock_filter_summary"]] == [
        "Multiple: SPY, MSFT",
        "CALL",
        "2026-07-17",
        "Strike 0.95-0.98",
        "Matches 2",
    ]
    assert [chip.children for chip in result["single_stock_filter_summary"]] == [
        "Single: SPY",
        "CALL",
        "2026-07-17",
        "Strike 0.95-0.98",
        "Matches 1",
    ]
    assert [chip.children for chip in result["contract_filter_summary"]] == [
        "Single: SPY",
        "CALL",
        "2026-07-17",
        "Strike 0.95-0.98",
        "Matches 1",
    ]
    assert [chip.children for chip in result["metric_filter_summary"]] == [
        "Single: SPY",
        "CALL",
        "2026-07-17",
        "Strike 0.95-0.98",
        "Matches 1",
    ]


def test_option_filter_callback_includes_all_selected_stocks(app):
    """Verify selecting every stock includes all matching multi-stock contracts."""
    callback = _callback_by_name(app, "options_callback")

    result = callback(
        "SPY",
        ["SPY", "MSFT"],
        "CALL",
        ["2026-07-17T00:00:00", "2026-08-21T00:00:00"],
        [0.9423, 0.9808],
    )

    multiple_stocks = pd.read_json(
        StringIO(result["filtered_options_multiple_stocks"]),
        orient="split",
    )

    assert multiple_stocks["contractSymbol"].tolist() == [
        "SPY260717C00500000",
        "SPY260821C00510000",
        "MSFT260717C00350000",
    ]
    assert result["multiple_stock_filter_summary"][-1].children == "Matches 3"


def test_option_filter_callback_clears_store_when_no_contracts_match(app):
    """Verify empty filter results clear stores instead of leaving stale data."""
    callback = _callback_by_name(app, "options_callback")

    result = callback(
        "SPY",
        ["SPY"],
        "CALL",
        ["2026-07-17T00:00:00"],
        [0.1, 0.2],
    )

    single_stock = pd.read_json(
        StringIO(result["filtered_options_single_stock"]),
        orient="split",
    )
    multiple_stocks = pd.read_json(
        StringIO(result["filtered_options_multiple_stocks"]),
        orient="split",
    )

    assert single_stock.empty
    assert multiple_stocks.empty
    assert result["single_stock_filter_summary"][-1].children == "Matches 0"
    assert result["multiple_stock_filter_summary"][-1].children == "Matches 0"


def test_contract_selection_callback_preselects_last_contract(app):
    """Verify contract dropdown options are derived from filtered store data."""
    filter_callback = _callback_by_name(app, "options_callback")
    selection_callback = _callback_by_name(app, "contractSelectionDropdown_callback")
    filter_result = filter_callback(
        "SPY",
        ["SPY"],
        "CALL",
        ["2026-07-17T00:00:00", "2026-08-21T00:00:00"],
        [0.95, 0.99],
    )

    result = selection_callback(filter_result["filtered_options_single_stock"])

    assert result["contracts"].tolist() == [
        "SPY260717C00500000",
        "SPY260821C00510000",
    ]
    assert result["preselected"] == "SPY260821C00510000"


def test_option_store_reader_restores_date_columns(app):
    """Verify callback store JSON restores expiration and trade dates."""
    filter_callback = _callback_by_name(app, "options_callback")
    filter_result = filter_callback(
        "SPY",
        ["SPY"],
        "CALL",
        ["2026-07-17T00:00:00"],
        [0.95, 0.98],
    )

    result = _read_store(filter_result["filtered_options_single_stock"])

    assert pd.api.types.is_datetime64_any_dtype(result["expirationDate"])
    assert pd.api.types.is_datetime64_any_dtype(result["lastTradeDate"])
    assert result.loc[0, "expirationDate"].strftime("%Y-%m-%d") == "2026-07-17"


def test_synced_single_stock_value_prefers_triggered_selector():
    """Verify synced single-stock selectors use the changed control."""
    result = _synced_single_stock_value(
        "SELECTOR_StockSelectionDropdown_Contract",
        single_stock="SPY",
        contract_stock="MSFT",
        metric_stock="AAPL",
        current_stock="SPY",
        single_stock_id="SELECTOR_StockSelectionDropdown_SingleStock",
        contract_stock_id="SELECTOR_StockSelectionDropdown_Contract",
        metric_stock_id="SELECTOR_StockSelectionDropdown_Metrics",
    )

    assert result == "MSFT"


def test_single_stock_option_callback_builds_summary_and_heatmaps(app):
    """Verify single-stock option charts are built from filtered store data."""
    filter_callback = _callback_by_name(app, "options_callback")
    chart_callback = _callback_by_name(app, "single_stock_option_charts_callback")
    filter_result = filter_callback(
        "SPY",
        ["SPY"],
        "CALL",
        ["2026-07-17T00:00:00", "2026-08-21T00:00:00"],
        [0.95, 0.99],
    )

    result = chart_callback(
        filter_result["filtered_options_single_stock"],
        "SPY",
        "CALL",
    )

    assert result["nominal_per_contract_Div"] == "Nominal per contract: 52,000 $"
    assert result["cost_per_contract_Graph"].layout.title.text == (
        "Cost per Contract for SPY CALL Options"
    )
    assert result["option_volume_Graph"].layout.title.text == "Volume for SPY CALL Options"


def test_option_metric_callback_builds_six_metric_figures(app):
    """Verify the metric callback returns figures in the registered output order."""
    filter_callback = _callback_by_name(app, "options_callback")
    metric_callback = _callback_by_name(app, "option_metric_heatmaps_callback")
    filter_result = filter_callback(
        "SPY",
        ["SPY"],
        "CALL",
        ["2026-07-17T00:00:00", "2026-08-21T00:00:00"],
        [0.95, 0.99],
    )

    result = metric_callback(
        filter_result["filtered_options_single_stock"],
        "time_relative_strike",
    )

    assert list(result) == [
        "implied_volatility",
        "delta",
        "gamma",
        "theta",
        "vega",
        "rho",
    ]
    assert result["delta"].layout.xaxis.title.text == "Years to expiry"
    assert result["rho"].layout.title.text == "Rho - SPY"


def test_option_metric_callback_restores_expiration_dates(app):
    """Verify metric heatmaps display expiration dates after store round-trips."""
    filter_callback = _callback_by_name(app, "options_callback")
    metric_callback = _callback_by_name(app, "option_metric_heatmaps_callback")
    filter_result = filter_callback(
        "SPY",
        ["SPY"],
        "CALL",
        ["2026-07-17T00:00:00", "2026-08-21T00:00:00"],
        [0.95, 0.99],
    )

    result = metric_callback(
        filter_result["filtered_options_single_stock"],
        "expiration_strike",
    )

    assert result["implied_volatility"].layout.xaxis.title.text == "Expiration"
    assert list(result["implied_volatility"].data[0].x) == [
        "2026-07-17",
        "2026-08-21",
    ]


def test_option_metric_callback_handles_empty_store(app):
    """Verify the metric callback returns empty-state figures for no store data."""
    metric_callback = _callback_by_name(app, "option_metric_heatmaps_callback")

    result = metric_callback(None, "expiration_strike")

    assert result["implied_volatility"].layout.annotations[0].text == (
        "No metric data for the selected filters"
    )
    assert result["rho"].layout.title.text == "Rho"


def test_stock_info_callbacks_select_items_and_build_grid(app):
    """Verify stock info callbacks shape dropdown values and grid rows."""
    item_callback = _callback_by_name(app, "update_items")
    grid_callback = _callback_by_name(app, "stock_info_callback")

    items = item_callback(["company_profile", "valuation"])
    grid = grid_callback(["SPY", "MSFT"], ["longName", "marketCap"])
    rows_by_symbol = {row["stockSymbol"]: row for row in grid["grid_rows"]}

    assert items["info_items_value"][:2] == ["longName", "country"]
    assert set(rows_by_symbol) == {"SPY", "MSFT"}
    assert rows_by_symbol["SPY"]["marketCap"] == "1,000,000"
    assert rows_by_symbol["MSFT"]["marketCap"] == "2,000,000"
    assert grid["info_status"] == ""
    assert [column["field"] for column in grid["grid_columns"]] == [
        "stockSymbol",
        "longName",
        "marketCap",
    ]


def test_stock_info_callbacks_handle_empty_selections(app):
    """Verify empty stock-info selections use dashboard defaults cleanly."""
    item_callback = _callback_by_name(app, "update_items")
    grid_callback = _callback_by_name(app, "stock_info_callback")

    items = item_callback([])
    grid = grid_callback(None, [])

    assert items == {"info_items_options": {}, "info_items_value": []}
    assert grid["grid_rows"] == []
    assert grid["grid_columns"] == [{"field": "stockSymbol", "rowDrag": True}]
    assert grid["info_status"] == "No stock info items are available for: AAPL."


def test_stock_info_callback_reports_stocks_without_info(app):
    """Verify selected stocks without info rows are shown to the user."""
    grid_callback = _callback_by_name(app, "stock_info_callback")

    grid = grid_callback(["SPY", "TSLA"], ["longName", "marketCap"])

    assert grid["grid_rows"] == [
        {
            "stockSymbol": "SPY",
            "longName": "SPDR S&P 500 ETF Trust",
            "marketCap": "1,000,000",
        }
    ]
    assert grid["info_status"] == "No stock info items are available for: TSLA."


def test_stock_info_callback_reports_stocks_without_selected_items(app):
    """Verify stocks missing the selected info items are shown to the user."""
    grid_callback = _callback_by_name(app, "stock_info_callback")

    grid = grid_callback(["SPY", "MSFT"], ["lastFiscalYearEnd"])

    assert grid["grid_rows"] == [
        {
            "stockSymbol": "SPY",
            "lastFiscalYearEnd": "2026-07-17",
        }
    ]
    assert (
        grid["info_status"]
        == "No selected stock info items are available for: MSFT."
    )


def test_stock_price_and_option_time_series_callbacks(app):
    """Verify time-series callbacks filter source data by selected symbol."""
    stock_callback = _callback_by_name(app, "stockPriceVolumeGraph_callback")
    option_callback = _callback_by_name(app, "optionTimeSeries_callback")

    stock_result = stock_callback("SPY", "max")
    option_result = option_callback("SPY260717C00500000")

    assert stock_result["stockPriceVolumeGraph"].layout.title.text == "SPY"
    assert list(stock_result["stockPriceVolumeGraph"].data[0].y) == [520.0, 522.0]
    assert option_result["optionTimeSeriesGraph"].layout.title.text == (
        "SPY260717C00500000"
    )
    assert list(option_result["optionTimeSeriesGraph"].data[0].y) == [5.0]


def test_chart_callbacks_use_configured_font_sizes(dashboard_parquet_dir):
    """Verify callback-built charts use font sizes from app config."""
    app = create_app(
        AppConfig(
            dashboard_data_dir=str(dashboard_parquet_dir),
            font_sizes=FontSizeConfig(chart=18, chart_hover=19),
        )
    )
    callback = _callback_by_name(app, "stockPriceVolumeGraph_callback")

    result = callback("SPY", "max")
    figure = result["stockPriceVolumeGraph"]

    assert figure.layout.font.size == 18
    assert figure.layout.hoverlabel.font.size == 19


def test_stock_price_callback_filters_date_range(app):
    """Verify stock price range control limits the chart lookback window."""
    prices = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-06-20", "2026-06-01", "2026-06-20"]),
            "close": [400.0, 510.0, 522.0],
            "volume": [900, 1000, 1200],
        }
    )

    result = _filter_price_range(prices, "1m")

    assert result["close"].tolist() == [510.0, 522.0]


def _callback_by_name(app, name: str):
    """Return the undecorated callback body registered under a function name."""
    return next(
        metadata["callback"].__wrapped__
        for metadata in app.callback_map.values()
        if metadata["callback"].__name__ == name
    )
