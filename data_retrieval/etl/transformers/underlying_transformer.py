"""Transform OCC underlying download files into SQLModel rows."""

from io import BytesIO

import pandas as pd

from schemas.underlying import Underlying


class UnderlyingTransformer:
    """Convert OCC underlying text downloads to :class:`Underlying` rows."""

    @staticmethod
    def transform(
        file_content: bytes,
        descriptions: list[str],
    ) -> list[Underlying]:
        """Transform an OCC underlying download into filtered underlying rows.

        :param file_content: Raw OCC underlying download bytes.
        :param descriptions: Column names matching the requested OCC fields.
        :returns: Unique equity underlyings as :class:`Underlying` rows.
        """
        df = pd.read_table(BytesIO(file_content), header=None, index_col=None)
        if df.shape[1] == len(descriptions) + 1 and df.iloc[:, -1].isna().all():
            df = df.iloc[:, :-1]
        df.columns = descriptions
        df = df[df["Product Type"] == "EU"]
        df = df.rename(
            columns={
                "Underlying Symbol": "symbol",
                "Symbol Name": "name",
            }
        )

        df = df[["symbol", "name"]]

        df["symbol"] = df["symbol"].str.strip()
        df["name"] = df["name"].str.strip().str.title()
        df = df.drop_duplicates("symbol")

        return [Underlying(symbol=row.symbol, name=row.name) for row in df.itertuples()]
