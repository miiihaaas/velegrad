"""
RED-phase contract tests for Story 3.1 — "Signature listing sa server-side filterima".

These tests define the CONTRACT for the public Signature listing at /properties/:
the PropertyListView (signature + active + non-sold/rented base queryset, filters
applied, then a [:12] slice), the PropertyFilterForm (Django forms, no
django-filter, every field required=False), templates/properties.html (filter-bar
<form method="get"> + listing-grid + listing-empty), and the /properties/ route
(name="properties"). They are written BEFORE the feature is built, so EVERY 3.1
test in this module MUST FAIL/ERROR until the Dev implements:

  * properties/forms.py::PropertyFilterForm with fields location / property_type /
    status / price_min / price_max / bedrooms / keyword (all required=False), a
    clean() that neutralises an inverted price range, min_value=0 guards;
  * properties/views.py::PropertyListView whose queryset is
    Property.objects.filter(collection_type="signature", is_active=True,
        status__in=["for_sale","for_rent","price_on_request"]) -> filters from
    form.cleaned_data -> [:12] (slice AFTER filters, NOT paginate_by);
  * config/urls.py route path("properties/", ..., name="properties");
  * templates/properties.html ({% extends base %} + filter-bar <form method=get> +
    listing-grid property-card cards + listing-empty + extra_css properties.css +
    extra_js filters.js).

Design / locked rules (mirrors the 2.2 + 1.3 harness):
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * Card count is asserted via html.count('class="property-card"').
  * Property is seeded via .objects.create(hero_image="") — full_clean() is NEVER
    called (hero_image has no blank=True; create() skips validation on SQLite).
  * Base queryset EXCLUDES private / off_market / is_active=False / sold / rented.
  * bedrooms -> bedrooms__gte (minimum). keyword -> title__icontains ONLY.
    location -> __icontains. price_min/max gte/lte; price_min>price_max -> ignore
    both. The [:12] slice is applied AFTER filters (the critical latent-bug guard).
  * Invalid/garbage/negative/huge GET params -> HTTP 200, never 500 (form is the
    sole gate; no raw request.GET reaches the ORM).
  * Card CTA href is the HARDCODED absolute "/properties/<slug>/" (NOT {% url %} —
    the detail route is Story 3.2; NoReverseMatch would 500). The "GET /properties/
    == 200" guard catches any {% url %} slip.
  * No |safe on card fields (auto-escape).
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    3-1-signature-listing-sa-server-side-filterima-interface-contract.md
"""
import importlib

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.urls import NoReverseMatch, reverse


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


def _try_reverse(name):
    """reverse(name) or None if the route does not exist yet (RED phase)."""
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


