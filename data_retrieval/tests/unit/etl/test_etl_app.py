"""Tests for :mod:`etl.etl_app`.

These tests verify that :class:`etl.etl_app.App` wires its dependencies,
initializes database tables, and runs ETL pipelines in the expected order.
"""

import logging

from etl.etl_app import App


class Config:
    """Configuration stub for :class:`etl.etl_app.App` tests."""

    db_path = "test.db"
    volume_concurrency = 3
    volume_threshold = 1000
    run_occ_pipeline = True
    historical_period = "1y"


class DatabaseStub:
    """Record database construction, initialization, and scalar queries."""

    def __init__(self, db_path, model_package):
        """Initialize the database stub.

        :param db_path: Database path supplied by the app.
        :param model_package: SQLModel package name supplied by the app.
        """
        self.db_path = db_path
        self.model_package = model_package
        self.created = False

    def create_all_tables(self):
        """Record that table creation was requested."""
        self.created = True

    def scalars(self, statement):
        """Return deterministic underlying symbols for pipeline tests.

        :param statement: SQL statement requested by the app.
        :returns: Static list of underlying symbols.
        """
        self.statement = statement
        return ["AAPL", "MSFT"]


class PipelineStub:
    """Record pipeline construction arguments and ``run`` calls."""

    def __init__(self, *args, **kwargs):
        """Initialize a pipeline stub.

        :param args: Positional arguments supplied by the app.
        :param kwargs: Keyword arguments supplied by the app.
        """
        self.args = args
        self.kwargs = kwargs
        self.run_calls = []

    def run(self, *args):
        """Record a pipeline run invocation.

        :param args: Arguments passed to ``run``.
        """
        self.run_calls.append(args)


class VolumeServiceStub:
    """Record volume-service construction arguments."""

    def __init__(self, occ_client, concurrency):
        """Initialize the volume service stub.

        :param occ_client: OCC client supplied by the app.
        :param concurrency: Configured volume-fetch concurrency.
        """
        self.occ_client = occ_client
        self.concurrency = concurrency


def patch_app_dependencies(monkeypatch):
    """Patch app dependencies with deterministic test doubles.

    :param monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr("etl.etl_app.Database", DatabaseStub)
    monkeypatch.setattr("etl.etl_app.OCCClient", lambda: "occ-client")
    monkeypatch.setattr("etl.etl_app.YFinanceClient", lambda: "yf-client")
    monkeypatch.setattr("etl.etl_app.VolumeService", VolumeServiceStub)
    monkeypatch.setattr("etl.etl_app.OCCPipeline", PipelineStub)
    monkeypatch.setattr("etl.etl_app.OptionsPipeline", PipelineStub)
    monkeypatch.setattr("etl.etl_app.StockInfoPipeline", PipelineStub)
    monkeypatch.setattr("etl.etl_app.HistoricalPipeline", PipelineStub)
    monkeypatch.setattr("etl.etl_app.InterestRatePipeline", PipelineStub)


def test_app_wires_dependencies(monkeypatch):
    """Verify app construction wires configured dependencies."""
    patch_app_dependencies(monkeypatch)

    app = App(Config())

    assert app.database.db_path == "test.db"
    assert app.database.model_package == "schemas"
    assert app.volume_service.occ_client == "occ-client"
    assert app.volume_service.concurrency == 3
    assert app.occ_pipeline.kwargs["volume_threshold"] == 1000
    assert app.historical_pipeline.kwargs["period"] == "1y"
    assert app.interest_rate_pipeline.kwargs["client"] == "yf-client"


def test_initialize_creates_tables(monkeypatch):
    """Verify app initialization creates database tables."""
    patch_app_dependencies(monkeypatch)

    app = App(Config())
    app.initialize()

    assert app.database.created


def test_run_executes_pipelines_in_order(monkeypatch, caplog):
    """Verify app run executes each pipeline with expected symbols."""
    patch_app_dependencies(monkeypatch)
    caplog.set_level(logging.INFO, logger="etl.etl_app")
    app = App(Config())

    app.run()

    assert app.occ_pipeline.run_calls == [()]
    assert app.options_pipeline.run_calls == [(["AAPL", "MSFT"],)]
    assert app.stock_info_pipeline.run_calls == [(["AAPL", "MSFT"],)]
    assert app.historical_pipeline.run_calls == [(["AAPL", "MSFT"],)]
    assert app.interest_rate_pipeline.run_calls == [()]
    assert [
        record.message
        for record in caplog.records
        if record.message.startswith("Running")
    ] == [
        "Running OCC pipeline",
        "Running options pipeline",
        "Running stock info pipeline",
        "Running historical pipeline",
        "Running interest rate pipeline",
    ]


def test_run_can_skip_occ_pipeline(monkeypatch, caplog):
    """Verify app can reuse existing underlyings without running OCC."""
    patch_app_dependencies(monkeypatch)
    caplog.set_level(logging.INFO, logger="etl.etl_app")

    class SkipOCCConfig(Config):
        """Configuration stub with OCC loading disabled."""

        run_occ_pipeline = False

    app = App(SkipOCCConfig())

    app.run()

    assert app.occ_pipeline.run_calls == []
    assert app.options_pipeline.run_calls == [(["AAPL", "MSFT"],)]
    assert "Skipping OCC pipeline" in [record.message for record in caplog.records]
