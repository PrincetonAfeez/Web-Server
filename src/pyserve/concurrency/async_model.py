""" Asyncio concurrency model for the pyserve project """

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from pyserve.concurrency.base import BaseServer
from pyserve.dispatch import ALLOWED_METHODS, method_not_allowed_response, should_keep_alive
from pyserve.exceptions import BadRequest, HeaderTooLarge, HTTPError, RequestTimeout
from pyserve.http.request_parser import (
    CONTINUE_RESPONSE,
    HEADER_END,
    expects_continue,
    parse_request_head,
)
from pyserve.http.response import Response, error_response, serialize_response
from pyserve.models import Request
from pyserve.observability.access_log import log_access, log_access_error
from pyserve.transport.listener import create_listening_socket
from pyserve.wsgi.adapter import run_wsgi_app

LOGGER = logging.getLogger(__name__)


class AsyncioServer(BaseServer):
    _executor: ThreadPoolExecutor | None = None

    def run(self) -> None:
        self.config.wsgi_multithread = True
        asyncio.run(self._run())

    async def _run(self) -> None:
        # The bounded WSGI executor must exist before clients are accepted so early
        # requests never fall through to asyncio's default executor.
        executor = ThreadPoolExecutor(max_workers=self.config.threads, thread_name_prefix="pyserve-wsgi")
        self._executor = executor
        listener = create_listening_socket(self.config)
        server = await asyncio.start_server(
            self._handle_client,
            sock=listener,
            backlog=self.config.backlog,
            limit=self.config.max_header_size + len(HEADER_END),
        )
        self.ready_event.set()
        LOGGER.info("serving on %s:%s with asyncio model", self.config.effective_host, self.config.effective_port)

        try:
            async with server:
                while not self.stop_event.is_set():
                    await asyncio.sleep(0.1)
                server.close()
                await server.wait_closed()
        finally:
            executor.shutdown(wait=True)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        requests_handled = 0
        peer = writer.get_extra_info("peername") or ("", 0)
        remote_addr = str(peer[0]) if len(peer) >= 2 else ""
        self.stats.connection_opened()

        try:
            while requests_handled < self.config.max_keep_alive_requests:
                try:
                    request = await self._read_request(reader, writer, requests_handled)
                except RequestTimeout as exc:
                    await self._write_error(writer, exc, remote_addr)
                    break
                except EOFError:
                    break
                except HTTPError as exc:
                    await self._write_error(writer, exc, remote_addr)
                    break

                # Timing starts after the request is fully read so it reflects server work.
                started = time.monotonic()
                if len(peer) >= 2:
                    request.remote_addr = str(peer[0])
                    request.remote_port = int(peer[1])

                requests_handled += 1
                response = await self._response_for_request(request)
                keep_alive = should_keep_alive(request, requests_handled, self.config)
                try:
                    await self._write_response(writer, response, request.method, keep_alive)
                except RequestTimeout as exc:
                    if not exc.request_method:
                        exc.request_method = request.method
                        exc.raw_target = request.raw_target
                        exc.http_version = request.http_version
                    await self._write_error(writer, exc, remote_addr)
                    break
                elapsed = time.monotonic() - started
                log_access(self.config, request, response.status_code, len(response.body), elapsed)
                self.stats.record(response.status_code, elapsed)
                if not keep_alive:
                    break
        finally:
            self.stats.connection_closed()
            writer.close()
            await writer.wait_closed()

    async def _read_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        requests_handled: int,
    ) -> Request:
        timeout = self.config.keep_alive_timeout if requests_handled else self.config.read_timeout
        try:
            head_with_delimiter = await asyncio.wait_for(reader.readuntil(HEADER_END), timeout=timeout)
        except TimeoutError as exc:
            raise RequestTimeout("timed out while reading request") from exc
        except asyncio.IncompleteReadError as exc:
            if exc.partial:
                raise BadRequest("connection closed before request was complete") from exc
            raise EOFError from exc
        except asyncio.LimitOverrunError as exc:
            raise HeaderTooLarge("request headers exceed configured limit") from exc

        head = head_with_delimiter[: -len(HEADER_END)]
        request, content_length = parse_request_head(head, self.config)
        if content_length:
            if expects_continue(request.headers):
                writer.write(CONTINUE_RESPONSE)
                await self._drain_with_timeout(writer)
            try:
                request.body = await asyncio.wait_for(
                    reader.readexactly(content_length), timeout=self.config.read_timeout
                )
            except TimeoutError as exc:
                raise RequestTimeout("timed out while reading request body") from exc
            except asyncio.IncompleteReadError as exc:
                raise BadRequest("request body is shorter than Content-Length") from exc
        return request

    async def _write_error(self, writer: asyncio.StreamWriter, exc: HTTPError, remote_addr: str) -> None:
        # exc.request_method is None until the request line is parsed, so a body is fine
        # before that; a failed HEAD (method already parsed) gets a bodyless error.
        started = time.monotonic()
        method = exc.request_method or "GET"
        error = error_response(exc.status_code, exc.public_message)
        try:
            await self._write_response(writer, error, method, False)
        except RequestTimeout:
            return
        elapsed = time.monotonic() - started
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

    async def _drain_with_timeout(self, writer: asyncio.StreamWriter) -> None:
        try:
            await asyncio.wait_for(writer.drain(), timeout=self.config.write_timeout)
        except TimeoutError as exc:
            raise RequestTimeout("timed out while writing response") from exc

    async def _response_for_request(self, request: Request) -> Response:
        if request.method not in ALLOWED_METHODS:
            return method_not_allowed_response()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, partial(run_wsgi_app, self.app, request, self.config))

    async def _write_response(
        self,
        writer: asyncio.StreamWriter,
        response: Response,
        request_method: str,
        keep_alive: bool,
    ) -> None:
        writer.write(serialize_response(response, request_method, keep_alive, self.config.server_header))
        await self._drain_with_timeout(writer)
