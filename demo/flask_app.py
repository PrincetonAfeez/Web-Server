"""Minimal Flask WSGI app for framework proof (optional demo)."""

application = None

try:
    from flask import Flask

    app = Flask(__name__)

    @app.get("/")
    def index():
        return "Hello from Flask through pyserve"

    application = app.wsgi_app
except ImportError:
    def application(environ, start_response):  # type: ignore[misc]
        start_response("503 Service Unavailable", [("Content-Type", "text/plain")])
        return [b"Install Flask to run this demo: pip install flask"]
