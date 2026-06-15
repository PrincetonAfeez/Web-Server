# Architecture Decision Record
## App — Web Server
**HTTP Runtime Systems Group | Document 1 of 5**
**Status: Accepted**

---

## Context

The HTTP Runtime Systems group requires an educational HTTP/1.1 WSGI server that makes the path between a TCP socket and a Python WSGI application visible. The project is not intended to replace nginx, Apache, Gunicorn, uWSGI, or Uvicorn. Its purpose is to show, in readable Python, how an HTTP server accepts connections, reads byte streams, parses HTTP requests, constructs a WSGI `environ`, runs an application callable, serializes responses, handles keep-alive, records access/stats, and supports multiple concurrency models.

The selected architecture is a Python package named `pyserve` with both a command-line interface and an importable `WSGIServer` class. The design separates transport, HTTP parsing/serialization, WSGI adaptation, middleware, observability, and concurrency models.

---

## Decisions

### Decision 1 — Build an educational raw-socket HTTP/1.1 server

**Chosen:** Implement the socket listener, request parsing, response serialization, and WSGI bridge directly in Python.

**Rejected:** Wrapping Gunicorn, `wsgiref.simple_server`, `http.server`, or a production web server.

**Reason:** The capstone goal is to demonstrate what happens between TCP and a Django-style view callable. Using an existing server would hide the core learning objective.

---

### Decision 2 — Support only HTTP/1.1

**Chosen:** The parser accepts HTTP/1.1 and rejects unsupported versions.

**Rejected:** Supporting HTTP/1.0, HTTP/2, HTTP/3, or WebSockets.

**Reason:** HTTP/1.1 is enough to demonstrate request lines, Host headers, headers, bodies, keep-alive, and WSGI. HTTP/2+ and WebSockets require substantially different protocol machinery and are out of scope.

---

### Decision 3 — Require Host and reject duplicate Host headers

**Chosen:** HTTP/1.1 requests must include exactly one Host header.

**Rejected:** Accepting missing or duplicate Host headers.

**Reason:** Host is required for HTTP/1.1 origin servers. Duplicate Host headers can create ambiguity and request-smuggling risk.

---

### Decision 4 — Enforce parser limits

**Chosen:** Configurable limits exist for request line size, header size, header count, body size, read timeout, write timeout, keep-alive timeout, and requests per connection.

**Rejected:** Reading unbounded request data.

**Reason:** Even an educational server must not consume unlimited memory or wait forever on slow clients.

---

### Decision 5 — Reject unsupported Transfer-Encoding

**Chosen:** Transfer-Encoding values other than identity are outside scope and rejected.

**Rejected:** Implementing chunked request bodies.

**Reason:** Chunked transfer parsing is a meaningful protocol feature, but adding it would increase complexity beyond the WSGI/server-boundary focus of this version.

---

### Decision 6 — Implement `Expect: 100-continue` in the connection layer

**Chosen:** The parser recognizes `Expect: 100-continue`, but the connection layer owns writing the interim `100 Continue` response.

**Rejected:** Letting the parser write to the socket.

**Reason:** Parsing should remain pure. Socket writes belong to the transport/connection layer.

---

### Decision 7 — Share dispatch policy across concurrency models

**Chosen:** Serial, threaded, and asyncio servers share the same request parsing, dispatch, WSGI adapter, response serialization, keep-alive policy, stats, and logging behavior.

**Rejected:** Duplicating HTTP behavior in each concurrency implementation.

**Reason:** The project compares concurrency models, not protocol semantics. Only the transport/concurrency mechanism should vary.

---

### Decision 8 — Run WSGI apps in a bounded executor in async mode

**Chosen:** The asyncio model accepts clients asynchronously, but WSGI app execution runs in a bounded thread pool.

**Rejected:** Running synchronous WSGI apps directly in the event loop.

**Reason:** WSGI applications are synchronous. Running them on the event loop would block all other async connections.

---

### Decision 9 — Serialize server-owned headers authoritatively

**Chosen:** The response serializer owns `Date`, `Server`, `Connection`, and `Content-Length`, dropping app-supplied duplicates for those names.

