# Equity Options Documentation

Equity Options is a Dockerized market-data and dashboard project. It retrieves
equity option data, enriches the latest contracts with Black-Scholes-Merton
metrics, and serves an interactive Dash dashboard behind Nginx.

```{toctree}
:maxdepth: 2
:caption: Project

overview
architecture
data-flow
setup
dashboard
```

```{toctree}
:maxdepth: 2
:caption: Packages

packages/data_retrieval
packages/option_metrics
packages/app
```

```{toctree}
:maxdepth: 1
:caption: API Reference

api/reference/index
```

## Build the Documentation

Install the documentation dependencies from the repository root:

```bash
python3 -m pip install -r docs/requirements.txt
```

Build the HTML site:

```bash
cd docs
make html
```

Open `docs/_build/html/index.html` in a browser.
