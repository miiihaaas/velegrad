"""
RED-phase contract tests for Story 2.1 — "Integracija dizajn sistema i bazni layout".

These tests define the CONTRACT for the public frontend FRAME: the design-system
static cascade copied into static/, templates/base.html (head blocks + branded
header/footer), a base-extending custom premium templates/404.html served via an
explicit handler404, a minimal "/" home route so the layout can be rendered, and
the placeholder-SVG fallback. They are written BEFORE the feature is built, so
EVERY 2.1 test in this module MUST FAIL/ERROR until the Dev implements:

  * static/css/{tokens,base,layout,components,utilities}.css + css/pages/*.css,
    static/js/{main,gallery,filters,forms}.js, and all 9
    static/images/placeholders/*.svg (assets copied from docs/OpenDesignFiles);
  * templates/base.html with {% block title/meta_description/og/schema/ga4/
    extra_css/content/extra_js %}, the {% static %}-referenced cascade in order,
    main.js with `defer`, and classes site-header / site-nav / lang-switcher /
    mobile-menu-toggle / mobile-menu / site-footer — all UI strings {% trans %};
  * templates/404.html that {% extends "base.html" %} (error-page in the content
    block, error.css via extra_css);
  * pages.views.custom_404 + handler404 = "pages.views.custom_404" in config.urls;
  * a minimal "/" route rendering a base-extending home.html WITHOUT DB content.

Design rules (mirrors the 1.3 harness in tests/test_admin_dashboard.py):
  * DB / client tests are marked @pytest.mark.django_db (pytest-django is active
    via DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * The admin path is computed from settings.ADMIN_URL the SAME way the app does
    (config/urls.py reads settings.ADMIN_URL, already slash-normalized) — the 1.3
    regression tests use _admin_index_path(), never a hardcoded "/admin/".
  * RED failures are meant to read as "feature absent" (missing static file /
    TemplateDoesNotExist / 404-vs-expected / "/" route absent), NOT collection
    crashes. Helpers that touch fragile state (reading maybe-absent template
    files) are guarded so the failure is a clean assertion, not an import error.
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    2-1-integracija-dizajn-sistema-i-bazni-layout-interface-contract.md
"""
from pathlib import Path

import pytest
from django.conf import settings
from django.test import override_settings


# --------------------------------------------------------------------------- #
# Path helpers — static/ on disk and templates/ on disk.                        #
# --------------------------------------------------------------------------- #
def _static_dir():
    return Path(settings.BASE_DIR) / "static"


def _template_path(name):
    return Path(settings.BASE_DIR) / "templates" / name


def _read_template(name):
    """Return the raw text of templates/<name>, or "" if it does not exist yet.

    Returning "" (instead of raising) lets the calling test assert the feature's
    *absence* as a clean failure rather than erroring at read time in RED.
    """
    p = _template_path(name)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Admin-regression helpers — derive the admin URL the way the app does (1.3).   #
# --------------------------------------------------------------------------- #
def _admin_index_path():
    """The mounted admin index path, derived from settings.ADMIN_URL."""
    return "/" + settings.ADMIN_URL.strip("/") + "/"


def _superuser(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass12345",
    )


# Canonical asset lists (Interface Contract §1).
_CASCADE_CSS = ["tokens.css", "base.css", "layout.css", "components.css", "utilities.css"]
_PLACEHOLDER_SVGS = [
    "hero-placeholder.svg",
    "founder-portrait.svg",
    "property-1.svg",
    "property-2.svg",
    "property-3.svg",
    "property-4.svg",
    "logo.svg",
    "floor-plan.svg",
    "property-detail-hero.svg",
]


# =========================================================================== #
# AC1 — CSS cascade + JS in static/, referenced via {% static %} in order      #
# =========================================================================== #
def test_cascade_css_files_exist_on_disk():
    # AC1: the five global cascade CSS files must be copied into static/css/.
    css_dir = _static_dir() / "css"
    missing = [name for name in _CASCADE_CSS if not (css_dir / name).exists()]
    assert not missing, (
        f"missing global cascade CSS in static/css/: {missing} (AC1). Copy from "
        f"docs/OpenDesignFiles/assets/css/."
    )


