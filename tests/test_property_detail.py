"""
RED-phase contract tests for Story 3.2 — "Property Detail stranica" + the FIRST
DB write (Inquiry(viewing) mini-form).

These tests define the CONTRACT for the public Property Detail page at
/properties/<slug>/ and the agent-contact mini Inquiry form. They are written
BEFORE the feature is built, so EVERY 3.2 test in this module MUST FAIL/ERROR
until the Dev implements:

  * properties/views.py::PropertyDetailView — GET resolves via
    get_object_or_404(Property, slug=...) + can_preview() gating (404 for
    missing / inactive-to-public; staff ?preview=1 -> 200); POST handles
    InquiryForm (honeypot, server-set fields, PRG redirect to ?sent=1);
  * inquiries/forms.py::InquiryForm(ModelForm) — Meta.fields = exactly
    [name, email, phone, message] + a non-model honeypot `website` field;
    inquiry_type/property/status/preferred_language are NEVER form fields;
  * config/urls.py route path("properties/<slug:slug>/", ...,
    name="property-detail");
  * templates/property-detail.html ({% extends base %} + detail-hero <img> +
    thumbnail-strip + lightbox + detail-sidebar/def-table + detail-description
    (description_sr|safe) + amenity-grid + detail-floorplan + #property-map +
    agent-block + agent-block__form) — WITHOUT data-validate and WITHOUT
    loading js/forms.js (the forms.js hijack trap).

Design / locked rules (mirrors the 2.2 / 3.1 harness):
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * Property is seeded via .objects.create(hero_image="") — full_clean() is
    NEVER called (hero_image has no blank=True; create() skips validation on
    SQLite). description_en is NOT NULL but may be minimal (template renders only
    description_sr in 3.2).
  * PropertyImage rows are seeded with DISTINCT image URLs (gallery.js dedups by
    URL — same hero/thumb URL would be skipped).
  * The Inquiry POST is the FIRST DB write: count() is the reliable marker.
    server-side fields (inquiry_type/property/status/preferred_language) must
    win over any client-supplied (tampering) POST values.
  * No |safe except description_sr (admin-curated HTMLField). Auto-escape proven
    via title='<script>'.
  * Email: 5.2 SADA šalje preko create_inquiry seam-a — kad je email_inquiries
    seed-ovan, jedan validan viewing POST pošalje 2 mejla (agent + auto-reply).
    Ovi testovi su već invertovani da to potvrde (ne više mail.outbox == 0).
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    3-2-property-detail-stranica-interface-contract.md
"""
import importlib

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.test import Client
from django.urls import NoReverseMatch, reverse


# --------------------------------------------------------------------------- #
# Model / path helpers — mirror tests/test_property_listing.py + admin_dashboard #
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


