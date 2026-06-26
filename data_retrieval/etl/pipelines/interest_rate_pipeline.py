"""Pipeline for loading Treasury interest rates."""

from etl.transformers.interest_rate_transformer import InterestRateTransformer


class InterestRatePipeline:
    """Load latest Treasury interest rates.

    :param client: Market data client with ``get_interest_rates()``.
    :param database: Shared database helper.
    """

    def __init__(self, client, database):
        """Initialize the pipeline."""
        self.client = client
        self.database = database

    def run(self):
        """Fetch, transform, and insert latest interest-rate rows."""
        data = self.client.get_interest_rates()
        rows = InterestRateTransformer.transform(data)
        self.database.insert_many_ignore_duplicates(rows)
