"""
RED-phase contract tests for Story 1.4 — "Admin upravljanje nekretninama,
upitima i podešavanjima".

These tests define the CONTRACT for turning the MINIMAL Story 1.3 ModelAdmins
into FULL management functionality (FR24–FR27). They are written BEFORE the
feature is built, so EVERY 1.4 test in this module MUST FAIL/ERROR until the Dev
implements:

  * "adminsortable2" + "tinymce" in INSTALLED_APPS; bounded pins for
    django-admin-sortable2 AND django-tinymce in requirements/base.txt;
  * include("tinymce.urls") in config/urls.py;
  * a sortable PropertyImageInline (subclass of adminsortable2's
    SortableInlineAdminMixin) wired into PropertyAdmin.inlines;
  * TinyMCE WYSIWYG on Property.description_* / SiteSettings.founder_bio_*;
  * a "Dupliraj" admin action (duplicate_selected) that copies fields + M2M
    features, resets slug, mints a new UUID pk, and does NOT copy PropertyImage;
  * a reusable preview authorization helper
    (properties/preview.py::can_preview(request, obj)) + an admin-side ?preview=1
    link in the Property change form;
  * InquiryAdmin list_display / list_filter (status + date) / list_editable /
    search_fields;
  * bilingual SR/EN PropertyAdmin fieldsets + full SiteSettingsAdmin fieldsets.

Design rules (mirrors tests/test_admin_dashboard.py — the 1.3 harness):
  * DB / client tests are marked @pytest.mark.django_db (pytest-django active via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * The admin path is computed from settings.ADMIN_URL the SAME way the app does.
  * We DO NOT import unfold types and we GUARD the fragile adminsortable2 import
    (it is NOT installed yet) so RED failures read as "feature absent"
    (missing attr / NoReverseMatch / unbranded HTML / not-a-subclass), NOT a
    collection-time ImportError.
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    1-4-admin-upravljanje-nekretninama-upitima-i-podesavanjima-interface-contract.md
"""
import importlib
import re
from pathlib import Path

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
    """The mounted admin index path, derived from settings.ADMIN_URL."""
    return "/" + settings.ADMIN_URL.strip("/") + "/"


def _try_reverse(name, args=None):
    """reverse(name) or None if the route does not exist yet (RED phase)."""
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return None


def _get_model(app_label, class_name):
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


def _get_modeladmin(app_label, class_name):
    """Return the registered ModelAdmin instance for a model, or None."""
    model = _get_model(app_label, class_name)
    return dj_admin.site._registry.get(model)


def _import_optional(dotted):
    """Import a dotted attr, returning None if anything is missing.

    Used to guard the fragile ``adminsortable2`` import (NOT installed in RED)
    and the future ``properties.preview`` module so the test fails as a clean
    assertion rather than a collection-time ImportError/AttributeError.
    """
    module_path, _, attr = dotted.rpartition(".")
    try:
        module = importlib.import_module(module_path)
    except Exception:
        return None
    return getattr(module, attr, None)


# --------------------------------------------------------------------------- #
# DB seeding helpers (consistent with tests/test_admin_dashboard.py).          #
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


def _make_feature(**overrides):
    PropertyFeature = _get_model("properties", "PropertyFeature")
    defaults = dict(
        name_sr="Terasa",
        name_en="Terrace",
        icon="terrace",
        category="exterior",
    )
    defaults.update(overrides)
    return PropertyFeature.objects.create(**defaults)


def _make_image(prop, **overrides):
    PropertyImage = _get_model("properties", "PropertyImage")
    defaults = dict(
        property=prop,
        image="properties/gallery/test.jpg",
        caption="Dnevna soba",
        order=0,
        is_hero=True,
    )
    defaults.update(overrides)
    return PropertyImage.objects.create(**defaults)


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


def _seed_singleton():
    """Ensure exactly one SiteSettings row exists (required by 1.3 redirect)."""
    SiteSettings = _get_model("core", "SiteSettings")
    SiteSettings.objects.all().delete()
    return SiteSettings.load()


def _superuser(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass12345",
    )


def _staff(django_user_model):
    return django_user_model.objects.create_user(
        username="staffer", email="staff@example.com", password="pass12345",
        is_staff=True,
    )


def _plain_user(django_user_model):
    return django_user_model.objects.create_user(
        username="visitor", email="visitor@example.com", password="pass12345",
    )


def _flatten_fieldset_fields(fieldsets):
    """Flatten the ``fields`` of every fieldset into a flat set of names."""
    out = set()
    for _label, opts in fieldsets:
        for field in opts.get("fields", ()):
            if isinstance(field, (tuple, list)):
                out.update(field)
            else:
                out.add(field)
    return out


# =========================================================================== #
# AC1 — PropertyImage sortable inline (adminsortable2)                          #
# =========================================================================== #
def test_adminsortable2_in_installed_apps():
    # AC1: "adminsortable2" must be in INSTALLED_APPS (sortable JS/CSS statics).
    assert "adminsortable2" in settings.INSTALLED_APPS, (
        "'adminsortable2' must be added to INSTALLED_APPS (AC1)."
    )


def test_adminsortable2_is_importable():
    # AC1: django-admin-sortable2 must be installed in the active venv.
    mixin = _import_optional("adminsortable2.admin.SortableInlineAdminMixin")
    assert mixin is not None, (
        "django-admin-sortable2 must be installed: "
        "`import adminsortable2.admin.SortableInlineAdminMixin` failed (AC1)."
    )


