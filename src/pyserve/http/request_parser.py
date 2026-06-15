""" Request parser module for the pyserve project """

from __future__ import annotations

import re
import socket
from urllib.parse import unquote, urlsplit

from pyserve.config import ServerConfig
from pyserve.exceptions import (
    BadRequest,
    BodyTooLarge,
    ExpectationFailed,
    HeaderTooLarge,
    HTTPError,
    InvalidContentLength,
    RequestLineTooLarge,
    RequestTimeout,
    TooManyHeaders,
    UnsupportedHTTPVersion,
)
from pyserve.http.headers import CaseInsensitiveHeaders
from pyserve.models import Request
from pyserve.parsing import parse_ascii_int

CRLF = b"\r\n"
HEADER_END = b"\r\n\r\n"
CONTINUE_RESPONSE = b"HTTP/1.1 100 Continue\r\n\r\n"
HEADER_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
# C0 control characters (and DEL) are forbidden in header values; HTAB (0x09) is allowed.
# This rejects bare CR/LF that could otherwise enable header/response splitting.
HEADER_VALUE_FORBIDDEN_RE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")


def expects_continue(headers: CaseInsensitiveHeaders) -> bool:
    return (headers.get("expect", "") or "").strip().lower() == "100-continue"


def validate_expect_header(headers: CaseInsensitiveHeaders) -> None:
    expect = (headers.get("expect", "") or "").strip()
    if expect and expect.lower() != "100-continue":
        raise ExpectationFailed("unsupported Expect request")


def parse_request_head(head: bytes, config: ServerConfig) -> tuple[Request, int]:
    if len(head) + len(HEADER_END) > config.max_header_size:
        raise HeaderTooLarge("request headers exceed configured limit")

    lines = head.split(CRLF)
    if not lines or not lines[0]:
        raise BadRequest("empty request line")

    request_line = lines[0]
    if len(request_line) > config.max_request_line_size:
        raise RequestLineTooLarge("request line exceeds configured limit")

    try:
        request_line_text = request_line.decode("ascii")
    except UnicodeDecodeError as exc:
        raise BadRequest("request line must be ASCII") from exc

    parts = request_line_text.split(" ")
    if len(parts) != 3 or not all(parts):
        raise BadRequest("request line must be METHOD target HTTP/version")

    method, raw_target, http_version = parts
    method = method.upper()

    # Everything past the request line is wrapped so the parsed method travels with
    # any error, letting the connection layer suppress a body for a failed HEAD request.
    try:
        if http_version.upper() != "HTTP/1.1":
            raise UnsupportedHTTPVersion(f"unsupported HTTP version {http_version!r}")
        http_version = "HTTP/1.1"

        if len(lines) - 1 > config.max_header_count:
            raise TooManyHeaders("too many request headers")

        headers = CaseInsensitiveHeaders()
        for raw_line in lines[1:]:
            if not raw_line:
                continue
            if b":" not in raw_line:
                raise BadRequest("header line missing colon")

            raw_name, raw_value = raw_line.split(b":", 1)
            try:
                name = raw_name.decode("ascii")
                value = raw_value.decode("latin-1").strip(" \t")
            except UnicodeDecodeError as exc:
                raise BadRequest("header name must be ASCII") from exc

            if not name or not HEADER_NAME_RE.match(name):
                raise BadRequest("invalid header field name")
            if HEADER_VALUE_FORBIDDEN_RE.search(value):
                raise BadRequest("header value contains control characters")
            headers.add(name, value)

        host_value = headers.get("host", "") or ""
        if not host_value.strip():
            raise BadRequest("HTTP/1.1 requests require a Host header")
        if len(headers.get_all("host")) > 1:
            # RFC 7230 section 5.4: a request with multiple Host fields must be rejected.
            raise BadRequest("multiple Host headers are not allowed")

        validate_expect_header(headers)

        transfer_encoding = headers.get("transfer-encoding")
        if transfer_encoding and transfer_encoding.lower() != "identity":
            raise BadRequest("Transfer-Encoding is outside this server's scope")

        if method == "POST" and "content-length" not in headers:
            raise BadRequest("POST requests require a Content-Length header")

        content_length = parse_content_length(headers, config)
        raw_path, path, query_string = parse_target(raw_target)
    except HTTPError as exc:
        exc.request_method = method
        exc.raw_target = raw_target
        exc.http_version = http_version
        raise

    return (
        Request(
            method=method,
            raw_target=raw_target,
            raw_path=raw_path,
            path=path,
            query_string=query_string,
            http_version=http_version,
            headers=headers,
        ),
        content_length,
    )


