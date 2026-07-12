"""Unit tests for the SQLModel-backed database helper.

These tests cover model discovery, schema creation, inserts, DataFrame reads,
custom queries, and scalar helpers exposed by :class:`database.Database`.
"""

import logging
import sys

import pytest
from sqlalchemy import inspect
from sqlmodel import select

from database import Database
from schemas.underlying import Underlying


@pytest.fixture
def empty_db(tmp_path):
    """Create a database helper without creating schema tables.

    :param tmp_path: Pytest temporary directory fixture.
    :returns: Database helper bound to an isolated SQLite file.
    """
    return Database(str(tmp_path / "test.db"), model_package="schemas")


@pytest.fixture
def db(empty_db):
    """Create an empty test database with application schemas loaded.

    :param empty_db: Database fixture without created schema tables.
    :returns: Database helper with application schema tables created.
    """
    empty_db.create_all_tables()
    return empty_db


@pytest.fixture
def seeded_db(db):
    """Create a database seeded with two underlying rows.

    :param db: Empty database fixture.
    :returns: Database helper containing deterministic stock rows.
    """
    db.insert_many(
        [
            Underlying(symbol="AAPL", name="Apple"),
            Underlying(symbol="MSFT", name="Microsoft"),
        ]
    )
    return db


def test_import_all_models_imports_schema_modules(empty_db):
    """Import every module in the configured application schema package.

    :param empty_db: Database fixture without created schema tables.
    """
    empty_db.import_all_models()

    assert {
        "schemas.historical_price",
        "schemas.option_contract",
        "schemas.option_volume",
        "schemas.stock_info",
        "schemas.underlying",
    }.issubset(sys.modules)


def test_create_all_tables_creates_schema_tables(empty_db):
    """Create all registered application schema tables.

    :param empty_db: Database fixture without created schema tables.
    """
    empty_db.create_all_tables()

    assert {
        "aggOptionVolume",
        "options",
        "stockInfo",
        "stockPrices",
        "stocks",
    }.issubset(inspect(empty_db.engine).get_table_names())


def test_insert_many_commits_rows(db):
    """Commit inserted rows.

    :param db: Empty database fixture.
    """
    db.insert_many([Underlying(symbol="AAPL", name="Apple")])

    assert db.scalars(select(Underlying.symbol)) == ["AAPL"]


def test_insert_many_returns_none_for_empty_list(db):
    """Return ``None`` when there are no objects to insert.

    :param db: Empty database fixture.
    """
    assert db.insert_many([]) is None


def test_insert_many_ignore_duplicates_skips_existing_primary_keys(db):
    """Skip duplicate primary keys while inserting new rows.

    :param db: Empty database fixture.
    """
    db.insert_many([Underlying(symbol="AAPL", name="Apple")])

    inserted = db.insert_many_ignore_duplicates(
        [
            Underlying(symbol="AAPL", name="Apple Duplicate"),
            Underlying(symbol="MSFT", name="Microsoft"),
        ]
    )

    df = db.read_pandas(Underlying).sort_values("symbol").to_dict("records")
    assert df == [
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
    ]
    assert inserted == 1


def test_insert_many_ignore_duplicates_batches_large_inserts(db, monkeypatch):
    """Split duplicate-tolerant inserts across SQLite variable limits.

    :param db: Empty database fixture.
    :param monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr("database.SQLITE_MAX_VARIABLES", 4)

    inserted = db.insert_many_ignore_duplicates(
        [
            Underlying(symbol="AAPL", name="Apple"),
            Underlying(symbol="MSFT", name="Microsoft"),
            Underlying(symbol="NVDA", name="Nvidia"),
        ]
    )

    assert inserted == 3
    assert db.scalars(select(Underlying.symbol).order_by(Underlying.symbol)) == [
        "AAPL",
        "MSFT",
        "NVDA",
    ]


def test_insert_many_ignore_duplicates_logs_insert_count(db, caplog):
    """Log inserted and skipped row counts for duplicate-tolerant inserts.

    :param db: Empty database fixture.
    :param caplog: Pytest log capture fixture.
    """
    db.insert_many([Underlying(symbol="AAPL", name="Apple")])
    caplog.set_level(logging.INFO, logger="database")

    db.insert_many_ignore_duplicates(
        [
            Underlying(symbol="AAPL", name="Apple Duplicate"),
            Underlying(symbol="MSFT", name="Microsoft"),
        ]
    )

    assert (
        "Inserted 1/2 Underlying rows after skipping duplicates"
        in caplog.messages
    )


def test_insert_many_overwrite_duplicates_updates_existing_primary_keys(db):
    """Update duplicate primary keys while inserting new rows.

    :param db: Empty database fixture.
    """
    db.insert_many([Underlying(symbol="AAPL", name="Apple")])

    affected = db.insert_many_overwrite_duplicates(
        [
            Underlying(symbol="AAPL", name="Apple Inc."),
            Underlying(symbol="MSFT", name="Microsoft"),
        ]
    )

    df = db.read_pandas(Underlying).sort_values("symbol").to_dict("records")
    assert df == [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft"},
    ]
    assert affected == 2


def test_insert_many_overwrite_duplicates_returns_zero_for_empty_list(db):
    """Return zero when there are no objects to upsert.

    :param db: Empty database fixture.
    """
    assert db.insert_many_overwrite_duplicates([]) == 0


def test_insert_many_overwrite_duplicates_batches_large_upserts(db, monkeypatch):
    """Split overwrite-tolerant inserts across SQLite variable limits.

    :param db: Empty database fixture.
    :param monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr("database.SQLITE_MAX_VARIABLES", 4)
    db.insert_many([Underlying(symbol="AAPL", name="Apple")])

    affected = db.insert_many_overwrite_duplicates(
        [
            Underlying(symbol="AAPL", name="Apple Inc."),
            Underlying(symbol="MSFT", name="Microsoft"),
            Underlying(symbol="NVDA", name="Nvidia"),
        ]
    )

    assert affected == 3
    assert db.read_pandas(Underlying).sort_values("symbol").to_dict("records") == [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft"},
        {"symbol": "NVDA", "name": "Nvidia"},
    ]


