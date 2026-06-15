""" Test Django WSGI app compliance """

from __future__ import annotations

import pytest

from pyserve.config import ServerConfig, load_wsgi_app
from pyserve.http.request_parser import parse_request_bytes
from pyserve.server import WSGIServer
from pyserve.wsgi.adapter import run_wsgi_app
from tests.conftest import request, socket_roundtrip, wait_for_thread


def test_demo_django_wsgi_app_runs_unmodified():
    pytest.importorskip("django")
    app = load_wsgi_app("demo.django_demo.config.wsgi:application")

    response = run_wsgi_app(app, parse_request_bytes(request()), ServerConfig())

    assert response.status_code == 200
    assert b"Hello from Django through pyserve" in response.body


@pytest.mark.parametrize("model", ["serial", "threaded", "async"])
def test_demo_django_wsgi_app_serves_over_socket_roundtrip(model: str):
    pytest.importorskip("django")
    app = load_wsgi_app("demo.django_demo.config.wsgi:application")
    kwargs: dict[str, object] = {"port": 0, "model": model, "keep_alive_timeout": 0.2}
    if model == "threaded":
        kwargs["threads"] = 2
    server = WSGIServer(app, **kwargs)
    thread = server.start_in_thread()
    try:
        status, _, body = socket_roundtrip(
            server.port,
            request(target="/", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert b"Hello from Django through pyserve" in body
