""" Test stats """

from __future__ import annotations

import threading

import pytest

from pyserve.observability.stats import ServerStats


def test_average_request_time_zero_when_no_requests():
    stats = ServerStats()

    assert stats.average_request_time == 0.0


def test_average_request_time_computes_mean():
    stats = ServerStats()
    stats.record(200, 0.1)
    stats.record(404, 0.3)

    assert stats.average_request_time == pytest.approx(0.2)


def test_snapshot_matches_average_request_time():
    stats = ServerStats()
    stats.record(200, 0.5)

    snapshot = stats.snapshot()

    assert snapshot["average_request_time"] == stats.average_request_time
    assert snapshot["request_count"] == 1
    assert snapshot["status_codes"] == {200: 1}


def test_connection_counters_track_active_clients():
    stats = ServerStats()
    stats.connection_opened()
    stats.connection_opened()
    stats.connection_closed()

    assert stats.active_connections == 1
    assert stats.snapshot()["active_connections"] == 1


def test_record_is_thread_safe_under_contention():
    stats = ServerStats()

    def worker() -> None:
        for _ in range(100):
            stats.record(200, 0.001)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert stats.request_count == 400