**Rejected:** Passing those headers through from the WSGI app unchanged.

**Reason:** These headers reflect the final serialized response. The server is the only component that knows whether a body will be sent, whether the connection will stay alive, and what the exact body length is.

---

### Decision 10 — Respect HEAD and no-body statuses

**Chosen:** The serializer suppresses bodies for HEAD responses, 1xx, 204, and 304 statuses.

**Rejected:** Sending the response body exactly as the WSGI app produced it for every method/status.

**Reason:** HTTP method and status semantics require body suppression in these cases.

---

### Decision 11 — Build a PEP 3333 WSGI adapter

**Chosen:** Convert parsed requests into WSGI `environ`, implement `start_response`, collect bytes from the iterable, and close returned iterables when applicable.

**Rejected:** Passing the raw socket/request object to applications.

**Reason:** WSGI is the intended learning boundary between low-level HTTP servers and Python web applications.

---

### Decision 12 — Drop underscored request headers from WSGI environ

**Chosen:** Header names containing underscores are not mapped into `HTTP_*` environ variables.

**Rejected:** Mapping every header directly.

**Reason:** Dashes and underscores collapse to the same CGI variable name. Dropping underscored headers prevents spoofing a trusted dashed header.

---

### Decision 13 — Provide optional middleware for stats and static files

**Chosen:** Middleware can expose a JSON stats endpoint and serve static files with Last-Modified / 304 behavior.

**Rejected:** Baking these features into the core WSGI adapter.

**Reason:** Static files and stats are useful demos, but they are not the core HTTP-to-WSGI boundary. Middleware keeps them optional.

---

### Decision 14 — Keep production non-goals explicit

**Chosen:** TLS, HTTP/2+, WebSockets, reverse proxying, chunked transfer, advanced hardening, and production deployment guarantees are out of scope.

**Rejected:** Presenting the project as production-ready.

**Reason:** Honesty matters. The server is a portfolio/capstone artifact showing understanding, not a replacement for mature servers.

---

## Consequences

**Positive:**
- The TCP → HTTP → WSGI pipeline is visible.
- The parser is testable independently from sockets.
- The WSGI adapter is testable independently from transport.
- Serial, threaded, and async models can be compared fairly.
- Keep-alive, stats, access logs, and static middleware demonstrate realistic server concerns.
- Strict limits and error mapping make the server safer for local demos.

**Negative / Trade-offs:**
- No TLS termination.
- No HTTP/2 or WebSockets.
- No reverse proxy behavior.
- No chunked request body support.
- Threaded model can experience head-of-line blocking when keep-alive clients occupy workers.
- Async model still needs threads for synchronous WSGI apps.
- Static file support is demo-grade, not production CDN/server behavior.

---

## Alternatives Not Explored

- Building on `http.server`.
- Building on `wsgiref.simple_server` as the main server.
- ASGI support.
- HTTP/2 support.
- TLS termination.
- Chunked transfer coding.
- Multipart parsing.
- Reverse proxy features.
- Production worker supervisor.
- Zero-copy sendfile static serving.

---

*Constitution reference: Article 1 (Python fundamentals and architectural thinking), Article 3.3 (scope discipline), Article 4 (quality proportional to scope), Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity).*

---


# Technical Design Document
## App — Web Server
**HTTP Runtime Systems Group | Document 2 of 5**

---

## Overview

Web Server is a Python package named `pyserve`. It exposes a CLI command, `pyserve`, and an importable `WSGIServer` class. It runs WSGI applications over a hand-built HTTP/1.1 server implemented on raw sockets.

**Package:** `pyserve`  
**Console script:** `pyserve`  
**Version:** `0.2.1`  
**Python:** `>=3.11`  
**Runtime dependencies:** none required  
**Optional demo dependency:** Django  
**Dev tools:** pytest, pytest-cov, ruff, mypy

---

## System Architecture

```text
TCP client
  │
  ▼
listener socket
  │
  ▼
concurrency model
  ├── serial accept loop
  ├── threaded accept loop + ThreadPoolExecutor
  └── asyncio server + bounded WSGI executor
  │
  ▼
connection handler
  ├── read headers
  ├── parse request line and headers
  ├── optionally send 100 Continue
  ├── read body
  ├── attach remote address
  ├── dispatch to WSGI
  ├── serialize HTTP response
  ├── access log
  ├── stats update
  └── keep-alive or close
```

