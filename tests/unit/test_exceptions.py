""" Test exceptions """

from __future__ import annotations

from pyserve.exceptions import (
    BadRequest,
    BodyTooLarge,
    ExpectationFailed,
    HTTPError,
    HeaderTooLarge,
    InvalidContentLength,
    MethodNotAllowed,
    ParserError,
    PyServeError,
    RequestLineTooLarge,
    RequestTimeout,
    TooManyHeaders,
    UnsupportedHTTPVersion,
    WSGIError,
)


def test_pyserve_error_is_base_exception():
    assert issubclass(HTTPError, PyServeError)
    assert issubclass(WSGIError, PyServeError)


def test_parser_errors_are_http_errors():
    assert issubclass(BadRequest, ParserError)
    assert issubclass(ParserError, HTTPError)


def test_http_error_custom_message():
    exc = HTTPError("custom failure")

    assert str(exc) == "custom failure"
    assert exc.message == "custom failure"


def test_http_error_defaults_to_public_message():
    exc = RequestTimeout()

    assert exc.status_code == 408
    assert exc.public_message == "Request Timeout"
    assert str(exc) == "Request Timeout"


def test_request_error_context_fields_start_empty():
    exc = BadRequest("bad")

    assert exc.request_method is None
    assert exc.raw_target is None
    assert exc.http_version is None


def test_exception_status_codes_match_http_semantics():
    assert BadRequest().status_code == 400
    assert RequestLineTooLarge().status_code == 414
    assert HeaderTooLarge().status_code == 431
    assert TooManyHeaders().status_code == 431
    assert BodyTooLarge().status_code == 413
    assert InvalidContentLength().status_code == 400
    assert UnsupportedHTTPVersion().status_code == 505
    assert ExpectationFailed().status_code == 417
    assert MethodNotAllowed().status_code == 405


def test_wsgi_error_is_distinct_from_http_error():
    exc = WSGIError("contract violation")

    assert not isinstance(exc, HTTPError)
    assert str(exc) == "contract violation"
