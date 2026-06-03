"""
RED-phase contract tests for Story 6.1 — "Dvojezičnost SR/EN".

These tests define the CONTRACT for activating bilingual support (SR default
without a URL prefix, EN under a /en/ prefix) across config (urls/settings/
middleware), core (the {% loc %} templatetag), templates/base.html (the language
switcher + <html lang>) and the locale/ catalogs. They are written BEFORE the
feature is built, so the 6.1 tests in this module MUST FAIL/ERROR until the Dev
implements (GREEN phase):

  * config/settings/base.py — "django.middleware.locale.LocaleMiddleware" in
    MIDDLEWARE, STRICTLY after SessionMiddleware and STRICTLY before
    CommonMiddleware (Django-mandated ordering for URL-prefix language
    detection + APPEND_SLASH). LANGUAGE_CODE/USE_I18N/LANGUAGES/LOCALE_PATHS
    are unchanged (already correct).
  * config/urls.py — localizable routes (home/properties/property-detail/about/
    international/contact/private-collection) wrapped in
    i18n_patterns(prefix_default_language=False) -> SR default has NO prefix, EN
    gets /en/. ADMIN_URL/tinymce stay OUTSIDE i18n_patterns; an optional
    path("i18n/", include("django.conf.urls.i18n")) (set_language) is registered
    OUTSIDE the prefix as a fallback (the switcher does NOT use it).
  * core/templatetags/i18n_content.py — {% loc obj "base" %} simple_tag returning
    obj.localized(base) (active-language field with _sr fallback). HTMLField
    content uses {% loc obj "base" as var %}{{ var|safe }}.
  * templates/base.html — <html lang="{{ LANGUAGE_CODE }}">; the switcher is a
    GET <a href> built with {% translate_url %} (NO set_language POST form, NO
    {% csrf_token %}), keeping the exact lang-switcher container classes.
  * locale/sr/LC_MESSAGES + locale/en/LC_MESSAGES — .po (filled EN msgstr) + .mo
    (compilemessages). At RED there is no .po/.mo, so the gettext assertions are
    RED until the Dev adds + compiles the catalogs.

Design / locked rules (mirrors the 4.1 / 4.2 / 5.2 harness):
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * SiteSettings is seeded via load() (founder_photo="" placeholder branch). Page
    is seeded via .objects.create(slug=, title_sr=, content_sr=) (title_sr/
    content_sr required; _en is blank=True). Property is seeded via a DIRECT ORM
    .objects.create(...) (so description_en="" can be forced for the fallback
    test even though description_en is NOT blank=True at the model level).
  * Localizable-route reverse() assertions STILL return the SR no-prefix path
    under prefix_default_language=False — those existing tests are NOT touched
    here; this module re-asserts a few as a guard.
  * The 4 existing /en/->404 smoke tests are inverted by the Dev in GREEN — NOT
    in this file. A guard test here captures the NEW expected behaviour
    (GET /en/contact/ -> 200).
  * Each test maps to an acceptance criterion via an `# ACN:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    6-1-dvojezicnost-sr-en-interface-contract.md
"""
import importlib
import os

import pytest
from django.conf import settings
from django.template import Context, Template, TemplateSyntaxError
from django.urls import NoReverseMatch, reverse
from django.utils import translation


# --------------------------------------------------------------------------- #
# Model / path helpers — mirror tests/test_static_pages.py + test_contact_page #
# --------------------------------------------------------------------------- #
def _get_model(app_label, class_name):
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


def _admin_index_path():
    """The mounted admin index path, derived from settings.ADMIN_URL."""
    return "/" + settings.ADMIN_URL.strip("/") + "/"


def _try_reverse(name, **kwargs):
    """reverse(name) or None if the route does not exist yet (RED phase)."""
    try:
        return reverse(name, **kwargs)
    except NoReverseMatch:
        return None


# Distinct content sentinels so a render-assert proves the exact _sr/_en field
# reached the HTML (not an incidental substring collision).
ABOUT_TITLE_SR = "O-NAMA-SR"
ABOUT_TITLE_EN = "ABOUT-US-EN"
ABOUT_CONTENT_SR = "SADRZAJ-ABOUT-SR"
INTL_TITLE_SR = "MEDJUNARODNI-SR"
INTL_CONTENT_SR = "SADRZAJ-INTL-SR"
PROP_DESC_SR = "OPIS-SR-JEDINSTVEN"
PROP_DESC_EN = "DESC-EN-UNIQUE"


