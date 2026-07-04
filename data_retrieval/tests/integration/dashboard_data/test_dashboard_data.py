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


SYMBOL = "AAPL"
CONTRACT_SYMBOL = "AAPL260116C00100000"
TRADE_DATE = date(2026, 1, 2)
OLD_TRADE_DATE = date(2026, 1, 1)
EXPIRATION_DATE = date(2026, 1, 16)
OPTION_COLUMNS = [
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
OPTION_HISTORY_COLUMNS = [
    "contractSymbol",
    "lastTradeDate",
    "ask",
    "volume",
    "openInterest",
]
STOCK_PRICE_COLUMNS = ["symbol", "date", "close", "volume"]
DASHBOARD_DATASETS = ["stocks", "options_hist", "options_last", "stock_info", "stock_prices"]
PARQUET_FILES = sorted(f"{key}.parquet" for key in DASHBOARD_DATASETS)


@dataclass
class DashboardConfig:
    """Dashboard app configuration for integration tests."""

    db_path: str
    dashboard_data_dir: str


@pytest.fixture
def dashboard_db(tmp_path):
    """Create an initialized temporary SQLite database."""
    db_path = tmp_path / "dashboard.db"
    db = Database(str(db_path), model_package="schemas")
    db.create_all_tables()
    return db_path, db


@pytest.fixture
def seeded_dashboard_db(dashboard_db):
    """Create a temporary SQLite database with baseline dashboard rows."""
    _, db = dashboard_db
    seed_dashboard_rows(db)
    return dashboard_db


def seed_dashboard_rows(db, strike: float = 100.0):
    """Insert the baseline dashboard dataset."""
    db.insert_many([Underlying(symbol=SYMBOL, name="Apple")])
    db.insert_many(
        [
            StockInfoItem(stockSymbol=SYMBOL, itemName="sector", itemValue='"Technology"'),
            StockInfoItem(stockSymbol=SYMBOL, itemName="Dividend Yield", itemValue="0.012"),
        ]
    )
    db.insert_many(
        [
            InterestRate(ticker="^IRX", name="13 Week Treasury Bill", date=TRADE_DATE, rate=0.04),
            InterestRate(ticker="^FVX", name="5 Year Treasury Note", date=TRADE_DATE, rate=0.05),
        ]
    )
    db.insert_many(
        [
            OptionContract(
                contractSymbol=CONTRACT_SYMBOL,
                stockSymbol=SYMBOL,
                expirationDate=EXPIRATION_DATE,
                lastTradeDate=TRADE_DATE,
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
                date=TRADE_DATE,
                symbol=SYMBOL,
                open=95.0,
                high=105.0,
                low=94.0,
                close=100.0,
                volume=1000,
            )
        ]
    )


def test_repository_loads_dashboard_data_from_sqlite(seeded_dashboard_db):
    """Load each dashboard dataset from SQLite."""
    db_path, db = seeded_dashboard_db
    db.insert_many([Underlying(symbol="MSFT", name="Microsoft")])
    db.insert_many([StockInfoItem(stockSymbol="MSFT", itemName="sector", itemValue='"Technology"')])

    repository = DashboardRepository(str(db_path))

    assert repository.load_stocks().sort("symbol").to_dicts() == [
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
    ]
    assert repository.load_stock_info().sort("stockSymbol", "itemName").to_dicts() == [
        {"stockSymbol": "AAPL", "itemName": "Dividend Yield", "itemValue": "0.012"},
        {"stockSymbol": "AAPL", "itemName": "sector", "itemValue": '"Technology"'},
        {"stockSymbol": "MSFT", "itemName": "sector", "itemValue": '"Technology"'},
    ]
    assert repository.load_interest_rates().sort("ticker").select("ticker", "rate").to_dicts() == [
        {"ticker": "^FVX", "rate": 0.05},
        {"ticker": "^IRX", "rate": 0.04},
    ]
    latest_options = repository.load_latest_options(TRADE_DATE)
    assert latest_options.columns == OPTION_COLUMNS
    assert latest_options.select(
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
            "contractSymbol": CONTRACT_SYMBOL,
            "stockSymbol": SYMBOL,
            "strike": 100.0,
            "ask": 2.5,
            "volume": 20,
            "openInterest": 200,
            "contractSize": "REGULAR",
            "direction": "CALL",
        }
    ]
    stock_prices = repository.load_stock_prices()
    assert stock_prices.columns == STOCK_PRICE_COLUMNS
    assert stock_prices.select("symbol", "close", "volume").to_dicts() == [
        {"symbol": "AAPL", "close": 100.0, "volume": 1000}
    ]


def test_repository_omits_non_dashboard_columns(seeded_dashboard_db):
    """Return only the columns consumed by dashboard exports."""
    db_path, _ = seeded_dashboard_db
    repository = DashboardRepository(str(db_path))
    latest_options = repository.load_latest_options(TRADE_DATE)
    stock_prices = repository.load_stock_prices()

    assert "lastPrice" not in latest_options.columns
    assert "bid" not in latest_options.columns
    assert "open" not in stock_prices.columns
    assert "high" not in stock_prices.columns
    assert "low" not in stock_prices.columns


