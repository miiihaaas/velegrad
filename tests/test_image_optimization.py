"""
RED-phase contract tests for Story 6.3 — "Performanse i optimizacija slika"
(WebP + responsive srcset via django-imagekit, keširano; lazy-load ispod fold-a;
storage-agnostic varijante kroz django-storages, S3-ready).

These tests define the CONTRACT for the image-optimization layer laid OVER the
existing <img> patterns (home/properties/property-detail/about). They are written
BEFORE the feature is built, so EVERY new BEHAVIORAL 6.3 test in this module MUST
FAIL/ERROR until the Dev implements:

  * config/settings/base.py — "imagekit" in INSTALLED_APPS;
    IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY = "imagekit.cachefiles.strategies.Optimistic"
    (MANDATORY-for-correctness — JustInTime 500s on byteless .url); a STORAGES dict
    whose "default" BACKEND is chosen by STORAGE_BACKEND via a pure helper.
  * core/storages.py — a PURE helper mapping "local" -> FileSystemStorage backend
    string, "s3" -> storages.backends.s3.S3Storage backend string (the CANONICAL
    AC4 verification — override_settings can NOT re-run module-level base.py).
  * properties/ + core/ — ImageSpecField / registered ImageSpec (WEBP, >=2 widths)
    for Property.hero_image / PropertyImage.image / SiteSettings.hero_image /
    founder_photo, rendered via spec .url (string-safe under Optimistic).
  * templates/{home,properties,property-detail,about}.html — media <img> ->
    <picture><source type="image/webp" srcset="... NNNw, ... NNNw"><img alt loading>;
    above-fold hero OMITS loading (eager); below-fold lazy; sizes on detail-hero.

Locked rules (mirror the 3.2 / 6.2 harness — see the story's LOCKED decisions):
  * BYTELESS markup-only strategy: seed images as STRING paths
    (hero_image="properties/hero/x.jpg"); NO real bytes. Under the MANDATORY
    Optimistic strategy spec .url is a pure string op (source.name + spec hash) so
    the variant URL renders into markup WITHOUT opening the source — assert MARKUP
    (<picture>, <source type="image/webp">, srcset NNNw widths, sizes, loading) and
    SETTINGS, NOT generated WebP bytes. Do NOT use {% generateimage %}/{% thumbnail %}
    forms that touch .width/.height (they 500 even under Optimistic).
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE=config.settings.test, in-memory SQLite).
  * Property is seeded via .objects.create(...) — full_clean() is NEVER called
    (SQLite skips it). The home property-card seed MUST be is_featured=True,
    is_active=True, collection_type="signature" + non-empty hero_image (HomeView
    renders ONLY those, up to 4 — pages/views.py l.31-33), else no card renders and
    the assertion is vacuous.
  * The seed helpers below are COPY-ADAPTED from tests/test_property_detail.py +
    tests/test_static_pages.py (private underscore helpers are NOT cross-imported).
  * conftest.py autouse _reset_active_language keeps the language state clean.
  * 6.2 SEO (og:image full hero_image.url -> "x.jpg") and 3.2 gallery (data-full =
    full image url) are NOT broken; <img> keeps alt.
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    6-3-performanse-i-optimizacija-slika-interface-contract.md
"""
import importlib
import io
import re

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings


# --------------------------------------------------------------------------- #
# Model / seed helpers — COPY-ADAPTED from test_property_detail / test_static_pages
# (the story forbids cross-importing the private underscore helpers).         #
# --------------------------------------------------------------------------- #
def _get_model(app_label, class_name):
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


# A populated hero seed path (mirrors the 6.2 SEO test's "properties/hero/x.jpg").
HERO_PATH = "properties/hero/x.jpg"
GALLERY_PATH = "properties/gallery/thumb-0.jpg"
FOUNDER_PATH = "site/founder.jpg"
FOUNDER_NAME = "Đorđije Potpara"


def _make_property(**overrides):
    """Create a Property with all required non-null scalar fields supplied.

    Seeds hero_image as a STRING path (no real bytes) by default; .create() skips
    full_clean() on SQLite. For the home property-card assertion the caller MUST
    pass is_featured=True (collection_type="signature"/is_active=True are defaults)
    so HomeView (is_featured + is_active + signature, [:4]) renders the card.
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
        hero_image=HERO_PATH,
        is_featured=False,
        is_active=True,
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


def _add_images(prop, count=2):
    """Attach ``count`` PropertyImage rows with DISTINCT image URLs (string paths,
    no bytes). DISTINCT URLs matter: gallery.js dedups by URL.
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


