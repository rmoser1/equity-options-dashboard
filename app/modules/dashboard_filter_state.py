"""Input and output helpers for dashboard filter state.

This module owns shared dashboard selector defaults plus helpers that convert
stock, option direction, expiration, and relative-strike selections into values
that can be assigned to option filter controls. They preserve existing
selections when possible, replace invalid expiration choices with an initial
slice of available expirations, and clamp relative-strike ranges to the bounds
present in the option data.
"""

from dataclasses import dataclass

import pandas as pd


DEFAULT_MULTIPLE_STOCKS = ["AAPL", "MSFT"]
DEFAULT_SINGLE_STOCK = "SPY"
DEFAULT_DIRECTION = "PUT"
DEFAULT_EXPIRATION_COUNT = 10
DEFAULT_RELATIVE_STRIKE_RANGE = [0.85, 1.10]


@dataclass(frozen=True)
class OptionFilterControls:
    """Option filter output values.

    :ivar expiration_options: Expiration dropdown options.
    :ivar expiration_value: Selected expiration dropdown values.
    :ivar relative_strike_min: Relative-strike slider minimum.
    :ivar relative_strike_max: Relative-strike slider maximum.
    :ivar relative_strike_value: Selected relative-strike slider range.
    """

    expiration_options: list[dict[str, str]]
    expiration_value: list[str]
    relative_strike_min: float
    relative_strike_max: float
    relative_strike_value: list[float]


def option_symbols(selected_stock: str | None, selected_stocks: list[str] | None) -> list[str]:
    """Return unique symbols from selector inputs.

    :param selected_stock: Single selected stock symbol.
    :param selected_stocks: Multiple selected stock symbols.
    :returns: Sorted unique symbols from both selectors.
    """
    symbols = set(selected_stocks or [])
    if selected_stock:
        symbols.add(selected_stock)
    return sorted(symbols)


def derive_option_filter_controls(
    options: pd.DataFrame,
    selected_stock: str | None,
    selected_stocks: list[str] | None,
    direction: str,
    current_expirations: list[str] | None,
    current_relative_strikes: list[float] | None,
) -> OptionFilterControls:
    """Return option filter outputs for the given inputs.

    :param options: ``options_last`` dataframe containing at least
        ``stockSymbol``, ``direction``, ``expirationDate``, and
        ``relativeStrikePrice``.
    :param selected_stock: Single selected stock symbol.
    :param selected_stocks: Multiple selected stock symbols.
    :param direction: Selected option direction.
    :param current_expirations: Current expiration dropdown values.
    :param current_relative_strikes: Current relative-strike slider range.
    :returns: Derived expiration options, selected expiration values, and
        relative-strike slider bounds and value.
    """
    symbols = option_symbols(selected_stock, selected_stocks)
    filtered = options[
        options["stockSymbol"].isin(symbols) & (options["direction"] == direction)
    ]
    if filtered.empty:
        return OptionFilterControls([], [], 0, 1, [0, 1])

    expirations = pd.to_datetime(filtered["expirationDate"]).drop_duplicates()
    expiration_options = [
        {"label": date.strftime("%Y-%m-%d"), "value": date.isoformat()}
        for date in expirations.sort_values()
    ]
    available_values = [option["value"] for option in expiration_options]

    minimum = float(filtered["relativeStrikePrice"].min())
    maximum = float(filtered["relativeStrikePrice"].max())
    return OptionFilterControls(
        expiration_options=expiration_options,
        expiration_value=valid_expiration_value(current_expirations, available_values),
        relative_strike_min=minimum,
        relative_strike_max=maximum,
        relative_strike_value=valid_relative_strike_value(
            current_relative_strikes,
            minimum,
            maximum,
        ),
    )


def default_relative_strike_range(value_range: list[float]) -> list[float]:
    """Return the default relative-strike range.

    :param value_range: Two-item available ``[minimum, maximum]`` range.
    :returns: Two-item default ``[lower, upper]`` range.
    """
    return valid_relative_strike_value(None, value_range[0], value_range[1])


def valid_expiration_value(
    current_expirations: list[str] | None,
    available_values: list[str],
) -> list[str]:
    """Return valid expiration dropdown values.

    :param current_expirations: Current expiration dropdown values.
    :param available_values: Available ISO-formatted expiration values.
    :returns: Selected expiration values contained in ``available_values``.
    """
    current = {
        pd.Timestamp(value).isoformat()
        for value in (current_expirations or [])
        if value is not None
    }
    value = [date for date in available_values if date in current]
    if value:
        return value
    return available_values[: min(DEFAULT_EXPIRATION_COUNT, len(available_values))]


def valid_relative_strike_value(
    current_value: list[float] | None,
    minimum: float,
    maximum: float,
) -> list[float]:
    """Return a valid relative-strike slider range.

    :param current_value: Current two-endpoint slider range.
    :param minimum: Minimum available relative strike price.
    :param maximum: Maximum available relative strike price.
    :returns: Two-item ``[lower, upper]`` relative-strike slider value.
    """
    if current_value and len(current_value) == 2:
        lower = max(minimum, float(current_value[0]))
        upper = min(maximum, float(current_value[1]))
        if lower <= upper:
            return [lower, upper]

    lower = max(minimum, DEFAULT_RELATIVE_STRIKE_RANGE[0])
    upper = min(maximum, DEFAULT_RELATIVE_STRIKE_RANGE[1])
    if lower > upper:
        return [minimum, maximum]
    return [lower, upper]