def _seed_site_settings(**overrides):
    """Load the singleton, populate founder/hero/contact and force the
    founder_photo="" placeholder branch (no SimpleUploadedFile / MEDIA_ROOT
    flakiness)."""
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.founder_name = "Đorđije Potpara"
    obj.founder_title_sr = "Osnivač"
    obj.founder_title_en = "Founder"
    obj.founder_bio_sr = "<p>Biografija SR</p>"
    obj.founder_bio_en = "<p>Biography EN</p>"
    obj.hero_headline_sr = "Naslov SR"
    obj.hero_headline_en = "Headline EN"
    obj.hero_cta_text_sr = "Pogledaj"
    obj.hero_cta_text_en = "Browse"
    obj.phone_primary = "+381119988776"
    obj.whatsapp_number = "381119988776"
    obj.email_primary = "kontakt@velegradestate.test"
    obj.email_inquiries = "upiti@velegradestate.test"
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _seed_page(slug, title_sr, content_sr, **overrides):
    """Create a Page. title_sr AND content_sr are required (else IntegrityError);
    title_en/content_en are blank=True so "" is fine."""
    Page = _get_model("pages", "Page")
    defaults = dict(
        slug=slug,
        title_sr=title_sr,
        title_en="",
        content_sr=content_sr,
        content_en="",
        is_active=True,
    )
    defaults.update(overrides)
    return Page.objects.create(**defaults)


def _make_property(**overrides):
    """Minimal active Property for routing + {% loc %} description tests.

    DIRECT ORM seed: lets the fallback test force description_en="" even though
    description_en is NOT blank=True at the model level (admin form would reject
    it, but the ORM accepts it — the documented edge scenario, M-C3)."""
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
        description_sr=f"<p>{PROP_DESC_SR}</p>",
        description_en=f"<p>{PROP_DESC_EN}</p>",
        price="485000.00",
        hero_image="",
        is_featured=False,
        is_active=True,
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


def _valid_post_data(**overrides):
    """The 4 user Inquiry fields + an empty honeypot (mirrors test_contact_page)."""
    data = dict(
        name="Marko Markovic",
        email="marko@example.com",
        phone="+381601234567",
        message="Zelim da stupim u kontakt sa savetnikom.",
        website="",  # honeypot empty -> a real (human) submit
    )
    data.update(overrides)
    return data


def _locale_file(lang, ext):
    return os.path.join(
        settings.BASE_DIR, "locale", lang, "LC_MESSAGES", f"django.{ext}"
    )


# =========================================================================== #
# AC1 — Routing: i18n_patterns(prefix_default_language=False)                  #
#   SR default has NO prefix; EN gets /en/. Admin/tinymce stay OUTSIDE.        #
# =========================================================================== #
@pytest.mark.django_db
def test_sr_routes_return_200_no_prefix(client):
    # AC1: SR (default, no prefix) routes still return 200 (seed Page(about/
    # international) + active Property so page_view/property-detail
    # get_object_or_404 don't yield a FALSE 404 from a missing object).
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE_SR, ABOUT_CONTENT_SR)
    _seed_page("international", INTL_TITLE_SR, INTL_CONTENT_SR)
    prop = _make_property()
    for path in [
        "/",
        "/properties/",
        f"/properties/{prop.slug}/",
        "/about/",
        "/international/",
        "/contact/",
        "/private-collection/",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"SR (no-prefix) GET {path} must return 200, got {resp.status_code} "
            f"(AC1)."
        )


@pytest.mark.django_db
def test_en_routes_return_200_with_prefix(client):
    # AC1: EN equivalents get the /en/ prefix and now return 200 (no longer 404 —
    # i18n_patterns was introduced). Seed the same objects so /en/about/,
    # /en/international/, /en/properties/<slug>/ don't yield a FALSE 404.
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE_SR, ABOUT_CONTENT_SR)
    _seed_page("international", INTL_TITLE_SR, INTL_CONTENT_SR)
    prop = _make_property()
    for path in [
        "/en/",
        "/en/properties/",
        f"/en/properties/{prop.slug}/",
        "/en/about/",
        "/en/international/",
        "/en/contact/",
        "/en/private-collection/",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"EN GET {path} must return 200 once i18n_patterns is wrapped around "
            f"the localizable routes, got {resp.status_code} (AC1)."
        )


