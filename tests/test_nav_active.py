"""
Regression + coverage for the navigation active-link ("is-active") bug.

Bug (pre-fix): only the "Početna" (Home) nav link received the .is-active class
(via a hardcoded `request.path == '/'` check); the other 5 links never got it,
so they never underlined when their page was active. The hardcoded '/' check also
failed under the EN locale (home is /en/).

Fix: is-active is derived from request.resolver_match.url_name (locale-agnostic —
same url_name with or without the /en/ prefix), applied to BOTH the desktop
.site-nav and the mobile .mobile-menu, for all 6 links. "properties" is active on
both the listing and property-detail pages.

These tests assert, per page, that the EXPECTED nav link carries is-active inside
the .site-nav region AND that a DIFFERENT link does not.
"""
import importlib
import re

import pytest
from django.conf import settings


# --------------------------------------------------------------------------- #
# Seed helpers — mirror tests/test_i18n.py (SiteSettings.load + direct ORM).    #
# --------------------------------------------------------------------------- #
def _get_model(app_label, class_name):
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


def _seed_site_settings():
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.founder_name = "Đorđije Potpara"
    obj.founder_title_sr = "Osnivač"
    obj.hero_headline_sr = "Naslov SR"
    obj.hero_cta_text_sr = "Pogledaj"
    obj.phone_primary = "+381119988776"
    obj.email_primary = "kontakt@velegradestate.test"
    obj.email_inquiries = "upiti@velegradestate.test"
    obj.founder_photo = ""
    obj.save()
    return obj


