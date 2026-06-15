""" Test server """

from __future__ import annotations

from threading import Event

import pytest

from pyserve.config import ServerConfig
from pyserve.server import WSGIServer


def test_wsgi_server_accepts_config_overrides(simple_app):
    server = WSGIServer(simple_app, access_log=True, debug_errors=True)

    assert server.config.access_log is True
    assert server.config.debug_errors is True


def test_wsgi_server_rejects_unknown_override(simple_app):
    with pytest.raises(TypeError, match="unknown server option"):
        WSGIServer(simple_app, not_a_field=True)  # type: ignore[call-arg]


def test_wsgi_server_host_and_port_reflect_bound_values(simple_app):
    server = WSGIServer(simple_app, port=0)
    thread = server.start_in_thread()
    try:
        assert server.host == "127.0.0.1"
        assert server.port > 0
        assert server.config.bound_port == server.port
    finally:
        server.stop()
        server.join()
        thread.join(timeout=3)


def test_serve_forever_is_alias_for_run(simple_app):
    assert WSGIServer.serve_forever is WSGIServer.run


def test_join_waits_for_background_thread(simple_app):
    server = WSGIServer(simple_app, port=0)
    thread = server.start_in_thread()
    server.stop()
    server.join(timeout=3)
    thread.join(timeout=3)
    assert not thread.is_alive()


def test_join_noop_when_thread_never_started(simple_app):
    server = WSGIServer(simple_app, port=0)
    server.join(timeout=0.1)


def test_start_in_thread_raises_when_already_running(simple_app):
    server = WSGIServer(simple_app, port=0)
    thread = server.start_in_thread()
    try:
        with pytest.raises(RuntimeError, match="already running"):
            server.start_in_thread()
    finally:
        server.stop()
        server.join()
        thread.join(timeout=3)


def test_start_in_thread_raises_on_startup_timeout(simple_app, monkeypatch):
    server = WSGIServer(simple_app, port=0)

    def never_ready(self, timeout=None):
        return False

    monkeypatch.setattr(Event, "wait", never_ready)

    with pytest.raises(RuntimeError, match="did not start before timeout"):
        server.start_in_thread(timeout=0.01)


def test_start_in_thread_reraises_bind_failure(simple_app, monkeypatch):
    server = WSGIServer(simple_app, host="127.0.0.1", port=1)

    def fail_serve(self) -> None:
        self._startup_error = OSError("bind failed")
        self._ready_event.set()

    monkeypatch.setattr(WSGIServer, "_serve", fail_serve)

    with pytest.raises(OSError, match="bind failed"):
        server.start_in_thread(timeout=1.0)


def test_wsgi_server_with_explicit_config_object(simple_app):
    config = ServerConfig(model="serial", port=0)
    server = WSGIServer(simple_app, config=config)

    assert server.config is config


def test_serve_raises_when_model_mapping_disappears(simple_app, monkeypatch):
    from pyserve import server as server_module

    server = WSGIServer(simple_app, model="serial")
    monkeypatch.delitem(server_module.SERVER_MODELS, "serial")

    with pytest.raises(ValueError, match="unknown concurrency model"):
        server._serve()