def test_main_js_exists_on_disk():
    # AC1: static/js/main.js must be copied into static/js/.
    assert (_static_dir() / "js" / "main.js").exists(), (
        "static/js/main.js must exist (copied from docs/OpenDesignFiles/assets/js/) (AC1)."
    )


def test_secondary_js_files_exist_on_disk():
    # AC1: gallery/filters/forms.js are part of the complete cascade copy (used
    # per-page in later epics) — they must still be present in static/js/.
    js_dir = _static_dir() / "js"
    missing = [n for n in ("gallery.js", "filters.js", "forms.js") if not (js_dir / n).exists()]
    assert not missing, f"missing JS in static/js/: {missing} (AC1)."


def test_pages_css_files_exist_on_disk():
    # AC1: all per-page CSS (incl. error.css used by 404) is copied into
    # static/css/pages/ so the cascade is complete (pages CSS is included
    # per-page in later epics, not globally in base).
    pages_dir = _static_dir() / "css" / "pages"
    expected = [
        "home.css", "about.css", "contact.css", "error.css",
        "international.css", "private-collection.css",
        "properties.css", "property-detail.css",
    ]
    missing = [n for n in expected if not (pages_dir / n).exists()]
    assert not missing, f"missing per-page CSS in static/css/pages/: {missing} (AC1)."


@pytest.mark.django_db
def test_home_renders_css_cascade_in_correct_order(client):
    # AC1/AC4: GET / returns HTML whose {% static %}-resolved CSS hrefs appear in
    # the exact cascade order tokens < base < layout < components < utilities.
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / must return 200 so the base layout can be validated, got "
        f"{resp.status_code} (AC1/AC7)."
    )
    html = resp.content.decode("utf-8")
    # Anchor each lookup on the {% static %}-resolved path fragment "css/<name>"
    # (e.g. "css/base.css") rather than the bare filename. This is the exact
    # shape {% static 'css/base.css' %} renders, and it makes the positional
    # assertion robust against any incidental substring collision (the bare
    # "base.css" can never be mistaken for a stray token; the global-cascade
    # links live under css/, while per-page CSS lives under css/pages/ and is
    # excluded from base — see test_home_does_not_include_pages_css_globally).
    positions = {}
    for name in _CASCADE_CSS:
        needle = f"css/{name}"
        idx = html.find(needle)
        assert idx != -1, (
            f"{needle!r} reference missing from GET / HTML — base.html must link "
            f"the global cascade via {{% static 'css/{name}' %}} (AC1)."
        )
        positions[name] = idx
    assert (
        positions["tokens.css"] < positions["base.css"]
        < positions["layout.css"] < positions["components.css"]
        < positions["utilities.css"]
    ), (
        f"CSS cascade must load in order tokens<base<layout<components<utilities "
        f"(tokens define vars used downstream) (AC1); got {positions}."
    )


@pytest.mark.django_db
def test_home_includes_main_js_with_defer(client):
    # AC1: base.html references main.js via {% static %} AND its <script> tag
    # carries `defer` (faithful to docs/OpenDesignFiles/index.html line 341).
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "main.js" in html, "base.html must include js/main.js via {% static %} (AC1)."
    # Find the specific <script> tag for main.js and require `defer` on it.
    import re
    m = re.search(r"<script\b[^>]*\bmain\.js[^>]*>", html)
    assert m is not None, "could not find the <script> tag loading main.js (AC1)."
    assert "defer" in m.group(0), (
        f"the main.js <script> tag must carry `defer` (AC1); got: {m.group(0)!r}."
    )


