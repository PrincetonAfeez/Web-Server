""" Test middleware """

from __future__ import annotations

import json
from pathlib import Path

from pyserve.config import load_toml_config, server_config_from_mapping
from pyserve.observability.stats import ServerStats
from pyserve.wsgi.middleware import wrap_static_files, wrap_stats_endpoint


def test_load_toml_config_reads_values(tmp_path: Path):
    config_file = tmp_path / "serve.toml"
    config_file.write_text('host = "0.0.0.0"\nport = 9000\nmodel = "threaded"\n', encoding="utf-8")

    data = load_toml_config(config_file)

    assert data["host"] == "0.0.0.0"
    assert data["port"] == 9000


def test_server_config_from_mapping_supports_aliases():
    config = server_config_from_mapping(
        {
            "workers": 3,
            "max_requests_per_connection": 5,
            "benchmark_friendly": True,
            "stats_path": "/_pyserve/stats",
        }
    )

    assert config.threads == 3
    assert config.max_keep_alive_requests == 5
    assert config.keep_alive_timeout == 0.0
    assert config.stats_path == "/_pyserve/stats"


def test_stats_endpoint_returns_json_snapshot():
    stats = ServerStats()
    stats.record(200, 0.01)

    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"app"]

    wrapped = wrap_stats_endpoint(app, stats, "/_pyserve/stats")
    body = b"".join(
        wrapped(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/_pyserve/stats"},
            lambda status, headers, exc_info=None: None,
        )
    )

    payload = json.loads(body.decode())
    assert payload["request_count"] == 1


def test_static_middleware_serves_file(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()
    (root / "hello.txt").write_text("hello", encoding="utf-8")

    def app(environ, start_response):
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"missing"]

    wrapped = wrap_static_files(app, str(root), "/static")
    chunks = wrapped(
        {"REQUEST_METHOD": "GET", "PATH_INFO": "/static/hello.txt"},
        lambda status, headers, exc_info=None: None,
    )

    assert b"".join(chunks) == b"hello"


def test_static_middleware_returns_304_when_unmodified(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()
    file_path = root / "hello.txt"
    file_path.write_text("hello", encoding="utf-8")
    stat = file_path.stat()
    from email.utils import formatdate

    modified = formatdate(stat.st_mtime, usegmt=True)

    def app(environ, start_response):
        raise AssertionError("app should not run")

    wrapped = wrap_static_files(app, str(root), "/static")
    captured: dict[str, object] = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = headers

    wrapped(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/static/hello.txt",
            "HTTP_IF_MODIFIED_SINCE": modified,
        },
        start_response,
    )

    assert captured["status"] == "304 Not Modified"


def test_apply_middleware_composes_static_and_stats(tmp_path: Path):
    from pyserve.config import ServerConfig
    from pyserve.wsgi.middleware import apply_middleware

    root = tmp_path / "public"
    root.mkdir()
    (root / "file.txt").write_text("static", encoding="utf-8")

    stats = ServerStats()
    config = ServerConfig(static_root=str(root), static_url_prefix="/static", stats_path="/stats")

    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"app"]

    wrapped = apply_middleware(app, config, stats)

    static_chunks = wrapped(
        {"REQUEST_METHOD": "GET", "PATH_INFO": "/static/file.txt"},
        lambda status, headers, exc_info=None: None,
    )
    assert b"".join(static_chunks) == b"static"

    stats.record(201, 0.02)
    stats_body = b"".join(
        wrapped(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/stats"},
            lambda status, headers, exc_info=None: None,
        )
    )
    payload = json.loads(stats_body.decode())
    assert payload["request_count"] == 1


def test_stats_endpoint_normalizes_path_without_leading_slash():
    stats = ServerStats()

    def app(environ, start_response):
        raise AssertionError("app should not run")

    wrapped = wrap_stats_endpoint(app, stats, "_pyserve/stats")
    body = b"".join(
        wrapped(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/_pyserve/stats"},
            lambda status, headers, exc_info=None: None,
        )
    )

    assert json.loads(body.decode())["request_count"] == 0


def test_static_middleware_head_returns_no_body(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()
    (root / "hello.txt").write_text("hello", encoding="utf-8")

    def app(environ, start_response):
        raise AssertionError("app should not run")

    wrapped = wrap_static_files(app, str(root), "/static")
    chunks = wrapped(
        {"REQUEST_METHOD": "HEAD", "PATH_INFO": "/static/hello.txt"},
        lambda status, headers, exc_info=None: None,
    )

    assert chunks == []


def test_static_middleware_blocks_path_traversal(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

    def app(environ, start_response):
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"missing"]

    wrapped = wrap_static_files(app, str(root), "/static")
    chunks = wrapped(
        {"REQUEST_METHOD": "GET", "PATH_INFO": "/static/../secret.txt"},
        lambda status, headers, exc_info=None: None,
    )

    assert b"".join(chunks) == b"missing"


def test_static_middleware_passes_through_non_get_methods(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()

    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"app"]

    wrapped = wrap_static_files(app, str(root), "/static")
    chunks = wrapped(
        {"REQUEST_METHOD": "POST", "PATH_INFO": "/static/missing.txt"},
        lambda status, headers, exc_info=None: None,
    )

    assert b"".join(chunks) == b"app"


def test_static_middleware_serves_file_when_if_modified_since_is_invalid(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()
    (root / "hello.txt").write_text("hello", encoding="utf-8")

    captured: dict[str, object] = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status

    wrapped = wrap_static_files(lambda e, s: None, str(root), "/static")
    wrapped(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/static/hello.txt",
            "HTTP_IF_MODIFIED_SINCE": "not-a-date",
        },
        start_response,
    )

    assert captured["status"] == "200 OK"


def test_static_middleware_ignores_unrelated_paths(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()

    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"app"]

    wrapped = wrap_static_files(app, str(root), "/static")
    chunks = wrapped(
        {"REQUEST_METHOD": "GET", "PATH_INFO": "/other/file.txt"},
        lambda status, headers, exc_info=None: None,
    )

    assert b"".join(chunks) == b"app"


def test_static_middleware_ignores_prefix_without_file_segment(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()

    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"app"]

    wrapped = wrap_static_files(app, str(root), "/static")
    chunks = wrapped(
        {"REQUEST_METHOD": "GET", "PATH_INFO": "/static"},
        lambda status, headers, exc_info=None: None,
    )

    assert b"".join(chunks) == b"app"


def test_static_middleware_304_handles_naive_if_modified_since(tmp_path: Path, monkeypatch):
    from datetime import UTC, datetime

    root = tmp_path / "public"
    root.mkdir()
    file_path = root / "hello.txt"
    file_path.write_text("hello", encoding="utf-8")

    captured: dict[str, object] = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status

    monkeypatch.setattr(
        "pyserve.wsgi.middleware.parsedate_to_datetime",
        lambda value: datetime(2099, 1, 1, tzinfo=UTC),
    )

    wrapped = wrap_static_files(lambda e, s: None, str(root), "/static")
    wrapped(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/static/hello.txt",
            "HTTP_IF_MODIFIED_SINCE": "Friday, 01-Jan-99 00:00:00 GMT",
        },
        start_response,
    )

    assert captured["status"] == "304 Not Modified"