def test_requirements_base_pins_sortable2_with_bounded_range():
    # AC1/AC6: requirements/base.txt must bounded-pin django-admin-sortable2
    # (Story 1.3 AC11 convention) — not a bare name.
    base_txt = Path(settings.BASE_DIR) / "requirements" / "base.txt"
    lines = [
        ln.strip() for ln in base_txt.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    matched = [ln for ln in lines if ln.lower().startswith("django-admin-sortable2")]
    assert matched, "requirements/base.txt must list django-admin-sortable2."
    spec = matched[0]
    assert spec.lower() != "django-admin-sortable2", (
        "django-admin-sortable2 must be PINNED, not bare (AC1, 1.3 AC11)."
    )
    assert "<" in spec, f"sortable2 pin needs an upper bound, got: {spec!r}"
    assert (">=" in spec) or ("==" in spec), (
        f"sortable2 pin needs a lower bound (>= or ==), got: {spec!r}"
    )


def test_property_image_inline_is_subclass_of_sortable_mixin():
    # AC1(a): PropertyImageInline must be a subclass of adminsortable2's
    # SortableInlineAdminMixin — a Python-level proof, not just HTML. A plain
    # (non-sortable) inline MUST NOT satisfy this.
    inline_cls = _import_optional("properties.admin.PropertyImageInline")
    assert inline_cls is not None, (
        "properties.admin.PropertyImageInline must be defined (AC1)."
    )
    sortable_mixin = _import_optional("adminsortable2.admin.SortableInlineAdminMixin")
    assert sortable_mixin is not None, (
        "adminsortable2 must be installed so SortableInlineAdminMixin exists (AC1)."
    )
    assert issubclass(inline_cls, sortable_mixin), (
        "PropertyImageInline must subclass adminsortable2.admin."
        "SortableInlineAdminMixin (AC1a) — a plain inline does NOT qualify."
    )
    PropertyImage = _get_model("properties", "PropertyImage")
    assert getattr(inline_cls, "model", None) is PropertyImage, (
        "PropertyImageInline.model must be PropertyImage (AC1)."
    )


def test_property_admin_declares_image_inline():
    # AC1: PropertyAdmin.inlines must contain PropertyImageInline.
    modeladmin = _get_modeladmin("properties", "Property")
    assert modeladmin is not None, "Property must be registered in admin."
    inline_cls = _import_optional("properties.admin.PropertyImageInline")
    assert inline_cls is not None, "PropertyImageInline must be defined (AC1)."
    assert inline_cls in list(getattr(modeladmin, "inlines", [])), (
        "PropertyAdmin.inlines must include PropertyImageInline (AC1)."
    )


@pytest.mark.django_db
def test_property_add_form_renders_inline_baseline(client, django_user_model):
    # AC1 baseline: GET Property add form (superuser) -> 200 with the PropertyImage
    # inline formset present (stable baseline marker, not the sortable marker).
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_add")
    assert url is not None, "Property add route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property add form must return 200, got {resp.status_code} (AC1)."
    )
    html = resp.content.decode("utf-8")
    assert "images-TOTAL_FORMS" in html or "images-" in html, (
        "the Property add form must render the PropertyImage inline formset "
        "(related_name='images') — inline not wired into PropertyAdmin (AC1)."
    )


@pytest.mark.django_db
def test_property_change_form_renders_sortable_marker(client, django_user_model):
    # AC1(b): the Property change form HTML must contain an adminsortable2-SPECIFIC
    # marker injected ONLY by an active sortable inline — namely the package's
    # static media path "adminsortable2/" (its reorder JS). The bare word
    # "sortable" is NOT used as a marker because it can appear elsewhere (e.g. in
    # a Property title/slug); "adminsortable2/" is emitted only when the sortable
    # inline's Media is loaded, so a plain (non-sortable) inline cannot satisfy it.
    _superuser(django_user_model)
    prop = _make_property(title="Galerija Demo")
    _make_image(prop, order=0)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_change", args=[prop.pk])
    assert url is not None, "Property change route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property change form must return 200, got {resp.status_code} (AC1)."
    )
    html = resp.content.decode("utf-8").lower()
    assert "adminsortable2" in html, (
        "the Property change form HTML must reference the adminsortable2 static "
        "media (e.g. an 'adminsortable2/...' JS/CSS path) — emitted ONLY by an "
        "ACTIVE sortable inline's Media; a plain inline does not (AC1b)."
    )


# =========================================================================== #
# AC2 — TinyMCE WYSIWYG for RichText descriptions                              #
# =========================================================================== #
def test_tinymce_in_installed_apps():
    # AC2: "tinymce" must be in INSTALLED_APPS (activates the HTMLField widget).
    assert "tinymce" in settings.INSTALLED_APPS, (
        "'tinymce' must be added to INSTALLED_APPS (AC2)."
    )


