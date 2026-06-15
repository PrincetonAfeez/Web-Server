""" Test response serializer """

from __future__ import annotations

import pytest

from pyserve import __version__
from pyserve.http.response import Response, error_response, serialize_response


def test_default_server_header_matches_package_version():
    raw = serialize_response(Response(200, "OK", [], b"ok"))

    assert f"Server: pyserve/{__version__}\r\n".encode() in raw


def test_serializes_status_headers_content_length_and_body():
    raw = serialize_response(
        Response(200, "OK", [("Content-Type", "text/plain")], b"hello"),
        request_method="GET",
        keep_alive=False,
    )

    assert raw.startswith(b"HTTP/1.1 200 OK\r\n")
    assert b"Content-Type: text/plain\r\n" in raw
    assert b"Content-Length: 5\r\n" in raw
    assert b"Connection: close\r\n" in raw
    assert raw.endswith(b"\r\n\r\nhello")


def test_head_response_sends_headers_without_body():
    raw = serialize_response(Response(200, "OK", [], b"hello"), request_method="HEAD")

    assert b"Content-Length: 5\r\n" in raw
    assert raw.endswith(b"\r\n\r\n")
    assert not raw.endswith(b"hello")


def test_204_response_sends_no_body_or_content_length():
    raw = serialize_response(Response(204, "No Content", [], b"ignored"), request_method="GET")

    assert b"Content-Length:" not in raw
    assert raw.endswith(b"\r\n\r\n")
    assert b"ignored" not in raw


def test_304_response_sends_no_body_or_content_length():
    raw = serialize_response(Response(304, "Not Modified", [], b"ignored"), request_method="GET")

    assert b"Content-Length:" not in raw
    assert raw.endswith(b"\r\n\r\n")
    assert b"ignored" not in raw


def test_response_from_status_builds_reason_phrase():
    response = Response.from_status(404)

    assert response.status_code == 404
    assert response.reason == "Not Found"
    assert response.body == b""


def test_response_from_status_accepts_custom_reason_and_headers():
    response = Response.from_status(201, b"created", [("X-Test", "1")], reason="Created")

    assert response.reason == "Created"
    assert response.headers == [("X-Test", "1")]


def test_serialize_response_honors_custom_server_header():
    raw = serialize_response(Response(200, "OK", [], b""), server_header="custom/1.0")

    assert b"Server: custom/1.0\r\n" in raw


def test_serialize_response_emits_keep_alive_connection_header():
    raw = serialize_response(Response(200, "OK", [], b"ok"), keep_alive=True)

    assert b"Connection: keep-alive\r\n" in raw


def test_serialize_response_omits_body_for_1xx_status():
    raw = serialize_response(Response(100, "Continue", [], b"ignored"), request_method="GET")

    assert b"Content-Length:" not in raw
    assert raw.endswith(b"\r\n\r\n")
    assert b"ignored" not in raw


def test_serialize_response_rejects_non_bytes_body():
    response = Response(200, "OK", [], b"ok")
    response.body = "not bytes"  # type: ignore[assignment]

    with pytest.raises(TypeError, match="response body must be bytes"):
        serialize_response(response)


def test_error_response_uses_detail_when_provided():
    response = error_response(500, detail="traceback here")

    assert response.status_code == 500
    assert response.body == b"traceback here\n"


def test_error_response_falls_back_to_message_then_reason():
    assert error_response(404, message="missing").body == b"missing\n"
    assert error_response(418).body == b"Unknown\n"
