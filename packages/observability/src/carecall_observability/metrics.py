import threading
from collections import defaultdict
from typing import Dict

"""Minimal in-process, Prometheus-text-exposable metrics - no external
metrics backend or OpenTelemetry SDK wired up (documented as a natural next
step in docs/architecture/overview.md rather than built as a placeholder).
Good enough for a single-process demo/production-like deployment; a real
multi-instance deployment would swap this for a proper client library
without changing any call site (increment/observe)."""

_lock = threading.Lock()
_counters: Dict[str, float] = defaultdict(float)
_histogram_sums: Dict[str, float] = defaultdict(float)
_histogram_counts: Dict[str, int] = defaultdict(int)


def _key(name: str, labels: dict) -> str:
    if not labels:
        return name
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{name}{{{label_str}}}"


def increment(name: str, value: float = 1.0, **labels) -> None:
    with _lock:
        _counters[_key(name, labels)] += value


def observe(name: str, value: float, **labels) -> None:
    key = _key(name, labels)
    with _lock:
        _histogram_sums[key] += value
        _histogram_counts[key] += 1


def render_prometheus() -> str:
    lines = []
    with _lock:
        for key, value in sorted(_counters.items()):
            lines.append(f"{key} {value}")
        for key in sorted(_histogram_sums.keys()):
            count = _histogram_counts[key]
            total = _histogram_sums[key]
            base, _, labels = key.partition("{")
            suffix = "{" + labels if labels else ""
            lines.append(f"{base}_count{suffix} {count}")
            lines.append(f"{base}_sum{suffix} {total}")
    return "\n".join(lines) + "\n"


def reset() -> None:
    """Test-only: clears all recorded metrics."""
    with _lock:
        _counters.clear()
        _histogram_sums.clear()
        _histogram_counts.clear()