def test_requirements_base_pins_tinymce_with_bounded_range():
    # AC2/AC6: django-tinymce must be bounded-pinned (1.3 AC11 convention).
    base_txt = Path(settings.BASE_DIR) / "requirements" / "base.txt"
    lines = [
        ln.strip() for ln in base_txt.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    # Match django-tinymce but NOT django-tinymce-* hypothetical siblings.
    matched = [
        ln for ln in lines
        if re.match(r"(?i)^django-tinymce(\s|>|<|=|!|~|$)", ln)
    ]
    assert matched, "requirements/base.txt must list django-tinymce."
    spec = matched[0]
    assert spec.lower() != "django-tinymce", (
        "django-tinymce must be PINNED, not bare (AC2, 1.3 AC11)."
    )
    assert "<" in spec, f"django-tinymce pin needs an upper bound, got: {spec!r}"
    assert (">=" in spec) or ("==" in spec), (
        f"django-tinymce pin needs a lower bound (>= or ==), got: {spec!r}"
    )


def test_installed_tinymce_version_within_pinned_range():
    # AC2: the installed django-tinymce version satisfies the declared range.
    from importlib.metadata import version

    from packaging.requirements import Requirement

    installed = version("django-tinymce")
    base_txt = Path(settings.BASE_DIR) / "requirements" / "base.txt"
    lines = [
        ln.strip() for ln in base_txt.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    matched = [
        ln for ln in lines
        if re.match(r"(?i)^django-tinymce(\s|>|<|=|!|~|$)", ln)
    ]
    assert matched, "requirements/base.txt must list django-tinymce."
    req = Requirement(matched[0])
    assert len(req.specifier) > 0, (
        f"django-tinymce must carry a bounded specifier, got bare {matched[0]!r}."
    )
    assert req.specifier.contains(installed, prereleases=True), (
        f"installed django-tinymce {installed} is OUTSIDE the pinned range "
        f"'{matched[0]}' (AC2)."
    )


def test_tinymce_urls_are_mounted():
    # AC2: tinymce.urls must be included in config/urls.py — its named routes must
    # be RESOLVABLE (the include is wired). We do NOT assert a "tinymce:"
    # namespace (django-tinymce 5.0.0 has app_name=None / no namespace); the real
    # route names are tinymce-compressor / tinymce-filebrowser / tinymce-linklist.
    #
    # WHY reverse() (URLConf-level), not a GET on the view: the compressor /
    # filebrowser views execute logic that 500s in this minimal project (they
    # render a missing template / reverse the optional django-filebrowser app),
    # and with DEBUG=True the test client RE-RAISES that exception — so a GET
    # would ERROR after implementation, not assert "not 404". reverse() cleanly
    # distinguishes RED (route absent -> NoReverseMatch) from GREEN (route
    # mounted -> resolves) without invoking the fragile view body. The path it
    # resolves to MUST sit under the documented "tinymce/" mount prefix.
    url = _try_reverse("tinymce-compressor")
    assert url is not None, (
        "tinymce.urls must be mounted (include('tinymce.urls') in config/urls.py) "
        "so reverse('tinymce-compressor') resolves (AC2). It does not yet."
    )
    assert "tinymce" in url, (
        f"the tinymce route must mount under a 'tinymce/' prefix, got {url!r} (AC2)."
    )
    # A second route name from the same include, to prove the whole urlconf landed.
    assert _try_reverse("tinymce-filebrowser") is not None, (
        "reverse('tinymce-filebrowser') must also resolve — the full tinymce.urls "
        "include must be mounted (AC2)."
    )


@pytest.mark.django_db
def test_property_change_form_renders_tinymce_widget(client, django_user_model):
    # AC2: the Property change form must render a TinyMCE-initialized widget for
    # the description_* HTMLFields (class="tinymce").
    #
    # WHY THIS IS A GENUINE RED SIGNAL (verified against this Unfold admin):
    # Unfold's ModelAdmin maps models.TextField -> UnfoldAdminTextareaWidget via
    # formfield_overrides, and HTMLField subclasses TextField, so the minimal 1.3
    # PropertyAdmin renders description_* as a PLAIN Unfold textarea (NO
    # class="tinymce"), regardless of whether django-tinymce is installed. The 1.4
    # delta is wiring the TinyMCE widget explicitly (e.g. formfield_overrides =
    # {HTMLField: {"widget": TinyMCE}} or unfold.contrib.forms WysiwygWidget) AND
    # adding "tinymce" to INSTALLED_APPS. Only then does class="tinymce" appear.
    #
    # NOTE: we deliberately do NOT assert that /static/tinymce/*.js is served by
    # the test client — in this project the test client routes through
    # config.urls, which mounts NO staticfiles view (DEBUG static serving is not
    # wired into the URLconf), so EVERY /static/... path 404s under the test
    # client even for stock admin/unfold assets. Such an assertion would be
    # unsatisfiable. The widget marker + the tinymce.urls mount test
    # (test_tinymce_urls_are_mounted) are the deterministic AC2 signals.
    _superuser(django_user_model)
    prop = _make_property(title="TinyMCE Test")
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_change", args=[prop.pk])
    assert url is not None, "Property change route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property change form must return 200, got {resp.status_code} (AC2)."
    )
    html = resp.content.decode("utf-8")
    assert 'class="tinymce"' in html.lower(), (
        "the Property change form must render the TinyMCE widget (class='tinymce') "
        "for description_* — the minimal 1.3 admin renders a plain Unfold textarea; "
        "the 1.4 delta wires the TinyMCE widget for the HTMLFields (AC2)."
    )


@pytest.mark.django_db
def test_sitesettings_change_form_renders_tinymce_for_founder_bio(client, django_user_model):
    # AC2: SiteSettings change form renders the TinyMCE widget for founder_bio_*
    # (class="tinymce"). Same RED rationale as the Property test above: the
    # minimal 1.3 SiteSettingsAdmin renders founder_bio_* as a plain Unfold
    # textarea (Unfold's TextField override), so class="tinymce" is ABSENT until
    # the 1.4 TinyMCE widget wiring lands. We do NOT assert a served static asset
    # (the test client serves no /static/... under config.urls — unsatisfiable).
    obj = _seed_singleton()
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:core_sitesettings_change", args=[obj.pk])
    assert url is not None, "SiteSettings change route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"SiteSettings change form must return 200, got {resp.status_code} (AC2)."
    )
    html = resp.content.decode("utf-8")
    assert 'class="tinymce"' in html.lower(), (
        "the SiteSettings change form must render the TinyMCE widget for "
        "founder_bio_* — the minimal 1.3 admin renders a plain Unfold textarea; "
        "the 1.4 delta wires TinyMCE for the founder_bio HTMLFields (AC2)."
    )


# =========================================================================== #
# AC3 — "Dupliraj" admin action + preview helper                               #
# =========================================================================== #
def test_property_admin_registers_duplicate_action():
    # AC3a: PropertyAdmin.actions must include "duplicate_selected".
    modeladmin = _get_modeladmin("properties", "Property")
    assert modeladmin is not None, "Property must be registered in admin."
    actions = list(getattr(modeladmin, "actions", []) or [])
    assert "duplicate_selected" in actions, (
        "PropertyAdmin.actions must include 'duplicate_selected' (the 'Dupliraj' "
        "action) (AC3a)."
    )


@pytest.mark.django_db
def test_duplicate_action_copies_fields_features_resets_slug(client, django_user_model):
    # AC3a: running "Dupliraj" over 1 property (with features + 1 image) creates
    # exactly one new Property with a DIFFERENT slug+pk, the SAME features, NO
    # copied images, and leaves the original untouched.
    Property = _get_model("properties", "Property")
    PropertyImage = _get_model("properties", "PropertyImage")
    modeladmin = _get_modeladmin("properties", "Property")
    assert modeladmin is not None, "Property must be registered in admin."
    duplicate = getattr(modeladmin, "duplicate_selected", None)
    assert callable(duplicate), (
        "PropertyAdmin.duplicate_selected must be a callable admin action (AC3a)."
    )

    feature = _make_feature()
    original = _make_property(title="Original Stan")
    original.features.add(feature)
    _make_image(original, order=0)

    from django.test import RequestFactory
    rf = RequestFactory()
    req = rf.post("/")
    req.user = _superuser(django_user_model)
    # Some admin actions emit messages; attach a message store defensively.
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(req, "session", {})
    setattr(req, "_messages", FallbackStorage(req))

    duplicate(modeladmin, req, Property.objects.filter(pk=original.pk))

    assert Property.objects.count() == 2, (
        "Dupliraj must create exactly one new Property (AC3a)."
    )
    copy = Property.objects.exclude(pk=original.pk).get()
    assert copy.pk != original.pk, "the copy must have a new (UUID) pk (AC3a)."
    assert copy.slug and copy.slug != original.slug, (
        "the copy must get a DIFFERENT, auto-regenerated slug (AC3a)."
    )
    assert set(copy.features.all()) == {feature}, (
        "the copy must carry the SAME M2M features (AC3a)."
    )
    assert PropertyImage.objects.filter(property=copy).count() == 0, (
        "the copy must have NO PropertyImage rows (gallery not duplicated) (AC3a)."
    )
    # Original untouched.
    original.refresh_from_db()
    assert original.slug, "the original property must remain intact (AC3a)."
    assert PropertyImage.objects.filter(property=original).count() == 1, (
        "the original's image must remain (AC3a)."
    )


