""" Test CLI """

from __future__ import annotations

import subprocess
import sys

import pytest

from pyserve import __version__
from pyserve.cli.main import EXIT_APP_LOAD_FAILED, build_parser, main
from pyserve.config import load_wsgi_app


def test_cli_parser_accepts_required_options():
    args = build_parser().parse_args(
        [
            "--app",
            "demo.trivial_app:application",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--model",
            "threaded",
            "--workers",
            "2",
        ]
    )

    assert args.app == "demo.trivial_app:application"
    assert args.model == "threaded"
    assert args.threads == 2


def test_load_wsgi_app_imports_callable():
    app = load_wsgi_app("demo.trivial_app:application")

    assert callable(app)


def test_workers_must_be_at_least_one():
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--app", "demo.trivial_app:application", "--workers", "0"])

    assert excinfo.value.code == 2  # argparse usage-error convention


def test_max_requests_per_connection_must_be_at_least_one():
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(
            ["--app", "demo.trivial_app:application", "--max-requests-per-connection", "0"]
        )

    assert excinfo.value.code == 2


def test_max_header_size_must_be_at_least_one():
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(
            ["--app", "demo.trivial_app:application", "--max-header-size", "0"]
        )

    assert excinfo.value.code == 2


def test_max_body_size_must_be_at_least_one():
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(
            ["--app", "demo.trivial_app:application", "--max-body-size", "0"]
        )

    assert excinfo.value.code == 2


def test_port_must_be_non_negative():
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(
            ["--app", "demo.trivial_app:application", "--port", "-1"]
        )

    assert excinfo.value.code == 2


def test_keep_alive_timeout_must_be_non_negative():
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(
            ["--app", "demo.trivial_app:application", "--keep-alive-timeout", "-1"]
        )

    assert excinfo.value.code == 2


def test_configure_application_logging_honors_verbose():
    import logging

    from pyserve.config import ServerConfig, configure_application_logging

    configure_application_logging(ServerConfig(verbose=True, log_level="INFO"))
    assert logging.getLogger().level == logging.DEBUG


def test_benchmark_friendly_sets_keep_alive_timeout_to_zero():
    args = build_parser().parse_args(
        ["--app", "demo.trivial_app:application", "--benchmark-friendly"]
    )

    keep_alive_timeout = 0.0 if args.benchmark_friendly else args.keep_alive_timeout
    assert keep_alive_timeout == 0.0


def test_wsgi_server_rejects_unknown_model():
    from pyserve.server import WSGIServer

    with pytest.raises(ValueError, match="unknown concurrency model"):
        WSGIServer(lambda e, s: None, model="invalid")


def test_wsgi_server_rejects_config_and_host_together():
    from pyserve.config import ServerConfig
    from pyserve.server import WSGIServer

    with pytest.raises(TypeError, match="not both"):
        WSGIServer(lambda e, s: None, host="10.0.0.1", config=ServerConfig())


def test_version_flag_reports_package_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--version"])

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"pyserve {__version__}"


def test_unloadable_app_exits_with_distinct_code(capsys):
    exit_code = main(["--app", "does.not.exist:application"])

    assert exit_code == EXIT_APP_LOAD_FAILED == 3
    assert "could not load app" in capsys.readouterr().err


def test_package_is_runnable_as_module():
    result = subprocess.run(
        [sys.executable, "-m", "pyserve", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert "--app" in result.stdout


def test_server_stats_is_part_of_public_api():
    from pyserve import ServerStats

    assert ServerStats().snapshot()["request_count"] == 0


def test_default_server_header_matches_package_version():
    from pyserve import __version__
    from pyserve.config import ServerConfig

    assert ServerConfig().server_header == f"pyserve/{__version__}"


def test_cli_on_bound_prints_ephemeral_port(capsys):
    from pyserve.cli.main import main

    thread = __import__("threading").Thread(
        target=lambda: main(
            [
                "--app",
                "demo.trivial_app:application",
                "--host",
                "127.0.0.1",
                "--port",
                "0",
                "--model",
                "serial",
            ]
        ),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=3)
    output = capsys.readouterr().out
    assert "pyserve serving demo.trivial_app:application on http://127.0.0.1:" in output
    assert ":0 (" not in output
