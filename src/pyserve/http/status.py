""" Status module for the pyserve project """

from __future__ import annotations

from pyserve.parsing import parse_ascii_int

REASON_PHRASES: dict[int, str] = {
    100: "Continue",
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    304: "Not Modified",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    408: "Request Timeout",
    413: "Payload Too Large",
    414: "URI Too Long",
    417: "Expectation Failed",
    431: "Request Header Fields Too Large",
    500: "Internal Server Error",
    505: "HTTP Version Not Supported",
}


def reason_phrase(status_code: int) -> str:
    return REASON_PHRASES.get(status_code, "Unknown")


def parse_status(status: str) -> tuple[int, str]:
    parts = status.split(" ", 1)
    code = parse_ascii_int(parts[0])
    if code is None:
        raise ValueError(f"invalid WSGI status string {status!r}")

    if code < 100 or code > 999:
        raise ValueError(f"invalid WSGI status code {code}")

    reason = parts[1] if len(parts) == 2 else reason_phrase(code)
    return code, reason