---

## Module-Level Structure

```text
src/pyserve/
  __init__.py
  config.py
  dispatch.py
  exceptions.py
  models.py
  parsing.py
  server.py

  cli/
    main.py

  concurrency/
    base.py
    serial.py
    threaded.py
    async_model.py

  http/
    headers.py
    request_parser.py
    response.py
    status.py

  observability/
    access_log.py
    stats.py

  transport/
    listener.py
    connection.py

  wsgi/
    adapter.py
    encoding.py
    environ.py
    middleware.py
```

---

## Main Data Structures

### `Request`

```python
@dataclass
class Request:
    method: str
    raw_target: str
    raw_path: str
    path: str
    query_string: str
    http_version: str
    headers: CaseInsensitiveHeaders
    body: bytes = b""
    remote_addr: str = ""
    remote_port: int = 0
```

Represents a parsed HTTP request. `server_protocol` returns the HTTP version.

---

### `CaseInsensitiveHeaders`

A small collection that:
- preserves raw insertion order
- supports case-insensitive lookup
- supports repeated headers through `get_all()`
- exposes raw header pairs for WSGI mapping

---

### `Response`

```python
@dataclass
class Response:
    status_code: int = 200
    reason: str = "OK"
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""
```

Serialized by `serialize_response()` into HTTP/1.1 bytes.

---

### `ServerConfig`

Important fields:
- host / port
- model: `serial`, `threaded`, or `async`
- threads / workers
- backlog
- access logging flags
- parser limits
- read/write/keep-alive timeouts
- max requests per keep-alive connection
- server header
- WSGI flags
- stats path
- static root and URL prefix

Computed:
- `effective_host`
- `effective_port`

---

### `WSGIServer`

Public server facade.

Responsibilities:
- validate concurrency model
- apply middleware
- own `ServerStats`
- select server implementation
- provide `run()`, `serve_forever()`, `start_in_thread()`, `stop()`, and `join()`

---

## Request Parsing

### Request-head parsing

`parse_request_head()` performs:
1. header-size check
2. request-line extraction
3. ASCII request-line decoding
4. method/target/version split
5. HTTP/1.1 enforcement
6. header-count check
7. header line parsing
8. header name validation
9. header value control-character validation
10. Host requirement
11. duplicate Host rejection
12. Expect validation
13. Transfer-Encoding scope check
14. POST Content-Length requirement
15. Content-Length parse and size check
16. target parsing

---

### Content-Length parsing

Rules:
- missing length means 0
- each value must be a non-negative ASCII integer
- duplicate Content-Length values must agree
- value must not exceed max body size

---

### Target parsing

Rules:
- empty target rejected
- `*` accepted as special target
- absolute-form accepted, but authority is ignored for server identity
- origin-form must begin with `/`
- path is percent-decoded for logical path
- raw path is preserved for WSGI `PATH_INFO` conversion

---

## Connection Handling

`ConnectionHandler.handle()` loop:
1. open stats connection
2. read request head
3. if body exists and `Expect: 100-continue`, send `100 Continue`
4. read body
5. attach remote address/port
6. check allowed method
7. run WSGI app
8. determine keep-alive
9. serialize response
10. write all bytes
11. log access
12. record stats
13. continue until keep-alive cap or close
14. close socket quietly

Allowed methods:
```text
GET, HEAD, POST
```

Unsupported methods return 405 with `Allow: GET, HEAD, POST`.

---

## Keep-Alive Policy

A connection stays open only when:
- request does not include `Connection: close`
- protocol is HTTP/1.1
- keep-alive timeout is greater than zero
- handled request count is below configured maximum

`--benchmark-friendly` disables keep-alive by setting timeout to zero.

---

## Response Serialization

`serialize_response()`:
- verifies body is bytes
- suppresses body for HEAD, 1xx, 204, and 304
- drops app-supplied Date/Server/Connection/Content-Length
- inserts Date and Server
- appends Content-Length when status allows body
- appends Connection close/keep-alive
- encodes status line and headers as Latin-1
- appends body when allowed

