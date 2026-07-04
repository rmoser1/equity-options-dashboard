"""Offline integration tests for the ETL package.

These tests keep external providers fake and deterministic while exercising the
real ETL pipelines, transformers, SQLModel schemas, and SQLite database writes.
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd
import pytest

from database import Database
from etl.etl_app import App
from etl.pipelines.historical_pipeline import HistoricalPipeline
from etl.pipelines.interest_rate_pipeline import InterestRatePipeline
from etl.pipelines.occ_pipeline import OCCPipeline
from etl.pipelines.options_pipeline import OptionsPipeline
from etl.pipelines.stock_info_pipeline import StockInfoPipeline
from schemas.historical_price import HistoricalPrice
from schemas.interest_rate import InterestRate
from schemas.option_contract import OptionContract
from schemas.option_volume import OptionVolume
from schemas.stock_info import StockInfoItem
from schemas.underlying import Underlying


@dataclass
class ETLConfig:
    """Configuration object for ETL app integration tests."""

    db_path: str
    volume_concurrency: int = 2
    volume_threshold: int = 1000
    historical_period: str = "1mo"


class DateProvider:
    """Deterministic OCC report date provider."""

    def get_date(self):
        """Return a fixed OCC report date."""
        return "20260102"


class OCCClientFake:
    """Fake OCC client returning a parseable underlyings file."""

    def __init__(self):
        """Initialize recorded calls."""
        self.underlying_fields = None

    def download_underlyings(self, fields):
        """Return tab-separated OCC rows matching the requested field order."""
        self.underlying_fields = fields
        return (
            "AAPL\tAAPL\tAPPLE INC\tNYSE\t250000\tEU\n"
            "MSFT\tMSFT\tMICROSOFT CORP\tNASDAQ\t250000\tEU\n"
            "SPX\tSPX\tS&P 500 INDEX\tCBOE\t250000\tIU\n"
        ).encode()


class VolumeServiceFake:
    """Fake aggregate option volume service."""

    def __init__(self, occ_client=None, concurrency=None):
        """Initialize recorded constructor arguments and calls."""
        self.occ_client = occ_client
        self.concurrency = concurrency
        self.calls = []

    async def get_volumes(self, symbols, report_date):
        """Return deterministic volumes for filtering."""
        self.calls.append((symbols, report_date))
        return {"AAPL": 1200, "MSFT": 50, "SPX": 5000}


class YFinanceClientFake:
    """Fake yfinance client returning transformer-compatible payloads."""

    def __init__(self):
        """Initialize recorded calls."""
        self.calls = []

    def get_options(self, symbol):
        """Return one option expiration for the symbol."""
        self.calls.append(("get_options", symbol))
        return {"symbol": symbol, "expirations": ("2026-01-16",)}

    def get_option_chain(self, symbol, expiration):
        """Return one call and one put option-chain row."""
        self.calls.append(("get_option_chain", symbol, expiration))
        return {
            "symbol": symbol,
            "expiration": expiration,
            "calls": option_chain_frame(f"{symbol}260116C00100000"),
            "puts": option_chain_frame(f"{symbol}260116P00095000", strike=95.0),
        }

    def get_info(self, symbol):
        """Return stock metadata for the symbol."""
        self.calls.append(("get_info", symbol))
        return {"symbol": symbol, "info": {"sector": "Technology", "beta": 1.2}}

    def get_history(self, symbol, period):
        """Return full-period historical data."""
        self.calls.append(("get_history", symbol, period))
        return {
            "symbol": symbol,
            "data": historical_frame("2026-01-02", open_price=100.0),
        }

    def get_history_since(self, symbol, start_date):
        """Return date-bounded historical data."""
        self.calls.append(("get_history_since", symbol, start_date))
        return {
            "symbol": symbol,
            "data": historical_frame(start_date, open_price=110.0),
        }

    def get_interest_rates(self):
        """Return recent Treasury yield data."""
        self.calls.append(("get_interest_rates",))
        columns = pd.MultiIndex.from_product(
            [["Close"], ["^IRX", "^FVX"]],
            names=["Price", "Ticker"],
        )
        return {
            "tickers": ("^IRX", "^FVX"),
            "data": pd.DataFrame(
                [[4.2, 4.7]],
                index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
                columns=columns,
            ),
        }


class DeterministicRandom:
    """Random-compatible object that makes batch pipelines immediate."""

    def randrange(self, start, stop):
        """Always process one symbol per batch."""
        return start

    def random(self):
        """Avoid randomized sleep delays."""
        return 0


@pytest.fixture
def etl_db(tmp_path):
    """Create an initialized temporary SQLite database for ETL tests."""
    db = Database(str(tmp_path / "etl.db"), model_package="schemas")
    db.create_all_tables()
    return db


def option_chain_frame(contract_symbol, strike=100.0):
    """Build a minimal yfinance-like option-chain DataFrame."""
    return pd.DataFrame(
        [
            {
                "contractSymbol": contract_symbol,
                "lastTradeDate": pd.Timestamp("2026-01-02"),
                "strike": strike,
                "lastPrice": 2.25,
                "bid": 2.0,
                "ask": 2.5,
                "change": 0.1,
                "percentChange": 4.6,
                "volume": 20,
                "openInterest": 200,
                "impliedVolatility": 0.25,
                "inTheMoney": False,
                "contractSize": "REGULAR",
                "currency": "USD",
            }
        ]
    )


def historical_frame(day, open_price):
    """Build a flat yfinance-like historical price DataFrame."""
    return pd.DataFrame(
        [{"Open": open_price, "High": open_price + 5, "Low": open_price - 5, "Close": open_price + 2, "Volume": 1000}],
        index=pd.DatetimeIndex([day], name="Date"),
    )


def run_symbol_pipeline(pipeline, symbols):
    """Run a symbol pipeline without randomized sleeps."""
    pipeline.random = DeterministicRandom()
    pipeline.sleep = lambda _: None
    pipeline.run(symbols)


def seed_underlying(db):
    """Insert the underlying required by foreign-keyed ETL tables."""
    db.insert_many([Underlying(symbol="AAPL", name="Apple Inc")])


def test_occ_pipeline_persists_filtered_underlyings_and_option_volumes(etl_db):
    """Run OCC download, transform, volume filtering, and database writes."""
    occ_client = OCCClientFake()
    volume_service = VolumeServiceFake()

    OCCPipeline(
        occ_client=occ_client,
        volume_service=volume_service,
        database=etl_db,
        date_provider=DateProvider(),
        volume_threshold=1000,
    ).run()

    stocks = etl_db.read_pandas(Underlying).sort_values("symbol").to_dict("records")
    volumes = etl_db.read_pandas(OptionVolume).sort_values("symbol").to_dict("records")

    assert stocks == [{"symbol": "AAPL", "name": "Apple Inc"}]
    assert volumes == [{"symbol": "AAPL", "date": date(2026, 1, 2), "volume": 1200}]
    assert volume_service.calls == [(["AAPL", "MSFT"], "20260102")]


def test_symbol_pipelines_transform_provider_payloads_and_persist_rows(etl_db):
    """Run option and stock-info pipelines through real transformers and SQLite."""
    seed_underlying(etl_db)
    client = YFinanceClientFake()

    run_symbol_pipeline(OptionsPipeline(client=client, database=etl_db), ["AAPL"])
    run_symbol_pipeline(StockInfoPipeline(client=client, database=etl_db), ["AAPL"])

    options = etl_db.read_pandas(OptionContract).to_dict("records")
    stock_info = etl_db.read_pandas(StockInfoItem).sort_values("itemName").to_dict("records")

    assert [
        {
            "contractSymbol": row["contractSymbol"],
            "stockSymbol": row["stockSymbol"],
            "strike": row["strike"],
            "direction": row["direction"],
        }
        for row in sorted(options, key=lambda item: item["contractSymbol"])
    ] == [
        {
            "contractSymbol": "AAPL260116C00100000",
            "stockSymbol": "AAPL",
            "strike": 100.0,
            "direction": "CALL",
        },
        {
            "contractSymbol": "AAPL260116P00095000",
            "stockSymbol": "AAPL",
            "strike": 95.0,
            "direction": "PUT",
        },
    ]
    assert stock_info == [
        {"stockSymbol": "AAPL", "itemName": "beta", "itemValue": "1.2"},
        {"stockSymbol": "AAPL", "itemName": "sector", "itemValue": '"Technology"'},
    ]


def test_interest_rate_pipeline_transforms_provider_payload_and_persists_rows(etl_db):
    """Run the interest-rate pipeline through transformer and SQLite."""
    client = YFinanceClientFake()

    InterestRatePipeline(client=client, database=etl_db).run()

    rows = etl_db.read_pandas(InterestRate).sort_values("ticker").to_dict("records")
    assert rows == [
        {
            "ticker": "^FVX",
            "date": date(2026, 1, 2),
            "name": "5 Year Treasury Note",
            "rate": 0.047,
        },
        {
            "ticker": "^IRX",
            "date": date(2026, 1, 2),
            "name": "13 Week Treasury Bill",
            "rate": 0.042,
        },
    ]


def test_historical_pipeline_uses_stored_max_date_and_persists_increment(etl_db):
    """Run incremental history loading against a real stored max date."""
    seed_underlying(etl_db)
    etl_db.insert_many(
        [
            HistoricalPrice(
                date=date(2026, 1, 2),
                symbol="AAPL",
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000,
            )
        ]
    )
    client = YFinanceClientFake()

    run_symbol_pipeline(HistoricalPipeline(client=client, database=etl_db), ["AAPL"])

    rows = etl_db.read_pandas(HistoricalPrice).sort_values("date").to_dict("records")
    assert client.calls == [("get_history_since", "AAPL", "2026-01-03")]
    assert [
        {"date": row["date"], "symbol": row["symbol"], "open": row["open"], "close": row["close"]}
        for row in rows
    ] == [
        {"date": date(2026, 1, 2), "symbol": "AAPL", "open": 100.0, "close": 102.0},
        {"date": date(2026, 1, 3), "symbol": "AAPL", "open": 110.0, "close": 112.0},
    ]


def test_app_runs_offline_etl_flow_into_sqlite(tmp_path, monkeypatch):
    """Run the app with fake providers and real pipelines/database."""
    monkeypatch.setattr("etl.etl_app.OCCClient", OCCClientFake)
    monkeypatch.setattr("etl.etl_app.YFinanceClient", YFinanceClientFake)
    monkeypatch.setattr("etl.etl_app.VolumeService", VolumeServiceFake)

    db_path = tmp_path / "app.db"
    app = App(ETLConfig(db_path=str(db_path)))
    app.occ_pipeline.date_provider = DateProvider()
    app.options_pipeline.random = DeterministicRandom()
    app.stock_info_pipeline.random = DeterministicRandom()
    app.historical_pipeline.random = DeterministicRandom()
    app.options_pipeline.sleep = lambda _: None
    app.stock_info_pipeline.sleep = lambda _: None
    app.historical_pipeline.sleep = lambda _: None

    app.initialize()
    app.run()

    db = Database(str(db_path), model_package="schemas")
    assert db.read_pandas(Underlying).to_dict("records") == [{"symbol": "AAPL", "name": "Apple Inc"}]
    assert len(db.read_pandas(StockInfoItem)) == 2
    assert len(db.read_pandas(HistoricalPrice)) == 1
    assert len(db.read_pandas(InterestRate)) == 2
