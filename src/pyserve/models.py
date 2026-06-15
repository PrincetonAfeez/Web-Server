""" Models module for the pyserve project """

from __future__ import annotations

from dataclasses import dataclass

from pyserve.http.headers import CaseInsensitiveHeaders


@dataclass
class Request:
    method: str
    raw_target: str
    raw_path: str
    path: str
    query_string: str
    http_version: str
    headers: CaseInsensitiveHeaders
    body: bytes = b""
    remote_addr: str = ""
    remote_port: int = 0

    @property
    def server_protocol(self) -> str:
        return self.http_version