@pytest.mark.django_db
def test_duplicate_action_twice_no_integrity_error(client, django_user_model):
    # AC3a edge: duplicating an already-duplicated property must NOT raise
    # IntegrityError (title grows "Kopija — Kopija — ..."; slug reset + the 1.2
    # collision-safe save keep slugs unique). Title growth is acceptable for MVP.
    Property = _get_model("properties", "Property")
    modeladmin = _get_modeladmin("properties", "Property")
    assert modeladmin is not None, "Property must be registered in admin."
    duplicate = getattr(modeladmin, "duplicate_selected", None)
    assert callable(duplicate), "duplicate_selected must be callable (AC3a)."

    from django.test import RequestFactory
    from django.contrib.messages.storage.fallback import FallbackStorage
    rf = RequestFactory()
    req = rf.post("/")
    req.user = _superuser(django_user_model)
    setattr(req, "session", {})
    setattr(req, "_messages", FallbackStorage(req))

    original = _make_property(title="Penthouse")
    duplicate(modeladmin, req, Property.objects.filter(pk=original.pk))
    first_copy = Property.objects.exclude(pk=original.pk).get()
    # Duplicate the copy again — must not blow up on slug collision.
    duplicate(modeladmin, req, Property.objects.filter(pk=first_copy.pk))

    assert Property.objects.count() == 3, (
        "double-duplicate must produce 3 distinct properties without IntegrityError "
        "(AC3a)."
    )
    slugs = list(Property.objects.values_list("slug", flat=True))
    assert len(slugs) == len(set(slugs)), (
        "all property slugs must remain unique after double-duplicate (AC3a)."
    )


@pytest.mark.django_db
def test_duplicate_action_multi_select_creates_one_copy_each(client, django_user_model):
    # AC3a: running "Dupliraj" over a queryset of 2+ properties AT ONCE creates
    # exactly one copy per selected property (mirrors the single + sequential
    # tests). 2 originals -> 4 total, with unique slugs.
    Property = _get_model("properties", "Property")
    modeladmin = _get_modeladmin("properties", "Property")
    assert modeladmin is not None, "Property must be registered in admin."
    duplicate = getattr(modeladmin, "duplicate_selected", None)
    assert callable(duplicate), "duplicate_selected must be callable (AC3a)."

    from django.test import RequestFactory
    from django.contrib.messages.storage.fallback import FallbackStorage
    rf = RequestFactory()
    req = rf.post("/")
    req.user = _superuser(django_user_model)
    setattr(req, "session", {})
    setattr(req, "_messages", FallbackStorage(req))

    first = _make_property(title="Stan A")
    second = _make_property(title="Stan B")

    duplicate(modeladmin, req, Property.objects.filter(pk__in=[first.pk, second.pk]))

    assert Property.objects.count() == 4, (
        "Dupliraj over a 2-property queryset must create exactly 2 new copies "
        "(4 total) (AC3a)."
    )
    slugs = list(Property.objects.values_list("slug", flat=True))
    assert len(slugs) == len(set(slugs)), (
        "all property slugs must remain unique after a multi-select duplicate "
        "(AC3a)."
    )
    # The two originals remain intact.
    first.refresh_from_db()
    second.refresh_from_db()
    assert {first.pk, second.pk}.issubset(
        set(Property.objects.values_list("pk", flat=True))
    ), "both original properties must remain after a multi-select duplicate (AC3a)."


@pytest.mark.django_db
def test_can_preview_boolean_matrix(rf, django_user_model):
    # AC3b: the reusable can_preview(request, obj) helper returns True only when
    # is_active=True OR (staff + preview=1); False otherwise.
    can_preview = _import_optional("properties.preview.can_preview")
    assert callable(can_preview), (
        "properties.preview.can_preview(request, obj) must be a callable helper "
        "(AC3b) — Epic 3's detail view imports it for gating."
    )

    active = _make_property(title="Aktivna", is_active=True)
    inactive = _make_property(title="Neaktivna", is_active=False)
    staff = _staff(django_user_model)
    plain = _plain_user(django_user_model)

    from django.contrib.auth.models import AnonymousUser

    def _req(query, user):
        r = rf.get("/", query)
        r.user = user
        return r

    # is_active=True -> always True.
    assert can_preview(_req({}, AnonymousUser()), active) is True
    assert can_preview(_req({"preview": "1"}, staff), active) is True
    # is_active=False -> False for anonymous / non-staff / preview!=1.
    assert can_preview(_req({}, AnonymousUser()), inactive) is False
    assert can_preview(_req({"preview": "1"}, AnonymousUser()), inactive) is False
    assert can_preview(_req({"preview": "0"}, staff), inactive) is False
    assert can_preview(_req({}, staff), inactive) is False
    assert can_preview(_req({"preview": "1"}, plain), inactive) is False
    # is_active=False -> True ONLY for staff + preview=1.
    assert can_preview(_req({"preview": "1"}, staff), inactive) is True


@pytest.mark.django_db
def test_property_change_form_has_preview_link_for_inactive(client, django_user_model):
    # AC3c: the Property change form for an is_active=False property renders a
    # link/button whose URL contains '?preview=1' (real URL or documented
    # placeholder). Must NOT depend on a future Epic 3 detail route resolving.
    _superuser(django_user_model)
    prop = _make_property(title="Skrivena", is_active=False)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_change", args=[prop.pk])
    assert url is not None, "Property change route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property change form must return 200, got {resp.status_code} (AC3c)."
    )
    html = resp.content.decode("utf-8")
    assert "?preview=1" in html, (
        "the Property change form for an is_active=False property must render a "
        "preview link/button whose URL contains '?preview=1' (AC3c)."
    )


