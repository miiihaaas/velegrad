"""
RED-phase contract tests for Story 1.3 — "Brendiran admin i dashboard".

These tests define the CONTRACT for the django-unfold branded "Velegrad CMS"
admin shell + dashboard. They are written BEFORE the feature is built, so EVERY
1.3 test in this module MUST FAIL/ERROR until the Dev implements:

  * `"unfold"` in INSTALLED_APPS (above django.contrib.admin) + `UNFOLD`
    settings dict (SITE_TITLE/SITE_HEADER/COLORS/DASHBOARD_CALLBACK);
  * a defensive `core.admin.dashboard_callback(request, context)`;
  * minimal admin registration of `Property` and `Inquiry` (so the quick-action
    `reverse()` routes exist);
  * a `SiteSettings` singleton ModelAdmin (no add when a row exists, no delete,
    changelist → change-view redirect);
  * a dashboard index template override that RENDERS the metric cards, the two
    quick-action links and the latest-inquiries table;
  * a bounded `django-unfold` pin in requirements/base.txt.

Design rules (mirrors the 1.1 / 1.2 harness):
  * DB / client tests are marked @pytest.mark.django_db (pytest-django is active
    via DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * The admin path is computed from settings.ADMIN_URL the SAME way the app does
    (config/urls.py reads settings.ADMIN_URL, already slash-normalized).
  * We DO NOT import unfold types. RED failures are meant to read as
    "feature absent" (missing UNFOLD key / NoReverseMatch / unbranded HTML /
    model not registered), not ImportError noise. Helpers that touch fragile
    state (reverse on maybe-unregistered models) are wrapped so the failure is a
    clean assertion, not a collection-time crash.
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    1-3-brendiran-admin-i-dashboard-interface-contract.md
"""
import re

import pytest
from django.conf import settings
from django.contrib import admin as dj_admin
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.urls import NoReverseMatch, reverse


# --------------------------------------------------------------------------- #
# Path / URL helpers — derive the admin URL the way the app does.              #
# --------------------------------------------------------------------------- #
def _admin_index_path():
    """The mounted admin index path, derived from settings.ADMIN_URL.

    config/urls.py mounts admin at f"{settings.ADMIN_URL}/"; ADMIN_URL is already
    normalized (no surrounding slashes) in base.py. We rebuild the leading-slash
    absolute path so the Django test client can GET it regardless of ADMIN_URL.
    """
    return "/" + settings.ADMIN_URL.strip("/") + "/"


def _admin_login_path():
    """The admin login path under the mounted ADMIN_URL."""
    return _admin_index_path() + "login/"


def _try_reverse(name):
    """reverse(name) or None if the route does not exist yet (RED phase).

    Returning None (instead of raising) lets the calling test assert the
    feature's *absence* as a clean failure rather than erroring in a helper.
    """
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


def _get_model(app_label, class_name):
    import importlib
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


# --------------------------------------------------------------------------- #
# DB seeding helpers (consistent with tests/test_models.py _make_property).    #
# --------------------------------------------------------------------------- #
def _make_property(**overrides):
    """Create a Property with all required non-null scalar fields supplied."""
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
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


def _make_inquiry(**overrides):
    Inquiry = _get_model("inquiries", "Inquiry")
    defaults = dict(
        name="Marko Markovic",
        email="marko@example.com",
        inquiry_type="viewing",
        phone="+381601234567",
        message="Zainteresovan sam za razgledanje.",
        preferred_language="sr",
        status="new",
    )
    defaults.update(overrides)
    return Inquiry.objects.create(**defaults)


def _seed_dashboard_data():
    """3 active + 1 inactive Property (1 of the active is featured);
    2 status='new' + 1 status='closed' Inquiry.

    Yields the canonical metric expectation: active=3, new=2, featured=1.
    """
    _make_property(title="Aktivna 1", is_active=True, is_featured=True)
    _make_property(title="Aktivna 2", is_active=True)
    _make_property(title="Aktivna 3", is_active=True)
    _make_property(title="Neaktivna", is_active=False)
    _make_inquiry(name="Upit Novi 1", status="new")
    _make_inquiry(name="Upit Novi 2", status="new")
    _make_inquiry(name="Upit Zatvoren", status="closed")


