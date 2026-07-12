"""Callbacks for option price filters and charts."""

from io import StringIO

from dash import Dash, Input, Output, State, ctx, html
import pandas as pd

from config import DEFAULT_FONT_SIZES, FontSizeConfig
from modules.components import ComponentGroups, DEFAULT_SINGLE_STOCK
from modules.plotly_figures.option_prices import (
    heatmaps_options_single_stock,
    option_time_series,
    scatter_relativeOptionPrice_vs_expirationDate,
    scatter_relativeOptionPrice_vs_relativeStrikePrice,
)
from modules.parquet_contract import OPTION_METRIC_COLUMNS


def register_option_price_callbacks(
    app: Dash,
    components: ComponentGroups,
    data: dict,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> None:
    """Register option-price callbacks.

    :param app: Dash app instance.
    :param components: Named dashboard component groups.
    :param data: Dashboard app data.
    :param font_sizes: Dashboard font-size scale.
    """
    options = data["options_last_df"]
    options_hist = data["options_hist_df"]

    _register_single_stock_sync_callback(app, components)
    _register_option_filter_callback(app, components, options)
    _register_contract_selection_callback(app, components)
    _register_multiple_stock_charts_callback(app, components, font_sizes)
    _register_single_stock_charts_callback(app, components, font_sizes)
    _register_contract_time_series_callback(app, components, options_hist, font_sizes)


def _register_single_stock_sync_callback(
    app: Dash,
    components: ComponentGroups,
) -> None:
    """Register callbacks that keep single-stock selectors synchronized."""

    @app.callback(
        output=dict(
            selected_stock=Output(components.store.selected_single_stock, "data"),
            single_stock_value=Output(
                components.filters.single_stock_selection,
                "value",
            ),
            contract_stock_value=Output(
                components.filters.contract_single_stock_selection,
                "value",
            ),
            metric_stock_value=Output(
                components.filters.metric_single_stock_selection,
                "value",
            ),
        ),
        inputs=dict(
            single_stock=Input(
                components.filters.single_stock_selection,
                "value",
            ),
            contract_stock=Input(
                components.filters.contract_single_stock_selection,
                "value",
            ),
            metric_stock=Input(
                components.filters.metric_single_stock_selection,
                "value",
            ),
        ),
        state=dict(
            current_stock=State(components.store.selected_single_stock, "data"),
        ),
    )
    def sync_single_stock_selectors_callback(
        single_stock,
        contract_stock,
        metric_stock,
        current_stock,
    ):
        selected_stock = _synced_single_stock_value(
            ctx.triggered_id,
            single_stock,
            contract_stock,
            metric_stock,
            current_stock,
            components.filters.single_stock_selection.id,
            components.filters.contract_single_stock_selection.id,
            components.filters.metric_single_stock_selection.id,
        )

        return dict(
            selected_stock=selected_stock,
            single_stock_value=selected_stock,
            contract_stock_value=selected_stock,
            metric_stock_value=selected_stock,
        )


def _synced_single_stock_value(
    triggered_id: str | None,
    single_stock: str | None,
    contract_stock: str | None,
    metric_stock: str | None,
    current_stock: str | None,
    single_stock_id: str,
    contract_stock_id: str,
    metric_stock_id: str,
) -> str:
    """Choose the current single-stock value from synced selectors."""
    selected_stock = current_stock or DEFAULT_SINGLE_STOCK
    if triggered_id == single_stock_id:
        return single_stock or selected_stock
    if triggered_id == contract_stock_id:
        return contract_stock or selected_stock
    if triggered_id == metric_stock_id:
        return metric_stock or selected_stock
    return single_stock or contract_stock or metric_stock or selected_stock


def _register_option_filter_callback(
    app: Dash,
    components: ComponentGroups,
    options: pd.DataFrame,
) -> None:
    """Register the option filtering callback."""

    @app.callback(
        output=dict(
            filtered_options_single_stock=Output(
                components.store.filtered_options_single_stock,
                "data",
            ),
            filtered_options_multiple_stocks=Output(
                components.store.filtered_options_multiple_stocks,
                "data",
            ),
            multiple_stock_filter_summary=Output(
                components.text.multiple_stock_filter_summary,
                "children",
            ),
            single_stock_filter_summary=Output(
                components.text.single_stock_filter_summary,
                "children",
            ),
            contract_filter_summary=Output(
                components.text.contract_filter_summary,
                "children",
            ),
            metric_filter_summary=Output(
                components.text.metric_filter_summary,
                "children",
            ),
        ),
        inputs=dict(
            selected_stock=Input(components.store.selected_single_stock, "data"),
            selected_stocks=Input(components.filters.multiple_stock_selection, "value"),
            direction=Input(components.filters.direction, "value"),
            selected_expiration_dates=Input(
                components.filters.expiration_dates,
                "value",
            ),
            relativeStrikePrice_Range=Input(
                components.filters.relative_strike_price_range,
                "value",
            ),
            cost_per_contract_range=Input(
                components.filters.cost_per_contract_range,
                "value",
            ),
        ),
    )
    def options_callback(
        selected_stock,
        selected_stocks,
        direction,
        selected_expiration_dates,
        relativeStrikePrice_Range,
        cost_per_contract_range,
    ):
        selected_stocks = selected_stocks or []
        selected_expiration_dates = selected_expiration_dates or []
        selected_expiration_dates = pd.to_datetime(selected_expiration_dates)

        filtered_options = options[
            (options["direction"] == direction)
            & (
                pd.to_datetime(options["expirationDate"]).isin(
                    selected_expiration_dates
                )
            )
            & (
                options["relativeStrikePrice"].between(
                    relativeStrikePrice_Range[0],
                    relativeStrikePrice_Range[1],
                )
            )
            & (
                options["costPerContract"].between(
                    cost_per_contract_range[0],
                    cost_per_contract_range[1],
                )
            )
        ]

        filtered_options_single_stock = filtered_options[
            filtered_options["stockSymbol"] == selected_stock
        ].reset_index()
        filtered_options_multiple_stocks = filtered_options[
            filtered_options["stockSymbol"].isin(selected_stocks)
        ].reset_index()

        n_contracts_single_stock = filtered_options_single_stock.shape[0]
        n_contracts_multiple_stocks = filtered_options_multiple_stocks.shape[0]
        n_metric_contracts = int(
            filtered_options_single_stock[list(OPTION_METRIC_COLUMNS)]
            .notna()
            .all(axis=1)
            .sum()
        )

        return dict(
            filtered_options_single_stock=filtered_options_single_stock.to_json(
                orient="split"
            ),
            filtered_options_multiple_stocks=filtered_options_multiple_stocks.to_json(
                orient="split"
            ),
            multiple_stock_filter_summary=_filter_summary(
                stock_chip=_selected_stocks_chip(selected_stocks),
                direction=direction,
                selected_expiration_dates=selected_expiration_dates,
                relative_strike_range=relativeStrikePrice_Range,
                cost_per_contract_range=cost_per_contract_range,
                n_contracts=n_contracts_multiple_stocks,
            ),
            single_stock_filter_summary=_filter_summary(
                stock_chip=f"Single: {selected_stock or 'None'}",
                direction=direction,
                selected_expiration_dates=selected_expiration_dates,
                relative_strike_range=relativeStrikePrice_Range,
                cost_per_contract_range=cost_per_contract_range,
                n_contracts=n_contracts_single_stock,
            ),
            contract_filter_summary=_filter_summary(
                stock_chip=f"Single: {selected_stock or 'None'}",
                direction=direction,
                selected_expiration_dates=selected_expiration_dates,
                relative_strike_range=relativeStrikePrice_Range,
                cost_per_contract_range=cost_per_contract_range,
                n_contracts=n_contracts_single_stock,
            ),
            metric_filter_summary=_filter_summary(
                stock_chip=f"Single: {selected_stock or 'None'}",
                direction=direction,
                selected_expiration_dates=selected_expiration_dates,
                relative_strike_range=relativeStrikePrice_Range,
                cost_per_contract_range=cost_per_contract_range,
                n_contracts=n_contracts_single_stock,
                n_metric_contracts=n_metric_contracts,
            ),
        )


def _register_contract_selection_callback(
    app: Dash,
    components: ComponentGroups,
) -> None:
    """Register the contract-selection callback."""

    @app.callback(
        output=dict(
            contracts=Output(components.filters.contract_selection, "options"),
            preselected=Output(components.filters.contract_selection, "value"),
        ),
        inputs=dict(
            df=Input(components.store.filtered_options_single_stock, "data"),
        ),
    )
    def contractSelectionDropdown_callback(df):
        df = _read_store(df)
        if df.empty:
            return dict(contracts=[], preselected=None)
        contracts = df["contractSymbol"].unique()
        preselected = contracts[-1]
        return dict(contracts=contracts, preselected=preselected)


def _register_multiple_stock_charts_callback(
    app: Dash,
    components: ComponentGroups,
    font_sizes: FontSizeConfig,
) -> None:
    """Register the multiple-stock option chart callback."""

    @app.callback(
        output=dict(
            strikePrice_Graph=Output(
                components.charts.strike_price_multiple_stocks,
                "figure",
            ),
            expirationDate_Graph=Output(
                components.charts.expiration_date_multiple_stocks,
                "figure",
            ),
        ),
        inputs=dict(
            df=Input(components.store.filtered_options_multiple_stocks, "data"),
        ),
    )
    def multiple_stock_option_charts_callback(df):
        df = _read_store(df)
        return dict(
            strikePrice_Graph=scatter_relativeOptionPrice_vs_relativeStrikePrice(
                df,
                font_sizes=font_sizes,
            ),
            expirationDate_Graph=scatter_relativeOptionPrice_vs_expirationDate(
                df,
                font_sizes=font_sizes,
            ),
        )


def _register_single_stock_charts_callback(
    app: Dash,
    components: ComponentGroups,
    font_sizes: FontSizeConfig,
) -> None:
    """Register the single-stock option chart callback."""

    @app.callback(
        output=dict(
            nominal_per_contract_Div=Output(
                components.text.nominal_per_contract,
                "children",
            ),
            cost_per_contract_Graph=Output(
                components.charts.cost_per_contract_single_stock,
                "figure",
            ),
            option_volume_Graph=Output(
                components.charts.volume_single_stock,
                "figure",
            ),
        ),
        inputs=dict(
            df=Input(components.store.filtered_options_single_stock, "data"),
            selected_stock=Input(components.store.selected_single_stock, "data"),
            direction=Input(components.filters.direction, "value"),
        ),
    )
    def single_stock_option_charts_callback(df, selected_stock, direction):
        df = _read_store(df)
        if df.empty:
            cost_per_contract_Graph, option_volume_Graph = heatmaps_options_single_stock(
                df,
                selected_stock,
                direction,
                font_sizes=font_sizes,
            )
            return dict(
                nominal_per_contract_Div="No contracts matching",
                cost_per_contract_Graph=cost_per_contract_Graph,
                option_volume_Graph=option_volume_Graph,
            )

        df["relativeStrikePrice"] = df["relativeStrikePrice"].round(4)
        df["relativeOptionPrice"] = df["relativeOptionPrice"].round(4)

        cost_per_contract_Graph, option_volume_Graph = heatmaps_options_single_stock(
            df,
            selected_stock,
            direction,
            font_sizes=font_sizes,
        )
        nominal_per_contract = df.loc[0, "nominalPerContract"]

        return dict(
            nominal_per_contract_Div=f"Nominal per contract: {nominal_per_contract:,} $",
            cost_per_contract_Graph=cost_per_contract_Graph,
            option_volume_Graph=option_volume_Graph,
        )


def _register_contract_time_series_callback(
    app: Dash,
    components: ComponentGroups,
    options_hist: pd.DataFrame,
    font_sizes: FontSizeConfig,
) -> None:
    """Register the contract time-series callback."""

    @app.callback(
        output=dict(
            optionTimeSeriesGraph=Output(
                components.charts.options_time_series,
                "figure",
            ),
        ),
        inputs=dict(
            selected_contract=Input(components.filters.contract_selection, "value"),
        ),
    )
    def optionTimeSeries_callback(selected_contract):
        df = options_hist.loc[options_hist["contractSymbol"] == selected_contract, :]
        return dict(
            optionTimeSeriesGraph=option_time_series(
                df=df,
                contractSymbol=selected_contract,
                font_sizes=font_sizes,
            )
        )


def _read_store(data: str | None) -> pd.DataFrame:
    """Read a JSON store payload into a DataFrame."""
    if not data:
        return pd.DataFrame()
    df = pd.read_json(StringIO(data), orient="split")
    for column in ["expirationDate", "lastTradeDate"]:
        if column in df:
            unit = "ms" if pd.api.types.is_numeric_dtype(df[column]) else None
            df[column] = pd.to_datetime(df[column], unit=unit)
    return df


def _filter_summary(
    stock_chip: str,
    direction: str,
    selected_expiration_dates,
    relative_strike_range: list[float],
    cost_per_contract_range: list[float],
    n_contracts: int,
    n_metric_contracts: int | None = None,
) -> list:
    """Create active option filter summary chips."""
    expirations = pd.to_datetime(selected_expiration_dates)
    expiration_text = f"{len(expirations)} expirations"
    if len(expirations) == 1:
        expiration_text = expirations[0].strftime("%Y-%m-%d")
    chips = [
        stock_chip,
        direction,
        expiration_text,
        f"Strike {relative_strike_range[0]:.2f}-{relative_strike_range[1]:.2f}",
        (
            f"Cost ${cost_per_contract_range[0]:,.0f}-"
            f"${cost_per_contract_range[1]:,.0f}"
        ),
        f"Matches {n_contracts:,}",
    ]
    if n_metric_contracts is not None:
        contract_label = "contract" if n_metric_contracts == 1 else "contracts"
        chips.append(
            f"Thereof {n_metric_contracts:,} {contract_label} "
            "with valid calculated metrics"
        )
    return [html.Span(chip, className="filter-chip") for chip in chips]


def _selected_stocks_chip(selected_stocks: list[str]) -> str:
    """Create the multiple-stock filter summary chip."""
    selected_stocks_text = ", ".join(selected_stocks) if selected_stocks else "None"
    return f"Multiple: {selected_stocks_text}"
