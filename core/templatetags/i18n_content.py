"""``{% loc %}`` template tag (Story 6.1).

Izlaže ``LocalizedMixin.localized(base)`` template-ima: vraća vrednost polja na
aktivnom jeziku (``_en`` pod EN) sa ``_sr`` fallbackom kada je ``_en`` prazno.
Sadržaj iz baze (Property/Page/SiteSettings/PropertyFeature) prelazi sa direktnog
``_sr`` na ``{% loc obj "base" %}``.

Učitava se preko ``{% load i18n_content %}`` (``core`` je u INSTALLED_APPS,
APP_DIRS=True). FR (``_fr``) se NIKADA ne renderuje — ``get_language()[:2]``
razrešava samo ``sr``/``en`` (FR nije u ``LANGUAGES``; fallback vodi na ``_sr``).
"""
from django import template
from django.urls import translate_url as _translate_url
from django.utils.translation import get_language

register = template.Library()


@register.simple_tag(takes_context=True)
def translate_url(context, lang_code):
    """Vrati TEKUĆU putanju u ciljnom jeziku (Story 6.1 language switcher).

    Django nema ugrađen ``{% translate_url %}`` tag (samo funkciju
    ``django.urls.translate_url``), pa ga ovde izlažemo. Čuva tekuću putanju
    (``request.path``) i samo dodaje/skida ``/en/`` prefiks
    (``/ ↔ /en/``, ``/properties/ ↔ /en/properties/``) preko
    ``prefix_default_language=False`` semantike i18n_patterns-a.
    """
    request = context.get("request")
    path = request.path if request is not None else "/"
    return _translate_url(path, lang_code)


@register.simple_tag
def loc(obj, base):
    """Vrati ``obj.localized(base)`` (aktivni jezik + ``_sr`` fallback).

    Rezultat je auto-escape-ovan (simple_tag NE markira kao safe). Za
    admin-curated HTMLField sadržaj koristi obrazac
    ``{% loc obj "base" as var %}{{ var|safe }}``.
    """
    if hasattr(obj, "localized"):
        return obj.localized(base)
    # Robustan fallback ako obj nema LocalizedMixin.localized (edge).
    lang = (get_language() or "sr")[:2]
    return getattr(obj, f"{base}_{lang}", "") or getattr(obj, f"{base}_sr", "")
