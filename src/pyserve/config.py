""" Config module for the pyserve project """

from __future__ import annotations

import importlib
import logging
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any, TextIO

WSGIApplication = Callable[[dict[str, Any], Callable[..., Callable[[bytes], None]]], object]


def default_server_header() -> str:
    from pyserve import __version__

    return f"pyserve/{__version__}"


def _default_server_header() -> str:
    return default_server_header()


def notify_bound(config: ServerConfig) -> None:
    if config.on_bound is not None:
        config.on_bound(config)


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    model: str = "serial"
    threads: int = 8
    backlog: int = 128
    verbose: bool = False
    log_level: str = "INFO"
    access_log: bool = False
    access_log_clf: bool = False
    debug_errors: bool = False
    max_request_line_size: int = 8 * 1024
    max_header_size: int = 64 * 1024
    max_header_count: int = 100
    max_body_size: int = 1024 * 1024
    read_timeout: float = 10.0
    write_timeout: float = 10.0
    keep_alive_timeout: float = 5.0
    max_keep_alive_requests: int = 100
    read_chunk_size: int = 4096
    server_header: str = field(default_factory=_default_server_header)
    url_scheme: str = "http"
    wsgi_multithread: bool = False
    wsgi_multiprocess: bool = False
    wsgi_run_once: bool = False
    error_stream: TextIO = sys.stderr
    bound_host: str | None = None
    bound_port: int | None = None
    on_bound: Callable[[ServerConfig], None] | None = None
    stats_path: str | None = None
    static_root: str | None = None
    static_url_prefix: str = "/static"

    @property
    def effective_host(self) -> str:
        return self.bound_host or self.host

    @property
    def effective_port(self) -> int:
        return self.bound_port or self.port


def configure_application_logging(config: ServerConfig) -> None:
    level_name = config.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    if config.verbose:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(message)s", force=True)


_CONFIG_FIELD_MAP = {
    "workers": "threads",
    "max_requests_per_connection": "max_keep_alive_requests",
    "benchmark_friendly": "_benchmark_friendly",
}


def load_toml_config(path: str | Path) -> dict[str, object]:
    import tomllib

    config_path = Path(path)
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"config file {config_path} must contain a TOML table at the top level")
    return data


def server_config_from_mapping(data: Mapping[str, object]) -> ServerConfig:
    kwargs: dict[str, object] = {}
    benchmark_friendly = False
    for key, value in data.items():
        if key == "app":
            continue
        target = _CONFIG_FIELD_MAP.get(key, key)
        if target == "_benchmark_friendly":
            benchmark_friendly = bool(value)
            continue
        if target not in ServerConfig.__dataclass_fields__:
            raise ValueError(f"unknown config key {key!r}")
        kwargs[target] = value
    if benchmark_friendly:
        kwargs["keep_alive_timeout"] = 0.0
    return ServerConfig(**kwargs)  # type: ignore[arg-type]


def merge_server_config(base: ServerConfig, overrides: Mapping[str, object]) -> ServerConfig:
    data = {name: getattr(base, name) for name in base.__dataclass_fields__ if name != "on_bound"}
    data.update(overrides)
    return server_config_from_mapping(data)


def load_wsgi_app(spec: str) -> WSGIApplication:
    if ":" not in spec:
        raise ValueError("--app must use import.path:callable format")

    module_name, object_path = spec.split(":", 1)
    if not module_name or not object_path:
        raise ValueError("--app must include both a module and callable name")

    module = importlib.import_module(module_name)
    obj: Any = module
    for part in object_path.split("."):
        if not part:
            raise ValueError(f"invalid callable path in {spec!r}")
        obj = getattr(obj, part)

    if not callable(obj):
        raise TypeError(f"{spec!r} resolved to {type(obj).__name__}, not a callable")

    return obj


def reraise(exc_info: tuple[type[BaseException], BaseException, TracebackType]) -> None:
    exc_type, exc, traceback = exc_info
    raise exc.with_traceback(traceback)