@pytest.mark.django_db
def test_home_does_not_include_pages_css_globally(client):
    # Story 2.2 (AC7) intentionally moves the page-CSS boundary: home.html now
    # loads its OWN per-page CSS (css/pages/home.css) via {% block extra_css %}.
    # The original 2.1 assertion ("home must not include ANY pages/home.css")
    # encoded the 2.1-era frame where Home had no page CSS; 2.2 legitimately adds
    # it. Narrowed assertion: home MAY load its own home.css, but must NOT pull in
    # OTHER pages' CSS (e.g. about/contact).
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "css/pages/about.css" not in html and "css/pages/contact.css" not in html, (
        "home must not include OTHER pages' per-page CSS; only css/pages/home.css "
        "is allowed (2.2 AC7 moved the boundary)."
    )


# =========================================================================== #
# AC2 — base.html: head blocks + branded header + footer                       #
# =========================================================================== #
@pytest.mark.django_db
def test_base_renders_header_and_footer_classes(client):
    # AC2: GET / (which extends base.html) renders the required structural
    # classes: site-header, site-nav, lang-switcher, mobile-menu-toggle (with
    # aria-expanded), mobile-menu, site-footer.
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    for needle in (
        'class="site-header"',
        'class="site-nav"',
        "lang-switcher",
        "mobile-menu-toggle",
        "mobile-menu",
        'class="site-footer"',
    ):
        assert needle in html, f"base.html must render {needle!r} (AC2)."
    assert "aria-expanded" in html, (
        "the mobile-menu-toggle must carry aria-expanded (AC2/a11y)."
    )


@pytest.mark.django_db
def test_base_renders_title_and_meta_description(client):
    # AC2: base.html has a <title> and a meta description.
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "<title>" in html, "base.html must render a <title> (AC2)."
    assert 'name="description"' in html, (
        "base.html must render a <meta name=\"description\"> (AC2)."
    )


@pytest.mark.django_db
def test_header_precedes_content_precedes_footer(client):
    # AC2: header comes before {% block content %} which comes before the footer
    # (the frame wraps the page content).
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    h = html.find("site-header")
    f = html.find("site-footer")
    assert h != -1 and f != -1, "both site-header and site-footer must render (AC2)."
    assert h < f, "site-header must appear before site-footer in the document (AC2)."


def test_child_template_overriding_title_block_changes_title():
    # AC2: a child template extending base.html and overriding {% block title %}
    # changes the rendered <title>. Render an inline child via the template engine
    # (no DB, no route needed) so this binds to base.html's block contract.
    from django.template import engines

    marker = "ZZ_CHILD_TITLE_MARKER_2_1_ZZ"
    src = (
        "{% extends 'base.html' %}"
        "{% block title %}" + marker + "{% endblock %}"
        "{% block content %}x{% endblock %}"
    )
    dj = engines["django"]
    template = dj.from_string(src)
    # render() resolves {% extends 'base.html' %}; if base.html is absent yet
    # (RED) it raises TemplateDoesNotExist("base.html") — a clean "feature
    # absent" failure, not a collection crash.
    rendered = template.render({})
    assert marker in rendered, (
        "a child overriding {% block title %} must change the rendered <title> — "
        "base.html must wrap its title in an override-able {% block title %} (AC2)."
    )
    title_idx = rendered.find("<title>")
    assert title_idx != -1 and marker in rendered[title_idx:title_idx + 200], (
        "the overridden title text must appear inside the <title> element (AC2)."
    )


# =========================================================================== #
# AC3 — i18n hygiene: {% load i18n %} + mandatory {% trans %} string set        #
# =========================================================================== #
def test_base_template_loads_i18n_and_uses_trans():
    # AC3: base.html must {% load i18n %} and mark UI strings with {% trans %}.
    src = _read_template("base.html")
    assert src, "templates/base.html must exist (AC2/AC3)."
    assert "{% load i18n %}" in src or "{% load static i18n %}" in src or "i18n" in (
        " ".join(line for line in src.splitlines() if "{% load" in line)
    ), "base.html must {% load i18n %} (AC3)."
    assert "{% trans" in src or "{% blocktrans" in src, (
        "base.html must mark UI strings with {% trans %}/{% blocktrans %} (AC3)."
    )


