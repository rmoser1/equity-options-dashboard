"""Unit tests for the OCC HTTP client.

These tests keep client request construction deterministic and offline while
the live OCC provider shape is covered by contract tests.
"""

from urllib.parse import urlparse

from etl.client.occ_client import OCCClient


class StubResponse:
    """Minimal response object used by mocked ``requests.get`` calls."""

    def __init__(self, content=b"", text=""):
        """Create a response stub.

        :param content: Binary response body returned by download endpoints.
        :param text: Text response body returned by CSV endpoints.
        """
        self.content = content
        self.text = text
        self.raise_for_status_called = False

    def raise_for_status(self):
        """Record that HTTP status validation was requested."""
        self.raise_for_status_called = True


def parsed_request(call):
    """Return parsed request details from a single captured HTTP call.

    :param call: Captured ``requests.get`` call details.
    :returns: Parsed URL, parsed query parameters, and timeout.
    """

    url, params, timeout = call
    parsed_url = urlparse(url)

    return parsed_url, params, timeout


def test_download_underlyings_builds_request(monkeypatch):
    """Verify the underlyings download request and binary return value."""
    call = None
    response = StubResponse(content=b"raw")

    def fake_get(url, params, timeout):
        nonlocal call
        call = (url, params, timeout)
        return response

    monkeypatch.setattr("etl.client.occ_client.requests.get", fake_get)

    result = OCCClient(base_url="https://occ.test").download_underlyings("OS;US")

    assert result == b"raw"
    assert response.raise_for_status_called

    parsed_url, params, timeout = parsed_request(call)
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "occ.test"
    assert parsed_url.path == "/delo-download"
    assert params == {
        "prodType": "ALL",
        "downloadFields": "OS;US",
        "format": "txt",
    }
    assert timeout == (5, 30)


def test_fetch_volume_csv_builds_request(monkeypatch):
    """Verify the option-volume CSV request and text return value."""
    call = None
    response = StubResponse(text="quantity\n10\n")

    def fake_get(url, params, timeout):
        nonlocal call
        call = (url, params, timeout)
        return response

    monkeypatch.setattr("etl.client.occ_client.requests.get", fake_get)

    result = OCCClient(base_url="https://occ.test").fetch_volume_csv("20260102", "AAPL")

    assert result == "quantity\n10\n"
    assert response.raise_for_status_called

    parsed_url, params, timeout = parsed_request(call)
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "occ.test"
    assert parsed_url.path == "/volume-query"
    assert params == {
        "reportDate": "20260102",
        "format": "csv",
        "volumeQueryType": "O",
        "symbolType": "U",
        "symbol": "AAPL",
        "reportType": "D",
        "accountType": "ALL",
        "productKind": "OSTK",
        "porc": "BOTH",
    }
    assert timeout == (5, 30)