def _superuser(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass12345",
    )


# =========================================================================== #
# AC1 — unfold installed & registered BEFORE django.contrib.admin             #
# =========================================================================== #
def test_unfold_in_installed_apps_before_django_admin():
    # AC1: "unfold" must be in INSTALLED_APPS and precede "django.contrib.admin".
    apps = list(settings.INSTALLED_APPS)
    assert "unfold" in apps, "'unfold' must be added to INSTALLED_APPS (AC1)"
    assert "django.contrib.admin" in apps, "django.contrib.admin must remain installed"
    assert apps.index("unfold") < apps.index("django.contrib.admin"), (
        "'unfold' must be listed BEFORE 'django.contrib.admin' in INSTALLED_APPS "
        "(Unfold overrides admin templates and requires this ordering)."
    )


def test_manage_py_check_passes():
    # AC1/AC8: `manage.py check` runs clean (no SystemCheckError) once Unfold +
    # admin registrations are in place.
    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc}")


# =========================================================================== #
# AC11 — django-unfold pinned with a bounded range in requirements/base.txt   #
# =========================================================================== #
def test_requirements_base_pins_unfold_with_bounded_range():
    # AC11: requirements/base.txt must pin django-unfold with BOTH a lower and an
    # upper bound — not a bare "django-unfold".
    from pathlib import Path

    base_txt = Path(settings.BASE_DIR) / "requirements" / "base.txt"
    assert base_txt.exists(), f"{base_txt} must exist"
    lines = [
        ln.strip() for ln in base_txt.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    unfold_lines = [ln for ln in lines if ln.lower().startswith("django-unfold")]
    assert unfold_lines, "requirements/base.txt must list django-unfold"
    spec = unfold_lines[0]
    assert spec.lower() != "django-unfold", (
        "django-unfold must be PINNED, not bare 'django-unfold' (AC11)."
    )
    # A bounded range needs an upper bound (<) AND a lower anchor (>= or ==).
    assert "<" in spec, f"django-unfold pin must have an upper bound, got: {spec!r}"
    assert (">=" in spec) or ("==" in spec), (
        f"django-unfold pin must have a lower bound (>= or ==), got: {spec!r}"
    )


def test_installed_unfold_version_is_within_pinned_range():
    # AC11: the installed django-unfold version must satisfy the declared range.
    from importlib.metadata import version
    from pathlib import Path

    from packaging.requirements import Requirement

    installed = version("django-unfold")
    base_txt = Path(settings.BASE_DIR) / "requirements" / "base.txt"
    lines = [
        ln.strip() for ln in base_txt.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    unfold_lines = [ln for ln in lines if ln.lower().startswith("django-unfold")]
    assert unfold_lines, "requirements/base.txt must list django-unfold"
    req = Requirement(unfold_lines[0])
    # A bare "django-unfold" yields an EMPTY specifier whose .contains() is
    # always True — that is the RED state. AC11 demands an actual bounded pin.
    assert len(req.specifier) > 0, (
        f"django-unfold must carry a version specifier (bounded pin), got bare "
        f"'{unfold_lines[0]}' (AC11)."
    )
    assert req.specifier.contains(installed, prereleases=True), (
        f"installed django-unfold {installed} is OUTSIDE the pinned range "
        f"'{unfold_lines[0]}' (AC11)."
    )


# =========================================================================== #
# AC2 — brand COLORS scale: RGB-channel strings, not hex                       #
# =========================================================================== #
_RGB_CHANNEL_RE = re.compile(r"^\d{1,3} \d{1,3} \d{1,3}$")
_SHADE_KEYS = {"50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"}


def _all_color_values(colors):
    """Flatten every shade string in a COLORS dict (nested scales)."""
    out = []
    for scale in colors.values():
        if isinstance(scale, dict):
            out.extend(str(v) for v in scale.values())
        else:
            out.append(str(scale))
    return out


def test_unfold_settings_dict_exists():
    # AC2/AC3: a UNFOLD settings dict must exist in settings.
    assert hasattr(settings, "UNFOLD"), "settings.UNFOLD dict must be defined (AC2/AC3)"
    assert isinstance(settings.UNFOLD, dict), "settings.UNFOLD must be a dict"


def test_unfold_colors_primary_is_full_shade_scale_of_rgb_channels():
    # AC2: UNFOLD["COLORS"]["primary"] is a 50–950 shade dict whose values are
    # space-separated RGB-channel strings (NOT hex).
    colors = getattr(settings, "UNFOLD", {}).get("COLORS", {})
    primary = colors.get("primary")
    assert isinstance(primary, dict), (
        "UNFOLD['COLORS']['primary'] must be a shade-scale dict (AC2)."
    )
    assert _SHADE_KEYS.issubset(set(primary.keys())), (
        f"primary scale must cover shade keys 50–950, got {sorted(primary.keys())}"
    )
    for key, value in primary.items():
        assert "#" not in str(value), (
            f"COLORS primary['{key}']={value!r} is HEX; Unfold expects RGB-channel "
            f"strings like '74 82 64' (AC2)."
        )
        assert _RGB_CHANNEL_RE.match(str(value)), (
            f"COLORS primary['{key}']={value!r} must be a 'R G B' channel string."
        )


def test_unfold_primary_center_is_deep_olive_rgb_channel():
    # AC2: the brand Deep Olive #4A5240 -> "74 82 64" sits at the center of the
    # primary scale (key "500" and/or "600").
    primary = getattr(settings, "UNFOLD", {}).get("COLORS", {}).get("primary", {})
    center = {primary.get("500"), primary.get("600")}
    assert "74 82 64" in center, (
        "Deep Olive '74 82 64' must be the center (500/600) of COLORS primary "
        f"(AC2); got 500={primary.get('500')!r}, 600={primary.get('600')!r}."
    )


def test_unfold_colors_include_champagne_rgb_channel():
    # AC2: Champagne #C9A96E -> "201 169 110" must appear in the secondary/accent
    # COLORS scale (RGB-channel, not hex).
    colors = getattr(settings, "UNFOLD", {}).get("COLORS", {})
    values = _all_color_values(colors)
    assert "201 169 110" in values, (
        "Champagne '201 169 110' must appear somewhere in UNFOLD['COLORS'] "
        f"(secondary/accent scale) (AC2); got values={values}."
    )


def test_unfold_dashboard_callback_is_dotted_path_to_callable():
    # AC4: UNFOLD["DASHBOARD_CALLBACK"] is a dotted path that imports to a callable.
    callback = getattr(settings, "UNFOLD", {}).get("DASHBOARD_CALLBACK")
    assert isinstance(callback, str) and "." in callback, (
        "UNFOLD['DASHBOARD_CALLBACK'] must be a dotted import path string (AC4)."
    )
    from django.utils.module_loading import import_string
    func = import_string(callback)
    assert callable(func), f"DASHBOARD_CALLBACK '{callback}' must import to a callable."


# =========================================================================== #
# AC3 — branded shell: SITE_TITLE / SITE_HEADER = "Velegrad CMS"               #
# =========================================================================== #
def test_unfold_site_title_and_header_are_velegrad_cms():
    # AC3: UNFOLD sets SITE_TITLE and SITE_HEADER to the brand title.
    unfold = getattr(settings, "UNFOLD", {})
    assert "Velegrad CMS" in str(unfold.get("SITE_TITLE", "")), (
        "UNFOLD['SITE_TITLE'] must be 'Velegrad CMS' (AC3)."
    )
    assert "Velegrad CMS" in str(unfold.get("SITE_HEADER", "")), (
        "UNFOLD['SITE_HEADER'] must be 'Velegrad CMS' (AC3)."
    )


@pytest.mark.django_db
def test_admin_index_is_branded_velegrad_cms(client, django_user_model):
    # AC3: logged-in superuser GET on admin index returns branded HTML containing
    # "Velegrad CMS" and NOT the default "Django administration".
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index must return 200, got {resp.status_code}"
    )
    html = resp.content.decode("utf-8")
    assert "Velegrad CMS" in html, "admin index HTML must contain 'Velegrad CMS' (AC3)."
    assert "Django administration" not in html, (
        "admin index must NOT show default 'Django administration' branding (AC3)."
    )


# =========================================================================== #
# AC4 / AC9 — dashboard metrics rendered (3 / 2 / 1) on the index HTML         #
# =========================================================================== #
def _assert_card_count(html, label, expected, *, ac="AC4"):
    """Assert the metric card whose label is ``label`` renders ``expected``.

    Binds each count to ITS card: the dashboard template (templates/admin/
    index.html) renders every metric card as a label paragraph immediately
    followed by the count paragraph::

        <p class="...text-sm">Aktivne nekretnine</p>
        <p class="font-semibold text-2xl mt-2">3</p>

    So we anchor on the (translated) label text and require the very next
    ``font-semibold text-2xl`` paragraph to hold the expected number. A
    callback that swaps two counts, or a bare ``>N<`` matching a table/
    pagination cell elsewhere, can NOT satisfy this — the number must sit in
    the count paragraph that follows this specific label.
    """
    pattern = (
        re.escape(label)
        + r"\s*</p>\s*"
        + r'<p class="font-semibold text-2xl[^"]*">\s*'
        + re.escape(str(expected))
        + r"\s*</p>"
    )
    match = re.search(pattern, html)
    assert match is not None, (
        f"the '{label}' card must render its count {expected} in the count "
        f"paragraph immediately after its label ({ac}). Pattern not found — the "
        f"count is missing, mis-bound to another card, or rendered elsewhere."
    )


@pytest.mark.django_db
def test_dashboard_renders_metric_numbers(client, django_user_model):
    # AC4/AC9: with seed data (3 active / 1 inactive Property, 2 new / 1 closed
    # Inquiry, 1 featured), the admin index HTML renders 3 / 2 / 1 — each in ITS
    # OWN card. The counts are mutually distinct (3, 2, 1) so any swap or
    # mis-binding between the active / new-inquiries / featured cards FAILS here.
    _superuser(django_user_model)
    _seed_dashboard_data()
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index must return 200 with seed data, got {resp.status_code}"
    )
    html = resp.content.decode("utf-8")
    # Each count is anchored to its card's label (label text -> the very next
    # count paragraph), so the assertion binds the RIGHT number to the RIGHT card.
    _assert_card_count(html, "Aktivne nekretnine", 3)
    _assert_card_count(html, "Novi upiti", 2)
    _assert_card_count(html, "Izdvojene nekretnine", 1)


