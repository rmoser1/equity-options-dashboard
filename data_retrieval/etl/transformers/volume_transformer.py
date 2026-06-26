"""Transform OCC volume CSV text into aggregate volume values."""

from io import StringIO

import pandas as pd


class VolumeTransformer:
    """Extract total option volume from OCC volume CSV responses."""

    @staticmethod
    def extract_volume(csv_text: str) -> int:
        """Return summed volume from OCC CSV text.

        :param csv_text: OCC volume CSV response text.
        :returns: Sum of the ``quantity`` column, or ``0`` when parsing fails.
        """
        try:
            df = pd.read_csv(StringIO(csv_text), index_col=False)
            return int(df["quantity"].sum())
        except Exception:
            return 0
