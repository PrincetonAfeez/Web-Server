""" Test status """

from __future__ import annotations

import pytest

from pyserve.http.status import parse_status


def test_parse_status_splits_code_and_reason():
    assert parse_status("404 Not Found") == (404, "Not Found")


def test_parse_status_fills_in_missing_reason():
    assert parse_status("200") == (200, "OK")


def test_parse_status_rejects_non_ascii_digits():
    # "²00" satisfies str.isdigit() but not int(); it must not slip through.
    with pytest.raises(ValueError):
        parse_status("²00 OK")


def test_parse_status_rejects_out_of_range_code():
    with pytest.raises(ValueError):
        parse_status("99 Too Small")


def test_reason_phrase_unknown_code_returns_unknown():
    from pyserve.http.status import reason_phrase

    assert reason_phrase(418) == "Unknown"
    assert reason_phrase(200) == "OK"