# =========================================================================== #
# AC5 / AC9 — quick actions + latest inquiries table rendered                  #
# =========================================================================== #
@pytest.mark.django_db
def test_dashboard_renders_quick_action_hrefs(client, django_user_model):
    # AC5/AC9/AC10: admin index HTML contains the reverse()-derived hrefs for the
    # "Add property" and "Inquiries changelist" quick actions.
    _superuser(django_user_model)
    _seed_dashboard_data()
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")

    add_url = _try_reverse("admin:properties_property_add")
    inq_url = _try_reverse("admin:inquiries_inquiry_changelist")
    assert add_url is not None, (
        "admin:properties_property_add must resolve — Property must be registered "
        "(AC10); without it the dashboard reverse() raises NoReverseMatch -> 500."
    )
    assert inq_url is not None, (
        "admin:inquiries_inquiry_changelist must resolve — Inquiry must be "
        "registered (AC10)."
    )
    assert f'href="{add_url}"' in html, (
        f"dashboard must link to the Add-property route ({add_url}) (AC5)."
    )
    assert f'href="{inq_url}"' in html, (
        f"dashboard must link to the Inquiry changelist ({inq_url}) (AC5)."
    )


@pytest.mark.django_db
def test_dashboard_renders_latest_inquiry_rows(client, django_user_model):
    # AC5/AC9: the dashboard renders rows from the latest inquiries (name shows up).
    _superuser(django_user_model)
    _make_inquiry(name="Jelena Najnovija", status="new")
    _make_inquiry(name="Petar Stariji", status="contacted")
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "Jelena Najnovija" in html, (
        "the latest-inquiries table must render the newest inquiry's name (AC5)."
    )


