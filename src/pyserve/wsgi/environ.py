""" Environment module for the pyserve project """

from __future__ import annotations

import sys
from io import BytesIO

from pyserve.config import ServerConfig
from pyserve.models import Request
from pyserve.parsing import parse_ascii_int
from pyserve.wsgi.encoding import path_to_wsgi_string


def build_environ(request: Request, config: ServerConfig) -> dict[str, object]:
    server_name, server_port = server_from_host_header(request, config)
    environ: dict[str, object] = {
        "REQUEST_METHOD": request.method,
        "SCRIPT_NAME": "",
        "PATH_INFO": path_to_wsgi_string(request.raw_path),
        "QUERY_STRING": request.query_string,
        "CONTENT_TYPE": request.headers.get("content-type", "") or "",
        "CONTENT_LENGTH": request.headers.get("content-length", "") or "",
        "SERVER_NAME": server_name,
        "SERVER_PORT": str(server_port),
        "SERVER_PROTOCOL": request.server_protocol,
        "REMOTE_ADDR": request.remote_addr,
        "REMOTE_PORT": str(request.remote_port) if request.remote_port else "",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": config.url_scheme,
        "wsgi.input": BytesIO(request.body),
        "wsgi.errors": config.error_stream or sys.stderr,
        "wsgi.multithread": config.wsgi_multithread,
        "wsgi.multiprocess": config.wsgi_multiprocess,
        "wsgi.run_once": config.wsgi_run_once,
    }

    for name, value in request.headers.raw_items():
        lower = name.lower()
        if lower in {"content-type", "content-length"}:
            continue
        # Header names with underscores collapse to the same CGI variable as their
        # dashed counterpart (X_Foo and X-Foo both map to HTTP_X_FOO), so dropping
        # them prevents a client from spoofing a trusted dashed header.
        if "_" in name:
            continue
        key = "HTTP_" + name.upper().replace("-", "_")
        if key in environ:
            separator = "; " if key == "HTTP_COOKIE" else ","
            environ[key] = f"{environ[key]}{separator}{value}"
        else:
            environ[key] = value

    return environ


def server_from_host_header(request: Request, config: ServerConfig) -> tuple[str, int]:
    host = request.headers.get("host", "") or ""
    if host.startswith("[") and "]" in host:
        end = host.find("]")
        name = host[1:end]
        remainder = host[end + 1 :]
        if remainder.startswith(":"):
            port = parse_ascii_int(remainder[1:])
            if port is not None:
                return name, port
        return name, config.effective_port

    if ":" in host:
        name, port_text = host.rsplit(":", 1)
        port = parse_ascii_int(port_text)
        if port is not None:
            return name, port
        # Malformed port: keep the host name but fall back to the bound port rather
        # than leaking "host:garbage" into SERVER_NAME.
        return name, config.effective_port

    return host or config.effective_host, config.effective_port