@pytest.mark.django_db
def test_property_change_form_preview_link_contains_slug(client, django_user_model):
    # AC3c (strengthened): the preview link for an is_active=False property must
    # point at the property's PUBLIC detail URL — i.e. contain
    # '/properties/{slug}/?preview=1', not merely the '?preview=1' substring.
    _superuser(django_user_model)
    prop = _make_property(title="Skrivena Sa Slugom", is_active=False)
    assert prop.slug, "the property must have an auto-generated slug (1.2)."
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_change", args=[prop.pk])
    assert url is not None, "Property change route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property change form must return 200, got {resp.status_code} (AC3c)."
    )
    html = resp.content.decode("utf-8")
    expected = f"/properties/{prop.slug}/?preview=1"
    assert expected in html, (
        "the preview link must point at the property's public detail URL "
        f"'{expected}' (slug-bound), not merely the '?preview=1' substring (AC3c)."
    )


@pytest.mark.django_db
def test_property_change_form_no_preview_link_for_active(client, django_user_model):
    # AC3c (negative): an is_active=True property is publicly visible, so its
    # change form/preview_link must NOT render a '?preview=1' link — preview_link
    # returns the em-dash placeholder "—". Complements the is_active=False test.
    _superuser(django_user_model)
    prop = _make_property(title="Aktivna Vidljiva", is_active=True)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_change", args=[prop.pk])
    assert url is not None, "Property change route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property change form must return 200, got {resp.status_code} (AC3c)."
    )
    html = resp.content.decode("utf-8")
    assert "?preview=1" not in html, (
        "an is_active=True property is public; its change form must NOT render a "
        "'?preview=1' preview link — preview_link returns the em-dash '—' (AC3c)."
    )


# =========================================================================== #
# AC4 — Inquiry admin: status/date filters + status editing                    #
# =========================================================================== #
def test_inquiry_admin_list_filter_has_status_and_date():
    # AC4: InquiryAdmin.list_filter includes a status-bound filter and a created_at
    # date filter. We verify a STATUS filter exists WITHOUT mandating the bare
    # "status" string: the bare string would register Django's
    # ChoicesFieldListFilter (?status__exact=) IN ADDITION to the custom
    # StatusListFilter (?status=), rendering a DUPLICATE "Status" panel in the
    # sidebar (a UX bug). So we accept either a SimpleListFilter whose
    # parameter_name == "status" OR a (field, filter) tuple whose field is "status".
    from inquiries.admin import StatusListFilter

    modeladmin = _get_modeladmin("inquiries", "Inquiry")
    assert modeladmin is not None, "Inquiry must be registered in admin."
    list_filter = list(getattr(modeladmin, "list_filter", []) or [])

    def _is_status_filter(entry):
        # A custom SimpleListFilter subclass bound to the "status" parameter.
        if isinstance(entry, type) and getattr(entry, "parameter_name", None) == "status":
            return True
        # A (field, filter) tuple or a bare "status" string both target the field.
        if isinstance(entry, (tuple, list)) and entry:
            return entry[0] == "status"
        return entry == "status"

    assert any(_is_status_filter(entry) for entry in list_filter), (
        "InquiryAdmin.list_filter must include a status-bound filter — e.g. the "
        "custom StatusListFilter (parameter_name='status') (AC4)."
    )
    # The custom StatusListFilter is the one that yields clean ?status= links.
    assert StatusListFilter in list_filter, (
        "InquiryAdmin.list_filter must use the custom StatusListFilter for status "
        "(clean ?status= links, single panel) (AC4)."
    )

    def _names(lf):
        for entry in lf:
            if isinstance(entry, (tuple, list)) and entry:
                yield entry[0]
            else:
                yield entry

    assert "created_at" in set(_names(list_filter)), (
        "InquiryAdmin.list_filter must include a 'created_at' date filter (AC4)."
    )


def test_inquiry_admin_search_fields():
    # AC4: InquiryAdmin.search_fields includes name/email/phone.
    modeladmin = _get_modeladmin("inquiries", "Inquiry")
    assert modeladmin is not None, "Inquiry must be registered in admin."
    search_fields = set(getattr(modeladmin, "search_fields", []) or [])
    for required in ("name", "email", "phone"):
        assert required in search_fields, (
            f"InquiryAdmin.search_fields must include '{required}' (AC4)."
        )


def test_inquiry_admin_list_editable_status_not_first_column():
    # AC4 edge: if list_editable contains 'status', then in list_display 'status'
    # must NOT be the first column (admin.E124). check() does not reliably catch
    # this; the GET-changelist test below is the runtime guard.
    modeladmin = _get_modeladmin("inquiries", "Inquiry")
    assert modeladmin is not None, "Inquiry must be registered in admin."
    list_editable = list(getattr(modeladmin, "list_editable", []) or [])
    list_display = list(getattr(modeladmin, "list_display", []) or [])
    assert "status" in list_display, (
        "InquiryAdmin.list_display must include 'status' (AC4)."
    )
    if "status" in list_editable:
        assert list_display.index("status") >= 1, (
            "when list_editable=['status'], 'status' must NOT be the first column "
            "of list_display (admin.E124) (AC4)."
        )


@pytest.mark.django_db
def test_inquiry_changelist_renders_status_filter_ui(client, django_user_model):
    # AC4: GET Inquiry changelist (superuser) -> 200 and the HTML contains the
    # status filter UI (e.g. ?status=new / ?status=closed filter links). A real
    # GET also surfaces any list_editable/first-column E124 runtime conflict.
    _superuser(django_user_model)
    _make_inquiry(name="Ana", status="new")
    _make_inquiry(name="Bojan", status="closed")
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:inquiries_inquiry_changelist")
    assert url is not None, "Inquiry changelist route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Inquiry changelist must return 200, got {resp.status_code} (AC4)."
    )
    html = resp.content.decode("utf-8")
    assert "status=new" in html or "status=closed" in html, (
        "the Inquiry changelist must render the status filter UI "
        "(?status=... links) — 'status' missing from list_filter (AC4)."
    )


