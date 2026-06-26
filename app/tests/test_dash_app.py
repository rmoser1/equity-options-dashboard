"""Dash app factory, layout, and callback registration tests."""

from pathlib import Path
import re

from dash import dcc
import pandas as pd
import pytest


from config import (
    AppConfig,
    DEFAULT_FONT_SIZE_PRESET,
    DEFAULT_FONT_SIZES,
    FontSizeConfig,
    LARGE_FONT_SIZES,
    SMALL_FONT_SIZES,
    get_font_size_preset,
)
from dash_app import create_app


APP_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(dashboard_parquet_dir):
    """Create the Dash app from minimal dashboard parquet files."""
    return create_app(AppConfig(dashboard_data_dir=str(dashboard_parquet_dir)))


def test_create_app_builds_layout_from_temp_parquet(app):
    """Verify the app factory builds the full layout from valid parquet data."""
    assert _component_by_id(app.layout, "APP_Shell") is not None
    assert _heading_texts(app.layout, "H1") == ["Equity Options Dashboard"]
    assert _component_by_id(app.layout, "STORE_SelectedSingleStock").data == "SPY"
    assert any("STORE_FilteredOptionsSingleStock" in key for key in app.callback_map)


def test_create_app_exposes_configured_font_sizes(dashboard_parquet_dir):
    """Verify the app shell publishes font-size config as CSS variables."""
    font_sizes = FontSizeConfig(body=19, app_title=42, chart=18)
    app = create_app(
        AppConfig(
            dashboard_data_dir=str(dashboard_parquet_dir),
            font_sizes=font_sizes,
        )
    )

    shell = _component_by_id(app.layout, "APP_Shell")

    assert shell.style["--font-size-body"] == "19px"
    assert shell.style["--font-size-app-title"] == "42px"
    assert shell.style["fontSize"] == "var(--font-size-body)"


def test_create_app_uses_named_font_size_preset(dashboard_parquet_dir):
    """Verify the app shell uses the centrally selected font-size preset."""
    app = create_app(
        AppConfig(
            dashboard_data_dir=str(dashboard_parquet_dir),
            font_size_preset="large",
        )
    )

    shell = _component_by_id(app.layout, "APP_Shell")

    assert shell.style["--font-size-body"] == f"{LARGE_FONT_SIZES.body}px"
    assert shell.style["--font-size-app-title"] == f"{LARGE_FONT_SIZES.app_title}px"


def test_app_config_resolves_default_font_size_preset():
    """Verify default app config resolves to the configured typography preset."""
    assert AppConfig().resolved_font_sizes == get_font_size_preset(
        DEFAULT_FONT_SIZE_PRESET
    )

def test_app_config_reads_font_size_preset_from_env(monkeypatch):
    """Verify env config can centrally select the dashboard typography preset."""
    monkeypatch.setenv("DASHBOARD_FONT_SIZE_PRESET", "small")

    config = AppConfig.from_env()

    assert config.resolved_font_sizes == SMALL_FONT_SIZES


def test_app_config_reports_unknown_font_size_preset():
    """Verify invalid typography presets fail with the available options."""
    with pytest.raises(ValueError, match="Unknown font size preset 'huge'"):
        get_font_size_preset("huge")


def test_create_app_registers_option_metric_components(app):
    """Verify metric controls and charts are present in the app layout."""
    ids = _layout_ids(app.layout)

    assert "SELECTOR_MetricAxisModeRadioItems" in ids
    assert {
        "CHART_CalculatedImpliedVolatility",
        "CHART_Delta",
        "CHART_Gamma",
        "CHART_Theta",
        "CHART_Vega",
        "CHART_Rho",
    }.issubset(ids)
    assert any("CHART_CalculatedImpliedVolatility" in key for key in app.callback_map)