def test_404_template_loads_i18n_and_uses_trans():
    # AC3: 404.html must {% load i18n %} and mark its UI strings with {% trans %}.
    src = _read_template("404.html")
    assert src, "templates/404.html must exist (AC5/AC3)."
    assert "i18n" in " ".join(line for line in src.splitlines() if "{% load" in line), (
        "404.html must {% load i18n %} (AC3)."
    )
    assert "{% trans" in src or "{% blocktrans" in src, (
        "404.html must mark its UI strings (404 CTAs, message) with {% trans %} (AC3)."
    )


def test_base_has_no_unwrapped_mandatory_nav_strings():
    # AC3: the LOCKED mandatory header-nav UI strings must be {% trans %}-wrapped,
    # i.e. they must NOT appear as bare literal text in <a>...</a> in base.html.
    # (A {% trans "Kontakt" %} keeps "Kontakt" only inside the tag, not as bare
    # ">Kontakt<" anchor text — so bare anchor text means an unmarked string.)
    src = _read_template("base.html")
    assert src, "templates/base.html must exist (AC3)."
    for label in ("Kontakt", "Početna"):
        assert f">{label}<" not in src, (
            f"the nav label {label!r} appears as a bare (unmarked) anchor string "
            f"in base.html — it MUST be wrapped in {{% trans %}} (AC3)."
        )


def test_404_has_no_unwrapped_mandatory_cta_strings():
    # AC3/AC5: both 404 CTA strings ("Vratite se na početnu", "Kontaktirajte nas")
    # must be {% trans %}-wrapped, not bare literal anchor text.
    src = _read_template("404.html")
    assert src, "templates/404.html must exist (AC3/AC5)."
    for cta in ("Vratite se na početnu", "Kontaktirajte nas"):
        assert f">{cta}<" not in src, (
            f"the 404 CTA {cta!r} appears as bare anchor text — it MUST be wrapped "
            f"in {{% trans %}} (AC3/AC5)."
        )
        assert cta in src, (
            f"the 404 CTA {cta!r} must be present (inside a {{% trans %}}) in "
            f"404.html (AC5)."
        )


# =========================================================================== #
# AC4 — responsive / mobile-first markup (viewport + toggle + hide-mobile)      #
# =========================================================================== #
@pytest.mark.django_db
def test_base_has_viewport_meta(client):
    # AC4: base.html must carry the device-width viewport meta tag.
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'name="viewport"' in html and "width=device-width" in html, (
        "base.html must render <meta name=\"viewport\" content=\"width=device-width"
        ", initial-scale=1.0\"> (AC4)."
    )


@pytest.mark.django_db
def test_base_has_mobile_toggle_and_hide_mobile_lang_switcher(client):
    # AC4: the mobile-menu-toggle (hamburger) and the lang-switcher.hide-mobile
    # classes are present (mobile-first markup carried faithfully from design).
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "mobile-menu-toggle" in html, "mobile-menu-toggle class must be present (AC4)."
    assert "hide-mobile" in html, (
        "the header lang-switcher must carry the hide-mobile class (AC4)."
    )


# =========================================================================== #
# AC5 — custom premium 404 via handler404, extending base                      #
# =========================================================================== #
def test_404_template_extends_base():
    # AC5 (locked): templates/404.html MUST {% extends "base.html" %} so the error
    # page inherits the site-header/site-footer frame (brand consistency). A
    # standalone copy of docs/OpenDesignFiles/404.html would fail this.
    src = _read_template("404.html")
    assert src, "templates/404.html must exist (AC5)."
    assert '{% extends "base.html" %}' in src or "{% extends 'base.html' %}" in src, (
        "404.html MUST {% extends \"base.html\" %} (locked AC5) — not a standalone page."
    )


def test_404_template_links_error_css_via_extra_css():
    # AC5: error-specific styles load via {% block extra_css %} -> error.css
    # (NOT re-loading the global cascade; base already provides it).
    src = _read_template("404.html")
    assert src, "templates/404.html must exist (AC5)."
    assert "extra_css" in src, "404.html must override {% block extra_css %} (AC5)."
    assert "css/pages/error.css" in src, (
        "404.html must load css/pages/error.css via {% block extra_css %} (AC5)."
    )


