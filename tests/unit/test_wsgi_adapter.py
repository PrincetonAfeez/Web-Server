""" Test WSGI adapter """

from __future__ import annotations

import pytest

from pyserve.config import ServerConfig
from pyserve.http.request_parser import parse_request_bytes
from pyserve.wsgi.adapter import run_wsgi_app
from tests.conftest import request


def parsed_request():
    return parse_request_bytes(request())


def test_start_response_write_callable_is_supported():
    def app(environ, start_response):
        write = start_response("200 OK", [("Content-Type", "text/plain")])
        write(b"a")
        return [b"b"]

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 200
    assert response.body == b"ab"


def test_write_callable_during_iteration_is_not_lost():
    def app(environ, start_response):
        write = start_response("200 OK", [("Content-Type", "text/plain")])

        def stream():
            write(b"a")
            yield b"b"
            write(b"c")
            yield b"d"

        return stream()

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    # write() output precedes the iterable's output, and none of it is dropped.
    assert response.body == b"acbd"


def test_wsgi_iterable_close_is_called():
    closed = {"value": False}

    class Body:
        def __iter__(self):
            yield b"ok"

        def close(self):
            closed["value"] = True

    def app(environ, start_response):
        start_response("200 OK", [])
        return Body()

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.body == b"ok"
    assert closed["value"] is True


def test_wsgi_app_exception_becomes_500():
    def app(environ, start_response):
        raise RuntimeError("boom")

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 500


def test_wsgi_non_bytes_chunk_becomes_500():
    def app(environ, start_response):
        start_response("200 OK", [])
        return ["not bytes"]

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 500


def test_start_response_exc_info_reraises_after_prior_call():
    import sys

    from pyserve.wsgi.adapter import StartResponse

    start_response = StartResponse()
    start_response("200 OK", [])
    with pytest.raises(ValueError, match="boom"):
        try:
            raise ValueError("boom")
        except ValueError:
            start_response("500 Internal Server Error", [], sys.exc_info())


def test_start_response_called_twice_without_exc_info_becomes_500():
    def app(environ, start_response):
        start_response("200 OK", [])
        start_response("200 OK", [])
        return [b"ok"]

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 500


def test_missing_start_response_becomes_500():
    def app(environ, start_response):
        return [b"ok"]

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 500


def test_non_string_header_pair_becomes_500():
    def app(environ, start_response):
        start_response("200 OK", [(b"X-Bad", "v")])  # type: ignore[list-item]
        return [b"ok"]

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 500


def test_header_with_cr_or_lf_becomes_500():
    def app(environ, start_response):
        start_response("200 OK", [("X-Bad", "a\r\ninjected")])
        return [b"ok"]

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 500


def test_write_non_bytes_becomes_500():
    def app(environ, start_response):
        write = start_response("200 OK", [])
        write("text")  # type: ignore[arg-type]
        return []

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 500


def test_invalid_status_string_becomes_500():
    def app(environ, start_response):
        start_response("not-a-status", [])
        return [b"ok"]

    response = run_wsgi_app(app, parsed_request(), ServerConfig())

    assert response.status_code == 500

