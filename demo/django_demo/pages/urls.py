from __future__ import annotations

from django.urls import path

from demo.django_demo.pages.views import dashboard, home, stats_panel

urlpatterns = [
    path("", home),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/stats/", stats_panel, name="stats-panel"),
]
