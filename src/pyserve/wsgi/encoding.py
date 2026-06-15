""" Encoding module for the pyserve project """

from __future__ import annotations

from urllib.parse import unquote_to_bytes


def path_to_wsgi_string(raw_path: str) -> str:
    return unquote_to_bytes(raw_path).decode("latin-1")
