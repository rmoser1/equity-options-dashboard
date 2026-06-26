"""Tests for :mod:`etl.transformers.underlying_transformer`.

The transformer accepts OCC tab-delimited download bytes plus configured field
descriptions, then returns normalized equity-underlying schema rows.
"""

import pandas as pd
import pytest

from etl.config.occ import download_field_descriptions
from etl.transformers.underlying_transformer import UnderlyingTransformer
from schemas.underlying import Underlying


def test_transform_filters_equity_underlyings_and_deduplicates_symbols():
    """Verify OCC rows are filtered, normalized, and deduplicated."""
    content = (
        b"OPT1\t AAPL \t apple inc \tNYSE\t1\tEU\t\n"
        b"OPT2\tAAPL\tduplicate\tNYSE\t1\tEU\t\n"
        b"OPT3\t SPX \ts&p 500\tCBOE\t1\tIU\t\n"
    )

    rows = UnderlyingTransformer.transform(content, download_field_descriptions())

    assert len(rows) == 1
    assert isinstance(rows[0], Underlying)
    assert rows[0].symbol == "AAPL"
    assert rows[0].name == "Apple Inc"


def test_transform_keeps_first_duplicate_symbol():
    """Verify duplicate OCC symbols preserve the first row's name."""
    content = (
        b"OPT1\t AAPL \t apple inc \tNYSE\t1\tEU\t\n"
        b"OPT2\tAAPL\tapple duplicate inc\tNYSE\t1\tEU\t\n"
    )

    rows = UnderlyingTransformer.transform(content, download_field_descriptions())

    assert rows == [Underlying(symbol="AAPL", name="Apple Inc")]


def test_transform_accepts_rows_without_trailing_empty_column():
    """Verify OCC rows are accepted when they do not end with a trailing tab."""
    content = b"OPT1\t AAPL \t apple inc \tNYSE\t1\tEU\n"

    rows = UnderlyingTransformer.transform(content, download_field_descriptions())

    assert rows == [Underlying(symbol="AAPL", name="Apple Inc")]


def test_transform_returns_empty_list_when_no_equity_underlyings():
    """Verify non-equity OCC rows are filtered out completely."""
    content = (
        b"OPT1\t SPX \ts&p 500 index\tCBOE\t1\tIU\t\n"
        b"OPT2\t VIX \tcboe volatility index\tCBOE\t1\tIU\t\n"
    )

    assert UnderlyingTransformer.transform(content, download_field_descriptions()) == []


def test_transform_raises_for_empty_file_content():
    """Verify empty OCC files surface a parse failure."""
    with pytest.raises(pd.errors.EmptyDataError):
        UnderlyingTransformer.transform(b"", download_field_descriptions())


def test_transform_raises_for_unexpected_column_count():
    """Verify malformed OCC files surface a schema mismatch."""
    content = b"OPT1\tAAPL\tapple inc\tNYSE\t1\tEU\tunexpected\t\n"

    with pytest.raises(ValueError, match="Length mismatch"):
        UnderlyingTransformer.transform(content, download_field_descriptions())