@pytest.mark.django_db
def test_dashboard_latest_inquiries_capped_at_five(client, django_user_model):
    # AC5: the latest-inquiries table shows at most the 5 newest by -created_at.
    _superuser(django_user_model)
    # created_at is auto_now_add; on some hosts datetime.now() resolution lets
    # rapid creates share a timestamp, and the UUID pk gives no stable tiebreak.
    # Stamp strictly-increasing created_at values so "Broj i" ordering is
    # deterministic and this cap-at-5 assertion can never flake.
    import datetime

    from django.utils import timezone

    Inquiry = _get_model("inquiries", "Inquiry")
    base = timezone.now() - datetime.timedelta(hours=1)
    for i in range(7):
        inq = _make_inquiry(name=f"Upit Broj {i}", status="new")
        Inquiry.objects.filter(pk=inq.pk).update(
            created_at=base + datetime.timedelta(minutes=i)
        )
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    # The 2 oldest (created first) must be pushed out of the top-5 window.
    assert "Upit Broj 6" in html, "the newest inquiry must appear in the table (AC5)."
    assert "Upit Broj 0" not in html and "Upit Broj 1" not in html, (
        "the latest-inquiries table must be capped at the 5 newest (AC5)."
    )


@pytest.mark.django_db
def test_dashboard_empty_state_when_no_inquiries(client, django_user_model):
    # AC5: with NO inquiries, the dashboard still renders 200 (defensive callback,
    # never 500) AND the dashboard scaffold is present — the two quick-action
    # links still render from the callback context even with an empty table. This
    # ties the test to the FEATURE (callback + registration + override), so it
    # fails in RED rather than passing on the stock admin index.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        "dashboard must render 200 with an empty DB (defensive callback, AC5/Dev "
        f"Note d); got {resp.status_code}."
    )
    html = resp.content.decode("utf-8")
    add_url = _try_reverse("admin:properties_property_add")
    inq_url = _try_reverse("admin:inquiries_inquiry_changelist")
    assert add_url is not None and inq_url is not None, (
        "quick-action routes must resolve even on an empty DB (AC5/AC10)."
    )
    assert f'href="{add_url}"' in html and f'href="{inq_url}"' in html, (
        "the dashboard quick-action links must render even when there are no "
        "inquiries (empty-state still shows the scaffold) (AC5)."
    )


