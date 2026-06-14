""" Django URLs for the Django demo """

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("demo.django_demo.pages.urls")),
]
