""" Test CLI utilities """

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

from pyserve.cli.main import (
    EXIT_OK,
    _config_from_args,
    build_parser,
    main,
    non_negative_float,
    port_number,
    positive_float,
    positive_int,
)


def test_positive_int_rejects_non_integer():
    with pytest.raises(argparse.ArgumentTypeError, match="not an integer"):
        positive_int("abc")


def test_positive_int_rejects_zero():
    with pytest.raises(argparse.ArgumentTypeError, match="at least 1"):
        positive_int("0")


def test_positive_float_rejects_non_number():
    with pytest.raises(argparse.ArgumentTypeError, match="not a number"):
        positive_float("abc")


def test_positive_float_rejects_zero():
    with pytest.raises(argparse.ArgumentTypeError, match="greater than 0"):
        positive_float("0")


def test_port_number_rejects_negative():
    with pytest.raises(argparse.ArgumentTypeError, match="non-negative"):
        port_number("-1")


def test_non_negative_float_rejects_negative():
    with pytest.raises(argparse.ArgumentTypeError, match="non-negative"):
        non_negative_float("-0.1")


def test_config_from_args_merges_toml_and_cli_overrides(tmp_path: Path):
    config_file = tmp_path / "serve.toml"
    config_file.write_text(
        'host = "0.0.0.0"\nport = 9000\nmodel = "serial"\naccess_log = true\n',
        encoding="utf-8",
    )
    args = build_parser().parse_args(
        [
            "--app",
            "demo.trivial_app:application",
            "--config",
            str(config_file),
            "--port",
            "9100",
            "--model",
            "threaded",
            "--stats-path",
            "/metrics",
        ]
    )

    config = _config_from_args(args)

    assert config.host == "0.0.0.0"
    assert config.port == 9100
    assert config.model == "threaded"
    assert config.access_log is True
    assert config.stats_path == "/metrics"


def test_config_from_args_defaults_without_inputs():
    args = build_parser().parse_args(["--app", "demo.trivial_app:application"])

    config = _config_from_args(args)

    assert config.host == "127.0.0.1"
    assert config.port == 8000


def test_main_handles_keyboard_interrupt(monkeypatch):
    stopped = {"value": False}

    class FakeServer:
        def __init__(self, app, config=None, **kwargs):
            pass

        def run(self):
            raise KeyboardInterrupt

        def stop(self):
            stopped["value"] = True

    monkeypatch.setattr("pyserve.cli.main.WSGIServer", FakeServer)

    exit_code = main(["--app", "demo.trivial_app:application"])

    assert exit_code == EXIT_OK
    assert stopped["value"] is True


def test_read_timeout_zero_is_rejected_by_parser():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["--app", "demo.trivial_app:application", "--read-timeout", "0"]
        )


def test_write_timeout_zero_is_rejected_by_parser():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["--app", "demo.trivial_app:application", "--write-timeout", "0"]
        )