def _seed_site_settings(**overrides):
    """Load the SiteSettings singleton and populate founder/contact + photos."""
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.founder_name = FOUNDER_NAME
    obj.founder_title_sr = "Privatni savetnik"
    obj.phone_primary = "+381119988776"
    obj.whatsapp_number = "381119988776"
    obj.email_primary = "kontakt@velegradestate.test"
    obj.hero_image = ""
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _seed_page(slug, title_sr, content_sr="<p>Sadrzaj</p>", **overrides):
    """Create-or-update a Page (title_sr + content_sr required; *_en blank=True).

    Uses update_or_create (NOT create) because 0002_seed_static_pages already
    seeds Page(slug='about'/'international') into the test DB at migration time —
    a plain create() would raise IntegrityError on the unique slug.
    """
    Page = _get_model("pages", "Page")
    defaults = dict(
        title_sr=title_sr,
        title_en="",
        content_sr=content_sr,
        content_en="",
        is_active=True,
    )
    defaults.update(overrides)
    obj, _ = Page.objects.update_or_create(slug=slug, defaults=defaults)
    return obj


def _detail_path(slug):
    return f"/properties/{slug}/"


def _region_after(html, marker, length=900, end=None):
    """Return the HTML window starting at ``marker`` (or "" if not present).

    When ``end`` is given, the window is truncated at the FIRST occurrence of the
    ``end`` marker after ``marker`` (still capped by ``length``). This keeps a
    region-scoped assertion (e.g. the above-fold hero) from spilling into the NEXT
    region (e.g. the below-fold thumbnail-strip / advisor portrait, which ARE
    lazy-loaded) — without an ``end`` bound a fixed-length window over the SHORT
    hero markup would catch the next region's loading="lazy" and falsely fail a
    correct implementation (the hero regions sit only ~220-590 chars before the
    next, lazy, region in the rendered HTML).
    """
    idx = html.find(marker)
    if idx == -1:
        return ""
    window = html[idx:idx + length]
    if end is not None:
        cut = window.find(end, len(marker))
        if cut != -1:
            window = window[:cut]
    return window


# ``NNNw`` srcset width descriptors (e.g. "480w", "960w", "1440w").
_SRCSET_W = re.compile(r"\b\d{2,4}w\b")


def _count_srcset_widths(fragment):
    return len(set(_SRCSET_W.findall(fragment)))


# =========================================================================== #
# AC1 — WebP variants + responsive srcset via django-imagekit, cached          #
# =========================================================================== #
def test_imagekit_in_installed_apps():
    # AC1: the imagekit app (label "imagekit", package django-imagekit already in
    # base.txt) must be wired into INSTALLED_APPS.
    assert "imagekit" in settings.INSTALLED_APPS, (
        "'imagekit' must be in settings.INSTALLED_APPS (AC1) — django-imagekit is "
        "already in requirements/base.txt; 6.3 activates it."
    )


def test_imagekit_cachefile_strategy_is_optimistic():
    # AC1 (MANDATORY-for-correctness): the cachefile strategy must be Optimistic,
    # NOT the imagekit default JustInTime. Under JustInTime a registered spec's
    # .url OPENS the source -> 500 on byteless seed; Optimistic makes .url an
    # I/O-free string op (empirically confirmed, imagekit 6.1.0).
    assert getattr(settings, "IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY", None) == (
        "imagekit.cachefiles.strategies.Optimistic"
    ), (
        "IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY must be "
        "'imagekit.cachefiles.strategies.Optimistic' (NOT the JustInTime default) "
        "so registered-spec .url is I/O-free on byteless seed/dev (AC1)."
    )


@pytest.mark.django_db
def test_detail_hero_has_picture_webp_source_with_srcset(client):
    # AC1: GET /properties/<slug>/ with a populated hero_image -> the detail-hero
    # region contains <picture> + <source type="image/webp"> + a srcset with >=2
    # NNNw width descriptors.
    _seed_site_settings()
    prop = _make_property(hero_image=HERO_PATH)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200, (
        f"GET {_detail_path(prop.slug)} must return 200 (no 500 from byteless "
        f".url under Optimistic), got {resp.status_code} (AC1)."
    )
    html = resp.content.decode("utf-8")
    # Scope to the detail-hero region ONLY (stop at the thumbnail-strip, which is a
    # SEPARATE below-fold region) so a hero <picture>/srcset assertion is not
    # satisfied by the thumbnail markup instead.
    hero = _region_after(html, 'class="detail-hero"', length=1400,
                         end="thumbnail-strip")
    assert "<picture" in hero, (
        "the detail-hero must render a <picture> element for a populated hero_image (AC1)."
    )
    assert 'type="image/webp"' in hero, (
        "the detail-hero <picture> must contain a <source type=\"image/webp\"> (AC1)."
    )
    assert "srcset" in hero, "the detail-hero WebP <source> must carry a srcset (AC1)."
    assert _count_srcset_widths(hero) >= 2, (
        "the detail-hero srcset must declare at least TWO NNNw width descriptors "
        f"(responsive), found {_count_srcset_widths(hero)} (AC1)."
    )