def test_option_metric_info_markers_are_clickable_disclosures(app):
    """Verify metric descriptions use click-open disclosure elements."""
    details = [
        item
        for item in _walk_layout(app.layout)
        if type(item).__name__ == "Details"
        and getattr(item, "className", None) == "info-details"
    ]

    assert len(details) == 6
    assert details[0].children[0].children == "i"
    assert details[0].children[1].children.startswith("Market-implied")


def test_create_app_uses_dashboard_tabs(app):
    """Verify the app shell splits views into workflow tabs."""
    tabs = _component_by_id(app.layout, "APP_Tabs")

    assert tabs.value == "options"
    assert [tab.value for tab in tabs.children] == [
        "options",
        "stock_info",
        "stock_prices",
    ]
    assert isinstance(tabs, dcc.Tabs)


def test_create_app_shows_plain_data_status(app):
    """Verify the header data status uses the updated wording."""
    status = _component_by_id(app.layout, "TEXT_LastTradeDateDiv")

    assert status.children == "Data as of 2026-06-19"
    assert status.className == "dataset-status"


def test_create_app_shares_option_filters_across_option_tabs(app):
    """Verify shared option filters only hold option-universe controls."""
    shared_filter_panel = _component_by_id(app.layout, "PANEL_OptionFilters")
    option_tabs = _component_by_id(app.layout, "APP_OptionTabs")
    shared_filter_ids = _layout_ids(shared_filter_panel)
    nested_tab_ids = _layout_ids(option_tabs)

    assert option_tabs.value == "option_prices"
    assert [tab.value for tab in option_tabs.children] == [
        "option_prices",
        "option_metrics",
    ]
    assert {
        "SELECTOR_DirectionRadioItems",
        "SELECTOR_ExpirationDateDropdown",
        "SELECTOR_RelativeStrikePriceRangeSlider",
    }.issubset(shared_filter_ids)
    assert "SELECTOR_StockSelectionDropdown_SingleStock" not in shared_filter_ids
    assert "SELECTOR_StockSelectionDropdown_MultipleStocks" not in shared_filter_ids
    assert "TEXT_MultipleStockFilterSummary" not in shared_filter_ids
    assert shared_filter_ids.isdisjoint(nested_tab_ids)


def test_create_app_splits_option_prices_into_workflow_tabs(app):
    """Verify option price views are split into task-focused subtabs."""
    option_price_tabs = _component_by_id(app.layout, "APP_OptionPriceTabs")
    multiple_stocks_tab = _tab_by_value(option_price_tabs, "multiple_stocks")
    single_stock_tab = _tab_by_value(option_price_tabs, "single_stock")
    contract_tab = _tab_by_value(option_price_tabs, "option_contract")

    assert isinstance(option_price_tabs, dcc.Tabs)
    assert option_price_tabs.value == "multiple_stocks"
    assert [tab.value for tab in option_price_tabs.children] == [
        "multiple_stocks",
        "single_stock",
        "option_contract",
    ]
    assert [tab.label for tab in option_price_tabs.children] == [
        "Multiple stocks",
        "Single stock",
        "Single contract",
    ]
    assert {
        "SELECTOR_StockSelectionDropdown_MultipleStocks",
        "TEXT_MultipleStockFilterSummary",
    }.issubset(_layout_ids(multiple_stocks_tab))
    assert {
        "SELECTOR_StockSelectionDropdown_SingleStock",
        "TEXT_SingleStockFilterSummary",
    }.issubset(_layout_ids(single_stock_tab))
    assert {
        "SELECTOR_StockSelectionDropdown_Contract",
        "SELECTOR_ContractSelectionDropdown",
        "TEXT_ContractFilterSummary",
    }.issubset(_layout_ids(contract_tab))


def test_create_app_places_metric_single_stock_selector_in_metrics_tab(app):
    """Verify option metrics exposes its synced single-stock selector."""
    metric_tab = _tab_by_value(_component_by_id(app.layout, "APP_OptionTabs"), "option_metrics")

    assert "SELECTOR_StockSelectionDropdown_Metrics" in _layout_ids(metric_tab)
    assert "TEXT_MetricFilterSummary" in _layout_ids(metric_tab)


