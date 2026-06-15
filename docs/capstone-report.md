# Capstone Report — pyserve

## 1. Problem and goal

Build a Python HTTP/1.1 WSGI server from raw TCP sockets that can run
unmodified WSGI applications, including Django, to demonstrate mastery of the
protocol layers frameworks usually hide.

**Defense sentence:** This project implements everything between the socket and
Django’s view function, by hand, in Python.

## 2. Architecture

Layers (bottom to top):

1. **Transport** — `socket`/`bind`/`listen`/`accept`, partial read/send loops
2. **HTTP** — request parser, response serializer, limits, keep-alive policy
3. **WSGI** — environ, `start_response`, iterable handling, `wsgiref.validate`
4. **Concurrency** — serial, threaded, asyncio (shared dispatch policy)
5. **Interfaces** — CLI and `WSGIServer` library API

See `docs/adr/README.md` for decision records.

## 3. Protocol mastery

- TCP treated as a byte stream; headers read until `CRLF CRLF`
- Content-Length bodies; POST without `Content-Length` rejected
- Parser limits → 400/413/414/431/505/417 as appropriate
- Keep-alive bounded by idle timeout (`408`), max requests, and `Connection: close`
- `Expect: 100-continue` supported; other `Expect` values → `417`

## 4. WSGI compliance

- Full PEP 3333 environ, `wsgi.input`, write callable, iterable `close()`
- Compliance tests: `wsgiref.validate`, Django socket round-trips (all models)
- Optional middleware: JSON stats endpoint, static file serving with `304`

## 5. Concurrency tradeoffs

| Model | Strength | Weakness |
| --- | --- | --- |
| Serial | Easiest to explain | One slow client blocks all others |
| Threaded | Natural for sync WSGI | Pool saturation under many keep-alive clients |
| Async | Efficient socket I/O | WSGI still runs in a thread pool (not ASGI) |

Benchmark results: `docs/benchmark-results.md` (local runs).

## 6. Production tradeoffs (intentional non-goals)

Documented in `docs/production-reflection.md` and ADR 0004:

- No TLS, HTTP/2+, WebSockets, reverse proxy, chunked encoding
- No worker process supervision, graceful reload, or slowloris hardening
- No production-grade observability stack

These are teaching boundaries, not accidental omissions.

## 7. Testing

129 automated tests (~89% coverage): parser edge cases, socket round-trips,
compliance (Django, `wsgiref.validate`), concurrency parity, benchmark smoke.

## 8. Demonstration

Follow `docs/demo-script.md` and `docs/demo-rehearsal.md`. Key proof points:

- `curl -i` trivial app
- Malformed input → 400 (server survives)
- Django in browser via pyserve
- Optional HTMX dashboard polling `/_pyserve/stats`

## 9. Conclusion

`pyserve` is a focused capstone artifact proving protocol understanding. It is
portfolio-ready as an educational server, not a production deployment target.
