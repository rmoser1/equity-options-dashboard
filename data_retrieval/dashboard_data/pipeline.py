"""Dashboard pipeline orchestration.

This module provides :class:`DashboardPipeline`, which loads raw dashboard
data, transforms it, and writes the transformed outputs.
"""


class DashboardPipeline:
    """Coordinate the dashboard repository, transformer, and writer."""

    def __init__(self, repository, transformer, writer):
        """Initialize the dashboard pipeline.

        :param repository: Object that provides ``load_all()``.
        :param transformer: Object that provides ``transform(data)``.
        :param writer: Object that provides ``write(data)``.
        """
        self.repository = repository
        self.transformer = transformer
        self.writer = writer

    def run(self):
        """Run the dashboard pipeline."""
        data = self.repository.load_all()
        transformed = self.transformer.transform(data)
        self.writer.write(transformed)
