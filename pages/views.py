"""Public frontend views (Story 2.1).

Minimalna home ruta renderuje bazni layout (templates/home.html koji
{% extends "base.html" %}), BEZ sadržaja iz baze (to dolazi u Story 2.2).
custom_404 je eksplicitni handler404 koji renderuje premium 404.html unutar
baznog okvira (site-header/site-footer) sa HTTP statusom 404.
"""
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView

from properties.models import Property

from .models import Page


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


def page_view(request, slug, template_name):
    """Tanak CMS page view (Story 4.1).

    Razrešava Page po fiksnom slug-u (prosleđenom kao kwarg iz eksplicitne rute)
    sa is_active=True gating-om U upitu: nepostojeći ILI is_active=False slug → 404
    (Page NEMA preview polje — gating je čist is_active, ne can_preview). Rute su
    FIKSNE (/about/, /international/) bez <slug> segmenta, pa slug i template_name
    dolaze kao argumenti rute. site_settings je već globalno dostupan preko
    core.context_processors.site_settings (2.2) — NE re-load-uje se ovde.
    """
    page = get_object_or_404(Page, slug=slug, is_active=True)
    return render(request, template_name, {"page": page})
