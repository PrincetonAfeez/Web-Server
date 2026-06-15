""" Test listener """

from __future__ import annotations

import pytest

from pyserve.config import ServerConfig
from pyserve.transport.listener import create_listening_socket


def test_second_bind_to_same_port_is_refused():
    # On Windows this requires SO_EXCLUSIVEADDRUSE: plain SO_REUSEADDR would let a
    # second listener bind the same (host, port) and silently steal connections.
    first = create_listening_socket(ServerConfig(host="127.0.0.1", port=0))
    try:
        taken_port = first.getsockname()[1]
        with pytest.raises(OSError):
            second = create_listening_socket(ServerConfig(host="127.0.0.1", port=taken_port))
            second.close()
    finally:
        first.close()


def test_bound_address_is_recorded_on_config():
    config = ServerConfig(host="127.0.0.1", port=0)
    listener = create_listening_socket(config)
    try:
        assert config.bound_host == "127.0.0.1"
        assert config.bound_port == listener.getsockname()[1]
        assert config.bound_port != 0
    finally:
        listener.close()


def test_listener_uses_reuseaddr_on_non_windows_platform(monkeypatch):
    import sys

    import pyserve.transport.listener as listener_module

    monkeypatch.setattr(sys, "platform", "linux")
    setsockopt_calls: list[tuple[int, int, int]] = []

    original_socket = listener_module.socket.socket

    class RecordingSocket(original_socket):
        def setsockopt(self, level, option, value):
            setsockopt_calls.append((level, option, value))
            return super().setsockopt(level, option, value)

    monkeypatch.setattr(listener_module.socket, "socket", RecordingSocket)

    listener = create_listening_socket(ServerConfig(host="127.0.0.1", port=0))
    try:
        assert (listener_module.socket.SOL_SOCKET, listener_module.socket.SO_REUSEADDR, 1) in setsockopt_calls
    finally:
        listener.close()