def test_localizable_reverses_have_no_en_prefix():
    # AC1: under prefix_default_language=False the SR default has NO prefix, so
    # reverse() for localizable named routes returns the SR (no-/en/) path. This
    # is WHY the existing reverse() assertions stay valid — if any of these gain a
    # /en/ (or /sr/) prefix, prefix_default_language is mis-set (fix settings, NOT
    # the test).
    assert _try_reverse("home") == "/", "reverse('home') must equal '/' (AC1)."
    assert _try_reverse("about") == "/about/", (
        "reverse('about') must equal '/about/' (SR no-prefix) (AC1)."
    )
    assert _try_reverse("contact") == "/contact/", (
        "reverse('contact') must equal '/contact/' (SR no-prefix) (AC1)."
    )
    assert _try_reverse("properties") == "/properties/", (
        "reverse('properties') must equal '/properties/' (SR no-prefix) (AC1)."
    )


def test_locale_middleware_is_between_session_and_common():
    # AC1: LocaleMiddleware must sit STRICTLY after SessionMiddleware and STRICTLY
    # before CommonMiddleware (Django-mandated ordering — it reads the language
    # from the session/cookie/URL and must run before CommonMiddleware's
    # APPEND_SLASH redirect).
    mw = list(settings.MIDDLEWARE)
    assert "django.middleware.locale.LocaleMiddleware" in mw, (
        "MIDDLEWARE must contain django.middleware.locale.LocaleMiddleware (AC1)."
    )
    i_locale = mw.index("django.middleware.locale.LocaleMiddleware")
    i_session = mw.index("django.contrib.sessions.middleware.SessionMiddleware")
    i_common = mw.index("django.middleware.common.CommonMiddleware")
    assert i_session < i_locale < i_common, (
        "LocaleMiddleware must be AFTER SessionMiddleware and BEFORE "
        f"CommonMiddleware; got indices session={i_session}, locale={i_locale}, "
        f"common={i_common} (AC1)."
    )


@pytest.mark.django_db
def test_admin_stays_outside_i18n_patterns(client, django_user_model):
    # AC1: admin (ADMIN_URL) stays OUTSIDE i18n_patterns -> no /en/ prefix.
    # GET /en/<ADMIN_URL>/ -> 404 (admin does NOT get a language prefix);
    # /admin/ -> 404 (admin is mounted on the non-default ADMIN_URL, NFR-5).
    en_admin = "/en" + _admin_index_path()
    resp_en = client.get(en_admin)
    assert resp_en.status_code == 404, (
        f"admin must stay OUTSIDE i18n_patterns: GET {en_admin} must be 404, got "
        f"{resp_en.status_code} (AC1)."
    )
    resp_default = client.get("/admin/")
    assert resp_default.status_code == 404, (
        "the admin is mounted on ADMIN_URL, so GET /admin/ must be 404 (NFR-5) "
        f"(AC1); got {resp_default.status_code}."
    )


# =========================================================================== #
# AC2 — Language switcher (GET <a href> via translate_url) + <html lang>       #
# =========================================================================== #
@pytest.mark.django_db
def test_sr_render_has_html_lang_sr(client):
    # AC2: under SR (default, no prefix) the active language resolves to "sr"
    # (LANGUAGE_CODE="sr-latn" is NOT in LANGUAGES -> resolves to "sr"), so
    # <html lang="{{ LANGUAGE_CODE }}"> renders lang="sr".
    _seed_site_settings()
    resp = client.get("/")
    html = resp.content.decode("utf-8")
    assert 'lang="sr"' in html, (
        'GET / must render <html lang="sr"> (active language under the SR default) '
        "(AC2)."
    )


