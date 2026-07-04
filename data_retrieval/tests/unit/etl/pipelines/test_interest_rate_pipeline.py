"""Tests for :mod:`etl.pipelines.interest_rate_pipeline`."""

from etl.pipelines.interest_rate_pipeline import InterestRatePipeline


class ClientStub:
    """Interest-rate client stub."""

    def __init__(self):
        """Initialize the client stub."""
        self.calls = []
        self.payload = {"data": object()}

    def get_interest_rates(self):
        """Return provider payload."""
        self.calls.append("get_interest_rates")
        return self.payload


class DatabaseStub:
    """Database stub recording inserted rows."""

    def insert_many_ignore_duplicates(self, rows):
        """Record inserted rows."""
        self.inserted = rows
        return len(rows)


def test_run_fetches_transforms_and_inserts(monkeypatch):
    """Verify the pipeline fetches interest rates and persists transformed rows."""
    rows = [object()]
    transformed = []

    def fake_transform(payload):
        transformed.append(payload)
        return rows

    monkeypatch.setattr(
        "etl.pipelines.interest_rate_pipeline.InterestRateTransformer.transform",
        fake_transform,
    )
    client = ClientStub()
    db = DatabaseStub()

    InterestRatePipeline(client=client, database=db).run()

    assert client.calls == ["get_interest_rates"]
    assert transformed == [client.payload]
    assert db.inserted is rows
