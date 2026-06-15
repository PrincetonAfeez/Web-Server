""" Base concurrency model for the pyserve project """

from __future__ import annotations

from threading import Event

from pyserve.config import ServerConfig, WSGIApplication
from pyserve.observability.stats import ServerStats


class BaseServer:
    def __init__(
        self,
        app: WSGIApplication,
        config: ServerConfig,
        stop_event: Event,
        ready_event: Event,
        stats: ServerStats | None = None,
    ) -> None:
        self.app = app
        self.config = config
        self.stop_event = stop_event
        self.ready_event = ready_event
        self.stats = stats if stats is not None else ServerStats()

    def run(self) -> None:
        raise NotImplementedError
