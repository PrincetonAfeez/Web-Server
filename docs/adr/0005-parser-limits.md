# ADR 0005: Parser Limits

Network input must have boundaries. `pyserve` enforces limits for request line
length, total header bytes, header count, request body size, socket read
timeout, keep-alive idle timeout, and maximum keep-alive requests.

These limits prevent the educational server from waiting forever or allocating
unbounded memory when a client sends malformed or incomplete input.

HTTP/1.1 `POST` requests without a `Content-Length` header are rejected with
`400 Bad Request`. Clients must send an explicit `Content-Length` (including
`0` for an empty body).
