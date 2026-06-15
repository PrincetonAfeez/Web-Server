""" Parsing module for the pyserve project """

from __future__ import annotations


def parse_ascii_int(value: str) -> int | None:
    """Parse a run of ASCII digits into an int, returning None if it is not one.

    ``str.isdigit`` accepts non-ASCII numerics such as ``"²"`` (superscript two)
    that ``int`` then rejects with ``ValueError``. Any code that validates a string
    with ``isdigit`` and later calls ``int`` on it can be crashed by such input, so
    network-facing parsers must restrict themselves to ASCII ``0``-``9`` first.
    """
    if value.isascii() and value.isdigit():
        return int(value)
    return None
