"""
RED-phase contract tests for Story 4.1 — "About i International stranice iz CMS-a".

These tests define the CONTRACT for the two public CMS-driven pages — About
(/about/) and International (/international/) — both served by a single
PageDetailView that resolves a Page by slug with an is_active=True gate, plus
two design-faithful templates (templates/about.html, templates/international.html).
They are written BEFORE the feature is built, so EVERY 4.1 test in this module
MUST FAIL/ERROR until the Dev implements:

  * pages.views — a thin page_view(request, slug, template_name) (RECOMMENDED) OR
    a PageDetailView(DetailView) with a fixed slug + custom get_object — resolving
    via get_object_or_404(Page, slug=..., is_active=True) (HomeView/custom_404
    untouched, no new migrations);
  * config/urls.py — EXPLICIT routes path("about/", ..., name="about") and
    path("international/", ..., name="international"), each carrying its own slug +
    template_name, with NO root catch-all and NO i18n_patterns;
  * templates/about.html ({% extends base %} + about-hero/about-portrait/about-bio
    (content_sr|safe) + services-list + why-pillar skeleton + founder from
    site_settings + hardcoded /contact/ CTA + css/pages/about.css);
  * templates/international.html ({% extends base %} + intl-hero/intl-intro
    (content_sr|safe) + curated timeline 01–06 + "Pravni okvir" thematic headings
    + hardcoded /contact/ CTA + css/pages/international.css).

Design / locked rules (mirrors the 2.2 / 3.2 harness):
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * Page is seeded via .objects.create(slug=..., title_sr=..., content_sr=...) —
    title_sr AND content_sr are required (omitting either -> IntegrityError);
    title_en/content_en are blank=True so "" is fine.
  * SiteSettings is seeded via load() -> set founder/contact -> founder_photo=""
    (placeholder branch, no SimpleUploadedFile / MEDIA_ROOT flakiness) -> save().
  * DB content is rendered DIRECTLY via _sr fields ({{ page.title_sr }},
    {{ page.content_sr|safe }}) — NOT .localized() in {{ }}. content_sr is the ONLY
    |safe field (admin-curated HTMLField); title_sr / founder_* are auto-escaped.
  * The CTA is a HARDCODED absolute /contact/ string (NOT {% url 'contact' %} ->
    NoReverseMatch -> 500). The CTA test asserts the STRING href="/contact/" in the
    render WITHOUT issuing an HTTP request to /contact/; a separate regression
    guard asserts GET /contact/ == 404 (route is Story 4.2).
  * founder_photo is tested on BOTH branches: "" -> founder-portrait.svg, and set
    -> the photo .url is rendered (distinct seeds).
  * Anti-"impoverished page": the render must include the curated STATIC design
    sections (About: services-list + why-pillar; International: timeline 01/06 +
    "Pravni okvir"), not just hero + content_sr|safe.
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    4-1-about-i-international-stranice-iz-cms-a-interface-contract.md
"""
import importlib

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape as _escape


# --------------------------------------------------------------------------- #
# Model / path helpers — mirror tests/test_home_page.py + test_admin_dashboard #
# --------------------------------------------------------------------------- #
def _get_model(app_label, class_name):
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


def _admin_index_path():
    """The mounted admin index path, derived from settings.ADMIN_URL."""
    return "/" + settings.ADMIN_URL.strip("/") + "/"


def _superuser(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass12345",
    )


def _try_reverse(name, **kwargs):
    """reverse(name) or None if the route does not exist yet (RED phase)."""
    try:
        return reverse(name, **kwargs)
    except NoReverseMatch:
        return None


# Distinct SiteSettings sentinels so a render-assert proves the exact field
# reached the HTML. FOUNDER_TITLE deliberately contains '&' so the auto-escape
# assertion ('&' -> '&amp;') is meaningful.
FOUNDER_NAME = "Đorđije Potpara"
FOUNDER_TITLE = "Founder & Private Advisor"
PHONE = "+381119988776"
WHATSAPP = "381119988776"
EMAIL = "kontakt@velegradestate.test"

# Page content sentinels — distinct so the render-assert proves the seeded _sr
# field reached the HTML (not an incidental substring collision).
ABOUT_TITLE = "Privatno savetovanje"
ABOUT_CONTENT_TEXT = "Bio osnivaca test jedinstven"
ABOUT_CONTENT = f"<p>{ABOUT_CONTENT_TEXT}</p>"
INTL_TITLE = "Medjunarodni klijenti"
INTL_CONTENT_TEXT = "Vodic za strance test jedinstven"
INTL_CONTENT = f"<p>{INTL_CONTENT_TEXT}</p>"


