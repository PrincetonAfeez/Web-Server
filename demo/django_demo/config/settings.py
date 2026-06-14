""" Django settings for the Django demo """

from __future__ import annotations

# Demo-only settings: the hardcoded SECRET_KEY, DEBUG=True, and ALLOWED_HOSTS=["*"]
# exist to prove an unmodified Django app runs on pyserve. Never use these in production.
SECRET_KEY = "pyserve-capstone-demo"
DEBUG = True
ROOT_URLCONF = "demo.django_demo.config.urls"
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "demo.django_demo.pages",
]
MIDDLEWARE = []
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [],
        },
    }
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
