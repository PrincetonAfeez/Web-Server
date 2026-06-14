""" Echo app for the pyserve demo """

from __future__ import annotations


def application(environ, start_response):
    body = environ["wsgi.input"].read()
    response = (
        f"method={environ['REQUEST_METHOD']}\n"
        f"path={environ['PATH_INFO']}\n"
        f"content_length={environ.get('CONTENT_LENGTH', '')}\n"
    ).encode("utf-8") + body
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [response]