@override_settings(DEBUG=False)
@pytest.mark.django_db
def test_custom_404_served_within_base_frame(client):
    # AC5: with DEBUG=False, GET on a non-existent path returns HTTP 404, AND the
    # premium template renders ("404"/error-page) INSIDE the base frame (site-header
    # AND site-footer present). Use a non-existent path (NOT reverse). testserver
    # is in ALLOWED_HOSTS (config/settings/test.py). This proves the explicit
    # handler404 -> base-extending 404.html, not the Django default "Not Found".
    resp = client.get("/nepostojeca-stranica/")
    assert resp.status_code == 404, (
        f"a non-existent path must return HTTP 404, got {resp.status_code} (AC5)."
    )
    html = resp.content.decode("utf-8")
    assert "404" in html, "the custom 404 must render the '404' code (AC5)."
    assert "error-page" in html, (
        "the custom 404 must render the premium 'error-page' markup, not the "
        "Django default page (AC5)."
    )
    assert "site-header" in html and "site-footer" in html, (
        "the custom 404 must render INSIDE the base frame (site-header AND "
        "site-footer) — proving it {% extends \"base.html\" %} (locked AC5). A "
        "standalone 404 would fail here."
    )


def test_handler404_registered_as_explicit_custom_view():
    # AC5 (locked): config.urls must register handler404 = "pages.views.custom_404"
    # — an explicit view giving a clear status=404, not Django's implicit default.
    import config.urls as urlconf

    handler = getattr(urlconf, "handler404", None)
    assert handler == "pages.views.custom_404", (
        f"config.urls.handler404 must be 'pages.views.custom_404' (locked AC5); "
        f"got {handler!r}."
    )
    from django.utils.module_loading import import_string

    view = import_string("pages.views.custom_404")
    assert callable(view), "pages.views.custom_404 must be a callable view (AC5)."


# =========================================================================== #
# AC6 — placeholder SVG fallback                                               #
# =========================================================================== #
def test_all_nine_placeholder_svgs_exist_on_disk():
    # AC6: ALL 9 placeholder SVGs must be copied into static/images/placeholders/.
    ph_dir = _static_dir() / "images" / "placeholders"
    missing = [name for name in _PLACEHOLDER_SVGS if not (ph_dir / name).exists()]
    assert not missing, (
        f"missing placeholder SVGs in static/images/placeholders/: {missing} (AC6). "
        f"All 9 are mandatory."
    )


@pytest.mark.django_db
def test_base_logo_uses_static_placeholder_not_base64(client):
    # AC6: base.html's logo uses a {% static %} placeholder
    # (images/placeholders/logo.svg in src) — NOT the inline base64 blob from the
    # design's index.html.
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "images/placeholders/logo.svg" in html, (
        "base.html logo must reference images/placeholders/logo.svg via {% static %} "
        "(AC6)."
    )
    assert "data:image" not in html, (
        "base.html must NOT embed the inline base64 logo blob from the design — use "
        "the {% static %} placeholder logo instead (AC6)."
    )


# =========================================================================== #
# AC7 — base renders, / does not 500, manage.py check clean, 1.3 regression     #
# =========================================================================== #
@pytest.mark.django_db
def test_home_route_returns_200_with_frame(client):
    # AC7: GET / returns 200 and the HTML contains the base frame
    # (site-header + site-footer) — the minimal home route renders base.html.
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / must return 200 (minimal home route), got {resp.status_code} (AC7)."
    )
    html = resp.content.decode("utf-8")
    assert "site-header" in html and "site-footer" in html, (
        "GET / must render the base frame (site-header + site-footer) (AC7)."
    )


