""" Middleware module for the pyserve project """

from __future__ import annotations

import json
import mimetypes
import os
from datetime import UTC, datetime
from email.utils import formatdate, parsedate_to_datetime
from typing import TYPE_CHECKING

from pyserve.config import WSGIApplication

if TYPE_CHECKING:
    from pyserve.observability.stats import ServerStats


def wrap_stats_endpoint(app: WSGIApplication, stats: ServerStats, path: str) -> WSGIApplication:
    if not path.startswith("/"):
        path = f"/{path}"

    def middleware(environ, start_response):
        if environ.get("PATH_INFO") == path and environ.get("REQUEST_METHOD") == "GET":
            body = json.dumps(stats.snapshot(), sort_keys=True).encode("ascii")
            start_response(
                "200 OK",
                [("Content-Type", "application/json"), ("Content-Length", str(len(body)))],
            )
            return [body]
        return app(environ, start_response)

    return middleware


def _safe_join(root: str, relative: str) -> str | None:
    root_abs = os.path.abspath(root)
    candidate = os.path.abspath(os.path.join(root_abs, relative))
    if candidate == root_abs or candidate.startswith(root_abs + os.sep):
        return candidate
    return None


def wrap_static_files(
    app: WSGIApplication,
    root: str,
    url_prefix: str = "/static",
) -> WSGIApplication:
    prefix = url_prefix.rstrip("/") or "/static"

    def middleware(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        if method not in {"GET", "HEAD"}:
            return app(environ, start_response)

        path = environ.get("PATH_INFO", "")
        if path != prefix and not path.startswith(prefix + "/"):
            return app(environ, start_response)

        relative = path[len(prefix) :].lstrip("/")
        if not relative:
            return app(environ, start_response)

        file_path = _safe_join(root, relative)
        if file_path is None or not os.path.isfile(file_path):
            return app(environ, start_response)

        stat = os.stat(file_path)
        last_modified = formatdate(stat.st_mtime, usegmt=True)
        if_none_match = environ.get("HTTP_IF_MODIFIED_SINCE")
        if if_none_match:
            try:
                client_time = parsedate_to_datetime(if_none_match)
                if client_time.tzinfo is None:
                    client_time = client_time.replace(tzinfo=UTC)
                file_time = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                if int(client_time.timestamp()) >= int(file_time.timestamp()):
                    start_response("304 Not Modified", [("Date", formatdate(usegmt=True))])
                    return []
            except (TypeError, ValueError, OSError):
                pass

        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        with open(file_path, "rb") as handle:
            body = handle.read()

        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Last-Modified", last_modified),
        ]
        start_response("200 OK", headers)
        if method == "HEAD":
            return []
        return [body]

    return middleware


def apply_middleware(app: WSGIApplication, config, stats: ServerStats | None = None) -> WSGIApplication:
    if config.static_root:
        app = wrap_static_files(app, config.static_root, config.static_url_prefix)
    if config.stats_path and stats is not None:
        app = wrap_stats_endpoint(app, stats, config.stats_path)
    return app
