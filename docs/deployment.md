# Deployment Story

`pyserve` is an educational HTTP/1.1 WSGI server and is **not** intended for
production deployment. This document describes how to run it outside a one-off
local demo and what boundaries apply when doing so.

## Supported execution model

Minimal install and run (matches `docs/demo-script.md` trivial app):

```powershell
python -m pip install -r requirements.txt
pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model serial
```

On Windows, if `pyserve` is not on `PATH`, use `python -m pyserve` instead of
`pyserve`.

For repeatable local or classroom demonstrations, install the full contributor
toolchain (matches CI and the README quick start):

```powershell
python -m pip install -r requirements-all.txt -c constraints.txt
python -m pytest
pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model threaded
```

## Repeatable demo scripts

From the repository root:

| Platform | Command |
| --- | --- |
| Unix / macOS / Git Bash | `bash scripts/run-demo.sh` |
| Windows PowerShell | `.\scripts\run-demo.ps1` |

Each script installs locked dependencies and starts the trivial demo app on
`127.0.0.1:8000` with the threaded concurrency model.

## Deployment limitations

`pyserve` does not provide:

- TLS termination
- HTTP/2 or HTTP/3
- Reverse proxy behavior
- Process supervision or worker lifecycle management
- Graceful reload
- Production security hardening

See `docs/production-reflection.md` and `docs/adr/0004-production-non-goals.md`
for the full non-goals list and rationale.

## What to use for real deployment

For production traffic, place a production-grade server or reverse proxy in front
of an application server designed for production use (for example nginx, Caddy, or
a managed load balancer in front of gunicorn, uWSGI, or similar).

`pyserve` is intended to explain and demonstrate the protocol path between TCP
and a WSGI application — not to replace those tools.
