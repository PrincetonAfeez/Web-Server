""" Benchmark harness for the pyserve demo """

from __future__ import annotations

import argparse
import socket
import statistics
import threading
import time

from pyserve.server import WSGIServer


def build_request(target: str = "/") -> bytes:
    return (
        f"GET {target} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n".encode("latin-1")
    )


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def one_request(host: str, port: int, timeout: float) -> tuple[float, bool]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout) as client:
            client.sendall(build_request(target="/"))
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
        return time.perf_counter() - started, True
    except OSError:
        return time.perf_counter() - started, False


def run_load(host: str, port: int, workers: int, requests_per_worker: int, timeout: float) -> dict[str, float]:
    latencies: list[float] = []
    failures = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal failures
        local_latencies: list[float] = []
        local_failures = 0
        for _ in range(requests_per_worker):
            elapsed, ok = one_request(host, port, timeout)
            if ok:
                local_latencies.append(elapsed)
            else:
                local_failures += 1
        with lock:
            latencies.extend(local_latencies)
            failures += local_failures

    started = time.perf_counter()
    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    total = time.perf_counter() - started

    success = len(latencies)
    return {
        "workers": float(workers),
        "requests": float(workers * requests_per_worker),
        "success": float(success),
        "failures": float(failures),
        "total_seconds": total,
        "requests_per_second": success / total if total else 0.0,
        "mean_latency": statistics.mean(latencies) if latencies else 0.0,
        "p50_latency": percentile(latencies, 50),
        "p95_latency": percentile(latencies, 95),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark pyserve concurrency models.")
    parser.add_argument("--model", choices=["serial", "threaded", "async"], default="serial")
    parser.add_argument("--workers", type=int, default=8, help="Benchmark client threads")
    parser.add_argument("--requests", type=int, default=50, help="Requests per client thread")
    parser.add_argument("--server-threads", type=int, default=4, help="pyserve worker threads for threaded/async")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    kwargs: dict[str, object] = {
        "port": 0,
        "model": args.model,
        "keep_alive_timeout": 0.0,
    }
    if args.model in {"threaded", "async"}:
        kwargs["threads"] = args.server_threads

    server = WSGIServer(app, **kwargs)
    thread = server.start_in_thread()
    try:
        results = run_load(server.host, server.port, args.workers, args.requests, timeout=3.0)
    finally:
        server.stop()
        thread.join(timeout=5)

    print(f"model={args.model}")
    for key in (
        "workers",
        "requests",
        "success",
        "failures",
        "total_seconds",
        "requests_per_second",
        "mean_latency",
        "p50_latency",
        "p95_latency",
    ):
        value = results[key]
        if key in {"workers", "requests", "success", "failures"}:
            print(f"{key}={int(value)}")
        else:
            print(f"{key}={value:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
