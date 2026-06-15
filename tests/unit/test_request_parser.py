""" Test request parser """

from __future__ import annotations

import pytest

from pyserve.config import ServerConfig
from pyserve.exceptions import (
    BadRequest,
    BodyTooLarge,
    ExpectationFailed,
    HeaderTooLarge,
    InvalidContentLength,
    RequestLineTooLarge,
    TooManyHeaders,
    UnsupportedHTTPVersion,
)
from pyserve.http.request_parser import parse_request_bytes, read_request_from_socket
from tests.conftest import request


class ChunkSocket:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = list(chunks)

    def recv(self, size: int) -> bytes:
        if not self.chunks:
            return b""
        return self.chunks.pop(0)


def test_parse_get_request():
    parsed = parse_request_bytes(request(target="/hello%20there?x=1"))

    assert parsed.method == "GET"
    assert parsed.raw_target == "/hello%20there?x=1"
    assert parsed.path == "/hello there"
    assert parsed.query_string == "x=1"
    assert parsed.headers["host"] == "localhost"


def test_post_body_split_across_recv_calls():
    raw = request("POST", "/echo", {"Content-Type": "text/plain"}, b"hello")
    sock = ChunkSocket([raw[:12], raw[12:33], raw[33:-2], raw[-2:]])

    parsed, remaining = read_request_from_socket(sock, config=ServerConfig(read_chunk_size=3))

    assert parsed.method == "POST"
    assert parsed.body == b"hello"
    assert remaining == b""


def test_request_arrives_one_byte_at_a_time():
    raw = request(target="/slow")
    sock = ChunkSocket([raw[index : index + 1] for index in range(len(raw))])

    parsed, _ = read_request_from_socket(sock)

    assert parsed.path == "/slow"


def test_remaining_bytes_are_returned_for_keep_alive():
    first = request(target="/one", headers={"Connection": "keep-alive"})
    second = request(target="/two")
    sock = ChunkSocket([first + second])

    parsed, remaining = read_request_from_socket(sock)

    assert parsed.path == "/one"
    assert remaining == second


def test_invalid_content_length_is_rejected():
    with pytest.raises(InvalidContentLength):
        parse_request_bytes(request("POST", "/", {"Content-Length": "abc"}))


def test_non_ascii_digit_content_length_is_rejected():
    # 0xB2 decodes (latin-1) to "²", which str.isdigit() accepts but int() rejects.
    raw = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: \xb2\r\n\r\n"
    with pytest.raises(InvalidContentLength):
        parse_request_bytes(raw)


def test_control_characters_in_header_value_are_rejected():
    raw = b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Bad: a\x01b\r\n\r\n"
    with pytest.raises(BadRequest):
        parse_request_bytes(raw)


def test_horizontal_tab_in_header_value_is_allowed():
    parsed = parse_request_bytes(b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Tab: a\tb\r\n\r\n")
    assert parsed.headers["x-tab"] == "a\tb"


def test_disagreeing_duplicate_content_length_is_rejected():
    raw = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Length: 2\r\n"
        b"Content-Length: 3\r\n\r\n"
        b"abc"
    )
    with pytest.raises(InvalidContentLength):
        parse_request_bytes(raw)


def test_body_larger_than_limit_is_rejected():
    with pytest.raises(BodyTooLarge):
        parse_request_bytes(request("POST", "/", body=b"hello"), ServerConfig(max_body_size=2))


def test_body_shorter_than_content_length_is_rejected():
    with pytest.raises(BadRequest):
        parse_request_bytes(request("POST", "/", {"Content-Length": "5"}, b"hi"))


def test_missing_host_header_is_rejected():
    with pytest.raises(BadRequest):
        parse_request_bytes(b"GET / HTTP/1.1\r\n\r\n")


def test_empty_host_header_is_rejected():
    with pytest.raises(BadRequest):
        parse_request_bytes(b"GET / HTTP/1.1\r\nHost: \r\n\r\n")


