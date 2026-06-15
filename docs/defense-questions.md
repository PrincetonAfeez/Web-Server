# Oral defense — 17 questions

Use these while rehearsing `docs/demo-rehearsal.md`.

## 1. How does TCP `accept` create a client connection?

The listening socket returns a new connected socket per client. Each connection
is handled independently (serially or concurrently depending on model).

## 2. Why can `recv()` return partial data?

TCP is a byte stream, not message-oriented. The kernel may deliver any number of
bytes per `recv()`; the server loops until it has a complete HTTP header block.

## 3. Why can `send()` write only part of the response?

Socket send buffers have finite space. `send_all()` loops until all bytes are
accepted by the kernel.

## 4. How does the server know HTTP headers are complete?

It searches for the delimiter `CRLF CRLF` in the accumulated buffer.

## 5. How does `Content-Length` control body reading?

After headers, the server reads exactly N bytes into `request.body` and
`wsgi.input`.

## 6. How does a parsed HTTP request become a WSGI environ?

`build_environ()` maps method, path, query, headers (`HTTP_*`), server/client
addresses, and streams into PEP 3333 keys.

## 7. What is `wsgi.input`?

A file-like object exposing the request body bytes to the application.

## 8. What does `start_response` do?

Records status and headers, returns the legacy write callable, and gates header
emission until body bytes are produced.

## 9. Why must WSGI response chunks be bytes?

PEP 3333 requires byte strings on the wire path; non-bytes are protocol errors.

## 10. Why is `close()` called on the WSGI iterable?

Resources (files, sockets, pools) may be held by the iterable; WSGI requires
servers to call `close()` when present.

## 11. How is an HTTP response serialized?

Status line + headers + blank line + body, with `Content-Length`, `Date`,
`Server`, and `Connection` as appropriate.

## 12. Why do HEAD / 204 / 304 omit bodies?

HTTP semantics: clients must not receive entity bodies for those cases even if
the application returned one.

## 13. How is keep-alive bounded?

`Connection: close`, idle timeout (`408`), `max_keep_alive_requests`, and parse
errors all close or stop reusing the connection.

## 14. How do serial, threaded, and async models differ?

Same parser/WSGI path; differ in how connections are accepted and whether WSGI
work blocks other clients (serial blocks; threaded/async isolate socket I/O).

## 15. Why don’t WSGI and asyncio compose directly?

WSGI is a synchronous call interface; asyncio can manage sockets but WSGI apps
still run in a thread pool executor in this design.

## 16. How does Django run unmodified?

Django exposes a standard WSGI callable; pyserve builds a compliant environ and
streams the response like any WSGI server.

## 17. What do production servers handle that pyserve does not?

TLS termination, HTTP/2 multiplexing, reverse proxying, worker supervision,
advanced timeouts/backpressure, chunked encoding, compression, and hardened
security policies.
