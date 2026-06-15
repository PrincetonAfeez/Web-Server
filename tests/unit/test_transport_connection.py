""" Test transport connection """

from __future__ import annotations

import socket
import threading

import pytest

from pyserve.config import ServerConfig
from pyserve.transport import connection as connection_module
from pyserve.transport.connection import ConnectionHandler, close_quietly, send_all
from tests.conftest import recv_http_response, request


class PartialSender:
    def __init__(self, max_send: int) -> None:
        self.max_send = max_send
        self.sent = bytearray()

    def send(self, data) -> int:
        chunk = bytes(data[: self.max_send])
        self.sent.extend(chunk)
        return len(chunk)


def test_send_all_handles_partial_sends():
    sender = PartialSender(max_send=2)

    send_all(sender, b"abcdef")  # type: ignore[arg-type]

    assert bytes(sender.sent) == b"abcdef"


def test_write_timeout_on_success_path_records_408(monkeypatch, simple_app):
    client, server = socket.socketpair()
    original_send_all = connection_module.send_all
    attempts = {"count": 0}

    def flaky_send_all(sock, data: bytes) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("timed out")
        original_send_all(sock, data)

    monkeypatch.setattr(connection_module, "send_all", flaky_send_all)

    handler = ConnectionHandler(
        simple_app,
        ServerConfig(write_timeout=0.1, read_timeout=2.0),
    )
    thread = threading.Thread(target=handler.handle, args=(server, ("127.0.0.1", 4444)))
    thread.start()
    client.sendall(request(target="/", headers={"Connection": "close"}))
    status, _, _ = recv_http_response(client)
    thread.join(timeout=3)

    assert status.startswith("HTTP/1.1 408")
    assert handler.stats.snapshot()["status_codes"].get(408, 0) >= 1


def test_send_all_raises_when_socket_returns_zero():
    class BrokenSocket:
        def send(self, data: bytes) -> int:
            return 0

    with pytest.raises(ConnectionError, match="broken"):
        send_all(BrokenSocket(), b"data")  # type: ignore[arg-type]


def test_close_quietly_swallows_os_error(monkeypatch):
    class FailingSocket:
        def close(self) -> None:
            raise OSError("close failed")

    close_quietly(FailingSocket())  # type: ignore[arg-type]


def test_connection_handler_swallows_oserror_on_broken_socket(simple_app, monkeypatch):
    client, server = socket.socketpair()

    class FailingRecvSocket:
        def __init__(self, inner):
            self.inner = inner

        def recv(self, size: int) -> bytes:
            raise OSError("broken pipe")

        def settimeout(self, timeout: float) -> None:
            pass

        def send(self, data: bytes) -> int:
            return self.inner.send(data)

        def close(self) -> None:
            self.inner.close()

    handler = ConnectionHandler(simple_app, ServerConfig(read_timeout=1.0))
    wrapped = FailingRecvSocket(server)
    thread = threading.Thread(target=handler.handle, args=(wrapped, ("127.0.0.1", 1)))
    thread.start()
    client.sendall(request(headers={"Connection": "close"}))
    thread.join(timeout=3)
    client.close()

    assert handler.stats.snapshot()["request_count"] == 0


def test_connection_handler_exits_cleanly_on_eof(simple_app):
    client, server = socket.socketpair()
    handler = ConnectionHandler(simple_app, ServerConfig(read_timeout=1.0))
    thread = threading.Thread(target=handler.handle, args=(server, ("127.0.0.1", 4444)))
    thread.start()
    client.close()
    thread.join(timeout=3)

    assert handler.stats.snapshot()["request_count"] == 0


def test_error_response_write_timeout_is_swallowed(simple_app, monkeypatch):
    client, server = socket.socketpair()
    original_send_all = connection_module.send_all
    calls = {"count": 0}

    def fail_send(sock, data: bytes) -> None:
        calls["count"] += 1
        raise TimeoutError("timed out")

    monkeypatch.setattr(connection_module, "send_all", fail_send)

    handler = ConnectionHandler(simple_app, ServerConfig(write_timeout=0.1))
    thread = threading.Thread(target=handler.handle, args=(server, ("127.0.0.1", 4444)))
    thread.start()
    client.sendall(request(target="/", headers={"Connection": "close"}))
    thread.join(timeout=3)
    client.close()

    assert calls["count"] >= 1


