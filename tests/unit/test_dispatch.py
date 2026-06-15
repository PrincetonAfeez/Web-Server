""" Test dispatch """

from __future__ import annotations

from pyserve.config import ServerConfig
from pyserve.dispatch import method_not_allowed_response, should_keep_alive
from pyserve.http.headers import CaseInsensitiveHeaders
from pyserve.models import Request


def _request(**kwargs: object) -> Request:
    defaults = {
        "method": "GET",
        "raw_target": "/",
        "raw_path": "/",
        "path": "/",
        "query_string": "",
        "http_version": "HTTP/1.1",
        "headers": CaseInsensitiveHeaders([("Host", "localhost")]),
        "body": b"",
    }
    defaults.update(kwargs)
    return Request(**defaults)  # type: ignore[arg-type]


def test_method_not_allowed_includes_allow_header():
    response = method_not_allowed_response()

    assert response.status_code == 405
    assert ("Allow", "GET, HEAD, POST") in response.headers


def test_should_keep_alive_honors_connection_close():
    request = _request(headers=CaseInsensitiveHeaders([("Host", "localhost"), ("Connection", "close")]))

    assert should_keep_alive(request, 1, ServerConfig()) is False


def test_should_keep_alive_requires_http_11():
    request = _request(http_version="HTTP/1.0")

    assert should_keep_alive(request, 1, ServerConfig()) is False


def test_should_keep_alive_disabled_when_timeout_is_zero():
    request = _request()

    assert should_keep_alive(request, 1, ServerConfig(keep_alive_timeout=0.0)) is False


def test_should_keep_alive_stops_at_request_limit():
    request = _request()
    config = ServerConfig(max_keep_alive_requests=2)

    assert should_keep_alive(request, 1, config) is True
    assert should_keep_alive(request, 2, config) is False


def test_should_keep_alive_defaults_to_true_for_http_11():
    request = _request()

    assert should_keep_alive(request, 1, ServerConfig()) is True

