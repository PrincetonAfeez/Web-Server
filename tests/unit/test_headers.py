""" Test headers """

from __future__ import annotations

from pyserve.http.headers import CaseInsensitiveHeaders


def test_headers_are_case_insensitive_and_preserve_duplicates():
    headers = CaseInsensitiveHeaders()
    headers.add("X-Test", "one")
    headers.add("x-test", "two")

    assert headers["X-TEST"] == "two"
    assert headers.get_all("x-test") == ["one", "two"]
    assert headers.raw_items() == [("X-Test", "one"), ("x-test", "two")]


def test_normalize_lowercases_header_names():
    assert CaseInsensitiveHeaders.normalize("X-Custom-Header") == "x-custom-header"


def test_get_returns_default_when_missing():
    headers = CaseInsensitiveHeaders()

    assert headers.get("missing") is None
    assert headers.get("missing", "fallback") == "fallback"


def test_contains_is_case_insensitive():
    headers = CaseInsensitiveHeaders([("Host", "localhost")])

    assert "host" in headers
    assert "HOST" in headers
    assert "missing" not in headers
    assert 123 not in headers


def test_getitem_raises_key_error_for_missing_header():
    headers = CaseInsensitiveHeaders()

    try:
        headers["missing"]
    except KeyError as exc:
        assert str(exc) == "'missing'"
    else:
        raise AssertionError("expected KeyError")


def test_iter_and_len_expose_all_header_pairs():
    headers = CaseInsensitiveHeaders([("A", "1"), ("B", "2")])

    assert list(headers) == [("A", "1"), ("B", "2")]
    assert len(headers) == 2


def test_repr_includes_items():
    headers = CaseInsensitiveHeaders([("Host", "localhost")])

    assert repr(headers) == "CaseInsensitiveHeaders([('Host', 'localhost')])"


def test_constructor_accepts_initial_items():
    headers = CaseInsensitiveHeaders([("X-One", "a"), ("X-Two", "b")])

    assert headers.get_all("x-one") == ["a"]
    assert headers.get_all("x-two") == ["b"]