@pytest.mark.django_db
def test_en_render_has_html_lang_en(client):
    # AC2: under /en/ the active language is "en" -> <html lang="en">.
    _seed_site_settings()
    resp = client.get("/en/")
    # Guard against a framework 404 page accidentally carrying lang="en": the /en/
    # route must actually resolve (200) before we trust the lang attribute.
    assert resp.status_code == 200, (
        f"GET /en/ must resolve (200) before asserting <html lang> — i18n_patterns "
        f"must be wrapped around the localizable routes, got {resp.status_code} "
        "(AC2)."
    )
    html = resp.content.decode("utf-8")
    assert 'lang="en"' in html, (
        'GET /en/ must render <html lang="en"> (the html lang attribute must '
        "follow the active language) (AC2)."
    )


@pytest.mark.django_db
def test_switcher_uses_get_anchor_links_not_post_form(client):
    # AC2 (LOCKED): the switcher is a GET <a href> built with {% translate_url %},
    # NOT a set_language POST form. Within a lang-switcher container there must be
    # an <a ...href...> link and there must be NO csrf token field on the home
    # render (the switcher is the ONLY form-like element the contract introduces).
    _seed_site_settings()
    resp = client.get("/")
    html = resp.content.decode("utf-8")
    # A switcher LINK must exist (GET <a href>), not a <button>/POST form. The
    # switcher buttons keep their lang-switcher__btn class but become anchors, so
    # match an <a ...> that carries a switcher class AND an href (translate_url).
    import re
    switcher_anchor = re.search(
        r'<a\b[^>]*lang-switcher__[^>]*href=', html, re.IGNORECASE
    ) or re.search(
        r'<a\b[^>]*href=[^>]*lang-switcher__', html, re.IGNORECASE
    )
    assert switcher_anchor, (
        "the language switcher must use a GET <a href> link (translate_url) — not a "
        "<button>/set_language POST form — inside the lang-switcher container (AC2)."
    )
    assert "csrfmiddlewaretoken" not in html, (
        "the GET-link switcher must NOT introduce a CSRF token / POST form (the "
        "switcher is a pure GET <a href>, no {% csrf_token %}) (AC2)."
    )


def _switcher_hrefs(html):
    """Extract the SR + EN switcher hrefs from INSIDE a lang-switcher container.

    The page also carries non-switcher hrefs (e.g. the "reset filters" CTA on the
    properties listing renders href="/properties/"), so a whole-page substring
    assertion is a FALSE POSITIVE for the switcher. We scope to the lang-switcher__
    anchors and return {label: href} keyed by the anchor's visible label (SR/EN).
    """
    import re
    hrefs = {}
    for m in re.finditer(
        r'<a\b[^>]*class="[^"]*lang-switcher__btn[^"]*"[^>]*'
        r'href="([^"]*)"[^>]*>\s*([^<]+?)\s*</a>',
        html,
        re.IGNORECASE,
    ):
        href, label = m.group(1), m.group(2).strip()
        hrefs.setdefault(label, href)
    return hrefs


@pytest.mark.django_db
def test_switcher_links_to_en_equivalent_from_sr_page(client):
    # AC2: on an SR page the switcher's EN link points to the /en/ equivalent of
    # the CURRENT URL (translate_url preserves the path) and its SR link is the
    # no-prefix path. GET /properties/ -> switcher EN href == /en/properties/,
    # SR href == /properties/. Assertion is scoped to the lang-switcher anchors
    # (NOT the whole page) so a non-switcher href cannot mask a switcher bug.
    _seed_site_settings()
    resp = client.get("/properties/")
    hrefs = _switcher_hrefs(resp.content.decode("utf-8"))
    assert hrefs.get("EN") == "/en/properties/", (
        "on GET /properties/ the switcher EN link must point to the EN equivalent "
        f'/en/properties/ (translate_url); got {hrefs.get("EN")!r} (AC2).'
    )
    assert hrefs.get("SR") == "/properties/", (
        "on GET /properties/ the switcher SR link must be the no-prefix path "
        f'/properties/; got {hrefs.get("SR")!r} (AC2).'
    )


