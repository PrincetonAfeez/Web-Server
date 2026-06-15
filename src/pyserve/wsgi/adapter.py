""" WSGI adapter module for the pyserve project """

from __future__ import annotations

import sys
import traceback
from types import TracebackType
from typing import Any

from pyserve.config import ServerConfig, WSGIApplication, reraise
from pyserve.exceptions import WSGIError
from pyserve.http.response import Response, error_response
from pyserve.http.status import parse_status
from pyserve.models import Request
from pyserve.wsgi.environ import build_environ


class StartResponse:
    def __init__(self) -> None:
        self.called = False
        self.status = ""
        self.headers: list[tuple[str, str]] = []
        self.written: list[bytes] = []

    def __call__(
        self,
        status: str,
        headers: list[tuple[str, str]],
        exc_info: tuple[type[BaseException], BaseException, TracebackType] | None = None,
    ):
        if exc_info is not None:
            try:
                if self.called:
                    reraise(exc_info)
            finally:
                exc_info = None
        elif self.called:
            raise AssertionError("start_response called twice without exc_info")

        parse_status(status)
        for name, value in headers:
            if not isinstance(name, str) or not isinstance(value, str):
                raise WSGIError("WSGI response headers must be string pairs")
            if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
                raise WSGIError("WSGI response headers cannot contain CR or LF")

        self.status = status
        self.headers = list(headers)
        self.called = True
        return self.write

    def write(self, data: bytes) -> None:
        if not isinstance(data, bytes):
            raise WSGIError("WSGI write() argument must be bytes")
        self.written.append(data)


def run_wsgi_app(app: WSGIApplication, request: Request, config: ServerConfig) -> Response:
    start_response = StartResponse()
    result: Any = None

    try:
        environ = build_environ(request, config)
        result = app(environ, start_response)

        chunks: list[bytes] = []
        for chunk in result:
            if not isinstance(chunk, bytes):
                raise WSGIError("WSGI iterable yielded a non-bytes chunk")
            chunks.append(chunk)

        if not start_response.called:
            raise WSGIError("WSGI application never called start_response")

        # Read start_response.written after iterating: a generator app may call the
        # legacy write() callable between yields, so snapshotting it earlier would
        # drop those bytes. write() output precedes the iterable's output.
        body = b"".join(start_response.written) + b"".join(chunks)
        status_code, reason = parse_status(start_response.status)
        return Response(status_code, reason, start_response.headers, body)
    except Exception as exc:
        return _wsgi_error_response(exc, config)
    finally:
        if result is not None and hasattr(result, "close"):
            result.close()


def _wsgi_error_response(exc: Exception, config: ServerConfig) -> Response:
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=config.error_stream or sys.stderr)
    if config.debug_errors:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return error_response(500, detail=detail)
    return error_response(500)
