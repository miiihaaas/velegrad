"""
Root URL configuration (Story 1.1).

The admin is mounted on a non-default, env-configured path (ADMIN_URL) so it is
NOT reachable at /admin/ (NFR-5 / AC8). ADMIN_URL je promovisan u Django setting
(config/settings/base.py) i predstavlja JEDINI izvor istine — ovde se samo
konzumira preko django.conf.settings, bez ponovnog čitanja okruženja. Vrednost
je već normalizovana (bez kose crte); Django's path() zahteva prateću kosu crtu.
"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path, register_converter

from pages.views import ContactView, HomeView, PrivateCollectionView, page_view
from properties.views import PropertyDetailView, PropertyListView


class UnicodeSlugConverter:
    """Slug konverter koji prihvata unicode slug-ove (npr. ``kuća-zlatibor``).

    ``Property.slug`` se generiše sa ``slugify(title, allow_unicode=True)``
    (properties/models.py), pa može sadržati ne-ASCII znakove (ćčšžđ...).
    Ugrađeni Django ``<slug:>`` konverter je ASCII-only (``[-a-zA-Z0-9_]+``),
    pa unicode slug ne bi razrešio (NoReverseMatch pri reverse / 404 pri GET).
    ``\\w`` u str regex-u je unicode-aware, pa pokriva i ASCII i unicode slug-ove.
    """

    regex = r"[-\w]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(UnicodeSlugConverter, "uslug")

# Ne-lokalizabilne rute (Story 6.1) — OSTAJU VAN i18n_patterns (bez /en/ prefiksa):
#  - admin (ADMIN_URL): NFR-5 — admin putanja je deterministička, ne sme nositi
#    jezički prefiks (/en/<ADMIN_URL>/ -> 404).
#  - tinymce: asset/filebrowser rute (1.4 AC2).
#  - i18n/: Django set_language view kao OPCIONI fallback (registrovan VAN
#    prefiksa). Switcher ga NE koristi (LOCKED na {% translate_url %} GET linkove),
#    ali reverse("set_language") mora da razreši bez /en/ prefiksa.
urlpatterns = [
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    # TinyMCE asset/spellcheck/filebrowser routes (Story 1.4 AC2). 5.0.0 has
    # app_name=None -> no "tinymce:" namespace; routes are tinymce-compressor /
    # tinymce-filebrowser / tinymce-linklist.
    path("tinymce/", include("tinymce.urls")),
    # set_language view fallback (van prefiksa).
    path("i18n/", include("django.conf.urls.i18n")),
]

# Lokalizabilne rute (Story 6.1) — wrap-ovane u i18n_patterns sa
# prefix_default_language=False: SR (default sr-latn) ostaje BEZ prefiksa
# (reverse("home")=="/", reverse("about")=="/about/" ...), EN dobija /en/ prefiks.
urlpatterns += i18n_patterns(
    # Minimalna javna home ruta (Story 2.1, AC7) — renderuje bazni layout.
    path("", HomeView.as_view(), name="home"),
    # Signature listing sa server-side filterima (Story 3.1).
    path("properties/", PropertyListView.as_view(), name="properties"),
    # Property Detail (Story 3.2) — POSLE listing rute; <slug> ne poklapa praznu
    # putanju pa nema kolizije. Hardkodovani /properties/<slug>/ hrefovi iz
    # 3.1/2.2 sada vode na ovu živu rutu.
    path(
        "properties/<uslug:slug>/",
        PropertyDetailView.as_view(),
        name="property-detail",
    ),
    # CMS-driven statične stranice (Story 4.1) — EKSPLICITNE rute, BEZ root
    # catch-all. Svaka ruta nosi svoj fiksni slug + template; page_view radi
    # get_object_or_404(is_active=True).
    path(
        "about/",
        page_view,
        {"slug": "about", "template_name": "about.html"},
        name="about",
    ),
    path(
        "international/",
        page_view,
        {"slug": "international", "template_name": "international.html"},
        name="international",
    ),
    # Contact stranica (Story 4.2) — Contact je CBV (kao Home/PropertyDetail).
    path("contact/", ContactView.as_view(), name="contact"),
    # Private Collection stranica (Story 5.1).
    path(
        "private-collection/",
        PrivateCollectionView.as_view(),
        name="private-collection",
    ),
    prefix_default_language=False,
)

# Eksplicitni custom 404 handler (Story 2.1, AC5) — premium 404.html unutar
# baznog okvira sa HTTP statusom 404 (aktivno kada je DEBUG=False).
handler404 = "pages.views.custom_404"
