"""Static OCC field and product type configuration."""

OCC_DOWNLOAD_FIELDS = {
    "OS": "Option Symbol",
    "US": "Underlying Symbol",
    "SN": "Symbol Name",
    "EXCH": "Exchanges",
    "PL": "Position Limit",
    "ONN": "Product Type",
}

OCC_PRODUCT_TYPES = {
    "EU": "equity underlying",
    "EB": "equity bounds",
    "EL": "equity long term",
    "EF": "equity FLEX",
    "CU": "currency underlying",
    "CL": "currency long term",
    "CM": "currency month end",
    "CF": "currency FLEX",
    "IL": "index long term",
    "IU": "index underlying",
    "IF": "index FLEX",
    "GF": "interest rate futures",
    "SF": "stock futures",
    "FC": "futures cash index",
    "FP": "futures physical index",
    "TU": "treasury underlying",
    "TL": "treasury long term",
    "ALL": "include all product types",
}


def download_field_codes() -> str:
    """Return semicolon-delimited OCC download field codes."""
    return ";".join(OCC_DOWNLOAD_FIELDS)


def download_field_descriptions() -> list[str]:
    """Return OCC download field descriptions in request order."""
    return list(OCC_DOWNLOAD_FIELDS.values())
