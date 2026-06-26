"""Integration tests for the dashboard data package."""

from dataclasses import dataclass
from datetime import date

import polars as pl
import pytest

from dashboard_data.dashboard_data_app import App
from dashboard_data.pipeline import DashboardPipeline
from dashboard_data.repository import DashboardRepository
from dashboard_data.transformer import DashboardTransformer
from dashboard_data.writer import ParquetWriter
from database import Database
from schemas.historical_price import HistoricalPrice
from schemas.interest_rate import InterestRate
from schemas.option_contract import OptionContract, OptionDirection
from schemas.stock_info import StockInfoItem
from schemas.underlying import Underlying


@dataclass
class DashboardConfig:
    """Configuration object for dashboard app integration tests.

    :param db_path: Path to the SQLite database used by the dashboard app.
    :param dashboard_data_dir: Directory where dashboard parquet files are written.
    """

    db_path: str
    dashboard_data_dir: str


@pytest.fixture
def dashboard_db(tmp_path):
    """Create an initialized temporary SQLite database for dashboard tests.

    :param tmp_path: Pytest temporary directory fixture used for the database.
    :returns: Tuple containing the database path and initialized database helper.
    """
    db_path = tmp_path / "dashboard.db"
    db = Database(str(db_path), model_package="schemas")
    db.create_all_tables()
    return db_path, db


def seed_dashboard_rows(db, strike: float = 100.0):
    """Insert a minimal dashboard dataset.

    :param db: Database helper used to insert SQLModel rows.
    :param strike: Option strike price to store for the seeded contract.
    """
    db.insert_many([Underlying(symbol="AAPL", name="Apple")])
    db.insert_many(
        [
            StockInfoItem(stockSymbol="AAPL", itemName="sector", itemValue='"Technology"'),
            StockInfoItem(stockSymbol="AAPL", itemName="Dividend Yield", itemValue="0.012"),
        ]
    )
    db.insert_many(
        [
            InterestRate(ticker="^IRX", name="13 Week Treasury Bill", date=date(2026, 1, 2), rate=0.04),
            InterestRate(ticker="^FVX", name="5 Year Treasury Note", date=date(2026, 1, 2), rate=0.05),
        ]
    )
    db.insert_many(
        [
            OptionContract(
                contractSymbol="AAPL260116C00100000",
                stockSymbol="AAPL",
                expirationDate=date(2026, 1, 16),
                lastTradeDate=date(2026, 1, 2),
                strike=strike,
                direction=OptionDirection.CALL,
                lastPrice=2.25,
                bid=2.0,
                ask=2.5,
                volume=20,
                openInterest=200,
                contractSize="REGULAR",
                currency="USD",
            )
        ]
    )
    db.insert_many(
        [
            HistoricalPrice(
                date=date(2026, 1, 2),
                symbol="AAPL",
                open=95.0,
                high=105.0,
                low=94.0,
                close=100.0,
                volume=1000,
            )
        ]
    )


def test_repository_loads_dashboard_data_from_sqlite(dashboard_db):
    """Load dashboard datasets from a real temporary SQLite database.

    :param dashboard_db: Initialized temporary SQLite database fixture.
    """
    db_path, db = dashboard_db
    seed_dashboard_rows(db)
    db.insert_many([Underlying(symbol="MSFT", name="Microsoft")])
    db.insert_many([StockInfoItem(stockSymbol="MSFT", itemName="sector", itemValue='"Technology"')])

    data = DashboardRepository(str(db_path)).load_all()

    assert set(data) == {"stocks", "stock_info", "interest_rates", "options", "stock_prices"}
    assert data["stocks"].sort("symbol").to_dicts() == [
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
    ]
    assert data["stock_info"].sort("stockSymbol", "itemName").to_dicts() == [
        {"stockSymbol": "AAPL", "itemName": "Dividend Yield", "itemValue": "0.012"},
        {"stockSymbol": "AAPL", "itemName": "sector", "itemValue": '"Technology"'},
        {"stockSymbol": "MSFT", "itemName": "sector", "itemValue": '"Technology"'},
    ]
    assert data["interest_rates"].sort("ticker").select("ticker", "rate").to_dicts() == [
        {"ticker": "^FVX", "rate": 0.05},
        {"ticker": "^IRX", "rate": 0.04},
    ]
    assert data["options"].columns == [
        "contractSymbol",
        "stockSymbol",
        "lastTradeDate",
        "expirationDate",
        "strike",
        "ask",
        "volume",
        "openInterest",
        "contractSize",
        "direction",
    ]
    assert data["options"].select(
        "contractSymbol",
        "stockSymbol",
        "strike",
        "ask",
        "volume",
        "openInterest",
        "contractSize",
        "direction",
    ).to_dicts() == [
        {
            "contractSymbol": "AAPL260116C00100000",
            "stockSymbol": "AAPL",
            "strike": 100.0,
            "ask": 2.5,
            "volume": 20,
            "openInterest": 200,
            "contractSize": "REGULAR",
            "direction": "CALL",
        }
    ]
    assert data["stock_prices"].columns == ["symbol", "date", "close", "volume"]
    assert data["stock_prices"].select("symbol", "close", "volume").to_dicts() == [
        {"symbol": "AAPL", "close": 100.0, "volume": 1000}
    ]