def _make_property(**overrides):
    Property = _get_model("properties", "Property")
    defaults = dict(
        title="Vila Dedinje Test",
        status="for_sale",
        collection_type="signature",
        property_type="vila",
        location_city="Beograd",
        location_district="Dedinje",
        area_sqm="80.00",
        area_total_sqm="90.00",
        bedrooms=2,
        bathrooms=1,
        floor=3,
        total_floors=5,
        parking_spaces=1,
        description_sr="<p>Opis SR</p>",
        description_en="<p>Desc EN</p>",
        price="485000.00",
        hero_image="",
        is_featured=False,
        is_active=True,
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


# --------------------------------------------------------------------------- #
# Region-scoped assertion helpers — the .site-nav block only.                   #
# --------------------------------------------------------------------------- #
def _site_nav_html(html):
    """Return the inner HTML of the <nav class="site-nav">...</nav> block.

    Scoping is mandatory: a bare "is-active" substring also matches the
    lang-switcher (lang-switcher__btn is-active) and the mobile-menu, so a
    whole-page check would be a false positive for the desktop nav.
    """
    m = re.search(r'<nav class="site-nav".*?</nav>', html, re.DOTALL)
    assert m, "the .site-nav block must be present in the rendered HTML."
    return m.group(0)


def _mobile_menu_html(html):
    m = re.search(r'<div class="mobile-menu".*?</div>', html, re.DOTALL)
    assert m, "the .mobile-menu block must be present in the rendered HTML."
    return m.group(0)


# href -> link label, used to map an <a> to which nav item it is. The hrefs are
# the no-prefix SR paths produced by {% url %} under prefix_default_language=False.
_HREF_BY_KEY = {
    "home": "/",
    "about": "/about/",
    "properties": "/properties/",
    "private-collection": "/private-collection/",
    "international": "/international/",
    "contact": "/contact/",
}


def _link_is_active(region_html, key, href_prefix=""):
    """True if the nav <a> whose href matches `key` carries the is-active class.

    Matches the FULL <a ...>...</a> tag for the given href and checks for
    is-active inside its class attribute (so the assertion is scoped to that one
    link, not anywhere in the region). href_prefix supports the /en/ regression.
    """
    href = href_prefix + _HREF_BY_KEY[key]
    # The home href is "/" which is a prefix of every other href, so anchor on a
    # closing quote to require an EXACT href match.
    pattern = r'<a\b[^>]*\bhref="' + re.escape(href) + r'"[^>]*>'
    m = re.search(pattern, region_html)
    assert m, f"expected a nav <a> with href={href!r} in the region."
    tag = m.group(0)
    cls = re.search(r'class="([^"]*)"', tag)
    return bool(cls and "is-active" in cls.group(1))


# =========================================================================== #
# Per-page: the expected link is active, a different one is NOT (both menus).   #
# =========================================================================== #
@pytest.mark.django_db
def test_home_link_active_others_not(client):
    _seed_site_settings()
    html = client.get("/").content.decode("utf-8")
    nav = _site_nav_html(html)
    mob = _mobile_menu_html(html)
    assert _link_is_active(nav, "home"), "Home link must be is-active on GET / (desktop)."
    assert _link_is_active(mob, "home"), "Home link must be is-active on GET / (mobile)."
    assert not _link_is_active(nav, "contact"), "Contact must NOT be active on GET /."
    assert not _link_is_active(nav, "about"), "About must NOT be active on GET /."


@pytest.mark.django_db
def test_properties_link_active_on_listing(client):
    _seed_site_settings()
    html = client.get("/properties/").content.decode("utf-8")
    nav = _site_nav_html(html)
    mob = _mobile_menu_html(html)
    assert _link_is_active(nav, "properties"), "Properties must be active on /properties/ (desktop)."
    assert _link_is_active(mob, "properties"), "Properties must be active on /properties/ (mobile)."
    assert not _link_is_active(nav, "home"), "Home must NOT be active on /properties/."


@pytest.mark.django_db
def test_properties_link_active_on_property_detail(client):
    # property-detail url_name must light up the "Odabrane nekretnine" (properties)
    # link too — the listing's parent nav item.
    _seed_site_settings()
    prop = _make_property()
    html = client.get(f"/properties/{prop.slug}/").content.decode("utf-8")
    nav = _site_nav_html(html)
    assert _link_is_active(nav, "properties"), (
        "Properties must be active on a property-detail page (/properties/<slug>/)."
    )
    assert not _link_is_active(nav, "home"), "Home must NOT be active on property-detail."


@pytest.mark.django_db
def test_about_link_active(client):
    # /about/ is 200 thanks to the 0002_seed_static_pages seed migration.
    _seed_site_settings()
    html = client.get("/about/").content.decode("utf-8")
    nav = _site_nav_html(html)
    mob = _mobile_menu_html(html)
    assert _link_is_active(nav, "about"), "About must be active on /about/ (desktop)."
    assert _link_is_active(mob, "about"), "About must be active on /about/ (mobile)."
    assert not _link_is_active(nav, "home"), "Home must NOT be active on /about/."


@pytest.mark.django_db
def test_international_link_active(client):
    # /international/ is 200 thanks to the 0002_seed_static_pages seed migration.
    _seed_site_settings()
    html = client.get("/international/").content.decode("utf-8")
    nav = _site_nav_html(html)
    assert _link_is_active(nav, "international"), "International must be active on /international/."
    assert not _link_is_active(nav, "contact"), "Contact must NOT be active on /international/."


@pytest.mark.django_db
def test_contact_link_active(client):
    _seed_site_settings()
    html = client.get("/contact/").content.decode("utf-8")
    nav = _site_nav_html(html)
    mob = _mobile_menu_html(html)
    assert _link_is_active(nav, "contact"), "Contact must be active on /contact/ (desktop)."
    assert _link_is_active(mob, "contact"), "Contact must be active on /contact/ (mobile)."
    assert not _link_is_active(nav, "home"), "Home must NOT be active on /contact/."


@pytest.mark.django_db
def test_private_collection_link_active(client):
    _seed_site_settings()
    html = client.get("/private-collection/").content.decode("utf-8")
    nav = _site_nav_html(html)
    assert _link_is_active(nav, "private-collection"), (
        "Private collection must be active on /private-collection/."
    )
    assert not _link_is_active(nav, "home"), "Home must NOT be active on /private-collection/."


# =========================================================================== #
# Regression for the hardcoded-'/' bug: Home must be active under /en/ too.     #
# =========================================================================== #
@pytest.mark.django_db
def test_home_link_active_under_en_locale(client):
    # The old `request.path == '/'` check failed under EN (home is /en/). The
    # url_name-based check is locale-agnostic, so Home is active on /en/ as well.
    _seed_site_settings()
    html = client.get("/en/").content.decode("utf-8")
    nav = _site_nav_html(html)
    # The Home link is a literal href="/" (not {% url %}), so it stays "/" even on
    # /en/. What matters is the is-active class, derived from url_name=='home'.
    assert _link_is_active(nav, "home"), (
        "Home must be is-active on GET /en/ (url_name-based, locale-agnostic) — "
        "regression for the hardcoded '/' bug."
    )
