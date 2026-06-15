""" Access log module for the pyserve project """

from __future__ import annotations

import logging
from datetime import UTC, datetime

from pyserve.config import ServerConfig
from pyserve.models import Request

LOGGER = logging.getLogger("pyserve.access")


def log_access(config: ServerConfig, request: Request, status_code: int, response_size: int, elapsed: float) -> None:
    if not config.access_log:
        return

    _emit_access_line(
        config,
        request.remote_addr or "-",
        request.method,
        request.raw_target,
        request.http_version,
        status_code,
        response_size,
        elapsed,
    )


def log_access_error(
    config: ServerConfig,
    *,
    remote_addr: str,
    method: str | None,
    raw_target: str,
    http_version: str,
    status_code: int,
    response_size: int,
    elapsed: float,
) -> None:
    if not config.access_log:
        return

    _emit_access_line(
        config,
        remote_addr or "-",
        method or "-",
        raw_target,
        http_version,
        status_code,
        response_size,
        elapsed,
    )


def _emit_access_line(
    config: ServerConfig,
    remote_addr: str,
    method: str,
    raw_target: str,
    http_version: str,
    status_code: int,
    response_size: int,
    elapsed: float,
) -> None:
    if config.access_log_clf:
        timestamp = datetime.now(UTC).strftime("%d/%b/%Y:%H:%M:%S %z")
        LOGGER.info(
            '%s - - [%s] "%s %s %s" %s %s',
            remote_addr,
            timestamp,
            method,
            raw_target,
            http_version,
            status_code,
            response_size,
        )
        return

    LOGGER.info(
        '%s - "%s %s %s" %s %s %.4fs',
        remote_addr,
        method,
        raw_target,
        http_version,
        status_code,
        response_size,
        elapsed,
    )