@pytest.mark.django_db
def test_home_property_card_has_picture_webp_source(client):
    # AC1: GET / with a is_featured=True/is_active=True/signature Property having a
    # populated hero_image -> the property-card renders <picture>/<source
    # type="image/webp">. (HomeView renders ONLY featured+active+signature, [:4];
    # without is_featured the card never renders and the assertion is vacuous.)
    _seed_site_settings()
    _make_property(
        title="Featured Signature",
        hero_image=HERO_PATH,
        is_featured=True,
        is_active=True,
        collection_type="signature",
    )
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / must return 200, got {resp.status_code} (AC1)."
    )
    html = resp.content.decode("utf-8")
    card = _region_after(html, "property-card__image", length=900)
    assert card, "a featured property-card must render on the home page (AC1)."
    assert "<picture" in card, (
        "the home property-card must render a <picture> for a populated hero_image (AC1)."
    )
    assert 'type="image/webp"' in card, (
        "the home property-card <picture> must contain a <source type=\"image/webp\"> (AC1)."
    )


@pytest.mark.django_db
def test_detail_empty_hero_renders_svg_placeholder_no_500(client):
    # AC1 (placeholder branch, edge-case): hero_image="" -> the existing {% static %}
    # SVG placeholder renders (NO imagekit call, NO WebP <source>, NO 500).
    _seed_site_settings()
    prop = _make_property(hero_image="")
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200, (
        "an empty hero_image must NOT 500 (placeholder branch, imagekit NOT called) "
        f"(AC1), got {resp.status_code}."
    )
    html = resp.content.decode("utf-8")
    hero = _region_after(html, 'class="detail-hero"', length=1400,
                         end="thumbnail-strip")
    assert ".svg" in hero, (
        "an empty hero_image must fall back to the static SVG placeholder in the "
        "detail-hero (AC1)."
    )
    assert 'type="image/webp"' not in hero, (
        "an empty hero_image must NOT emit a WebP <source> — SVG is a vector, "
        "imagekit must not be invoked on the empty branch (AC1)."
    )


@pytest.mark.django_db
def test_properties_listing_card_has_picture_webp_source_and_lazy(client):
    # AC1+AC2 (T1): GET /properties/ with an active Property having a populated
    # hero_image -> the listing card renders <picture> + <source type="image/webp">
    # AND the card image is lazy-loaded (below fold). The listing was previously
    # untested (only home + detail covered).
    _seed_site_settings()
    _make_property(
        title="Listing Card",
        hero_image=HERO_PATH,
        is_active=True,
    )
    resp = client.get("/properties/")
    assert resp.status_code == 200, (
        f"GET /properties/ must return 200, got {resp.status_code} (AC1)."
    )
    html = resp.content.decode("utf-8")
    card = _region_after(html, "property-card__image", length=900)
    assert card, "an active property listing card must render on /properties/ (AC1)."
    assert "<picture" in card, (
        "the properties listing card must render a <picture> for a populated "
        "hero_image (AC1)."
    )
    assert 'type="image/webp"' in card, (
        "the properties listing card <picture> must contain a "
        '<source type="image/webp"> (AC1).'
    )
    assert 'loading="lazy"' in card, (
        "the properties listing card image must carry loading=\"lazy\" "
        "(below fold) (AC2)."
    )


@pytest.mark.django_db
def test_about_empty_founder_photo_renders_placeholder_no_500(client):
    # AC1 (placeholder branch, T2): SiteSettings.founder_photo="" -> GET /about/
    # returns 200, the portrait region emits NO WebP <source>, and the placeholder
    # <img> still carries loading="lazy" (below fold). Mirrors the detail empty-hero
    # placeholder pattern.
    _seed_site_settings(founder_photo="")
    _seed_page("about", "O nama")
    resp = client.get("/about/")
    assert resp.status_code == 200, (
        "an empty founder_photo must NOT 500 on /about/ (placeholder branch, "
        f"imagekit NOT called) (AC1), got {resp.status_code}."
    )
    html = resp.content.decode("utf-8")
    portrait = _region_after(html, "about-portrait", length=700)
    assert portrait, "the about-portrait region must render (AC1)."
    assert 'type="image/webp"' not in portrait, (
        "an empty founder_photo must NOT emit a WebP <source> — the SVG placeholder "
        "is a vector, imagekit must not be invoked on the empty branch (AC1)."
    )
    assert 'loading="lazy"' in portrait, (
        "the about placeholder portrait <img> must still carry loading=\"lazy\" "
        "(below fold / non-LCP) (AC2)."
    )