def _seed_site_settings(**overrides):
    """Load the singleton and populate founder/contact fields.

    founder_photo is blank=True -> set to "" so the {% if %} placeholder branch
    fires (no SimpleUploadedFile / MEDIA_ROOT flakiness). Pass founder_photo=...
    via overrides to exercise the positive (real photo .url) branch.
    """
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.founder_name = FOUNDER_NAME
    obj.founder_title_sr = FOUNDER_TITLE
    obj.phone_primary = PHONE
    obj.whatsapp_number = WHATSAPP
    obj.email_primary = EMAIL
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _seed_page(slug, title_sr, content_sr, is_active=True, **overrides):
    """Create-or-update a Page with the given fields. title_sr AND content_sr are
    required by the schema; title_en/content_en are blank=True so "" is fine.

    Uses update_or_create (NOT create) because the 0002_seed_static_pages data
    migration already seeds Page(slug='about'/'international') into the test DB at
    migration time — a plain create() would raise IntegrityError on the unique
    slug. update_or_create overwrites ALL the fields under test, so the test's
    sentinels/precondition still hold whether or not the row pre-exists.

    NOTE: meta_title/meta_description are explicitly reset to "" in the base
    defaults so they DON'T leak from the seed-migration row — the original
    create() produced a row with blank meta_*, and the <head> tests rely on
    meta_title being empty (so {% block title %} falls back to title_sr). Tests
    that need a meta value pass it via **overrides (which win over the reset).
    """
    Page = _get_model("pages", "Page")
    defaults = dict(
        title_sr=title_sr,
        title_en="",
        content_sr=content_sr,
        content_en="",
        meta_title="",
        meta_description="",
        is_active=is_active,
    )
    defaults.update(overrides)
    obj, _ = Page.objects.update_or_create(slug=slug, defaults=defaults)
    return obj


