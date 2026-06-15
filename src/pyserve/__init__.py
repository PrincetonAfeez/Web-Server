""" Main module for the pyserve project """

from pyserve.config import ServerConfig, configure_application_logging, load_wsgi_app
from pyserve.observability.stats import ServerStats
from pyserve.server import WSGIServer

# Single source of truth for the version; pyproject.toml reads it via
# [tool.setuptools.dynamic] and the CLI exposes it as --version.
__version__ = "0.2.1"

__all__ = ["ServerConfig", "ServerStats", "WSGIServer", "__version__", "configure_application_logging", "load_wsgi_app"]
