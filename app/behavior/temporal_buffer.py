"""
Guardian Drive AI - Temporal Buffer
Rolling time-window storage for per-frame feature signals.
Uses monotonic timestamps — not frame counts.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Tuple

from app.models import FaceFeatures
from app.utils.time_utils import monotonic


class TemporalBuffer:
    """
    Keeps a sliding window of (timestamp, value) pairs older entries
    are pruned automatically when window_s seconds have elapsed.
    """

    def __init__(self, window_s: float = 60.0) -> None:
        self._window = window_s
        self._data: Deque[Tuple[float, float]] = deque()

    def push(self, value: float, ts: float | None = None) -> None:
        now = ts if ts is not None else monotonic()
        self._data.append((now, value))
        self._prune(now)

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._data and self._data[0][0] < cutoff:
            self._data.popleft()

    def values(self) -> list[float]:
        return [v for _, v in self._data]

    def sum(self) -> float:
        return sum(v for _, v in self._data)

    def count_above(self, threshold: float) -> int:
        return sum(1 for _, v in self._data if v > threshold)

    def count_nonzero(self) -> int:
        return sum(1 for _, v in self._data if v != 0.0)

    def latest(self) -> float | None:
        return self._data[-1][1] if self._data else None

    def oldest_ts(self) -> float | None:
        return self._data[0][0] if self._data else None

    def __len__(self) -> int:
        return len(self._data)

    def clear(self) -> None:
        self._data.clear()


class YawnEventBuffer:
    """Tracks discrete yawn event timestamps."""

    def __init__(self, window_s: float = 60.0) -> None:
        self._window = window_s
        self._events: Deque[float] = deque()

    def record_yawn(self, ts: float | None = None) -> None:
        now = ts if ts is not None else monotonic()
        self._events.append(now)
        self._prune(now)

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0] < cutoff:
            self._events.popleft()

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()


class LookAwayBuffer:
    """Tracks discrete look-away events."""

    def __init__(self, window_s: float = 30.0) -> None:
        self._window = window_s
        self._events: Deque[float] = deque()

    def record_event(self, ts: float | None = None) -> None:
        now = ts if ts is not None else monotonic()
        self._events.append(now)
        self._prune(now)

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0] < cutoff:
            self._events.popleft()

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()