def _make_property(**overrides):
    """Minimal active Property for the /properties/<slug>/ regression guard."""
    Property = _get_model("properties", "Property")
    defaults = dict(
        title="Regresija Nekretnina",
        status="for_sale",
        collection_type="signature",
        property_type="stan",
        location_city="Beograd",
        location_district="Vracar",
        area_sqm="80.00",
        area_total_sqm="90.00",
        bedrooms=2,
        bathrooms=1,
        floor=3,
        total_floors=5,
        parking_spaces=1,
        description_sr="<p>Opis</p>",
        description_en="<p>Description</p>",
        price="485000.00",
        hero_image="",
        is_featured=False,
        is_active=True,
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


def _get_about(client):
    resp = client.get("/about/")
    return resp, resp.content.decode("utf-8")


def _get_intl(client):
    resp = client.get("/international/")
    return resp, resp.content.decode("utf-8")


# =========================================================================== #
# AC1 — About /about/ 200 from Page(slug='about') + SiteSettings               #
# =========================================================================== #
@pytest.mark.django_db
def test_about_returns_200_and_extends_base(client):
    # AC1: GET /about/ for an active Page(slug="about") -> 200, renders
    # about.html which extends base.html (site-header + site-footer) and loads
    # css/pages/about.css. This is ALSO the guard that no {% url 'contact' %}
    # slipped in (it would NoReverseMatch -> 500).
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp, html = _get_about(client)
    assert resp.status_code == 200, (
        f"GET /about/ for an active Page must return 200 (no {{% url 'contact' %}}, "
        f"no template error), got {resp.status_code} (AC1)."
    )
    template_names = [getattr(t, "name", None) for t in resp.templates]
    assert "about.html" in template_names, (
        f"the About page must render 'about.html', got {template_names} (AC1)."
    )
    assert "site-header" in html and "site-footer" in html, (
        "about.html must extend base.html (site-header + site-footer) (AC1)."
    )
    assert "css/pages/about.css" in html, (
        "about.html must load css/pages/about.css via {% block extra_css %} (AC1)."
    )


@pytest.mark.django_db
def test_about_hero_renders_title_sr(client):
    # AC1: the about-hero section renders with the seeded title_sr (proving DB
    # content reached the hero via the _sr field, NOT .localized() in {{ }}).
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp, html = _get_about(client)
    assert resp.status_code == 200
    assert 'class="about-hero"' in html, (
        "about.html must render <section class=\"about-hero\"> (AC1)."
    )
    assert ABOUT_TITLE in html, (
        f"the about-hero <h1> must render page.title_sr {ABOUT_TITLE!r} (AC1)."
    )


@pytest.mark.django_db
def test_about_renders_content_sr_safe(client):
    # AC1/AC4: page.content_sr (admin-curated HTMLField) renders via |safe inside
    # the about-bio — the <p> is NOT escaped and the inner text appears.
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp, html = _get_about(client)
    assert resp.status_code == 200
    assert ABOUT_CONTENT_TEXT in html, (
        f"the content_sr text {ABOUT_CONTENT_TEXT!r} must render in about-bio (AC1)."
    )
    assert ABOUT_CONTENT in html, (
        f"content_sr must render via |safe (the {ABOUT_CONTENT!r} <p> must NOT be "
        f"escaped) (AC1/AC4)."
    )
    assert f"&lt;p&gt;{ABOUT_CONTENT_TEXT}" not in html, (
        "content_sr must NOT be auto-escaped — it is the only |safe field (AC4)."
    )


@pytest.mark.django_db
def test_about_renders_founder_from_site_settings(client):
    # AC1: founder_name (plain) + founder_title_sr (auto-escaped — contains '&')
    # must render from the global site_settings context processor.
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp, html = _get_about(client)
    assert resp.status_code == 200
    assert FOUNDER_NAME in html, (
        f"About must render site_settings.founder_name {FOUNDER_NAME!r} (AC1)."
    )
    assert _escape(FOUNDER_TITLE) in html, (
        f"About must render founder_title_sr auto-escaped {_escape(FOUNDER_TITLE)!r} "
        f"(plain CharField, no |safe) (AC1/AC4)."
    )


@pytest.mark.django_db
def test_about_renders_static_design_sections(client):
    # AC1 (anti-"impoverished page"): the render MUST include the curated STATIC
    # design sections — services-list AND why-pillar — not just hero + content_sr.
    # NOTE: why-pillar (NOT pillars-grid/pillar — those are HOME classes).
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp, html = _get_about(client)
    assert resp.status_code == 200
    # Markers scoped to the design's class= markup so they tie to the curated
    # sections (not an incidental substring) — a dev who renders only hero +
    # content_sr genuinely fails the anti-impoverished gate.
    assert 'class="services-list"' in html, (
        "about.html must render the <ul class=\"services-list\"> section "
        "(anti-impoverished static skeleton) (AC1)."
    )
    assert 'class="why-pillar' in html, (
        "about.html must render the why-pillar section (anti-impoverished static "
        "skeleton) — NOT pillars-grid/pillar (those are HOME classes) (AC1)."
    )


@pytest.mark.django_db
def test_about_cta_links_hardcoded_contact(client):
    # AC1/AC5: the About CTA links to the HARDCODED absolute href="/contact/"
    # (NOT {% url 'contact' %} -> NoReverseMatch). Asserts the STRING only — does
    # NOT issue an HTTP request to /contact/ (route is Story 4.2).
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp, html = _get_about(client)
    assert resp.status_code == 200
    assert 'href="/contact/"' in html, (
        "the About CTA must link to the hardcoded absolute href=\"/contact/\" "
        "(NOT {% url 'contact' %}) (AC1/AC5)."
    )


@pytest.mark.django_db
def test_about_uses_placeholder_when_no_photo(client):
    # AC1/AC4 (placeholder branch): with founder_photo="" the about-portrait
    # references the founder-portrait.svg placeholder.
    _seed_site_settings(founder_photo="")
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp, html = _get_about(client)
    assert resp.status_code == 200
    assert "founder-portrait.svg" in html, (
        "with no founder_photo the about-portrait must reference "
        "images/placeholders/founder-portrait.svg (AC1/AC4 placeholder branch)."
    )


@pytest.mark.django_db
def test_about_renders_real_photo_url_when_set(client):
    # AC4 (positive branch): with founder_photo SET, the render must reference the
    # real photo .url (NOT the placeholder SVG). Distinct seed complements the
    # placeholder-fallback test.
    _seed_site_settings(founder_photo="site/founder-real.jpg")
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp, html = _get_about(client)
    assert resp.status_code == 200
    assert "founder-real.jpg" in html, (
        "with founder_photo set, the about-portrait must render the real photo "
        ".url ('founder-real.jpg') (AC4 positive branch)."
    )
    assert "founder-portrait.svg" not in html, (
        "with founder_photo set, the placeholder founder-portrait.svg must NOT be "
        "rendered (the {% if %} chose the real photo branch) (AC4)."
    )


# =========================================================================== #
# AC2 — International /international/ 200 from Page(slug='international')        #
# =========================================================================== #
@pytest.mark.django_db
def test_international_returns_200_and_extends_base(client):
    # AC2: GET /international/ for an active Page(slug="international") -> 200,
    # renders international.html extending base.html and loading
    # css/pages/international.css.
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT)
    resp, html = _get_intl(client)
    assert resp.status_code == 200, (
        f"GET /international/ for an active Page must return 200, got "
        f"{resp.status_code} (AC2)."
    )
    template_names = [getattr(t, "name", None) for t in resp.templates]
    assert "international.html" in template_names, (
        f"the International page must render 'international.html', got "
        f"{template_names} (AC2)."
    )
    assert "site-header" in html and "site-footer" in html, (
        "international.html must extend base.html (site-header + site-footer) (AC2)."
    )
    assert "css/pages/international.css" in html, (
        "international.html must load css/pages/international.css via "
        "{% block extra_css %} (AC2)."
    )


