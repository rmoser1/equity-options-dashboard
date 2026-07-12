"""Tests for :mod:`option_metrics.transformer`."""

import pandas as pd
import pytest

from option_metrics.transformer import OptionMetricsTransformer


def test_transform_appends_metrics_to_options_dataframe():
    """Verify the transformer preserves input rows and appends metric columns."""
    options = pd.DataFrame(
        [
            {
                "contractSymbol": "AAPL260131C00100000",
                "stockSymbol": "AAPL",
                "timeToExpiryYears": 30 / 365,
                "strike": 100.0,
                "ask": 2.898810513716974,
                "direction": "CALL",
                "lastStockPrice": 100.0,
                "riskFreeRate": 0.01,
                "dividendYield": 0.0,
            }
        ]
    )

    result = OptionMetricsTransformer.transform(options)

    assert result.loc[0, "contractSymbol"] == "AAPL260131C00100000"
    assert set(OptionMetricsTransformer.METRIC_COLUMNS).issubset(result.columns)
    assert result.loc[0, "timeToExpiryYears"] == pytest.approx(30 / 365)
    assert result.loc[0, "calculatedImpliedVolatility"] == pytest.approx(0.25, rel=1e-8)
    assert result.loc[0, "delta"] > 0
    assert result.loc[0, "gamma"] > 0


def test_transform_consumes_decimal_dividend_yield():
    """Verify dashboard dividend yields reach the pricing model as decimals."""
    options = pd.DataFrame(
        [
            {
                "timeToExpiryYears": 30 / 365,
                "strike": 100.0,
                "ask": 2.8479303712546127,
                "direction": "CALL",
                "lastStockPrice": 100.0,
                "riskFreeRate": 0.01,
                "dividendYield": 0.012,
            }
        ]
    )

    result = OptionMetricsTransformer.transform(options)

    assert result.loc[0, "calculatedImpliedVolatility"] == pytest.approx(
        0.25,
        rel=1e-8,
    )


def test_transform_expands_implied_volatility_search_bound():
    """Solve quotes whose implied volatility exceeds the initial 500% bound."""
    options = pd.DataFrame(
        [
            {
                "timeToExpiryYears": 30 / 365,
                "strike": 100.0,
                "ask": 60.961774652657866,
                "direction": "CALL",
                "lastStockPrice": 100.0,
                "riskFreeRate": 0.01,
                "dividendYield": 0.012,
            }
        ]
    )

    result = OptionMetricsTransformer.transform(options)

    assert result.loc[0, "calculatedImpliedVolatility"] == pytest.approx(
        6.0,
        rel=1e-8,
    )


def test_transform_sets_nan_metrics_for_invalid_rows():
    """Verify invalid rows do not prevent valid output generation."""
    options = pd.DataFrame(
        [
            {
                "timeToExpiryYears": -30 / 365,
                "strike": 100.0,
                "ask": 1.0,
                "direction": "CALL",
                "lastStockPrice": 100.0,
                "riskFreeRate": 0.0,
                "dividendYield": 0.0,
            }
        ]
    )

    result = OptionMetricsTransformer.transform(options)

    assert result.loc[0, "timeToExpiryYears"] < 0
    assert pd.isna(result.loc[0, "calculatedImpliedVolatility"])
    assert pd.isna(result.loc[0, "delta"])


def test_transform_replaces_existing_metric_columns():
    """Verify reruns overwrite metrics instead of duplicating columns."""
    options = pd.DataFrame(
        [
            {
                "timeToExpiryYears": 30 / 365,
                "strike": 100.0,
                "ask": 2.898810513716974,
                "direction": "CALL",
                "lastStockPrice": 100.0,
                "riskFreeRate": 0.01,
                "dividendYield": 0.0,
                "delta": -999.0,
            }
        ]
    )

    result = OptionMetricsTransformer.transform(options)

    assert result.columns.tolist().count("delta") == 1
    assert result.loc[0, "delta"] > 0


def test_transform_requires_expected_input_columns():
    """Verify missing required input columns raise a clear error."""
    with pytest.raises(ValueError, match="Missing required columns"):
        OptionMetricsTransformer.transform(pd.DataFrame({"strike": [100.0]}))