@pytest.mark.django_db
def test_admin_index_still_200_for_superuser(client, django_user_model):
    # AC7 (1.3 regression): the branded admin index at settings.ADMIN_URL still
    # returns 200 for a logged-in superuser (unchanged by adding the frontend).
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index at {_admin_index_path()} must still return 200 (1.3 "
        f"regression), got {resp.status_code} (AC7)."
    )


@pytest.mark.django_db
def test_default_admin_path_still_404(client):
    # AC7 (1.3 regression): GET /admin/ must still be 404 (admin mounts on
    # ADMIN_URL, NFR-5). Adding the "/" route and handler404 must not expose /admin/.
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must still return 404 (NFR-5, 1.3 regression), got "
        f"{resp.status_code} (AC7)."
    )


# =========================================================================== #
# AC3 — FULL locked mandatory {% trans %} set (broadened — source assertions)  #
# =========================================================================== #
def _trans_wrapped(src, label):
    """True if `label` appears inside a {% trans "..." %}/{% trans '...' %} tag.

    Asserting on the template SOURCE (not the render) is the robust check the
    Interface Contract asks for: without .mo files {% trans %} returns the bare
    string, so a rendered ">Label<" cannot distinguish wrapped from unwrapped.
    """
    return (
        f'{{% trans "{label}" %}}' in src
        or f"{{% trans '{label}' %}}" in src
    )


def test_base_full_mandatory_trans_set_is_wrapped():
    # AC3 (locked, broadened): the FULL mandatory UI-string set in base.html must
    # be {% trans %}-wrapped — header nav labels, the hamburger aria-label, both
    # SR/EN language-switcher labels, the footer copyright, the footer nav section
    # titles, and the logo aria-label. Source-level assertion (see _trans_wrapped).
    src = _read_template("base.html")
    assert src, "templates/base.html must exist (AC3)."

    mandatory = [
        # header nav link labels (site-nav)
        "Početna",
        "Privatno savetovanje",
        "Odabrane nekretnine",
        "Privatna kolekcija",
        "Međunarodni klijenti",
        "Kontakt",
        # hamburger (mobile-menu-toggle) aria-label
        "Otvori meni",
        # SR/EN language-switcher labels (both switchers reuse the same strings)
        "SR",
        "EN",
        # footer copyright
        "Velegrad Estate © 2026",
        # footer nav section titles
        "Stranice",
        "Više",
        # logo aria-label
        "Velegrad Estate",
    ]
    unwrapped = [label for label in mandatory if not _trans_wrapped(src, label)]
    assert not unwrapped, (
        f"these LOCKED mandatory UI strings are not {{% trans %}}-wrapped in "
        f"base.html: {unwrapped} (AC3)."
    )


def test_404_full_mandatory_trans_set_is_wrapped():
    # AC3/AC5 (locked, broadened): both 404 CTA labels must be {% trans %}-wrapped
    # in the SOURCE (complements the bare-anchor-text negative check above).
    src = _read_template("404.html")
    assert src, "templates/404.html must exist (AC3/AC5)."
    unwrapped = [
        cta for cta in ("Vratite se na početnu", "Kontaktirajte nas")
        if not _trans_wrapped(src, cta)
    ]
    assert not unwrapped, (
        f"these 404 CTA labels are not {{% trans %}}-wrapped in 404.html: "
        f"{unwrapped} (AC3/AC5)."
    )


# =========================================================================== #
# AC2 — Google Fonts, <html lang> + charset, head override blocks             #
# =========================================================================== #
@pytest.mark.django_db
def test_base_includes_google_fonts_preconnect_and_link(client):
    # AC2: the head must wire Google Fonts — the preconnect hints plus the
    # Bodoni Moda / DM Sans stylesheet link (faithful to the design head).
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "fonts.googleapis.com" in html and "fonts.gstatic.com" in html, (
        "base.html head must include the Google Fonts preconnect hints (AC2)."
    )
    assert "rel=\"preconnect\"" in html, (
        "base.html must include rel=\"preconnect\" hints for Google Fonts (AC2)."
    )
    assert "Bodoni+Moda" in html and "DM+Sans" in html, (
        "base.html must link the Bodoni Moda + DM Sans Google Fonts stylesheet (AC2)."
    )