# =========================================================================== #
# AC9 — the index template override is actually used                           #
# =========================================================================== #
@pytest.mark.django_db
def test_admin_index_uses_project_override_template(client, django_user_model):
    # AC9: the admin index must render an 'admin/index.html' that resolves to the
    # PROJECT override under BASE_DIR/templates — NOT the stock template shipped by
    # django.contrib.admin (whose presence alone would falsely pass in RED).
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200
    project_templates = str(settings.BASE_DIR).replace("\\", "/").rstrip("/") + "/templates"
    origins = []
    for tmpl in resp.templates:
        if getattr(tmpl, "name", None) != "admin/index.html":
            continue
        origin = getattr(tmpl, "origin", None)
        origin_name = getattr(origin, "name", "") or ""
        origins.append(origin_name.replace("\\", "/"))
    assert origins, (
        "admin index did not render any 'admin/index.html' template (AC9)."
    )
    assert any(o.startswith(project_templates) for o in origins), (
        "the admin index must use the PROJECT 'admin/index.html' override under "
        f"{project_templates} — got origins {origins}. A stock contrib template "
        "(no override) means the dashboard cards/links/table are not rendered (AC9)."
    )


# =========================================================================== #
# AC10 — Property & Inquiry registered (routes resolve; registry holds them)   #
# =========================================================================== #
def test_property_and_inquiry_registered_in_admin():
    # AC10: Property and Inquiry must be in the admin site registry so the named
    # routes exist and reverse() works.
    Property = _get_model("properties", "Property")
    Inquiry = _get_model("inquiries", "Inquiry")
    registry = dj_admin.site._registry
    assert Property in registry, "Property must be registered in admin (AC10)."
    assert Inquiry in registry, "Inquiry must be registered in admin (AC10)."