@pytest.mark.django_db
def test_about_founder_portrait_has_picture_webp_source_with_srcset(client):
    # AC1 (T3): SiteSettings.founder_photo set to a non-empty string path ->
    # GET /about/ -> the portrait region has <picture> + <source type="image/webp">
    # + srcset with >=2 widths. about.html uses INLINE <picture> markup (it needs
    # width/height for CLS), so this guards that inline markup directly.
    _seed_site_settings(founder_photo=FOUNDER_PATH)
    _seed_page("about", "O nama")
    resp = client.get("/about/")
    assert resp.status_code == 200, (
        f"GET /about/ must return 200, got {resp.status_code} (AC1)."
    )
    html = resp.content.decode("utf-8")
    portrait = _region_after(html, "about-portrait", length=900)
    assert portrait, "the about-portrait region must render (AC1)."
    assert "<picture" in portrait, (
        "the about founder portrait must render a <picture> for a populated "
        "founder_photo (AC1)."
    )
    assert 'type="image/webp"' in portrait, (
        "the about founder portrait <picture> must contain a "
        '<source type="image/webp"> (AC1).'
    )
    assert "srcset" in portrait, (
        "the about founder portrait WebP <source> must carry a srcset (AC1)."
    )
    assert _count_srcset_widths(portrait) >= 2, (
        "the about founder portrait srcset must declare at least TWO NNNw width "
        f"descriptors (responsive), found {_count_srcset_widths(portrait)} (AC1)."
    )


@pytest.mark.django_db
def test_home_empty_hero_card_no_500_uses_placeholder(client):
    # AC1 (edge-case): a featured signature property with hero_image="" still
    # renders the home page (placeholder branch, no imagekit call, no 500).
    _seed_site_settings()
    _make_property(
        title="Featured Bez Slike",
        hero_image="",
        is_featured=True,
        is_active=True,
        collection_type="signature",
    )
    resp = client.get("/")
    assert resp.status_code == 200, (
        "GET / with a featured property whose hero_image='' must NOT 500 "
        f"(placeholder branch), got {resp.status_code} (AC1)."
    )


# =========================================================================== #
# AC2 — Lazy-load below the fold; eager (no loading) above the fold            #
# =========================================================================== #
@pytest.mark.django_db
def test_home_property_card_img_is_lazy(client):
    # AC2: the home property-card <img> (below fold) carries loading="lazy".
    _seed_site_settings()
    _make_property(
        title="Featured Lazy",
        hero_image=HERO_PATH,
        is_featured=True,
        is_active=True,
        collection_type="signature",
    )
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    card = _region_after(html, "property-card__image", length=900)
    assert card, "a featured property-card must render (AC2)."
    assert 'loading="lazy"' in card, (
        "the home property-card image must carry loading=\"lazy\" (below fold) (AC2)."
    )


@pytest.mark.django_db
def test_home_hero_is_not_lazy(client):
    # AC2: the home hero (above fold / LCP) must NOT carry loading="lazy" (eager
    # default — atribut izostavljen) so the largest paint is not deferred.
    _seed_site_settings(hero_image=HERO_PATH)
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    # Scope to the hero region ONLY (stop at the advisor block, whose founder
    # portrait IS below-fold/lazy) — the rendered advisor portrait sits only ~590
    # chars after hero__bg, so an unbounded 700-char window would catch the
    # advisor's loading="lazy" and falsely fail a CORRECT implementation.
    hero = _region_after(html, 'class="hero__bg"', length=900, end="advisor")
    assert hero, "the home hero region must render (AC2)."
    assert "<img" in hero, "the home hero region must contain the hero <img> (AC2)."
    assert 'loading="lazy"' not in hero, (
        "the home hero (above fold / LCP) must NOT be lazy-loaded (LCP regression) (AC2)."
    )


@pytest.mark.django_db
def test_detail_thumbnails_are_lazy(client):
    # AC2: the property-detail thumbnail-strip images (below fold) carry
    # loading="lazy".
    _seed_site_settings()
    prop = _make_property(hero_image=HERO_PATH)
    _add_images(prop, count=2)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    strip = _region_after(html, "thumbnail-strip", length=1400)
    assert strip, "the thumbnail-strip must render with 2 images (AC2)."
    assert 'loading="lazy"' in strip, (
        "the thumbnail-strip images must carry loading=\"lazy\" (below fold) (AC2)."
    )


