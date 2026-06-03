"""Sitemap definicije (Story 6.2).

``django.contrib.sitemaps`` generiše ``/sitemap.xml`` iz ovih klasa. ``core`` je
kanonski dom za sitemap (arhitektura §2). Dve klase:

  * ``PropertySitemap`` — svi aktivni (javno vidljivi) Property zapisi.
  * ``PageSitemap`` — aktivne statične stranice (about/international); rute NISU
    generičke (nema ``/pages/<slug>/``) pa se slug mapira na ime eksplicitne rute.

⚠️ SR-jezik determinizam (LOCKED): ``reverse()`` razrešava pod AKTIVNIM jezikom.
Sa ``i18n_patterns(prefix_default_language=False)`` ambijentalna EN aktivacija bi
ubacila ``/en/`` u kanonski sitemap. Zato OBA ``location()`` forsiraju default/SR
jezik preko ``translation.override(settings.LANGUAGE_CODE)`` — telo sitemap-a NIKAD
ne sadrži ``/en/`` prefiks, čak i kad je ``translation.activate("en")`` aktivan.
"""
from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import translation

from pages.models import Page
from properties.models import Property


class PropertySitemap(Sitemap):
    """Sve javno vidljive (``is_active=True``) nekretnine."""

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # .only() — sitemap koristi samo slug (get_absolute_url) i updated_at
        # (lastmod); ne učitavaj cele redove.
        return Property.objects.filter(is_active=True).only("slug", "updated_at")

    def location(self, obj):
        # Forsiraj SR (no-prefix) jezik deterministički — bez /en/ leak-a.
        with translation.override(settings.LANGUAGE_CODE):
            return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class PageSitemap(Sitemap):
    """Aktivne statične stranice (about/international)."""

    changefreq = "monthly"
    priority = 0.5

    # Page rute NISU generičke — eksplicitne rute u config/urls.py sa fiksnim
    # slug->name mapiranjem. items() filtrira na poznate slug-ove pa location()
    # nikad ne dobije nemapiran slug.
    _slug_to_route = {"about": "about", "international": "international"}

    def items(self):
        # order_by(slug) — Page nema Meta.ordering; eksplicitan redosled gasi
        # UnorderedObjectListWarning iz sitemap paginatora (deterministički izlaz).
        # .only("slug") — sitemap koristi samo slug (location mapira slug->ruta).
        return (
            Page.objects.filter(is_active=True, slug__in=list(self._slug_to_route))
            .only("slug")
            .order_by("slug")
        )

    def location(self, obj):
        with translation.override(settings.LANGUAGE_CODE):
            return reverse(self._slug_to_route[obj.slug])
