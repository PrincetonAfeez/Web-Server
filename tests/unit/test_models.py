""" Test models """

from __future__ import annotations

from pyserve.http.headers import CaseInsensitiveHeaders
from pyserve.models import Request


def _sample_request(**overrides) -> Request:
    defaults = {
        "method": "GET",
        "raw_target": "/",
        "raw_path": "/",
        "path": "/",
        "query_string": "",
        "http_version": "HTTP/1.1",
        "headers": CaseInsensitiveHeaders([("Host", "localhost")]),
    }
    defaults.update(overrides)
    return Request(**defaults)


def test_request_default_field_values():
    request = _sample_request()

    assert request.body == b""
    assert request.remote_addr == ""
    assert request.remote_port == 0


def test_server_protocol_aliases_http_version():
    request = _sample_request(http_version="HTTP/1.1")

    assert request.server_protocol == "HTTP/1.1"


def test_request_accepts_remote_metadata():
    request = _sample_request(remote_addr="10.0.0.1", remote_port=54321)

    assert request.remote_addr == "10.0.0.1"
    assert request.remote_port == 54321
