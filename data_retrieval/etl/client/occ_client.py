"""HTTP client for OCC market data endpoints.

This module provides :class:`OCCClient`, a small wrapper around the OCC
underlying-download and option-volume endpoints.
"""

import logging

import requests


logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = (5, 30)


class OCCClient:
    """Fetch OCC underlying and option-volume data.

    :param base_url: Base URL for OCC market data endpoints.
    :param timeout: ``requests`` timeout as ``(connect, read)`` seconds.
    :default base_url: ``"https://marketdata.theocc.com"``
    :default timeout: ``(5, 30)``
    """

    def __init__(self, base_url: str = "https://marketdata.theocc.com", timeout=DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout

    def download_underlyings(self, download_fields: str) -> bytes:
        """Download the OCC underlyings file.

        :param download_fields: Semicolon-delimited OCC field codes.
        :returns: Raw response content.
        """
        url = f"{self.base_url}/delo-download"
        params = {
            "prodType": "ALL",
            "downloadFields": download_fields,
            "format": "txt",
        }

        logger.info("Downloading OCC underlyings")

        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        logger.info("Downloaded OCC underlyings (%s bytes)", len(resp.content))

        return resp.content

    def fetch_volume_csv(self, date: str, symbol: str) -> str:
        """Fetch OCC option-volume CSV text for one underlying.

        :param date: OCC report date in ``YYYYMMDD`` format.
        :param symbol: Underlying ticker symbol.
        :returns: CSV response text.
        """
        url = f"{self.base_url}/volume-query"
        params = {
            "reportDate": date,
            "format": "csv",
            "volumeQueryType": "O",
            "symbolType": "U",
            "symbol": symbol,
            "reportType": "D",
            "accountType": "ALL",
            "productKind": "OSTK",
            "porc": "BOTH",
        }

        logger.debug("Fetching volume for %s", symbol)
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text