def _make_property(**overrides):
    """Create a Property with all required non-null scalar fields supplied.

    hero_image="" passes on SQLite (.create() skips full validation) and is falsy
    in the template -> placeholder branch. Mirrors the _make_property helpers in
    tests/test_home_page.py / test_admin_dashboard.py plus the description_*
    HTMLFields. full_clean() is DELIBERATELY NOT called (would fail on the blank
    hero_image, which has no blank=True).
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


def _get_listing(client, query=""):
    """GET /properties/ (with an optional ?query string) -> (resp, html)."""
    url = "/properties/"
    if query:
        url = url + "?" + query.lstrip("?")
    resp = client.get(url)
    return resp, resp.content.decode("utf-8")


def _card_count(html):
    return html.count('class="property-card"')


# =========================================================================== #
# AC1 — Signature listing /properties/ with editorial cards                    #
# =========================================================================== #
@pytest.mark.django_db
def test_listing_returns_200(client):
    # AC1: GET /properties/ must return 200. This is ALSO the guard that no
    # {% url %} on a missing route (e.g. property-detail) slipped in (-> 500).
    _make_property(title="Vidljiva")
    resp, _ = _get_listing(client)
    assert resp.status_code == 200, (
        f"GET /properties/ must return 200 (route registered, template renders, "
        f"no {{% url %}} on a missing route), got {resp.status_code} (AC1)."
    )


@pytest.mark.django_db
def test_listing_uses_properties_template_extending_base(client):
    # AC1/AC6: the listing renders templates/properties.html, which extends
    # base.html (site-header + site-footer present).
    _make_property(title="Vidljiva")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    template_names = [getattr(t, "name", None) for t in resp.templates]
    assert "properties.html" in template_names, (
        f"the listing must render 'properties.html', got templates {template_names} (AC1)."
    )
    assert "site-header" in html and "site-footer" in html, (
        "properties.html must extend base.html (site-header + site-footer present) (AC1/AC6)."
    )


@pytest.mark.django_db
def test_listing_shows_only_signature_active_non_sold_rented(client):
    # AC1: only collection_type=signature AND is_active=True AND status in
    # (for_sale/for_rent/price_on_request) render as property-card. 3 visible;
    # inactive / private / off_market / sold / rented are excluded.
    _make_property(title="Sig For Sale", status="for_sale")
    _make_property(title="Sig For Rent", status="for_rent")
    _make_property(title="Sig On Request", status="price_on_request",
                   price_on_request=True, price=None)
    _make_property(title="Sig Inactive", is_active=False)
    _make_property(title="Private Active", collection_type="private")
    _make_property(title="OffMarket Active", collection_type="off_market")
    _make_property(title="Sig Sold", status="sold")
    _make_property(title="Sig Rented", status="rented")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    assert _card_count(html) == 3, (
        f"exactly 3 signature+active+non-sold/rented cards must render; "
        f"got {_card_count(html)} (AC1)."
    )
    assert "Sig For Sale" in html and "Sig For Rent" in html and "Sig On Request" in html, (
        "the 3 visible signature titles must appear in the listing (AC1)."
    )


@pytest.mark.django_db
def test_listing_excludes_hidden_titles_explicitly(client):
    # AC1: the inactive / private / off_market / SOLD / rented titles must NOT
    # appear in the HTML (hard queryset boundary). 'sold' asserted explicitly.
    _make_property(title="Vidljiva Signature", status="for_sale")
    _make_property(title="Skrivena Neaktivna", is_active=False)
    _make_property(title="Skrivena Privatna", collection_type="private")
    _make_property(title="Skrivena OffMarket", collection_type="off_market")
    _make_property(title="Skrivena Prodata", status="sold")
    _make_property(title="Skrivena Izdata", status="rented")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    assert "Vidljiva Signature" in html
    for hidden in ("Skrivena Neaktivna", "Skrivena Privatna",
                   "Skrivena OffMarket", "Skrivena Prodata", "Skrivena Izdata"):
        assert hidden not in html, (
            f"{hidden!r} must NOT appear on the curated listing (AC1 boundary). "
            f"'sold'/'rented' are excluded from the curated listing."
        )


@pytest.mark.django_db
def test_listing_capped_at_twelve(client):
    # AC1: with 13 visible signature+active properties, EXACTLY 12 cards render
    # ([:12] slice). Tightened to == 12 (13 seeded, all visible → 12 shown).
    for i in range(13):
        _make_property(title=f"Sig {i}", status="for_sale")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    assert _card_count(html) == 12, (
        f"the listing must render exactly 12 cards ([:12] slice on 13 visible); "
        f"got {_card_count(html)} (AC1)."
    )


# =========================================================================== #
# AC2 — Server-side filters via GET + the critical slice-after-filter guard    #
# =========================================================================== #
@pytest.mark.django_db
def test_slice_applied_after_filter_not_before(client):
    # AC2 (CRITICAL latent bug): seed 13 signature+active that ALL match one
    # filter (property_type=vila) FIRST, then 5 NON-matching (stan) LAST. Model
    # ordering is ["-created_at"] (newest first), so the 5 stan rows are the
    # NEWEST and occupy the front of the BASE queryset. GET ?property_type=vila
    # must render exactly 12 cards (13 vila filtered, then [:12]) AND none of the
    # stan rows — proving [:12] runs on the FILTERED queryset (filter BEFORE
    # slice). A buggy PRE-slice impl (base[:12] THEN filter) would take the 12
    # newest = 5 stan + 7 vila, then filter to vila -> only 7 cards, FAILING the
    # ==12 assertion below. That discriminator is what proves the ordering; seeding
    # the non-matching rows LAST (newest) is essential — if they were oldest, a
    # pre-slice impl would coincidentally still yield 12 vila and pass falsely.
    for i in range(13):
        _make_property(title=f"Vila {i}", property_type="vila", status="for_sale")
    for i in range(5):
        _make_property(title=f"Stan {i}", property_type="stan", status="for_sale")
    resp, html = _get_listing(client, "property_type=vila")
    assert resp.status_code == 200
    assert _card_count(html) <= 12, (
        f"?property_type=vila must render at most 12 cards (slice after filter); "
        f"got {_card_count(html)} (AC2)."
    )
    assert _card_count(html) == 12, (
        f"with 13 matching vile the filtered+sliced result must be EXACTLY 12 "
        f"(proves [:12] is applied to the FILTERED set, not a pre-sliced one — a "
        f"pre-slice impl would yield only 7 vila here because the 5 NEWEST rows are "
        f"stan and would steal slots before filtering); got {_card_count(html)} (AC2)."
    )
    for i in range(5):
        assert f"Stan {i}" not in html, (
            f"'Stan {i}' (property_type=stan) must NOT appear under "
            f"?property_type=vila — filtering must precede the [:12] slice (AC2)."
        )


@pytest.mark.django_db
def test_filter_property_type(client):
    # AC2: ?property_type=vila returns only vile.
    _make_property(title="Vila A", property_type="vila")
    _make_property(title="Stan B", property_type="stan")
    resp, html = _get_listing(client, "property_type=vila")
    assert resp.status_code == 200
    assert "Vila A" in html and "Stan B" not in html, (
        "?property_type=vila must show only the vila and exclude the stan (AC2)."
    )


@pytest.mark.django_db
def test_filter_status(client):
    # AC2: ?status=for_sale returns only for_sale properties.
    _make_property(title="Na prodaju X", status="for_sale")
    _make_property(title="Za izdavanje Y", status="for_rent")
    resp, html = _get_listing(client, "status=for_sale")
    assert resp.status_code == 200
    assert "Na prodaju X" in html and "Za izdavanje Y" not in html, (
        "?status=for_sale must show only the for_sale property (AC2)."
    )


@pytest.mark.django_db
def test_filter_location_icontains_case_insensitive(client):
    # AC2: ?location=dedinje (lowercase) matches location_district="Dedinje" via
    # case-insensitive __icontains.
    _make_property(title="Na Dedinju", location_district="Dedinje")
    _make_property(title="Na Vracaru", location_district="Vracar")
    resp, html = _get_listing(client, "location=dedinje")
    assert resp.status_code == 200
    assert "Na Dedinju" in html, (
        "?location=dedinje must match location_district='Dedinje' "
        "(case-insensitive __icontains) (AC2)."
    )
    assert "Na Vracaru" not in html, (
        "?location=dedinje must NOT match the Vracar property (AC2)."
    )


@pytest.mark.django_db
def test_filter_price_range_inclusive(client):
    # AC2: ?price_min=200000&price_max=400000 returns only properties whose price
    # is within [200000, 400000] inclusive.
    _make_property(title="Jeftina", price="150000.00")
    _make_property(title="Donja granica", price="200000.00")
    _make_property(title="Srednja", price="300000.00")
    _make_property(title="Gornja granica", price="400000.00")
    _make_property(title="Skupa", price="500000.00")
    resp, html = _get_listing(client, "price_min=200000&price_max=400000")
    assert resp.status_code == 200
    assert "Donja granica" in html and "Srednja" in html and "Gornja granica" in html, (
        "price range [200000,400000] must include the boundary + middle prices (AC2)."
    )
    assert "Jeftina" not in html and "Skupa" not in html, (
        "price range [200000,400000] must exclude prices outside the range (AC2)."
    )


@pytest.mark.django_db
def test_price_range_keeps_price_on_request_listings(client):
    # AC2 (BUG fix): a price-range filter must NARROW priced listings but KEEP
    # "Cena na upit" (price_on_request=True, price=None) listings visible — their
    # price is undisclosed, NOT out-of-range. SQL NULL fails price__gte/__lte, so
    # without the OR-in guard the slider (which always submits the full default
    # range) would silently drop every price-on-request premium listing.
    _make_property(title="Na upit premium", status="price_on_request",
                   price_on_request=True, price=None)
    _make_property(title="Cenovna nekretnina", status="for_sale",
                   price="300000.00")
    # Full default slider range (the exact scenario that triggered the defect:
    # user submits the form without touching the price slider).
    resp, html = _get_listing(client, "price_min=0&price_max=5000000")
    assert resp.status_code == 200
    assert "Na upit premium" in html, (
        "a price_on_request (price=None) listing must SURVIVE the full default "
        "price range — NULL price must not be excluded by price__gte/__lte (AC2)."
    )
    assert "Cenovna nekretnina" in html, (
        "an in-range priced listing must still show under the default range (AC2)."
    )
    # A NARROW range that excludes the priced listing must STILL keep the
    # price-on-request listing (it has no comparable price).
    resp, html = _get_listing(client, "price_min=400000&price_max=500000")
    assert resp.status_code == 200
    assert "Na upit premium" in html, (
        "a price_on_request listing must SURVIVE even a narrow price range that "
        "excludes priced listings — undisclosed price is not out-of-range (AC2)."
    )
    assert "Cenovna nekretnina" not in html, (
        "the priced (300000) listing must be excluded by the narrow [400000,500000] "
        "range — priced listings are still narrowed normally (AC2)."
    )


@pytest.mark.django_db
def test_filter_bedrooms_is_gte(client):
    # AC2: ?bedrooms=3 returns only properties with bedrooms >= 3 (NOT exact).
    # Seed bedrooms=2 (must be excluded), bedrooms=3 (boundary, included),
    # bedrooms=5 (included — proves "5+" chip semantics).
    _make_property(title="Dve sobe", bedrooms=2)
    _make_property(title="Tri sobe", bedrooms=3)
    _make_property(title="Pet soba", bedrooms=5)
    resp, html = _get_listing(client, "bedrooms=3")
    assert resp.status_code == 200
    assert "Tri sobe" in html and "Pet soba" in html, (
        "?bedrooms=3 must include bedrooms>=3 (boundary 3 and 5) — bedrooms__gte (AC2)."
    )
    assert "Dve sobe" not in html, (
        "?bedrooms=3 must EXCLUDE bedrooms=2 (gte, not <) (AC2)."
    )


@pytest.mark.django_db
def test_filter_keyword_title_only(client):
    # AC2: ?keyword matches title__icontains ONLY. A property whose TITLE contains
    # the keyword is shown; one whose title does not (even if description does) is
    # excluded.
    _make_property(title="Luksuzni Penthouse", description_sr="<p>obican opis</p>")
    _make_property(title="Obican Stan",
                   description_sr="<p>Luksuzni enterijer</p>")
    resp, html = _get_listing(client, "keyword=Luksuzni")
    assert resp.status_code == 200
    assert "Luksuzni Penthouse" in html, (
        "?keyword=Luksuzni must match the property whose TITLE contains it (AC2)."
    )
    assert "Obican Stan" not in html, (
        "?keyword=Luksuzni must NOT match a property whose only the DESCRIPTION "
        "contains it — keyword is title__icontains ONLY (AC2)."
    )


@pytest.mark.django_db
def test_filters_combine_as_and(client):
    # AC2: two params intersect (AND). Only the property matching BOTH survives.
    _make_property(title="Vila Dedinje", property_type="vila",
                   location_district="Dedinje")
    _make_property(title="Vila Vracar", property_type="vila",
                   location_district="Vracar")
    _make_property(title="Stan Dedinje", property_type="stan",
                   location_district="Dedinje")
    resp, html = _get_listing(client, "property_type=vila&location=dedinje")
    assert resp.status_code == 200
    assert "Vila Dedinje" in html, (
        "the property matching BOTH property_type=vila AND location=dedinje must show (AC2)."
    )
    assert "Vila Vracar" not in html and "Stan Dedinje" not in html, (
        "properties matching only one of the two params must be excluded (AND intersect) (AC2)."
    )


@pytest.mark.django_db
def test_no_params_shows_all_visible(client):
    # AC2: with no query params the full (up to 12) signature+active listing shows.
    _make_property(title="Prva", status="for_sale")
    _make_property(title="Druga", status="for_rent")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    assert _card_count(html) == 2, (
        f"with no filters all visible signature properties show; got {_card_count(html)} (AC2)."
    )


# =========================================================================== #
# AC3 — PropertyFilterForm validates; invalid input never 500s                 #
# =========================================================================== #
def test_property_filter_form_importable_and_all_fields_optional():
    # AC3: PropertyFilterForm is importable; an empty form is valid (all fields
    # required=False).
    forms_mod = importlib.import_module("properties.forms")
    PropertyFilterForm = getattr(forms_mod, "PropertyFilterForm")
    form = PropertyFilterForm(data={})
    assert form.is_valid(), (
        "an empty PropertyFilterForm must be valid — every field is required=False "
        f"(AC3). Errors: {form.errors!r}"
    )
    expected = {"location", "property_type", "price_min", "price_max",
                "bedrooms", "status", "keyword"}
    assert expected.issubset(set(form.fields.keys())), (
        f"PropertyFilterForm must declare fields {expected}; got {set(form.fields.keys())} (AC3)."
    )


def test_property_filter_form_garbage_is_invalid_but_does_not_raise():
    # AC3: garbage values make the offending field invalid (form not valid) but
    # the form itself never raises — it just collects errors.
    forms_mod = importlib.import_module("properties.forms")
    PropertyFilterForm = getattr(forms_mod, "PropertyFilterForm")
    form = PropertyFilterForm(data={"price_min": "abc", "bedrooms": "xyz",
                                    "status": "hack"})
    # is_valid() must run without raising; the garbage fields are invalid.
    assert form.is_valid() is False, (
        "garbage price_min/bedrooms/status must make the form invalid (AC3)."
    )


def test_property_filter_form_valid_params_populate_cleaned_data():
    # AC3: valid params populate cleaned_data with the coerced values.
    forms_mod = importlib.import_module("properties.forms")
    PropertyFilterForm = getattr(forms_mod, "PropertyFilterForm")
    form = PropertyFilterForm(data={"property_type": "vila", "bedrooms": "3",
                                    "keyword": "Luks"})
    assert form.is_valid(), f"valid params must validate (AC3). Errors: {form.errors!r}"
    assert form.cleaned_data["property_type"] == "vila"
    assert form.cleaned_data["bedrooms"] == 3
    assert form.cleaned_data["keyword"] == "Luks"


@pytest.mark.django_db
@pytest.mark.parametrize("query", [
    "price_min=abc",
    "bedrooms=xyz",
    "status=hack",
    "status=__nonexistent__",
    "bedrooms=-1",
    "price_min=-5",
    "price_min=99999999999999",
    "property_type=__bogus__",
])
def test_garbage_params_never_500(client, query):
    # AC3: every garbage / negative / huge / bogus-choice param yields HTTP 200,
    # never 500 — the form is the sole gate; the invalid field is ignored and the
    # listing still renders.
    _make_property(title="Postojeca", status="for_sale")
    resp, _ = _get_listing(client, query)
    assert resp.status_code != 500, (
        f"?{query} must NOT cause a 500 — invalid input is ignored by the form (AC3)."
    )
    assert resp.status_code == 200, (
        f"?{query} must render the listing (200), got {resp.status_code} (AC3)."
    )


@pytest.mark.django_db
def test_inverted_price_range_ignores_both_and_renders(client):
    # AC3: ?price_min=500000&price_max=100000 (inverted) -> clean() sets both to
    # None -> both price filters ignored -> listing NOT empty (200).
    _make_property(title="Srednja cena", price="300000.00")
    resp, html = _get_listing(client, "price_min=500000&price_max=100000")
    assert resp.status_code == 200, (
        "an inverted price range must render 200 (clean() neutralises it) (AC3)."
    )
    assert "Srednja cena" in html, (
        "with an inverted price range BOTH price filters are ignored, so the "
        "in-range property still shows (listing not empty) (AC3)."
    )


@pytest.mark.django_db
def test_valid_price_range_filters_correctly(client):
    # AC3: a valid (non-inverted) range filters as expected.
    _make_property(title="U opsegu", price="300000.00")
    _make_property(title="Van opsega", price="900000.00")
    resp, html = _get_listing(client, "price_min=100000&price_max=500000")
    assert resp.status_code == 200
    assert "U opsegu" in html and "Van opsega" not in html, (
        "a valid price range [100000,500000] must filter correctly (AC3)."
    )


# =========================================================================== #
# AC4 — GET form, names aligned, filters.js included, no XHR                    #
# =========================================================================== #
@pytest.mark.django_db
def test_filter_bar_is_get_form(client):
    # AC4: the filter-bar is wrapped in a <form ... method="get" ...>.
    _make_property(title="Postojeca")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    lowered = html.lower()
    assert "<form" in lowered and 'method="get"' in lowered, (
        "the filter-bar must be wrapped in a <form method=\"get\"> (AC4)."
    )
    assert "filter-bar" in html, "the filter-bar must render (AC4)."


@pytest.mark.django_db
def test_filter_controls_have_form_aligned_names(client):
    # AC4: filter controls carry the PropertyFilterForm name attributes (NOT the
    # design's legacy type / price-min / price-max).
    _make_property(title="Postojeca")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    for name in ("location", "property_type", "price_min", "price_max",
                 "bedrooms", "status", "keyword"):
        assert f'name="{name}"' in html, (
            f"the filter-bar must expose a control with name=\"{name}\" "
            f"(aligned with PropertyFilterForm) (AC4)."
        )
    assert 'name="type"' not in html, (
        "the legacy design name=\"type\" must be renamed to property_type (AC4)."
    )
    assert 'name="price-min"' not in html and 'name="price-max"' not in html, (
        "the legacy design price-min/price-max names must be renamed to "
        "price_min/price_max (AC4)."
    )


@pytest.mark.django_db
def test_listing_includes_filters_js_and_no_xhr(client):
    # AC4: properties.html loads js/filters.js via {% block extra_js %} and the
    # render contains no fetch( / XMLHttpRequest / /api/ (pure GET reload).
    _make_property(title="Postojeca")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    assert "js/filters.js" in html, (
        "properties.html must load js/filters.js via {% block extra_js %} (AC4)."
    )
    assert "fetch(" not in html and "XMLHttpRequest" not in html and "/api/" not in html, (
        "the listing must use a pure GET reload — no fetch( / XMLHttpRequest / "
        "/api/ for filtering (AC4)."
    )


@pytest.mark.django_db
def test_filter_values_retained_after_reload(client):
    # AC4: after ?keyword=Testic the keyword input retains its value (form bound
    # to request.GET).
    _make_property(title="Testic Nekretnina")
    resp, html = _get_listing(client, "keyword=Testic")
    assert resp.status_code == 200
    assert 'value="Testic"' in html, (
        "the keyword control must retain its submitted value after reload "
        "(form bound to request.GET) (AC4)."
    )


# =========================================================================== #
# AC5 — price_on_request -> "Cena na upit"; concrete price formatted            #
# =========================================================================== #
@pytest.mark.django_db
def test_price_on_request_renders_cena_na_upit(client):
    # AC5: a property with price_on_request=True renders "Cena na upit" (and no
    # numeric/None/€0), while a property with a concrete price renders that price.
    _make_property(title="Na upit nekretnina", status="price_on_request",
                   price_on_request=True, price=None)
    _make_property(title="Sa cenom nekretnina", status="for_sale",
                   price="485000.00")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    assert "Cena na upit" in html, (
        "a price_on_request property must render 'Cena na upit' (AC5)."
    )
    assert "None" not in html, (
        "a price_on_request property must NOT render 'None' in the price slot (AC5)."
    )
    assert "485000" in html or "485.000" in html, (
        "a property with a concrete price must render the formatted price (AC5)."
    )


# =========================================================================== #
# AC6 — empty-state, CTA href, route, regression                               #
# =========================================================================== #
@pytest.mark.django_db
def test_empty_state_renders_no_cards(client):
    # AC6: a filter matching nothing renders the listing-empty message, NO
    # property-card, and stays 200 (filter-bar still present).
    _make_property(title="Bilo sta")
    resp, html = _get_listing(client, "keyword=__nepostoji__")
    assert resp.status_code == 200
    assert _card_count(html) == 0, (
        f"a no-match filter must render NO property-card; got {_card_count(html)} (AC6)."
    )
    assert "listing-empty" in html, (
        "a no-match filter must render the listing-empty message (AC6)."
    )
    assert "filter-bar" in html, (
        "the filter-bar must remain visible on the empty state (AC6)."
    )


@pytest.mark.django_db
def test_card_cta_href_is_hardcoded_slug_path(client):
    # AC6/AC1: the card CTA links to the HARDCODED absolute /properties/<slug>/
    # (NOT {% url 'property-detail' %} — that route is 3.2; NoReverseMatch -> 500).
    # The 200 status here also proves no {% url %} blew up.
    p = _make_property(title="Sa Slugom", status="for_sale")
    resp, html = _get_listing(client)
    assert resp.status_code == 200, (
        "GET /properties/ must be 200 — a {% url 'property-detail' %} on the card "
        "would raise NoReverseMatch -> 500 (AC6)."
    )
    assert f'href="/properties/{p.slug}/"' in html, (
        f"the card CTA must link to the hardcoded absolute "
        f"href=\"/properties/{p.slug}/\" (NOT {{% url %}}) (AC1/AC6)."
    )


@pytest.mark.django_db
def test_listing_includes_pages_properties_css(client):
    # AC6: properties.html loads css/pages/properties.css via {% block extra_css %}.
    _make_property(title="Postojeca")
    resp, html = _get_listing(client)
    assert resp.status_code == 200
    assert "css/pages/properties.css" in html, (
        "properties.html must load css/pages/properties.css via {% block extra_css %} (AC6)."
    )


def test_properties_route_reverses_to_expected_path():
    # AC6: reverse("properties") == "/properties/".
    url = _try_reverse("properties")
    assert url == "/properties/", (
        f"reverse('properties') must equal '/properties/', got {url!r} (AC6)."
    )


def test_manage_py_check_passes():
    # AC6: `manage.py check` runs clean after the view/form/template/url changes.
    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc} (AC6)")


@pytest.mark.django_db
def test_home_still_returns_200(client):
    # AC6 (2.2 regression): GET / still returns 200 (Home featured links to the
    # now-live /properties/ route).
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / (Home) must still return 200, got {resp.status_code} (AC6 regression)."
    )


@pytest.mark.django_db
def test_admin_index_still_200_for_superuser(client, django_user_model):
    # AC6 (1.3 regression): the branded admin index still returns 200.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index at {_admin_index_path()} must still return 200 (AC6 regression)."
    )


@pytest.mark.django_db
def test_default_admin_path_still_404(client):
    # AC6 (1.3 regression): GET /admin/ stays 404 (admin mounts on ADMIN_URL).
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must still return 404, got {resp.status_code} (AC6 regression)."
    )


# =========================================================================== #
# Code-review hardening (batch-fix pass) — per-field validation + extra guards #
# =========================================================================== #
@pytest.mark.django_db
def test_per_field_skip_invalid_keeps_valid_filter(client):
    # AC2/AC3 (per-field validation): a garbage price_min must NOT discard a valid
    # property_type filter. ?price_min=abc&property_type=vila -> 200 AND only vile
    # render (price_min ignored per-field; property_type still applied). Guards the
    # old all-or-nothing `if form.is_valid()` regression.
    _make_property(title="Vila Validna", property_type="vila", status="for_sale")
    _make_property(title="Stan Nevidljiv", property_type="stan", status="for_sale")
    resp, html = _get_listing(client, "price_min=abc&property_type=vila")
    assert resp.status_code == 200, (
        "a garbage price_min alongside a valid property_type must still render 200 "
        "(per-field skip, not all-or-nothing)."
    )
    assert "Vila Validna" in html, (
        "the valid property_type=vila filter must STILL apply even though price_min "
        "is garbage (per-field validation)."
    )
    assert "Stan Nevidljiv" not in html, (
        "the property_type=vila filter must exclude the stan — proving the valid "
        "filter is applied despite the invalid price_min (per-field skip)."
    )


@pytest.mark.django_db
def test_filter_location_matches_location_city_branch(client):
    # AC2 (location_city branch): seed location_city="Beograd" with a DIFFERENT
    # district; ?location=beograd must match via the location_city icontains branch
    # of the single Q() filter.
    _make_property(title="Grad Beograd", location_city="Beograd",
                   location_district="Centar")
    _make_property(title="Drugi Grad", location_city="Novi Sad",
                   location_district="Liman")
    resp, html = _get_listing(client, "location=beograd")
    assert resp.status_code == 200
    assert "Grad Beograd" in html, (
        "?location=beograd must match location_city='Beograd' (icontains, "
        "case-insensitive) — the location_city OR branch."
    )
    assert "Drugi Grad" not in html, (
        "?location=beograd must NOT match the Novi Sad property."
    )


@pytest.mark.django_db
def test_bedrooms_zero_applies_gte_zero(client):
    # AC2: ?bedrooms=0 -> 200 and bedrooms__gte=0 (all visible). Guards against a
    # future `if bedrooms:` regression (0 is falsy — must be applied via
    # `is not None`, so all properties survive bedrooms>=0).
    _make_property(title="Nula soba", bedrooms=0)
    _make_property(title="Dve sobe", bedrooms=2)
    resp, html = _get_listing(client, "bedrooms=0")
    assert resp.status_code == 200
    assert "Nula soba" in html and "Dve sobe" in html, (
        "?bedrooms=0 must apply bedrooms__gte=0 (all visible) — 0 must not be "
        "treated as 'no filter' (guards `if bedrooms:` regression)."
    )


@pytest.mark.django_db
def test_price_min_only_keeps_price_on_request(client):
    # AC2: ?price_min=X alone applies price__gte AND keeps price_on_request
    # listings (NULL price OR-ed in). No price_max submitted.
    _make_property(title="Skupa cena", status="for_sale", price="600000.00")
    _make_property(title="Jeftina cena", status="for_sale", price="100000.00")
    _make_property(title="Na upit", status="price_on_request",
                   price_on_request=True, price=None)
    resp, html = _get_listing(client, "price_min=300000")
    assert resp.status_code == 200
    assert "Skupa cena" in html, (
        "?price_min=300000 must include a 600000 priced listing (price__gte)."
    )
    assert "Jeftina cena" not in html, (
        "?price_min=300000 must EXCLUDE a 100000 priced listing (below the min)."
    )
    assert "Na upit" in html, (
        "?price_min=300000 alone must KEEP a price_on_request listing (undisclosed "
        "price is not below the min — OR-ed in)."
    )


def test_clean_neutralises_inverted_range_to_none():
    # AC3 (clean() unit): instantiate PropertyFilterForm with an inverted range
    # (price_min > price_max), is_valid(), assert cleaned_data price_min/price_max
    # are BOTH None (neutralised, not a ValidationError).
    forms_mod = importlib.import_module("properties.forms")
    PropertyFilterForm = getattr(forms_mod, "PropertyFilterForm")
    form = PropertyFilterForm(data={"price_min": "500000", "price_max": "100000"})
    assert form.is_valid(), (
        f"an inverted range must NOT make the form invalid (clean() neutralises it, "
        f"no ValidationError). Errors: {form.errors!r}"
    )
    assert form.cleaned_data["price_min"] is None, (
        "clean() must set price_min to None on an inverted range."
    )
    assert form.cleaned_data["price_max"] is None, (
        "clean() must set price_max to None on an inverted range."
    )


@pytest.mark.django_db
def test_bedrooms_empty_deselection_skips_filter(client):
    # AC2/AC4: ?bedrooms= (empty) -> 200, all visible (required=False -> None ->
    # filter skipped). Mirrors the chip-deselection path (hidden input cleared).
    _make_property(title="Jedna soba", bedrooms=1)
    _make_property(title="Cetiri sobe", bedrooms=4)
    resp, html = _get_listing(client, "bedrooms=")
    assert resp.status_code == 200
    assert "Jedna soba" in html and "Cetiri sobe" in html, (
        "?bedrooms= (empty) must skip the bedrooms filter (None) — all visible."
    )
