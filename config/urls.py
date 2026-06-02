"""
Root URL configuration (Story 1.1).

The admin is mounted on a non-default, env-configured path (ADMIN_URL) so it is
NOT reachable at /admin/ (NFR-5 / AC8). ADMIN_URL je promovisan u Django setting
(config/settings/base.py) i predstavlja JEDINI izvor istine — ovde se samo
konzumira preko django.conf.settings, bez ponovnog čitanja okruženja. Vrednost
je već normalizovana (bez kose crte); Django's path() zahteva prateću kosu crtu.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from pages.views import HomeView
from properties.views import PropertyDetailView, PropertyListView

urlpatterns = [
    # Minimalna javna home ruta (Story 2.1, AC7) — renderuje bazni layout.
    path("", HomeView.as_view(), name="home"),
    # Signature listing sa server-side filterima (Story 3.1).
    path("properties/", PropertyListView.as_view(), name="properties"),
    # Property Detail (Story 3.2) — POSLE listing rute; <slug> ne poklapa praznu
    # putanju pa nema kolizije. Hardkodovani /properties/<slug>/ hrefovi iz
    # 3.1/2.2 sada vode na ovu živu rutu.
    path(
        "properties/<slug:slug>/",
        PropertyDetailView.as_view(),
        name="property-detail",
    ),
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    # TinyMCE asset/spellcheck/filebrowser routes (Story 1.4 AC2). 5.0.0 has
    # app_name=None -> no "tinymce:" namespace; routes are tinymce-compressor /
    # tinymce-filebrowser / tinymce-linklist.
    path("tinymce/", include("tinymce.urls")),
]

# Eksplicitni custom 404 handler (Story 2.1, AC5) — premium 404.html unutar
# baznog okvira sa HTTP statusom 404 (aktivno kada je DEBUG=False).
handler404 = "pages.views.custom_404"
