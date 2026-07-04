"""Service for fetching OCC option volumes.

This module provides :class:`VolumeService`, which fetches option-volume CSVs
for multiple underlyings and returns total volume by symbol.
"""

import asyncio
import logging

from etl.transformers.volume_transformer import VolumeTransformer


logger = logging.getLogger(__name__)


class VolumeService:
    """Fetch aggregate OCC option volume for symbols.

    :param occ_client: Client object that provides ``fetch_volume_csv(date, symbol)``.
    :param concurrency: Maximum number of concurrent volume requests.
    """

    def __init__(self, occ_client, concurrency: int = 5):
        """Initialize the service.

        :param occ_client: Client object that provides ``fetch_volume_csv(date, symbol)``.
        :param concurrency: Maximum number of concurrent volume requests.
        :default concurrency: ``5``
        """
        self.occ_client = occ_client
        self.concurrency = concurrency

    async def get_volumes(self, symbols: list[str], date: str) -> dict[str, int]:
        """Fetch total option volume by symbol.

        :param symbols: Underlying ticker symbols.
        :param date: OCC report date in ``YYYYMMDD`` format.
        :returns: Mapping from symbol to total option volume.
        """
        if not symbols:
            logger.info("No OCC volume requests to fetch")
            return {}

        logger.info(
            "Fetching OCC option volumes for %s symbols with concurrency %s",
            len(symbols),
            self.concurrency,
        )
        semaphore = asyncio.Semaphore(self.concurrency)
        tasks = [asyncio.create_task(self._get_volume(symbol, date, semaphore)) for symbol in symbols]
        volumes = {}

        for completed, task in enumerate(asyncio.as_completed(tasks), start=1):
            symbol, volume = await task
            volumes[symbol] = volume
            if completed % 100 == 0 or completed == len(symbols):
                logger.info("Fetched OCC volumes for %s/%s symbols", completed, len(symbols))

        return volumes

    async def _get_volume(self, symbol: str, date: str, semaphore: asyncio.Semaphore):
        """Fetch and aggregate volume for one symbol.

        :param symbol: Underlying ticker symbol.
        :param date: OCC report date in ``YYYYMMDD`` format.
        :param semaphore: Concurrency limiter for client calls.
        :returns: Tuple of symbol and aggregated option volume.
        """
        async with semaphore:
            csv_text = await asyncio.to_thread(self.occ_client.fetch_volume_csv, date, symbol)
            return symbol, VolumeTransformer.extract_volume(csv_text)
