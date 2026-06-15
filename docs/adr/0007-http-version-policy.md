# ADR 0007: HTTP Version Policy

## Status

Accepted

## Context

`pyserve` implements HTTP/1.1 only. Clients may still send other protocol tokens on
the request line (for example `HTTP/1.0`).

## Decision

Requests whose request line does not declare `HTTP/1.1` are rejected with:

```http
HTTP/1.1 505 HTTP Version Not Supported
```

The server does not upgrade, downgrade, or silently accept other HTTP versions.

## Consequences

- Behavior is explicit and easy to explain in a capstone demo.
- Clients expecting HTTP/1.0 keep-alive semantics will not interoperate; that is
  consistent with the project's HTTP/1.1-only scope.
- `505` is used instead of `400` so the status code matches the failure category.
