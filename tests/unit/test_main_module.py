""" Test main module """

from __future__ import annotations

import subprocess
import sys

import pytest

from pyserve.cli.main import EXIT_APP_LOAD_FAILED


def test_main_module_runs_help():
    result = subprocess.run(
        [sys.executable, "-m", "pyserve", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert "--app" in result.stdout


def test_main_module_reports_app_load_failure():
    result = subprocess.run(
        [sys.executable, "-m", "pyserve", "--app", "does.not.exist:application"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == EXIT_APP_LOAD_FAILED
    assert "could not load app" in result.stderr


def test_main_module_entrypoint_exits_with_main_return_code(monkeypatch):
    import runpy

    monkeypatch.setattr("pyserve.cli.main.main", lambda argv=None: 7)

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("pyserve", run_name="__main__")

    assert excinfo.value.code == 7
