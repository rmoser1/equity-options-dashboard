# Data Flow

## Ingestion

`data_retrieval` downloads OCC underlyings and aggregate option volume,
filters underlyings by volume, fetches yfinance option chains, stock metadata,
historical prices, and Treasury-rate inputs, then stores normalized rows in
SQLite.

## Dashboard Export

`dashboard_data` reads SQLite tables and writes these parquet files:

```text
data/parquet/
  stocks.parquet
  options_hist.parquet
  options_last.parquet
  stock_info.parquet
  stock_prices.parquet
```

`options_last.parquet` includes dashboard enrichment fields such as
`timeToExpiryYears`, `riskFreeRate`, `dividendYield`, and
`relativeStrikePrice`.

## Metrics

`option_metrics` reads `options_last.parquet`, calculates implied volatility and
Greeks, and atomically overwrites the same dashboard-facing file:

```text
data/parquet/options_last.parquet
```

Theta is reported per calendar day. Vega and rho are reported per one percentage
point move.

## Dashboard

`app` validates the required parquet files at startup. If files are missing
or invalid, the app serves a startup status page instead of registering the main
dashboard callbacks.