def test_single_stock_option_nominal_value_is_in_metric_note(app):
    """Verify the nominal per-contract value is presented as a styled note."""
    nominal_note = next(
        item
        for item in _walk_layout(app.layout)
        if getattr(item, "className", None) == "metric-note"
    )

    assert "TEXT_NominalPerContractDiv" in _layout_ids(nominal_note)


def test_option_filter_summaries_are_inside_stock_filter_cards(app):
    """Verify option summary chips sit inside the relevant stock filter card."""
    for summary_id, selector_id in [
        (
            "TEXT_MultipleStockFilterSummary",
            "SELECTOR_StockSelectionDropdown_MultipleStocks",
        ),
        ("TEXT_SingleStockFilterSummary", "SELECTOR_StockSelectionDropdown_SingleStock"),
        ("TEXT_ContractFilterSummary", "SELECTOR_StockSelectionDropdown_Contract"),
        ("TEXT_MetricFilterSummary", "SELECTOR_StockSelectionDropdown_Metrics"),
    ]:
        parent = _parent_by_child_ids(app.layout, {summary_id, selector_id})

        assert parent is not None
        assert parent.className == "field-group"


def test_filter_cards_share_equal_height_css(app):
    """Verify filter rows and their direct cards have the equal-height contract."""
    filter_bands = [
        item
        for item in _walk_layout(app.layout)
        if _class_names(item) & {"filter-band"}
    ]
    css = (APP_DIR / "assets" / "dashboard.css").read_text()

    assert filter_bands
    for filter_band in filter_bands:
        filter_controls = [
            child
            for child in _children(filter_band)
            if type(child).__name__ != "H2"
        ]

        assert filter_controls
        assert all("field-group" in _class_names(control) for control in filter_controls)

    assert _css_rule(css, ".filter-band")["display"] == "grid"
    assert _css_rule(css, ".filter-band")["align-items"] == "stretch"
    assert _css_rule(css, ".field-group")["height"] == "100%"


def test_tab_strips_use_shared_blue_top_rule(app):
    """Verify tab levels use a shared blue line instead of selected-tab accents."""
    dashboard_tabs = _component_by_id(app.layout, "APP_Tabs")
    nested_tabs = [
        _component_by_id(app.layout, "APP_OptionTabs"),
        _component_by_id(app.layout, "APP_OptionPriceTabs"),
    ]
    css = (APP_DIR / "assets" / "dashboard.css").read_text()

    assert dashboard_tabs.className == "dashboard-tabs"
    assert dashboard_tabs.parent_className == "dashboard-tabs-wrap"
    for tabs in nested_tabs:
        assert "nested-tabs" in _class_names(tabs)
        assert "nested-tabs-wrap" in _class_name_tokens(tabs.parent_className)

    assert _css_rule(css, ".dashboard-tabs-wrap")["border-top"] == "3px solid #087f8c"
    assert _css_rule(css, ".nested-tabs-wrap")["border-top"] == "3px solid #087f8c"
    assert (
        _css_rule(css, ".dashboard-tabs .tab--selected")["border-top"]
        == "0 !important"
    )
    assert _css_rule(css, ".nested-tabs .tab--selected")["border-top"] == "0 !important"
    assert "border-bottom" not in _css_rule(css, ".dashboard-tabs .tab--selected")
    assert "border-bottom" not in _css_rule(css, ".nested-tabs .tab--selected")


def test_create_app_registers_stock_price_range_control(app):
    """Verify stock price view exposes a range selector."""
    selector = _component_by_id(app.layout, "SELECTOR_StockPriceRangeRadioItems")

    assert selector.value == "1y"
    assert [option["value"] for option in selector.options] == ["1m", "1y", "5y", "max"]


