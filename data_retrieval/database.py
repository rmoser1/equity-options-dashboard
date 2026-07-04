"""Database access helpers for SQLModel-backed SQLite storage.

This module provides the :class:`Database` helper, which can create tables,
insert SQLModel objects, and read query results into pandas or Polars
DataFrames.
"""

import importlib
import logging
import pkgutil

import pandas as pd
import polars as pl
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import SQLModel, Session, create_engine, select


SQLITE_MAX_VARIABLES = 30_000
logger = logging.getLogger(__name__)


class Database:
    """Small SQLModel-backed SQLite database helper.

    :param sqlite_path: Path to the SQLite database file.
    :param model_package: Import path for the package containing SQLModel models.
    """

    def __init__(self, sqlite_path: str, model_package: str = "models"):
        logger.info("Opening SQLite database at %s", sqlite_path)
        self.engine = create_engine(f"sqlite:///{sqlite_path}", echo=False)
        self.model_package = model_package

    # --------------------------------------------------
    # model discovery
    # --------------------------------------------------

    def import_all_models(self):
        """Import every module in the configured model package."""
        logger.debug("Importing SQLModel modules from %s", self.model_package)
        package = importlib.import_module(self.model_package)
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            module_path = f"{self.model_package}.{module_name}"
            logger.debug("Importing SQLModel module %s", module_path)
            importlib.import_module(module_path)

    # --------------------------------------------------
    # schema
    # --------------------------------------------------

    def create_all_tables(self):
        """Create all SQLModel tables registered by the configured models.

        Existing tables are left unchanged: this creates missing tables only,
        does not drop or overwrite data, and does not apply schema migrations.
        """
        logger.info("Creating missing database tables")
        self.import_all_models()
        SQLModel.metadata.create_all(self.engine)
        logger.info("Database table creation complete")

    # --------------------------------------------------
    # inserts
    # --------------------------------------------------

    def insert_many(self, objects: list[SQLModel]):
        """Insert multiple SQLModel objects.

        :param objects: Objects to add to the current session.
        """
        if not objects:
            logger.debug("No objects supplied for insert_many")
            return

        model = type(objects[0])
        logger.info("Inserting %s %s rows", len(objects), model.__name__)
        with Session(self.engine) as session:
            session.add_all(objects)
            session.commit()
        logger.info("Inserted %s %s rows", len(objects), model.__name__)

    def insert_many_ignore_duplicates(self, objects: list[SQLModel]) -> int:
        """Insert SQLModel objects, skipping rows with existing primary keys.

        :param objects: Objects to add when they do not already exist.
        :returns: Number of rows inserted.
        """
        if not objects:
            logger.debug("No objects supplied for insert_many_ignore_duplicates")
            return 0

        model = type(objects[0])
        columns = model.__table__.columns
        rows_per_statement = max(1, SQLITE_MAX_VARIABLES // len(columns))
        total = len(objects)
        logger.info(
            "Inserting %s %s rows with duplicate skipping in batches of %s",
            total,
            model.__name__,
            rows_per_statement,
        )

        with Session(self.engine) as session:
            inserted = 0
            for start in range(0, len(objects), rows_per_statement):
                batch = objects[start : start + rows_per_statement]
                values = [
                    {column.name: getattr(obj, column.name) for column in columns}
                    for obj in batch
                ]
                statement = sqlite_insert(model).values(values).prefix_with("OR IGNORE")
                result = session.exec(statement)
                inserted += result.rowcount
                logger.debug(
                    "Inserted %s/%s %s rows after batch %s-%s",
                    inserted,
                    total,
                    model.__name__,
                    start + 1,
                    start + len(batch),
                )
            session.commit()
            logger.info(
                "Inserted %s/%s %s rows after skipping duplicates",
                inserted,
                total,
                model.__name__,
            )
            return inserted

    def insert_many_overwrite_duplicates(self, objects: list[SQLModel]) -> int:
        """Insert SQLModel objects, updating rows with existing primary keys.

        :param objects: Objects to insert or use to overwrite existing rows.
        :returns: Number of rows inserted or updated.
        """
        if not objects:
            logger.debug("No objects supplied for insert_many_overwrite_duplicates")
            return 0

        model = type(objects[0])
        columns = model.__table__.columns
        primary_key_columns = [column.name for column in columns if column.primary_key]
        update_columns = [column for column in columns if not column.primary_key]
        if not primary_key_columns:
            raise ValueError(f"{model.__name__} has no primary key columns")
        if not update_columns:
            raise ValueError(f"{model.__name__} has no non-primary-key columns to update")

        rows_per_statement = max(1, SQLITE_MAX_VARIABLES // len(columns))
        total = len(objects)
        logger.info(
            "Inserting %s %s rows with duplicate overwriting in batches of %s",
            total,
            model.__name__,
            rows_per_statement,
        )

        with Session(self.engine) as session:
            affected = 0
            for start in range(0, len(objects), rows_per_statement):
                batch = objects[start : start + rows_per_statement]
                values = [
                    {column.name: getattr(obj, column.name) for column in columns}
                    for obj in batch
                ]
                statement = sqlite_insert(model).values(values)
                statement = statement.on_conflict_do_update(
                    index_elements=primary_key_columns,
                    set_={
                        column.name: getattr(statement.excluded, column.name)
                        for column in update_columns
                    },
                )
                result = session.exec(statement)
                affected += result.rowcount
                logger.debug(
                    "Inserted or updated %s/%s %s rows after batch %s-%s",
                    affected,
                    total,
                    model.__name__,
                    start + 1,
                    start + len(batch),
                )
            session.commit()
            logger.info(
                "Inserted or updated %s/%s %s rows after overwriting duplicates",
                affected,
                total,
                model.__name__,
            )
            return affected

    # --------------------------------------------------
    # reads
    # --------------------------------------------------

    def read_pandas(self, model, columns: list[str] | None = None) -> pd.DataFrame:
        """Read rows from a model into a pandas DataFrame.

        :param model: SQLModel table model to query.
        :param columns: Optional list of column names to select.
        :returns: Query results as a pandas DataFrame.
        """
        if columns:
            selected = [getattr(model, c) for c in columns]
            stmt = select(*selected)
        else:
            stmt = select(model)

        logger.debug("Reading %s rows into pandas", model.__name__)
        return pd.read_sql(stmt, self.engine)

    def read_polars(self, model, columns: list[str] | None = None) -> pl.DataFrame:
        """Read rows from a model directly into a Polars DataFrame.

        :param model: SQLModel table model to query.
        :param columns: Optional list of column names to select.
        :returns: Query results as a Polars DataFrame.
        """
        if columns:
            selected = [getattr(model, c) for c in columns]
            stmt = select(*selected)
        else:
            stmt = select(model)

        logger.debug("Reading %s rows into Polars", model.__name__)
        return pl.read_database(stmt, self.engine)

    # --------------------------------------------------
    # custom query
    # --------------------------------------------------

    def query_pandas(self, statement) -> pd.DataFrame:
        """Run a custom database query and return pandas results.

        ``statement`` can be a plain SQL string, such as
        ``"SELECT * FROM historical_price"``, or a SQLAlchemy query object,
        such as one created with ``select(...)`` or ``text(...)``.

        :param statement: Query to run against the database.
        :returns: Query results as a pandas DataFrame.
        """
        logger.debug("Running pandas database query")
        return pd.read_sql(statement, self.engine)

    def query_polars(self, statement) -> pl.DataFrame:
        """Run a custom database query and return Polars results.

        ``statement`` can be a plain SQL string, such as
        ``"SELECT * FROM historical_price"``, or a SQLAlchemy query object,
        such as one created with ``select(...)`` or ``text(...)``.

        :param statement: Query to run against the database.
        :returns: Query results as a Polars DataFrame.
        """
        logger.debug("Running Polars database query")
        return pl.read_database(statement, self.engine)

    def scalar(self, statement):
        """Run a query and return the first column of the first row.

        :param statement: Query to run against the database.
        :returns: Scalar result value, or ``None`` when no rows exist.
        """
        logger.debug("Running scalar database query")
        with Session(self.engine) as session:
            return session.exec(statement).first()

    def scalars(self, statement) -> list:
        """Run a query and return the first column from every row.

        :param statement: Query to run against the database.
        :returns: List of scalar result values.
        """
        logger.debug("Running scalars database query")
        with Session(self.engine) as session:
            return list(session.exec(statement).all())