---

## WSGI Adapter

### Environ builder

`build_environ()` sets:
- REQUEST_METHOD
- SCRIPT_NAME
- PATH_INFO
- QUERY_STRING
- CONTENT_TYPE
- CONTENT_LENGTH
- SERVER_NAME
- SERVER_PORT
- SERVER_PROTOCOL
- REMOTE_ADDR
- REMOTE_PORT
- wsgi.version
- wsgi.url_scheme
- wsgi.input
- wsgi.errors
- wsgi.multithread
- wsgi.multiprocess
- wsgi.run_once
- HTTP_* request headers

Header mapping rule:
- Content-Type and Content-Length get special WSGI keys.
- headers containing underscores are dropped.
- repeated Cookie headers join with `; `.
- other repeated headers join with `,`.

---

### `StartResponse`

Behavior:
- validates status string
- validates header pairs are strings
- rejects CR/LF in response headers
- prevents duplicate `start_response` calls without `exc_info`
- supports legacy `write(bytes)` callable

---

### Running the app

`run_wsgi_app()`:
1. builds environ
2. calls WSGI app
3. iterates returned iterable
4. requires bytes chunks
5. requires `start_response` to be called
6. prepends `write()` bytes before iterable bytes
7. closes iterable if it has `.close()`
8. returns `Response`
9. converts app/contract exceptions into 500 responses

---

## Concurrency Models

### Serial

- one listener
- accepts one client at a time
- handles connection synchronously
- sets `wsgi_multithread=False`

### Threaded

- one listener
- accepts clients in the main loop
- submits each client to a `ThreadPoolExecutor`
- sets `wsgi_multithread=True`
- known trade-off: keep-alive clients occupy workers

### Asyncio

- uses `asyncio.start_server()` over a prepared listener socket
- reads request headers/body asynchronously
- writes response asynchronously
- runs synchronous WSGI app in bounded thread executor
- sets `wsgi_multithread=True`

---

## Middleware

### Stats endpoint

When `stats_path` is configured, `GET <stats_path>` returns JSON:
- request_count
- active_connections
- status_codes
- average_request_time

### Static files

When `static_root` is configured:
- only GET and HEAD are handled
- path must be under static URL prefix
- safe path join prevents traversal
- content type from mimetypes
- Last-Modified header is set
- If-Modified-Since can produce 304

---

## Configuration Loading

Sources:
- CLI flags
- optional TOML config
- dataclass defaults

TOML behavior:
- unknown config keys are rejected
- `workers` maps to `threads`
- `max_requests_per_connection` maps to `max_keep_alive_requests`
- `benchmark_friendly` sets `keep_alive_timeout` to 0

WSGI app loading:
```text
import.path:callable
```

---

## Observability

### Access logs

Optional access logging supports:
- plain format with elapsed time
- Common Log Format mode
- error-path logging when parser/timeout errors occur

### Stats

`ServerStats` is protected by a lock and tracks:
- total request count
- active connection count
- status-code counts
- total request time
- average request time

---

## Error Handling Strategy

Parser/HTTP errors map to HTTP status codes:
- 400 Bad Request
- 408 Request Timeout
- 413 Payload Too Large
- 414 URI Too Long
- 417 Expectation Failed
- 431 Request Header Fields Too Large
- 505 HTTP Version Not Supported
- 405 Method Not Allowed

WSGI app failures return 500. With debug errors enabled, the response body includes traceback detail.

---

## Verification Summary

The repository configures:
- pytest test path under `tests`
- coverage source `pyserve`
- branch coverage enabled
- coverage fail-under 82
- Ruff linting
- mypy over `src`
- GitHub Actions matrix across Ubuntu/Windows and Python 3.11, 3.12, and 3.13

---

*Constitution reference: Article 4 (engineering quality), Article 6 (behavior verification), Article 7 (progressive complexity), and Article 8 (valid learner work).*

---


# Interface Design Specification
## App — Web Server
**HTTP Runtime Systems Group | Document 3 of 5**

