# ADR 0002: Sync WSGI vs Async Transport

## Status

Accepted

## Context

WSGI is a synchronous Python callable interface. It is not a network protocol
and it is not ASGI.

The asyncio transport can accept connections and read/write bytes
asynchronously, but the WSGI application itself must either run synchronously or
be delegated to an executor.

## Decision

`pyserve` uses a dedicated bounded `ThreadPoolExecutor` for WSGI work in the
async model. The executor is created before the server signals readiness so
early connections never fall through to asyncio's default executor.

## Consequences

- A slow WSGI callable does not block the entire event loop.
- `--workers` means the same thing in threaded and async models.
- WSGI remains synchronous; asyncio is transport-only, not ASGI.
