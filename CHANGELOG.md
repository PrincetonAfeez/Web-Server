# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Async model now returns `400` (not `500`) for truncated requests, matching serial/threaded behavior.
- `WSGIServer` can be stopped and restarted on the same instance after `join()`.
- CLI rejects `--max-requests-per-connection` values below 1.
- CLI startup banner prints the bound address when `--port 0` is used.
- Access logs now include parser and protocol error responses.
- `--verbose` no longer implicitly enables access logging.

### Changed

- Default `Server` header is derived from package version (`pyserve/0.1.0`).
- Unsupported HTTP versions return `505 HTTP Version Not Supported`.
- `WSGIServer` rejects mixing `config=` with `host`/`port`/`model`/`threads`.
- Capstone planning documents moved under `docs/planning/`.

### Added

- `py.typed` marker for type checkers.
- CLI flags for `--backlog`, `--max-request-line-size`, `--max-header-count`,
  `--read-timeout`, and `--write-timeout`.
- Integration tests for server restart, async truncated requests, threaded
  concurrency, error access logs, and Django socket round-trip.
- Windows CI job and pytest coverage reporting (82% threshold).
- `project.urls` metadata in `pyproject.toml`.

## [0.1.0] - 2026-06-11

Initial release.

### Added

- HTTP/1.1 request parser (GET, HEAD, POST) with enforced limits on the request
  line, header size, header count, and body size, and strict rejection of
  malformed input (non-ASCII Content-Length, control characters in header
  values, duplicate `Host` headers).
- WSGI 1.0 (PEP 3333) adapter: environ builder, `start_response` with the
  legacy `write()` callable, iterable `close()`, and validated status/headers.
- Three concurrency models behind one dispatch policy: `serial`, `threaded`
  (thread pool), and `async` (asyncio transport with a bounded WSGI executor).
- Bounded keep-alive with pipelining-safe buffering and `Expect: 100-continue`
  interim responses.
- Access logging and in-process server stats (request count, status histogram,
  active connections, average request time), exposed as `WSGIServer.stats`.
- CLI (`pyserve`, also `python -m pyserve`) with documented flags and exit
  codes, plus an importable `WSGIServer` library API.
- Django demo app proving an unmodified WSGI framework runs on the server.
- Test suite covering parser limits, partial reads/writes, WSGI compliance
  (`wsgiref.validate`), keep-alive, and all three concurrency models.