def test_quick_action_routes_resolve_without_noreversematch():
    # AC10: the two quick-action routes must resolve (no NoReverseMatch).
    assert _try_reverse("admin:properties_property_add") is not None, (
        "reverse('admin:properties_property_add') must not raise NoReverseMatch "
        "(AC10)."
    )
    assert _try_reverse("admin:inquiries_inquiry_changelist") is not None, (
        "reverse('admin:inquiries_inquiry_changelist') must not raise "
        "NoReverseMatch (AC10)."
    )


@pytest.mark.django_db
def test_property_changelist_returns_200(client, django_user_model):
    # AC8/AC10: superuser GET on the Property changelist returns 200.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_changelist")
    assert url is not None, "Property changelist route must resolve (AC10)."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property changelist must return 200, got {resp.status_code} (AC8)."
    )


@pytest.mark.django_db
def test_inquiry_changelist_returns_200(client, django_user_model):
    # AC8/AC10: superuser GET on the Inquiry changelist returns 200.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:inquiries_inquiry_changelist")
    assert url is not None, "Inquiry changelist route must resolve (AC10)."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Inquiry changelist must return 200, got {resp.status_code} (AC8)."
    )


@pytest.mark.django_db
def test_property_add_route_returns_200(client, django_user_model):
    # AC10: superuser GET on the Property add form returns 200 (quick-action target).
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_add")
    assert url is not None, "Property add route must resolve (AC10)."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property add form must return 200, got {resp.status_code} (AC10)."
    )


# =========================================================================== #
# AC6 — SiteSettings singleton admin (no add when exists, no delete, redirect) #
# =========================================================================== #
def test_sitesettings_registered_in_admin():
    # AC6: SiteSettings must be registered in the admin.
    SiteSettings = _get_model("core", "SiteSettings")
    assert SiteSettings in dj_admin.site._registry, (
        "SiteSettings must be registered in admin (AC6)."
    )


@pytest.mark.django_db
def test_sitesettings_has_add_permission_false_when_row_exists(rf, django_user_model):
    # AC6: has_add_permission is False once the singleton row exists.
    SiteSettings = _get_model("core", "SiteSettings")
    modeladmin = dj_admin.site._registry.get(SiteSettings)
    assert modeladmin is not None, "SiteSettings must be registered (AC6)."
    SiteSettings.objects.all().delete()
    SiteSettings.load()  # creates the singleton row
    request = rf.get("/")
    request.user = _superuser(django_user_model)
    assert modeladmin.has_add_permission(request) is False, (
        "has_add_permission must be False when a SiteSettings row exists (AC6)."
    )


@pytest.mark.django_db
def test_sitesettings_has_delete_permission_false(rf, django_user_model):
    # AC6: has_delete_permission is always False (singleton is never deleted).
    SiteSettings = _get_model("core", "SiteSettings")
    modeladmin = dj_admin.site._registry.get(SiteSettings)
    assert modeladmin is not None, "SiteSettings must be registered (AC6)."
    SiteSettings.objects.all().delete()
    obj = SiteSettings.load()
    request = rf.get("/")
    request.user = _superuser(django_user_model)
    assert modeladmin.has_delete_permission(request, obj) is False, (
        "has_delete_permission(obj) must be False (AC6)."
    )
    assert modeladmin.has_delete_permission(request) is False, (
        "has_delete_permission() must be False (AC6)."
    )


