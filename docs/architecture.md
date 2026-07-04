# Architecture

```{mermaid}
flowchart TD
    OCC[OCC market data] --> DR[data_retrieval]
    YF[yfinance] --> DR
    DR --> DB[(SQLite DB)]
    DR --> PQ[Dashboard parquet files]
    PQ --> OM[option_metrics]
    OM --> Enriched[enriched options_last.parquet]
    Enriched --> APP[Dash app]
    APP --> NGINX[Nginx]
```

The Compose startup order is:

```text
data_retrieval -> option_metrics -> app -> nginx
```

`data_retrieval` and `option_metrics` are one-shot batch jobs. The `app` service
starts only after the batch jobs complete successfully, and `nginx` starts only
after the app healthcheck passes.

For daily refreshes, `scripts/daily-startup.sh` reruns the batch services while
the current dashboard stays online. It recreates the app and Nginx services only
after fresh parquet data is available.
