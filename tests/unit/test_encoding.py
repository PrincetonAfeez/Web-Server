""" Test encoding """

from __future__ import annotations

from pyserve.wsgi.encoding import path_to_wsgi_string


def test_path_to_wsgi_string_decodes_percent_encoding():
    assert path_to_wsgi_string("/hello%20world") == "/hello world"


def test_path_to_wsgi_string_empty_path():
    assert path_to_wsgi_string("/") == "/"


def test_path_to_wsgi_string_preserves_reserved_characters():
    assert path_to_wsgi_string("/files%2Freadme.txt") == "/files/readme.txt"


def test_path_to_wsgi_string_uses_latin1_for_non_utf8_bytes():
    # %FF is not valid UTF-8 but is valid as a latin-1 byte.
    assert path_to_wsgi_string("/%FF") == "/\xff"
