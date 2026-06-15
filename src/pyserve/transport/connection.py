""" Connection module for the pyserve project """

from __future__ import annotations

import logging
import socket
import time

from pyserve.config import ServerConfig, WSGIApplication
from pyserve.dispatch import ALLOWED_METHODS, method_not_allowed_response, should_keep_alive
from pyserve.exceptions import HTTPError, RequestTimeout
from pyserve.http.request_parser import (
    CONTINUE_RESPONSE,
    expects_continue,
    read_request_body_from_socket,
    read_request_head_from_socket,
)
from pyserve.http.response import Response, error_response, serialize_response
from pyserve.models import Request
from pyserve.observability.access_log import log_access, log_access_error
from pyserve.observability.stats import ServerStats
from pyserve.wsgi.adapter import run_wsgi_app

LOGGER = logging.getLogger(__name__)


class ConnectionHandler:
    def __init__(self, app: WSGIApplication, config: ServerConfig, stats: ServerStats | None = None) -> None:
        self.app = app
        self.config = config
        self.stats = stats if stats is not None else ServerStats()

    def handle(self, client: socket.socket, address: tuple[str, int] | tuple) -> None:
        buffer = b""
        requests_handled = 0
        client.settimeout(self.config.read_timeout)
        self.stats.connection_opened()

        try:
            while requests_handled < self.config.max_keep_alive_requests:
                try:
                    request, content_length, rest = read_request_head_from_socket(client, buffer, self.config)
                    # Sent whenever the client asked, even if the body already arrived:
                    # clients must tolerate 1xx responses (RFC 7230), and this keeps the
                    # behavior identical to the asyncio model, which cannot peek at its
                    # stream buffer to tell whether the body is already in flight.
                    if content_length and expects_continue(request.headers):
                        send_all(client, CONTINUE_RESPONSE)
                    # Headers are in; the body is read under read_timeout regardless of
                    # whether this connection was idling on the keep-alive timeout.
                    client.settimeout(self.config.read_timeout)
                    request.body, buffer = read_request_body_from_socket(client, rest, content_length, self.config)
                except EOFError:
                    break
                except RequestTimeout as exc:
                    self._send_error(client, exc, address)
                    break
                except HTTPError as exc:
                    self._send_error(client, exc, address)
                    break

                # Timing starts now so request time reflects server work, not the time
                # spent waiting for the client to send the request.
                started = time.monotonic()
                self._attach_remote(request, address)
                requests_handled += 1
                response = self._response_for_request(request)
                keep_alive = should_keep_alive(request, requests_handled, self.config)
                payload = serialize_response(
                    response,
                    request_method=request.method,
                    keep_alive=keep_alive,
                    server_header=self.config.server_header,
                )
                client.settimeout(self.config.write_timeout)
                try:
                    send_all(client, payload)
                except TimeoutError:
                    timeout = RequestTimeout("timed out while writing response")
                    if requests_handled:
                        timeout.request_method = request.method
                        timeout.raw_target = request.raw_target
                        timeout.http_version = request.http_version
                    self._send_error(client, timeout, address)
                    break
                elapsed = time.monotonic() - started
                log_access(self.config, request, response.status_code, len(response.body), elapsed)
                self.stats.record(response.status_code, elapsed)

                if not keep_alive:
                    break
                client.settimeout(self.config.keep_alive_timeout)
        except TimeoutError:
            LOGGER.debug("connection ended with socket timeout", exc_info=True)
        except OSError:
            LOGGER.debug("connection ended with socket error", exc_info=True)
        finally:
            self.stats.connection_closed()
            close_quietly(client)

    def _response_for_request(self, request: Request) -> Response:
        if request.method not in ALLOWED_METHODS:
            return method_not_allowed_response()
        return run_wsgi_app(self.app, request, self.config)

    def _send_error(
        self,
        client: socket.socket,
        exc: HTTPError,
        address: tuple[str, int] | tuple,
    ) -> None:
        # exc.request_method is set once the request line is parsed (None before that,
        # so a body is fine); a failed HEAD gets a bodyless error response.
        started = time.monotonic()
        error = error_response(exc.status_code, exc.public_message)
        payload = serialize_response(
            error,
            request_method=exc.request_method or "GET",
            keep_alive=False,
            server_header=self.config.server_header,
        )
        client.settimeout(self.config.write_timeout)
        try:
            send_all(client, payload)
        except TimeoutError:
            return
        elapsed = time.monotonic() - started
        remote_addr = str(address[0]) if len(address) >= 2 else ""
        log_access_error(
            self.config,
            remote_addr=remote_addr,
            method=exc.request_method,
            raw_target=exc.raw_target or "-",
            http_version=exc.http_version or "HTTP/1.1",
            status_code=exc.status_code,
            response_size=len(error.body),
            elapsed=elapsed,
        )
        self.stats.record(exc.status_code, elapsed)

    @staticmethod
    def _attach_remote(request: Request, address: tuple[str, int] | tuple) -> None:
        if len(address) >= 2:
            request.remote_addr = str(address[0])
            request.remote_port = int(address[1])


def send_all(sock: socket.socket, data: bytes) -> None:
    view = memoryview(data)
    total_sent = 0
    while total_sent < len(view):
        sent = sock.send(view[total_sent:])
        if sent == 0:
            raise ConnectionError("socket connection broken during send")
        total_sent += sent


def close_quietly(sock: socket.socket) -> None:
    try:
        sock.close()
    except OSError:
        pass