---

## Public CLI Interface

```powershell
pyserve --app import.path:callable [options]
```

Windows fallback:
```powershell
python -m pyserve --app import.path:callable
```

Version:
```powershell
pyserve --version
```

---

## Required Option

| Option | Description |
|---|---|
| `--app` | WSGI application as `import.path:callable` |

Examples:
```powershell
pyserve --app demo.trivial_app:application
pyserve --app demo.django_app:get_wsgi_application --model threaded
```

---

## Server Options

| Option | Default | Description |
|---|---:|---|
| `--host` | `127.0.0.1` | Bind host |
| `--port` | `8000` | Bind port; `0` allowed for ephemeral port |
| `--model` | `serial` | `serial`, `threaded`, or `async` |
| `--workers` / `--threads` | `8` | Thread pool or async WSGI executor size |
| `--backlog` | `128` | Listener backlog |
| `--config` | none | TOML config file |
| `--verbose` | false | Debug-level logging |
| `--log-level` | `INFO` | Logging level |

---

## Safety / Limit Options

| Option | Default |
|---|---:|
| `--max-request-line-size` | `8192` |
| `--max-header-size` | `65536` |
| `--max-header-count` | `100` |
| `--max-body-size` | `1048576` |
| `--read-timeout` | `10.0` |
| `--write-timeout` | `10.0` |
| `--keep-alive-timeout` | `5.0` |
| `--max-requests-per-connection` | `100` |

Validation:
- positive integer required for sizes/counts except port can be zero
- positive floats for read/write timeouts
- non-negative float for keep-alive timeout

---

## Observability / Middleware Options

| Option | Description |
|---|---|
| `--access-log` | Enable access logs |
| `--access-log-clf` | Common Log Format access lines |
| `--stats-path PATH` | Expose JSON stats endpoint |
| `--static PATH` | Serve static files from directory |
| `--static-url-prefix PREFIX` | URL prefix for static middleware |
| `--benchmark-friendly` | Disable keep-alive for benchmark runs |
| `--debug-errors` | Return traceback detail for WSGI failures |

---

## TOML Config Interface

Example:
```toml
app = "demo.trivial_app:application"
host = "127.0.0.1"
port = 8000
model = "threaded"
workers = 8
access_log = true
stats_path = "/_pyserve/stats"
static_root = "demo/public"
```

Notes:
- CLI flags override TOML values.
- unknown keys raise errors.
- `workers` maps to `threads`.
- `benchmark_friendly = true` disables keep-alive.

---

## Public Python Interface

```python
from pyserve import WSGIServer, ServerConfig, ServerStats, load_wsgi_app
```

### `WSGIServer`

```python
server = WSGIServer(application, host="127.0.0.1", port=8000, model="threaded")
server.run()
```

Threaded test helper:
```python
thread = server.start_in_thread()
server.stop()
server.join()
```

Constructor forms:
```python
WSGIServer(app, host="127.0.0.1", port=8000, model="serial", threads=8)
WSGIServer(app, config=ServerConfig(...))
```

Do not pass both `config=` and host/port/model/threads overrides.

---

## Supported HTTP Request Contract

Supported methods:
```text
GET, HEAD, POST
```

Required:
- HTTP/1.1 request line
- Host header
- Content-Length for POST

Rejected:
- missing Host
- duplicate Host
- malformed request line
- non-ASCII request line
- invalid header field name
- control characters in header values
- unsupported HTTP version
- unsupported Transfer-Encoding
- unsupported Expect header
- body larger than configured max
- headers larger than configured max
- too many headers

---

## WSGI Environ Contract

The server provides:
- REQUEST_METHOD
- SCRIPT_NAME
- PATH_INFO
- QUERY_STRING
- CONTENT_TYPE
- CONTENT_LENGTH
- SERVER_NAME
- SERVER_PORT
- SERVER_PROTOCOL
- REMOTE_ADDR
- REMOTE_PORT
- wsgi.version
- wsgi.url_scheme
- wsgi.input
- wsgi.errors
- wsgi.multithread
- wsgi.multiprocess
- wsgi.run_once
- HTTP_* headers

