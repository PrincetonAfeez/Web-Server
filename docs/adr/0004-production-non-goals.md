# ADR 0004: Production Non-Goals

## Status

Accepted

## Context

`pyserve` is an educational capstone project demonstrating the path from TCP
bytes to a WSGI application.

## Decision

`pyserve` is not a production replacement for nginx, gunicorn, uWSGI, uvicorn,
or Apache.

The server intentionally excludes TLS, reverse proxying, HTTP/2, HTTP/3,
WebSockets, compression, process supervision, graceful reload, and production
security hardening.

## Consequences

- The capstone goal is protocol understanding, not production feature parity.
- Documented tradeoffs (for example keep-alive limits and parser boundaries) are
  intentional teaching boundaries rather than accidental omissions.
