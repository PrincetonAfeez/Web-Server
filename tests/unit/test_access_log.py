""" Test access log """

from __future__ import annotations

import logging

import pytest

from pyserve.config import ServerConfig
from pyserve.http.headers import CaseInsensitiveHeaders
from pyserve.models import Request
from pyserve.observability.access_log import log_access, log_access_error


def _request() -> Request:
    return Request(
        method="GET",
        raw_target="/path",
        raw_path="/path",
        path="/path",
        query_string="",
        http_version="HTTP/1.1",
        headers=CaseInsensitiveHeaders([("Host", "localhost")]),
        remote_addr="127.0.0.1",
    )


def test_log_access_noop_when_disabled(caplog):
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        log_access(ServerConfig(access_log=False), _request(), 200, 10, 0.123)

    assert caplog.records == []


def test_log_access_emits_default_format_with_elapsed(caplog):
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        log_access(ServerConfig(access_log=True), _request(), 201, 42, 0.5)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert '127.0.0.1 - "GET /path HTTP/1.1" 201 42' in message
    assert message.endswith("0.5000s")


def test_log_access_error_uses_dash_for_missing_method(caplog):
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        log_access_error(
            ServerConfig(access_log=True),
            remote_addr="10.0.0.2",
            method=None,
            raw_target="/bad",
            http_version="HTTP/1.1",
            status_code=400,
            response_size=11,
            elapsed=0.01,
        )

    assert '- "GET /bad HTTP/1.1"' not in caplog.records[0].getMessage()
    assert '- "- /bad HTTP/1.1" 400 11' in caplog.records[0].getMessage()


def test_log_access_error_noop_when_disabled(caplog):
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        log_access_error(
            ServerConfig(access_log=False),
            remote_addr="127.0.0.1",
            method="GET",
            raw_target="/",
            http_version="HTTP/1.1",
            status_code=408,
            response_size=0,
            elapsed=0.0,
        )

    assert caplog.records == []