Header mapping rules:
- Content-Type and Content-Length are special-cased.
- Headers containing `_` are dropped.
- repeated Cookie headers join with `; `.
- other repeated headers join with `,`.

---

## WSGI Application Contract

Application must:
- be callable
- accept `(environ, start_response)`
- call `start_response(status, headers)`
- return an iterable of bytes
- yield only bytes
- avoid CR/LF in response header names/values

The server supports the legacy `write(bytes)` callable returned by `start_response`.

---

## Response Contract

Server-owned headers:
- Date
- Server
- Content-Length
- Connection

Body suppression:
- HEAD responses send no body
- 1xx, 204, and 304 send no body

Keep-alive:
- `Connection: keep-alive` when policy allows another request
- `Connection: close` otherwise

---

## Static Files Contract

When enabled:
- only GET/HEAD handled
- request path must match static URL prefix
- path must remain inside static root
- missing files fall through to app
- `If-Modified-Since` can return 304
- HEAD returns headers without body

---

## Stats Endpoint Contract

When `--stats-path /_pyserve/stats` is enabled:

```powershell
curl http://127.0.0.1:8000/_pyserve/stats
```

Returns JSON:
```json
{
  "active_connections": 0,
  "average_request_time": 0.001,
  "request_count": 10,
  "status_codes": {"200": 10}
}
```

---

## CLI Exit Codes

| Code | Meaning |
|---:|---|
| `0` | Success / clean shutdown |
| `2` | argparse usage error |
| `3` | WSGI app load failed |

Runtime bind errors and other uncaught server failures propagate as process errors.

---

## Side Effects

| Operation | Side Effect |
|---|---|
| `pyserve` | Binds host/port and accepts TCP clients |
| `--static` | Reads files from static root |
| `--stats-path` | Exposes in-memory server stats |
| `--access-log` | Writes access log lines through logging |
| `--debug-errors` | May expose traceback in HTTP response |
| `start_in_thread()` | Starts server in daemon thread |

---

*Constitution reference: Article 4 (input/output boundaries), Article 6 (verification), and Article 8 (understandable and verifiable work).*

---


# Runbook
## App — Web Server
**HTTP Runtime Systems Group | Document 4 of 5**

---

## Requirements

### Runtime

- Python 3.11+
- No required runtime dependencies

### Optional

- Django for demo proof

### Development

- pytest
- pytest-cov
- ruff
- mypy

---

## Installation

```powershell
python -m pip install -r requirements-all.txt -c constraints.txt
```

Editable install:
```powershell
python -m pip install -e .
```

Development install:
```powershell
python -m pip install -e ".[dev]"
```

---

## First Smoke Test

```powershell
pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model serial
```

In another terminal:
```powershell
curl -i http://127.0.0.1:8000/
```

Expected:
- HTTP/1.1 response
- Server header showing pyserve
- body from demo app

Windows fallback:
```powershell
python -m pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000
```

---

## Standard Operating Procedures

### Run serial model

```powershell
pyserve --app demo.trivial_app:application --model serial
```

Use for explaining the simplest accept/handle loop.

---

### Run threaded model

```powershell
pyserve --app demo.trivial_app:application --model threaded --workers 8
```

Use for showing concurrent clients through `ThreadPoolExecutor`.

---

### Run async model

```powershell
pyserve --app demo.trivial_app:application --model async --workers 8
```

Use for showing async accept/read/write plus bounded WSGI executor.

---

### Enable access logs

```powershell
pyserve --app demo.trivial_app:application --access-log
```

Common Log Format:
```powershell
pyserve --app demo.trivial_app:application --access-log --access-log-clf
```

---

### Enable stats endpoint

```powershell
pyserve --app demo.trivial_app:application --stats-path /_pyserve/stats
curl http://127.0.0.1:8000/_pyserve/stats
```

---

### Serve static files

```powershell
pyserve --app demo.trivial_app:application --static demo/public --static-url-prefix /static
curl -i http://127.0.0.1:8000/static/example.txt
```

---

### Benchmark-friendly mode

```powershell
pyserve --app demo.trivial_app:application --benchmark-friendly
```

