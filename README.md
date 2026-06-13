# pyserve

`pyserve` is an educational HTTP/1.1 WSGI server built from raw TCP sockets.
It is not trying to replace nginx, gunicorn, uWSGI, uvicorn, or Apache. The
point is to show every layer between a TCP connection and a Python WSGI app.

```text
socket accept
-> recv bytes from TCP
-> parse HTTP/1.1
-> build WSGI environ
-> call the WSGI app
-> serialize HTTP response
-> send bytes back to the socket
```

## Quick Start

Run the demo app from the repository root:

```powershell
python -m pip install -r requirements.txt
pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model serial
```

On Windows, if the generated `pyserve.exe` directory is not on `PATH`, use:

```powershell
python -m pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model serial
```

Then send a request:

```powershell
curl -i http://127.0.0.1:8000/
```

The package also exposes a library API:

```python
from pyserve import WSGIServer
from demo.trivial_app import application

server = WSGIServer(application, host="127.0.0.1", port=8000, model="threaded")
server.run()
```

For background use in tests or embedding:

```python
thread = server.start_in_thread()
# ... exercise server at server.host / server.port ...
server.stop()
server.join()
```

`WSGIServer` can be stopped and started again on the same instance after
`stop()` and `join()` complete. Pass either `config=ServerConfig(...)` or
`host`/`port`/`model`/`threads` keyword arguments, not both.

## CLI Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--app` | (required) | WSGI app as `import.path:callable`. |
| `--host` / `--port` | `127.0.0.1` / `8000` | Bind address. Use `--port 0` for an ephemeral port; the startup banner prints the bound port. |
| `--model` | `serial` | Concurrency model: `serial`, `threaded`, or `async`. |
| `--workers` / `--threads` | `8` | Thread-pool size for the threaded model and for the async model's WSGI executor. Must be at least 1. |
| `--backlog` | `128` | Listen backlog passed to `listen()`. |
| `--max-request-line-size` | `8192` | Maximum request-line bytes (else `414`). |
| `--max-header-size` | `65536` | Maximum total request-header bytes (else `431`). |
| `--max-header-count` | `100` | Maximum number of request header lines (else `431`). |
| `--max-body-size` | `1048576` | Maximum request-body bytes (else `413`). |
| `--read-timeout` | `10.0` | Seconds to wait while reading a request. |
| `--write-timeout` | `10.0` | Seconds to wait while sending a response. |
| `--keep-alive-timeout` | `5.0` | Idle seconds before a kept-alive connection is closed. |
| `--max-requests-per-connection` | `100` | Requests served per connection before closing. Must be at least 1. |
| `--benchmark-friendly` | off | Sets `--keep-alive-timeout 0`, disabling keep-alive so each connection serves one request. Useful for throughput benchmarks. |
| `--access-log` | off | Emit one access-log line per handled request, including parser and protocol errors. |
| `--debug-errors` | off | Return the traceback in `500` response bodies (never use in production). |
| `--verbose` / `--log-level` | off / `INFO` | `--verbose` forces `DEBUG` logging via `configure_application_logging()`; otherwise `--log-level` controls verbosity. Does not enable access logs; use `--access-log` for those. |
| `--version` | — | Print `pyserve <version>` and exit. |

### Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Clean exit, including Ctrl-C shutdown. |
| `2` | Command-line usage error (argparse convention). |
| `3` | The WSGI app named by `--app` could not be imported or is not callable. |

## What Is Implemented

- Raw TCP listener using `socket()`, `bind()`, `listen()`, and `accept()`.
- Manual read loop because TCP is a byte stream, not an HTTP message stream.
- Manual send loop to handle partial `send()` writes.
- HTTP/1.1 request parser for GET, HEAD, and POST.
- Case-insensitive headers with duplicate-header preservation.
- Content-Length request bodies.
- Parser limits for request line, headers, header count, and body size.
- HTTP response serializer with Date, Server, Content-Length, and Connection.
- HEAD, 204, and 304 no-body rules.
- WSGI environ builder with PEP 3333-style variables.
- `start_response`, WSGI write callable, byte chunk validation, and iterable `close()`.
- Serial, threaded, and asyncio transport models sharing one dispatch policy.
- Basic bounded keep-alive.
- `Expect: 100-continue` interim responses before reading a request body.
- Access logging and in-process server stats (request count, status histogram,
  active connections, average request time) wired across all three models.
- CLI and importable `WSGIServer` API (stats exposed as `server.stats`).
- Optional Django proof under `demo/django_demo`.

## Concurrency Models

Serial mode handles one client connection at a time. It is the simplest baseline
and the easiest place to explain the protocol path.

Threaded mode uses a thread pool and handles multiple connections concurrently.
This is a natural fit for synchronous WSGI applications.

Asyncio mode uses `asyncio.start_server` for the socket transport, then runs the
synchronous WSGI app in an executor. WSGI itself remains synchronous; this is
not an ASGI implementation.

## Shutdown

Calling `stop()` sets an internal flag so the accept loop exits on the next
iteration. Active connections may still run until they finish or hit a
keep-alive/read timeout. When using `start_in_thread()`, call `join()` after
`stop()` so callers wait for the server thread to finish.

Idle keep-alive timeouts return `408 Request Timeout` (with an access-log line
when `--access-log` is enabled), matching first-request read timeouts.

## Install

Runtime only (stdlib dependencies; installs pyserve from this repo):

```powershell
python -m pip install -r requirements.txt
```

Full contributor setup (tests, lint, type-check, Django demo):

```powershell
python -m pip install -r requirements-all.txt -c constraints.txt
```

Equivalent pyproject extra:

```powershell
python -m pip install -e ".[dev,demo]" -c constraints.txt
```

| File | Purpose |
| --- | --- |
| `requirements.txt` | Editable install of pyserve |
| `requirements-dev.txt` | Test/lint/type-check toolchain |
| `requirements-demo.txt` | Django demo dependency |
| `requirements-all.txt` | Dev + demo (what CI uses) |
| `constraints.txt` | Pinned versions for reproducible installs |

## Tests

```powershell
python -m pip install -r requirements-all.txt -c constraints.txt
python -m pytest
python -m pytest --cov=pyserve --cov-report=term-missing
```

`constraints.txt` pins the exact test/lint/type-check toolchain that CI uses;
`pyserve` itself has no runtime dependencies beyond the standard library.

The tests cover parser limits, partial reads, response serialization,
`wsgiref.validate`, socket round-trips, keep-alive, and the concurrency models.

## Scope Boundary

The server intentionally does not implement TLS termination, HTTP/2, HTTP/3,
WebSockets, reverse proxy behavior, gzip/br compression, chunked transfer,
production worker management, or production security hardening. Those are
documented tradeoffs, not accidental omissions.

Unsupported HTTP versions (for example `HTTP/1.0`) receive `505 HTTP Version Not
Supported` rather than being silently upgraded. See `docs/adr/0007-http-version-policy.md`.

HTTP/1.1 `POST` requests without a `Content-Length` header are parsed as having
no body; extra bytes can remain in the connection buffer on keep-alive. See
`docs/adr/0005-parser-limits.md`.

## Portfolio Metadata

Before submitting or publishing, personalize:

- `pyproject.toml` → `authors` and `[project.urls]`
- `LICENSE` → copyright holder name