@pytest.mark.django_db
def test_international_hero_renders_title_sr(client):
    # AC2: the intl-hero section renders with the seeded title_sr.
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT)
    resp, html = _get_intl(client)
    assert resp.status_code == 200
    assert 'class="intl-hero"' in html, (
        "international.html must render <section class=\"intl-hero\"> (AC2)."
    )
    assert INTL_TITLE in html, (
        f"the intl-hero <h1> must render page.title_sr {INTL_TITLE!r} (AC2)."
    )


@pytest.mark.django_db
def test_international_renders_content_sr_safe(client):
    # AC2/AC4: page.content_sr renders via |safe inside intl-intro — the <p> is
    # NOT escaped and the inner text appears.
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT)
    resp, html = _get_intl(client)
    assert resp.status_code == 200
    assert INTL_CONTENT_TEXT in html, (
        f"the content_sr text {INTL_CONTENT_TEXT!r} must render in intl-intro (AC2)."
    )
    assert INTL_CONTENT in html, (
        f"content_sr must render via |safe (the {INTL_CONTENT!r} <p> must NOT be "
        f"escaped) (AC2/AC4)."
    )


@pytest.mark.django_db
def test_international_renders_static_timeline_and_thematic_sections(client):
    # AC2 (anti-"impoverished page"): the render MUST include the curated STATIC
    # timeline (class + the FIRST and LAST step numbers 01 and 06) AND at least
    # the "Pravni okvir" thematic heading — not just hero + content_sr.
    #
    # The "01"/"06" markers are SCOPED to the design's timeline__number markup
    # (`<div class="timeline__number">01</div>`) — a bare `"01" in html` would
    # be a false-pass risk (2-char substrings collide with years/phones/coords).
    # Scoping ties the step numbers to the curated timeline structure, so a dev
    # who strips the timeline (renders only hero + content_sr) genuinely fails.
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT)
    resp, html = _get_intl(client)
    assert resp.status_code == 200
    assert 'class="timeline' in html, (
        "international.html must render the <div class=\"timeline\"> section "
        "(anti-impoverished static skeleton) (AC2)."
    )
    assert "timeline__step" in html, (
        "the curated timeline must render its timeline__step items "
        "(anti-impoverished static skeleton) (AC2)."
    )
    # First (01) and last (06) curated steps, scoped to timeline__number so the
    # marker cannot false-pass on an incidental "01"/"06" substring elsewhere.
    assert 'timeline__number">01<' in html, (
        "the curated timeline must render its FIRST step number "
        "(<div class=\"timeline__number\">01</div>) — not just the wrapper (AC2)."
    )
    assert 'timeline__number">06<' in html, (
        "the curated timeline must render its LAST step number "
        "(<div class=\"timeline__number\">06</div>) — proving the full 01–06 "
        "skeleton rendered, not a truncated stub (AC2)."
    )
    assert "Pravni okvir" in html, (
        "international.html must render the 'Pravni okvir' thematic heading "
        "(anti-impoverished static skeleton) (AC2)."
    )


