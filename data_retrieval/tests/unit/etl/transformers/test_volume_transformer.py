"""Tests for :mod:`etl.transformers.volume_transformer`.

The transformer accepts raw OCC CSV response text and returns one aggregate
integer volume. Bad or unsupported CSV shapes are expected to default to
``0``.
"""

from etl.transformers.volume_transformer import VolumeTransformer


def test_extract_volume_sums_quantity_column():
    """Verify quantity values are summed into one aggregate volume."""
    assert VolumeTransformer.extract_volume("quantity\n10\n20\n") == 30


def test_extract_volume_returns_zero_when_csv_is_invalid():
    """Verify malformed CSV shapes default to zero volume."""
    assert VolumeTransformer.extract_volume("not_quantity\n10\n") == 0


def test_extract_volume_returns_zero_for_empty_csv():
    """Verify empty CSV text defaults to zero volume."""
    assert VolumeTransformer.extract_volume("") == 0


def test_extract_volume_returns_zero_for_empty_quantity_column():
    """Verify a CSV with no quantity rows has zero volume."""
    assert VolumeTransformer.extract_volume("quantity\n") == 0


def test_extract_volume_skips_missing_quantity_values():
    """Verify missing quantity values are ignored by the aggregate sum."""
    assert VolumeTransformer.extract_volume("quantity\n10\n\n20\n") == 30


def test_extract_volume_truncates_decimal_quantity_sum():
    """Verify decimal quantity sums are coerced to integer volume."""
    assert VolumeTransformer.extract_volume("quantity\n10.9\n20.2\n") == 31


def test_extract_volume_returns_zero_for_non_numeric_quantity_values():
    """Verify unparsable quantity values default to zero volume."""
    assert VolumeTransformer.extract_volume("quantity\nnot-a-number\n") == 0


def test_extract_volume_ignores_extra_csv_columns():
    """Verify additional OCC CSV columns do not affect volume aggregation."""
    csv_text = "symbol,quantity,description\nAAPL,10,call\nAAPL,20,put\n"

    assert VolumeTransformer.extract_volume(csv_text) == 30


def test_extract_volume_handles_occ_rows_with_trailing_empty_column():
    """Verify live OCC rows with trailing delimiters keep quantity numeric."""
    csv_text = (
        "quantity,underlying,symbol,actype,porc,exchange,actdate\n"
        "25,AAPL,2AAPL,C,C,CBOE,06/23/2026,\n"
        "96,AAPL,2AAPL,M,C,ISE,06/23/2026,\n"
    )

    assert VolumeTransformer.extract_volume(csv_text) == 121