def test_http_version_is_case_insensitive():
    parsed = parse_request_bytes(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    assert parsed.http_version == "HTTP/1.1"

    parsed_lower = parse_request_bytes(b"GET / http/1.1\r\nHost: localhost\r\n\r\n")
    assert parsed_lower.http_version == "HTTP/1.1"


def test_post_without_content_length_is_rejected():
    with pytest.raises(BadRequest):
        parse_request_bytes(b"POST / HTTP/1.1\r\nHost: localhost\r\n\r\n")


def test_unsupported_expect_header_returns_417():
    with pytest.raises(ExpectationFailed) as excinfo:
        parse_request_bytes(b"POST / HTTP/1.1\r\nHost: localhost\r\nExpect: custom\r\n\r\n")
    assert excinfo.value.status_code == 417


def test_absolute_form_target_is_accepted():
    parsed = parse_request_bytes(
        b"GET http://example.com/path?q=1 HTTP/1.1\r\nHost: localhost\r\n\r\n"
    )

    assert parsed.raw_path == "/path"
    assert parsed.path == "/path"
    assert parsed.query_string == "q=1"


def test_duplicate_host_headers_are_rejected():
    # RFC 7230 section 5.4: more than one Host field must yield a 400.
    raw = b"GET / HTTP/1.1\r\nHost: a.example\r\nHost: b.example\r\n\r\n"
    with pytest.raises(BadRequest):
        parse_request_bytes(raw)


def test_malformed_request_line_is_rejected():
    with pytest.raises(BadRequest):
        parse_request_bytes(b"GET / too many parts HTTP/1.1\r\nHost: localhost\r\n\r\n")


def test_unsupported_http_version_is_rejected():
    with pytest.raises(UnsupportedHTTPVersion) as excinfo:
        parse_request_bytes(b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n")
    assert excinfo.value.status_code == 505


def test_request_line_too_large_is_rejected():
    raw = request(target="/" + "a" * 20)
    with pytest.raises(RequestLineTooLarge):
        parse_request_bytes(raw, ServerConfig(max_request_line_size=10))


def test_headers_larger_than_limit_are_rejected():
    raw = request(headers={"X-Big": "a" * 100})
    with pytest.raises(HeaderTooLarge):
        parse_request_bytes(raw, ServerConfig(max_header_size=50))


def test_too_many_headers_are_rejected():
    raw = b"GET / HTTP/1.1\r\nHost: localhost\r\nX-A: 1\r\nX-B: 2\r\n\r\n"
    with pytest.raises(TooManyHeaders):
        parse_request_bytes(raw, ServerConfig(max_header_count=2))


def test_empty_request_line_is_rejected():
    with pytest.raises(BadRequest, match="empty request line"):
        parse_request_bytes(b"\r\n\r\n")


def test_non_ascii_request_line_is_rejected():
    with pytest.raises(BadRequest, match="ASCII"):
        parse_request_bytes(b"GET / \xff HTTP/1.1\r\nHost: localhost\r\n\r\n")


def test_header_line_missing_colon_is_rejected():
    with pytest.raises(BadRequest, match="missing colon"):
        parse_request_bytes(b"GET / HTTP/1.1\r\nHost: localhost\r\nBadHeader\r\n\r\n")


def test_invalid_header_field_name_is_rejected():
    with pytest.raises(BadRequest, match="invalid header field name"):
        parse_request_bytes(b"GET / HTTP/1.1\r\nHost: localhost\r\nBad Header: x\r\n\r\n")


def test_transfer_encoding_other_than_identity_is_rejected():
    with pytest.raises(BadRequest, match="Transfer-Encoding"):
        parse_request_bytes(
            b"POST / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\nContent-Length: 0\r\n\r\n"
        )


def test_empty_request_target_is_rejected():
    from pyserve.http.request_parser import parse_target

    with pytest.raises(BadRequest, match="empty request target"):
        parse_target("")


def test_non_origin_form_target_is_rejected():
    with pytest.raises(BadRequest, match="origin-form"):
        parse_request_bytes(b"GET relative HTTP/1.1\r\nHost: localhost\r\n\r\n")


def test_read_request_head_timeout_raises_request_timeout():
    from pyserve.exceptions import RequestTimeout
    from pyserve.http.request_parser import read_request_head_from_socket

    class TimeoutSocket:
        def recv(self, size: int) -> bytes:
            raise TimeoutError("timed out")

    with pytest.raises(RequestTimeout, match="reading request headers"):
        read_request_head_from_socket(TimeoutSocket(), config=ServerConfig())  # type: ignore[arg-type]


def test_read_request_head_closed_before_complete_raises_bad_request():
    from pyserve.http.request_parser import read_request_head_from_socket

    class ClosedSocket:
        def recv(self, size: int) -> bytes:
            return b""

    with pytest.raises(BadRequest, match="connection closed before headers"):
        read_request_head_from_socket(ClosedSocket(), initial_buffer=b"GET / HTTP/1.1\r\n", config=ServerConfig())  # type: ignore[arg-type]


def test_read_request_body_timeout_raises_request_timeout():
    from pyserve.exceptions import RequestTimeout
    from pyserve.http.request_parser import read_request_body_from_socket

    class TimeoutSocket:
        def recv(self, size: int) -> bytes:
            raise TimeoutError("timed out")

    with pytest.raises(RequestTimeout, match="reading request body"):
        read_request_body_from_socket(TimeoutSocket(), b"", 5, ServerConfig())  # type: ignore[arg-type]


def test_header_name_non_ascii_is_rejected():
    with pytest.raises(BadRequest, match="ASCII"):
        parse_request_bytes(b"GET / HTTP/1.1\r\nH\xf6st: localhost\r\n\r\n")


def test_incomplete_headers_in_parse_request_bytes_are_rejected():
    with pytest.raises(BadRequest, match="incomplete"):
        parse_request_bytes(b"GET / HTTP/1.1\r\nHost: localhost")


def test_asterisk_target_is_accepted():
    from pyserve.http.request_parser import parse_target

    raw_path, path, query = parse_target("*")

    assert raw_path == "*"
    assert path == "*"
    assert query == ""


def test_read_request_body_closed_early_raises_bad_request():
    from pyserve.http.request_parser import read_request_body_from_socket

    class ClosedSocket:
        def recv(self, size: int) -> bytes:
            return b""

    with pytest.raises(BadRequest, match="shorter than Content-Length"):
        read_request_body_from_socket(ClosedSocket(), b"ab", 5, ServerConfig())  # type: ignore[arg-type]


