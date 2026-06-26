"""Pipeline for loading OCC underlyings and aggregate option volume."""

import asyncio
from datetime import datetime
import logging

import pandas as pd

from etl.config.occ import download_field_codes, download_field_descriptions
from etl.transformers.underlying_transformer import UnderlyingTransformer
from schemas.option_volume import OptionVolume


logger = logging.getLogger(__name__)


class OCCPipeline:
    """Load OCC underlyings and filtered aggregate option volumes.

    :param occ_client: OCC client used to download underlyings.
    :param volume_service: Service used to fetch option volume by symbol.
    :param database: Shared database helper.
    :param date_provider: Optional report date provider.
    :param volume_threshold: Minimum option volume required for insertion.
    :default date_provider: ``None``
    :default volume_threshold: ``1000``
    """

    def __init__(self, occ_client, volume_service, database, date_provider=None, volume_threshold=1000):
        """Initialize the pipeline."""
        self.occ_client = occ_client
        self.volume_service = volume_service
        self.database = database
        self.date_provider = date_provider
        self.volume_threshold = volume_threshold

    def run(self):
        """Run the OCC pipeline."""
        underlyings = self._download_underlyings()
        symbols = [u.symbol for u in underlyings]
        report_date = self._report_date()
        logger.info("Fetching OCC volumes for %s underlyings on %s", len(symbols), report_date)
        volumes = asyncio.run(self.volume_service.get_volumes(symbols, report_date))
        filtered = self._filter_by_volume(underlyings, volumes)
        logger.info("Filtered OCC underlyings from %s to %s", len(underlyings), len(filtered))
        option_volumes = self._option_volumes(filtered, volumes, report_date)

        self.database.insert_many_ignore_duplicates(filtered)
        self.database.insert_many_ignore_duplicates(option_volumes)

    def _download_underlyings(self):
        """Download and transform OCC underlyings."""
        raw_file = self.occ_client.download_underlyings(download_field_codes())
        underlyings = UnderlyingTransformer.transform(raw_file, download_field_descriptions())
        logger.info("Parsed %s OCC underlyings", len(underlyings))
        return underlyings

    def _report_date(self) -> str:
        """Return the OCC report date in ``YYYYMMDD`` format."""
        if self.date_provider:
            return self.date_provider.get_date()

        return (pd.Timestamp.today() - pd.tseries.offsets.BDay(2)).strftime("%Y%m%d")

    def _filter_by_volume(self, underlyings, volumes: dict[str, int]):
        """Return underlyings meeting the configured volume threshold."""
        return [u for u in underlyings if volumes.get(u.symbol, 0) >= self.volume_threshold]

    @staticmethod
    def _option_volumes(underlyings, volumes: dict[str, int], report_date: str) -> list[OptionVolume]:
        """Build aggregate option-volume rows."""
        date_value = datetime.strptime(report_date, "%Y%m%d").date()
        return [
            OptionVolume(
                symbol=u.symbol,
                date=date_value,
                volume=volumes[u.symbol],
            )
            for u in underlyings
        ]
