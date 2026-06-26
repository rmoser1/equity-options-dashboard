"""Runtime configuration for the Dash application.

This module defines default app settings, named typography presets, and helpers
for converting the selected font-size configuration into CSS variables.
"""

from dataclasses import dataclass
import os


DEFAULT_DASHBOARD_DATA_DIR = "data/parquet"
DEFAULT_FONT_SIZE_PRESET = "small"


@dataclass(frozen=True)
class FontSizeConfig:
    """Dashboard typography scale in pixels."""

    body: int = 16
    app_title: int = 34
    app_title_mobile: int = 25
    subtitle: int = 17
    status: int = 15
    tab: int = 14
    section_title: int = 22
    panel_title: int = 18
    field_label: int = 15
    control: int = 15
    filter_chip: int = 14
    hint: int = 14
    metric_note: int = 16
    info_dot: int = 11
    popover: int = 14
    table: int = 15
    chart: int = 15
    chart_title: int = 17
    chart_axis_title: int = 15
    chart_annotation: int = 13
    chart_heatmap_text: int = 9
    chart_hover: int = 15


SMALL_FONT_SIZES = FontSizeConfig(
    body=14,
    app_title=28,
    app_title_mobile=22,
    subtitle=15,
    status=13,
    tab=12,
    section_title=19,
    panel_title=16,
    field_label=13,
    control=13,
    filter_chip=12,
    hint=12,
    metric_note=14,
    info_dot=10,
    popover=12,
    table=13,
    chart=13,
    chart_title=15,
    chart_axis_title=13,
    chart_annotation=11,
    chart_heatmap_text=8,
    chart_hover=13,
)
MEDIUM_FONT_SIZES = FontSizeConfig()
LARGE_FONT_SIZES = FontSizeConfig(
    body=18,
    app_title=39,
    app_title_mobile=28,
    subtitle=19,
    status=17,
    tab=16,
    section_title=26,
    panel_title=20,
    field_label=17,
    control=17,
    filter_chip=16,
    hint=16,
    metric_note=18,
    info_dot=13,
    popover=16,
    table=17,
    chart=17,
    chart_title=19,
    chart_axis_title=17,
    chart_annotation=15,
    chart_heatmap_text=11,
    chart_hover=17,
)
FONT_SIZE_PRESETS = {
    "small": SMALL_FONT_SIZES,
    "medium": MEDIUM_FONT_SIZES,
    "large": LARGE_FONT_SIZES,
}
DEFAULT_FONT_SIZES = FONT_SIZE_PRESETS[DEFAULT_FONT_SIZE_PRESET]


@dataclass(frozen=True)
class AppConfig:
    """Dash application runtime configuration.

    :ivar dashboard_data_dir: Directory containing dashboard parquet files.
    :ivar font_size_preset: Name of the font-size preset to use when
        ``font_sizes`` is not provided.
    :ivar font_sizes: Optional explicit font-size configuration.
    """

    dashboard_data_dir: str = DEFAULT_DASHBOARD_DATA_DIR
    font_size_preset: str = DEFAULT_FONT_SIZE_PRESET

    font_sizes: FontSizeConfig | None = None

    @property
    def resolved_font_sizes(self) -> FontSizeConfig:
        """Return the configured font-size scale.

        :returns: The explicit ``font_sizes`` value, or the named preset from
            ``font_size_preset``.
        :raises ValueError: If ``font_size_preset`` is unknown.
        """
        if self.font_sizes is not None:
            return self.font_sizes
        return get_font_size_preset(self.font_size_preset)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build application config from environment variables.

        :returns: Config using ``DASHBOARD_DATA_DIR`` and
            ``DASHBOARD_FONT_SIZE_PRESET`` when set, otherwise module defaults.
        """
        return cls(
            dashboard_data_dir=os.getenv(
                "DASHBOARD_DATA_DIR",
                DEFAULT_DASHBOARD_DATA_DIR,
            ),
            font_size_preset=os.getenv(
                "DASHBOARD_FONT_SIZE_PRESET",
                DEFAULT_FONT_SIZE_PRESET,
            ),
        )


def get_font_size_preset(name: str) -> FontSizeConfig:
    """Return a named dashboard font-size preset.

    :param name: Preset name from :data:`FONT_SIZE_PRESETS`.
    :returns: Font-size configuration for ``name``.
    :raises ValueError: If ``name`` is not a known preset.
    """
    try:
        return FONT_SIZE_PRESETS[name]
    except KeyError as exc:
        options = ", ".join(sorted(FONT_SIZE_PRESETS))
        raise ValueError(
            f"Unknown font size preset '{name}'. Choose one of: {options}."
        ) from exc


def font_size_css_variables(
    font_sizes: FontSizeConfig = DEFAULT_FONT_SIZES,
) -> dict[str, str]:
    """Return CSS variables for dashboard font sizes.

    :param font_sizes: Font-size configuration to convert.
    :returns: CSS variable names and pixel values for dashboard typography.
    """
    return {
        "--font-size-body": f"{font_sizes.body}px",
        "--font-size-app-title": f"{font_sizes.app_title}px",
        "--font-size-app-title-mobile": f"{font_sizes.app_title_mobile}px",
        "--font-size-subtitle": f"{font_sizes.subtitle}px",
        "--font-size-status": f"{font_sizes.status}px",
        "--font-size-tab": f"{font_sizes.tab}px",
        "--font-size-section-title": f"{font_sizes.section_title}px",
        "--font-size-panel-title": f"{font_sizes.panel_title}px",
        "--font-size-field-label": f"{font_sizes.field_label}px",
        "--font-size-control": f"{font_sizes.control}px",
        "--font-size-filter-chip": f"{font_sizes.filter_chip}px",
        "--font-size-hint": f"{font_sizes.hint}px",
        "--font-size-metric-note": f"{font_sizes.metric_note}px",
        "--font-size-info-dot": f"{font_sizes.info_dot}px",
        "--font-size-popover": f"{font_sizes.popover}px",
        "--font-size-table": f"{font_sizes.table}px",
        "fontSize": "var(--font-size-body)",
    }
