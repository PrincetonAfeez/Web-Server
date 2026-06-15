""" Server module for the pyserve project """

from __future__ import annotations

from threading import Event, Thread

from pyserve.concurrency.async_model import AsyncioServer
from pyserve.concurrency.serial import SerialServer
from pyserve.concurrency.threaded import ThreadedServer
from pyserve.config import ServerConfig, WSGIApplication
from pyserve.observability.stats import ServerStats
from pyserve.wsgi.middleware import apply_middleware

SERVER_MODELS = {
    "serial": SerialServer,
    "threaded": ThreadedServer,
    "async": AsyncioServer,
}

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000
_DEFAULT_MODEL = "serial"
_DEFAULT_THREADS = 8


class WSGIServer:
    def __init__(
        self,
        app: WSGIApplication,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        model: str = _DEFAULT_MODEL,
        threads: int = _DEFAULT_THREADS,
        config: ServerConfig | None = None,
        **overrides: object,
    ) -> None:
        if config is not None:
            if (
                host != _DEFAULT_HOST
                or port != _DEFAULT_PORT
                or model != _DEFAULT_MODEL
                or threads != _DEFAULT_THREADS
            ):
                raise TypeError("pass either config= or host/port/model/threads, not both")
        else:
            config = ServerConfig(host=host, port=port, model=model, threads=threads)
        for key, value in overrides.items():
            if not hasattr(config, key):
                raise TypeError(f"unknown server option {key!r}")
            setattr(config, key, value)
        if config.model not in SERVER_MODELS:
            raise ValueError(f"unknown concurrency model {config.model!r}")
        self.config = config
        self.stats = ServerStats()
        self.app = apply_middleware(app, self.config, self.stats)
        self._stop_event = Event()
        self._ready_event = Event()
        self._thread: Thread | None = None
        self._startup_error: BaseException | None = None

    @property
    def host(self) -> str:
        return self.config.effective_host

    @property
    def port(self) -> int:
        return self.config.effective_port

    def _prepare_run(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("server is already running")
        self._stop_event.clear()
        self._ready_event.clear()
        self._startup_error = None
        self.config.bound_host = None
        self.config.bound_port = None

    def run(self) -> None:
        self._prepare_run()
        self._serve()

    def _serve(self) -> None:
        server_cls = SERVER_MODELS.get(self.config.model)
        if server_cls is None:
            raise ValueError(f"unknown concurrency model {self.config.model!r}")
        server_cls(self.app, self.config, self._stop_event, self._ready_event, self.stats).run()

    serve_forever = run

    def _run_for_thread(self) -> None:
        try:
            self._serve()
        except BaseException as exc:
            # Stash the failure and unblock the waiter so start_in_thread can re-raise
            # the real error (e.g. a bind failure) instead of a generic timeout. Not
            # re-raised here: the thread's stderr traceback would only be noise.
            self._startup_error = exc
            self._ready_event.set()

    def start_in_thread(self, timeout: float = 5.0) -> Thread:
        self._prepare_run()
        self._thread = Thread(target=self._run_for_thread, daemon=True)
        self._thread.start()
        if not self._ready_event.wait(timeout):
            raise RuntimeError("server did not start before timeout")
        if self._startup_error is not None:
            raise self._startup_error
        return self._thread

    def stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)
