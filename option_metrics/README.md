# Option Metrics

Calculates Black-Scholes-Merton implied volatility and Greeks for the latest
option contracts exported by `data_retrieval`.

For the upstream parquet export, see
`data_retrieval/README.md`. For the downstream dashboard contract, see
`app/README.md`.

## Input

The package reads:

```text
data/parquet/options_last.parquet
```

Required columns are `timeToExpiryYears`, `strike`, `ask`, `direction`,
`lastStockPrice`, `riskFreeRate`, and `dividendYield`.

## Output

The package atomically overwrites:

```text
data/parquet/options_last.parquet
```

The output preserves the input columns and appends
`calculatedImpliedVolatility`, `delta`, `gamma`, `theta`, `vega`, and `rho`.
Theta is per calendar day. Vega and rho are per one percentage point move.

## Run

```bash
python3 -m option_metrics.main
```

The app reads `DASHBOARD_DATA_DIR` when set, falling back to `data/parquet`.
Logs are always written to a file. Set `OPTION_METRICS_LOG_FILE` or `LOG_FILE`
to override the default `../logs/option_metrics.log` path.

## Docker

The Compose service expects dashboard parquet files under `/app/data/parquet`
and writes logs to `/app/logs/option_metrics.log`.

```bash
docker compose run --rm option_metrics
```

See `docs/setup.md` for the complete stack startup order and daily refresh flow.
