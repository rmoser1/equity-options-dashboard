# Overview

Equity Options is a Dockerized market-data and dashboard project for exploring
equity options. It retrieves OCC and yfinance data, stores normalized rows in
SQLite, exports dashboard-ready parquet files, enriches the latest options with
Black-Scholes-Merton metrics, and serves an interactive Dash app behind Nginx.

## Runtime Services

| Service | Source | Role |
| --- | --- | --- |
| `data_retrieval` | `data_retrieval/` | Downloads OCC and yfinance data, stores SQLite rows, and writes dashboard parquet files. |
| `option_metrics` | `option_metrics/` | Adds implied volatility and Greeks to the latest option-contract parquet data. |
| `app` | `app/` | Serves the Dash dashboard with Gunicorn. |
| `nginx` | `nginx/` | Handles SSL, basic auth, and reverse proxying to the app service. |

Startup order:

```text
data_retrieval -> option_metrics -> app -> nginx
```

The batch services write shared files under `data/`, and the app reads the
resulting parquet bundle at startup.

## Data Flow

```text
OCC + yfinance
  -> data_retrieval
  -> SQLite + dashboard parquet
  -> option_metrics
  -> Dash app
  -> Nginx
```

Main runtime outputs:

```text
data/
  DB.db
  parquet/
    stocks.parquet
    options_hist.parquet
    options_last.parquet
    stock_info.parquet
    stock_prices.parquet
logs/
```

## Repository Map

```text
data_retrieval/  Data ingestion, SQLite storage, and dashboard parquet export.
option_metrics/      Option metric calculation pipeline.
app/             Dash dashboard.
nginx/               Reverse proxy image and configuration.
deploy/systemd/      Daily refresh service and timer templates.
scripts/             Operational scripts used by deployment automation.
docs/                Sphinx documentation source.
```

## Package Documentation

- {doc}`packages/data_retrieval`: ingestion, SQLite schemas, parquet export,
  configuration, and tests.
- {doc}`packages/option_metrics`: metric input/output contract and runtime
  command.
- {doc}`packages/app`: Dash app architecture, parquet contract, local run
  command, and tests.

## Tests

Run the standard test suite from the repository root:

```bash
python3 -m pytest
```

Live OCC/yfinance provider checks are opt-in contract tests:

```bash
python3 -m pytest -m contract
```