@pytest.mark.django_db
def test_detail_hero_is_not_lazy(client):
    # AC2: the detail-hero (above fold) must NOT carry loading="lazy".
    _seed_site_settings()
    prop = _make_property(hero_image=HERO_PATH)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    # Scope to the hero region BEFORE the thumbnail-strip (which IS lazy) — the
    # strip starts only ~220 chars after class="detail-hero" in the rendered HTML,
    # so an unbounded window would catch the thumbnails' loading="lazy" and falsely
    # fail a CORRECT implementation (hero eager + thumbnails lazy).
    hero = _region_after(html, 'class="detail-hero"', length=1400,
                         end="thumbnail-strip")
    assert hero, "the detail-hero must render (AC2)."
    assert 'loading="lazy"' not in hero, (
        "the detail-hero (above fold) must NOT be lazy-loaded (LCP regression) (AC2)."
    )


@pytest.mark.django_db
def test_about_founder_portrait_is_lazy(client):
    # AC2: GET /about/ founder portrait (below fold / non-LCP) carries
    # loading="lazy". Requires a Page(slug="about") + a populated founder_photo.
    _seed_site_settings(founder_photo=FOUNDER_PATH)
    _seed_page("about", "O nama")
    resp = client.get("/about/")
    assert resp.status_code == 200, (
        f"GET /about/ must return 200, got {resp.status_code} (AC2)."
    )
    html = resp.content.decode("utf-8")
    portrait = _region_after(html, "about-portrait", length=700)
    assert portrait, "the about-portrait must render (AC2)."
    assert 'loading="lazy"' in portrait, (
        "the about founder portrait must carry loading=\"lazy\" (below fold / "
        "non-LCP) (AC2)."
    )


@pytest.mark.django_db
def test_detail_agent_avatar_img_is_lazy(client):
    # AC2 (T4): the property-detail agent-block avatar (below-fold founder photo,
    # line ~223) is a plain <img>; it must carry loading="lazy". This block is well
    # below the fold so the avatar must not eagerly load. (The avatar stays a plain
    # <img>, NOT a <picture>/WebP source — converting it was deferred as low-value;
    # so we assert lazy only.)
    _seed_site_settings(founder_photo=FOUNDER_PATH)
    prop = _make_property(hero_image=HERO_PATH)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200, (
        f"GET {_detail_path(prop.slug)} must return 200, got {resp.status_code} (AC2)."
    )
    html = resp.content.decode("utf-8")
    avatar = _region_after(html, "agent-block__avatar", length=300)
    assert avatar, "the agent-block avatar region must render (AC2)."
    assert "<img" in avatar, (
        "the agent-block avatar must render an <img> for a populated founder_photo (AC2)."
    )
    assert 'loading="lazy"' in avatar, (
        "the property-detail agent-block avatar <img> must carry loading=\"lazy\" "
        "(below fold) (AC2)."
    )


# =========================================================================== #
# AC3 — Fast load PROXY (NOT timing): WebP + >=2 widths + sizes + below-fold lazy
# =========================================================================== #
@pytest.mark.django_db
def test_detail_hero_picture_has_two_widths_and_sizes(client):
    # AC3 (standalone proxy, NOT timing): the detail-hero <picture> has a WebP
    # <source> with >=2 srcset widths AND a `sizes` attribute, so a mobile client
    # picks a SMALLER variant (not the largest / full original).
    _seed_site_settings()
    prop = _make_property(hero_image=HERO_PATH)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    hero = _region_after(html, 'class="detail-hero"', length=1400,
                         end="thumbnail-strip")
    assert "<picture" in hero and 'type="image/webp"' in hero, (
        "the detail-hero must serve WebP via <picture><source type=\"image/webp\"> (AC3)."
    )
    assert _count_srcset_widths(hero) >= 2, (
        "the detail-hero must offer >=2 srcset widths so the mobile client does NOT "
        "fetch a single full-size original (AC3 proxy — properly size images)."
    )
    assert "sizes=" in hero, (
        "the detail-hero <picture>/<img> must carry a `sizes` attribute so the "
        "browser selects a smaller variant on mobile (AC3 standalone)."
    )


@pytest.mark.django_db
def test_home_card_serves_webp_and_lazy_together(client):
    # AC3 (grouped perf-evidence): the home property-card image both serves WebP
    # (<source type="image/webp">) AND is lazy-loaded (below fold) — together they
    # cut the initial payload (proxy for "fast load on mobile").
    _seed_site_settings()
    _make_property(
        title="Featured Perf",
        hero_image=HERO_PATH,
        is_featured=True,
        is_active=True,
        collection_type="signature",
    )
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    card = _region_after(html, "property-card__image", length=900)
    assert 'type="image/webp"' in card, (
        "the home property-card must serve a WebP <source> (smaller payload) (AC3)."
    )
    assert 'loading="lazy"' in card, (
        "the home property-card must be lazy-loaded (defer offscreen images) (AC3)."
    )


