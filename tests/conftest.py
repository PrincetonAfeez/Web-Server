""" Test configuration """

from __future__ import annotations

import socket
import weakref

import pytest

_pending_responses: weakref.WeakKeyDictionary[socket.socket, bytes] = weakref.WeakKeyDictionary()


@pytest.fixture
def simple_app():
    def app(environ, start_response):
        body = f"{environ['REQUEST_METHOD']} {environ['PATH_INFO']}?{environ['QUERY_STRING']}".encode()
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [body]

    return app


def recv_http_response(sock: socket.socket, read_body: bool = True) -> tuple[str, dict[str, str], bytes]:
    pending = _pending_responses.pop(sock, b"")
    buffer = bytearray(pending)
    while b"\r\n\r\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer.extend(chunk)

    head_end = buffer.find(b"\r\n\r\n")
    if head_end < 0:
        return "", {}, b""

    head = bytes(buffer[:head_end])
    rest_start = head_end + 4
    lines = head.decode("latin-1").split("\r\n")
    status_line = lines[0]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            continue
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()

    content_length = int(headers.get("content-length", "0")) if read_body else 0
    message_end = rest_start + content_length
    while len(buffer) < message_end:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer.extend(chunk)

    body = bytes(buffer[rest_start:message_end])
    leftover = bytes(buffer[message_end:])
    if leftover:
        _pending_responses[sock] = leftover
    return status_line, headers, body


def request(
    method: str = "GET",
    target: str = "/",
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> bytes:
    headers = {"Host": "localhost", **(headers or {})}
    if body and "Content-Length" not in headers:
        headers["Content-Length"] = str(len(body))
    header_text = "".join(f"{name}: {value}\r\n" for name, value in headers.items())
    return f"{method} {target} HTTP/1.1\r\n{header_text}\r\n".encode("latin-1") + body


def socket_roundtrip(port: int, payload: bytes, read_body: bool = True) -> tuple[str, dict[str, str], bytes]:
    with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
        client.sendall(payload)
        return recv_http_response(client, read_body=read_body)


def wait_for_thread(thread, timeout: float = 2.0) -> None:
    thread.join(timeout)
    assert not thread.is_alive()


def ipv6_loopback_available() -> bool:
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as sock:
            sock.bind(("::1", 0))
        return True
    except OSError:
        return False


def socket_roundtrip_host(
    host: str,
    port: int,
    payload: bytes,
    read_body: bool = True,
) -> tuple[str, dict[str, str], bytes]:
    with socket.create_connection((host, port), timeout=3) as client:
        client.sendall(payload)
        return recv_http_response(client, read_body=read_body)
