""" Test WSGI adapter compliance """

from __future__ import annotations

from wsgiref.validate import validator

import pytest

from pyserve.config import ServerConfig
from pyserve.http.request_parser import parse_request_bytes
from pyserve.server import WSGIServer
from pyserve.wsgi.adapter import run_wsgi_app
from tests.conftest import request, socket_roundtrip, wait_for_thread


def test_wsgi_adapter_passes_wsgiref_validate():
    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"validated"]

    response = run_wsgi_app(validator(app), parse_request_bytes(request()), ServerConfig())

    assert response.status_code == 200
    assert response.body == b"validated"


@pytest.mark.parametrize("model", ["serial", "threaded", "async"])
def test_wsgiref_validate_app_through_socket_roundtrip(model: str):
    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"validated"]

    kwargs: dict[str, object] = {"port": 0, "model": model, "keep_alive_timeout": 0.2}
    if model == "threaded":
        kwargs["threads"] = 2
    server = WSGIServer(validator(app), **kwargs)
    thread = server.start_in_thread()
    try:
        status, _, body = socket_roundtrip(
            server.port,
            request(target="/validated", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert body == b"validated"
