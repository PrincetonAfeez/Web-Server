# ADR 0003: Keep-Alive and Connection Scope

## Status

Accepted

## Context

HTTP/1.1 allows reusable TCP connections, but a teaching server must bound
connection lifetime to avoid unbounded memory use and ambiguous parser state.

## Decision

`pyserve` supports **bounded keep-alive**:

- Multiple **sequential** requests on one connection.
- Honor `Connection: close`.
- Close after `max_keep_alive_requests`.
- Close idle connections after `keep_alive_timeout` with `408 Request Timeout`.
- Close after parse/protocol errors.

HTTP **pipelining** (multiple in-flight requests on one connection) is out of
scope. Keep-alive here means reuse after the current response completes.

## Consequences

- Clients must send `Content-Length` on `POST` bodies so the parser knows when
  one message ends.
- Pipelined clients are not supported; extra bytes remain a known edge case if
  a client violates sequential semantics.
- Production servers add connection caps, drain deadlines, and richer timeout
  policies.