# =========================================================================== #
# AC4 — Variants flow through the same django-storages backend (S3-ready)      #
# =========================================================================== #
def _storage_helper():
    """Return the first available pure storage-backend-choice helper from
    core.storages, or None if the module/helper does not exist yet (RED phase).
    """
    try:
        mod = importlib.import_module("core.storages")
    except ImportError:
        return None
    for name in (
        "default_storage_backend",
        "storage_backend_for",
        "resolve_storage_backend",
        "get_default_storage_backend",
        "storage_backend",
    ):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    return None


def test_storage_helper_local_returns_filesystemstorage_string():
    # AC4 (CANONICAL pure-helper unit test): core/storages.py exposes a pure
    # function mapping "local" -> the FileSystemStorage BACKEND string. This is the
    # canonical AC4 path (override_settings can NOT re-run module-level base.py, so
    # the choice MUST live in a directly-testable pure function).
    fn = _storage_helper()
    assert fn is not None, (
        "core/storages.py must expose a pure storage-backend-choice helper "
        "(e.g. default_storage_backend(name)) — the CANONICAL AC4 verification (AC4)."
    )
    result = fn("local")
    assert result == "django.core.files.storage.FileSystemStorage", (
        f"the helper must map 'local' -> 'django.core.files.storage."
        f"FileSystemStorage', got {result!r} (AC4)."
    )


def test_storage_helper_s3_returns_s3storage_string():
    # AC4 (CANONICAL pure-helper unit test): "s3" -> the django-storages S3 BACKEND
    # string. (boto3 stays commented; this only verifies the storage-agnostic PATH.)
    fn = _storage_helper()
    assert fn is not None, (
        "core/storages.py must expose a pure storage-backend-choice helper (AC4)."
    )
    result = fn("s3")
    assert result == "storages.backends.s3.S3Storage", (
        f"the helper must map 's3' -> 'storages.backends.s3.S3Storage', got "
        f"{result!r} (AC4)."
    )


def test_storages_setting_default_resolves_filesystem_under_local():
    # AC4: settings.STORAGES["default"]["BACKEND"] exists and, under the default
    # env (STORAGE_BACKEND="local"), resolves to FileSystemStorage — NOT a
    # hardcoded S3 backend.
    storages = getattr(settings, "STORAGES", None)
    assert isinstance(storages, dict), (
        "settings.STORAGES must be a dict wiring storage-agnostic backends (AC4)."
    )
    assert "default" in storages and "BACKEND" in storages["default"], (
        "settings.STORAGES['default']['BACKEND'] must exist (AC4)."
    )
    backend = storages["default"]["BACKEND"]
    assert backend == "django.core.files.storage.FileSystemStorage", (
        f"under the default env (STORAGE_BACKEND='local') STORAGES['default'] must "
        f"resolve to FileSystemStorage (NOT hardcoded S3), got {backend!r} (AC4)."
    )


def test_storages_setting_has_staticfiles_key():
    # AC4: STORAGES also wires a "staticfiles" backend (static is NOT media; it
    # stays FS/whitenoise, not S3).
    storages = getattr(settings, "STORAGES", None)
    assert isinstance(storages, dict) and "staticfiles" in storages, (
        "settings.STORAGES must keep a 'staticfiles' backend (static is not media) (AC4)."
    )


def test_imagekit_file_storage_not_hardcoded_filesystem():
    # AC4: ImageKit cachefile storage must NOT be hardcoded to FileSystemStorage —
    # IMAGEKIT_DEFAULT_FILE_STORAGE is either unset or == "default" so variants
    # follow originals to S3 when 6.4 flips STORAGE_BACKEND.
    value = getattr(settings, "IMAGEKIT_DEFAULT_FILE_STORAGE", None)
    assert value in (None, "default"), (
        "IMAGEKIT_DEFAULT_FILE_STORAGE must be unset or 'default' (storage-agnostic) "
        f"— NOT a hardcoded FileSystemStorage; got {value!r} (AC4)."
    )


def test_storage_backend_default_is_local():
    # AC4 (S3 deferred): STORAGE_BACKEND default stays "local" (S3 activation =
    # Story 6.4). The default env (no override) must yield local.
    backend = getattr(settings, "STORAGE_BACKEND", None)
    # STORAGE_BACKEND may not be exported as a settings attribute; if it is, it
    # must be "local". The storage helper round-trip already proves the mapping.
    if backend is not None:
        assert backend == "local", (
            f"STORAGE_BACKEND default must be 'local' (S3 deferred to 6.4), got "
            f"{backend!r} (AC4)."
        )


