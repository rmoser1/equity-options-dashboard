"""Process memory diagnostics for dashboard data logging."""

import os
import resource
import sys


def memory_usage() -> str:
    """Return current and peak resident memory as a compact log string."""
    current = _current_rss_mb()
    peak = _peak_rss_mb()
    return f"rss={current:.1f}MB peak_rss={peak:.1f}MB"


def _current_rss_mb() -> float:
    """Return current resident memory where the platform exposes it."""
    try:
        with open("/proc/self/status", encoding="utf-8") as status_file:
            for line in status_file:
                if line.startswith("VmRSS:"):
                    return float(line.split()[1]) / 1024
    except FileNotFoundError:
        pass
    return _peak_rss_mb()


def _peak_rss_mb() -> float:
    """Return maximum resident memory for the current process."""
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return usage / 1024 / 1024
    return usage / 1024