def test_create_app_registers_stock_info_status(app):
    """Verify stock info view has a user-facing empty-data status."""
    status = _component_by_id(app.layout, "TEXT_StockInfoStatus")

    assert status is not None
    assert status.className == "table-status"


def test_create_app_shows_missing_data_layout_for_missing_parquet(tmp_path):
    """Verify the app shows a startup state when parquet files are missing."""
    app = create_app(AppConfig(dashboard_data_dir=str(tmp_path)))

    assert _heading_texts(app.layout, "H2") == ["Data unavailable"]
    assert app.callback_map == {}


def test_create_app_shows_exception_layout_for_invalid_parquet(dashboard_parquet_dir):
    """Verify invalid parquet contracts are surfaced in the startup layout."""
    invalid_options = dashboard_parquet_dir / "options_last.parquet"
    invalid_options.unlink()
    pd.DataFrame({"contractSymbol": ["SPY260717C00500000"]}).to_parquet(
        invalid_options,
        index=False,
    )
    app = create_app(AppConfig(dashboard_data_dir=str(dashboard_parquet_dir)))

    assert _heading_texts(app.layout, "H2") == ["An exception occurred"]
    assert "options_last.parquet is missing columns" in _text_content(app.layout)


def _layout_ids(component) -> set[str]:
    """Collect component IDs from a Dash layout tree."""
    return {
        item.id
        for item in _walk_layout(component)
        if getattr(item, "id", None) is not None
    }


def _component_by_id(component, component_id: str):
    """Find one component by ID in a Dash layout tree."""
    return next(
        (
            item
            for item in _walk_layout(component)
            if getattr(item, "id", None) == component_id
        ),
        None,
    )


def _tab_by_value(tabs, value: str):
    """Find one Dash tab by value."""
    return next(tab for tab in tabs.children if tab.value == value)


def _parent_by_child_ids(component, child_ids: set[str]):
    """Find one component with all child IDs somewhere below it."""
    return next(
        (
            item
            for item in _walk_layout(component)
            if getattr(item, "className", None) == "field-group"
            and child_ids.issubset(_layout_ids(item) - {getattr(item, "id", None)})
        ),
        None,
    )


def _heading_texts(component, heading_name: str) -> list[str]:
    """Collect heading text by Dash component class name."""
    return [
        item.children
        for item in _walk_layout(component)
        if type(item).__name__ == heading_name
    ]


def _text_content(component) -> str:
    """Collect textual content from a Dash layout tree."""
    return " ".join(
        item
        for layout_item in _walk_layout(component)
        for item in [getattr(layout_item, "children", None)]
        if isinstance(item, str)
    )


def _children(component) -> list:
    """Return a component's direct children as a list."""
    children = getattr(component, "children", None)
    if children is None:
        return []
    if isinstance(children, list):
        return children
    return [children]


def _class_names(component) -> set[str]:
    """Return className tokens from a Dash component."""
    return _class_name_tokens(getattr(component, "className", None))


def _class_name_tokens(class_name: str | None) -> set[str]:
    """Return className tokens from a class string."""
    if not class_name:
        return set()
    return set(class_name.split())


def _css_rule(css: str, selector: str) -> dict[str, str]:
    """Return declarations for a simple CSS selector."""
    match = next(
        (
            match
            for match in re.finditer(r"([^{}]+)\{([^}]+)\}", css)
            if selector in {item.strip() for item in match.group(1).split(",")}
        ),
        None,
    )
    assert match is not None
    declarations = {}
    for line in match.group(2).split(";"):
        if ":" not in line:
            continue
        property_name, value = line.split(":", maxsplit=1)
        declarations[property_name.strip()] = value.strip()
    return declarations


def _walk_layout(component):
    """Yield each item in a Dash layout tree."""
    if isinstance(component, list):
        for child in component:
            yield from _walk_layout(child)
        return

    yield component

    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, list):
        children = [children]
    for child in children:
        yield from _walk_layout(child)
