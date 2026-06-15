# ADR 0001: Concurrency Models

`pyserve` provides serial, threaded, and asyncio modes.

Serial mode is the baseline. It handles one accepted connection at a time and
is easiest to reason about when explaining the socket-to-WSGI path.

Threaded mode uses a thread pool. This matches synchronous WSGI naturally
because each connection can block while the app runs without blocking every
other connection.

Asyncio mode uses `asyncio.start_server` for socket I/O. The WSGI app is still
synchronous and runs in a dedicated thread pool sized by `--workers` (the same
knob that sizes the threaded model), not asyncio's default executor. This
demonstrates async transport without pretending WSGI is ASGI.

All three models share one request-dispatch policy (`pyserve.dispatch`): the
allowed-method set, the 405 response, and the keep-alive decision live in one
place so the models cannot drift apart. They also share a single `ServerStats`
instance and emit access logs identically.

Known tradeoff: the threaded model queues accepted connections without bound and
lets each keep-alive connection hold a worker for its lifetime, so a saturated
pool can head-of-line block new clients. The serial model cannot observe a stop
request while a keep-alive client is mid-stream. Both are acceptable for a
teaching server; a production server would add a connection cap and a shutdown
deadline.

Shutdown semantics differ by model. Serial finishes the connection it is
handling, then notices the stop request on its next accept poll. Threaded stops
accepting and then drains: the pool's context exit waits for every in-flight
connection (including idle keep-alive waits) to finish. Async stops accepting,
closes the listener, and relies on handler `finally` blocks to close client
sockets when the event loop tears down — requests mid-flight on a stopped async
server are dropped rather than drained. A WSGI call already running in the async
model's executor is not interrupted (threads cannot be cancelled); its thread
runs to completion, but its response may have nowhere to go. None of the models
offer a graceful-drain deadline; that is an explicit non-goal for a teaching
server.

Listener setup is shared across models. All three models build the listening
socket via `create_listening_socket`, which sets `SO_REUSEADDR` on POSIX and
`SO_EXCLUSIVEADDRUSE` on Windows (where `SO_REUSEADDR` would let two listeners
share one port), and chooses the address family from whether the host looks like
IPv6. The asyncio model passes that pre-built socket to `asyncio.start_server`
so bind policy matches serial and threaded modes.