@pytest.mark.django_db
def test_switcher_links_back_to_sr_equivalent_from_en_page(client):
    # AC2: on an /en/ page the switcher's SR link points back to the SR (no-prefix)
    # equivalent and its EN link is the /en/ path. GET /en/properties/ -> switcher
    # SR href == /properties/, EN href == /en/properties/. Assertion is scoped to
    # the lang-switcher anchors (NOT the whole page) so the "reset filters" CTA's
    # href="/properties/" cannot produce a FALSE POSITIVE for the switcher.
    _seed_site_settings()
    resp = client.get("/en/properties/")
    hrefs = _switcher_hrefs(resp.content.decode("utf-8"))
    assert hrefs.get("SR") == "/properties/", (
        "on GET /en/properties/ the switcher SR link must point back to the SR "
        f'no-prefix equivalent /properties/; got {hrefs.get("SR")!r} (AC2).'
    )
    assert hrefs.get("EN") == "/en/properties/", (
        "on GET /en/properties/ the switcher EN link must be the /en/ path "
        f'/en/properties/; got {hrefs.get("EN")!r} (AC2).'
    )


@pytest.mark.django_db
def test_sr_prefixed_urls_are_404_sr_is_no_prefix_only(client):
    # AC1 (guard — SR analog of the /en/ guards): SR is the no-prefix default
    # (LANGUAGE_CODE="sr", prefix_default_language=False), so SR-prefixed URLs must
    # NOT serve content. GET /sr/ and GET /sr/properties/ -> 404 (the M1 bug made
    # these unexpectedly 200, duplicating SR content under a /sr/ prefix).
    _seed_site_settings()
    _make_property()
    for path in ["/sr/", "/sr/properties/"]:
        resp = client.get(path)
        assert resp.status_code == 404, (
            f"SR is no-prefix only: GET {path} must be 404 (not serve duplicate SR "
            f"content under a /sr/ prefix), got {resp.status_code} (AC1 guard)."
        )


@pytest.mark.django_db
def test_switcher_container_classes_preserved(client):
    # AC2: the wiring must NOT break test_base_layout.py — the exact header
    # (lang-switcher hide-mobile) and footer (lang-switcher) container classes
    # each still appear EXACTLY once on the home render (links go INSIDE the
    # containers; container classes are not changed).
    _seed_site_settings()
    resp = client.get("/")
    html = resp.content.decode("utf-8")
    assert html.count('class="lang-switcher hide-mobile"') == 1, (
        "exactly one (header) lang-switcher must carry hide-mobile (AC2)."
    )
    assert html.count('class="lang-switcher"') == 1, (
        "exactly one (footer) lang-switcher (without hide-mobile) must be present "
        "(AC2)."
    )


def test_set_language_fallback_is_registered_outside_prefix():
    # AC2 (optional fallback): path("i18n/", include("django.conf.urls.i18n")) MAY
    # stay registered as a fallback so reverse("set_language") resolves OUTSIDE the
    # /en/ prefix. The switcher does NOT use it, but the contract registers it.
    url = _try_reverse("set_language")
    assert url is not None, (
        "set_language must be registered (path('i18n/', "
        "include('django.conf.urls.i18n'))) as an OUTSIDE-prefix fallback (AC2)."
    )
    assert not url.startswith("/en/"), (
        "set_language must be registered OUTSIDE i18n_patterns (no /en/ prefix); "
        f"got {url!r} (AC2)."
    )


# =========================================================================== #
# AC3 — UI strings translated via gettext (.po/.mo, locale/sr + locale/en)     #
# =========================================================================== #
def test_locale_po_files_exist_and_non_empty():
    # AC3 (always-checkable structural assertion): the EN and SR .po catalogs
    # must exist and be non-empty (makemessages ran + EN msgstr filled). RED until
    # the Dev generates the catalogs.
    for lang in ("en", "sr"):
        po = _locale_file(lang, "po")
        assert os.path.exists(po), (
            f"locale/{lang}/LC_MESSAGES/django.po must exist (makemessages) (AC3)."
        )
        assert os.path.getsize(po) > 0, (
            f"locale/{lang}/LC_MESSAGES/django.po must be non-empty (AC3)."
        )


def test_locale_mo_files_exist():
    # AC3 (compilemessages foot-gun): Django reads the binary .mo at runtime, NOT
    # the .po — without compiled .mo no translation applies. RED until the Dev
    # runs compilemessages + checks in the .mo.
    for lang in ("en", "sr"):
        mo = _locale_file(lang, "mo")
        assert os.path.exists(mo), (
            f"locale/{lang}/LC_MESSAGES/django.mo must exist (compilemessages) "
            f"(AC3)."
        )


