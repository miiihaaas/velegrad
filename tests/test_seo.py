"""
RED-phase contract tests for Story 6.2 — "SEO: meta/OG per zapis, sitemap.xml/
robots.txt (django.contrib.sitemaps), Schema.org RealEstateListing, GA4 preko
SiteSettings".

These tests define the CONTRACT for the SEO layer built ON TOP of the 6.1 i18n
stack. They are written BEFORE the feature is built, so EVERY test in this module
MUST FAIL/ERROR until the Dev implements (GREEN phase):

  * config/settings/base.py — "django.contrib.sites" + "django.contrib.sitemaps"
    in INSTALLED_APPS, SITE_ID = 1 (test.py inherits via `from .base import *`).
  * properties/models.py — Property.get_absolute_url() (method, NOT a migration):
    reverse("property-detail", kwargs={"slug": self.slug}).
  * core/sitemaps.py — PropertySitemap (is_active=True, location via
    get_absolute_url, lastmod=updated_at) + PageSitemap (is_active=True,
    items() filtered to slug__in=["about","international"], slug->route mapping),
    BOTH location() wrapped in translation.override(settings.LANGUAGE_CODE) so the
    canonical sitemap NEVER contains a /en/ prefix.
  * config/urls.py — sitemap.xml + robots.txt mounted OUTSIDE i18n_patterns
    (plain urlpatterns); sitemap view name "django.contrib.sitemaps.views.sitemap";
    robots.txt as TemplateView/HttpResponse content_type=text/plain.
  * templates/base.html — {% block title/meta_description/og/ga4 %} filled from
    SiteSettings.seo_default_* / google_analytics_id; og:image ABSOLUTE in both
    branches; GA4 only when google_analytics_id is non-empty AND non-whitespace.
  * templates/property-detail.html — {% block title/meta_description/og/schema %}
    per-property; schema_data built in PropertyDetailView, rendered via json_script.
  * templates/about.html, templates/international.html — {% block title/
    meta_description %} per-page.
  * templates/robots.txt — User-agent/Allow, Disallow: /<ADMIN_URL>/, absolute
    Sitemap: line.

Design / locked rules (mirrors the 3.2 / 4.1 / 6.1 harness):
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * Property is seeded via .objects.create(hero_image="", ...) — full_clean() is
    NEVER called (REUSE _make_property pattern from tests/test_property_detail.py).
  * Page is seeded via .objects.create(slug=, title_sr=, content_sr=) (REUSE
    _seed_page pattern from tests/test_static_pages.py).
  * SiteSettings is a singleton (save() pins pk=1) — SiteSettings.load()+setattr+
    save() is used here (identical to .objects.create()).
  * The conftest autouse _reset_active_language fixture keeps the active language
    deterministic between language-aware tests.
  * og:image absolute assertion: Django test client host is "testserver" ->
    absolute URL is http://testserver/...; the test asserts the og:image value is
    NOT a relative /static/ or /media/ path.
  * Schema.org JSON-LD is parsed with json.loads (the json_script-produced body).
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/6-2-seo-interface-contract.md
"""
import importlib
import json
import re

import pytest
from django.conf import settings
from django.utils import translation


# --------------------------------------------------------------------------- #
# Model / path helpers — mirror tests/test_property_detail.py + test_static_pages #
# --------------------------------------------------------------------------- #
def _get_model(app_label, class_name):
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


def _admin_index_path():
    """The mounted admin index path, derived from settings.ADMIN_URL."""
    return "/" + settings.ADMIN_URL.strip("/") + "/"