@pytest.mark.django_db
def test_international_cta_links_hardcoded_contact(client):
    # AC2/AC5: the International CTA links to the HARDCODED absolute
    # href="/contact/" (NOT {% url %}). String-only assert (no HTTP to /contact/).
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT)
    resp, html = _get_intl(client)
    assert resp.status_code == 200
    assert 'href="/contact/"' in html, (
        "the International CTA must link to the hardcoded absolute "
        "href=\"/contact/\" (NOT {% url 'contact' %}) (AC2/AC5)."
    )


# =========================================================================== #
# AC3a — PageDetailView gating (slug + is_active=True -> 404 otherwise)         #
# =========================================================================== #
@pytest.mark.django_db
def test_about_unseeded_returns_404(client):
    # AC3a: with NO Page(slug="about") seeded, GET /about/ -> 404 (intentional MVP
    # gating, NOT a graceful "coming soon" placeholder).
    # NOTE: 0002_seed_static_pages seeds Page(slug='about') into the test DB at
    # migration time; delete it here to re-establish the genuine "unseeded"
    # precondition this AC describes (the 404-when-absent assertion is unchanged).
    _seed_site_settings()
    _get_model("pages", "Page").objects.filter(slug="about").delete()
    resp = client.get("/about/")
    assert resp.status_code == 404, (
        "GET /about/ with no seeded Page(slug='about') must return 404 (intentional "
        f"gating, not graceful), got {resp.status_code} (AC3a)."
    )


@pytest.mark.django_db
def test_international_unseeded_returns_404(client):
    # AC3a: with NO Page(slug="international") seeded, GET /international/ -> 404.
    # NOTE: 0002_seed_static_pages seeds Page(slug='international') at migration
    # time; delete it to re-establish the genuine "unseeded" precondition (the
    # 404-when-absent assertion is unchanged).
    _seed_site_settings()
    _get_model("pages", "Page").objects.filter(slug="international").delete()
    resp = client.get("/international/")
    assert resp.status_code == 404, (
        "GET /international/ with no seeded Page(slug='international') must return "
        f"404 (intentional gating), got {resp.status_code} (AC3a)."
    )


@pytest.mark.django_db
def test_about_inactive_returns_404_anonymous(client):
    # AC3a: Page(slug="about", is_active=False) -> GET /about/ -> 404 for an
    # anonymous visitor (is_active filter is in the query).
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT, is_active=False)
    resp = client.get("/about/")
    assert resp.status_code == 404, (
        "an inactive Page(slug='about') must 404 for anonymous visitors, got "
        f"{resp.status_code} (AC3a)."
    )


@pytest.mark.django_db
def test_about_inactive_returns_404_even_for_superuser(client, django_user_model):
    # AC3a: Page has NO preview field — is_active=False -> 404 even for a logged-in
    # superuser (gating is pure is_active=True, NOT a can_preview pattern).
    _seed_site_settings()
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT, is_active=False)
    resp = client.get("/about/")
    assert resp.status_code == 404, (
        "an inactive Page must 404 even for a logged-in superuser (Page has no "
        f"preview field — pure is_active gating), got {resp.status_code} (AC3a)."
    )


@pytest.mark.django_db
def test_international_inactive_returns_404_anonymous(client):
    # AC3a (TEST_GAP — symmetry with About): Page(slug="international",
    # is_active=False) -> GET /international/ -> 404 for an anonymous visitor
    # (is_active filter is in the query). Mirrors test_about_inactive_returns_404_anonymous.
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT, is_active=False)
    resp = client.get("/international/")
    assert resp.status_code == 404, (
        "an inactive Page(slug='international') must 404 for anonymous visitors, got "
        f"{resp.status_code} (AC3a)."
    )


@pytest.mark.django_db
def test_international_inactive_returns_404_even_for_superuser(client, django_user_model):
    # AC3a (TEST_GAP — symmetry with About): Page has NO preview field —
    # is_active=False -> 404 even for a logged-in superuser (gating is pure
    # is_active=True, NOT a can_preview pattern). Mirrors
    # test_about_inactive_returns_404_even_for_superuser.
    _seed_site_settings()
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    _seed_page("international", INTL_TITLE, INTL_CONTENT, is_active=False)
    resp = client.get("/international/")
    assert resp.status_code == 404, (
        "an inactive Page(slug='international') must 404 even for a logged-in "
        "superuser (Page has no preview field — pure is_active gating), got "
        f"{resp.status_code} (AC3a)."
    )


