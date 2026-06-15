# CLI Reference

```powershell
pyserve --app demo.trivial_app:application [options]
```

On Windows, if `pyserve` is not on `PATH`, use `python -m pyserve` instead.

CLI flags override values from an optional TOML config file (`--config serve.toml`).
See `serve.toml` for example keys and defaults.

## Required options

| Option | Meaning |
| --- | --- |
| `--app` | WSGI app in `import.path:callable` format |

## General options

| Option | Default | Meaning |
| --- | --- | --- |
| `--version` | — | Print pyserve version and exit |
| `--config` | — | Optional TOML config file |
| `--host` | `127.0.0.1` | Bind host |
| `--port` | `8000` | Bind port |
| `--model` | `serial` | Concurrency model: `serial`, `threaded`, or `async` |
| `--workers` / `--threads` | `8` | Thread pool size or async WSGI executor size |
| `--backlog` | `128` | Socket listen backlog |

## Logging options

| Option | Default | Meaning |
| --- | --- | --- |
| `--verbose` | `false` | Enable DEBUG logging (overrides `--log-level`) |
| `--log-level` | `INFO` | Logging level |
| `--access-log` | `false` | Emit per-request access logs |
| `--access-log-clf` | `false` | Emit Common Log Format access logs |
| `--debug-errors` | `false` | Include traceback details in `500` responses |

## Protocol limit options

| Option | Default | Meaning |
| --- | --- | --- |
| `--max-request-line-size` | `8192` | Maximum request line size in bytes |
| `--max-header-size` | `65536` | Maximum total header size in bytes |
| `--max-header-count` | `100` | Maximum number of request headers |
| `--max-body-size` | `1048576` | Maximum request body size in bytes |
| `--read-timeout` | `10.0` | Socket read timeout in seconds |
| `--write-timeout` | `10.0` | Socket write timeout in seconds |
| `--keep-alive-timeout` | `5.0` | Keep-alive idle timeout in seconds |
| `--max-requests-per-connection` | `100` | Maximum requests on one keep-alive connection |

## Middleware and demo options

| Option | Default | Meaning |
| --- | --- | --- |
| `--static` | — | Serve files from a directory |
| `--static-url-prefix` | `/static` | URL prefix for static files |
| `--stats-path` | — | Expose JSON server stats at this path |
| `--benchmark-friendly` | `false` | Set keep-alive timeout to `0` for benchmark runs |

## Exit codes

| Code | Meaning |
| ---: | --- |
| `0` | Server exited normally |
| `2` | CLI usage error reported by argparse |
| `3` | WSGI application failed to load |

Runtime protocol errors are returned as HTTP responses, not process exit codes.
