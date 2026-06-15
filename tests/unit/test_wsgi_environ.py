""" Test WSGI environment """

from __future__ import annotations

from pyserve.config import ServerConfig
from pyserve.http.request_parser import parse_request_bytes
from pyserve.wsgi.environ import build_environ
from tests.conftest import request


def test_builds_required_wsgi_environ_variables():
    parsed = parse_request_bytes(
        request(
            "POST",
            "/hello?x=1",
            {"Content-Type": "text/plain", "X-Test-Header": "ok"},
            b"body",
        )
    )
    parsed.remote_addr = "127.0.0.1"
    parsed.remote_port = 5555

    environ = build_environ(parsed, ServerConfig(port=8000, wsgi_multithread=True))

    assert environ["REQUEST_METHOD"] == "POST"
    assert environ["SCRIPT_NAME"] == ""
    assert environ["PATH_INFO"] == "/hello"
    assert environ["QUERY_STRING"] == "x=1"
    assert environ["CONTENT_TYPE"] == "text/plain"
    assert environ["CONTENT_LENGTH"] == "4"
    assert environ["SERVER_NAME"] == "localhost"
    assert environ["SERVER_PORT"] == "8000"
    assert environ["SERVER_PROTOCOL"] == "HTTP/1.1"
    assert environ["REMOTE_ADDR"] == "127.0.0.1"
    assert environ["REMOTE_PORT"] == "5555"
    assert environ["wsgi.version"] == (1, 0)
    assert environ["wsgi.url_scheme"] == "http"
    assert environ["wsgi.input"].read() == b"body"
    assert environ["wsgi.multithread"] is True
    assert environ["wsgi.multiprocess"] is False
    assert environ["wsgi.run_once"] is False
    assert environ["HTTP_X_TEST_HEADER"] == "ok"


def test_host_with_non_numeric_port_does_not_leak_into_server_name():
    parsed = parse_request_bytes(request(headers={"Host": "example.com:notaport"}))

    environ = build_environ(parsed, ServerConfig(port=8000))

    assert environ["SERVER_NAME"] == "example.com"
    assert environ["SERVER_PORT"] == "8000"


def test_non_ascii_host_port_does_not_crash():
    parsed = parse_request_bytes(request(headers={"Host": "example.com:\xb2"}))

    environ = build_environ(parsed, ServerConfig(port=8000))

    assert environ["SERVER_NAME"] == "example.com"
    assert environ["SERVER_PORT"] == "8000"


def test_underscore_headers_are_dropped_but_dashed_headers_pass():
    underscored = parse_request_bytes(request(headers={"X_Forwarded_For": "evil"}))
    dashed = parse_request_bytes(request(headers={"X-Real-IP": "1.2.3.4"}))

    assert "HTTP_X_FORWARDED_FOR" not in build_environ(underscored, ServerConfig())
    assert build_environ(dashed, ServerConfig())["HTTP_X_REAL_IP"] == "1.2.3.4"


def test_duplicate_headers_fold_with_header_specific_separator():
    cookies = parse_request_bytes(
        b"GET / HTTP/1.1\r\nHost: localhost\r\nCookie: a=1\r\nCookie: b=2\r\n\r\n"
    )
    multi = parse_request_bytes(
        b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Multi: a\r\nX-Multi: b\r\n\r\n"
    )

    assert build_environ(cookies, ServerConfig())["HTTP_COOKIE"] == "a=1; b=2"
    assert build_environ(multi, ServerConfig())["HTTP_X_MULTI"] == "a,b"


def test_ipv6_host_header_parses_bracketed_address_and_port():
    parsed = parse_request_bytes(request(headers={"Host": "[::1]:9000"}))

    environ = build_environ(parsed, ServerConfig(port=8000))

    assert environ["SERVER_NAME"] == "::1"
    assert environ["SERVER_PORT"] == "9000"


def test_ipv6_host_without_port_falls_back_to_bound_port():
    from pyserve.wsgi.environ import server_from_host_header

    parsed = parse_request_bytes(request(headers={"Host": "[::1]"}))

    name, port = server_from_host_header(parsed, ServerConfig(port=8123))

    assert name == "::1"
    assert port == 8123


def test_bracketed_ipv6_with_invalid_port_falls_back_to_bound_port():
    from pyserve.wsgi.environ import server_from_host_header

    parsed = parse_request_bytes(request(headers={"Host": "[::1]:notaport"}))

    name, port = server_from_host_header(parsed, ServerConfig(port=8123))

    assert name == "::1"
    assert port == 8123