# =========================================================================== #
# AC3b — i18n boundary (named routes; /en/ NOT introduced in 4.1)              #
# =========================================================================== #
def test_about_route_reverses_to_expected_path():
    # AC3b: reverse("about") == "/about/" (named route, NOT /en/about/).
    url = _try_reverse("about")
    assert url == "/about/", (
        f"reverse('about') must equal '/about/' (named route, no /en/ prefix), "
        f"got {url!r} (AC3b)."
    )


def test_international_route_reverses_to_expected_path():
    # AC3b: reverse("international") == "/international/".
    url = _try_reverse("international")
    assert url == "/international/", (
        f"reverse('international') must equal '/international/', got {url!r} (AC3b)."
    )


@pytest.mark.django_db
def test_en_international_returns_200_with_i18n_patterns(client):
    # AC3b (INVERTED by Story 6.1): GET /en/international/ -> 200, proving
    # i18n_patterns / the /en/ prefix IS now introduced (Epik 6). Was a NEGATIVE
    # 404 smoke-check pre-6.1; now a positive EN-route resolution check.
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT)
    resp = client.get("/en/international/")
    assert resp.status_code == 200, (
        "GET /en/international/ must return 200 — 6.1 adds i18n_patterns / "
        f"the /en/ prefix, got {resp.status_code} (AC3b)."
    )


@pytest.mark.django_db
def test_en_about_returns_200_with_i18n_patterns(client):
    # AC3b (INVERTED by Story 6.1): GET /en/about/ -> 200, proving i18n_patterns /
    # the /en/ prefix IS now introduced (Epik 6). Mirrors
    # test_en_international_returns_200_with_i18n_patterns.
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT)
    resp = client.get("/en/about/")
    assert resp.status_code == 200, (
        "GET /en/about/ must return 200 — 6.1 adds i18n_patterns / "
        f"the /en/ prefix, got {resp.status_code} (AC3b)."
    )


# =========================================================================== #
# AC4 — content |safe vs CharField auto-escape (XSS)                           #
# =========================================================================== #
@pytest.mark.django_db
def test_about_title_xss_is_escaped_but_content_is_safe(client):
    # AC4: a Page title_sr with a <script> payload must be HTML-escaped (plain
    # CharField, no |safe), while content_sr's <p> renders unescaped (|safe — the
    # admin-curated HTMLField trust boundary).
    _seed_site_settings()
    _seed_page("about", "<script>alert(1)</script>", "<p>ok</p>")
    resp, html = _get_about(client)
    assert resp.status_code == 200
    assert "<script>alert(1)</script>" not in html, (
        "a raw <script> from title_sr must NOT appear unescaped (XSS) (AC4)."
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html, (
        "title_sr must be HTML-escaped (&lt;script&gt;...) — auto-escape, no |safe "
        "on the CharField (AC4)."
    )
    assert "<p>ok</p>" in html, (
        "content_sr must render via |safe (the <p> is NOT escaped — admin-curated "
        "HTMLField trust boundary) (AC4)."
    )


@pytest.mark.django_db
def test_international_content_sr_safe_negative_escape(client):
    # AC2/AC4 (TEST_GAP — negative-escape symmetry with About): international
    # content_sr renders raw via |safe (the seeded "<p>...</p>" appears unescaped)
    # AND the escaped form ("&lt;p&gt;...") does NOT appear. Mirrors the
    # test_about_renders_content_sr_safe negative assertion (which International
    # lacked).
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT)
    resp, html = _get_intl(client)
    assert resp.status_code == 200
    assert INTL_CONTENT in html, (
        f"content_sr must render via |safe (the {INTL_CONTENT!r} <p> must NOT be "
        f"escaped) (AC2/AC4)."
    )
    assert f"&lt;p&gt;{INTL_CONTENT_TEXT}" not in html, (
        "content_sr must NOT be auto-escaped — it is the only |safe field (AC4)."
    )