# =========================================================================== #
# Regression guards — MEDIA_URL leading slash, SR/EN smoke, 6.2 boundary       #
# =========================================================================== #
@pytest.mark.django_db
def test_variant_srcset_url_has_leading_slash(client):
    # Regression (MEDIA_URL leading-slash, SM-A#5): MEDIA_URL is "media/" (relative).
    # 6.3 is the first story to render .url en masse in srcset/variants — every
    # variant/srcset URL must start with "/media/" (or at least "/"). If the impl
    # must set MEDIA_URL="/media/" that is the expected scoped fix.
    _seed_site_settings()
    prop = _make_property(hero_image=HERO_PATH)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    hero = _region_after(html, 'class="detail-hero"', length=1400,
                         end="thumbnail-strip")
    # Pull the srcset value and inspect its first URL token.
    m = re.search(r'srcset="([^"]+)"', hero)
    assert m, "the detail-hero WebP <source> must carry a srcset to inspect (regression)."
    first_url = m.group(1).strip().split()[0]
    assert first_url.startswith("/"), (
        f"the rendered variant/srcset URL must start with '/' (leading slash; "
        f"ideally '/media/') — got {first_url!r}. Fix: MEDIA_URL='/media/' (regression)."
    )


@pytest.mark.django_db
def test_home_sr_and_en_both_return_200(client):
    # Regression (6.1 i18n smoke): GET / (SR, no prefix) and GET /en/ both 200
    # after the image-optimization layer is added.
    _seed_site_settings(hero_image=HERO_PATH)
    _make_property(
        title="Smoke Featured",
        hero_image=HERO_PATH,
        is_featured=True,
        is_active=True,
        collection_type="signature",
    )
    resp_sr = client.get("/")
    resp_en = client.get("/en/")
    assert resp_sr.status_code == 200, (
        f"GET / (SR) must return 200, got {resp_sr.status_code} (regression)."
    )
    assert resp_en.status_code == 200, (
        f"GET /en/ must return 200, got {resp_en.status_code} (regression)."
    )


@pytest.mark.django_db
def test_detail_og_image_still_contains_source_filename(client):
    # Regression (6.2 boundary lock): og:image must stay the FULL hero_image.url and
    # still contain the source filename ("x.jpg") — a WebP variant URL would break
    # tests/test_seo.py. (We assert the 6.2 boundary holds; we do NOT duplicate the
    # absolute-URL assertion already owned by test_seo.)
    _seed_site_settings()
    prop = _make_property(hero_image=HERO_PATH)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    assert m, "the property-detail page must render an og:image meta tag (6.2)."
    assert "x.jpg" in m.group(1), (
        "og:image must remain the FULL hero_image.url containing the source "
        f"filename 'x.jpg' (6.2 LOCKED — NOT a WebP variant), got {m.group(1)!r}."
    )


@pytest.mark.django_db
def test_detail_thumbnail_data_full_is_full_image_url(client):
    # Regression (3.2 gallery lock): each thumbnail keeps data-full = the FULL
    # image url (gallery.js lightbox/dedup). A variant URL here would break the
    # lightbox. The thumbnail <img> may be variantized for DISPLAY, but data-full
    # must still reference the original gallery file.
    _seed_site_settings()
    prop = _make_property(hero_image=HERO_PATH)
    _add_images(prop, count=2)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "data-full" in html, "thumbnails must keep a data-full attribute (3.2)."
    assert "photo-0.jpg" in html and "photo-1.jpg" in html, (
        "thumbnail data-full must reference the FULL gallery image urls "
        "(photo-0.jpg / photo-1.jpg) — gallery.js lightbox/dedup (3.2)."
    )


@pytest.mark.django_db
def test_detail_hero_img_keeps_alt(client):
    # Regression (a11y / base_layout + home_page lock): the <picture><img> must keep
    # its alt attribute (existing tests assert alt presence).
    _seed_site_settings()
    prop = _make_property(title="Alt Test", hero_image=HERO_PATH)
    resp = client.get(_detail_path(prop.slug))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    hero = _region_after(html, 'class="detail-hero"', length=1400,
                         end="thumbnail-strip")
    assert "<img" in hero and "alt=" in hero, (
        "the detail-hero <picture> must retain a fallback <img> with an alt "
        "attribute (a11y regression — <picture><img> keeps alt)."
    )


