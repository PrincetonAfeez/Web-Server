from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    return HttpResponse("Hello from Django through pyserve\n", content_type="text/plain")


def dashboard(request):
    return render(request, "pages/dashboard.html")


def stats_panel(request):
    return render(request, "pages/stats_panel.html")