def _make_property(**overrides):
    """Create a Property with all required non-null scalar fields supplied.

    hero_image="" passes on SQLite (.create() skips full validation) and is
    falsy in the template -> placeholder branch. description_en is NOT NULL so a
    minimal value is supplied (template 3.2 renders only description_sr).
    full_clean() is DELIBERATELY NOT called.
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


def _add_images(prop, count=2):
    """Attach ``count`` PropertyImage rows with DISTINCT image URLs.

    DISTINCT URLs are essential: gallery.js dedups by URL, so a thumbnail with
    the same URL as the hero would be skipped from the lightbox set (story Dev
    Note: gallery hero-dup trap).
    """
    PropertyImage = _get_model("properties", "PropertyImage")
    rows = []
    for i in range(count):
        rows.append(
            PropertyImage.objects.create(
                property=prop,
                image=f"properties/gallery/photo-{i}.jpg",
                caption=f"Fotografija {i}",
                order=i,
            )
        )
    return rows


def _add_features(prop, names=("Klimatizacija", "Bazen", "Lift")):
    """Attach M2M PropertyFeature rows with the given name_sr values."""
    PropertyFeature = _get_model("properties", "PropertyFeature")
    feats = []
    for i, name in enumerate(names):
        f = PropertyFeature.objects.create(
            name_sr=name, name_en=f"Feature {i}", icon="icon", category="interior",
        )
        prop.features.add(f)
        feats.append(f)
    return feats


# Distinct SiteSettings sentinels so an agent-block render-assert proves the
# exact field reached the HTML.
PHONE = "+381119988776"
WHATSAPP = "381119988776"
EMAIL = "kontakt@velegradestate.test"
FOUNDER_NAME = "Đorđije Potpara"
FOUNDER_TITLE = "Privatni savetnik"


def _seed_site_settings(**overrides):
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.phone_primary = PHONE
    obj.whatsapp_number = WHATSAPP
    obj.email_primary = EMAIL
    obj.founder_name = FOUNDER_NAME
    obj.founder_title_sr = FOUNDER_TITLE
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _detail_path(slug):
    return f"/properties/{slug}/"


def _get_detail(client, prop, query=""):
    """GET /properties/<slug>/ (optional ?query) -> (resp, html)."""
    url = _detail_path(prop.slug)
    if query:
        url = url + "?" + query.lstrip("?")
    resp = client.get(url)
    return resp, resp.content.decode("utf-8")


def _valid_post_data(**overrides):
    data = dict(
        name="Marko Markovic",
        email="marko@example.com",
        phone="+381601234567",
        message="Zainteresovan sam za razgledanje.",
    )
    data.update(overrides)
    return data


def _inquiry_count():
    return _get_model("inquiries", "Inquiry").objects.count()


# =========================================================================== #
# AC1 — Detail 200 for visible property + can_preview gating + 404             #
# =========================================================================== #
@pytest.mark.django_db
def test_detail_returns_200_and_uses_template_extending_base(client):
    # AC1: GET /properties/<slug>/ for an is_active=True property -> 200, renders
    # property-detail.html which extends base.html (site-header + site-footer),
    # and loads css/pages/property-detail.css.
    _seed_site_settings()
    prop = _make_property(title="Vidljiva", is_active=True)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200, (
        f"GET {_detail_path(prop.slug)} for an active property must return 200, "
        f"got {resp.status_code} (AC1)."
    )
    template_names = [getattr(t, "name", None) for t in resp.templates]
    assert "property-detail.html" in template_names, (
        f"the detail page must render 'property-detail.html', got {template_names} (AC1)."
    )
    assert "site-header" in html and "site-footer" in html, (
        "property-detail.html must extend base.html (site-header + site-footer) (AC1)."
    )
    assert "css/pages/property-detail.css" in html, (
        "property-detail.html must load css/pages/property-detail.css via "
        "{% block extra_css %} (AC1)."
    )


@pytest.mark.django_db
def test_detail_nonexistent_slug_returns_404(client):
    # AC1: a slug that resolves to no Property -> 404 (get_object_or_404).
    resp = client.get(_detail_path("__nepostoji__"))
    assert resp.status_code == 404, (
        f"GET a nonexistent slug must return 404, got {resp.status_code} (AC1)."
    )


@pytest.mark.django_db
def test_detail_inactive_anonymous_returns_404(client):
    # AC1: is_active=False to an anonymous/non-staff user -> 404 (even ?preview=1).
    prop = _make_property(title="Neaktivna", is_active=False)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 404, (
        f"an inactive property must 404 for anonymous users, got {resp.status_code} (AC1)."
    )
    resp = client.get(_detail_path(prop.slug) + "?preview=1")
    assert resp.status_code == 404, (
        "an inactive property must 404 for anonymous users even with ?preview=1 "
        f"(preview is staff-only), got {resp.status_code} (AC1)."
    )


@pytest.mark.django_db
def test_detail_inactive_staff_preview_returns_200(client, django_user_model):
    # AC1: is_active=False + authenticated staff + ?preview=1 -> 200 (can_preview
    # True). Without ?preview=1 -> 404 (explicit opt-in).
    _seed_site_settings()
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    prop = _make_property(title="Neaktivna Preview", is_active=False)
    resp = client.get(_detail_path(prop.slug) + "?preview=1")
    assert resp.status_code == 200, (
        "an inactive property must render 200 for a logged-in staff user with "
        f"?preview=1, got {resp.status_code} (AC1)."
    )
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 404, (
        "an inactive property must 404 for staff WITHOUT ?preview=1 (explicit "
        f"opt-in), got {resp.status_code} (AC1)."
    )


@pytest.mark.django_db
def test_detail_any_collection_type_visible_when_active(client):
    # AC1: gating is by is_active/can_preview, NOT collection_type — a
    # private/off_market active property is reachable on its detail route.
    _seed_site_settings()
    prop = _make_property(title="Privatna Aktivna", collection_type="private",
                          is_active=True)
    resp, _ = _get_detail(client, prop)
    assert resp.status_code == 200, (
        "an active private-collection property must be reachable on its detail "
        f"route (gating is by is_active, not collection_type), got {resp.status_code} (AC1)."
    )


def test_property_detail_route_reverses_to_expected_path():
    # AC1: reverse("property-detail", slug=...) == "/properties/<slug>/".
    url = _try_reverse("property-detail", kwargs={"slug": "penthouse-dedinje"})
    assert url == "/properties/penthouse-dedinje/", (
        f"reverse('property-detail', slug='penthouse-dedinje') must equal "
        f"'/properties/penthouse-dedinje/', got {url!r} (AC1)."
    )


# =========================================================================== #
# AC2 — Hero gallery + thumbnail strip + lightbox + gallery.js                 #
# =========================================================================== #
@pytest.mark.django_db
def test_detail_hero_is_img_element(client):
    # AC2: the detail-hero section contains an <img> (gallery.js targets
    # '.detail-hero img' as lightbox index 0 — it MUST be an <img>, not svg/bg).
    _seed_site_settings()
    prop = _make_property()
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert 'class="detail-hero"' in html, "detail-hero section must render (AC2)."
    hero_idx = html.find('class="detail-hero"')
    # the next <img must appear shortly after the detail-hero open tag.
    assert "<img" in html[hero_idx:hero_idx + 600], (
        "the detail-hero must contain an <img> element (gallery.js targets "
        "'.detail-hero img' as lightbox index 0) (AC2)."
    )


@pytest.mark.django_db
def test_detail_renders_lightbox_with_gallery_js(client):
    # AC2: the lightbox markup with the exact gallery.js classes renders, and
    # js/gallery.js is loaded via {% block extra_js %}.
    _seed_site_settings()
    prop = _make_property()
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert 'class="lightbox"' in html, "the .lightbox container must render (AC2)."
    for cls in ("lightbox__close", "lightbox__prev", "lightbox__next",
                "lightbox__img", "lightbox__counter"):
        assert cls in html, (
            f"the lightbox must render the gallery.js selector '{cls}' (AC2)."
        )
    assert "js/gallery.js" in html, (
        "property-detail.html must load js/gallery.js via {% block extra_js %} (AC2)."
    )


@pytest.mark.django_db
def test_detail_thumbnail_strip_from_property_images(client):
    # AC2: 2 PropertyImage rows (DISTINCT URLs) -> 2 thumbnail-strip__item with
    # data-full attributes (gallery.js reads data-full || src).
    _seed_site_settings()
    prop = _make_property()
    _add_images(prop, count=2)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert html.count("thumbnail-strip__item") == 2, (
        f"2 PropertyImage rows must render 2 thumbnail-strip__item, got "
        f"{html.count('thumbnail-strip__item')} (AC2)."
    )
    assert "data-full" in html, (
        "each thumbnail must carry a data-full attribute (gallery.js reads "
        "data-full || src) (AC2)."
    )
    assert "photo-0.jpg" in html and "photo-1.jpg" in html, (
        "the DISTINCT thumbnail image URLs must appear in the strip (AC2)."
    )


@pytest.mark.django_db
def test_detail_no_images_is_graceful(client):
    # AC2: a property with NO PropertyImage rows still renders 200 (hero present,
    # strip empty/omitted, no error).
    _seed_site_settings()
    prop = _make_property(title="Bez slika")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200, (
        "a property with no gallery images must still render 200 (graceful) (AC2)."
    )
    assert 'class="detail-hero"' in html, (
        "the hero must still render even without PropertyImage rows (AC2)."
    )


# =========================================================================== #
# AC3 — Sticky info sidebar from Property fields                               #
# =========================================================================== #
@pytest.mark.django_db
def test_detail_sidebar_renders_property_fields(client):
    # AC3: the detail-sidebar renders title + known field values (area, bedrooms,
    # bathrooms, year_built).
    _seed_site_settings()
    # Distinctive values that will not collide with incidental page digits/CSS:
    # area_sqm 285 / area_total 347 / bedrooms 7 / bathrooms 6 / year 2024.
    prop = _make_property(title="Sidebar Test", area_sqm="285.00",
                          area_total_sqm="347.00", bedrooms=7, bathrooms=6,
                          year_built=2024)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "detail-sidebar" in html, "the detail-sidebar must render (AC3)."
    # Scope the field-value assertions to the sidebar region so a stray "7"/"6"
    # elsewhere (CSS, header, footer) can't masquerade as the rendered field.
    side_idx = html.find("detail-sidebar")
    sidebar = html[side_idx:]
    assert "Sidebar Test" in sidebar, "the sidebar must render the property title (AC3)."
    assert "285" in sidebar, "the sidebar must render area_sqm 285 (AC3)."
    assert "347" in sidebar, "the sidebar must render area_total_sqm 347 (AC3)."
    assert "7" in sidebar and "6" in sidebar, (
        "the sidebar must render bedrooms (7) and bathrooms (6) (AC3)."
    )
    assert "2024" in sidebar, "the sidebar must render year_built 2024 (AC3)."


@pytest.mark.django_db
def test_detail_price_on_request_renders_cena_na_upit(client):
    # AC3: price_on_request=True (price=None) renders "Cena na upit", NOT
    # "None"/"€0".
    _seed_site_settings()
    prop = _make_property(title="Na upit", status="price_on_request",
                          price_on_request=True, price=None)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "Cena na upit" in html, (
        "a price_on_request property must render 'Cena na upit' in the sidebar (AC3)."
    )
    assert "None" not in html, (
        "a price_on_request property must NOT render 'None' in the price slot (AC3)."
    )


@pytest.mark.django_db
def test_detail_concrete_price_formatted(client):
    # AC3: a concrete price renders the formatted number (the digits must appear).
    _seed_site_settings()
    prop = _make_property(title="Sa cenom", price="1250000.00",
                          price_on_request=False, status="for_sale")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert ("1250000" in html) or ("1.250.000" in html) or ("1,250,000" in html), (
        "a concrete price (1250000) must render formatted in the sidebar — the "
        "full number, not just a leading digit (AC3)."
    )


@pytest.mark.django_db
def test_detail_year_built_none_omits_row(client):
    # AC3: year_built=None -> the "Godina gradnje" row is omitted (no "None").
    _seed_site_settings()
    prop = _make_property(title="Bez godine", year_built=None)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "None" not in html, (
        "year_built=None must NOT render 'None' — the row must be omitted "
        "{% if property.year_built %} (AC3)."
    )


# =========================================================================== #
# AC4 — Storytelling description (|safe) + features 2-col                       #
# =========================================================================== #
@pytest.mark.django_db
def test_detail_description_rendered_safe(client):
    # AC4: description_sr HTMLField is rendered via |safe (admin-curated) — the
    # <p> tag is NOT escaped and the inner text appears in detail-description.
    _seed_site_settings()
    prop = _make_property(
        title="Opis Test",
        description_sr="<p>Storytelling tekst opisa</p>",
    )
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "Storytelling tekst opisa" in html, (
        "the description_sr text must render inside detail-description (AC4)."
    )
    assert "<p>Storytelling tekst opisa</p>" in html, (
        "description_sr must render via |safe (the <p> must NOT be escaped) (AC4)."
    )
    assert "&lt;p&gt;Storytelling" not in html, (
        "description_sr must NOT be auto-escaped — it is the only |safe field (AC4)."
    )


@pytest.mark.django_db
def test_detail_features_render_in_amenity_grid(client):
    # AC4: 3 PropertyFeature (M2M) render in amenity-grid with their name_sr.
    _seed_site_settings()
    prop = _make_property()
    _add_features(prop, names=("Klimatizacija", "Bazen", "Lift"))
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "amenity-grid" in html, "the amenity-grid must render (AC4)."
    for name in ("Klimatizacija", "Bazen", "Lift"):
        assert name in html, (
            f"the feature name_sr '{name}' must render in the amenity-grid (AC4)."
        )


@pytest.mark.django_db
def test_detail_no_features_is_graceful(client):
    # AC4: a property with no features still renders 200 (section omitted).
    _seed_site_settings()
    prop = _make_property(title="Bez karakteristika")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200, (
        "a property with no features must still render 200 (graceful) (AC4)."
    )


# =========================================================================== #
# AC5 — Floor plan + Leaflet map graceful (HTML container only — no JS)         #
# =========================================================================== #
@pytest.mark.django_db
def test_detail_map_container_when_coords_and_show_address(client):
    # AC5: latitude+longitude present AND show_address=True -> the map container
    # #property-map renders with data-lat/data-lng attributes.
    _seed_site_settings()
    prop = _make_property(latitude="44.780000", longitude="20.440000",
                          show_address=True)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert 'id="property-map"' in html, (
        "with coords + show_address=True the #property-map container must render (AC5)."
    )
    assert "data-lat=" in html and "data-lng=" in html, (
        "the map container must carry data-lat/data-lng attributes (AC5)."
    )
    assert "44.78" in html and "20.44" in html, (
        "the map container must carry the seeded coordinates in data-* (AC5)."
    )


@pytest.mark.django_db
def test_detail_no_map_when_show_address_false(client):
    # AC5 (privacy): show_address=False (even with coords) -> NO map container with
    # coordinates, "dostupna na upit" text shown, 200.
    _seed_site_settings()
    prop = _make_property(latitude="44.780000", longitude="20.440000",
                          show_address=False,
                          location_address="Tajna ulica 5")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert 'id="property-map"' not in html, (
        "show_address=False must NOT render the #property-map container (privacy) (AC5)."
    )
    assert "dostupna na upit" in html, (
        "without a map the discreet 'dostupna na upit' text must show (AC5)."
    )
    assert "Tajna ulica 5" not in html, (
        "show_address=False must NOT leak the exact location_address (privacy) (AC5)."
    )


@pytest.mark.django_db
def test_detail_no_map_when_coords_missing(client):
    # AC5: latitude/longitude None -> no map container, 200 (graceful).
    _seed_site_settings()
    prop = _make_property(latitude=None, longitude=None, show_address=True)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert 'id="property-map"' not in html, (
        "missing coordinates must NOT render the #property-map container (AC5)."
    )


@pytest.mark.django_db
def test_detail_floor_plan_download_link_when_present(client):
    # AC5: floor_plan present -> a "Preuzmi" download link to its URL renders.
    _seed_site_settings()
    prop = _make_property(floor_plan="properties/floorplans/plan.pdf")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "Preuzmi" in html, (
        "a property with a floor_plan must render a 'Preuzmi' download link (AC5)."
    )
    assert "plan.pdf" in html, (
        "the floor plan link must point to the floor_plan file URL (AC5)."
    )


@pytest.mark.django_db
def test_detail_floor_plan_omitted_when_absent(client):
    # AC5: no floor_plan -> the floor-plan section is omitted (graceful, 200).
    _seed_site_settings()
    prop = _make_property(title="Bez osnove", floor_plan="")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200, (
        "a property without a floor_plan must still render 200 (graceful) (AC5)."
    )


# =========================================================================== #
# AC6 — Agent Contact Block + mini Inquiry(viewing) form: GET markup            #
# =========================================================================== #
@pytest.mark.django_db
def test_detail_agent_block_and_form_markup(client):
    # AC6: GET renders agent-block, a <form method="post">, the CSRF token, the 4
    # field names, the one-click tel:/wa.me/mailto: from site_settings, and
    # EXACTLY ONE submit button ("Zakažite privatnu prezentaciju").
    _seed_site_settings()
    prop = _make_property()
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "agent-block" in html, "the agent-block must render (AC6)."
    assert '<form method="post"' in html or "method='post'" in html.lower(), (
        "the inquiry form must be a <form method=\"post\"> (AC6)."
    )
    assert "csrfmiddlewaretoken" in html, (
        "the inquiry form must include {% csrf_token %} (AC6)."
    )
    for name in ("name", "email", "phone", "message"):
        assert f'name="{name}"' in html, (
            f"the inquiry form must expose a control name=\"{name}\" (AC6)."
        )
    assert f"tel:{PHONE}" in html, "agent-block must render tel: from site_settings (AC6)."
    assert f"wa.me/{WHATSAPP}" in html, "agent-block must render wa.me from site_settings (AC6)."
    assert f"mailto:{EMAIL}" in html, "agent-block must render mailto: from site_settings (AC6)."
    assert html.count('type="submit"') == 1, (
        f"the inquiry form must have EXACTLY ONE submit button, got "
        f"{html.count('type=\"submit\"')} (AC6 — the 'Zakažite konsultaciju' button "
        f"is removed, deferred to Epik 4.2)."
    )
    assert "Zakažite privatnu prezentaciju" in html, (
        "the single submit button must read 'Zakažite privatnu prezentaciju' (AC6)."
    )
    assert "konsultacij" not in html.lower(), (
        "the 'Zakažite konsultaciju' button must NOT appear (removed in 3.2) (AC6)."
    )


@pytest.mark.django_db
def test_detail_form_no_data_validate_and_no_forms_js(client):
    # AC6 (forms.js HIJACK guard, LOCKED): the rendered detail HTML must NOT carry
    # data-validate on the inquiry form AND must NOT load js/forms.js — otherwise
    # forms.js fakes a client "success" with e.preventDefault() and the real
    # Inquiry POST never reaches the server (a silent prod bug on the first DB
    # write that the JS-less test client would never catch).
    _seed_site_settings()
    prop = _make_property()
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "data-validate" not in html, (
        "the inquiry form must NOT carry data-validate (forms.js would hijack the "
        "submit and fake success without a real POST) (AC6 HIJACK guard)."
    )
    assert "js/forms.js" not in html, (
        "the detail page must NOT load js/forms.js (only gallery.js + Leaflet) "
        "(AC6 HIJACK guard)."
    )


# =========================================================================== #
# AC6 — Inquiry POST: the FIRST DB write (valid / invalid / tamper / honeypot)  #
# =========================================================================== #
@pytest.mark.django_db
def test_inquiry_form_importable_fields_exactly_four(client):
    # AC6 (InquiryForm unit): the form is importable; Meta.fields == [name, email,
    # phone, message]; a non-model honeypot 'website' field exists; the
    # server-side fields are NOT form fields.
    forms_mod = importlib.import_module("inquiries.forms")
    InquiryForm = getattr(forms_mod, "InquiryForm")
    form = InquiryForm()
    model_field_names = set(form.Meta.fields)
    assert model_field_names == {"name", "email", "phone", "message"}, (
        f"InquiryForm.Meta.fields must be exactly [name, email, phone, message]; "
        f"got {model_field_names} (AC6)."
    )
    assert "website" in form.fields, (
        "InquiryForm must declare a non-model honeypot field 'website' (AC6)."
    )
    for forbidden in ("inquiry_type", "property", "status", "preferred_language"):
        assert forbidden not in form.fields, (
            f"InquiryForm must NOT expose '{forbidden}' as a field (server-side "
            f"only — tampering prevention) (AC6)."
        )


@pytest.mark.django_db
def test_inquiry_post_valid_creates_one_row_and_redirects(client):
    # AC6: a valid POST creates EXACTLY ONE Inquiry with all server-set fields,
    # then PRG-redirects (302) to ?sent=1; following the redirect -> 200 success.
    _seed_site_settings()
    prop = _make_property()
    Inquiry = _get_model("inquiries", "Inquiry")
    assert _inquiry_count() == 0
    resp = client.post(_detail_path(prop.slug), data=_valid_post_data())
    assert resp.status_code == 302, (
        f"a valid Inquiry POST must PRG-redirect (302), got {resp.status_code} (AC6)."
    )
    assert "sent=1" in resp.url, (
        f"the PRG redirect must carry the success marker ?sent=1, got {resp.url!r} (AC6)."
    )
    assert _inquiry_count() == 1, (
        f"a valid POST must create exactly ONE Inquiry, got {_inquiry_count()} (AC6)."
    )
    inq = Inquiry.objects.get()
    assert inq.inquiry_type == "viewing", "server must set inquiry_type='viewing' (AC6)."
    assert inq.property_id == prop.id, "server must set property=this page's property (AC6)."
    assert inq.status == "new", "server must set status='new' (AC6)."
    assert inq.preferred_language == "sr", (
        "server must set preferred_language='sr' (required, no DB default — "
        "omitting it would IntegrityError) (AC6)."
    )
    assert inq.name == "Marko Markovic"
    assert inq.email == "marko@example.com"
    assert inq.phone == "+381601234567"
    assert inq.message == "Zainteresovan sam za razgledanje."
    # follow the redirect -> 200 success marker
    follow = client.get(resp.url)
    assert follow.status_code == 200
    assert "form-success" in follow.content.decode("utf-8"), (
        "the GET after ?sent=1 must render the form-success message (PRG) (AC6)."
    )


@pytest.mark.django_db
def test_inquiry_post_tampering_server_fields_win(client):
    # AC6 (tampering): a POST that ALSO sends inquiry_type/property/status/
    # preferred_language must be ignored — the created Inquiry keeps the
    # server-set values (the form does not expose those fields).
    _seed_site_settings()
    prop = _make_property()
    other = _make_property(title="Druga nekretnina")
    Inquiry = _get_model("inquiries", "Inquiry")
    data = _valid_post_data(
        inquiry_type="private_collection",
        property=str(other.id),
        status="closed",
        preferred_language="en",
    )
    resp = client.post(_detail_path(prop.slug), data=data)
    assert resp.status_code == 302, "a (tampered) valid POST still PRG-redirects (AC6)."
    assert _inquiry_count() == 1, "exactly one Inquiry created on a tampered POST (AC6)."
    inq = Inquiry.objects.get()
    assert inq.inquiry_type == "viewing", (
        "client-supplied inquiry_type must be IGNORED (server sets 'viewing') (AC6)."
    )
    assert inq.property_id == prop.id, (
        "client-supplied property must be IGNORED (server sets this page's property) (AC6)."
    )
    assert inq.status == "new", (
        "client-supplied status must be IGNORED (server sets 'new') (AC6)."
    )
    assert inq.preferred_language == "sr", (
        "client-supplied preferred_language must be IGNORED (server sets 'sr') (AC6)."
    )


@pytest.mark.django_db
def test_inquiry_post_invalid_email_no_row(client):
    # AC6: an invalid email re-renders (200) with form errors and creates NO row.
    _seed_site_settings()
    prop = _make_property()
    resp = client.post(_detail_path(prop.slug),
                       data=_valid_post_data(email="not-an-email"))
    assert resp.status_code == 200, (
        f"an invalid POST must re-render (200), got {resp.status_code} (AC6)."
    )
    assert _inquiry_count() == 0, (
        f"an invalid email must create NO Inquiry, got {_inquiry_count()} (AC6)."
    )


@pytest.mark.django_db
def test_inquiry_post_blank_email_no_row(client):
    # AC6: a blank required field (email) re-renders 200, no row.
    _seed_site_settings()
    prop = _make_property()
    resp = client.post(_detail_path(prop.slug),
                       data=_valid_post_data(email=""))
    assert resp.status_code == 200, (
        f"a blank email must re-render (200), got {resp.status_code} (AC6)."
    )
    assert _inquiry_count() == 0, (
        "a blank required email must create NO Inquiry (AC6)."
    )


@pytest.mark.django_db
def test_inquiry_post_blank_message_no_row(client):
    # AC6: message is REQUIRED (server wins over the design's optional textarea) —
    # a blank message re-renders 200 and creates NO row.
    _seed_site_settings()
    prop = _make_property()
    resp = client.post(_detail_path(prop.slug),
                       data=_valid_post_data(message=""))
    assert resp.status_code == 200, (
        f"a blank message must re-render (200), got {resp.status_code} (AC6)."
    )
    assert _inquiry_count() == 0, (
        "a blank message must create NO Inquiry (message is required — server "
        "wins over the design's non-required textarea) (AC6)."
    )


@pytest.mark.django_db
def test_inquiry_post_honeypot_filled_silently_rejected(client):
    # AC6 (honeypot, LOCKED): a POST with the honeypot 'website' field filled (a
    # bot) returns the SAME success branch (302 -> ?sent=1) so the bot sees
    # "success" — but NO Inquiry is created.
    _seed_site_settings()
    prop = _make_property()
    resp = client.post(_detail_path(prop.slug),
                       data=_valid_post_data(website="http://spam.example"))
    assert resp.status_code == 302, (
        "a honeypot-filled POST must return the SAME success branch (302) as a "
        f"real submit (so the bot sees 'success'), got {resp.status_code} (AC6)."
    )
    assert _inquiry_count() == 0, (
        f"a honeypot-filled POST must create NO Inquiry (silently rejected), got "
        f"{_inquiry_count()} (AC6)."
    )


@pytest.mark.django_db
def test_inquiry_post_csrf_enforced_403_no_row(client, django_user_model):
    # AC6 (CSRF): an enforce_csrf_checks client POSTing WITHOUT a token -> 403,
    # and NO Inquiry created.
    _seed_site_settings()
    prop = _make_property()
    csrf_client = Client(enforce_csrf_checks=True)
    resp = csrf_client.post(_detail_path(prop.slug), data=_valid_post_data())
    assert resp.status_code == 403, (
        f"a POST without a CSRF token must return 403, got {resp.status_code} (AC6)."
    )
    assert _inquiry_count() == 0, (
        "a CSRF-rejected POST must create NO Inquiry (AC6)."
    )


@pytest.mark.django_db
def test_inquiry_post_sends_two_emails(client):
    # 5.2 (AC1/AC6 cross-cutting): a valid viewing submit now SENDS 2 emails
    # (agent notification + buyer auto-reply) via the create_inquiry hook. With
    # email_inquiries seeded the agent recipient is deterministic, so the outbox
    # grows by exactly 2. (Inverted in GREEN from the 3.2 no-email assertion.)
    from django.core import mail
    _seed_site_settings(email_inquiries="agent@velegradestate.test")
    prop = _make_property()
    before = len(mail.outbox)
    client.post(_detail_path(prop.slug), data=_valid_post_data())
    assert len(mail.outbox) == before + 2, (
        "5.2 must send 2 emails (agent + auto-reply) on a valid Inquiry submit "
        "via the create_inquiry hook (AC1/AC6)."
    )


# =========================================================================== #
# AC7 — auto-escape (XSS) + regression guards                                  #
# =========================================================================== #
@pytest.mark.django_db
def test_detail_title_xss_is_escaped(client):
    # AC7: a Property title containing a <script> payload must be HTML-escaped in
    # the detail page (no |safe on CharField fields — only description_sr is safe).
    _seed_site_settings()
    prop = _make_property(title="<script>alert(1)</script>")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "<script>alert(1)</script>" not in html, (
        "a raw <script> from the title must NOT appear unescaped (XSS) (AC7)."
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html, (
        "the title must be HTML-escaped (&lt;script&gt;...) — auto-escape, no "
        "|safe on CharField fields (AC7)."
    )


def test_manage_py_check_passes():
    # AC7: `manage.py check` runs clean after the view/form/template/url changes.
    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc} (AC7)")


@pytest.mark.django_db
def test_home_still_returns_200(client):
    # AC7 (2.2 regression): GET / still returns 200.
    _seed_site_settings()
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / (Home) must still return 200, got {resp.status_code} (AC7 regression)."
    )


@pytest.mark.django_db
def test_listing_still_returns_200(client):
    # AC7 (3.1 regression): GET /properties/ listing still 200 (its hardcoded
    # /properties/<slug>/ card links now point at the live detail route).
    _seed_site_settings()
    _make_property(title="Listing Regresija", status="for_sale")
    resp = client.get("/properties/")
    assert resp.status_code == 200, (
        f"GET /properties/ (listing) must still return 200, got {resp.status_code} "
        f"(AC7 regression)."
    )


@pytest.mark.django_db
def test_admin_index_still_200_for_superuser(client, django_user_model):
    # AC7 (1.3 regression): the branded admin index still returns 200.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index at {_admin_index_path()} must still return 200 (AC7 regression)."
    )


@pytest.mark.django_db
def test_default_admin_path_still_404(client):
    # AC7 (1.3 regression): GET /admin/ stays 404 (admin mounts on ADMIN_URL).
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must still return 404, got {resp.status_code} (AC7 regression)."
    )


# =========================================================================== #
# Code-review batch (non-mandatory) additions                                  #
# =========================================================================== #
@pytest.mark.django_db
def test_inquiry_post_blank_name_no_row(client):
    # AC6 (blank required name): a blank `name` re-renders 200 and creates NO row
    # (name is a required model CharField -> ModelForm required).
    _seed_site_settings()
    prop = _make_property()
    resp = client.post(_detail_path(prop.slug),
                       data=_valid_post_data(name=""))
    assert resp.status_code == 200, (
        f"a blank name must re-render (200), got {resp.status_code} (AC6)."
    )
    assert _inquiry_count() == 0, (
        "a blank required name must create NO Inquiry (AC6)."
    )


@pytest.mark.django_db
def test_features_distinct_icons_render_distinguishably(client):
    # AC4 / icon spec: two features with DIFFERENT icon values must render
    # distinguishably (PropertyFeature.icon is no longer ignored — it reaches the
    # HTML as a class / data-icon, auto-escaped, no |safe).
    _seed_site_settings()
    prop = _make_property()
    PropertyFeature = _get_model("properties", "PropertyFeature")
    f1 = PropertyFeature.objects.create(
        name_sr="Klimatizacija", name_en="AC", icon="snowflake",
        category="interior",
    )
    f2 = PropertyFeature.objects.create(
        name_sr="Bazen", name_en="Pool", icon="pool", category="exterior",
    )
    prop.features.add(f1, f2)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    # The two distinct icon slugs must both appear in the rendered HTML so the
    # features are visually distinguishable (not a single static placeholder).
    assert "snowflake" in html, (
        "feature icon 'snowflake' must reach the HTML (PropertyFeature.icon must "
        "not be ignored)."
    )
    assert "pool" in html, (
        "feature icon 'pool' must reach the HTML (different features must render "
        "distinguishably)."
    )


@pytest.mark.django_db
def test_features_icon_is_auto_escaped(client):
    # icon is a CharField rendered as a class/attribute — it must be auto-escaped
    # (no |safe), so a malicious icon value cannot break out of the attribute.
    _seed_site_settings()
    prop = _make_property()
    PropertyFeature = _get_model("properties", "PropertyFeature")
    f = PropertyFeature.objects.create(
        name_sr="XSS", name_en="XSS", icon='"><script>alert(1)</script>',
        category="interior",
    )
    prop.features.add(f)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "<script>alert(1)</script>" not in html, (
        "a malicious icon value must be auto-escaped (no |safe on f.icon)."
    )


@pytest.mark.django_db
def test_detail_map_uses_leaflet_with_sri_integrity(client):
    # TEA: when show_map is True the rendered HTML's Leaflet tags must carry an
    # integrity= (Subresource Integrity) attribute (the interim hardening for the
    # external CDN dependency until full vendoring).
    _seed_site_settings()
    prop = _make_property(latitude="44.780000", longitude="20.440000",
                          show_address=True)
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert "leaflet" in html.lower(), "the Leaflet asset must be referenced (SRI)."
    assert "integrity=" in html, (
        "the Leaflet CDN tags must carry an integrity= (SRI) attribute (TEA)."
    )


def test_gallery_js_has_touch_swipe_handlers():
    # TEA / FR10: the gallery.js file must contain touchstart + touchend handlers
    # (documents the FR10 swipe addition). Read the static file directly.
    from pathlib import Path

    from django.conf import settings

    gallery_path = Path(settings.BASE_DIR) / "static" / "js" / "gallery.js"
    assert gallery_path.exists(), f"gallery.js must exist at {gallery_path}."
    source = gallery_path.read_text(encoding="utf-8")
    assert "touchstart" in source, (
        "gallery.js must add a 'touchstart' handler (FR10 swipe) (TEA)."
    )
    assert "touchend" in source, (
        "gallery.js must add a 'touchend' handler (FR10 swipe) (TEA)."
    )


@pytest.mark.django_db
def test_detail_price_has_euro_prefix_in_sidebar(client):
    # AC3 (TEA tighten): the formatted price must appear WITH the € prefix in the
    # sidebar region — not just bare digits anywhere in the HTML.
    _seed_site_settings()
    prop = _make_property(title="Sa cenom EUR", price="1250000.00",
                          price_on_request=False, status="for_sale")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    side_idx = html.find("detail-sidebar")
    assert side_idx != -1, "the detail-sidebar must render (AC3)."
    sidebar = html[side_idx:]
    assert "€1250000" in sidebar, (
        "the formatted price must render with the € prefix in the sidebar "
        "(€1250000), not just bare digits anywhere in the page (AC3 / TEA)."
    )


# =========================================================================== #
# SECURITY review fixes (story 3.2 code-review batch — S1/S2/S3)               #
# =========================================================================== #
@pytest.mark.django_db
def test_honeypot_input_has_protective_attrs(client):
    # S1 (AC6 / interface contract §2): the honeypot `website` input itself must
    # carry tabindex="-1" and autocomplete="off" (bots that fill every visible
    # field trip it; humans never reach it via Tab / autofill). The .sr-only +
    # aria-hidden wrapper alone is not enough — the locked spec requires the
    # attributes on the input.
    _seed_site_settings()
    prop = _make_property()
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    # Locate the rendered honeypot input (name="website").
    assert 'name="website"' in html, (
        "the honeypot 'website' input must render (S1)."
    )
    w_idx = html.find('name="website"')
    # The protective attrs live on the same <input ...> tag — scan a small window
    # around the name attribute.
    tag_start = html.rfind("<input", 0, w_idx)
    tag_end = html.find(">", w_idx)
    tag = html[tag_start:tag_end + 1]
    assert 'tabindex="-1"' in tag, (
        "the honeypot input must carry tabindex=\"-1\" (S1 — locked spec)."
    )
    assert 'autocomplete="off"' in tag, (
        "the honeypot input must carry autocomplete=\"off\" (S1 — locked spec)."
    )


@pytest.mark.django_db
def test_virtual_tour_javascript_scheme_suppressed(client):
    # S2 (XSS): an admin-entered javascript: scheme in virtual_tour_url must NOT
    # become a clickable href (Django auto-escape does not neutralize a
    # javascript:/data: scheme inside an href). The view sanitizes it to "" so
    # the link is suppressed entirely.
    _seed_site_settings()
    prop = _make_property(virtual_tour_url="javascript:alert(1)")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert 'href="javascript:' not in html, (
        "a javascript: virtual_tour_url must NOT render as a clickable href "
        "(XSS suppressed by the view) (S2)."
    )
    assert "alert(1)" not in html, (
        "the javascript: payload must not appear in the page at all (S2)."
    )


@pytest.mark.django_db
def test_virtual_tour_https_scheme_renders(client):
    # S2: a legitimate https virtual_tour_url still renders as a link (the
    # sanitization only suppresses unsafe schemes, not safe ones).
    _seed_site_settings()
    prop = _make_property(virtual_tour_url="https://tour.example/12345")
    resp, html = _get_detail(client, prop)
    assert resp.status_code == 200
    assert 'href="https://tour.example/12345"' in html, (
        "a valid https virtual_tour_url must render as a clickable link (S2)."
    )
