""" CLI for the pyserve project """

from __future__ import annotations

import argparse
import sys

from pyserve import __version__
from pyserve.config import (
    ServerConfig,
    configure_application_logging,
    load_toml_config,
    load_wsgi_app,
    server_config_from_mapping,
)
from pyserve.server import WSGIServer

EXIT_OK = 0
EXIT_APP_LOAD_FAILED = 3


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text!r} is not an integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return value


def port_number(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text!r} is not an integer") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return value


def non_negative_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a WSGI app with pyserve.")
    parser.add_argument("--version", action="version", version=f"pyserve {__version__}")
    parser.add_argument("--config", help="Optional TOML config file (CLI flags override)")
    parser.add_argument("--app", required=True, help="WSGI app in import.path:callable format")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=port_number, default=None)
    parser.add_argument("--model", choices=["serial", "threaded", "async"], default=None)
    parser.add_argument("--workers", "--threads", dest="threads", type=positive_int, default=None)
    parser.add_argument("--backlog", type=positive_int, default=None)
    parser.add_argument("--verbose", action="store_true", default=None)
    parser.add_argument("--log-level", default=None)
    parser.add_argument("--max-request-line-size", type=positive_int, default=None)
    parser.add_argument("--max-header-size", type=positive_int, default=None)
    parser.add_argument("--max-header-count", type=positive_int, default=None)
    parser.add_argument("--max-body-size", type=positive_int, default=None)
    parser.add_argument("--read-timeout", type=positive_float, default=None)
    parser.add_argument("--write-timeout", type=positive_float, default=None)
    parser.add_argument("--keep-alive-timeout", type=non_negative_float, default=None)
    parser.add_argument("--max-requests-per-connection", type=positive_int, default=None)
    parser.add_argument("--access-log", action="store_true", default=None)
    parser.add_argument("--access-log-clf", action="store_true", default=None)
    parser.add_argument("--benchmark-friendly", action="store_true", default=None)
    parser.add_argument("--debug-errors", action="store_true", default=None)
    parser.add_argument("--static", dest="static_root", default=None, help="Serve files from this directory")
    parser.add_argument("--static-url-prefix", default=None)
    parser.add_argument("--stats-path", default=None, help="Expose JSON stats at this path (for dashboards)")
    return parser


def _config_from_args(args: argparse.Namespace) -> ServerConfig:
    data: dict[str, object] = {}
    if args.config:
        data.update(load_toml_config(args.config))

    if args.benchmark_friendly:
        data["benchmark_friendly"] = True

    cli_fields = {
        "host": args.host,
        "port": args.port,
        "model": args.model,
        "threads": args.threads,
        "backlog": args.backlog,
        "verbose": args.verbose,
        "log_level": args.log_level,
        "max_request_line_size": args.max_request_line_size,
        "max_header_size": args.max_header_size,
        "max_header_count": args.max_header_count,
        "max_body_size": args.max_body_size,
        "read_timeout": args.read_timeout,
        "write_timeout": args.write_timeout,
        "keep_alive_timeout": args.keep_alive_timeout,
        "max_keep_alive_requests": args.max_requests_per_connection,
        "access_log": args.access_log,
        "access_log_clf": args.access_log_clf,
        "debug_errors": args.debug_errors,
        "static_root": args.static_root,
        "static_url_prefix": args.static_url_prefix,
        "stats_path": args.stats_path,
    }
    for key, value in cli_fields.items():
        if value is not None:
            data[key] = value

    return server_config_from_mapping(data) if data else ServerConfig()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        app = load_wsgi_app(args.app)
    except Exception as exc:
        print(f"pyserve: could not load app: {exc}", file=sys.stderr)
        return EXIT_APP_LOAD_FAILED

    app_spec = args.app

    def on_bound(config: ServerConfig) -> None:
        print(
            f"pyserve serving {app_spec} on http://{config.effective_host}:{config.effective_port} ({config.model})"
        )

    config = _config_from_args(args)
    config.on_bound = on_bound
    configure_application_logging(config)
    server = WSGIServer(app, config=config)

    try:
        server.run()
    except KeyboardInterrupt:
        server.stop()
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
