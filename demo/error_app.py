""" Error app for the pyserve demo """

from __future__ import annotations


def application(environ, start_response):
    raise RuntimeError("demo error")
