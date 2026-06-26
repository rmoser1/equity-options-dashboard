"""Sphinx configuration for the Equity Options documentation."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

project = "Equity Options"
author = "Richard Moser"

extensions = [
    "myst_parser",
    "autoapi.extension",
    "sphinxcontrib.mermaid",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
suppress_warnings = ["ref.python"]
html_theme = "furo"
html_title = "Equity Options Documentation"
html_static_path = ["_static"]

myst_enable_extensions = [
    "colon_fence",
]
myst_fence_as_directive = ["mermaid"]

autoapi_type = "python"
autoapi_dirs = [
    str(PROJECT_ROOT),
]
autoapi_ignore = [
    "*/deploy/*",
    "*/docs/*",
    "*/nginx/*",
    "*/scripts/*",
    "*/tests/*",
    "*/gunicorn.conf.py",
    "*/Dockerfile",
]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]
autoapi_root = "api/reference"