def test_gettext_translates_ui_label_under_en():
    # AC3 (runtime reinforcement — depends on a compiled .mo): with EN active, a
    # UI label is translated. RED until the Dev adds the .po translation +
    # compilemessages.
    with translation.override("en"):
        assert translation.gettext("Kontakt") == "Contact", (
            "with EN active, gettext('Kontakt') must return 'Contact' (compiled "
            ".mo) (AC3)."
        )


@pytest.mark.django_db
def test_en_render_contains_translated_ui_label(client):
    # AC3 (runtime reinforcement): the /en/ render contains an EN UI label that is
    # NOT in the SR render. "Contact" (EN) vs "Kontakt" (SR) for the nav/footer
    # label. RED until the .mo is compiled.
    _seed_site_settings()
    en_html = client.get("/en/").content.decode("utf-8")
    sr_html = client.get("/").content.decode("utf-8")
    assert "Contact" in en_html, (
        "the EN render must contain the translated UI label 'Contact' (AC3)."
    )
    assert "Contact" not in sr_html, (
        "the SR render must NOT contain the EN label 'Contact' (it stays 'Kontakt') "
        "(AC3)."
    )


# =========================================================================== #
# AC4 — DB content via {% loc %} (active-language _sr/_en, _sr fallback)        #
# =========================================================================== #
@pytest.mark.django_db
def test_property_description_localizes_to_en(client):
    # AC4: a Property with description_sr / description_en -> GET
    # /en/properties/<slug>/ shows the EN description.
    _seed_site_settings()
    prop = _make_property()
    html = client.get(f"/en/properties/{prop.slug}/").content.decode("utf-8")
    assert PROP_DESC_EN in html, (
        f"GET /en/properties/<slug>/ must render the EN description "
        f"({PROP_DESC_EN!r}) via {{% loc %}} (AC4)."
    )
    assert PROP_DESC_SR not in html, (
        "the EN property page must NOT render the SR description when description_en "
        "is set (AC4)."
    )


@pytest.mark.django_db
def test_property_description_localizes_to_sr(client):
    # AC4: under SR (no prefix) the property page shows description_sr.
    _seed_site_settings()
    prop = _make_property()
    html = client.get(f"/properties/{prop.slug}/").content.decode("utf-8")
    assert PROP_DESC_SR in html, (
        f"GET /properties/<slug>/ must render the SR description ({PROP_DESC_SR!r}) "
        f"via {{% loc %}} (AC4)."
    )


@pytest.mark.django_db
def test_property_description_falls_back_to_sr_when_en_empty(client):
    # AC4 (fallback, edge): a DIRECT ORM Property with description_en="" -> the EN
    # page falls back to description_sr (description_en is NOT blank=True, so this
    # is a test-only ORM seed, M-C3).
    _seed_site_settings()
    prop = _make_property(description_en="")
    html = client.get(f"/en/properties/{prop.slug}/").content.decode("utf-8")
    assert PROP_DESC_SR in html, (
        "with description_en empty, the EN property page must fall back to the SR "
        f"description ({PROP_DESC_SR!r}) (AC4 fallback)."
    )


@pytest.mark.django_db
def test_page_title_falls_back_to_sr_when_en_empty(client):
    # AC4 (fallback, realistic): Page.title_en is blank=True -> empty _en is a real
    # scenario. With title_en="" the /en/about/ page falls back to title_sr.
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE_SR, ABOUT_CONTENT_SR, title_en="")
    html = client.get("/en/about/").content.decode("utf-8")
    assert ABOUT_TITLE_SR in html, (
        "with title_en empty, GET /en/about/ must fall back to title_sr "
        f"({ABOUT_TITLE_SR!r}) via {{% loc %}} (AC4 fallback)."
    )


@pytest.mark.django_db
def test_page_title_localizes_to_en_when_set(client):
    # AC4: when title_en is set, GET /en/about/ shows the EN title (not the SR one).
    _seed_site_settings()
    _seed_page("about", ABOUT_TITLE_SR, ABOUT_CONTENT_SR, title_en=ABOUT_TITLE_EN)
    html = client.get("/en/about/").content.decode("utf-8")
    assert ABOUT_TITLE_EN in html, (
        f"GET /en/about/ must render title_en ({ABOUT_TITLE_EN!r}) via {{% loc %}} "
        "(AC4)."
    )


