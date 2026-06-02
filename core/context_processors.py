"""Core context processors (Story 2.2).

Izlaže ``SiteSettings`` singleton svakom template-u (footer u base.html + sve
Home sekcije) kao ``site_settings``.
"""
from core.models import SiteSettings


def site_settings(request):
    """Učini SiteSettings singleton dostupnim u SVAKOM template-u.

    ``load()`` radi ``get_or_create(pk=1)`` — uvek vraća instancu (nikad
    ``None``), bezbedno i u praznoj bazi. Jedan upit po renderu je prihvatljivo
    za MVP; keširanje dolazi u Epiku 6 (perf).
    """
    return {"site_settings": SiteSettings.load()}
