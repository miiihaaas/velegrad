"""Public frontend views (Story 2.1).

Minimalna home ruta renderuje bazni layout (templates/home.html koji
{% extends "base.html" %}), BEZ sadržaja iz baze (to dolazi u Story 2.2).
custom_404 je eksplicitni handler404 koji renderuje premium 404.html unutar
baznog okvira (site-header/site-footer) sa HTTP statusom 404.
"""
from django.shortcuts import render
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"


def custom_404(request, exception):
    return render(request, "404.html", status=404)
