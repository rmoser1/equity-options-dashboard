"""Tests for parquet-backed dashboard data loading."""

from modules.load_app_data import load_app_data


def test_load_app_data_prepares_filter_and_component_data(dashboard_parquet_dir):
    """Verify loaded parquet data is shaped for components and callbacks."""
    data = load_app_data(dashboard_parquet_dir)

    assert [item["label"] for item in data["expiration_dates_dict"]] == [
        "2026-07-17",
        "2026-08-21",
    ]
    assert [item["value"] for item in data["stock_tickers_dict"]] == ["MSFT", "SPY"]
    assert data["relative_strike_price_range"] == [0.9423, 0.9808]
    assert data["cost_per_contract_range"] == [450.0, 750.0]
    assert data["last_trade_date"] == "2026-06-19"


def test_load_app_data_uses_transformed_stock_info_metadata(dashboard_parquet_dir):
    """Use display-ready values and derive ordered info-item controls."""
    data = load_app_data(dashboard_parquet_dir)
    stock_info = data["stock_info_df"]

    values = {
        (row.stockSymbol, row.itemName): row.itemValue
        for row in stock_info.itertuples(index=False)
    }
    assert values[("SPY", "longName")] == "SPDR S&P 500 ETF Trust"
    assert values[("SPY", "marketCap")] == "1,000,000"
    assert values[("SPY", "lastFiscalYearEnd")] == "2026-07-17"
    assert list(stock_info.columns) == [
        "stockSymbol",
        "itemName",
        "itemValue",
        "itemCategory",
    ]
    assert data["info_items_by_category"] == {
        "company_profile": ["longName", "country"],
        "valuation": ["marketCap"],
        "dividends_corporate_events": ["lastFiscalYearEnd"],
    }
    assert data["info_items_categories"] == [
        "company_profile",
        "valuation",
        "dividends_corporate_events",
    ]