@pytest.mark.django_db
def test_inquiry_changelist_has_no_duplicate_status_filter(client, django_user_model):
    # AC4 (regression): the changelist must render EXACTLY ONE status filter panel.
    # The custom StatusListFilter emits clean ?status= links; the bare "status"
    # string would ADDITIONALLY register Django's ChoicesFieldListFilter (emitting
    # ?status__exact= links) -> a DUPLICATE "Status" panel in the Unfold sidebar.
    # So the rendered HTML MUST contain ?status= but MUST NOT contain
    # ?status__exact= (the duplicate-panel marker).
    _superuser(django_user_model)
    _make_inquiry(name="Ana", status="new")
    _make_inquiry(name="Bojan", status="closed")
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:inquiries_inquiry_changelist")
    assert url is not None, "Inquiry changelist route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Inquiry changelist must return 200, got {resp.status_code} (AC4)."
    )
    html = resp.content.decode("utf-8")
    assert "status=new" in html or "status=closed" in html, (
        "the changelist must render the custom status filter (?status= links) (AC4)."
    )
    assert "status__exact=" not in html, (
        "the Inquiry changelist must NOT render a SECOND, duplicate status filter "
        "(?status__exact= links from Django's ChoicesFieldListFilter) — the bare "
        "'status' string must be dropped from list_filter, keeping ONLY the custom "
        "StatusListFilter (AC4)."
    )


@pytest.mark.django_db
def test_inquiry_status_change_persists_via_list_editable(client, django_user_model):
    # AC4: changing an inquiry's status via the changelist list_editable POST
    # persists to the DB. NOTE: the minimal 1.3 admin already persists status via
    # the per-object CHANGE form (Django builds it from the model), so that path
    # is NOT a valid RED signal. The 1.4 delta is inline `list_editable=["status"]`
    # on the CHANGELIST — that POST only updates the row once list_editable is
    # configured, so this is the 1.4-specific assertion.
    _superuser(django_user_model)
    inq = _make_inquiry(name="Vera", status="new")
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:inquiries_inquiry_changelist")
    assert url is not None, "Inquiry changelist route must resolve."
    resp = client.post(
        url,
        data={
            "_save": "Save",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": str(inq.pk),
            "form-0-status": "contacted",
        },
        follow=False,
    )
    assert resp.status_code in (200, 302), (
        f"Inquiry list_editable POST should not error, got {resp.status_code} (AC4)."
    )
    inq.refresh_from_db()
    assert inq.status == "contacted", (
        "changing status via the changelist list_editable POST must persist to the "
        "DB — requires InquiryAdmin.list_editable=['status'] (AC4)."
    )


# =========================================================================== #
# AC5 — bilingual SR/EN fieldsets (Property) + full SiteSettings fieldsets     #
# =========================================================================== #
def test_property_admin_fieldsets_group_sr_en_descriptions():
    # AC5a: PropertyAdmin fieldsets are non-empty and sort description_sr /
    # description_en into SR/EN-labelled groups.
    modeladmin = _get_modeladmin("properties", "Property")
    assert modeladmin is not None, "Property must be registered in admin."
    fieldsets = modeladmin.get_fieldsets(_dummy_request(), obj=None)
    assert fieldsets, "PropertyAdmin must define non-empty fieldsets (AC5a)."

    sr_groups = [
        opts.get("fields", ())
        for label, opts in fieldsets
        if label and "(SR)" in str(label)
    ]
    en_groups = [
        opts.get("fields", ())
        for label, opts in fieldsets
        if label and "(EN)" in str(label)
    ]
    assert any("description_sr" in _flat(fields) for fields in sr_groups), (
        "a fieldset labelled '(SR)' must contain description_sr (AC5a)."
    )
    assert any("description_en" in _flat(fields) for fields in en_groups), (
        "a fieldset labelled '(EN)' must contain description_en (AC5a)."
    )


def test_property_admin_fieldsets_cover_all_required_fields():
    # AC5a: the union of all fieldset fields must cover every editable Property
    # field (no required field silently dropped from the form), except the
    # deliberately-excluded auto fields.
    #
    # We read the DECLARED `.fieldsets` attribute (not get_fieldsets(), which
    # synthesizes a flat one-group default for an un-grouped admin and would pass
    # trivially in RED). A real 1.4 admin declares an EXPLICIT multi-group
    # fieldsets layout; the minimal 1.3 admin has fieldsets=None -> RED.
    modeladmin = _get_modeladmin("properties", "Property")
    assert modeladmin is not None, "Property must be registered in admin."
    declared = getattr(modeladmin, "fieldsets", None)
    assert declared, (
        "PropertyAdmin must declare an explicit `fieldsets` layout (AC5a) — the "
        "minimal 1.3 admin has none."
    )
    assert len(declared) >= 2, (
        "PropertyAdmin.fieldsets must group fields into multiple labelled sections "
        "(SR/EN + logical groups), not a single flat group (AC5a)."
    )
    covered = _flatten_fieldset_fields(declared)

    excluded = {"id", "slug", "created_at", "updated_at"}
    required = {
        "title", "status", "collection_type", "property_type",
        "location_city", "location_district", "location_address", "show_address",
        "price", "price_on_request", "area_sqm", "area_total_sqm",
        "bedrooms", "bathrooms", "floor", "total_floors", "parking_spaces",
        "year_built", "description_sr", "description_en", "description_fr",
        "features", "hero_image", "floor_plan", "virtual_tour_url",
        "latitude", "longitude", "is_featured", "is_active",
        "meta_title", "meta_description",
    }
    missing = required - covered - excluded
    assert not missing, (
        f"PropertyAdmin.fieldsets must cover all editable Property fields; "
        f"missing from the form: {sorted(missing)} (AC5a)."
    )


