"""Live contract tests for OCC market data endpoints.

These tests validate the external shape returned by :class:`etl.client.occ_client.OCCClient`.
They are marked as ``contract`` and ``network`` so normal test runs can skip
live provider calls.
"""

from io import StringIO

import pandas as pd
import pytest

from etl.client.occ_client import OCCClient
from etl.config.occ import download_field_codes, download_field_descriptions
from etl.transformers.underlying_transformer import UnderlyingTransformer
from etl.transformers.volume_transformer import VolumeTransformer
from schemas.option_volume import OptionVolume
from schemas.underlying import Underlying


pytestmark = [pytest.mark.contract, pytest.mark.network]

OCC_CONTRACT_REPORT_DATE = (
    pd.Timestamp.today() - pd.tseries.offsets.BDay(2)
).strftime("%Y%m%d")


def occ_contract_report_date():
    """Return the OCC report date used by live volume contract tests.

    The default is two business days before today, matching the ETL pipeline's
    OCC report-date convention.

    :returns: Report date formatted as ``YYYYMMDD``.
    :rtype: str
    """
    return OCC_CONTRACT_REPORT_DATE


def test_download_underlyings_returns_parseable_underlying_rows():
    """Verify the OCC underlyings endpoint returns schema-compatible data.

    The provider contract is that ``download_underlyings`` returns non-empty
    bytes that can be parsed by :class:`UnderlyingTransformer` into populated
    :class:`Underlying` schema objects.
    """
    content = OCCClient().download_underlyings(download_field_codes())
    underlyings = UnderlyingTransformer.transform(content, download_field_descriptions())

    assert isinstance(content, bytes)
    assert content
    assert underlyings
    assert all(isinstance(row, Underlying) for row in underlyings)
    assert all(row.symbol for row in underlyings)
    assert all(row.name for row in underlyings)


def test_fetch_volume_csv_returns_parseable_option_volume_shape():
    """Verify the OCC volume endpoint returns option-volume-shaped CSV data.

    The provider contract is that ``fetch_volume_csv`` returns non-empty CSV
    text containing a ``quantity`` column. The CSV must be compatible with
    :class:`VolumeTransformer` and produce a valid :class:`OptionVolume` row.
    """
    report_date = occ_contract_report_date()
    content = OCCClient().fetch_volume_csv(report_date, "AAPL")
    df = pd.read_csv(StringIO(content), index_col=False)
    volume = VolumeTransformer.extract_volume(content)
    row = OptionVolume(
        symbol="AAPL",
        date=pd.Timestamp(report_date).date(),
        volume=volume,
    )

    assert isinstance(content, str)
    assert content
    assert "quantity" in df.columns
    assert isinstance(volume, int)
    assert volume >= 0
    assert row.symbol == "AAPL"
    assert row.date == pd.Timestamp(report_date).date()
    assert row.volume == volume
