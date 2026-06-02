"""Public frontend views (Story 2.1).

Minimalna home ruta renderuje bazni layout (templates/home.html koji
{% extends "base.html" %}), BEZ sadržaja iz baze (to dolazi u Story 2.2).
custom_404 je eksplicitni handler404 koji renderuje premium 404.html unutar
baznog okvira (site-header/site-footer) sa HTTP statusom 404.
"""
from django.shortcuts import render
from django.views.generic import TemplateView

from properties.models import Property


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # SiteSettings (hero/founder/kontakt) dolazi ISKLJUČIVO preko
        # core.context_processors.site_settings — NE pozivati load() ponovo ovde.
        # FR4: private/off-market kolekcije NIKADA se ne prikazuju na javnoj
        # Home strani. Home featured preview je Signature kolekcija (Epic 2/3),
        # pa eksplicitno filtriramo collection_type='signature'.
        context["featured_properties"] = Property.objects.filter(
            is_featured=True, is_active=True, collection_type="signature"
        )[:4]
        return context


def custom_404(request, exception):
    return render(request, "404.html", status=404)