@pytest.mark.django_db
def test_sitesettings_changelist_redirects_to_change_view(client, django_user_model):
    # AC6: GET on the SiteSettings changelist redirects (302) to the change view
    # of the single row.
    SiteSettings = _get_model("core", "SiteSettings")
    SiteSettings.objects.all().delete()
    obj = SiteSettings.load()
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    changelist = _try_reverse("admin:core_sitesettings_changelist")
    assert changelist is not None, "SiteSettings changelist route must resolve (AC6)."
    resp = client.get(changelist)
    assert resp.status_code == 302, (
        f"SiteSettings changelist must redirect (302), got {resp.status_code} (AC6)."
    )
    change_url = _try_reverse("admin:core_sitesettings_change")
    # change_url reverse needs args; build expected target directly.
    expected = reverse("admin:core_sitesettings_change", args=[obj.pk])
    assert resp.url == expected, (
        f"SiteSettings changelist must redirect to the single row's change view "
        f"{expected}, got {resp.url} (AC6)."
    )


# =========================================================================== #
# AC7 — admin only on ADMIN_URL; /admin/ is 404; login branded                 #
# =========================================================================== #
@pytest.mark.django_db
def test_default_admin_path_returns_404(client):
    # AC7: GET /admin/ stays 404 (mount unchanged from 1.1).
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must return 404 (NFR-5, unchanged from 1.1), got {resp.status_code}."
    )


@pytest.mark.django_db
def test_admin_login_page_is_branded(client):
    # AC7: GET the configured ADMIN_URL login (anonymous) returns 200 and renders
    # the SITE_HEADER brand text.
    resp = client.get(_admin_login_path())
    assert resp.status_code == 200, (
        f"admin login at {_admin_login_path()} must return 200, got {resp.status_code}."
    )
    html = resp.content.decode("utf-8")
    assert "Velegrad CMS" in html, (
        "the branded admin login must render the SITE_HEADER 'Velegrad CMS' (AC7)."
    )


# =========================================================================== #
# AC8 — migrate on SQLite still works; check clean (regression)                #
# =========================================================================== #
@pytest.mark.django_db
def test_migrate_on_sqlite_has_no_unapplied_migrations():
    # AC8: adding Unfold must not break migrations on the SQLite test DB. The
    # pytest-django test DB is built by running migrate; here we assert the
    # migration executor sees NO unapplied migrations (the plan is fully applied)
    # AND that Unfold introduces no migrations of its own that would break this.
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    assert plan == [], (
        f"there must be NO unapplied migrations on the SQLite test DB (AC8); "
        f"unapplied plan: {plan}"
    )
    # Sanity: our app migrations must be present in the applied graph.
    applied_apps = {app for app, _name in executor.loader.applied_migrations}
    for app_label in ("properties", "inquiries", "core", "pages"):
        assert app_label in applied_apps, (
            f"app '{app_label}' migrations must be applied on the test DB (AC8)."
        )


# =========================================================================== #
# Dev-Note render prereqs — request context processor + staticfiles + STATIC   #
# =========================================================================== #
def test_request_context_processor_present():
    # Dev Note (a): Unfold templates require the request context processor.
    procs = settings.TEMPLATES[0]["OPTIONS"]["context_processors"]
    assert "django.template.context_processors.request" in procs, (
        "TEMPLATES context_processors must include "
        "'django.template.context_processors.request' (Unfold render prereq)."
    )


def test_staticfiles_app_and_static_url_present():
    # Dev Note (b): staticfiles app + STATIC_URL needed so {% static %} resolves
    # under the test client.
    assert "django.contrib.staticfiles" in settings.INSTALLED_APPS, (
        "'django.contrib.staticfiles' must be in INSTALLED_APPS (Unfold render prereq)."
    )
    assert getattr(settings, "STATIC_URL", None), (
        "STATIC_URL must be set (Unfold render prereq)."
    )


