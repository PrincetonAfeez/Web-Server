""" Trivial app for the pyserve demo """

from __future__ import annotations


def application(environ, start_response):
    body = (
        "Hello from pyserve\n"
        f"method={environ['REQUEST_METHOD']}\n"
        f"path={environ['PATH_INFO']}\n"
        f"query={environ['QUERY_STRING']}\n"
    ).encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [body]