def test_sitesettings_admin_fieldsets_cover_all_groups():
    # AC5b: SiteSettingsAdmin.fieldsets cover contact/founder/hero/analytics/SEO,
    # including hero_headline_* (tagline) and hero_cta_text_* (CTA).
    # Read the DECLARED `.fieldsets` (not get_fieldsets(), which would synthesize
    # a flat default for the minimal 1.3 admin and pass trivially in RED).
    modeladmin = _get_modeladmin("core", "SiteSettings")
    assert modeladmin is not None, "SiteSettings must be registered in admin."
    declared = getattr(modeladmin, "fieldsets", None)
    assert declared, (
        "SiteSettingsAdmin must declare an explicit `fieldsets` layout (AC5b) — "
        "the minimal 1.3 singleton admin has none."
    )
    assert len(declared) >= 2, (
        "SiteSettingsAdmin.fieldsets must group fields into multiple labelled "
        "sections (Kontakt/Osnivač/Hero/Analitika/SEO), not a flat group (AC5b)."
    )
    covered = _flatten_fieldset_fields(declared)

    required = {
        # Kontakt
        "phone_primary", "whatsapp_number", "email_primary", "email_inquiries",
        "address",
        # Osnivač
        "founder_name", "founder_title_sr", "founder_title_en", "founder_photo",
        "founder_bio_sr", "founder_bio_en",
        # Hero (tagline + CTA). NB: the hero video is the uploaded `hero_video`
        # FileField (MP4/WebM/MOV) — the legacy `hero_video_url` YouTube field was
        # removed from the form (a watch?v= URL can't be a background <video>).
        "hero_headline_sr", "hero_headline_en", "hero_cta_text_sr",
        "hero_cta_text_en", "hero_image", "hero_video",
        # Analitika
        "google_analytics_id", "facebook_pixel_id",
        # SEO
        "seo_default_title", "seo_default_description",
    }
    missing = required - covered
    assert not missing, (
        f"SiteSettingsAdmin.fieldsets must cover all settings groups; missing: "
        f"{sorted(missing)} (AC5b)."
    )


@pytest.mark.django_db
def test_property_change_form_renders_sr_en_legends(client, django_user_model):
    # AC5c: GET Property change form -> 200 with SR/EN fieldset legends rendered.
    _superuser(django_user_model)
    prop = _make_property(title="Fieldset Test")
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_change", args=[prop.pk])
    assert url is not None, "Property change route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"Property change form must return 200, got {resp.status_code} (AC5c)."
    )
    html = resp.content.decode("utf-8")
    assert "(SR)" in html and "(EN)" in html, (
        "the Property change form must render SR/EN fieldset legends (AC5c)."
    )


def test_sitesettings_admin_groups_sr_en_bilingual_pairs():
    # AC5b / FR27: the SiteSettings change form must visibly mark its bilingual
    # SR/EN content. Analogous to the Property `(SR)`/`(EN)` legend test, BUT:
    # the current SiteSettingsAdmin groups each `_sr`/`_en` pair side-by-side
    # inside a SINGLE row tuple (e.g. ("founder_title_sr","founder_title_en"),
    # ("hero_headline_sr","hero_headline_en")) under topical legends ("Osnivač",
    # "Hero / homepage") rather than under explicit "(SR)"/"(EN)" section labels.
    # Per the batch-fix guidance we assert the grouped PAIRING that actually
    # exists (the SR field and its EN sibling live in the same field-row tuple),
    # which is the structural FR27 grouping; the absence of a literal "(SR)"/"(EN)"
    # label here is reported as a deferred gap rather than forced.
    modeladmin = _get_modeladmin("core", "SiteSettings")
    assert modeladmin is not None, "SiteSettings must be registered in admin."
    declared = getattr(modeladmin, "fieldsets", None)
    assert declared, "SiteSettingsAdmin must declare explicit fieldsets (AC5b)."

    # Collect every multi-field row tuple across all fieldsets.
    row_tuples = []
    for _label, opts in declared:
        for field in opts.get("fields", ()):
            if isinstance(field, (tuple, list)):
                row_tuples.append(tuple(field))

    def _is_sr_en_pair(pair, sr_field, en_field):
        return sr_field in pair and en_field in pair

    assert any(
        _is_sr_en_pair(p, "founder_title_sr", "founder_title_en") for p in row_tuples
    ), (
        "the founder title SR/EN pair must be grouped together in one field row "
        "(founder_title_sr + founder_title_en) — FR27 bilingual pairing (AC5b)."
    )
    assert any(
        _is_sr_en_pair(p, "hero_headline_sr", "hero_headline_en") for p in row_tuples
    ), (
        "the hero headline SR/EN pair must be grouped together in one field row "
        "(hero_headline_sr + hero_headline_en) — FR27 bilingual pairing (AC5b)."
    )


@pytest.mark.django_db
def test_sitesettings_change_form_renders_grouped_inputs(client, django_user_model):
    # AC5c: GET SiteSettings change form -> 200 with inputs for the full settings
    # AND the declared fieldset group legends rendered. NOTE: the minimal 1.3
    # admin already renders every input (Django builds the form from the model),
    # so the inputs alone are NOT a valid RED signal. The 1.4 delta is the GROUPED
    # `fieldsets` layout, so we additionally require the section legends ("Kontakt"
    # + "Hero") to render — these appear only once explicit fieldsets are declared.
    obj = _seed_singleton()
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:core_sitesettings_change", args=[obj.pk])
    assert url is not None, "SiteSettings change route must resolve."
    resp = client.get(url)
    assert resp.status_code == 200, (
        f"SiteSettings change form must return 200, got {resp.status_code} (AC5c)."
    )
    html = resp.content.decode("utf-8")
    for field in ("phone_primary", "hero_headline_sr", "hero_cta_text_sr",
                  "founder_name", "google_analytics_id", "seo_default_title"):
        assert f'name="{field}"' in html, (
            f"the SiteSettings change form must render an input for '{field}' "
            f"(full FR26 settings entry) (AC5c)."
        )
    assert "Kontakt" in html and "Hero" in html, (
        "the SiteSettings change form must render its grouped fieldset legends "
        "(e.g. 'Kontakt', 'Hero') — present only with the 1.4 explicit fieldsets "
        "layout (AC5c)."
    )


# =========================================================================== #
# AC6 — regression: check clean, 1.3 preserved, security baseline              #
# =========================================================================== #
def test_manage_py_check_passes_after_1_4_additions():
    # AC6: `manage.py check` must run clean after adding tinymce/adminsortable2
    # and extending the ModelAdmins.
    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc}")