def test_insert_many_overwrite_duplicates_logs_affected_count(db, caplog):
    """Log inserted and updated row counts for overwrite-tolerant inserts.

    :param db: Empty database fixture.
    :param caplog: Pytest log capture fixture.
    """
    db.insert_many([Underlying(symbol="AAPL", name="Apple")])
    caplog.set_level(logging.INFO, logger="database")

    db.insert_many_overwrite_duplicates(
        [
            Underlying(symbol="AAPL", name="Apple Inc."),
            Underlying(symbol="MSFT", name="Microsoft"),
        ]
    )

    assert (
        "Inserted or updated 2/2 Underlying rows after overwriting duplicates"
        in caplog.messages
    )


def test_read_pandas_selects_all_model_columns_by_default(seeded_db):
    """Read all model columns into a pandas DataFrame by default.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    df = seeded_db.read_pandas(Underlying)

    assert df.to_dict("records") == [
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
    ]


def test_read_pandas_can_select_specific_columns(seeded_db):
    """Read selected model columns into a pandas DataFrame.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    df = seeded_db.read_pandas(Underlying, columns=["symbol"])

    assert df.to_dict("records") == [{"symbol": "AAPL"}, {"symbol": "MSFT"}]


def test_read_polars_selects_all_model_columns_by_default(seeded_db):
    """Read all model columns into a Polars DataFrame by default.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    df = seeded_db.read_polars(Underlying)

    assert df.to_dicts() == [
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
    ]


def test_read_polars_can_select_specific_columns(seeded_db):
    """Read selected model columns into a Polars DataFrame.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    df = seeded_db.read_polars(Underlying, columns=["symbol"])

    assert df.to_dicts() == [{"symbol": "AAPL"}, {"symbol": "MSFT"}]


def test_query_pandas_accepts_sql_string(seeded_db):
    """Run a SQL string and return pandas results.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    df = seeded_db.query_pandas("SELECT symbol FROM stocks ORDER BY symbol")

    assert df.to_dict("records") == [{"symbol": "AAPL"}, {"symbol": "MSFT"}]


def test_query_pandas_accepts_select_statement(seeded_db):
    """Run a SQLAlchemy select statement and return pandas results.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    df = seeded_db.query_pandas(select(Underlying.symbol).order_by(Underlying.symbol))

    assert df.to_dict("records") == [{"symbol": "AAPL"}, {"symbol": "MSFT"}]


def test_query_polars_accepts_sql_string(seeded_db):
    """Run a SQL string and return Polars results.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    df = seeded_db.query_polars("SELECT symbol FROM stocks ORDER BY symbol")

    assert df.to_dicts() == [{"symbol": "AAPL"}, {"symbol": "MSFT"}]


def test_query_polars_accepts_select_statement(seeded_db):
    """Run a SQLAlchemy select statement and return Polars results.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    df = seeded_db.query_polars(select(Underlying.symbol).order_by(Underlying.symbol))

    assert df.to_dicts() == [{"symbol": "AAPL"}, {"symbol": "MSFT"}]


def test_query_polars_batches_yields_batched_results(seeded_db):
    """Run a SQLAlchemy select statement and yield Polars batches."""
    batches = list(
        seeded_db.query_polars_batches(
            select(Underlying.symbol).order_by(Underlying.symbol),
            batch_size=1,
        )
    )

    assert [batch.to_dicts() for batch in batches] == [
        [{"symbol": "AAPL"}],
        [{"symbol": "MSFT"}],
    ]


def test_scalar_returns_first_result(seeded_db):
    """Return the first scalar value from a query result.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    assert seeded_db.scalar(select(Underlying.symbol).order_by(Underlying.symbol)) == "AAPL"


def test_scalar_returns_none_when_query_has_no_results(db):
    """Return ``None`` when a scalar query produces no rows.

    :param db: Empty database fixture.
    """
    assert db.scalar(select(Underlying.symbol)) is None


def test_scalars_returns_all_results(seeded_db):
    """Return every scalar value from a query result.

    :param seeded_db: Database fixture containing deterministic stock rows.
    """
    assert seeded_db.scalars(select(Underlying.symbol).order_by(Underlying.symbol)) == [
        "AAPL",
        "MSFT",
    ]
