# Production Reflection

`pyserve` deliberately stops before production server territory. It does not
handle TLS termination, HTTP/2, HTTP/3, WebSockets, reverse proxy behavior,
chunked transfer, compression, robust worker process management, graceful
reloads, `sendfile`, or production security hardening.

Those omissions are part of the capstone boundary. The implemented project
focuses on the protocol layers that frameworks usually hide: TCP byte streams,
HTTP/1.1 parsing and serialization, WSGI environ construction, concurrency
tradeoffs, and testable protocol behavior.