def parse_content_length(headers: CaseInsensitiveHeaders, config: ServerConfig) -> int:
    values = headers.get_all("content-length")
    if not values:
        return 0

    parsed: list[int] = []
    for value in values:
        number = parse_ascii_int(value)
        if number is None:
            raise InvalidContentLength("Content-Length must be a non-negative integer")
        parsed.append(number)

    if len(set(parsed)) != 1:
        raise InvalidContentLength("duplicate Content-Length values disagree")

    content_length = parsed[0]
    if content_length > config.max_body_size:
        raise BodyTooLarge("request body exceeds configured limit")
    return content_length


def parse_target(raw_target: str) -> tuple[str, str, str]:
    if not raw_target:
        raise BadRequest("empty request target")

    if raw_target == "*":
        return "*", "*", ""

    split = urlsplit(raw_target)
    if split.scheme or split.netloc:
        # Absolute-form (e.g. "http://host/path") and authority in the target are
        # accepted because RFC 7230 requires origin servers to do so, but the
        # authority is intentionally ignored: SERVER_NAME comes from the Host header.
        raw_path = split.path or "/"
        query_string = split.query
    else:
        if not raw_target.startswith("/"):
            raise BadRequest("request target must be origin-form")
        raw_path = split.path or "/"
        query_string = split.query

    path = unquote(raw_path, encoding="utf-8", errors="replace")
    return raw_path, path, query_string


def parse_request_bytes(raw: bytes, config: ServerConfig | None = None) -> Request:
    config = config or ServerConfig()
    head, separator, body_and_rest = raw.partition(HEADER_END)
    if not separator:
        raise BadRequest("request headers are incomplete")

    request, content_length = parse_request_head(head, config)
    if len(body_and_rest) < content_length:
        raise BadRequest("request body is shorter than Content-Length")
    request.body = body_and_rest[:content_length]
    return request


def read_request_head_from_socket(
    sock: socket.socket,
    initial_buffer: bytes = b"",
    config: ServerConfig | None = None,
) -> tuple[Request, int, bytes]:
    config = config or ServerConfig()
    buffer = bytearray(initial_buffer)

    while HEADER_END not in buffer:
        if len(buffer) > config.max_header_size:
            raise HeaderTooLarge("request headers exceed configured limit")
        try:
            chunk = sock.recv(config.read_chunk_size)
        except TimeoutError as exc:
            raise RequestTimeout("timed out while reading request headers") from exc
        if not chunk:
            if buffer:
                raise BadRequest("connection closed before headers were complete")
            raise EOFError
        buffer.extend(chunk)

    head_end = bytes(buffer).find(HEADER_END)
    head = bytes(buffer[:head_end])
    rest = bytes(buffer[head_end + len(HEADER_END) :])
    request, content_length = parse_request_head(head, config)
    return request, content_length, rest


def read_request_body_from_socket(
    sock: socket.socket,
    rest: bytes,
    content_length: int,
    config: ServerConfig | None = None,
) -> tuple[bytes, bytes]:
    config = config or ServerConfig()
    buffer = bytearray(rest)

    while len(buffer) < content_length:
        try:
            chunk = sock.recv(config.read_chunk_size)
        except TimeoutError as exc:
            raise RequestTimeout("timed out while reading request body") from exc
        if not chunk:
            raise BadRequest("request body is shorter than Content-Length")
        buffer.extend(chunk)

    return bytes(buffer[:content_length]), bytes(buffer[content_length:])


def read_request_from_socket(
    sock: socket.socket,
    initial_buffer: bytes = b"",
    config: ServerConfig | None = None,
) -> tuple[Request, bytes]:
    # Convenience wrapper that reads head then body in one call. It does not send a
    # 100-continue: that is the connection layer's job (it owns the socket writes),
    # so the parser itself never writes to the socket.
    config = config or ServerConfig()
    request, content_length, rest = read_request_head_from_socket(sock, initial_buffer, config)
    request.body, remaining = read_request_body_from_socket(sock, rest, content_length, config)
    return request, remaining