@pytest.mark.django_db
def test_international_title_xss_is_escaped_but_content_is_safe(client):
    # AC4 (TEST_GAP — symmetry with About XSS): a Page title_sr with a <script>
    # payload must be HTML-escaped on International (plain CharField, no |safe),
    # while content_sr's <p> renders unescaped (|safe). Mirrors
    # test_about_title_xss_is_escaped_but_content_is_safe.
    _seed_site_settings()
    _seed_page("international", "<script>alert(2)</script>", "<p>intl-ok</p>")
    resp, html = _get_intl(client)
    assert resp.status_code == 200
    assert "<script>alert(2)</script>" not in html, (
        "a raw <script> from title_sr must NOT appear unescaped on International "
        "(XSS) (AC4)."
    )
    assert "&lt;script&gt;alert(2)&lt;/script&gt;" in html, (
        "title_sr must be HTML-escaped (&lt;script&gt;...) — auto-escape, no |safe "
        "on the CharField (AC4)."
    )
    assert "<p>intl-ok</p>" in html, (
        "content_sr must render via |safe (the <p> is NOT escaped — admin-curated "
        "HTMLField trust boundary) (AC4)."
    )


# =========================================================================== #
# AC4 — <head> meta rendering (<title> + <meta name="description">)            #
# =========================================================================== #
# Distinct meta sentinels so a render-assert proves the exact field reached the
# <head> (not an incidental substring collision with body copy).
ABOUT_META = "About meta opis test jedinstven"
INTL_META = "International meta opis test jedinstven"


@pytest.mark.django_db
def test_about_head_renders_title_and_meta_description(client):
    # AC4 (TEST_GAP — <head> meta): GET /about/ renders <title> containing
    # page.title_sr, and (since meta_description is seeded non-empty) a
    # <meta name="description"> carrying the page's meta_description. base.html's
    # {% block title %} renders "{{ page.title_sr }} — Velegrad Estate" and
    # {% block meta_description %} renders the page value only when non-empty.
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE, ABOUT_CONTENT, meta_description=ABOUT_META)
    resp, html = _get_about(client)
    assert resp.status_code == 200
    assert f"<title>{ABOUT_TITLE} — Velegrad Estate</title>" in html, (
        f"the <head> <title> must contain page.title_sr {ABOUT_TITLE!r} "
        f"('{ABOUT_TITLE} — Velegrad Estate') (AC4 <head> meta)."
    )
    assert f'<meta name="description" content="{ABOUT_META}">' in html, (
        f"with meta_description set, the <head> must render "
        f"<meta name=\"description\" content=\"{ABOUT_META}\"> (AC4 <head> meta)."
    )


@pytest.mark.django_db
def test_international_head_renders_title_and_meta_description(client):
    # AC4 (TEST_GAP — <head> meta): GET /international/ renders <title> containing
    # page.title_sr, and a <meta name="description"> carrying the seeded
    # meta_description. Mirrors the About <head> meta assertion.
    _seed_site_settings()
    _seed_page("international", INTL_TITLE, INTL_CONTENT, meta_description=INTL_META)
    resp, html = _get_intl(client)
    assert resp.status_code == 200
    assert f"<title>{INTL_TITLE} — Velegrad Estate</title>" in html, (
        f"the <head> <title> must contain page.title_sr {INTL_TITLE!r} "
        f"('{INTL_TITLE} — Velegrad Estate') (AC4 <head> meta)."
    )
    assert f'<meta name="description" content="{INTL_META}">' in html, (
        f"with meta_description set, the <head> must render "
        f"<meta name=\"description\" content=\"{INTL_META}\"> (AC4 <head> meta)."
    )


# =========================================================================== #
# AC5 — regression: routes, render, existing pages/admin green; /contact/ 404   #
# =========================================================================== #
def test_manage_py_check_passes():
    # AC5: `manage.py check` runs clean after the view/template/url changes.
    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc} (AC5)")


@pytest.mark.django_db
def test_home_still_returns_200(client):
    # AC5 (2.2 regression): GET / still returns 200.
    _seed_site_settings()
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / (Home) must still return 200, got {resp.status_code} (AC5 regression)."
    )


@pytest.mark.django_db
def test_listing_still_returns_200(client):
    # AC5 (3.1 regression): GET /properties/ listing still 200.
    _seed_site_settings()
    _make_property(title="Listing Regresija")
    resp = client.get("/properties/")
    assert resp.status_code == 200, (
        f"GET /properties/ (listing) must still return 200, got {resp.status_code} "
        f"(AC5 regression)."
    )