Effect:
- disables keep-alive so benchmark requests do not reuse connections

---

### Use TOML config

```powershell
pyserve --config serve.toml --app demo.trivial_app:application
```

If `serve.toml` includes an `app` key, still pass `--app` because the CLI currently requires it.

---

## Quality Checks

### Tests

```powershell
python -m pytest
```

### Coverage

```powershell
python -m pytest --cov=pyserve --cov-report=term-missing
```

### Lint

```powershell
ruff check src tests
```

### Type-check

```powershell
mypy src
```

---

## CI Parity

The CI workflow runs:
- Ubuntu latest
- Windows latest
- Python 3.11, 3.12, 3.13
- locked toolchain install
- Ruff lint
- mypy
- pytest with coverage

---

## Health Checks

### Package import

```powershell
python -c "from pyserve import WSGIServer, ServerConfig; print('ok')"
```

Expected:
```text
ok
```

---

### CLI app loading failure

```powershell
pyserve --app missing.module:application
```

Expected:
- stderr: app could not load
- exit code 3

---

### Host header enforcement

```powershell
printf 'GET / HTTP/1.1\r\n\r\n' | nc 127.0.0.1 8000
```

Expected:
- 400 Bad Request

---

### HEAD handling

```powershell
curl -I http://127.0.0.1:8000/
```

Expected:
- headers only
- no body

---

### Keep-alive cap

Use a client that sends repeated HTTP/1.1 requests on one connection.

Expected:
- connection closes after configured max requests or explicit `Connection: close`

---

## Expected Failure Modes

### Bind failure

Cause:
- port already in use
- permission denied

Fix:
```powershell
pyserve --app demo.trivial_app:application --port 0
```

or choose another port.

---

### Request header too large

Cause:
- headers exceed `max_header_size`

Response:
```text
431 Request Header Fields Too Large
```

---

### Too many headers

Cause:
- header count exceeds `max_header_count`

Response:
```text
431 Request Header Fields Too Large
```

---

### Body too large

Cause:
- Content-Length exceeds `max_body_size`

Response:
```text
413 Payload Too Large
```

---

### Unsupported HTTP version

Cause:
- request uses HTTP/1.0 or another version

Response:
```text
505 HTTP Version Not Supported
```

---

### Unsupported method

Cause:
- method outside GET/HEAD/POST

Response:
```text
405 Method Not Allowed
Allow: GET, HEAD, POST
```

---

### WSGI app error

Cause:
- app raises or violates WSGI contract

Response:
```text
500 Internal Server Error
```

With `--debug-errors`, traceback detail may be returned in the response.

---

## Troubleshooting Decision Tree

```text
Server will not start
  ├── App import failed?
  │     └── check --app import.path:callable
  ├── Port in use?
  │     └── change --port or use --port 0
  ├── Bad config key?
  │     └── remove unknown TOML key
  └── Bad option value?
        └── check positive int/float validators

Request fails
  ├── 400?
  │     └── inspect request line, Host, headers, Content-Length
  ├── 413?
  │     └── raise --max-body-size or reduce body
  ├── 414?
  │     └── reduce target length or raise max request line size
  ├── 431?
  │     └── reduce header size/count
  ├── 505?
  │     └── send HTTP/1.1
  └── 500?
        └── inspect WSGI app error stream or use --debug-errors locally

Concurrency concern
  ├── Threaded workers blocked?
  │     └── reduce keep-alive or increase workers
  ├── Async still blocked?
  │     └── remember WSGI app runs in thread pool
  └── Benchmark inconsistent?
        └── use --benchmark-friendly
```

---

## Maintenance Notes

- Keep parser, serializer, and WSGI adapter separate.
- Add tests before changing HTTP parsing behavior.
- Preserve Host/Content-Length/Transfer-Encoding safety checks.
- Preserve HEAD/no-body status semantics.
- Keep serial/threaded/async dispatch behavior aligned.
- Keep WSGI app execution out of the asyncio event loop.
- Avoid production claims unless TLS, hardening, proxying, lifecycle, and worker management are added.
- Preserve public `WSGIServer` and CLI behavior.

---

