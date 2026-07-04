# Dashboard

The Dash app provides these top-level views:

- Options, with nested views for option prices and option metrics.
- Stock info.
- Stock prices.

The screenshots below were captured from a local dashboard run using the parquet
bundle in `data/parquet`.

## Option Prices

![Option prices dashboard view](_static/screenshots/options-prices.png)

The option price workflow includes multiple-stock scatter charts, single-stock
heatmaps, and a selected-contract time series.

### Multiple Stocks

![Relative strike option price scatter](_static/screenshots/option-prices-relative-strike-scatter.png)

![Expiration option price scatter](_static/screenshots/option-prices-expiration-scatter.png)

### Single Stock

![Cost per contract heatmap](_static/screenshots/option-prices-cost-per-contract.png)

![Option volume heatmap](_static/screenshots/option-prices-volume.png)

### Single Contract

![Option contract time series](_static/screenshots/option-prices-contract-timeseries.png)

## Option Metrics

![Option metrics dashboard view](_static/screenshots/option-metrics.png)

The option metrics view shows heatmaps for implied volatility and Greeks. The
implied-volatility chart below is representative of the metric chart layout.

![Implied volatility heatmap](_static/screenshots/option-metrics-implied-volatility-heatmap.png)

## Stock Info

![Stock info dashboard view](_static/screenshots/stock-info.png)

## Stock Prices

![Stock prices dashboard view](_static/screenshots/stock-prices.png)

The stock price view compares price history and volume for the selected
underlying.

![Stock price history chart](_static/screenshots/stock-prices-history.png)

## Startup Status

When required parquet files are missing, the app starts with a status page
instead of registering the full dashboard.

![Missing parquet startup status](_static/screenshots/startup-status.png)
