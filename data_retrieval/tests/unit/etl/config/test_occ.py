"""Tests for :mod:`etl.config.occ`.

The OCC download field order is part of the parsing contract with
:class:`etl.transformers.underlying_transformer.UnderlyingTransformer`.
"""

from etl.config.occ import download_field_codes, download_field_descriptions


def test_download_field_codes_preserve_request_order():
    """Verify OCC download field codes match the configured request order."""
    assert download_field_codes() == "OS;US;SN;EXCH;PL;ONN"


def test_download_field_descriptions_preserve_request_order():
    """Verify OCC field descriptions match downloaded column order."""
    assert download_field_descriptions() == [
        "Option Symbol",
        "Underlying Symbol",
        "Symbol Name",
        "Exchanges",
        "Position Limit",
        "Product Type",
    ]
