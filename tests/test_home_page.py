"""
RED-phase contract tests for Story 2.2 — "Home stranica povezana sa bazom".

These tests define the CONTRACT for the DB-driven Home page: the six design
sections (A–F) rendered inside home.html, the new `site_settings` context
processor, the `HomeView` featured-properties context, and the footer rebind in
base.html. They are written BEFORE the feature is built, so EVERY 2.2 test in
this module MUST FAIL/ERROR until the Dev implements:

  * core/context_processors.py::site_settings(request) -> {"site_settings":
    SiteSettings.load()} + its registration in TEMPLATES context_processors;
  * pages.views.HomeView.get_context_data adding
    context["featured_properties"] = Property.objects.filter(
        is_featured=True, is_active=True)[:4];
  * templates/home.html filled with sections A–F (hero / advisor /
    properties-preview / private-teaser / pillars-grid (6) / contact-teaser) +
    {% block extra_css %} -> css/pages/home.css;
  * templates/base.html footer site-footer__contact-info rebound to
    site_settings.

Design / locked rules (mirrors the 1.3 + 2.1 harness):
  * DB / client tests are marked @pytest.mark.django_db (pytest-django is active
    via DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * DB content is rendered DIRECTLY via _sr fields ({{ ..._sr }}) — NOT
    .localized() in {{ }}. Tests assert the seeded _sr text appears in the HTML.
  * Forward links to not-yet-existing routes are HARDCODED ABSOLUTE hrefs
    (/properties/, /private-collection/, contact -> /) — NOT {% url %}
    (NoReverseMatch -> 500). The "GET / == 200" guard catches any {% url %} slip.
  * hero_image="" / founder_photo="" / Property.hero_image="" exercise the
    placeholder branch (works on SQLite, avoids MEDIA flakiness).
  * Featured count is asserted via html.count('class="property-card"') == 4.
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    2-2-home-stranica-povezana-sa-bazom-interface-contract.md
"""
import importlib

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.test import RequestFactory, override_settings


# --------------------------------------------------------------------------- #
# Model / path helpers — mirror tests/test_admin_dashboard.py conventions.      #
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


# Seeded SiteSettings sentinel values — distinct so a render-assert can prove
# the exact _sr field reached the HTML (not a generic substring collision).
# NOTE: the headline is DELIBERATELY NOT the design's "Diskrecija. Stručnost.
# Rezultati." — that exact phrase already lives in base.html's og:description
# (and the 2.1 placeholder home.html), so asserting it would be a tautology that
# passes even pre-impl. A distinct sentinel proves hero_headline_sr genuinely
# reached the hero via the _sr field (RED fails honestly, GREEN proves binding).
HERO_HEADLINE = "Poverljivo. Posvećeno. Bez kompromisa."
HERO_CTA = "Zakažite privatne konsultacije"
FOUNDER_NAME = "Đorđije Potpara"
FOUNDER_TITLE = "Founder & Private Advisor"
FOUNDER_BIO = "<p>Test bio</p>"
# Contact sentinels are DELIBERATELY DISTINCT from the hardcoded placeholder
# values still living in templates/base.html's 2.1 footer (+381601234567 /
# 381601234567 / info@velegradestate.rs / "Beograd, Srbija"). Using different
# values means these strings can ONLY appear in the render once the footer is
# rebound to site_settings and the advisor/contact sections read the DB — so the
# RED phase fails honestly instead of matching the leftover static placeholder.
PHONE = "+381119988776"
WHATSAPP = "381119988776"
EMAIL = "kontakt@velegradestate.test"
ADDRESS = "Knez Mihailova 1, Beograd"


