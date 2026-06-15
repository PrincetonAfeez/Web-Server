""" Threaded concurrency model for the pyserve project """

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from pyserve.concurrency.base import BaseServer
from pyserve.transport.connection import ConnectionHandler
from pyserve.transport.listener import create_listening_socket

LOGGER = logging.getLogger(__name__)


class ThreadedServer(BaseServer):
    def run(self) -> None:
        self.config.wsgi_multithread = True
        listener = create_listening_socket(self.config)
        listener.settimeout(0.2)
        self.ready_event.set()
        LOGGER.info(
            "serving on %s:%s with threaded model (%s threads)",
            self.config.effective_host,
            self.config.effective_port,
            self.config.threads,
        )

        try:
            with ThreadPoolExecutor(max_workers=self.config.threads) as executor:
                while not self.stop_event.is_set():
                    try:
                        client, address = listener.accept()
                    except TimeoutError:
                        continue
                    # Known tradeoff: accepted connections are queued without bound, and
                    # keep-alive connections occupy a worker for their lifetime, so a full
                    # pool can head-of-line block new clients. Acceptable for a teaching server.
                    executor.submit(ConnectionHandler(self.app, self.config, self.stats).handle, client, address)
        finally:
            listener.close()