@pytest.mark.django_db
def test_property_detail_still_returns_200(client):
    # AC5 (3.2 regression): GET /properties/<slug>/ for an active property still 200.
    _seed_site_settings()
    prop = _make_property(title="Detalj Regresija")
    resp = client.get(f"/properties/{prop.slug}/")
    assert resp.status_code == 200, (
        f"GET /properties/{prop.slug}/ must still return 200, got "
        f"{resp.status_code} (AC5 regression)."
    )


@pytest.mark.django_db
def test_admin_index_still_200_for_superuser(client, django_user_model):
    # AC5 (1.3 regression): the branded admin index still returns 200.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index at {_admin_index_path()} must still return 200 (AC5 regression)."
    )


@pytest.mark.django_db
def test_default_admin_path_still_404(client):
    # AC5 (1.3 regression): GET /admin/ stays 404 (admin mounts on ADMIN_URL).
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must still return 404 (NFR-5), got {resp.status_code} (AC5)."
    )


@pytest.mark.django_db
def test_contact_route_now_200(client):
    # AC5 (4.2 inversion): GET /contact/ -> 200 — Story 4.2 delivers the Contact
    # route, so the original 4.1 guard (test_contact_route_still_404) is inverted
    # here. The About/International CTA href="/contact/" now points at a live route.
    resp = client.get("/contact/")
    assert resp.status_code == 200, (
        "GET /contact/ must return 200 (Story 4.2 delivers the Contact route), got "
        f"{resp.status_code} (AC5)."
    )


@pytest.mark.django_db
def test_no_root_catch_all_unknown_slug_404(client):
    # AC5: a non-existent root path -> 404 (proving there is NO root catch-all
    # path("<slug>/") that would otherwise trap arbitrary slugs).
    _seed_site_settings()
    resp = client.get("/nepostojeci-slug/")
    assert resp.status_code == 404, (
        "a non-existent root path must return 404 (no root catch-all "
        f"path(\"<slug>/\")), got {resp.status_code} (AC5)."
    )


# =========================================================================== #
# Seed migration (0002_seed_static_pages) — pages render WITHOUT explicit       #
# per-test seeding (the data migration populated the test DB at setup).         #
# =========================================================================== #
# Sentinels mirror 0002_seed_static_pages — proves the SEEDED row (not an
# in-test create) reached the render. Kept loose (title + a stable phrase) so
# an admin refining the prose later does not over-couple these tests.
SEED_ABOUT_TITLE = "Privatno savetovanje"
SEED_ABOUT_PHRASE = "Kako radimo"
SEED_INTL_TITLE = "Međunarodni klijenti"
SEED_INTL_PHRASE = "međunarodne investitore u nekretnine"


@pytest.mark.django_db
def test_about_renders_from_seed_migration_without_explicit_seeding(client):
    # The 0002_seed_static_pages data migration runs during test-DB setup, so
    # Page(slug="about") exists WITHOUT any _seed_page call here. GET /about/ must
    # be 200 and render the seeded title_sr + a phrase from the seeded content_sr.
    # This is the regression that guards the production fix: /about/ no longer 404s.
    _seed_site_settings()
    resp, html = _get_about(client)
    assert resp.status_code == 200, (
        f"GET /about/ must return 200 from the seed-migration row (no explicit "
        f"_seed_page), got {resp.status_code}."
    )
    assert SEED_ABOUT_TITLE in html, (
        f"the about-hero <h1> must render the seeded title_sr {SEED_ABOUT_TITLE!r}."
    )
    assert SEED_ABOUT_PHRASE in html, (
        f"the about-bio must render a phrase from the seeded content_sr "
        f"({SEED_ABOUT_PHRASE!r})."
    )


@pytest.mark.django_db
def test_international_renders_from_seed_migration_without_explicit_seeding(client):
    # Mirror for International: Page(slug="international") is seeded by
    # 0002_seed_static_pages at test-DB setup; GET /international/ -> 200 and renders
    # the seeded title_sr + a phrase from the seeded content_sr (intl-intro).
    _seed_site_settings()
    resp, html = _get_intl(client)
    assert resp.status_code == 200, (
        f"GET /international/ must return 200 from the seed-migration row (no "
        f"explicit _seed_page), got {resp.status_code}."
    )
    assert SEED_INTL_TITLE in html, (
        f"the intl-hero <h1> must render the seeded title_sr {SEED_INTL_TITLE!r}."
    )
    assert SEED_INTL_PHRASE in html, (
        f"the intl-intro must render a phrase from the seeded content_sr "
        f"({SEED_INTL_PHRASE!r})."
    )