*Constitution reference: Article 6 (behavior verification), Article 5 (constraints and trade-offs), and Article 8 (verifiable learner work).*

---


# Lessons Learned
## App — Web Server
**HTTP Runtime Systems Group | Document 5 of 5**

---

## Why This Design Was Chosen

This design was chosen because the goal is not to create the next production Python web server. The goal is to show that the author understands the machinery behind one. A real WSGI server sits between raw TCP bytes and a Python application callable. This project makes that boundary concrete.

The architecture splits the problem into layers: listener, connection handler, HTTP parser, response serializer, WSGI environ builder, WSGI adapter, middleware, stats, and concurrency models. That separation makes the code easier to reason about and easier to defend in a capstone review.

The three concurrency models are especially valuable. Serial mode shows the simplest path. Threaded mode shows common blocking-concurrency behavior. Async mode shows how an event loop can own I/O while synchronous WSGI work still needs a bounded executor.

---

## What Was Intentionally Omitted

**TLS:** Out of scope because TLS termination adds certificate management, handshake policy, ciphers, and deployment concerns.

**HTTP/2 and HTTP/3:** Out of scope because they are different protocols, not just parser extensions.

**WebSockets:** Out of scope because WSGI is request/response, not bidirectional streaming.

**Reverse proxying:** Out of scope because proxy behavior introduces upstream connection management and header trust policy.

**Chunked transfer:** Deferred because the current version focuses on Content-Length request bodies.

**Production hardening:** Mature servers handle many edge cases this project intentionally documents as non-goals.

---

## Biggest Weakness

The biggest weakness is that the server is educational rather than production-hardened. It handles important HTTP/1.1 fundamentals, but real deployment would require TLS termination, process supervision, stronger timeout/backpressure controls, better static file serving, reverse proxy compatibility, slow-client protections, graceful reload, structured logging, and extensive interoperability testing.

The second weakness is the threaded keep-alive trade-off. A keep-alive connection occupies a worker for its lifetime, so a full thread pool can block new clients. This is acceptable for teaching but important to mention.

The third weakness is that the async model still depends on a thread pool for WSGI. That is not a flaw in the implementation; it is a consequence of WSGI being synchronous.

---

## Scaling Considerations

**If this became production-oriented:**
- add TLS support or document running behind a TLS proxy
- implement graceful shutdown/reload
- add request queue limits and backpressure
- add stronger slowloris protections
- add structured logs and metrics export
- add process supervision and worker management
- add proxy-header trust configuration
- expand HTTP interoperability testing

**If serving large files:**
- add streaming file responses
- add sendfile where available
- avoid reading full static files into memory
- add ETag and cache-control policy

**If ASGI support is needed:**
- create a separate ASGI adapter
- avoid mixing WSGI and ASGI semantics in one path
- revisit async model around native coroutine apps

---

## What the Next Refactor Would Be

1. **Streaming response support** — avoid buffering the entire WSGI response body before serialization.

2. **Chunked request support** — parse chunked request bodies with strict limits.

3. **Better shutdown semantics** — graceful draining of open connections.

4. **Request queue limits** — prevent unbounded accepted-client queueing in threaded mode.

5. **Expanded compliance tests** — compare behavior against more HTTP edge cases.

---

## What This Project Taught

- **HTTP is a byte protocol first.** Request lines, CRLF separators, headers, body lengths, and status lines must be exact.

- **WSGI is a boundary contract.** The server must translate HTTP into a very specific Python dictionary and callable pattern.

- **Concurrency does not change protocol semantics.** Serial, threaded, and async models should agree on parsing, dispatch, response serialization, and errors.

- **Keep-alive is deceptively complex.** It affects timeouts, worker occupancy, connection lifecycle, and response headers.

- **HEAD and no-body statuses matter.** Correct response serialization requires method/status awareness.

- **Safety limits are architecture.** Header limits, body limits, timeouts, and unsupported transfer rejection are core behavior, not extras.

- **Mature servers are mature for a reason.** Building a focused subset makes the value of Gunicorn, uWSGI, nginx, and Apache more understandable.

---

*Constitution v2.0 checklist: This document satisfies Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity) for Web Server.*
