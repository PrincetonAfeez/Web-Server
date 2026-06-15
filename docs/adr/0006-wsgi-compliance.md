# ADR 0006: WSGI Compliance

## Status

Accepted

## Context

The capstone headline is running **unmodified** WSGI apps (trivial demo, Django,
`wsgiref.validate`). That requires a faithful PEP 3333 adapter, not a thin
function wrapper.

## Decision

The WSGI adapter:

- Builds a PEP 3333-style `environ` with required variables and `HTTP_*` header
  keys (special-casing `Content-Type` and `Content-Length`).
- Supplies `wsgi.input` as a file-like byte stream and `wsgi.errors` as a
  writable stream.
- Implements `start_response` with the legacy write callable.
- Streams iterable body chunks, validates bytes, and calls `close()` when
  present.
- Maps app failures to `500` without crashing the accept loop.

Compliance is verified with `wsgiref.validate` unit tests and socket round-trips
on all three concurrency models.

## Consequences

- HTTP is the wire protocol; WSGI is the Python boundary Django speaks.
- Optional middleware (static files, JSON stats endpoint) wraps the WSGI app
  without changing the adapter contract.
- ASGI is explicitly out of scope.
