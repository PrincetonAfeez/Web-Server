# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (local submission packaging)

- Benchmark harness (`demo/benchmark.py`) and `docs/benchmark-results.md`
- TOML config (`serve.toml`, `--config`), CLF access logs, static files with `304`
- JSON stats endpoint (`--stats-path`) and Django+HTMX dashboard
- Flask demo app, capstone report, defense Q&A, demo rehearsal, submission checklist
- Normalized ADR 0003 and ADR 0006; polished README landing page

## [0.2.1] - 2026-06-12

### Fixed

- Reject empty `Host` headers with `400 Bad Request`.
- Treat HTTP version tokens case-insensitively and normalize to `HTTP/1.1`.
- Require `Content-Length` on `POST` requests.
- Return `417 Expectation Failed` for unsupported `Expect` values.
- Create the async WSGI executor before accepting connections.
- Build the async listener via `create_listening_socket` for bind parity.

### Changed

- Portfolio metadata points at the `Web-Server` repository.
- ADRs 0001–0005 and the protocol checklist align with async listener behavior.
- Demo script matches README install instructions and documents `error_app`.

### Added

- `docs/adr/README.md` ADR index.
- Unit tests for `dispatch.py` and expanded parser/integration coverage (408 on
  first read, 413/414/417, pipelining, keep-alive limits, IPv6 threaded/async,
  `wsgiref.validate` on all models, parametrized 405).

## [0.2.0] - 2026-06-12

### Fixed

- Success-path write timeouts now return `408` instead of silently closing the
  connection (serial/threaded and async).
- `--verbose` enables `DEBUG` logging through `configure_application_logging()`.
- Async response writes honor `write_timeout` via bounded `drain()` calls.
- Error access logs include parsed `raw_target` and `http_version` when known.
- Idle keep-alive timeouts return `408` and are access-logged.
- Async model returns `400` (not `500`) for truncated requests.
- `WSGIServer` can be stopped and restarted after `join()`.
- CLI startup banner prints the bound address when `--port 0` is used.
- Access logs include parser and protocol error responses.

### Changed

- `serialize_response()` derives its default `Server` header from package version.
- CI installs from `requirements-all.txt`; README Quick Start matches.
- Removed unused `transport/limits.py`.
- CLI rejects invalid size limits, negative ports, and negative keep-alive timeouts.
- `WSGIServer` rejects unknown `model` values at construction time.
- Unsupported HTTP versions return `505 HTTP Version Not Supported`.
- `WSGIServer` rejects mixing `config=` with `host`/`port`/`model`/`threads`.
- ADR 0003 documents keep-alive `408` behavior; ADR 0005 documents bodyless POST.

### Added

- `configure_application_logging()` for CLI and library embedders.
- ADR 0007 for HTTP version policy.
- Requirements files and portfolio metadata guidance.
- `py.typed`, expanded CLI flags, Windows CI, and coverage reporting.
- Integration tests for restart, concurrency, IPv6, Django, `wsgiref.validate`
  round-trips, async/threaded protocol errors, keep-alive `408`, write timeouts,
  and `--debug-errors`.

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
