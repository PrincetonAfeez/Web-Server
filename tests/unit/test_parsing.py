""" Test parsing """

from __future__ import annotations

from pyserve.parsing import parse_ascii_int


def test_parses_plain_ascii_digits():
    assert parse_ascii_int("0") == 0
    assert parse_ascii_int("8000") == 8000


def test_rejects_non_ascii_numerics():
    assert parse_ascii_int("²") is None  # superscript two: isdigit() but not int()
    assert parse_ascii_int("١٢٣") is None  # arabic-indic digits


def test_rejects_non_numeric_strings():
    assert parse_ascii_int("") is None
    assert parse_ascii_int("12a") is None
    assert parse_ascii_int("-5") is None
    assert parse_ascii_int(" 5 ") is None
