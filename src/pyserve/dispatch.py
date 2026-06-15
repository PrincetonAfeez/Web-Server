""" Dispatch module for the pyserve project """

from __future__ import annotations

from pyserve.config import ServerConfig
from pyserve.exceptions import MethodNotAllowed
from pyserve.http.response import Response, error_response
from pyserve.models import Request

ALLOWED_METHODS = {"GET", "HEAD", "POST"}
ALLOW_HEADER = "GET, HEAD, POST"


def method_not_allowed_response() -> Response:
    response = error_response(MethodNotAllowed.status_code, MethodNotAllowed.public_message)
    response.headers.append(("Allow", ALLOW_HEADER))
    return response


def should_keep_alive(request: Request, requests_handled: int, config: ServerConfig) -> bool:
    connection = (request.headers.get("connection", "") or "").lower()
    if connection == "close":
        return False
    if request.http_version != "HTTP/1.1":
        return False
    if config.keep_alive_timeout <= 0:
        return False
    return requests_handled < config.max_keep_alive_requests
