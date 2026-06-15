""" Test concurrency """

from __future__ import annotations

import asyncio
import socket
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from pyserve.concurrency.async_model import AsyncioServer
from pyserve.concurrency.base import BaseServer
from pyserve.config import ServerConfig
from pyserve.exceptions import BadRequest, HeaderTooLarge, RequestTimeout
from pyserve.http.request_parser import HEADER_END
from pyserve.observability.stats import ServerStats
from tests.conftest import request


def test_base_server_run_raises_not_implemented():
    server = BaseServer(lambda e, s: None, ServerConfig(), Event(), Event())

    with pytest.raises(NotImplementedError):
        server.run()


def test_async_read_request_header_limit_overrun_becomes_431(simple_app):
    config = ServerConfig(max_header_size=20, read_timeout=2.0)
    server = AsyncioServer(simple_app, config, Event(), Event())

    oversized = b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Big: " + b"a" * 100 + b"\r\n\r\n"

    class DummyWriter:
        def write(self, data: bytes) -> None:
            pass

    async def run() -> int | None:
        reader = asyncio.StreamReader(limit=config.max_header_size + len(HEADER_END))
        reader.feed_data(oversized)
        try:
            await server._read_request(reader, DummyWriter(), 0)  # type: ignore[arg-type]
        except HeaderTooLarge as exc:
            return exc.status_code
        return None

    assert asyncio.run(run()) == 431


def test_async_body_read_timeout_returns_408(simple_app):
    config = ServerConfig(read_timeout=0.05, write_timeout=0.2)
    server = AsyncioServer(simple_app, config, Event(), Event())

    head = request("POST", "/", {"Content-Length": "5", "Connection": "close"}, b"")

    class DummyWriter:
        def write(self, data: bytes) -> None:
            pass

    async def run() -> str | None:
        reader = asyncio.StreamReader()
        reader.feed_data(head)
        try:
            await server._read_request(reader, DummyWriter(), 0)  # type: ignore[arg-type]
        except RequestTimeout as exc:
            return exc.public_message
        return None

    assert asyncio.run(run()) == "Request Timeout"


def test_async_drain_with_timeout_success(simple_app):
    config = ServerConfig(write_timeout=1.0)
    server = AsyncioServer(simple_app, config, Event(), Event())

    async def run() -> None:
        reader = asyncio.StreamReader()
        loop = asyncio.get_running_loop()
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        rsock, wsock = socket.socketpair()
        await loop.connect_accepted_socket(lambda: reader_protocol, rsock)
        writer = asyncio.StreamWriter(
            reader_protocol._transport,  # type: ignore[attr-defined]
            reader_protocol,
            reader,
            loop,
        )
        writer.write(b"ping")
        await server._drain_with_timeout(writer)
        writer.close()
        await writer.wait_closed()
        rsock.close()

    asyncio.run(run())


def test_async_clean_eof_on_first_byte_exits_without_error(simple_app):
    config = ServerConfig()
    stats = ServerStats()
    server = AsyncioServer(simple_app, config, Event(), Event(), stats)
    executor = ThreadPoolExecutor(max_workers=1)
    server._executor = executor

    async def run() -> dict[str, object]:
        reader = asyncio.StreamReader()
        reader.feed_eof()
        loop = asyncio.get_running_loop()
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        rsock, wsock = socket.socketpair()
        await loop.connect_accepted_socket(lambda: reader_protocol, rsock)
        writer = asyncio.StreamWriter(
            reader_protocol._transport,  # type: ignore[attr-defined]
            reader_protocol,
            reader,
            loop,
        )
        await server._handle_client(reader, writer)
        return stats.snapshot()

    try:
        snapshot = asyncio.run(run())
    finally:
        executor.shutdown(wait=True)

    assert snapshot["request_count"] == 0


def test_async_truncated_request_after_partial_headers_returns_400(simple_app):
    config = ServerConfig(read_timeout=1.0)
    server = AsyncioServer(simple_app, config, Event(), Event())

    async def run() -> int | None:
        reader = asyncio.StreamReader()
        reader.feed_data(b"GET / HTTP/1.1\r\nHost: local")
        reader.feed_eof()

        class DummyWriter:
            def write(self, data: bytes) -> None:
                pass

        try:
            await server._read_request(reader, DummyWriter(), 0)  # type: ignore[arg-type]
        except BadRequest:
            return 400
        return None

    assert asyncio.run(run()) == 400


def test_async_expect_continue_sends_interim_response(simple_app):
    config = ServerConfig(read_timeout=2.0, write_timeout=2.0)
    server = AsyncioServer(simple_app, config, Event(), Event())

    head = request(
        "POST",
        "/",
        {"Content-Length": "4", "Expect": "100-continue", "Connection": "close"},
        b"",
    )

    class CapturingWriter:
        def __init__(self) -> None:
            self.chunks: list[bytes] = []

        def write(self, data: bytes) -> None:
            self.chunks.append(data)

        async def drain(self) -> None:
            return None

    async def run() -> list[bytes]:
        reader = asyncio.StreamReader()
        reader.feed_data(head + b"body")
        writer = CapturingWriter()
        await server._read_request(reader, writer, 0)  # type: ignore[arg-type]
        return writer.chunks

    chunks = asyncio.run(run())
    assert any(chunk.startswith(b"HTTP/1.1 100 Continue") for chunk in chunks)

