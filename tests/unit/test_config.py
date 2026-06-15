""" Test config """

from __future__ import annotations

from pathlib import Path

import pytest

from pyserve import __version__
from pyserve.config import (
    ServerConfig,
    configure_application_logging,
    default_server_header,
    load_toml_config,
    load_wsgi_app,
    merge_server_config,
    notify_bound,
    reraise,
    server_config_from_mapping,
)


def test_default_server_header_includes_version():
    assert default_server_header() == f"pyserve/{__version__}"


def test_notify_bound_invokes_callback():
    seen: list[ServerConfig] = []

    def on_bound(config: ServerConfig) -> None:
        seen.append(config)

    config = ServerConfig(on_bound=on_bound, port=9001)
    notify_bound(config)

    assert seen == [config]


def test_notify_bound_noop_when_callback_missing():
    notify_bound(ServerConfig(on_bound=None))


def test_configure_application_logging_unknown_level_falls_back_to_info():
    import logging

    configure_application_logging(ServerConfig(log_level="NOT_A_LEVEL"))
    assert logging.getLogger().level == logging.INFO


def test_load_toml_config_reads_file(tmp_path: Path):
    config_file = tmp_path / "serve.toml"
    config_file.write_text('host = "0.0.0.0"\nport = 9000\n', encoding="utf-8")

    data = load_toml_config(config_file)

    assert data["host"] == "0.0.0.0"
    assert data["port"] == 9000


def test_load_toml_config_rejects_non_table(monkeypatch, tmp_path: Path):
    config_file = tmp_path / "bad.toml"
    config_file.write_bytes(b"")

    monkeypatch.setattr("tomllib.load", lambda handle: ["not", "a", "table"])

    with pytest.raises(ValueError, match="TOML table"):
        load_toml_config(config_file)


def test_server_config_from_mapping_unknown_key_raises():
    with pytest.raises(ValueError, match="unknown config key"):
        server_config_from_mapping({"not_a_real_field": 1})


def test_server_config_from_mapping_ignores_app_key():
    config = server_config_from_mapping({"app": "demo.trivial_app:application", "port": 4321})

    assert config.port == 4321


def test_merge_server_config_overrides_base_values():
    base = ServerConfig(host="127.0.0.1", port=8000, model="serial")
    merged = merge_server_config(base, {"port": 9000, "model": "threaded"})

    assert merged.host == "127.0.0.1"
    assert merged.port == 9000
    assert merged.model == "threaded"


def test_load_wsgi_app_requires_colon():
    with pytest.raises(ValueError, match="import.path:callable"):
        load_wsgi_app("demo.trivial_app.application")


def test_load_wsgi_app_rejects_empty_module():
    with pytest.raises(ValueError, match="module and callable"):
        load_wsgi_app(":application")


def test_load_wsgi_app_rejects_empty_callable():
    with pytest.raises(ValueError, match="module and callable"):
        load_wsgi_app("demo.trivial_app:")


def test_load_wsgi_app_rejects_invalid_dotted_path():
    with pytest.raises(ValueError, match="invalid callable path"):
        load_wsgi_app("sys:..path")


def test_load_wsgi_app_rejects_non_callable_object():
    with pytest.raises(TypeError, match="not a callable"):
        load_wsgi_app("pyserve:__version__")


def test_load_wsgi_app_imports_demo_application():
    app = load_wsgi_app("demo.trivial_app:application")

    assert callable(app)


def test_reraise_preserves_exception_type():
    import sys

    with pytest.raises(RuntimeError, match="boom"):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            reraise(sys.exc_info())
