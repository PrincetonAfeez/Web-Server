# Schema Folder for Web-Server / pyserve

This folder contains lightweight JSON Schema contracts for the `pyserve` educational HTTP/1.1 WSGI server.

These are **not database schemas**. They document and validate the project-facing contracts that matter most for this repository:

- server configuration values from `serve.toml` and `ServerConfig`
- normalized CLI invocation values
- parsed HTTP request shape
- serialized HTTP response shape
- WSGI `environ` values passed into an application
- JSON payload returned by the optional stats endpoint

All schemas use JSON Schema Draft 2020-12.

## Files

| File | Purpose |
| --- | --- |
| `server_config.schema.json` | Validates a JSON representation of pyserve TOML/config values. |
| `cli_args.schema.json` | Validates normalized CLI options before they are converted into `ServerConfig`. |
| `http_request.schema.json` | Documents the parsed HTTP/1.1 request contract. |
| `http_response.schema.json` | Documents the serialized HTTP response contract. |
| `wsgi_environ.schema.json` | Documents the WSGI environment mapping passed to WSGI apps. |
| `stats_response.schema.json` | Validates the JSON returned by the optional stats endpoint. |
| `schema_manifest.json` | Small index describing each schema file. |

## Example validation

```bash
python -m pip install jsonschema
python -m jsonschema -i serve.config.json Schema/server_config.schema.json
```

Because the repository's example config is TOML, convert it to JSON before using JSON Schema validation directly.