# =========================================================================== #
# BUG fix lock (Story 6.3) — the WebP pipeline is NOT inert in production      #
# =========================================================================== #
@pytest.mark.django_db
def test_webp_variant_actually_generates_under_simple_backend(tmp_path):
    # AC-1/AC-3: WebP variants ACTUALLY generate (production Simple backend path)
    # — guards against the inert-pipeline regression. The rest of this module uses
    # the markup-only strategy (byteless string-path seeds + the no-op test backend);
    # this is the EXPLICITLY-ALLOWED exception: a tiny REAL in-memory image seeded
    # to a temp MEDIA_ROOT, run under the PRODUCTION-like `Simple` backend, proving
    # the spec actually produces a non-empty WebP byte stream (the bug was that the
    # no-op backend was wired in PRODUCTION, so no path ever wrote a WebP cachefile
    # and every <source srcset> 404'd → silent JPEG/PNG fallback → NFR-1 inert).
    Property = _get_model("properties", "Property")

    # Build a tiny real JPEG in-memory (8x8 red) — REAL bytes, NOT a byteless seed.
    from PIL import Image  # imported lazily; Pillow is an imagekit dependency.

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, "JPEG")
    buf.seek(0)
    upload = SimpleUploadedFile("real.jpg", buf.getvalue(), content_type="image/jpeg")

    # @override_settings exercises the REAL generation path even though test.py
    # defaults to the no-op DeferredCacheFileBackend. MEDIA_ROOT -> pytest tmp_path
    # so the original + generated WebP cachefile land in a throwaway dir.
    with override_settings(
        IMAGEKIT_DEFAULT_CACHEFILE_BACKEND="imagekit.cachefiles.backends.Simple",
        MEDIA_ROOT=str(tmp_path),
    ):
        prop = _make_property(title="Real Image", hero_image=upload)
        spec = prop.hero_image_webp_480
        # Force generation (Simple writes the cachefile to default_storage on demand).
        spec.generate()

        # PROOF 1: the variant cachefile EXISTS in storage and is non-empty.
        assert spec.storage.exists(spec.name), (
            "the WebP variant cachefile must EXIST in storage after generation "
            "under the production-like Simple backend (inert-pipeline regression)."
        )
        with spec.storage.open(spec.name, "rb") as fh:
            data = fh.read()
        assert len(data) > 0, (
            "the generated WebP variant cachefile must be NON-EMPTY (real byte "
            "stream produced from the source image)."
        )
        # PROOF 2: it is a real WebP (RIFF....WEBP magic) — proves format conversion,
        # not just a copied JPEG.
        assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", (
            "the generated variant must be an actual WebP byte stream "
            f"(RIFF/WEBP magic), got header {data[:12]!r}."
        )
        # PROOF 3: the .url resolves to a string (string-safe under Optimistic).
        assert prop.hero_image_webp_480.url, "the generated variant .url must resolve."


def test_imagekit_cachefile_backend_wiring_locked():
    # AC-1: cachefile backend wiring locked (no-op deferred ONLY in tests).
    # Under the TEST settings the no-op DeferredCacheFileBackend is active so the
    # byteless string-path markup tests above do NOT crash with FileNotFoundError on
    # .save(). PRODUCTION (config/settings/base.py) deliberately does NOT set
    # IMAGEKIT_DEFAULT_CACHEFILE_BACKEND — imagekit falls back to its synchronous
    # `Simple` default, which writes a real WebP cachefile from real upload bytes
    # (proven by test_webp_variant_actually_generates_under_simple_backend). We can
    # not import base.py in isolation to assert its absence here (it has already been
    # overridden by test.py at import time), so the production intent is asserted via
    # that generation-proof test + the base.py comment; THIS test locks the test-only
    # no-op wiring.
    from imagekit.cachefiles.backends import BaseAsync

    from core.imagekit_backends import DeferredCacheFileBackend

    assert settings.IMAGEKIT_DEFAULT_CACHEFILE_BACKEND == (
        "core.imagekit_backends.DeferredCacheFileBackend"
    ), (
        "the TEST settings must wire the no-op DeferredCacheFileBackend so byteless "
        "string-path seeds do not raise FileNotFoundError on .save() (AC-1)."
    )
    assert issubclass(DeferredCacheFileBackend, BaseAsync), (
        "DeferredCacheFileBackend must subclass imagekit's BaseAsync (is_async=True "
        "→ .url/__bool__ skip file-existence checks) (AC-1)."
    )
    # schedule_generation is a no-op: calling it must NOT raise and must return None.
    backend = DeferredCacheFileBackend()
    assert backend.schedule_generation(object()) is None, (
        "DeferredCacheFileBackend.schedule_generation must be a no-op returning None "
        "(test-only deferral; production uses the synchronous Simple backend) (AC-1)."
    )
