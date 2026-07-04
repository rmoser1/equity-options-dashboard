# Equity Options Dashboard

Dash application for exploring parquet outputs produced by the data retrieval
and option metric pipelines.

For the upstream parquet export, see
`data_retrieval/README.md`. For the metric columns added to
`options_last.parquet`, see `option_metrics/README.md`. Dashboard screenshots
and deployment details live in `docs/`.

## Architecture

The app is a small Dash package built around one app factory and a local parquet
contract. `dash_app.py:create_app()` resolves `AppConfig`, validates and loads
the parquet bundle, builds the layout, registers callbacks, and falls back to a
startup status page when required data is missing or invalid.

The main modules are:

- `config.py`: runtime settings from env vars, including `DASHBOARD_DATA_DIR`
  and the optional `DASHBOARD_FONT_SIZE_PRESET`.
- `modules/parquet_contract.py`: required dashboard parquet files and columns.
- `modules/load_app_data.py`: validated parquet loading plus derived dropdown,
  filter, and stock-info values.
- `modules/components.py`: shared component ID groups used by layouts and
  callbacks.
- `modules/layout/`: the app shell, shared Options filter workspace, and feature
  tabs for option prices, option metrics, stock info, and stock prices.
- `modules/callbacks/`: Dash callback registration for each feature area.
- `modules/plotly_figures/`: chart builders kept separate from callbacks so
  plotting behavior can be tested directly.
- `assets/dashboard.css`: dashboard frame, filter bands, nested tabs, tables,
  charts, and responsive styling.

## Data Contract

The app reads these files from `DASHBOARD_DATA_DIR` or `data/parquet`:

- `stocks.parquet`
- `options_hist.parquet`
- `options_last.parquet`
- `stock_info.parquet`
- `stock_prices.parquet`

`options_last.parquet` must include the option price columns, enrichment inputs
(`timeToExpiryYears`, `riskFreeRate`, `dividendYield`), and option metric outputs
(`calculatedImpliedVolatility`, `delta`, `gamma`, `theta`, `vega`, `rho`). The
contract is checked before the main layout and callbacks are registered.

## Run Locally

```bash
cd app
python3 -m pip install -r requirements.txt
DASHBOARD_DATA_DIR=../data/parquet python3 dash_app.py
```

Open `http://127.0.0.1:8050`.

Optional typography presets are `small`, `medium`, and `large`:

```bash
DASHBOARD_FONT_SIZE_PRESET=small DASHBOARD_DATA_DIR=../data/parquet python3 dash_app.py
```

## Run With Docker Compose

Use the root `compose.yaml` when running the dashboard as part of the full
stack. See `docs/setup.md` for the required Nginx auth, certificate files,
startup order, and daily refresh flow.

## Dashboard Views

The app starts with these top-level tabs:

- Options, with nested views for option prices and option metrics
- Stock info
- Stock prices

## Tests

From the repository root:

```bash
python3 -m pytest app/tests
```

The tests use temporary parquet fixtures and cover the parquet contract, app
factory, data loading, callback behavior, and Plotly figure builders.
