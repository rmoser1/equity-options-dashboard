"""Tests for :mod:`etl.pipelines.occ_pipeline`."""

from datetime import date

from etl.config.occ import download_field_descriptions
from etl.pipelines.occ_pipeline import OCCPipeline
from schemas.underlying import Underlying


class DateProvider:
    """Report-date provider stub."""

    def get_date(self):
        """Return a deterministic OCC report date."""
        return "20260102"


class VolumeServiceStub:
    """Volume-service stub recording volume requests."""

    def __init__(self, volumes=None):
        """Initialize the volume-service stub."""
        self.volumes = volumes or {}
        self.calls = []

    async def get_volumes(self, symbols, report_date):
        """Record and return configured aggregate volumes."""
        self.calls.append((symbols, report_date))
        return self.volumes


class OCCClientStub:
    """OCC client stub recording underlying-download requests."""

    def __init__(self):
        """Initialize the OCC client stub."""
        self.calls = []

    def download_underlyings(self, fields):
        """Record an underlying-download request."""
        self.calls.append(("download_underlyings", fields))
        return b"raw"


class DatabaseStub:
    """Database stub recording inserted batches."""

    def __init__(self):
        """Initialize the database stub."""
        self.inserted = []

    def insert_many(self, rows):
        """Record one inserted row batch."""
        self.inserted.append(rows)


def test_filter_by_volume_keeps_underlyings_at_or_above_threshold():
    """Verify underlyings are filtered by inclusive volume threshold."""
    underlyings = [Underlying(symbol="AAPL", name="Apple"), Underlying(symbol="MSFT", name="Microsoft")]
    pipeline = OCCPipeline(None, None, None, volume_threshold=1000)

    result = pipeline._filter_by_volume(underlyings, {"AAPL": 1000, "MSFT": 999})

    assert [row.symbol for row in result] == ["AAPL"]


def test_option_volumes_builds_rows_for_filtered_underlyings():
    """Verify aggregate option-volume rows use the report date and volumes."""
    rows = OCCPipeline._option_volumes(
        [Underlying(symbol="AAPL", name="Apple")],
        {"AAPL": 1200},
        "20260102",
    )

    assert rows[0].symbol == "AAPL"
    assert rows[0].date == date(2026, 1, 2)
    assert rows[0].volume == 1200


def test_run_downloads_filters_and_inserts(monkeypatch):
    """Verify OCC underlyings and volumes are fetched, filtered, and inserted."""
    db = DatabaseStub()
    volume_service = VolumeServiceStub({"AAPL": 1200, "MSFT": 50})
    underlyings = [Underlying(symbol="AAPL", name="Apple"), Underlying(symbol="MSFT", name="Microsoft")]
    occ_client = OCCClientStub()
    transformed = []

    def fake_transform(raw, descriptions):
        transformed.append((raw, descriptions))
        return underlyings

    monkeypatch.setattr(
        "etl.pipelines.occ_pipeline.UnderlyingTransformer.transform",
        fake_transform,
    )

    OCCPipeline(
        occ_client=occ_client,
        volume_service=volume_service,
        database=db,
        date_provider=DateProvider(),
        volume_threshold=1000,
    ).run()

    assert [[row.symbol for row in batch] for batch in db.inserted] == [["AAPL"], ["AAPL"]]
    assert db.inserted[1][0].volume == 1200
    assert occ_client.calls == [("download_underlyings", "OS;US;SN;EXCH;PL;ONN")]
    assert transformed == [(b"raw", download_field_descriptions())]
    assert volume_service.calls == [(["AAPL", "MSFT"], "20260102")]


def test_run_inserts_empty_batches_when_no_underlyings(monkeypatch):
    """Verify empty OCC underlyings still produce empty insert batches."""
    db = DatabaseStub()
    volume_service = VolumeServiceStub()
    monkeypatch.setattr(
        "etl.pipelines.occ_pipeline.UnderlyingTransformer.transform",
        lambda raw, descriptions: [],
    )

    OCCPipeline(
        occ_client=OCCClientStub(),
        volume_service=volume_service,
        database=db,
        date_provider=DateProvider(),
        volume_threshold=1000,
    ).run()

    assert db.inserted == [[], []]
    assert volume_service.calls == [([], "20260102")]


def test_report_date_uses_date_provider_when_present():
    """Verify an injected date provider controls the OCC report date."""
    pipeline = OCCPipeline(None, None, None, date_provider=DateProvider())

    assert pipeline._report_date() == "20260102"