def test_repository_loads_memory_efficient_dashboard_slices(seeded_dashboard_db):
    """Load latest-date slices without loading the full raw payload."""
    db_path, db = seeded_dashboard_db
    db.insert_many(
        [
            OptionContract(
                contractSymbol="AAPL260116C00090000",
                stockSymbol=SYMBOL,
                expirationDate=EXPIRATION_DATE,
                lastTradeDate=OLD_TRADE_DATE,
                strike=90.0,
                direction=OptionDirection.CALL,
                lastPrice=1.25,
                bid=1.0,
                ask=1.5,
                volume=10,
                openInterest=100,
                contractSize="REGULAR",
                currency="USD",
            ),
        ]
    )
    db.insert_many(
        [
            HistoricalPrice(
                date=OLD_TRADE_DATE,
                symbol=SYMBOL,
                open=90.0,
                high=100.0,
                low=89.0,
                close=95.0,
                volume=900,
            )
        ]
    )
    repository = DashboardRepository(str(db_path))

    assert repository.latest_option_trade_date() == TRADE_DATE
    assert repository.load_options_history().columns == OPTION_HISTORY_COLUMNS
    latest_contracts = (
        repository.load_latest_options(TRADE_DATE)
        .select("contractSymbol")
        .to_series()
        .to_list()
    )
    assert latest_contracts == [CONTRACT_SYMBOL]
    assert repository.load_latest_stock_prices(TRADE_DATE).to_dicts() == [
        {"symbol": SYMBOL, "lastStockPrice": 100.0}
    ]


def test_writer_writes_datasets_to_expected_parquet_files(tmp_path):
    """Write one parquet file per dashboard dataset."""
    writer = ParquetWriter(str(tmp_path))

    for key in DASHBOARD_DATASETS:
        writer.write_dataset(key, pl.DataFrame({"value": [1]}))

    assert sorted(path.name for path in tmp_path.iterdir()) == PARQUET_FILES


def test_pipeline_writes_memory_efficient_datasets_incrementally():
    """Write narrowed datasets one at a time."""

    class RepositoryStub:
        def __init__(self):
            self.calls = []

        def _load(self, name, data):
            self.calls.append(name)
            return data

        def load_stocks(self):
            return self._load("load_stocks", pl.DataFrame({"symbol": [SYMBOL]}))

        def load_stock_info(self):
            return self._load(
                "load_stock_info",
                pl.DataFrame(
                    {"stockSymbol": [SYMBOL], "itemName": ["sector"], "itemValue": ['"Tech"']}
                ),
            )

        def load_stock_prices(self):
            return self._load(
                "load_stock_prices",
                pl.DataFrame({"symbol": [SYMBOL], "date": [TRADE_DATE], "close": [100.0]}),
            )

        def load_options_history(self):
            return self._load(
                "load_options_history",
                pl.DataFrame({"contractSymbol": [CONTRACT_SYMBOL]}),
            )

        def latest_option_trade_date(self):
            self.calls.append("latest_option_trade_date")
            return TRADE_DATE

        def load_latest_options(self, last_trade_date):
            self.calls.append(("load_latest_options", last_trade_date))
            return pl.DataFrame({"contractSymbol": [CONTRACT_SYMBOL]})

        def load_latest_stock_prices(self, last_trade_date):
            self.calls.append(("load_latest_stock_prices", last_trade_date))
            return pl.DataFrame({"symbol": [SYMBOL], "lastStockPrice": [100.0]})

        def load_interest_rates(self):
            return self._load(
                "load_interest_rates",
                pl.DataFrame({"ticker": ["^IRX", "^FVX"], "rate": [0.04, 0.05]}),
            )

    class TransformerStub:
        def transform_options_last(self, options, last_stock_price, stock_info, interest_rates):
            assert options.select("contractSymbol").item() == CONTRACT_SYMBOL
            assert last_stock_price.select("lastStockPrice").item() == 100.0
            assert stock_info.select("stockSymbol").item() == SYMBOL
            assert interest_rates.select("ticker").to_series().to_list() == ["^IRX", "^FVX"]
            return pl.DataFrame({"contractSymbol": [CONTRACT_SYMBOL], "relativeStrikePrice": [1.1]})

    class WriterStub:
        def __init__(self):
            self.calls = []

        def write_dataset(self, key, data):
            self.calls.append((key, data.height))

    repository = RepositoryStub()
    writer = WriterStub()

    DashboardPipeline(
        repository=repository,
        transformer=TransformerStub(),
        writer=writer,
    ).run()

    assert repository.calls == [
        "load_stocks",
        "load_stock_info",
        "load_stock_prices",
        "load_options_history",
        "latest_option_trade_date",
        ("load_latest_options", TRADE_DATE),
        ("load_latest_stock_prices", TRADE_DATE),
        "load_stock_info",
        "load_interest_rates",
    ]
    assert writer.calls == [
        ("stocks", 1),
        ("stock_info", 1),
        ("stock_prices", 1),
        ("options_hist", 1),
        ("options_last", 1),
    ]


def test_pipeline_reads_transforms_and_writes_parquet(tmp_path, dashboard_db):
    """Run repository, transformer, and writer against SQLite."""
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
            "contractSymbol": CONTRACT_SYMBOL,
            "relativeStrikePrice": 1.1,
            "riskFreeRate": 0.04,
            "dividendYield": 0.012,
            "timeToExpiryYears": round(14 / 365, 6),
        }
    ]


def test_app_creates_output_dir_and_writes_dashboard_parquet(tmp_path, dashboard_db):
    """Create the output directory and write dashboard parquet files."""
    db_path, db = dashboard_db
    output_dir = tmp_path / "dashboard"
    seed_dashboard_rows(db, strike=110.0)

    App(DashboardConfig(db_path=str(db_path), dashboard_data_dir=str(output_dir))).run()

    assert sorted(path.name for path in output_dir.iterdir()) == PARQUET_FILES
