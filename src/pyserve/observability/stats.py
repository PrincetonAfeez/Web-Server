""" Stats module for the pyserve project """

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ServerStats:
    request_count: int = 0
    active_connections: int = 0
    status_codes: Counter[int] = field(default_factory=Counter)
    total_request_time: float = 0.0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, status_code: int, elapsed: float) -> None:
        with self._lock:
            self.request_count += 1
            self.status_codes[status_code] += 1
            self.total_request_time += elapsed

    def connection_opened(self) -> None:
        with self._lock:
            self.active_connections += 1

    def connection_closed(self) -> None:
        with self._lock:
            self.active_connections -= 1

    @property
    def average_request_time(self) -> float:
        with self._lock:
            if self.request_count == 0:
                return 0.0
            return self.total_request_time / self.request_count

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            average = self.total_request_time / self.request_count if self.request_count else 0.0
            return {
                "request_count": self.request_count,
                "active_connections": self.active_connections,
                "status_codes": dict(self.status_codes),
                "average_request_time": average,
            }
