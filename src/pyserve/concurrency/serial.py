""" Serial concurrency model for the pyserve project """

from __future__ import annotations

import logging

from pyserve.concurrency.base import BaseServer
from pyserve.transport.connection import ConnectionHandler
from pyserve.transport.listener import create_listening_socket

LOGGER = logging.getLogger(__name__)


class SerialServer(BaseServer):
    def run(self) -> None:
        self.config.wsgi_multithread = False
        listener = create_listening_socket(self.config)
        listener.settimeout(0.2)
        self.ready_event.set()
        LOGGER.info("serving on %s:%s with serial model", self.config.effective_host, self.config.effective_port)

        try:
            while not self.stop_event.is_set():
                try:
                    client, address = listener.accept()
                except TimeoutError:
                    continue
                ConnectionHandler(self.app, self.config, self.stats).handle(client, address)
        finally:
            listener.close()