def _seed_site_settings(**overrides):
    """Load the singleton and populate hero/founder/contact fields.

    hero_image / founder_photo are blank=True -> set to "" so the {% if %}
    placeholder branch fires (no SimpleUploadedFile / MEDIA_ROOT flakiness).
    """
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.hero_headline_sr = HERO_HEADLINE
    obj.hero_cta_text_sr = HERO_CTA
    obj.founder_name = FOUNDER_NAME
    obj.founder_title_sr = FOUNDER_TITLE
    obj.founder_bio_sr = FOUNDER_BIO
    obj.phone_primary = PHONE
    obj.whatsapp_number = WHATSAPP
    obj.email_primary = EMAIL
    obj.address = ADDRESS
    obj.hero_image = ""
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _make_property(**overrides):
    """Create a Property with all required non-null scalar fields supplied.

    hero_image="" passes on SQLite (.create() skips full validation) and is
    falsy in the template -> placeholder branch. Mirrors _make_property in
    tests/test_admin_dashboard.py plus the description_* HTMLFields.
    """
    Property = _get_model("properties", "Property")
    defaults = dict(
        title="Nekretnina",
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
        hero_image="",
        is_featured=False,
        is_active=True,
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


def _seed_featured():
    """Seed the canonical featured fixture.

    4x featured+active (one price_on_request), 1x non-featured, 1x featured but
    inactive. The Home featured grid must show EXACTLY the 4 featured+active.
    """
    _make_property(title="Featured 1", is_featured=True, is_active=True,
                   price="1250000.00")
    _make_property(title="Featured 2", is_featured=True, is_active=True,
                   status="price_on_request", price_on_request=True, price=None)
    _make_property(title="Featured 3", is_featured=True, is_active=True,
                   price="485000.00")
    _make_property(title="Featured 4", is_featured=True, is_active=True,
                   property_type="vila", price="999000.00")
    _make_property(title="Nije izdvojena", is_featured=False, is_active=True)
    _make_property(title="Izdvojena ali neaktivna", is_featured=True,
                   is_active=False)


def _get_home(client):
    resp = client.get("/")
    return resp, resp.content.decode("utf-8")


# =========================================================================== #
# AC1 — Hero from SiteSettings (design section A)                              #
# =========================================================================== #
@pytest.mark.django_db
def test_home_returns_200(client):
    # AC1/AC7: GET / must return 200 with DB content seeded. This is ALSO the
    # guard that no {% url %} on a non-existent route slipped in (it would 500).
    _seed_site_settings()
    _seed_featured()
    resp, _ = _get_home(client)
    assert resp.status_code == 200, (
        f"GET / must return 200 with DB content (no {{% url %}} on a missing "
        f"route, no template error), got {resp.status_code} (AC1/AC7)."
    )


@pytest.mark.django_db
def test_hero_section_present(client):
    # AC1: home.html renders the hero section (class="hero").
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert 'class="hero"' in html, "home.html must render <section class=\"hero\"> (AC1)."


@pytest.mark.django_db
def test_hero_renders_headline_cta_and_founder_from_db(client):
    # AC1: the seeded _sr fields must appear in the rendered hero — proving DB
    # content reached the HTML via _sr (NOT .localized() in {{ }}).
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert HERO_HEADLINE in html, (
        f"hero__tagline must render hero_headline_sr {HERO_HEADLINE!r} (AC1)."
    )
    assert HERO_CTA in html, (
        f"hero__cta must render hero_cta_text_sr {HERO_CTA!r} (AC1)."
    )
    assert FOUNDER_NAME in html, (
        f"hero__kicker must render founder_name {FOUNDER_NAME!r} (AC1)."
    )


@pytest.mark.django_db
def test_hero_uses_placeholder_when_no_image(client):
    # AC1: with hero_image="" the hero references the hero-placeholder.svg.
    _seed_site_settings(hero_image="")
    resp, html = _get_home(client)
    assert resp.status_code == 200
    # Anchor inside the hero section: base.html already references
    # hero-placeholder.svg in its og:image meta, so a whole-HTML substring check
    # would falsely pass in RED. Require the placeholder INSIDE <section class="hero">.
    start = html.find('class="hero"')
    end = html.find("</section>", start) if start != -1 else -1
    hero = html[start:end] if start != -1 and end != -1 else ""
    assert "hero-placeholder.svg" in hero, (
        "with no hero_image the hero SECTION must reference images/placeholders/"
        "hero-placeholder.svg (AC1 placeholder branch) — not just the og:image meta."
    )


# =========================================================================== #
# AC2 — Personal Brand / Advisor section (design section B)                    #
# =========================================================================== #
@pytest.mark.django_db
def test_advisor_section_present(client):
    # AC2: home.html renders the advisor block (class="advisor").
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert 'class="advisor"' in html, "home.html must render the advisor block (AC2)."


@pytest.mark.django_db
def test_advisor_renders_name_title_and_bio_from_db(client):
    # AC2: founder_name + founder_title_sr (rendered _sr) + founder_bio_sr
    # (|safe HTML) must appear in the advisor section.
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert FOUNDER_NAME in html, f"advisor__name must render founder_name (AC2)."
    # founder_title_sr is a plain CharField — rendered WITHOUT |safe, so Django
    # auto-escapes it (security fix: no stored-XSS-via-admin). The sentinel
    # contains '&', which must appear HTML-escaped as '&amp;' in the output.
    from django.utils.html import escape as _escape
    assert _escape(FOUNDER_TITLE) in html, (
        f"advisor__title must render founder_title_sr (auto-escaped) "
        f"{_escape(FOUNDER_TITLE)!r} (AC2)."
    )
    # founder_bio_sr is rendered with |safe; "Test bio" must appear unescaped.
    assert "Test bio" in html, (
        "advisor__text must render founder_bio_sr ('Test bio') via |safe (AC2)."
    )


@pytest.mark.django_db
def test_advisor_renders_phone_and_whatsapp_from_db(client):
    # AC2: advisor__contact CTA links tel:phone_primary and wa.me/whatsapp_number.
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert f"tel:{PHONE}" in html, (
        f"advisor contact must render tel:{PHONE} from phone_primary (AC2)."
    )
    assert f"wa.me/{WHATSAPP}" in html, (
        f"advisor contact must render wa.me/{WHATSAPP} from whatsapp_number (AC2)."
    )


@pytest.mark.django_db
def test_advisor_uses_placeholder_when_no_photo(client):
    # AC2: with founder_photo="" the portrait references founder-portrait.svg.
    _seed_site_settings(founder_photo="")
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert "founder-portrait.svg" in html, (
        "with no founder_photo the advisor portrait must reference "
        "images/placeholders/founder-portrait.svg (AC2 placeholder branch)."
    )


# =========================================================================== #
# AC3 — Featured Property preview (design section C)                           #
# =========================================================================== #
@pytest.mark.django_db
def test_featured_grid_present(client):
    # AC3: home.html renders the properties-preview__grid container.
    _seed_site_settings()
    _seed_featured()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert "properties-preview__grid" in html, (
        "home.html must render the properties-preview__grid (AC3)."
    )


@pytest.mark.django_db
def test_featured_renders_exactly_four_cards(client):
    # AC3: exactly 4 property-card markers — is_active=False featured AND
    # non-featured are excluded (6 seeded, only 4 featured+active shown).
    _seed_site_settings()
    _seed_featured()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    count = html.count('class="property-card"')
    assert count == 4, (
        f"the featured grid must render EXACTLY 4 property-card markers "
        f"(is_featured=True, is_active=True, [:4]) — not 5 or 6; got {count} "
        f"(AC3). Inactive-featured and non-featured must be excluded."
    )


@pytest.mark.django_db
def test_featured_shows_price_on_request(client):
    # AC3: the price_on_request featured property renders "Cena na upit".
    _seed_site_settings()
    _seed_featured()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert "Cena na upit" in html, (
        "a featured property with price_on_request=True must render "
        "'Cena na upit' in its price slot (AC3)."
    )


@pytest.mark.django_db
def test_featured_section_links_to_listing_absolute_href(client):
    # AC3: the section links to /properties/ via a HARDCODED absolute href
    # (NOT {% url %} — that route does not exist yet -> NoReverseMatch -> 500).
    _seed_site_settings()
    _seed_featured()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert 'href="/properties/"' in html, (
        "the featured section must link to the listing via the hardcoded "
        "absolute href=\"/properties/\" (NOT {% url %}) (AC3)."
    )


@pytest.mark.django_db
def test_featured_empty_state_no_fake_cards(client):
    # AC3: with 0 featured the section renders a graceful {% empty %} message
    # and NO property-card markers (no fake cards).
    _seed_site_settings()
    # No featured seeded.
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert html.count('class="property-card"') == 0, (
        "with 0 featured properties the grid must render NO property-card "
        "markers (graceful {% empty %}, no fake cards) (AC3)."
    )


@pytest.mark.django_db
def test_featured_card_uses_property_placeholder_when_no_image(client):
    # AC3: a featured Property with hero_image="" renders a property placeholder
    # SVG inside the featured grid (the {% if p.hero_image %}...{% else %}
    # property-N.svg placeholder branch). Per Dev Notes the placeholder rotates
    # property-1..4.svg by forloop index, so distinct cards get distinct SVGs.
    _seed_site_settings()
    _seed_featured()  # 4 featured+active, all hero_image="" -> placeholder branch
    resp, html = _get_home(client)
    assert resp.status_code == 200
    # Isolate the featured grid section so a stray placeholder elsewhere can't
    # falsely satisfy the assertion.
    start = html.find("properties-preview__grid")
    end = html.find("</section>", start) if start != -1 else -1
    grid = html[start:end] if start != -1 and end != -1 else ""
    assert "images/placeholders/property-" in grid, (
        "a featured Property with no hero_image must render a property "
        "placeholder SVG ('images/placeholders/property-') inside the featured "
        "grid (AC3 placeholder branch)."
    )
    # Rotation: with 4 placeholder cards, at least two DISTINCT placeholders
    # (property-1.svg and property-2.svg) must appear — proving forloop-index
    # rotation, not the same SVG four times.
    assert "property-1.svg" in grid and "property-2.svg" in grid, (
        "the 4 placeholder cards must rotate distinct SVGs (property-1.svg, "
        "property-2.svg, ...) by forloop index, not repeat a single one (AC3)."
    )


# =========================================================================== #
# AC4 — Private Collection teaser + Contact teaser (design sections D & F)      #
# =========================================================================== #
@pytest.mark.django_db
def test_private_teaser_present_with_absolute_link_and_no_cards(client):
    # AC4: private-teaser links to /private-collection/ (absolute) and contains
    # NO property-card (FR4 — teaser is text + link only, zero properties).
    _seed_site_settings()
    _seed_featured()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert 'class="private-teaser"' in html, (
        "home.html must render the private-teaser section (AC4)."
    )
    assert 'href="/private-collection/"' in html, (
        "the private teaser must link to the hardcoded absolute "
        "href=\"/private-collection/\" (NOT {% url %}) (AC4)."
    )
    # Isolate the private-teaser section and assert no property-card inside it.
    start = html.find('class="private-teaser"')
    end = html.find("</section>", start)
    section = html[start:end] if end != -1 else html[start:]
    assert 'class="property-card"' not in section, (
        "the private-teaser must contain NO property-card — it is text + link "
        "only (FR4) (AC4)."
    )


@pytest.mark.django_db
def test_contact_teaser_present_with_tel_and_no_form(client):
    # AC4: contact-teaser has the links wrapper, a tel: from phone_primary, and
    # NO <form> (the contact form is Epik 4).
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert 'class="contact-teaser"' in html, (
        "home.html must render the contact-teaser section (AC4)."
    )
    assert "contact-teaser__links" in html, (
        "the contact teaser must render the contact-teaser__links wrapper (AC4)."
    )
    assert f"tel:{PHONE}" in html, (
        f"the contact teaser must render tel:{PHONE} from phone_primary (AC4)."
    )
    start = html.find('class="contact-teaser"')
    end = html.find("</section>", start)
    section = html[start:end] if end != -1 else html[start:]
    assert "<form" not in section, (
        "the contact teaser must be CTA-only — NO <form> (the form is Epik 4) "
        "(AC4)."
    )


# =========================================================================== #
# AC5 — Why Velegrad: exactly 6 pillars (design section E)                      #
# =========================================================================== #
@pytest.mark.django_db
def test_pillars_grid_present(client):
    # AC5: home.html renders the pillars-grid container (Why Velegrad as a Home
    # section, not a separate route).
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert "pillars-grid" in html, "home.html must render the pillars-grid (AC5)."


@pytest.mark.django_db
def test_pillars_grid_has_exactly_six_pillars(client):
    # AC5: exactly 6 pillar blocks.
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    count = html.count('class="pillar"')
    assert count == 6, (
        f"the Why Velegrad section must render EXACTLY 6 pillar blocks "
        f"(class=\"pillar\"); got {count} (AC5)."
    )


@pytest.mark.django_db
def test_pillars_include_first_and_last_titles(client):
    # AC5: the first ("Diskrecija") and last ("Pouzdanost") pillar titles render.
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert "Diskrecija" in html, "the first pillar title 'Diskrecija' must render (AC5)."
    assert "Pouzdanost" in html, "the last pillar title 'Pouzdanost' must render (AC5)."


# =========================================================================== #
# AC6 — site_settings context processor + footer rebind                        #
# =========================================================================== #
def test_site_settings_context_processor_registered():
    # AC6: "core.context_processors.site_settings" must be registered in
    # TEMPLATES[0]["OPTIONS"]["context_processors"].
    procs = settings.TEMPLATES[0]["OPTIONS"]["context_processors"]
    assert "core.context_processors.site_settings" in procs, (
        "'core.context_processors.site_settings' must be in "
        "TEMPLATES[0]['OPTIONS']['context_processors'] (AC6)."
    )


@pytest.mark.django_db
def test_site_settings_context_processor_returns_singleton():
    # AC6: the context processor callable returns {"site_settings": <instance>}.
    # Needs DB access — calls SiteSettings.load() -> get_or_create(pk=1).
    cp = importlib.import_module("core.context_processors")
    SiteSettings = _get_model("core", "SiteSettings")
    # Pass a real request (RequestFactory) instead of None so a future
    # context-processor that touches request.* won't raise AttributeError.
    result = cp.site_settings(RequestFactory().get("/"))
    assert isinstance(result, dict) and "site_settings" in result, (
        "site_settings(request) must return a dict with key 'site_settings' (AC6)."
    )
    assert isinstance(result["site_settings"], SiteSettings), (
        "site_settings(request)['site_settings'] must be a SiteSettings instance "
        "(SiteSettings.load()) (AC6)."
    )


@pytest.mark.django_db
def test_footer_contact_bound_to_db(client):
    # AC6: the footer renders contact data FROM the seeded SiteSettings (tel /
    # mailto / wa.me / address) — proving the footer is DB-bound, not hardcoded.
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    # Isolate the footer to assert the contact data comes from the footer block.
    fstart = html.find("site-footer")
    footer = html[fstart:] if fstart != -1 else html
    assert f"tel:{PHONE}" in footer, f"footer must render tel:{PHONE} from DB (AC6)."
    assert f"mailto:{EMAIL}" in footer, (
        f"footer must render mailto:{EMAIL} from DB (AC6)."
    )
    assert f"wa.me/{WHATSAPP}" in footer, (
        f"footer must render wa.me/{WHATSAPP} from DB (AC6)."
    )
    assert "Knez Mihailova 1" in footer, (
        "footer must render the seeded address ('Knez Mihailova 1') from DB — "
        "the distinct value proves the footer is DB-bound, not the leftover "
        "static placeholder (AC6)."
    )


@pytest.mark.django_db
def test_blank_site_settings_renders_graceful_empty_contact(client):
    # AC6: with an all-blank SiteSettings (the lazy-created singleton, no
    # phone/email/whatsapp/address seeded), GET / must still return 200 and the
    # footer/advisor/contact {% if %} guards must OMIT broken/empty
    # tel:/mailto:/wa.me links (no href="tel:" with an empty value, no 500).
    # NOTE: we deliberately do NOT call _seed_site_settings() — the context
    # processor's SiteSettings.load() lazily creates a blank singleton.
    resp, html = _get_home(client)
    assert resp.status_code == 200, (
        "GET / with an all-blank SiteSettings must still return 200 (the "
        "{% if %} guards prevent a 500), got %s (AC6)." % resp.status_code
    )
    assert "tel:" not in html, (
        "with a blank phone_primary the {% if %} guard must OMIT every "
        "href=\"tel:\" link (no broken/empty tel: link) (AC6)."
    )
    assert "mailto:" not in html, (
        "with a blank email_primary the {% if %} guard must OMIT the "
        "href=\"mailto:\" link (no broken/empty mailto: link) (AC6)."
    )
    assert "wa.me" not in html, (
        "with a blank whatsapp_number the {% if %} guard must OMIT the "
        "wa.me link (no broken/empty WhatsApp link) (AC6)."
    )


# =========================================================================== #
# AC7 — home.css included, render clean, regression preserved                  #
# =========================================================================== #
@pytest.mark.django_db
def test_home_includes_pages_home_css(client):
    # AC7: home.html loads css/pages/home.css via {% block extra_css %}.
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert "css/pages/home.css" in html, (
        "home.html must load css/pages/home.css via {% block extra_css %} (AC7)."
    )


@pytest.mark.django_db
def test_home_still_renders_base_frame(client):
    # AC7: GET / still renders inside the base frame (site-header + site-footer).
    _seed_site_settings()
    resp, html = _get_home(client)
    assert resp.status_code == 200
    assert "site-header" in html and "site-footer" in html, (
        "GET / must still render within the base frame (site-header + "
        "site-footer) (AC7 regression)."
    )


def test_manage_py_check_passes():
    # AC7: `manage.py check` runs clean after the context processor + view +
    # template changes.
    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc}")


@pytest.mark.django_db
def test_admin_index_still_200_for_superuser(client, django_user_model):
    # AC7 (1.3 regression): the branded admin index still returns 200.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index at {_admin_index_path()} must still return 200 (AC7)."
    )


@pytest.mark.django_db
def test_default_admin_path_still_404(client):
    # AC7 (1.3 regression): GET /admin/ stays 404 (admin mounts on ADMIN_URL).
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must still return 404 (NFR-5), got {resp.status_code} (AC7)."
    )


@override_settings(DEBUG=False)
@pytest.mark.django_db
def test_custom_404_still_served(client):
    # AC7 (2.1 regression): with DEBUG=False a non-existent path returns 404 with
    # the premium error-page markup.
    resp = client.get("/nepostojeca-stranica/")
    assert resp.status_code == 404, (
        f"a non-existent path must return 404, got {resp.status_code} (AC7)."
    )
    html = resp.content.decode("utf-8")
    assert "error-page" in html, (
        "the custom 404 must still render the premium 'error-page' markup (AC7)."
    )