@pytest.mark.django_db
def test_base_has_html_lang_sr_and_charset(client):
    # AC2/AC4: rendered base.html declares <html lang="sr"...> (sr default) and a
    # <meta charset=...>.
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'lang="sr"' in html, (
        "base.html must render <html lang=\"sr\"...> (sr default) (AC2)."
    )
    import re
    assert re.search(r"<meta\s+charset=", html), (
        "base.html must render a <meta charset=...> tag (AC2)."
    )


def test_base_defines_overridable_head_and_js_blocks():
    # AC2: base.html defines the override-able head blocks (og, schema, ga4) and
    # extra_js — a child overriding {% block og %} / {% block extra_js %} changes
    # the output. Complements test_child_template_overriding_title_block_changes_title.
    from django.template import engines

    src = _read_template("base.html")
    assert src, "templates/base.html must exist (AC2)."
    for block in ("og", "schema", "ga4", "extra_js"):
        assert (
            "{% block " + block + " %}" in src
        ), f"base.html must define an override-able {{% block {block} %}} (AC2)."

    og_marker = "ZZ_OG_OVERRIDE_2_1_ZZ"
    js_marker = "ZZ_EXTRA_JS_OVERRIDE_2_1_ZZ"
    child_src = (
        "{% extends 'base.html' %}"
        "{% block content %}x{% endblock %}"
        "{% block og %}" + og_marker + "{% endblock %}"
        "{% block extra_js %}" + js_marker + "{% endblock %}"
    )
    rendered = engines["django"].from_string(child_src).render({})
    assert og_marker in rendered, (
        "overriding {% block og %} must change base.html output (AC2)."
    )
    assert js_marker in rendered, (
        "overriding {% block extra_js %} must change base.html output (AC2)."
    )


# =========================================================================== #
# AC1/AC2 — no global pages CSS at all; two lang-switchers (header + footer)   #
# =========================================================================== #
@pytest.mark.django_db
def test_home_does_not_include_any_pages_css_globally(client):
    # Story 2.2 (AC7) moved the page-CSS boundary: home.html now loads its own
    # css/pages/home.css per-page via {% block extra_css %} (NOT in base). The
    # original 2.1 assertion ("no css/pages/* at all") is narrowed: home loads
    # ONLY its own home.css; no OTHER pages/*.css must leak into the render, and
    # base must still not pull page CSS globally for non-home pages.
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    import re
    # Every css/pages/* reference on the home render must be home.css.
    pages_css = re.findall(r"css/pages/([^\"'\s]+\.css)", html)
    assert pages_css, "home must load its own per-page CSS (css/pages/home.css) (AC7)."
    assert all(name == "home.css" for name in pages_css), (
        "the only per-page CSS allowed on the home render is css/pages/home.css; "
        f"found other pages/*.css: {sorted(set(pages_css))} (2.2 AC7 boundary)."
    )


@pytest.mark.django_db
def test_two_lang_switchers_present(client):
    # AC2: there are TWO lang-switcher occurrences — the header one (with
    # hide-mobile) and the footer one — not just a single switcher.
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    # Count the two distinct switcher CONTAINER openings (the __btn/__sep children
    # also begin with "lang-switcher", so anchor on the exact container classes):
    # header = class="lang-switcher hide-mobile", footer = class="lang-switcher".
    header_switchers = html.count('class="lang-switcher hide-mobile"')
    footer_switchers = html.count('class="lang-switcher"')
    assert header_switchers == 1, (
        "exactly one (header) lang-switcher must carry hide-mobile (AC2/AC4); "
        f"found {header_switchers}."
    )
    assert footer_switchers == 1, (
        "exactly one (footer) lang-switcher (without hide-mobile) must be present "
        f"(AC2); found {footer_switchers}."
    )
    assert header_switchers + footer_switchers == 2, (
        "base.html must render exactly TWO lang-switchers (header.hide-mobile + footer)."
    )