# =========================================================================== #
# Batch-fix regression coverage (non-mandatory hardening, Story 1.3 follow-up) #
# =========================================================================== #
@pytest.mark.django_db
def test_dashboard_empty_state_message_renders_when_no_inquiries(client, django_user_model):
    # A1: with NO inquiries the latest-inquiries panel must render its empty-state
    # message ("Još nema upita.") rather than an empty/blank table body — locking
    # the template's {% if velegrad_latest_inquiries %}/{% else %} branch.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "Još nema upita." in html, (
        "the dashboard must render the empty-state message 'Još nema upita.' when "
        "there are no inquiries (templates/admin/index.html {% else %} branch)."
    )


@pytest.mark.django_db
def test_sitesettings_has_add_permission_true_when_no_row(rf, django_user_model):
    # A2: has_add_permission is True on a completely empty DB (no SiteSettings row).
    # Complements the existing False-branch test.
    SiteSettings = _get_model("core", "SiteSettings")
    modeladmin = dj_admin.site._registry.get(SiteSettings)
    assert modeladmin is not None, "SiteSettings must be registered (AC6)."
    SiteSettings.objects.all().delete()
    request = rf.get("/")
    request.user = _superuser(django_user_model)
    assert modeladmin.has_add_permission(request) is True, (
        "has_add_permission must be True when no SiteSettings row exists (AC6)."
    )


@pytest.mark.django_db
def test_sitesettings_changelist_returns_200_when_no_row(client, django_user_model):
    # A3: when NO singleton row exists, the SiteSettings changelist must fall
    # through to super().changelist_view() and return 200 (not redirect, not 500).
    SiteSettings = _get_model("core", "SiteSettings")
    SiteSettings.objects.all().delete()
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    changelist = _try_reverse("admin:core_sitesettings_changelist")
    assert changelist is not None, "SiteSettings changelist route must resolve (AC6)."
    resp = client.get(changelist)
    assert resp.status_code == 200, (
        "SiteSettings changelist must return 200 via the super() fallback when no "
        f"singleton row exists, got {resp.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_dashboard_escapes_inquiry_name_xss(client, django_user_model):
    # A4 (security regression): an Inquiry name containing a <script> payload must
    # be HTML-escaped in the dashboard's latest-inquiries table. Locks in Django
    # auto-escaping so a future |safe / {% autoescape off %} regression is caught.
    _superuser(django_user_model)
    _make_inquiry(name="<script>alert(1)</script>", status="new")
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "<script>alert(1)</script>" not in html, (
        "raw <script> from an Inquiry name must NOT appear unescaped in the "
        "dashboard HTML (XSS regression)."
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html, (
        "the Inquiry name must be HTML-escaped (&lt;script&gt;...) in the "
        "dashboard's latest-inquiries table (Django auto-escaping)."
    )


@pytest.mark.django_db
def test_unfold_settings_colors_not_mutated_after_index_render(client, django_user_model):
    # A5 (architecture regression): rendering the admin index must NOT mutate
    # settings.UNFOLD. The Champagne secondary "500" must stay the raw
    # "201 169 110" RGB-channel string (NOT normalized to "rgb(...)") afterwards,
    # proving Unfold's merge deep-copies and our settings dict stays pristine.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200
    secondary = settings.UNFOLD["COLORS"]["secondary"]
    assert secondary["500"] == "201 169 110", (
        "settings.UNFOLD['COLORS']['secondary']['500'] must remain the raw RGB "
        f"channel string '201 169 110' after an index render, got {secondary['500']!r} "
        "— settings.UNFOLD was mutated in place."
    )
    assert "rgb(" not in secondary["500"], (
        "settings.UNFOLD must not be normalized to 'rgb(...)' in place (A5)."
    )
