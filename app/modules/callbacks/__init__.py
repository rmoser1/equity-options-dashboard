"""Callback registration package for dashboard feature areas."""

from dash import Dash

from modules.callbacks.option_metrics import register_option_metric_callbacks
from modules.callbacks.option_prices import register_option_price_callbacks
from modules.callbacks.stock_info import register_stock_info_callbacks
from modules.callbacks.stock_prices import register_stock_price_callbacks
from modules.components import ComponentGroups
from config import DEFAULT_FONT_SIZES, FontSizeConfig


def register_callbacks(
    app: Dash,
    components: ComponentGroups,
    data: dict,
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> None:
    """Register all dashboard callbacks on a Dash app instance.

    :param app: Dash app instance.
    :param components: Named dashboard component groups.
    :param data: Dashboard app data.
    :param font_sizes: Dashboard font-size scale.
    """
    register_option_price_callbacks(app, components, data, font_sizes)
    register_stock_info_callbacks(app, components, data)
    register_stock_price_callbacks(app, components, data, font_sizes)
    register_option_metric_callbacks(app, components, data, font_sizes)
