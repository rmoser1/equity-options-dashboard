"""Tests for :mod:`etl.services.volume_service`.

These tests keep OCC volume fetching offline while exercising the service's
request mapping, transformer delegation, error propagation, and concurrency
limit.
"""

import asyncio
import threading
import time

import pytest

from etl.services.volume_service import VolumeService


class OCCClientStub:
    """Return deterministic CSV responses for known OCC symbols."""

    def fetch_volume_csv(self, date, symbol):
        """Return CSV text for ``symbol``.

        :param date: OCC report date supplied by the service.
        :param symbol: Underlying symbol being fetched.
        :returns: CSV text shaped like an OCC volume response.
        """
        return {
            "AAPL": "quantity\n10\n20\n",
            "MSFT": "not_quantity\n1\n",
        }[symbol]


class RecordingOCCClientStub:
    """Record OCC volume requests made by :class:`VolumeService`."""

    def __init__(self):
        """Initialize an empty request log."""
        self.calls = []

    def fetch_volume_csv(self, date, symbol):
        """Record the request and return a minimal valid CSV.

        :param date: OCC report date supplied by the service.
        :param symbol: Underlying symbol being fetched.
        :returns: CSV text with a single quantity value.
        """
        self.calls.append((date, symbol))
        return "quantity\n1\n"


class ConcurrentOCCClientStub:
    """Track in-flight OCC requests for concurrency-limit assertions."""

    def __init__(self):
        """Initialize concurrency counters protected by a thread lock."""
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def fetch_volume_csv(self, date, symbol):
        """Simulate a slow OCC request while counting active calls.

        :param date: OCC report date supplied by the service.
        :param symbol: Underlying symbol being fetched.
        :returns: CSV text with a single quantity value.
        """
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)

        time.sleep(0.02)

        with self.lock:
            self.active -= 1

        return "quantity\n1\n"


class FailingOCCClientStub:
    """Raise fetch errors to verify service error propagation."""

    def fetch_volume_csv(self, date, symbol):
        """Raise a deterministic fetch failure.

        :param date: OCC report date supplied by the service.
        :param symbol: Underlying symbol being fetched.
        :raises RuntimeError: Always raised for the requested symbol.
        """
        raise RuntimeError(f"failed to fetch {symbol}")


def test_get_volumes_delegates_csv_parsing_to_volume_transformer(monkeypatch):
    """Verify volume service uses the shared volume transformer."""
    calls = []

    def fake_extract_volume(csv_text):
        """Return a distinct value for each transformer invocation.

        :param csv_text: CSV text passed from the volume service.
        :returns: The 1-based call count.
        """
        calls.append(csv_text)
        return len(calls)

    monkeypatch.setattr(
        "etl.services.volume_service.VolumeTransformer.extract_volume",
        fake_extract_volume,
    )

    result = asyncio.run(
        VolumeService(OCCClientStub(), concurrency=2).get_volumes(
            ["AAPL", "MSFT"],
            "20260102",
        )
    )

    assert calls == ["quantity\n10\n20\n", "not_quantity\n1\n"]
    assert result == {"AAPL": 1, "MSFT": 2}


def test_get_volumes_passes_date_and_symbol_to_occ_client():
    """Verify OCC requests are made for each requested symbol and report date."""
    client = RecordingOCCClientStub()

    result = asyncio.run(
        VolumeService(client, concurrency=2).get_volumes(
            ["AAPL", "MSFT"],
            "20260102",
        )
    )

    assert client.calls == [("20260102", "AAPL"), ("20260102", "MSFT")]
    assert result == {"AAPL": 1, "MSFT": 1}


def test_get_volumes_returns_empty_mapping_for_empty_symbols():
    """Verify no OCC requests are made when no symbols are requested."""
    client = RecordingOCCClientStub()

    result = asyncio.run(VolumeService(client).get_volumes([], "20260102"))

    assert result == {}
    assert client.calls == []


def test_get_volumes_propagates_occ_client_errors():
    """Verify fetch failures are surfaced to the caller."""
    with pytest.raises(RuntimeError, match="failed to fetch AAPL"):
        asyncio.run(
            VolumeService(FailingOCCClientStub()).get_volumes(
                ["AAPL"],
                "20260102",
            )
        )


def test_get_volumes_limits_concurrent_occ_requests():
    """Verify the configured concurrency limits in-flight OCC requests."""
    client = ConcurrentOCCClientStub()

    result = asyncio.run(
        VolumeService(client, concurrency=2).get_volumes(
            ["AAPL", "MSFT", "NVDA", "TSLA"],
            "20260102",
        )
    )

    assert result == {"AAPL": 1, "MSFT": 1, "NVDA": 1, "TSLA": 1}
    assert client.max_active <= 2
