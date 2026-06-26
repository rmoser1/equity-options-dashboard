"""Tests for :mod:`etl.pipelines.base_pipeline`."""

from etl.pipelines.base_pipeline import BasePipeline


class RandomStub:
    """Deterministic random module stub for batch sizing and sleep delays."""

    def __init__(self):
        self.randrange_values = [2, 2]

    def randrange(self, start, stop):
        """Return the next configured batch size."""
        return self.randrange_values.pop(0)

    def random(self):
        """Return a deterministic sleep multiplier."""
        return 0


class RecordingPipeline(BasePipeline):
    """Record processed symbols and optionally fail one symbol."""

    def __init__(self, *args, fail_symbol=None, **kwargs):
        """Initialize the recording pipeline."""
        super().__init__(*args, **kwargs)
        self.fail_symbol = fail_symbol
        self.processed = []

    def process_symbol(self, symbol):
        """Record one processed symbol."""
        self.processed.append(symbol)
        if symbol == self.fail_symbol:
            raise RuntimeError("boom")


def test_run_processes_symbols_in_randomized_batches():
    """Verify :meth:`BasePipeline.run` processes every symbol once."""
    sleeps = []
    pipeline = RecordingPipeline(
        database=object(),
        avg_batch_size=2,
        random_module=RandomStub(),
        sleep_func=sleeps.append,
    )

    pipeline.run(["AAPL", "MSFT", "NVDA"])

    assert pipeline.processed == ["AAPL", "MSFT", "NVDA"]
    assert len(sleeps) == 5


def test_run_continues_after_symbol_failure():
    """Verify one symbol failure does not stop later symbols."""
    pipeline = RecordingPipeline(
        database=object(),
        avg_batch_size=2,
        random_module=RandomStub(),
        sleep_func=lambda _: None,
        fail_symbol="MSFT",
    )

    pipeline.run(["AAPL", "MSFT", "NVDA"])

    assert pipeline.processed == ["AAPL", "MSFT", "NVDA"]
