""" Test benchmark smoke """

from __future__ import annotations

import subprocess
import sys


def test_benchmark_script_runs_serial_smoke():
    completed = subprocess.run(
        [sys.executable, "demo/benchmark.py", "--model", "serial", "--workers", "2", "--requests", "5"],
        cwd=str(__import__("pathlib").Path(__file__).resolve().parents[2]),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0
    assert "model=serial" in completed.stdout
    assert "requests_per_second=" in completed.stdout