@pytest.mark.django_db
def test_loc_tag_renders_active_language(client):
    # AC4 (focused unit): {% loc obj "base" %} renders obj.localized(base) — the
    # active-language field. activate("en") -> _en; activate("sr") -> _sr. RED
    # until core/templatetags/i18n_content.py exists (TemplateSyntaxError on load).
    prop = _make_property()
    tmpl = Template("{% load i18n_content %}{% loc obj 'description' %}")
    with translation.override("en"):
        out_en = tmpl.render(Context({"obj": prop}))
    with translation.override("sr"):
        out_sr = tmpl.render(Context({"obj": prop}))
    assert PROP_DESC_EN in out_en, (
        "{% loc obj 'description' %} under EN must render the _en value (AC4)."
    )
    assert PROP_DESC_SR in out_sr, (
        "{% loc obj 'description' %} under SR must render the _sr value (AC4)."
    )


@pytest.mark.django_db
def test_loc_tag_falls_back_to_sr_when_en_empty():
    # AC4 (focused unit, fallback): {% loc %} == localized() -> empty _en falls
    # back to _sr.
    prop = _make_property(description_en="")
    tmpl = Template("{% load i18n_content %}{% loc obj 'description' %}")
    with translation.override("en"):
        out = tmpl.render(Context({"obj": prop}))
    assert PROP_DESC_SR in out, (
        "{% loc %} must fall back to the _sr value when _en is empty (matching "
        "LocalizedMixin.localized) (AC4 fallback)."
    )


def test_localized_helper_matches_active_language(db):
    # AC4 (unit): the {% loc %} tag is a thin wrapper over LocalizedMixin.localized
    # — assert the helper itself (active language + _sr fallback) so the tag
    # contract is anchored to the model helper.
    prop = _make_property(description_en="")
    SiteSettings = _get_model("core", "SiteSettings")
    s = SiteSettings.load()
    s.founder_title_sr = "Osnivač"
    s.founder_title_en = "Founder"
    s.save()
    with translation.override("en"):
        assert s.localized("founder_title") == "Founder"
        assert prop.localized("description") == f"<p>{PROP_DESC_SR}</p>", (
            "empty _en must fall back to _sr in localized() (AC4)."
        )
    with translation.override("sr"):
        assert s.localized("founder_title") == "Osnivač"


# =========================================================================== #
# AC5 — Cross-cutting guard: the new expected /en/ behaviour (200, not 404)    #
#   (Dev inverts the 4 existing /en/->404 tests in GREEN — NOT in this file.)  #
# =========================================================================== #
@pytest.mark.django_db
def test_en_contact_route_is_200_guard(client):
    # AC5 (guard for the inverted smoke test): GET /en/contact/ -> 200 (the NEW
    # expected behaviour once i18n_patterns is introduced). This captures the
    # contract here; the Dev inverts the original /en/->404 tests in their files.
    _seed_site_settings()
    resp = client.get("/en/contact/")
    assert resp.status_code == 200, (
        "GET /en/contact/ must now be 200 (i18n_patterns introduced), got "
        f"{resp.status_code} (AC5 cross-cutting inversion)."
    )


# =========================================================================== #
# Form POST under /en/ — i18n_patterns + CSRF + PRG together                   #
# =========================================================================== #
@pytest.mark.django_db
def test_contact_post_under_en_prefix_redirects_and_creates_inquiry(client):
    # AC1/AC5 (regression — i18n_patterns + CSRF + PRG together under /en/): a
    # valid POST to /en/contact/ self-posts to the /en/-prefixed request.path,
    # creates exactly ONE Inquiry, and PRG-redirects (302) to /en/contact/?sent=1.
    # email_inquiries is seeded (5.2 sends email on inquiry); we assert 302 + row,
    # not a strict mail count (avoid brittleness).
    _seed_site_settings()
    Inquiry = _get_model("inquiries", "Inquiry")
    assert Inquiry.objects.count() == 0
    resp = client.post("/en/contact/", data=_valid_post_data())
    assert resp.status_code == 302, (
        f"a valid POST to /en/contact/ must PRG-redirect (302), got "
        f"{resp.status_code} (i18n_patterns + CSRF + PRG)."
    )
    assert "/en/contact/" in resp.url and "sent=1" in resp.url, (
        "the PRG redirect must self-post to the /en/-prefixed path and carry "
        f"?sent=1, got {resp.url!r}."
    )
    assert Inquiry.objects.count() == 1, (
        f"a valid /en/ POST must create exactly ONE Inquiry, got "
        f"{Inquiry.objects.count()}."
    )


