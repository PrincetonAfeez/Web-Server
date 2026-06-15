""" Listener module for the pyserve project """

from __future__ import annotations

import socket
import sys

from pyserve.config import ServerConfig, notify_bound


def create_listening_socket(config: ServerConfig) -> socket.socket:
    family = socket.AF_INET6 if ":" in config.host else socket.AF_INET
    listener = socket.socket(family, socket.SOCK_STREAM)
    if sys.platform == "win32":
        # On Windows, SO_REUSEADDR lets a second socket bind the same (host, port)
        # while the first is still listening — two servers silently compete for
        # connections. SO_EXCLUSIVEADDRUSE restores the expected "address in use"
        # error; Windows also does not need REUSEADDR to rebind after TIME_WAIT.
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((config.host, config.port))
    listener.listen(config.backlog)
    bound = listener.getsockname()
    config.bound_host = str(bound[0])
    config.bound_port = int(bound[1])
    notify_bound(config)
    return listener
