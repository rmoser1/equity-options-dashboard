"""Shared fixtures for Dash application tests."""

from pathlib import Path
import json
import sys

import pandas as pd
import pytest


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


@pytest.fixture
def dashboard_parquet_dir(tmp_path):
    """Create a realistic dashboard parquet bundle."""
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir()
    write_dashboard_parquet(parquet_dir)
    return parquet_dir


def write_dashboard_parquet(parquet_dir: Path) -> None:
    """Write dashboard parquet datasets with multiple stocks and contracts."""
    trade_date = pd.Timestamp("2026-06-19")
    next_trade_date = pd.Timestamp("2026-06-20")
    july_expiration = pd.Timestamp("2026-07-17")
    august_expiration = pd.Timestamp("2026-08-21")

    pd.DataFrame(
        [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust"},
            {"symbol": "MSFT", "name": "Microsoft Corporation"},
        ]
    ).to_parquet(parquet_dir / "stocks.parquet", index=False)
    pd.DataFrame(
        [
            {
                "contractSymbol": "SPY260717C00500000",
                "lastTradeDate": trade_date,
                "ask": 5.0,
                "volume": 10,
                "openInterest": 20,
            },
            {
                "contractSymbol": "SPY260821C00510000",
                "lastTradeDate": next_trade_date,
                "ask": 7.5,
                "volume": 12,
                "openInterest": 24,
            },
            {
                "contractSymbol": "MSFT260717C00350000",
                "lastTradeDate": trade_date,
                "ask": 6.0,
                "volume": 8,
                "openInterest": 16,
            },
        ]
    ).to_parquet(parquet_dir / "options_hist.parquet", index=False)
    pd.DataFrame(
        [
            _option_row(
                contract_symbol="SPY260717C00500000",
                stock_symbol="SPY",
                expiration_date=july_expiration,
                strike=500.0,
                ask=5.0,
                direction="CALL",
                last_stock_price=520.0,
                relative_strike_price=0.9615,
                relative_option_price=0.0096,
                cost_per_contract=500.0,
                nominal_per_contract=52000.0,
                time_to_expiry_years=0.0767,
                calculated_implied_volatility=0.20,
                delta=0.60,
                gamma=0.010,
                theta=-0.020,
                vega=0.10,
                rho=0.050,
            ),
            _option_row(
                contract_symbol="SPY260821C00510000",
                stock_symbol="SPY",
                expiration_date=august_expiration,
                strike=510.0,
                ask=7.5,
                direction="CALL",
                last_stock_price=520.0,
                relative_strike_price=0.9808,
                relative_option_price=0.0144,
                cost_per_contract=750.0,
                nominal_per_contract=52000.0,
                time_to_expiry_years=0.1726,
                calculated_implied_volatility=0.25,
                delta=0.70,
                gamma=0.020,
                theta=-0.030,
                vega=0.20,
                rho=0.060,
            ),
            _option_row(
                contract_symbol="SPY260717P00490000",
                stock_symbol="SPY",
                expiration_date=july_expiration,
                strike=490.0,
                ask=4.5,
                direction="PUT",
                last_stock_price=520.0,
                relative_strike_price=0.9423,
                relative_option_price=0.0087,
                cost_per_contract=450.0,
                nominal_per_contract=52000.0,
                time_to_expiry_years=0.0767,
                calculated_implied_volatility=0.30,
                delta=-0.35,
                gamma=0.015,
                theta=-0.025,
                vega=0.12,
                rho=-0.040,
            ),
            _option_row(
                contract_symbol="MSFT260717C00350000",
                stock_symbol="MSFT",
                expiration_date=july_expiration,
                strike=350.0,
                ask=6.0,
                direction="CALL",
                last_stock_price=360.0,
                relative_strike_price=0.9722,
                relative_option_price=0.0167,
                cost_per_contract=600.0,
                nominal_per_contract=36000.0,
                time_to_expiry_years=0.0767,
                calculated_implied_volatility=0.22,
                delta=0.58,
                gamma=0.018,
                theta=-0.021,
                vega=0.11,
                rho=0.045,
            ),
        ]
    ).to_parquet(parquet_dir / "options_last.parquet", index=False)
    pd.DataFrame(
        [
            _info_row("SPY", "longName", "SPDR S&P 500 ETF Trust"),
            _info_row("SPY", "marketCap", 1_000_000),
            _info_row("SPY", "lastFiscalYearEnd", 1784246400),
            _info_row("MSFT", "longName", "Microsoft Corporation"),
            _info_row("MSFT", "marketCap", 2_000_000),
        ]
    ).to_parquet(parquet_dir / "stock_info.parquet", index=False)
    pd.DataFrame(
        [
            {"symbol": "SPY", "date": trade_date, "close": 520.0, "volume": 1000},
            {"symbol": "SPY", "date": next_trade_date, "close": 522.0, "volume": 1200},
            {"symbol": "MSFT", "date": trade_date, "close": 360.0, "volume": 800},
        ]
    ).to_parquet(parquet_dir / "stock_prices.parquet", index=False)


def _option_row(
    *,
    contract_symbol: str,
    stock_symbol: str,
    expiration_date: pd.Timestamp,
    strike: float,
    ask: float,
    direction: str,
    last_stock_price: float,
    relative_strike_price: float,
    relative_option_price: float,
    cost_per_contract: float,
    nominal_per_contract: float,
    time_to_expiry_years: float,
    calculated_implied_volatility: float,
    delta: float,
    gamma: float,
    theta: float,
    vega: float,
    rho: float,
) -> dict:
    """Create one options-last parquet row."""
    return {
        "contractSymbol": contract_symbol,
        "stockSymbol": stock_symbol,
        "lastTradeDate": pd.Timestamp("2026-06-19"),
        "expirationDate": expiration_date,
        "strike": strike,
        "ask": ask,
        "volume": 10,
        "openInterest": 20,
        "direction": direction,
        "lastStockPrice": last_stock_price,
        "relativeStrikePrice": relative_strike_price,
        "relativeOptionPrice": relative_option_price,
        "costPerContract": cost_per_contract,
        "nominalPerContract": nominal_per_contract,
        "timeToExpiryYears": time_to_expiry_years,
        "riskFreeRate": 0.04,
        "dividendYield": 0.01,
        "calculatedImpliedVolatility": calculated_implied_volatility,
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
        "rho": rho,
    }


def _info_row(stock_symbol: str, item_name: str, item_value) -> dict:
    """Create one JSON-encoded stock-info row."""
    return {
        "stockSymbol": stock_symbol,
        "itemName": item_name,
        "itemValue": json.dumps(item_value),
    }
