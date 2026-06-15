""" Test server roundtrip """

from __future__ import annotations

import logging
import socket
import threading
import time

import pytest

from pyserve.server import WSGIServer
from tests.conftest import (
    ipv6_loopback_available,
    recv_http_response,
    request,
    socket_roundtrip,
    socket_roundtrip_host,
    wait_for_thread,
)


def test_serial_server_roundtrip(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, headers, body = socket_roundtrip(
            server.port,
            request(target="/serial?x=1", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert headers["content-length"] == str(len(body))
    assert body == b"GET /serial?x=1"


def test_threaded_server_roundtrip(simple_app):
    server = WSGIServer(simple_app, port=0, model="threaded", threads=2, keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, body = socket_roundtrip(
            server.port,
            request(target="/threaded", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert body == b"GET /threaded?"


def test_async_server_roundtrip(simple_app):
    server = WSGIServer(simple_app, port=0, model="async", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, body = socket_roundtrip(
            server.port,
            request(target="/async", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert body == b"GET /async?"


def test_keep_alive_handles_sequential_requests(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.5)
    thread = server.start_in_thread()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
            client.sendall(request(target="/one", headers={"Connection": "keep-alive"}))
            first_status, first_headers, first_body = recv_http_response(client)

            client.sendall(request(target="/two", headers={"Connection": "close"}))
            second_status, second_headers, second_body = recv_http_response(client)
    finally:
        server.stop()
        wait_for_thread(thread)

    assert first_status == "HTTP/1.1 200 OK"
    assert first_headers["connection"] == "keep-alive"
    assert first_body == b"GET /one?"
    assert second_status == "HTTP/1.1 200 OK"
    assert second_headers["connection"] == "close"
    assert second_body == b"GET /two?"


@pytest.mark.parametrize("model", ["serial", "threaded", "async"])
def test_unsupported_method_returns_405(simple_app, model):
    kwargs: dict[str, object] = {"port": 0, "model": model, "keep_alive_timeout": 0.2}
    if model == "threaded":
        kwargs["threads"] = 2
    server = WSGIServer(simple_app, **kwargs)
    thread = server.start_in_thread()
    try:
        status, headers, _ = socket_roundtrip(
            server.port,
            request(method="PUT", target="/", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 405 Method Not Allowed"
    assert headers["allow"] == "GET, HEAD, POST"


def test_malformed_content_length_returns_400_and_server_survives(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        # 0xB2 passes str.isdigit() but crashes int(); before the fix this killed the
        # serial accept loop, so the follow-up request is what proves the server lived.
        bad = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: \xb2\r\nConnection: close\r\n\r\n"
        bad_status, _, _ = socket_roundtrip(server.port, bad)
        good_status, _, good_body = socket_roundtrip(
            server.port,
            request(target="/after", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert bad_status.startswith("HTTP/1.1 400")
    assert good_status == "HTTP/1.1 200 OK"
    assert good_body == b"GET /after?"


def test_server_stats_count_handled_requests(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        socket_roundtrip(server.port, request(target="/a", headers={"Connection": "close"}))
        socket_roundtrip(server.port, request(target="/b", headers={"Connection": "close"}))
    finally:
        server.stop()
        wait_for_thread(thread)

    snapshot = server.stats.snapshot()
    assert snapshot["request_count"] == 2
    assert snapshot["active_connections"] == 0
    assert snapshot["status_codes"] == {200: 2}


def test_expect_100_continue_sends_interim_response(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
            client.sendall(
                b"POST /e HTTP/1.1\r\nHost: localhost\r\n"
                b"Content-Length: 5\r\nExpect: 100-continue\r\nConnection: close\r\n\r\n"
            )
            interim = client.recv(64)
            assert interim.startswith(b"HTTP/1.1 100 Continue\r\n\r\n")
            client.sendall(b"hello")
            status, _, body = recv_http_response(client)
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert body == b"POST /e?"


def test_failed_head_request_has_no_error_body(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2, max_header_count=2)
    thread = server.start_in_thread()
    try:
        # Host + 3 extra headers exceeds max_header_count=2 -> 431. The method (HEAD) is
        # parsed before the limit trips, so the error response must omit the body.
        payload = (
            b"HEAD / HTTP/1.1\r\nHost: localhost\r\n"
            b"A: 1\r\nB: 2\r\nC: 3\r\nConnection: close\r\n\r\n"
        )
        status, headers, body = socket_roundtrip(server.port, payload, read_body=False)
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status.startswith("HTTP/1.1 431")
    assert int(headers["content-length"]) > 0
    assert body == b""


def test_protocol_errors_are_counted_in_stats(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        socket_roundtrip(server.port, request(target="/ok", headers={"Connection": "close"}))
        bad = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: \xb2\r\nConnection: close\r\n\r\n"
        socket_roundtrip(server.port, bad)
    finally:
        server.stop()
        wait_for_thread(thread)

    snapshot = server.stats.snapshot()
    assert snapshot["request_count"] == 2
    assert snapshot["status_codes"] == {200: 1, 400: 1}


def test_async_model_records_stats(simple_app):
    server = WSGIServer(simple_app, port=0, model="async", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        socket_roundtrip(server.port, request(target="/x", headers={"Connection": "close"}))
    finally:
        server.stop()
        wait_for_thread(thread)

    assert server.stats.snapshot()["request_count"] == 1


def test_async_model_handles_expect_100_continue(simple_app):
    server = WSGIServer(simple_app, port=0, model="async", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
            client.sendall(
                b"POST /e HTTP/1.1\r\nHost: localhost\r\n"
                b"Content-Length: 5\r\nExpect: 100-continue\r\nConnection: close\r\n\r\n"
            )
            interim = client.recv(64)
            assert interim.startswith(b"HTTP/1.1 100 Continue\r\n\r\n")
            client.sendall(b"hello")
            status, _, body = recv_http_response(client)
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert body == b"POST /e?"


def test_async_model_emits_access_log(simple_app, caplog):
    server = WSGIServer(simple_app, port=0, model="async", keep_alive_timeout=0.2, access_log=True)
    thread = server.start_in_thread()
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        try:
            socket_roundtrip(server.port, request(target="/logged", headers={"Connection": "close"}))
        finally:
            server.stop()
            wait_for_thread(thread)

    assert any("/logged" in record.getMessage() for record in caplog.records)


def test_error_responses_use_configured_server_header(simple_app):
    server = WSGIServer(
        simple_app, port=0, model="serial", keep_alive_timeout=0.2, server_header="custom/9.9"
    )
    thread = server.start_in_thread()
    try:
        ok_status, ok_headers, _ = socket_roundtrip(
            server.port, request(target="/", headers={"Connection": "close"})
        )
        # Missing Host -> 400 via the error path, which must use the same Server header.
        err_status, err_headers, _ = socket_roundtrip(
            server.port, b"GET / HTTP/1.1\r\nConnection: close\r\n\r\n"
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert ok_status == "HTTP/1.1 200 OK"
    assert ok_headers["server"] == "custom/9.9"
    assert err_status.startswith("HTTP/1.1 400")
    assert err_headers["server"] == "custom/9.9"


def test_start_in_thread_raises_real_bind_error(simple_app):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        taken_port = busy.getsockname()[1]

        server = WSGIServer(simple_app, host="127.0.0.1", port=taken_port, model="serial")
        # The bind failure must surface as the real OSError, not a generic
        # "did not start before timeout" RuntimeError after the full wait.
        with pytest.raises(OSError):
            server.start_in_thread(timeout=5.0)


def test_async_wsgi_runs_in_bounded_named_executor():
    seen = {}

    def app(environ, start_response):
        seen["thread_name"] = threading.current_thread().name
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    server = WSGIServer(app, port=0, model="async", keep_alive_timeout=0.2, threads=2)
    thread = server.start_in_thread()
    try:
        socket_roundtrip(server.port, request(target="/", headers={"Connection": "close"}))
    finally:
        server.stop()
        wait_for_thread(thread)

    # The app must run on pyserve's own bounded executor, not asyncio's default one.
    assert seen["thread_name"].startswith("pyserve-wsgi")


def test_expect_100_continue_when_body_arrives_with_headers(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        payload = request(
            "POST", "/e", {"Expect": "100-continue", "Connection": "close"}, b"hello"
        )
        with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
            client.sendall(payload)  # headers AND body in one segment
            data = b""
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                data += chunk
    finally:
        server.stop()
        wait_for_thread(thread)

    # The interim response still precedes the final one; clients must tolerate 1xx.
    assert data.startswith(b"HTTP/1.1 100 Continue\r\n\r\n")
    assert b"HTTP/1.1 200 OK" in data


def test_head_request_has_no_body(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, headers, body = socket_roundtrip(
            server.port,
            request(method="HEAD", target="/", headers={"Connection": "close"}),
            read_body=False,
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert int(headers["content-length"]) > 0
    assert body == b""


def test_server_can_restart_after_stop(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        socket_roundtrip(server.port, request(target="/first", headers={"Connection": "close"}))
    finally:
        server.stop()
        wait_for_thread(thread)

    thread = server.start_in_thread()
    try:
        status, _, body = socket_roundtrip(server.port, request(target="/second", headers={"Connection": "close"}))
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert body == b"GET /second?"


def test_unsupported_http_version_returns_505(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, _ = socket_roundtrip(
            server.port,
            b"GET / HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 505 HTTP Version Not Supported"


def test_async_model_returns_400_for_truncated_request(simple_app):
    server = WSGIServer(simple_app, port=0, model="async", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
            client.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n")
            client.shutdown(socket.SHUT_WR)
            data = client.recv(4096)
    finally:
        server.stop()
        wait_for_thread(thread)

    assert data.startswith(b"HTTP/1.1 400 Bad Request")


def test_error_responses_are_access_logged(simple_app, caplog):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2, access_log=True)
    thread = server.start_in_thread()
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        try:
            socket_roundtrip(server.port, b"GET / HTTP/1.1\r\nConnection: close\r\n\r\n")
        finally:
            server.stop()
            wait_for_thread(thread)

    assert any("400" in record.getMessage() for record in caplog.records)


def test_threaded_server_handles_concurrent_requests(simple_app):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    server = WSGIServer(simple_app, port=0, model="threaded", threads=4, keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:

        def fetch(path: str) -> str:
            status, _, body = socket_roundtrip(
                server.port,
                request(target=path, headers={"Connection": "close"}),
            )
            assert status == "HTTP/1.1 200 OK"
            return body.decode()

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(fetch, f"/n{i}") for i in range(8)]
            bodies = [future.result() for future in as_completed(futures)]
    finally:
        server.stop()
        wait_for_thread(thread)

    assert len(bodies) == 8
    assert server.stats.snapshot()["request_count"] == 8


def test_threaded_unsupported_http_version_returns_505(simple_app):
    server = WSGIServer(simple_app, port=0, model="threaded", threads=2, keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, _ = socket_roundtrip(
            server.port,
            b"GET / HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 505 HTTP Version Not Supported"


def test_threaded_error_responses_are_access_logged(simple_app, caplog):
    server = WSGIServer(simple_app, port=0, model="threaded", threads=2, keep_alive_timeout=0.2, access_log=True)
    thread = server.start_in_thread()
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        try:
            socket_roundtrip(server.port, b"GET / HTTP/1.1\r\nConnection: close\r\n\r\n")
        finally:
            server.stop()
            wait_for_thread(thread)

    assert any("400" in record.getMessage() for record in caplog.records)


def test_keep_alive_idle_timeout_returns_408(simple_app, caplog):
    import time

    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.3, access_log=True)
    thread = server.start_in_thread()
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        try:
            with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
                client.sendall(request(target="/one", headers={"Connection": "keep-alive"}))
                recv_http_response(client)
                time.sleep(0.5)
                data = client.recv(4096)
        finally:
            server.stop()
            wait_for_thread(thread)

    assert data.startswith(b"HTTP/1.1 408")
    assert any("408" in record.getMessage() for record in caplog.records)


def test_error_access_log_includes_parsed_request_target(simple_app, caplog):
    server = WSGIServer(
        simple_app,
        port=0,
        model="serial",
        keep_alive_timeout=0.2,
        access_log=True,
        max_header_count=2,
    )
    thread = server.start_in_thread()
    payload = (
        b"HEAD /secret HTTP/1.1\r\nHost: localhost\r\n"
        b"A: 1\r\nB: 2\r\nC: 3\r\nConnection: close\r\n\r\n"
    )
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        try:
            socket_roundtrip(server.port, payload, read_body=False)
        finally:
            server.stop()
            wait_for_thread(thread)

    assert any('HEAD /secret HTTP/1.1" 431' in record.getMessage() for record in caplog.records)


@pytest.mark.skipif(not ipv6_loopback_available(), reason="IPv6 loopback unavailable")
def test_ipv6_server_roundtrip(simple_app):
    server = WSGIServer(simple_app, host="::1", port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, body = socket_roundtrip_host(
            "::1",
            server.port,
            request(target="/ipv6", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert body == b"GET /ipv6?"


def test_async_unsupported_http_version_returns_505(simple_app):
    server = WSGIServer(simple_app, port=0, model="async", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, _ = socket_roundtrip(
            server.port,
            b"GET / HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 505 HTTP Version Not Supported"


def test_async_keep_alive_idle_timeout_returns_408(simple_app, caplog):
    import time

    server = WSGIServer(simple_app, port=0, model="async", keep_alive_timeout=0.3, access_log=True)
    thread = server.start_in_thread()
    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        try:
            with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
                client.sendall(request(target="/one", headers={"Connection": "keep-alive"}))
                recv_http_response(client)
                time.sleep(0.5)
                data = client.recv(4096)
        finally:
            server.stop()
            wait_for_thread(thread)

    assert data.startswith(b"HTTP/1.1 408")
    assert any("408" in record.getMessage() for record in caplog.records)


def test_async_success_write_timeout_records_408(monkeypatch, simple_app):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from pyserve.concurrency.async_model import AsyncioServer
    from pyserve.config import ServerConfig
    from pyserve.exceptions import RequestTimeout
    from pyserve.observability.stats import ServerStats

    original_drain = AsyncioServer._drain_with_timeout
    response_drains = {"count": 0}

    async def fail_first_response_drain(self, writer):
        response_drains["count"] += 1
        if response_drains["count"] == 1:
            raise RequestTimeout("timed out while writing response")
        return await original_drain(self, writer)

    monkeypatch.setattr(AsyncioServer, "_drain_with_timeout", fail_first_response_drain)

    config = ServerConfig(write_timeout=0.1, read_timeout=2.0, keep_alive_timeout=0.2)
    stats = ServerStats()
    server = AsyncioServer(simple_app, config, Event(), Event(), stats)
    executor = ThreadPoolExecutor(max_workers=1)
    server._executor = executor

    async def run() -> dict[str, object]:
        rsock, wsock = socket.socketpair()
        wsock.setblocking(False)
        rsock.setblocking(False)
        wsock.sendall(request(target="/", headers={"Connection": "close"}))

        reader, writer = await asyncio.open_connection(sock=rsock)
        try:
            await server._handle_client(reader, writer)
        finally:
            writer.close()
            await writer.wait_closed()
            rsock.close()
            wsock.close()

        return server.stats.snapshot()

    try:
        stats_snapshot = asyncio.run(run())
    finally:
        executor.shutdown(wait=True)

    assert stats_snapshot["status_codes"].get(408, 0) >= 1


def test_debug_errors_includes_traceback_in_response_body():
    def app(environ, start_response):
        raise RuntimeError("boom")

    server = WSGIServer(app, port=0, model="serial", keep_alive_timeout=0.2, debug_errors=True)
    thread = server.start_in_thread()
    try:
        status, _, body = socket_roundtrip(
            server.port,
            request(target="/", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status.startswith("HTTP/1.1 500")
    assert b"RuntimeError" in body
    assert b"boom" in body


def test_first_request_read_timeout_returns_408(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", read_timeout=0.2, keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
            time.sleep(0.35)
            status, _, _ = recv_http_response(client)
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status.startswith("HTTP/1.1 408")


def test_max_keep_alive_requests_limits_connection_reuse(simple_app):
    server = WSGIServer(
        simple_app,
        port=0,
        model="serial",
        keep_alive_timeout=0.5,
        max_keep_alive_requests=2,
    )
    thread = server.start_in_thread()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
            for index in range(2):
                client.sendall(request(target=f"/{index}", headers={"Connection": "keep-alive"}))
                status, headers, _ = recv_http_response(client)
                assert status == "HTTP/1.1 200 OK"
                if index == 0:
                    assert headers["connection"] == "keep-alive"
                else:
                    assert headers["connection"] == "close"

            client.sendall(request(target="/third", headers={"Connection": "keep-alive"}))
            client.settimeout(0.5)
            with pytest.raises((TimeoutError, OSError, ConnectionResetError)):
                recv_http_response(client)
    finally:
        server.stop()
        wait_for_thread(thread)


def test_benchmark_friendly_disables_keep_alive(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.0)
    thread = server.start_in_thread()
    try:
        status, headers, _ = socket_roundtrip(
            server.port,
            request(target="/", headers={"Connection": "keep-alive"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert headers["connection"] == "close"


def test_request_line_too_large_returns_414(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2, max_request_line_size=20)
    thread = server.start_in_thread()
    try:
        status, _, _ = socket_roundtrip(
            server.port,
            request(target="/" + "a" * 40, headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status.startswith("HTTP/1.1 414")


def test_body_too_large_returns_413(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2, max_body_size=2)
    thread = server.start_in_thread()
    try:
        status, _, _ = socket_roundtrip(
            server.port,
            request("POST", "/", {"Connection": "close"}, b"hello"),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status.startswith("HTTP/1.1 413")


def test_pipelined_keep_alive_requests_receive_sequential_responses(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.5)
    thread = server.start_in_thread()
    try:
        payload = request(target="/one", headers={"Connection": "keep-alive"}) + request(
            target="/two",
            headers={"Connection": "close"},
        )
        with socket.create_connection(("127.0.0.1", server.port), timeout=3) as client:
            client.sendall(payload)
            first_status, _, first_body = recv_http_response(client)
            second_status, _, second_body = recv_http_response(client)
    finally:
        server.stop()
        wait_for_thread(thread)

    assert first_status == "HTTP/1.1 200 OK"
    assert first_body == b"GET /one?"
    assert second_status == "HTTP/1.1 200 OK"
    assert second_body == b"GET /two?"


def test_empty_host_header_returns_400(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, _ = socket_roundtrip(
            server.port,
            b"GET / HTTP/1.1\r\nHost: \r\nConnection: close\r\n\r\n",
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status.startswith("HTTP/1.1 400")


def test_post_without_content_length_returns_400(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, _ = socket_roundtrip(
            server.port,
            b"POST / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status.startswith("HTTP/1.1 400")


def test_unsupported_expect_header_returns_417(simple_app):
    server = WSGIServer(simple_app, port=0, model="serial", keep_alive_timeout=0.2)
    thread = server.start_in_thread()
    try:
        status, _, _ = socket_roundtrip(
            server.port,
            b"POST / HTTP/1.1\r\nHost: localhost\r\nExpect: custom\r\nConnection: close\r\n\r\n",
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status.startswith("HTTP/1.1 417")


def test_async_first_connection_uses_bounded_executor():
    seen = {}

    def app(environ, start_response):
        seen["thread_name"] = threading.current_thread().name
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    server = WSGIServer(app, port=0, model="async", keep_alive_timeout=0.2, threads=2)
    thread = server.start_in_thread()
    try:
        socket_roundtrip(server.port, request(target="/", headers={"Connection": "close"}))
    finally:
        server.stop()
        wait_for_thread(thread)

    assert seen["thread_name"].startswith("pyserve-wsgi")


@pytest.mark.parametrize("model", ["threaded", "async"])
@pytest.mark.skipif(not ipv6_loopback_available(), reason="IPv6 loopback unavailable")
def test_ipv6_server_roundtrip_models(simple_app, model):
    kwargs: dict[str, object] = {"host": "::1", "port": 0, "model": model, "keep_alive_timeout": 0.2}
    if model == "threaded":
        kwargs["threads"] = 2
    server = WSGIServer(simple_app, **kwargs)
    thread = server.start_in_thread()
    try:
        status, _, body = socket_roundtrip_host(
            "::1",
            server.port,
            request(target="/ipv6", headers={"Connection": "close"}),
        )
    finally:
        server.stop()
        wait_for_thread(thread)

    assert status == "HTTP/1.1 200 OK"
    assert body == b"GET /ipv6?"

