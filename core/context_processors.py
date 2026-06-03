"""Core context processors (Story 2.2).

Izlaže ``SiteSettings`` singleton svakom template-u (footer u base.html + sve
Home sekcije) kao ``site_settings``.
"""
from core.models import SiteSettings

# GA4 (Story 6.2) — JS-string-safe escape SAMO za znakove koji bi mogli da probiju
# inline `gtag('config','<id>')` string. Django |escapejs je previše agresivan
# (escape-uje i `-` u `-`), pa GA4 ID-u kao "G-TEST123" promeni vrednost.
# Mapiramo samo opasne znakove (navodnik/backslash/HTML meta/newline) → `\uXXXX`,
# a alfanumerik + `-` (legitimni GA4 measurement ID format) ostaju netaknuti.
_JS_STRING_ESCAPES = {
    "\\": "\\u005C",
    "'": "\\u0027",
    '"': "\\u0022",
    ">": "\\u003E",
    "<": "\\u003C",
    "&": "\\u0026",
    "=": "\\u003D",
    "\n": "\\u000A",
    "\r": "\\u000D",
    "\u2028": "\\u2028",  # LINE SEPARATOR (JS line terminator \u2192 mora se escape-ovati)
    "\u2029": "\\u2029",  # PARAGRAPH SEPARATOR (JS line terminator \u2192 mora se escape-ovati)
}


def _js_escape_ga_id(value):
    """Vrati JS-string-bezbedan GA4 ID (opasni znakovi → ``\\uXXXX``)."""
    return "".join(_JS_STRING_ESCAPES.get(ch, ch) for ch in value)


def site_settings(request):
    """Učini SiteSettings singleton dostupnim u SVAKOM template-u.

    ``load()`` radi ``get_or_create(pk=1)`` — uvek vraća instancu (nikad
    ``None``), bezbedno i u praznoj bazi. Jedan upit po renderu je prihvatljivo
    za MVP; keširanje dolazi u Epiku 6 (perf).

    GA4 (6.2): izlaže i ``ga4_id`` (obrezana vrednost — prazan/whitespace-only =
    "" → GA4 se ne renderuje) i ``ga4_id_js`` (JS-string-bezbedna varijanta za
    inline ``gtag('config', ...)`` poziv).
    """
    settings_obj = SiteSettings.load()
    ga4_id = (settings_obj.google_analytics_id or "").strip()
    return {
        "site_settings": settings_obj,
        "ga4_id": ga4_id,
        "ga4_id_js": _js_escape_ga_id(ga4_id),
    }
