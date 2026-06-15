""" Response module for the pyserve project """

from __future__ import annotations

from dataclasses import dataclass, field
from email.utils import formatdate

from pyserve.config import default_server_header
from pyserve.http.status import reason_phrase


@dataclass
class Response:
    status_code: int = 200
    reason: str = "OK"
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""

    @classmethod
    def from_status(
        cls,
        status_code: int,
        body: bytes = b"",
        headers: list[tuple[str, str]] | None = None,
        reason: str | None = None,
    ) -> Response:
        return cls(status_code, reason or reason_phrase(status_code), headers or [], body)


def serialize_response(
    response: Response,
    request_method: str = "GET",
    keep_alive: bool = False,
    server_header: str | None = None,
) -> bytes:
    if server_header is None:
        server_header = default_server_header()
    body = response.body
    if not isinstance(body, bytes):
        raise TypeError("response body must be bytes")

    no_body_status = response.status_code in {204, 304} or 100 <= response.status_code < 200
    send_body = b"" if request_method.upper() == "HEAD" or no_body_status else body

    headers: list[tuple[str, str]] = []
    # These are computed and owned by the server; any app-supplied copies are
    # dropped here so the serializer's values are authoritative and unduplicated.
    skip = {"date", "server", "connection", "content-length"}
    for name, value in response.headers:
        if name.lower() not in skip:
            headers.append((name, value))

    headers.insert(0, ("Server", server_header))
    headers.insert(0, ("Date", formatdate(usegmt=True)))

    if not no_body_status:
        headers.append(("Content-Length", str(len(body))))
    headers.append(("Connection", "keep-alive" if keep_alive else "close"))

    status_line = f"HTTP/1.1 {response.status_code} {response.reason}\r\n"
    header_lines = "".join(f"{name}: {value}\r\n" for name, value in headers)
    return (status_line + header_lines + "\r\n").encode("latin-1") + send_body


def error_response(
    status_code: int,
    message: str | None = None,
    detail: str | None = None,
) -> Response:
    reason = reason_phrase(status_code)
    text = detail or message or reason
    body = (text.rstrip() + "\n").encode("utf-8")
    return Response.from_status(
        status_code,
        body=body,
        headers=[("Content-Type", "text/plain; charset=utf-8")],
        reason=reason,
    )
