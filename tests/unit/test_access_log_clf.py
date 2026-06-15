""" Test access log CLF format """

from __future__ import annotations

import logging

from pyserve.config import ServerConfig
from pyserve.http.headers import CaseInsensitiveHeaders
from pyserve.models import Request
from pyserve.observability import access_log as access_log_module


def test_access_log_clf_format(caplog):
    config = ServerConfig(access_log=True, access_log_clf=True)
    request = Request(
        method="GET",
        raw_target="/",
        raw_path="/",
        path="/",
        query_string="",
        http_version="HTTP/1.1",
        headers=CaseInsensitiveHeaders([("Host", "localhost")]),
        body=b"",
        remote_addr="127.0.0.1",
    )

    with caplog.at_level(logging.INFO, logger="pyserve.access"):
        access_log_module.log_access(config, request, 200, 12, 0.01)

    assert '"GET / HTTP/1.1" 200 12' in caplog.records[0].message
    assert caplog.records[0].message.startswith("127.0.0.1 - - [")
