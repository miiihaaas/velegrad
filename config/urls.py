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
from django.urls import path

urlpatterns = [
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
]