def test_unfold_still_before_django_admin():
    # AC6: "unfold" must still precede "django.contrib.admin" after the new apps.
    apps = list(settings.INSTALLED_APPS)
    assert "unfold" in apps and "django.contrib.admin" in apps
    assert apps.index("unfold") < apps.index("django.contrib.admin"), (
        "'unfold' must remain BEFORE 'django.contrib.admin' (AC6, 1.3 not "
        "regressed)."
    )


@pytest.mark.django_db
def test_regression_admin_index_still_branded(client, django_user_model):
    # AC6: the 1.3 dashboard is not regressed — admin index still 200 + "Velegrad
    # CMS".
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index must still return 200, got {resp.status_code} (AC6)."
    )
    assert "Velegrad CMS" in resp.content.decode("utf-8"), (
        "the admin index must still be branded 'Velegrad CMS' (1.3 regression, AC6)."
    )


@pytest.mark.django_db
def test_regression_default_admin_path_still_404(client):
    # AC6: /admin/ stays 404 (mount unchanged).
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must remain 404 (AC6, 1.3 not regressed), got {resp.status_code}."
    )


@pytest.mark.django_db
def test_regression_sitesettings_singleton_redirect_preserved(client, django_user_model):
    # AC6: the 1.3 SiteSettings singleton changelist->change redirect still works
    # AFTER the fieldsets extension (singleton rules must NOT be touched).
    obj = _seed_singleton()
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    changelist = _try_reverse("admin:core_sitesettings_changelist")
    assert changelist is not None, "SiteSettings changelist route must resolve."
    resp = client.get(changelist)
    assert resp.status_code == 302, (
        f"SiteSettings changelist must still redirect (302), got {resp.status_code} "
        "(AC6, singleton rule preserved)."
    )
    expected = reverse("admin:core_sitesettings_change", args=[obj.pk])
    assert resp.url == expected, (
        f"SiteSettings changelist must still redirect to the single row's change "
        f"view {expected}, got {resp.url} (AC6)."
    )


@pytest.mark.django_db
def test_regression_sitesettings_no_delete_permission_preserved(rf, django_user_model):
    # AC6: the 1.3 has_delete_permission=False singleton rule is preserved.
    obj = _seed_singleton()
    modeladmin = _get_modeladmin("core", "SiteSettings")
    assert modeladmin is not None, "SiteSettings must be registered."
    request = rf.get("/")
    request.user = _superuser(django_user_model)
    assert modeladmin.has_delete_permission(request, obj) is False, (
        "has_delete_permission must remain False (AC6, singleton rule preserved)."
    )


@pytest.mark.django_db
def test_no_unapplied_migrations_on_sqlite():
    # AC6: tinymce/adminsortable2 introduce no schema-breaking migrations — the
    # migration plan must be fully applied on the SQLite test DB.
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    assert plan == [], (
        f"there must be NO unapplied migrations after adding the 1.4 apps (AC6); "
        f"unapplied plan: {plan}"
    )


@pytest.mark.django_db
def test_duplicate_action_post_without_csrf_is_403(client, django_user_model):
    # AC6 (security/NFR-5): POST to the Property changelist "Dupliraj" action
    # WITHOUT a CSRF token must return 403 (CSRF baseline not bypassed).
    from django.test import Client

    Property = _get_model("properties", "Property")
    _superuser(django_user_model)
    prop = _make_property(title="CSRF Dup")
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:properties_property_changelist")
    assert url is not None, "Property changelist route must resolve."
    resp = csrf_client.post(
        url,
        data={
            "action": "duplicate_selected",
            "_selected_action": [str(prop.pk)],
        },
    )
    assert resp.status_code == 403, (
        "POST to the 'Dupliraj' action without a CSRF token must be 403 "
        f"(CSRF baseline, AC6); got {resp.status_code}."
    )


@pytest.mark.django_db
def test_inquiry_status_change_post_without_csrf_is_403(client, django_user_model):
    # AC6 (security/NFR-5): POST a list_editable status change WITHOUT a CSRF token
    # must return 403.
    from django.test import Client

    _superuser(django_user_model)
    inq = _make_inquiry(name="CSRF", status="new")
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.login(username="admin", password="pass12345")
    url = _try_reverse("admin:inquiries_inquiry_changelist")
    assert url is not None, "Inquiry changelist route must resolve."
    resp = csrf_client.post(
        url,
        data={
            "_save": "Save",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-0-id": str(inq.pk),
            "form-0-status": "closed",
        },
    )
    assert resp.status_code == 403, (
        "POST to the Inquiry changelist (list_editable) without a CSRF token must "
        f"be 403 (CSRF baseline, AC6); got {resp.status_code}."
    )


@pytest.mark.django_db
def test_anonymous_property_changelist_redirects_to_login(client):
    # AC6 (security): anonymous GET on the Property changelist must redirect (302)
    # to admin login — admin not exposed to anonymous users.
    url = _try_reverse("admin:properties_property_changelist")
    assert url is not None, "Property changelist route must resolve."
    resp = client.get(url)
    assert resp.status_code in (302, 403), (
        "anonymous GET on the Property changelist must redirect to login (302) or "
        f"403, got {resp.status_code} (AC6 security)."
    )


@pytest.mark.django_db
def test_anonymous_inquiry_changelist_redirects_to_login(client):
    # AC6 (security): anonymous GET on the Inquiry changelist must redirect (302)
    # to admin login (or 403) — admin not exposed to anonymous users. Mirrors the
    # Property anon test above.
    url = _try_reverse("admin:inquiries_inquiry_changelist")
    assert url is not None, "Inquiry changelist route must resolve."
    resp = client.get(url)
    assert resp.status_code in (302, 403), (
        "anonymous GET on the Inquiry changelist must redirect to login (302) or "
        f"403, got {resp.status_code} (AC6 security)."
    )


# --------------------------------------------------------------------------- #
# Small local helpers used above.                                              #
# --------------------------------------------------------------------------- #
def _flat(fields):
    out = set()
    for f in fields:
        if isinstance(f, (tuple, list)):
            out.update(f)
        else:
            out.add(f)
    return out


def _dummy_request():
    """A minimal request object good enough for ModelAdmin.get_fieldsets()."""
    from django.test import RequestFactory
    from django.contrib.auth.models import AnonymousUser
    req = RequestFactory().get("/")
    req.user = AnonymousUser()
    return req

