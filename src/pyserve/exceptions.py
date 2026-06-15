""" Exceptions module for the pyserve project """

from __future__ import annotations


class PyServeError(Exception):
    """Base exception for pyserve."""


class HTTPError(PyServeError):
    status_code = 500
    public_message = "Internal Server Error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.public_message)
        self.message = message or self.public_message
        # Set once the request line is parsed, so error responses and logs can
        # honor method semantics (e.g. no body for a HEAD request).
        self.request_method: str | None = None
        self.raw_target: str | None = None
        self.http_version: str | None = None


class ParserError(HTTPError):
    status_code = 400
    public_message = "Bad Request"


class BadRequest(ParserError):
    status_code = 400
    public_message = "Bad Request"


class RequestLineTooLarge(ParserError):
    status_code = 414
    public_message = "URI Too Long"


class HeaderTooLarge(ParserError):
    status_code = 431
    public_message = "Request Header Fields Too Large"


class TooManyHeaders(ParserError):
    status_code = 431
    public_message = "Request Header Fields Too Large"


class BodyTooLarge(ParserError):
    status_code = 413
    public_message = "Payload Too Large"


class InvalidContentLength(ParserError):
    status_code = 400
    public_message = "Bad Request"


class UnsupportedHTTPVersion(ParserError):
    status_code = 505
    public_message = "HTTP Version Not Supported"


class RequestTimeout(ParserError):
    status_code = 408
    public_message = "Request Timeout"


class ExpectationFailed(ParserError):
    status_code = 417
    public_message = "Expectation Failed"


class MethodNotAllowed(HTTPError):
    status_code = 405
    public_message = "Method Not Allowed"


class WSGIError(PyServeError):
    """Raised when a WSGI application violates the server contract."""