# =========================================================================== #
# T1 — Added coverage (code-review TEST_GAP): the {% translate_url %} tag unit  #
#   contract, the SiteSettings _en->_sr render fallback through {% loc %}, and  #
#   tinymce staying OUTSIDE i18n_patterns (/en/tinymce/ -> 404).                #
# =========================================================================== #
@pytest.mark.django_db
def test_translate_url_tag_builds_en_path_and_falls_back_without_request():
    # AC2 (unit for core/templatetags/i18n_content.translate_url): rendering
    # {% translate_url 'en' %} with a RequestContext whose request.path is a
    # localizable path returns the /en/-prefixed equivalent. The tag is built on
    # request.path (django.urls.translate_url), so it does NOT carry the query
    # string — a query string on request is dropped (path-only contract). With NO
    # request in the context the tag must fall back gracefully to "/" (path="/")
    # WITHOUT raising.
    from django.template import RequestContext
    from django.test import RequestFactory

    tmpl = Template("{% load i18n_content %}{% translate_url 'en' %}")

    # 1) request present -> /en/ prefix on the current path (query string is NOT
    #    part of request.path, so it is not preserved — path-only by contract).
    request = RequestFactory().get("/properties/", data={"filter": "x"})
    assert request.path == "/properties/"
    out = tmpl.render(RequestContext(request, {}))
    assert out == "/en/properties/", (
        "{% translate_url 'en' %} on request.path '/properties/' must render the "
        f"/en/ equivalent '/en/properties/' (path-only, query string dropped); "
        f"got {out!r}."
    )

    # 2) request missing -> the tag falls back GRACEFULLY to path="/" WITHOUT
    #    raising (the contract guarantee). translate_url("/", "en") then resolves
    #    the root under EN; the load-bearing assertion is "no raise + a stable
    #    string result" (the EN root reverses to "/en/" via i18n_patterns).
    out_no_request = tmpl.render(Context({}))
    assert out_no_request in ("/", "/en/"), (
        "{% translate_url %} with no request in context must fall back to the root "
        f"path ('/' -> translated) WITHOUT raising; got {out_no_request!r}."
    )


@pytest.mark.django_db
def test_site_settings_en_falls_back_to_sr_via_loc_render(client):
    # AC4 (SiteSettings _en->_sr fallback THROUGH the template {% loc %}, not just
    # the model unit): seed hero_headline_en="" + a UNIQUE hero_headline_sr, then
    # GET /en/ (the home hero renders {% loc site_settings "hero_headline" %}). The
    # EN page must show the _sr value (fallback), proving the SiteSettings fallback
    # path reaches the rendered HTML.
    _seed_site_settings(
        hero_headline_sr="HERO-SR-UNIQUE",
        hero_headline_en="",
    )
    html = client.get("/en/").content.decode("utf-8")
    assert "HERO-SR-UNIQUE" in html, (
        "with hero_headline_en empty, GET /en/ must fall back to hero_headline_sr "
        "('HERO-SR-UNIQUE') via {% loc %} on the home hero (AC4 fallback)."
    )


@pytest.mark.django_db
def test_tinymce_stays_outside_i18n_patterns(client):
    # AC1 (analog to /en/<ADMIN_URL>/ -> 404): tinymce routes stay OUTSIDE
    # i18n_patterns, so they get NO /en/ prefix. GET /en/tinymce/ -> 404.
    resp = client.get("/en/tinymce/")
    assert resp.status_code == 404, (
        "tinymce must stay OUTSIDE i18n_patterns: GET /en/tinymce/ must be 404 "
        f"(no language prefix on tinymce routes), got {resp.status_code} (AC1)."
    )
