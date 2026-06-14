""" Django WSGI application for the Django demo """

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.django_demo.config.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