def test_repository_omits_non_dashboard_columns(dashboard_db):
    """Return only the narrowed columns used by the dashboard.

    :param dashboard_db: Initialized temporary SQLite database fixture.
    """
    db_path, _ = dashboard_db

    data = DashboardRepository(str(db_path)).load_all()

    assert "lastPrice" not in data["options"].columns
    assert "bid" not in data["options"].columns
    assert "open" not in data["stock_prices"].columns
    assert "high" not in data["stock_prices"].columns
    assert "low" not in data["stock_prices"].columns


def test_writer_writes_all_expected_parquet_files(tmp_path):
    """Write each transformed dashboard dataset as a parquet file.

    :param tmp_path: Pytest temporary directory fixture used for output files.
    """
    data = {
        key: pl.DataFrame({"value": [1]})
        for key in ["stocks", "options_hist", "options_last", "stock_info", "stock_prices"]
    }

    ParquetWriter(str(tmp_path)).write(data)

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "options_hist.parquet",
        "options_last.parquet",
        "stock_info.parquet",
        "stock_prices.parquet",
        "stocks.parquet",
    ]


def test_pipeline_reads_transforms_and_writes_parquet(tmp_path, dashboard_db):
    """Run the dashboard pipeline across repository, transformer, and writer.

    :param tmp_path: Pytest temporary directory fixture used for output files.
    :param dashboard_db: Initialized temporary SQLite database fixture.
    """
    db_path, db = dashboard_db
    output_dir = tmp_path / "parquet"
    output_dir.mkdir()
    seed_dashboard_rows(db, strike=110.0)

    DashboardPipeline(
        repository=DashboardRepository(str(db_path)),
        transformer=DashboardTransformer(),
        writer=ParquetWriter(str(output_dir)),
    ).run()

    options_last = pl.read_parquet(output_dir / "options_last.parquet")
    assert options_last.select(
        "contractSymbol",
        "relativeStrikePrice",
        "riskFreeRate",
        "dividendYield",
        "timeToExpiryYears",
    ).to_dicts() == [
        {
            "contractSymbol": "AAPL260116C00100000",
            "relativeStrikePrice": 1.1,
            "riskFreeRate": 0.04,
            "dividendYield": 0.012,
            "timeToExpiryYears": round(14 / 365, 6),
        }
    ]


def test_app_creates_output_dir_and_writes_dashboard_parquet(tmp_path, dashboard_db):
    """Run the dashboard app with real components and parquet output.

    :param tmp_path: Pytest temporary directory fixture used for output files.
    :param dashboard_db: Initialized temporary SQLite database fixture.
    """
    db_path, db = dashboard_db
    output_dir = tmp_path / "dashboard"
    seed_dashboard_rows(db, strike=110.0)

    App(DashboardConfig(db_path=str(db_path), dashboard_data_dir=str(output_dir))).run()

    assert sorted(path.name for path in output_dir.iterdir()) == [
        "options_hist.parquet",
        "options_last.parquet",
        "stock_info.parquet",
        "stock_prices.parquet",
        "stocks.parquet",
    ]
    options_last = pl.read_parquet(output_dir / "options_last.parquet")
    assert options_last.select("contractSymbol", "relativeStrikePrice").to_dicts() == [
        {"contractSymbol": "AAPL260116C00100000", "relativeStrikePrice": 1.1}
    ]