def _make_property(**overrides):
    """Create a Property with all required non-null scalar fields supplied.

    hero_image="" passes on SQLite (.create() skips full validation) and is falsy
    in the template -> placeholder branch. description_en is NOT NULL so a minimal
    value is supplied. full_clean() is DELIBERATELY NOT called. (REUSE of the
    tests/test_property_detail.py::_make_property pattern.)
    """
    Property = _get_model("properties", "Property")
    defaults = dict(
        title="Penthouse Rezidencija",
        status="for_sale",
        collection_type="signature",
        property_type="penthouse",
        location_city="Beograd",
        location_district="Dedinje",
        area_sqm="285.00",
        area_total_sqm="330.00",
        bedrooms=4,
        bathrooms=3,
        floor=6,
        total_floors=6,
        parking_spaces=2,
        year_built=2024,
        price="1250000.00",
        description_sr="<p>Opis</p>",
        description_en="<p>Description</p>",
        hero_image="",
        is_featured=False,
        is_active=True,
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


def _seed_page(slug, title_sr, content_sr, is_active=True, **overrides):
    """Create a Page. title_sr AND content_sr are required (else IntegrityError);
    title_en/content_en are blank=True so "" is fine. (REUSE of the
    tests/test_static_pages.py::_seed_page pattern.)
    """
    Page = _get_model("pages", "Page")
    defaults = dict(
        slug=slug,
        title_sr=title_sr,
        title_en="",
        content_sr=content_sr,
        content_en="",
        is_active=is_active,
    )
    defaults.update(overrides)
    return Page.objects.create(**defaults)


def _seed_site_settings(**overrides):
    """Load the SiteSettings singleton (pk=1), set baseline contact fields, then
    apply overrides (e.g. seo_default_title / google_analytics_id). founder_photo=""
    avoids MEDIA flakiness. Identical to SiteSettings.objects.create(...) (singleton).
    """
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.phone_primary = "+381119988776"
    obj.whatsapp_number = "381119988776"
    obj.email_primary = "kontakt@velegradestate.test"
    obj.founder_name = "Đorđije Potpara"
    obj.founder_title_sr = "Privatni savetnik"
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _detail_path(slug):
    return f"/properties/{slug}/"


def _get(client, url):
    resp = client.get(url)
    return resp, resp.content.decode("utf-8")


def _meta_description_content(html):
    """Return the content="" of the <meta name="description"> tag (or "")."""
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
    return m.group(1) if m else ""


def _og_content(html, prop):
    """Return the content="" of the <meta property="og:<prop>"> tag (or "")."""
    m = re.search(
        r'<meta\s+property="og:' + re.escape(prop) + r'"\s+content="([^"]*)"', html
    )
    return m.group(1) if m else ""


def _is_absolute_url(value):
    """True if value is an absolute URL (http:// or https:// or protocol-relative
    //...), False for a relative /static/.../ /media/... path."""
    return value.startswith(("http://", "https://", "//"))


def _ld_json_blocks(html):
    """Return a list of parsed JSON objects from every <script type="application/
    ld+json"> block in the HTML (json.loads on the inner text)."""
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    parsed = []
    for raw in blocks:
        try:
            parsed.append(json.loads(raw))
        except (ValueError, json.JSONDecodeError):
            pass
    return parsed


# =========================================================================== #
# AC1 — per-record meta_title / meta_description + Open Graph (absolute og:image) #
# =========================================================================== #
@pytest.mark.django_db
def test_home_global_meta_from_site_settings(client):
    # AC1: GET / renders <title> and <meta name="description"> from the
    # SiteSettings.seo_default_* singleton (no longer the hardcoded SR default).
    _seed_site_settings(seo_default_title="VG-TITLE", seo_default_description="VG-DESC")
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    assert "VG-TITLE" in html, (
        "GET / <title> must render SiteSettings.seo_default_title 'VG-TITLE' (AC1)."
    )
    assert "VG-DESC" in _meta_description_content(html), (
        "GET / <meta name=description> must render seo_default_description "
        "'VG-DESC' (AC1)."
    )


@pytest.mark.django_db
def test_home_global_og_tags_present_and_image_absolute(client):
    # AC1: GET / <head> exposes og:title/og:description/og:type/og:image, and
    # og:image is an ABSOLUTE URL (NOT a relative /static/... path).
    _seed_site_settings(seo_default_title="VG-TITLE", seo_default_description="VG-DESC")
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    for tag in ("title", "description", "type", "image"):
        assert f'property="og:{tag}"' in html, (
            f"GET / <head> must render an og:{tag} meta tag (AC1)."
        )
    og_image = _og_content(html, "image")
    assert og_image, "og:image must have a content value on GET / (AC1)."
    assert _is_absolute_url(og_image), (
        f"og:image on GET / must be an ABSOLUTE URL (http(s):// or //), not a "
        f"relative /static/ path; got {og_image!r} (AC1)."
    )


@pytest.mark.django_db
def test_property_detail_meta_title_and_description_override(client):
    # AC1: per-property meta_title/meta_description override base on the detail page.
    _seed_site_settings()
    prop = _make_property(
        title="Fallback Naslov",
        meta_title="PROP-META-TITLE",
        meta_description="PROP-META-DESC",
    )
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    assert "PROP-META-TITLE" in html, (
        "the detail <title> must render property.meta_title 'PROP-META-TITLE' (AC1)."
    )
    assert "PROP-META-DESC" in _meta_description_content(html), (
        "the detail <meta name=description> must render property.meta_description "
        "'PROP-META-DESC' (AC1)."
    )


@pytest.mark.django_db
def test_property_detail_title_falls_back_to_title(client):
    # AC1: with meta_title empty, the detail <title> AND the per-property og:title
    # fall back to property.title. (The og:title fallback is the RED marker: the
    # current base.html og:title is the hardcoded "Velegrad Estate" brand string,
    # so a detail page that does NOT override {% block og %} fails here.)
    _seed_site_settings()
    prop = _make_property(title="FALLBACK-TITLE-XYZ", meta_title="")
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    assert "FALLBACK-TITLE-XYZ" in html, (
        "with an empty meta_title the detail <title> must fall back to "
        "property.title 'FALLBACK-TITLE-XYZ' (AC1)."
    )
    assert "FALLBACK-TITLE-XYZ" in _og_content(html, "title"), (
        "with an empty meta_title the per-property og:title must fall back to "
        "property.title 'FALLBACK-TITLE-XYZ' (AC1)."
    )


@pytest.mark.django_db
def test_property_detail_og_title_uses_meta_title(client):
    # AC1: per-property og:title carries the meta_title.
    _seed_site_settings()
    prop = _make_property(title="X", meta_title="PROP-META-TITLE")
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    assert "PROP-META-TITLE" in _og_content(html, "title"), (
        "the detail og:title must contain property.meta_title 'PROP-META-TITLE' (AC1)."
    )


@pytest.mark.django_db
def test_property_detail_og_image_absolute_empty_hero_placeholder(client):
    # AC1 (LOCKED — empty-hero branch): with hero_image="" the placeholder og:image
    # MUST still be an ABSOLUTE URL (the {% static %} placeholder wrapped in
    # scheme://host), NOT a relative /static/.../ /media/... path.
    _seed_site_settings()
    prop = _make_property(meta_title="PROP-META", hero_image="")
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    og_image = _og_content(html, "image")
    assert og_image, "og:image must have a content value (empty-hero branch) (AC1)."
    assert _is_absolute_url(og_image), (
        f"with an EMPTY hero_image the placeholder og:image MUST be ABSOLUTE "
        f"(http(s):// or //) — the {{% static %}} placeholder wrapped in "
        f"scheme://host; got relative {og_image!r} (AC1 LOCKED)."
    )


@pytest.mark.django_db
def test_property_detail_og_image_absolute_populated_hero(client):
    # AC1 (LOCKED — populated-hero branch): with hero_image set, og:image MUST be
    # an ABSOLUTE URL containing the image filename (NOT a relative /media/... path).
    _seed_site_settings()
    prop = _make_property(meta_title="PROP2", hero_image="properties/hero/x.jpg")
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    og_image = _og_content(html, "image")
    assert "x.jpg" in og_image, (
        f"og:image must reference the populated hero_image file 'x.jpg'; got "
        f"{og_image!r} (AC1)."
    )
    assert _is_absolute_url(og_image), (
        f"with a populated hero_image, og:image MUST be ABSOLUTE (http(s):// or //), "
        f"not a relative /media/ path; got {og_image!r} (AC1 LOCKED)."
    )


@pytest.mark.django_db
def test_property_detail_og_url_is_absolute(client):
    # AC1: the detail page exposes an og:url that is an ABSOLUTE URL pointing at the
    # property's canonical path (via get_absolute_url).
    _seed_site_settings()
    prop = _make_property(meta_title="OGURL")
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    og_url = _og_content(html, "url")
    assert og_url, "the detail page must expose an og:url (AC1)."
    assert _is_absolute_url(og_url), (
        f"og:url must be an ABSOLUTE URL (http(s):// or //); got {og_url!r} (AC1)."
    )
    assert _detail_path(prop.slug) in og_url, (
        f"og:url must contain the property's canonical path "
        f"{_detail_path(prop.slug)!r}; got {og_url!r} (AC1)."
    )


@pytest.mark.django_db
def test_property_detail_meta_description_striptags_from_htmlfield(client):
    # AC1 (LOCKED): with meta_description empty and the fallback derived from the
    # HTMLField description, the <meta name=description> must NOT contain raw HTML
    # tags (|striptags applied).
    _seed_site_settings(seo_default_description="GLOBAL-DEFAULT-DESC")
    prop = _make_property(
        meta_description="",
        description_sr="<p><strong>LuksuzniMarker</strong> penthouse opis</p>",
        description_en="<p><strong>LuxuryMarker</strong> penthouse description</p>",
    )
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    desc = _meta_description_content(html)
    # The per-property meta description must derive from THIS property's HTMLField
    # description (striptagged), NOT fall through to the global default. The
    # 'LuksuzniMarker' anchor proves the property description reached <meta> and
    # rules out a false-pass where the (tag-free) global default renders instead.
    assert "LuksuzniMarker" in desc, (
        f"the empty-meta_description detail page must derive its <meta description> "
        f"from the property's HTMLField description ('LuksuzniMarker'), not the "
        f"global default; got {desc!r} (AC1 LOCKED)."
    )
    assert "<strong>" not in desc and "&lt;strong&gt;" not in desc, (
        f"the meta description derived from the HTMLField must have NO raw/escaped "
        f"tags (|striptags applied); got {desc!r} (AC1 LOCKED)."
    )
    assert "<p>" not in desc and "&lt;p&gt;" not in desc, (
        f"the meta description must not contain <p> tags; got {desc!r} (AC1)."
    )


@pytest.mark.django_db
def test_about_page_title_from_meta_title(client):
    # AC1: per-page about title comes from page.meta_title.
    _seed_site_settings()
    _seed_page("about", "Privatno savetovanje", "<p>Bio</p>", meta_title="ABOUT-META")
    resp, html = _get(client, "/about/")
    assert resp.status_code == 200
    assert "ABOUT-META" in html, (
        "GET /about/ <title> must render page.meta_title 'ABOUT-META' (AC1)."
    )


@pytest.mark.django_db
def test_international_page_title_from_meta_title(client):
    # AC1: per-page international title comes from page.meta_title.
    _seed_site_settings()
    _seed_page(
        "international", "Međunarodni klijenti", "<p>Intro</p>",
        meta_title="INTL-META",
    )
    resp, html = _get(client, "/international/")
    assert resp.status_code == 200
    assert "INTL-META" in html, (
        "GET /international/ <title> must render page.meta_title 'INTL-META' (AC1)."
    )


# =========================================================================== #
# AC2 — /sitemap.xml + /robots.txt via django.contrib.sitemaps                 #
# =========================================================================== #
def test_sitemaps_apps_installed_and_site_id():
    # AC2: settings must register django.contrib.sites + django.contrib.sitemaps
    # and pin SITE_ID = 1 (test.py inherits these from base.py).
    assert "django.contrib.sites" in settings.INSTALLED_APPS, (
        "settings.INSTALLED_APPS must contain 'django.contrib.sites' (AC2)."
    )
    assert "django.contrib.sitemaps" in settings.INSTALLED_APPS, (
        "settings.INSTALLED_APPS must contain 'django.contrib.sitemaps' (AC2)."
    )
    assert getattr(settings, "SITE_ID", None) == 1, (
        f"settings.SITE_ID must be 1 for the sitemap framework, got "
        f"{getattr(settings, 'SITE_ID', None)!r} (AC2)."
    )


@pytest.mark.django_db
def test_sitemap_returns_200_xml_with_active_property_and_pages(client):
    # AC2: GET /sitemap.xml -> 200 with an XML content-type and the active Property
    # URL (/properties/<slug>/) plus the active Page URLs (/about/, /international/).
    _seed_site_settings()
    prop = _make_property(title="Vidljiva Sitemap", is_active=True)
    _seed_page("about", "About", "<p>a</p>")
    _seed_page("international", "Intl", "<p>i</p>")
    resp, body = _get(client, "/sitemap.xml")
    assert resp.status_code == 200, (
        f"GET /sitemap.xml must return 200, got {resp.status_code} (AC2)."
    )
    assert "xml" in resp["Content-Type"], (
        f"GET /sitemap.xml Content-Type must be XML, got {resp['Content-Type']!r} (AC2)."
    )
    assert _detail_path(prop.slug) in body, (
        f"the sitemap must contain the active Property URL {_detail_path(prop.slug)!r} "
        f"(AC2)."
    )
    assert "/about/" in body, "the sitemap must contain the active Page URL /about/ (AC2)."
    assert "/international/" in body, (
        "the sitemap must contain the active Page URL /international/ (AC2)."
    )


@pytest.mark.django_db
def test_sitemap_excludes_inactive_property_and_pages(client):
    # AC2: an inactive (is_active=False) Property/Page must NOT appear in the sitemap.
    _seed_site_settings()
    active = _make_property(title="Aktivna", is_active=True)
    inactive = _make_property(title="Neaktivna Sitemap", is_active=False)
    _seed_page("about", "About", "<p>a</p>", is_active=True)
    _seed_page("international", "Intl", "<p>i</p>", is_active=False)
    resp, body = _get(client, "/sitemap.xml")
    assert resp.status_code == 200
    assert _detail_path(active.slug) in body, "the active Property must be present (AC2)."
    assert _detail_path(inactive.slug) not in body, (
        "an inactive (is_active=False) Property must NOT appear in the sitemap (AC2)."
    )
    assert "/about/" in body, "the active about Page must be present (AC2)."
    assert "/international/" not in body, (
        "an inactive (is_active=False) Page must NOT appear in the sitemap (AC2)."
    )


@pytest.mark.django_db
def test_sitemap_body_has_no_en_prefix_even_when_en_active(client):
    # AC2 (LOCKED — SR determinism): even when the active language is 'en' before
    # the request, the canonical sitemap body must contain NO /en/ prefix
    # (location() forces translation.override(LANGUAGE_CODE)).
    _seed_site_settings()
    prop = _make_property(title="SR Determinizam", is_active=True)
    _seed_page("about", "About", "<p>a</p>")
    _seed_page("international", "Intl", "<p>i</p>")
    translation.activate("en")
    try:
        resp, body = _get(client, "/sitemap.xml")
        assert resp.status_code == 200
        assert "/en/" not in body, (
            "the canonical sitemap body must contain NO /en/ prefix even when 'en' is "
            "active (location() must force the SR LANGUAGE_CODE) (AC2 LOCKED)."
        )
        assert _detail_path(prop.slug) in body, (
            "the (SR no-prefix) Property URL must still be present (AC2)."
        )
    finally:
        # C1: explicit cleanup so this test does not rely solely on the conftest
        # autouse fixture (removes the implicit ordering dependency).
        translation.deactivate()


@pytest.mark.django_db
def test_robots_txt_returns_200_text_plain_with_sitemap_and_disallow(client):
    # AC2: GET /robots.txt -> 200, text/plain, with a Sitemap: line to /sitemap.xml
    # and a Disallow: for the admin path (settings.ADMIN_URL).
    resp, body = _get(client, "/robots.txt")
    assert resp.status_code == 200, (
        f"GET /robots.txt must return 200, got {resp.status_code} (AC2)."
    )
    assert "text/plain" in resp["Content-Type"], (
        f"GET /robots.txt Content-Type must be text/plain, got "
        f"{resp['Content-Type']!r} (AC2)."
    )
    assert "Sitemap:" in body and "/sitemap.xml" in body, (
        "robots.txt must contain a 'Sitemap:' line referencing /sitemap.xml (AC2)."
    )
    admin_path = _admin_index_path()
    assert "Disallow:" in body, "robots.txt must contain a 'Disallow:' directive (AC2)."
    assert admin_path in body or settings.ADMIN_URL in body, (
        f"robots.txt must Disallow the admin path {admin_path!r} (AC2)."
    )


@pytest.mark.django_db
def test_en_sitemap_and_robots_are_404(client):
    # AC2: /sitemap.xml and /robots.txt are OUTSIDE i18n_patterns, so the /en/
    # prefixed variants must 404.
    _seed_site_settings()
    resp_sitemap = client.get("/en/sitemap.xml")
    assert resp_sitemap.status_code == 404, (
        f"GET /en/sitemap.xml must 404 (route is OUTSIDE i18n_patterns), got "
        f"{resp_sitemap.status_code} (AC2)."
    )
    resp_robots = client.get("/en/robots.txt")
    assert resp_robots.status_code == 404, (
        f"GET /en/robots.txt must 404 (route is OUTSIDE i18n_patterns), got "
        f"{resp_robots.status_code} (AC2)."
    )


# =========================================================================== #
# AC3 — Schema.org RealEstateListing JSON-LD on Property Detail                 #
# =========================================================================== #
@pytest.mark.django_db
def test_property_detail_has_realestatelisting_jsonld(client):
    # AC3: GET /properties/<slug>/ contains a <script type="application/ld+json">
    # whose parsed JSON has @type=="RealEstateListing", @context contains
    # "schema.org", and name contains the property title.
    _seed_site_settings()
    prop = _make_property(title="VILA-X", price="250000.00", price_on_request=False)
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    assert 'type="application/ld+json"' in html, (
        "the detail page must render a <script type=\"application/ld+json\"> (AC3)."
    )
    blocks = _ld_json_blocks(html)
    listing = next(
        (b for b in blocks if b.get("@type") == "RealEstateListing"), None
    )
    assert listing is not None, (
        f"the detail page must render a RealEstateListing JSON-LD block; parsed "
        f"blocks: {blocks!r} (AC3)."
    )
    assert "schema.org" in str(listing.get("@context", "")), (
        f"the JSON-LD @context must contain 'schema.org', got "
        f"{listing.get('@context')!r} (AC3)."
    )
    assert "VILA-X" in str(listing.get("name", "")), (
        f"the JSON-LD name must contain the property title 'VILA-X', got "
        f"{listing.get('name')!r} (AC3)."
    )


@pytest.mark.django_db
def test_property_detail_jsonld_offers_present_when_priced(client):
    # AC3: a concrete price (price_on_request=False) -> the JSON-LD has offers with
    # price + priceCurrency.
    _seed_site_settings()
    prop = _make_property(title="Sa cenom", price="250000.00", price_on_request=False)
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    listing = next(
        (b for b in _ld_json_blocks(html) if b.get("@type") == "RealEstateListing"),
        None,
    )
    assert listing is not None, "RealEstateListing JSON-LD must render (AC3)."
    offers = listing.get("offers")
    assert offers, (
        f"a priced property must render JSON-LD offers, got {offers!r} (AC3)."
    )
    # offers may be a dict or a list of dicts.
    offer = offers[0] if isinstance(offers, list) else offers
    assert "price" in offer, "the JSON-LD offer must carry a 'price' (AC3)."
    assert "priceCurrency" in offer, (
        "the JSON-LD offer must carry a 'priceCurrency' (AC3)."
    )
    assert offer.get("priceCurrency") == "EUR", (
        f"the JSON-LD offer priceCurrency is LOCKED to 'EUR', got "
        f"{offer.get('priceCurrency')!r} (AC3 LOCKED)."
    )
    assert "250000" in str(offer.get("price")), (
        f"the JSON-LD offer price must reflect 250000, got {offer.get('price')!r} (AC3)."
    )


@pytest.mark.django_db
def test_property_detail_jsonld_no_offers_when_price_on_request(client):
    # AC3: price_on_request=True / price=None -> NO offers in the JSON-LD (it must
    # not render null offers).
    _seed_site_settings()
    prop = _make_property(
        title="Na upit", status="price_on_request", price=None, price_on_request=True
    )
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    listing = next(
        (b for b in _ld_json_blocks(html) if b.get("@type") == "RealEstateListing"),
        None,
    )
    assert listing is not None, "RealEstateListing JSON-LD must render (AC3)."
    assert not listing.get("offers"), (
        f"a price_on_request property must NOT render JSON-LD offers (no null/empty "
        f"offer), got {listing.get('offers')!r} (AC3)."
    )


@pytest.mark.django_db
def test_home_has_no_realestatelisting_jsonld(client):
    # AC3: Schema is ONLY on the detail page — GET / must have NO RealEstateListing
    # JSON-LD block.
    _seed_site_settings()
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    listings = [
        b for b in _ld_json_blocks(html) if b.get("@type") == "RealEstateListing"
    ]
    assert not listings, (
        f"GET / (Home) must NOT render a RealEstateListing JSON-LD block (Schema is "
        f"detail-only), got {listings!r} (AC3)."
    )


# =========================================================================== #
# AC4 — GA4 via SiteSettings.google_analytics_id                               #
# =========================================================================== #
@pytest.mark.django_db
def test_ga4_rendered_on_home_when_id_set(client):
    # AC4: with google_analytics_id="G-TEST123", GET / contains the gtag.js loader
    # (googletagmanager.com/gtag/js?id=G-TEST123) and gtag('config','G-TEST123').
    _seed_site_settings(google_analytics_id="G-TEST123")
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    assert "googletagmanager.com/gtag/js?id=G-TEST123" in html, (
        "GET / must load the GA4 gtag.js with the configured id "
        "(googletagmanager.com/gtag/js?id=G-TEST123) (AC4)."
    )
    assert "gtag('config', 'G-TEST123')" in html or "gtag('config','G-TEST123')" in html, (
        "GET / must call gtag('config', 'G-TEST123') (AC4)."
    )


@pytest.mark.django_db
def test_ga4_rendered_on_property_detail_when_id_set(client):
    # AC4: GA4 lives in base.html, so it is also present on GET /properties/<slug>/.
    _seed_site_settings(google_analytics_id="G-TEST123")
    prop = _make_property()
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    assert "googletagmanager.com/gtag/js?id=G-TEST123" in html, (
        "the detail page (base.html) must also load GA4 when the id is set (AC4)."
    )


@pytest.mark.django_db
def test_ga4_inline_config_value_is_js_escaped(client):
    # AC4 (LOCKED — escapejs): the inline gtag('config', '<id>') value lives in a
    # JS-string context. A raw single quote in the id would break out of the JS
    # string; the value MUST pass through |escapejs (or json_script). With an id
    # carrying a single quote, the rendered HTML must NOT contain the unescaped
    # JS-breaking sequence  config', '<id-with-raw-quote>  — escapejs renders the
    # quote as ' (Django) so the raw quote never closes the string.
    _seed_site_settings(google_analytics_id="G-X'Y")
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    # The loader is present (id is non-empty / non-whitespace -> GA4 renders).
    assert "googletagmanager.com/gtag/js" in html, (
        "a non-empty google_analytics_id must render the GA4 loader (AC4)."
    )
    # The raw id with its unescaped quote must NOT appear inside the inline config
    # call (that would mean |escapejs was omitted and the JS string is broken).
    assert "gtag('config', 'G-X'Y')" not in html and "gtag('config','G-X'Y')" not in html, (
        "the inline gtag('config', ...) value must be JS-escaped (|escapejs); a raw "
        "single quote must never appear unescaped in the JS-string context "
        "(AC4 LOCKED)."
    )
    # The escaped form (Django escapejs emits \\u0027 for ') must be what renders.
    assert "G-X\\u0027Y" in html, (
        "the GA4 id with a single quote must render escapejs-encoded (\\u0027) in "
        "the inline gtag('config', ...) call (AC4 LOCKED)."
    )


@pytest.mark.django_db
def test_ga4_absent_when_id_empty(client):
    # AC4: with google_analytics_id="" (empty), GET / must have NO GA4 scripts.
    _seed_site_settings(google_analytics_id="")
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    assert "googletagmanager" not in html, (
        "with an empty google_analytics_id, GET / must NOT load googletagmanager (AC4)."
    )
    assert "gtag(" not in html, (
        "with an empty google_analytics_id, GET / must NOT call gtag( (AC4)."
    )


@pytest.mark.django_db
def test_ga4_absent_when_id_whitespace_only(client):
    # AC4 (LOCKED): a whitespace-only google_analytics_id ("   ") is treated as
    # "no id" — GET / must have NO GA4 scripts (.strip guard, not a bare {% if %}).
    _seed_site_settings(google_analytics_id="   ")
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    assert "googletagmanager" not in html, (
        "a whitespace-only google_analytics_id must render NO GA4 loader "
        "(.strip guard) (AC4 LOCKED)."
    )
    assert "gtag(" not in html, (
        "a whitespace-only google_analytics_id must render NO gtag( call "
        "(.strip guard) (AC4 LOCKED)."
    )


# =========================================================================== #
# Regression-light smoke (SR + EN both 200)                                     #
# =========================================================================== #
@pytest.mark.django_db
def test_home_sr_and_en_both_return_200(client):
    # Regression smoke: the SEO layer must not break the 6.1 i18n routes — GET /
    # (SR no-prefix) AND GET /en/ (EN prefix) both return 200.
    _seed_site_settings(seo_default_title="VG", seo_default_description="VG-DESC")
    resp_sr = client.get("/")
    assert resp_sr.status_code == 200, (
        f"GET / (SR) must return 200, got {resp_sr.status_code} (regression)."
    )
    resp_en = client.get("/en/")
    assert resp_en.status_code == 200, (
        f"GET /en/ (EN) must return 200, got {resp_en.status_code} (regression)."
    )


# =========================================================================== #
# Batch-fix regression guards (Story 6.2 code-review) — lock reviewed behavior #
# =========================================================================== #
def _listing(html):
    """Return the parsed RealEstateListing JSON-LD block (or None)."""
    return next(
        (b for b in _ld_json_blocks(html) if b.get("@type") == "RealEstateListing"),
        None,
    )


@pytest.mark.django_db
def test_jsonld_image_and_url_are_absolute(client):
    # A1: Schema.org `image` AND `url` are ABSOLUTE URLs (NOT relative), with a
    # POPULATED hero_image the image must still be absolute and reference the file.
    _seed_site_settings()
    prop = _make_property(meta_title="ABS", hero_image="properties/hero/abs.jpg")
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    listing = _listing(html)
    assert listing is not None, "RealEstateListing JSON-LD must render (A1)."
    assert _is_absolute_url(listing.get("image", "")), (
        f"JSON-LD image must be an ABSOLUTE URL; got {listing.get('image')!r} (A1)."
    )
    assert "abs.jpg" in listing.get("image", ""), (
        f"JSON-LD image must reference the populated hero file; got "
        f"{listing.get('image')!r} (A1)."
    )
    assert _is_absolute_url(listing.get("url", "")), (
        f"JSON-LD url must be an ABSOLUTE URL; got {listing.get('url')!r} (A1)."
    )
    assert _detail_path(prop.slug) in listing.get("url", ""), (
        f"JSON-LD url must contain the canonical path; got {listing.get('url')!r} (A1)."
    )


@pytest.mark.django_db
def test_jsonld_description_is_tag_free_from_htmlfield_fallback(client):
    # A2: with meta_description empty, the JSON-LD description falls back from the
    # HTMLField description and is TAG-FREE (strip_tags applied before json.dumps).
    _seed_site_settings()
    prop = _make_property(
        meta_description="",
        description_sr="<p><strong>LuksuzniMarker</strong> opis</p>",
        description_en="<p><strong>LuxuryMarker</strong> description</p>",
    )
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    listing = _listing(html)
    assert listing is not None, "RealEstateListing JSON-LD must render (A2)."
    desc = listing.get("description", "")
    assert "LuksuzniMarker" in desc, (
        f"JSON-LD description must derive from the HTMLField description "
        f"('LuksuzniMarker'); got {desc!r} (A2)."
    )
    for tag in ("<p>", "</p>", "<strong>", "<"):
        assert tag not in desc, (
            f"JSON-LD description must be tag-free (no {tag!r}); got {desc!r} (A2)."
        )


@pytest.mark.django_db
def test_jsonld_address_region_from_district(client):
    # A3: the PostalAddress carries addressLocality (city) AND addressRegion
    # (location_district).
    _seed_site_settings()
    prop = _make_property(
        meta_title="ADDR", location_city="Beograd", location_district="Vračar"
    )
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    listing = _listing(html)
    assert listing is not None, "RealEstateListing JSON-LD must render (A3)."
    address = listing.get("address", {})
    assert address.get("addressLocality") == "Beograd", (
        f"PostalAddress addressLocality must be 'Beograd'; got {address!r} (A3)."
    )
    assert address.get("addressRegion") == "Vračar", (
        f"PostalAddress addressRegion must be 'Vračar' (from location_district); "
        f"got {address!r} (A3)."
    )


@pytest.mark.django_db
def test_jsonld_address_has_no_empty_keys_when_both_blank(client):
    # A3: with both city and district empty, the PostalAddress emits NO empty
    # locality/region keys (and areaServed is not emitted — B3 guard).
    _seed_site_settings()
    prop = _make_property(
        meta_title="NOADDR", location_city="", location_district=""
    )
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    listing = _listing(html)
    assert listing is not None, "RealEstateListing JSON-LD must render (A3)."
    address = listing.get("address", {})
    assert "addressLocality" not in address, (
        f"no empty addressLocality key when city is blank; got {address!r} (A3)."
    )
    assert "addressRegion" not in address, (
        f"no empty addressRegion key when district is blank; got {address!r} (A3)."
    )
    assert "areaServed" not in listing, (
        f"areaServed must NOT be emitted when location_city is blank (B3); got "
        f"{listing.get('areaServed')!r}."
    )


@pytest.mark.django_db
def test_sitemap_has_lastmod_for_property(client):
    # A4: the sitemap XML carries a <lastmod> for the Property entry.
    _seed_site_settings()
    _make_property(title="Lastmod", is_active=True)
    resp, body = _get(client, "/sitemap.xml")
    assert resp.status_code == 200
    assert "<lastmod" in body, (
        "the sitemap must carry a <lastmod> entry (PropertySitemap.lastmod) (A4)."
    )


@pytest.mark.django_db
def test_about_page_meta_description_and_global_fallback(client):
    # A5: a Page with meta_description renders it in <meta name=description>; a Page
    # with an empty meta_description falls back to the global seo_default_description
    # (block.super).
    _seed_site_settings(seo_default_description="GLOBAL-ABOUT-FALLBACK")
    _seed_page("about", "Privatno savetovanje", "<p>Bio</p>",
               meta_description="ABOUT-DESC")
    resp, html = _get(client, "/about/")
    assert resp.status_code == 200
    assert "ABOUT-DESC" in _meta_description_content(html), (
        f"GET /about/ <meta description> must render page.meta_description "
        f"'ABOUT-DESC'; got {_meta_description_content(html)!r} (A5)."
    )

    # Empty meta_description -> fall back to the global default (block.super).
    Page = _get_model("pages", "Page")
    Page.objects.filter(slug="about").update(meta_description="")
    resp2, html2 = _get(client, "/about/")
    assert resp2.status_code == 200
    assert "GLOBAL-ABOUT-FALLBACK" in _meta_description_content(html2), (
        f"with an empty page.meta_description the <meta description> must fall back "
        f"to the global seo_default_description; got "
        f"{_meta_description_content(html2)!r} (A5)."
    )


@pytest.mark.django_db
def test_property_detail_og_description_and_og_type(client):
    # A6: on the PROPERTY DETAIL page specifically, og:description reflects the
    # per-property meta_description and og:type is present.
    _seed_site_settings()
    prop = _make_property(meta_title="OGT", meta_description="PER-PROP-OG-DESC")
    resp, html = _get(client, _detail_path(prop.slug))
    assert resp.status_code == 200
    assert "PER-PROP-OG-DESC" in _og_content(html, "description"), (
        f"the detail og:description must reflect property.meta_description; got "
        f"{_og_content(html, 'description')!r} (A6)."
    )
    og_type = _og_content(html, "type")
    assert og_type, "the detail page must expose an og:type (A6)."
    assert og_type in ("product", "website"), (
        f"the detail og:type must be 'product' or 'website'; got {og_type!r} (A6)."
    )


@pytest.mark.django_db
def test_robots_disallow_admin_on_disallow_line(client):
    # A7: the admin path appears specifically on a "Disallow:" line (tighter than the
    # path appearing anywhere in the doc).
    resp, body = _get(client, "/robots.txt")
    assert resp.status_code == 200
    admin = settings.ADMIN_URL.strip("/")
    pattern = re.compile(r"^Disallow:\s*/" + re.escape(admin) + r"/?\s*$", re.MULTILINE)
    assert pattern.search(body), (
        f"robots.txt must Disallow the admin path on a 'Disallow:' line "
        f"(/{admin}/); body={body!r} (A7)."
    )


@pytest.mark.django_db
def test_ga4_inline_config_escapes_dangerous_chars(client):
    # A8: dangerous chars in google_analytics_id are \u-escaped in the rendered GA4
    # inline script — no raw </script>, no raw unescaped quote/backslash/newline that
    # would break out of the JS string.
    dangerous = 'G-"X\\Y</script>\nZ'
    _seed_site_settings(google_analytics_id=dangerous)
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    # The GA4 loader renders (id is non-empty / non-whitespace).
    assert "googletagmanager.com/gtag/js" in html, (
        "a non-empty google_analytics_id must render the GA4 loader (A8)."
    )
    # Isolate the inline config call so we do not match the loader/CSP/other markup.
    m = re.search(r"gtag\('config',\s*'([^\n]*?)'\);", html)
    assert m is not None, "the inline gtag('config', ...) call must render (A8)."
    inline_value = m.group(1)
    # Each dangerous char must be \u-escaped inside the JS-string value.
    assert '"' not in inline_value, (
        f"a raw double-quote must not survive in the GA4 inline value; got "
        f"{inline_value!r} (A8)."
    )
    assert "\\u0022" in inline_value, "double-quote must be \\u0022-escaped (A8)."
    assert "\\u005C" in inline_value, "backslash must be \\u005C-escaped (A8)."
    assert "\\u003C" in inline_value and "\\u003E" in inline_value, (
        "< and > must be \\u003C / \\u003E-escaped (A8)."
    )
    assert "\\u000A" in inline_value, "newline must be \\u000A-escaped (A8)."
    # The dangerous </script> sequence must NEVER appear raw inside the inline script.
    assert "</script>" not in m.group(0), (
        f"a raw </script> must not appear inside the GA4 inline config call (A8)."
    )


@pytest.mark.django_db
def test_ga4_inline_config_escapes_line_separators(client):
    # AC-4: GA4 JS-string safety (U+2028/U+2029 line-separator escaping regression
    # guard). U+2028 (LINE SEPARATOR) and U+2029 (PARAGRAPH SEPARATOR) are JavaScript
    # line terminators: a RAW U+2028/U+2029 inside the single-quoted inline
    # gtag('config','<id>') string literal breaks the JS string -> potential script
    # breakout. A readability refactor once mapped them to themselves (no-op); this
    # locks them to their 6-char \uXXXX escape form so the raw chars never render.
    _seed_site_settings(google_analytics_id="G-AB CD EF")
    resp, html = _get(client, "/")
    assert resp.status_code == 200
    # The GA4 loader renders (id is non-empty / non-whitespace).
    assert "googletagmanager.com/gtag/js" in html, (
        "a non-empty google_analytics_id must render the GA4 loader (AC-4)."
    )
    # Isolate the inline config call (mirrors the A8 extraction helper).
    m = re.search(r"gtag\('config',\s*'([^\n]*?)'\);", html)
    assert m is not None, "the inline gtag('config', ...) call must render (AC-4)."
    inline_value = m.group(1)
    # A RAW line separator must never survive in the JS-string value.
    assert " " not in inline_value, (
        f"a raw U+2028 LINE SEPARATOR must not survive in the GA4 inline value; "
        f"got {inline_value!r} (AC-4)."
    )
    assert " " not in inline_value, (
        f"a raw U+2029 PARAGRAPH SEPARATOR must not survive in the GA4 inline value; "
        f"got {inline_value!r} (AC-4)."
    )
    # They must render as their escaped (literal backslash-u-2028 / -2029) form.
    assert "\\u2028" in inline_value, (
        "U+2028 must be \\u2028-escaped in the GA4 inline config value (AC-4)."
    )
    assert "\\u2029" in inline_value, (
        "U+2029 must be \\u2029-escaped in the GA4 inline config value (AC-4)."
    )
