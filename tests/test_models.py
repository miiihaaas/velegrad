"""
RED-phase contract tests for Story 1.2 — "CMS modeli i migracije".

These tests define the CONTRACT for the 6 Django CMS models (the projektni
zadatak §5.2 source of truth + Story 1.2 Dev Notes for Django-mandatory params).
They are written BEFORE the models exist, so EVERY test in this module MUST FAIL
or ERROR until the developer implements the models + migrations:

  * Introspection tests fail with ImportError / ModuleNotFoundError (the app
    `models.py` files are still empty) or AttributeError (field/choice absent).
  * @pytest.mark.django_db behavior tests fail/error because the model classes
    cannot be imported and no tables exist.

Design rules (mirrors the Story 1.1 harness):
  * Model imports happen INSIDE helpers/test bodies so an absent model surfaces
    as a per-test failure with a clear message, not a collection-time crash.
  * DB-touching tests are marked @pytest.mark.django_db (pytest-django is active
    via `DJANGO_SETTINGS_MODULE = config.settings.test`, an in-memory SQLite DB).
  * Pure introspection tests need no DB.
  * Each test maps to an acceptance criterion via an `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    1-2-cms-modeli-i-migracije-interface-contract.md
"""
import importlib
import uuid

import pytest
from django.db import models as dj_models


# --------------------------------------------------------------------------- #
# Import helpers — raise (=> the calling test FAILS) while models are absent.   #
# --------------------------------------------------------------------------- #
def _get_model(app_label, class_name):
    """Import and return ``<app>.models.<ClassName>``.

    Raises ImportError/ModuleNotFoundError (empty models.py) or AttributeError
    (model not defined) during the RED phase, failing the calling test cleanly.
    """
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


def _field(model, name):
    """Return the model's concrete field named ``name`` (raises FieldDoesNotExist)."""
    return model._meta.get_field(name)


def _choice_values(field):
    """Return the ordered list of stored choice values for a field."""
    return [value for value, _label in (field.choices or [])]


def _make_property(model, **overrides):
    """Create a Property supplying ALL required non-null scalar fields.

    The §5.2 / Story 1.2 contract defines ``Property``'s many IntegerField and
    DecimalField columns (bedrooms, bathrooms, floor, total_floors,
    parking_spaces, area_sqm, area_total_sqm) and the choice CharFields
    (status, collection_type, property_type, location_city/district) WITHOUT a
    DB default. So ``Property.objects.create(title=...)`` would raise
    IntegrityError (NOT NULL constraint) on SQLite *and* Postgres even with a
    perfectly correct model — failing for a reason unrelated to the behavior
    under test (slug / localized / __str__). This helper provides valid values
    for those required columns so the behavior tests exercise ONLY their target
    contract; callers override just the fields they care about.
    """
    defaults = dict(
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
    return model.objects.create(**defaults)


# Canonical model registry for parametrized existence tests.
MODEL_REGISTRY = [
    ("core", "SiteSettings"),
    ("properties", "Property"),
    ("properties", "PropertyImage"),
    ("properties", "PropertyFeature"),
    ("inquiries", "Inquiry"),
    ("pages", "Page"),
]


# =========================================================================== #
# AC13 — Model existence + correct app_label (all 6 models)                    #
# =========================================================================== #
@pytest.mark.parametrize("app_label,class_name", MODEL_REGISTRY)
def test_model_exists_and_is_registered_with_right_app(app_label, class_name):
    # AC13: each of the 6 models is importable, is a Django Model, and is
    # registered under the EXPECTED app_label (enforces arch §2 app boundaries).
    model = _get_model(app_label, class_name)
    assert issubclass(model, dj_models.Model), (
        f"{class_name} must be a django.db.models.Model subclass"
    )
    assert model._meta.app_label == app_label, (
        f"{class_name} must live in app '{app_label}', got '{model._meta.app_label}'"
    )


# =========================================================================== #
# AC1 — SiteSettings fields (core)                                             #
# =========================================================================== #
def test_sitesettings_has_all_required_fields():
    # AC1: SiteSettings exposes exactly the §5.2 field set (names present).
    model = _get_model("core", "SiteSettings")
    expected = {
        "phone_primary", "whatsapp_number", "email_primary", "email_inquiries",
        "address", "founder_name", "founder_title_sr", "founder_title_en",
        "founder_photo", "founder_bio_sr", "founder_bio_en", "hero_headline_sr",
        "hero_headline_en", "hero_cta_text_sr", "hero_cta_text_en", "hero_image",
        "hero_video_url", "google_analytics_id", "facebook_pixel_id",
        "seo_default_title", "seo_default_description",
    }
    present = {f.name for f in model._meta.get_fields()}
    missing = expected - present
    assert not missing, f"SiteSettings missing fields: {sorted(missing)}"


def test_sitesettings_field_types_and_maxlengths():
    # AC1: key SiteSettings field types + CharField max_length values (Dev Tabela 2).
    model = _get_model("core", "SiteSettings")
    assert isinstance(_field(model, "email_primary"), dj_models.EmailField)
    assert isinstance(_field(model, "email_inquiries"), dj_models.EmailField)
    assert isinstance(_field(model, "address"), dj_models.TextField)
    assert isinstance(_field(model, "hero_video_url"), dj_models.URLField)
    assert isinstance(_field(model, "founder_photo"), dj_models.ImageField)
    assert isinstance(_field(model, "hero_image"), dj_models.ImageField)
    expected_lengths = {
        "phone_primary": 30, "whatsapp_number": 20, "founder_name": 150,
        "founder_title_sr": 150, "founder_title_en": 150, "hero_headline_sr": 200,
        "hero_headline_en": 200, "hero_cta_text_sr": 80, "hero_cta_text_en": 80,
        "google_analytics_id": 50, "facebook_pixel_id": 50, "seo_default_title": 70,
    }
    for name, length in expected_lengths.items():
        assert _field(model, name).max_length == length, (
            f"SiteSettings.{name}.max_length must be {length}"
        )


# =========================================================================== #
# AC3 — Property fields, types, params (properties)                            #
# =========================================================================== #
def test_property_has_all_required_fields():
    # AC3: Property exposes the §5.2 field set (names present).
    model = _get_model("properties", "Property")
    expected = {
        "id", "title", "slug", "status", "collection_type", "property_type",
        "location_city", "location_district", "location_address", "show_address",
        "price", "price_on_request", "area_sqm", "area_total_sqm", "bedrooms",
        "bathrooms", "floor", "total_floors", "parking_spaces", "year_built",
        "description_sr", "description_en", "description_fr", "features",
        "hero_image", "floor_plan", "virtual_tour_url", "latitude", "longitude",
        "is_featured", "is_active", "created_at", "updated_at", "meta_title",
        "meta_description",
    }
    present = {f.name for f in model._meta.get_fields()}
    missing = expected - present
    assert not missing, f"Property missing fields: {sorted(missing)}"


def test_property_charfield_maxlengths():
    # AC3: Property CharField/SlugField max_length values (Dev Tabela 2).
    model = _get_model("properties", "Property")
    expected_lengths = {
        "title": 200, "slug": 255, "status": 20, "collection_type": 20,
        "property_type": 20, "location_city": 100, "location_district": 100,
        "location_address": 255, "meta_title": 70,
    }
    for name, length in expected_lengths.items():
        assert _field(model, name).max_length == length, (
            f"Property.{name}.max_length must be {length}"
        )


def test_property_decimalfield_precision():
    # AC3: DecimalField max_digits/decimal_places (Dev Tabela 1).
    model = _get_model("properties", "Property")
    expected = {
        "price": (12, 2),
        "area_sqm": (8, 2),
        "area_total_sqm": (8, 2),
        "latitude": (9, 6),
        "longitude": (9, 6),
    }
    for name, (digits, places) in expected.items():
        f = _field(model, name)
        assert isinstance(f, dj_models.DecimalField), f"Property.{name} must be Decimal"
        assert (f.max_digits, f.decimal_places) == (digits, places), (
            f"Property.{name} precision must be ({digits},{places}), "
            f"got ({f.max_digits},{f.decimal_places})"
        )


def test_property_price_is_nullable():
    # AC3: price is null=True (for price_on_request).
    model = _get_model("properties", "Property")
    assert _field(model, "price").null is True, "Property.price must be null=True"


def test_property_media_and_url_field_types():
    # AC3: media/url field types per §5.2.
    model = _get_model("properties", "Property")
    assert isinstance(_field(model, "hero_image"), dj_models.ImageField)
    assert isinstance(_field(model, "floor_plan"), dj_models.FileField)
    assert isinstance(_field(model, "virtual_tour_url"), dj_models.URLField)
    assert isinstance(_field(model, "meta_description"), dj_models.TextField)
    assert isinstance(_field(model, "created_at"), dj_models.DateTimeField)
    assert isinstance(_field(model, "updated_at"), dj_models.DateTimeField)


def test_property_boolean_defaults():
    # AC3 (Dev Tabela 3): boolean defaults — is_active True; the rest False.
    model = _get_model("properties", "Property")
    assert _field(model, "is_active").default is True, "Property.is_active default True"
    assert _field(model, "is_featured").default is False, "is_featured default False"
    assert _field(model, "show_address").default is False, "show_address default False"
    assert _field(model, "price_on_request").default is False, (
        "price_on_request default False"
    )


def test_property_meta_ordering_present():
    # AC3: Property has a sensible Meta.ordering (e.g. ["-created_at"]).
    model = _get_model("properties", "Property")
    assert model._meta.ordering, "Property.Meta.ordering must be set"
    assert "-created_at" in model._meta.ordering, (
        f"Property.Meta.ordering should include '-created_at', got {model._meta.ordering}"
    )


# =========================================================================== #
# AC4 — PropertyImage fields + relation + ordering                            #
# =========================================================================== #
def test_propertyimage_fields_and_defaults():
    # AC4: PropertyImage field set, caption max_length, is_hero default, ordering.
    model = _get_model("properties", "PropertyImage")
    present = {f.name for f in model._meta.get_fields()}
    for name in ("property", "image", "caption", "order", "is_hero"):
        assert name in present, f"PropertyImage missing field '{name}'"
    assert isinstance(_field(model, "image"), dj_models.ImageField)
    assert _field(model, "caption").max_length == 255, "caption max_length 255"
    assert _field(model, "is_hero").default is False, "is_hero default False"
    assert list(model._meta.ordering) == ["order"], (
        f"PropertyImage.Meta.ordering must be ['order'], got {model._meta.ordering}"
    )


# =========================================================================== #
# AC5 — PropertyFeature fields + choices                                       #
# =========================================================================== #
def test_propertyfeature_fields_and_maxlengths():
    # AC5: PropertyFeature field set + max_lengths.
    model = _get_model("properties", "PropertyFeature")
    present = {f.name for f in model._meta.get_fields()}
    for name in ("name_sr", "name_en", "icon", "category"):
        assert name in present, f"PropertyFeature missing field '{name}'"
    assert _field(model, "name_sr").max_length == 100
    assert _field(model, "name_en").max_length == 100
    assert _field(model, "icon").max_length == 50
    assert _field(model, "category").max_length == 20


# =========================================================================== #
# AC6 — Inquiry fields, types, defaults                                        #
# =========================================================================== #
def test_inquiry_has_all_required_fields():
    # AC6: Inquiry exposes the §5.2 field set.
    model = _get_model("inquiries", "Inquiry")
    expected = {
        "id", "property", "inquiry_type", "name", "email", "phone", "message",
        "preferred_language", "budget_range", "property_type_wanted", "status",
        "notes", "created_at", "ip_address",
    }
    present = {f.name for f in model._meta.get_fields()}
    missing = expected - present
    assert not missing, f"Inquiry missing fields: {sorted(missing)}"


def test_inquiry_field_types_and_maxlengths():
    # AC6: Inquiry field types + CharField max_lengths.
    model = _get_model("inquiries", "Inquiry")
    assert isinstance(_field(model, "email"), dj_models.EmailField)
    assert isinstance(_field(model, "message"), dj_models.TextField)
    assert isinstance(_field(model, "notes"), dj_models.TextField)
    assert isinstance(_field(model, "ip_address"), dj_models.GenericIPAddressField)
    assert isinstance(_field(model, "created_at"), dj_models.DateTimeField)
    expected_lengths = {
        "inquiry_type": 20, "name": 150, "phone": 30, "preferred_language": 5,
        "budget_range": 100, "property_type_wanted": 100, "status": 20,
    }
    for name, length in expected_lengths.items():
        assert _field(model, name).max_length == length, (
            f"Inquiry.{name}.max_length must be {length}"
        )


def test_inquiry_status_default_is_new():
    # AC6: Inquiry.status default is 'new'.
    model = _get_model("inquiries", "Inquiry")
    assert _field(model, "status").default == "new", "Inquiry.status default 'new'"


def test_inquiry_ip_address_nullable():
    # AC6: ip_address is null=True/blank=True (anti-spam, optional).
    model = _get_model("inquiries", "Inquiry")
    f = _field(model, "ip_address")
    assert f.null is True and f.blank is True, "ip_address must be null+blank"


def test_inquiry_meta_ordering():
    # AC6: Inquiry ordering newest-first.
    model = _get_model("inquiries", "Inquiry")
    assert list(model._meta.ordering) == ["-created_at"], (
        f"Inquiry.Meta.ordering must be ['-created_at'], got {model._meta.ordering}"
    )


# =========================================================================== #
# AC7 — Page fields, slug unique, default                                      #
# =========================================================================== #
def test_page_fields_types_and_maxlengths():
    # AC7: Page field set, types, max_lengths, is_active default.
    model = _get_model("pages", "Page")
    present = {f.name for f in model._meta.get_fields()}
    for name in ("slug", "title_sr", "title_en", "content_sr", "content_en",
                 "meta_title", "meta_description", "is_active"):
        assert name in present, f"Page missing field '{name}'"
    assert _field(model, "slug").max_length == 100
    assert _field(model, "title_sr").max_length == 200
    assert _field(model, "title_en").max_length == 200
    assert _field(model, "meta_title").max_length == 70
    assert isinstance(_field(model, "content_sr"), dj_models.TextField)
    assert isinstance(_field(model, "content_en"), dj_models.TextField)
    assert isinstance(_field(model, "meta_description"), dj_models.TextField)
    assert _field(model, "is_active").default is True, "Page.is_active default True"


# =========================================================================== #
# AC13 — Choices: exact counts + values                                       #
# =========================================================================== #
def test_property_status_choices():
    # AC13: Property.status has exactly 5 choices with exact values.
    model = _get_model("properties", "Property")
    values = _choice_values(_field(model, "status"))
    assert values == ["for_sale", "for_rent", "price_on_request", "sold", "rented"], (
        f"Property.status choices wrong/incomplete: {values}"
    )


def test_property_collection_type_choices():
    # AC13: Property.collection_type has exactly 3 choices.
    model = _get_model("properties", "Property")
    values = _choice_values(_field(model, "collection_type"))
    assert values == ["signature", "private", "off_market"], (
        f"Property.collection_type choices wrong: {values}"
    )


def test_property_type_choices():
    # AC13: Property.property_type has exactly 6 choices.
    model = _get_model("properties", "Property")
    values = _choice_values(_field(model, "property_type"))
    assert values == ["stan", "kuca", "penthouse", "vila", "komercijalno", "zemljiste"], (
        f"Property.property_type choices wrong: {values}"
    )


def test_inquiry_type_choices():
    # AC13: Inquiry.inquiry_type has exactly 4 choices.
    model = _get_model("inquiries", "Inquiry")
    values = _choice_values(_field(model, "inquiry_type"))
    assert values == ["viewing", "consultation", "private_collection", "general"], (
        f"Inquiry.inquiry_type choices wrong: {values}"
    )


def test_inquiry_status_choices():
    # AC13: Inquiry.status has exactly 4 choices.
    model = _get_model("inquiries", "Inquiry")
    values = _choice_values(_field(model, "status"))
    assert values == ["new", "contacted", "in_progress", "closed"], (
        f"Inquiry.status choices wrong: {values}"
    )


def test_inquiry_preferred_language_choices():
    # AC13: Inquiry.preferred_language choices are sr/en/fr.
    model = _get_model("inquiries", "Inquiry")
    values = _choice_values(_field(model, "preferred_language"))
    assert values == ["sr", "en", "fr"], (
        f"Inquiry.preferred_language choices wrong: {values}"
    )


def test_propertyfeature_category_choices():
    # AC13: PropertyFeature.category has exactly 4 choices.
    model = _get_model("properties", "PropertyFeature")
    values = _choice_values(_field(model, "category"))
    assert values == ["interior", "exterior", "building", "legal"], (
        f"PropertyFeature.category choices wrong: {values}"
    )


# =========================================================================== #
# AC13 — Relations (FK on_delete + related_name, M2M)                         #
# =========================================================================== #
def test_propertyimage_fk_cascade_related_name_images():
    # AC13: PropertyImage.property -> FK Property, on_delete=CASCADE, related_name 'images'.
    image = _get_model("properties", "PropertyImage")
    prop = _get_model("properties", "Property")
    f = _field(image, "property")
    assert isinstance(f, dj_models.ForeignKey), "PropertyImage.property must be FK"
    assert f.related_model is prop, "PropertyImage.property must point to Property"
    assert f.remote_field.on_delete is dj_models.CASCADE, "on_delete must be CASCADE"
    assert f.remote_field.related_name == "images", "related_name must be 'images'"


def test_inquiry_fk_set_null_and_nullable():
    # AC13: Inquiry.property -> FK Property, on_delete=SET_NULL, null=True.
    inquiry = _get_model("inquiries", "Inquiry")
    prop = _get_model("properties", "Property")
    f = _field(inquiry, "property")
    assert isinstance(f, dj_models.ForeignKey), "Inquiry.property must be FK"
    assert f.related_model is prop, "Inquiry.property must point to Property"
    assert f.remote_field.on_delete is dj_models.SET_NULL, "on_delete must be SET_NULL"
    assert f.null is True, "Inquiry.property must be null=True"


def test_property_features_m2m_to_propertyfeature():
    # AC13: Property.features -> M2M to PropertyFeature.
    prop = _get_model("properties", "Property")
    feature = _get_model("properties", "PropertyFeature")
    f = _field(prop, "features")
    assert isinstance(f, dj_models.ManyToManyField), "Property.features must be M2M"
    assert f.related_model is feature, "Property.features must point to PropertyFeature"


# =========================================================================== #
# AC13 — UUID primary keys                                                     #
# =========================================================================== #
@pytest.mark.parametrize("app_label,class_name", [
    ("properties", "Property"),
    ("inquiries", "Inquiry"),
])
def test_uuid_primary_key(app_label, class_name):
    # AC13: Property and Inquiry use a UUIDField pk, default=uuid4, editable=False.
    model = _get_model(app_label, class_name)
    pk = model._meta.pk
    assert isinstance(pk, dj_models.UUIDField), f"{class_name} pk must be UUIDField"
    assert pk.default is uuid.uuid4, f"{class_name} pk default must be uuid.uuid4"
    assert pk.editable is False, f"{class_name} pk must be editable=False"


# =========================================================================== #
# AC13 — Unique constraints on slugs                                           #
# =========================================================================== #
def test_page_slug_unique():
    # AC13: Page.slug is unique=True.
    model = _get_model("pages", "Page")
    assert _field(model, "slug").unique is True, "Page.slug must be unique=True"


def test_property_slug_unique():
    # AC13/AC3: Property.slug is unique=True.
    model = _get_model("properties", "Property")
    assert _field(model, "slug").unique is True, "Property.slug must be unique=True"


# =========================================================================== #
# AC2 — SiteSettings singleton behavior (DB)                                   #
# =========================================================================== #
@pytest.mark.django_db
def test_sitesettings_singleton_enforced():
    # AC2: creating/saving a second SiteSettings must NOT create a 2nd row.
    model = _get_model("core", "SiteSettings")
    model.objects.all().delete()
    model.objects.create()
    model.objects.create()
    assert model.objects.count() == 1, (
        f"SiteSettings must be a singleton (<=1 row), got {model.objects.count()}"
    )


@pytest.mark.django_db
def test_sitesettings_load_returns_single_row():
    # AC2: load() returns the one canonical instance.
    model = _get_model("core", "SiteSettings")
    model.objects.all().delete()
    instance = model.load()
    assert instance is not None, "SiteSettings.load() must return an instance"
    assert model.objects.count() == 1, "SiteSettings.load() must leave exactly one row"
    again = model.load()
    assert again.pk == instance.pk, "SiteSettings.load() must return the same row"


# =========================================================================== #
# AC9 — Property.slug auto-generation (collision-safe, DB)                     #
# =========================================================================== #
@pytest.mark.django_db
def test_property_slug_autogenerates_from_title():
    # AC9: blank slug auto-generates from title via slugify on save.
    model = _get_model("properties", "Property")
    p = _make_property(model, title="Luksuzni Stan Centar")
    assert p.slug, "Property.slug must auto-generate when blank"
    assert p.slug.startswith("luksuzni-stan-centar"), (
        f"slug should be slugified from title, got {p.slug!r}"
    )


@pytest.mark.django_db
def test_property_slug_collision_safe_same_title():
    # AC9: two Properties with the SAME title => DIFFERENT slugs, no IntegrityError.
    model = _get_model("properties", "Property")
    p1 = _make_property(model, title="Vila More")
    p2 = _make_property(model, title="Vila More")
    assert p1.slug != p2.slug, (
        f"Colliding titles must yield distinct slugs, got {p1.slug!r} == {p2.slug!r}"
    )


# =========================================================================== #
# AC8 — localized() helper + fallback contract (DB)                            #
# =========================================================================== #
@pytest.mark.django_db
def test_localized_returns_active_language_value():
    # AC8: localized() returns the value for the active language.
    from django.utils import translation
    model = _get_model("properties", "Property")
    p = _make_property(
        model, title="X", description_sr="Opis", description_en="Description",
    )
    with translation.override("en"):
        assert p.localized("description") == "Description"
    with translation.override("sr"):
        assert p.localized("description") == "Opis"


@pytest.mark.django_db
def test_localized_fallback_when_get_language_none():
    # AC8(i): get_language() -> None must NOT raise and must fall back to _sr.
    from django.utils import translation
    model = _get_model("properties", "Property")
    p = _make_property(
        model, title="Y", description_sr="Srpski opis", description_en="English",
    )
    translation.deactivate_all()  # get_language() now returns None
    try:
        assert p.localized("description") == "Srpski opis"
    finally:
        translation.activate("sr")


@pytest.mark.django_db
def test_localized_fallback_unsupported_language():
    # AC8(ii): unsupported language (de) must not raise and falls back to _sr.
    from django.utils import translation
    model = _get_model("properties", "Property")
    p = _make_property(
        model, title="Z", description_sr="Srpski", description_en="English",
    )
    with translation.override("de"):
        assert p.localized("description") == "Srpski"


@pytest.mark.django_db
def test_localized_fallback_empty_target_value():
    # AC8(iii): active 'en' but empty description_en => fall back to _sr value.
    from django.utils import translation
    model = _get_model("properties", "Property")
    p = _make_property(
        model, title="W", description_sr="Samo srpski", description_en="",
    )
    with translation.override("en"):
        assert p.localized("description") == "Samo srpski"


# =========================================================================== #
# AC13 — __str__ returns sensible values (DB)                                  #
# =========================================================================== #
@pytest.mark.django_db
def test_str_methods_sensible():
    # AC13: __str__ returns meaningful strings, not the default object repr.
    Property = _get_model("properties", "Property")
    Feature = _get_model("properties", "PropertyFeature")
    Inquiry = _get_model("inquiries", "Inquiry")
    Page = _get_model("pages", "Page")

    p = _make_property(Property, title="Penthouse Dorcol")
    assert str(p) == "Penthouse Dorcol", "Property.__str__ should return title"

    feat = Feature.objects.create(name_sr="Bazen", name_en="Pool", category="exterior")
    assert str(feat) == "Bazen", "PropertyFeature.__str__ should return name_sr"

    inq = Inquiry.objects.create(
        name="Marko", email="m@example.com", inquiry_type="viewing",
        phone="+381601234567", message="Zainteresovan sam.",
        preferred_language="sr",
    )
    assert "Marko" in str(inq), "Inquiry.__str__ should include the name"

    page = Page.objects.create(slug="about", title_sr="O nama", title_en="About")
    assert str(page) in ("about", "O nama"), "Page.__str__ should be slug or title_sr"


# =========================================================================== #
# AC10 — makemigrations --check --dry-run reports NO changes                   #
# =========================================================================== #
@pytest.mark.django_db
def test_makemigrations_check_no_pending_changes():
    # AC10: with models implemented + migrations generated, makemigrations
    # --check --dry-run must report NO pending changes (exit cleanly). FAILS in
    # RED because the models exist (in tests' contract) but no 0001_initial.py
    # migrations are generated yet, so changes ARE detected => SystemExit(1).
    # Marked @django_db because makemigrations reads the migration recorder table.
    #
    # Import every contract model first: in RED this raises ModuleNotFoundError
    # (empty models.py) so the test FAILS — there are no models to migrate yet, and
    # an empty-app makemigrations would otherwise spuriously report "no changes".
    # In GREEN, with models defined and 0001_initial.py generated, --check passes.
    for app_label, class_name in MODEL_REGISTRY:
        _get_model(app_label, class_name)

    from django.core.management import call_command
    from django.core.management.base import SystemCheckError

    try:
        call_command(
            "makemigrations", "--check", "--dry-run", verbosity=0,
        )
    except SystemExit as exc:
        # --check exits non-zero when there are unmade migrations.
        pytest.fail(f"makemigrations --check reported pending changes (exit {exc.code})")
    except SystemCheckError as exc:  # pragma: no cover - surfaces system check errors
        pytest.fail(f"makemigrations raised a system check error: {exc}")


# =========================================================================== #
# AC11 — manage.py check reports no errors                                     #
# =========================================================================== #
def test_django_system_check_passes():
    # AC11: `check` reports no E-level errors with all 6 models defined.
    #
    # We first import every contract model: in RED this raises ModuleNotFoundError
    # (empty models.py) so the test FAILS for the right reason — there is nothing
    # to system-check yet. In GREEN the imports succeed and `check` must then pass
    # with no E-level errors (FK/M2M resolve, choices/Meta valid, apps load).
    for app_label, class_name in MODEL_REGISTRY:
        _get_model(app_label, class_name)

    from django.core.management import call_command
    from django.core.management.base import SystemCheckError

    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc}")


# =========================================================================== #
# AC2 — RichTextField is MANDATED to be tinymce.models.HTMLField              #
# =========================================================================== #
# Story 1.2 AC2 + Dev Notes ("RichTextField realizacija — MANDAT, ne
# preporuka") require EVERY RichText field (founder_bio_*, description_*,
# content_*) to be realized as `tinymce.models.HTMLField`, consistently across
# all models. HTMLField subclasses TextField, so the type-checks elsewhere
# (isinstance TextField) would also pass for a plain TextField — this test
# closes that loophole by asserting the field is specifically an HTMLField.
RICHTEXT_FIELDS = [
    ("core", "SiteSettings", "founder_bio_sr"),
    ("core", "SiteSettings", "founder_bio_en"),
    ("properties", "Property", "description_sr"),
    ("properties", "Property", "description_en"),
    ("properties", "Property", "description_fr"),
    ("pages", "Page", "content_sr"),
    ("pages", "Page", "content_en"),
]


@pytest.mark.parametrize("app_label,class_name,field_name", RICHTEXT_FIELDS)
def test_richtext_fields_are_tinymce_htmlfield(app_label, class_name, field_name):
    # AC2: RichText fields MUST be tinymce.models.HTMLField (not a bare TextField).
    # In RED this fails with ModuleNotFoundError (empty models.py). In GREEN the
    # field must be an HTMLField instance. `tinymce` is imported INSIDE the body
    # so the right-reason RED failure (models absent) is surfaced first.
    from tinymce.models import HTMLField

    model = _get_model(app_label, class_name)
    field = _field(model, field_name)
    assert isinstance(field, HTMLField), (
        f"{class_name}.{field_name} must be tinymce.models.HTMLField "
        f"(AC2 mandate), got {type(field).__name__}"
    )


# =========================================================================== #
# AC8 — localized() behavior on SiteSettings, PropertyFeature, Page (batch)   #
# =========================================================================== #
# Property.localized() is already behavior-tested above. These close the gap   #
# for the other dual-language models, exercising the same three fallback paths #
# (None / unsupported-lang / empty target => _sr) per the §7 contract.         #
@pytest.mark.django_db
def test_localized_sitesettings_fallback_paths():
    # AC8: SiteSettings.localized() returns active-lang value with _sr fallback.
    from django.utils import translation
    model = _get_model("core", "SiteSettings")
    model.objects.all().delete()
    s = model.objects.create(
        founder_title_sr="Osnivač", founder_title_en="Founder",
    )
    with translation.override("en"):
        assert s.localized("founder_title") == "Founder"
    with translation.override("sr"):
        assert s.localized("founder_title") == "Osnivač"
    # (i) get_language() is None -> _sr
    translation.deactivate_all()
    try:
        assert s.localized("founder_title") == "Osnivač"
    finally:
        translation.activate("sr")
    # (ii) unsupported language -> _sr
    with translation.override("de"):
        assert s.localized("founder_title") == "Osnivač"
    # (iii) active lang present but target empty -> _sr
    s.founder_title_en = ""
    with translation.override("en"):
        assert s.localized("founder_title") == "Osnivač"


@pytest.mark.django_db
def test_localized_propertyfeature_fallback_paths():
    # AC8: PropertyFeature.localized("name") with _sr fallback.
    from django.utils import translation
    model = _get_model("properties", "PropertyFeature")
    f = model.objects.create(name_sr="Bazen", name_en="Pool", category="exterior")
    with translation.override("en"):
        assert f.localized("name") == "Pool"
    with translation.override("sr"):
        assert f.localized("name") == "Bazen"
    translation.deactivate_all()
    try:
        assert f.localized("name") == "Bazen"  # get_language() None -> _sr
    finally:
        translation.activate("sr")
    with translation.override("de"):
        assert f.localized("name") == "Bazen"  # unsupported -> _sr
    f.name_en = ""
    with translation.override("en"):
        assert f.localized("name") == "Bazen"  # empty target -> _sr


@pytest.mark.django_db
def test_localized_page_fallback_paths():
    # AC8: Page.localized("title") with _sr fallback.
    from django.utils import translation
    model = _get_model("pages", "Page")
    p = model.objects.create(
        slug="o-nama", title_sr="O nama", title_en="About",
    )
    with translation.override("en"):
        assert p.localized("title") == "About"
    with translation.override("sr"):
        assert p.localized("title") == "O nama"
    translation.deactivate_all()
    try:
        assert p.localized("title") == "O nama"  # get_language() None -> _sr
    finally:
        translation.activate("sr")
    with translation.override("de"):
        assert p.localized("title") == "O nama"  # unsupported -> _sr
    p.title_en = ""
    with translation.override("en"):
        assert p.localized("title") == "O nama"  # empty target -> _sr


# =========================================================================== #
# AC9 — Property.slug: manual slug respected + stability on re-save            #
# =========================================================================== #
@pytest.mark.django_db
def test_property_manual_slug_respected():
    # AC9: a manually supplied slug must NOT be overwritten by auto-generation.
    model = _get_model("properties", "Property")
    p = _make_property(model, title="X", slug="moj-slug")
    assert p.slug == "moj-slug", (
        f"manual slug must be respected, got {p.slug!r}"
    )


@pytest.mark.django_db
def test_property_slug_stable_on_resave():
    # AC9: saving an existing Property again must NOT re-slugify (slug stable).
    model = _get_model("properties", "Property")
    p = _make_property(model, title="Stabilan Slug")
    original = p.slug
    p.title = "Promenjen Naslov"  # title changes, but slug already set
    p.save()
    p.refresh_from_db()
    assert p.slug == original, (
        f"slug must be stable across re-saves, was {original!r}, now {p.slug!r}"
    )


# =========================================================================== #
# AC13 — __str__ for SiteSettings and PropertyImage                            #
# =========================================================================== #
@pytest.mark.django_db
def test_str_sitesettings_and_propertyimage():
    # AC13: SiteSettings + PropertyImage __str__ are sensible (not default repr).
    SiteSettings = _get_model("core", "SiteSettings")
    Property = _get_model("properties", "Property")
    PropertyImage = _get_model("properties", "PropertyImage")

    SiteSettings.objects.all().delete()
    s = SiteSettings.load()
    assert str(s) == "Podešavanja sajta", (
        f"SiteSettings.__str__ should be a site label, got {str(s)!r}"
    )

    p = _make_property(Property, title="Penthouse Dorcol")
    img = PropertyImage.objects.create(property=p, order=3)
    assert str(img) == f"{p} #3", (
        f"PropertyImage.__str__ should be f'{{property}} #{{order}}', got {str(img)!r}"
    )


# =========================================================================== #
# AC3 — Property indexes cover is_active/collection_type/status (no double idx) #
# =========================================================================== #
def test_property_meta_indexes_present_and_not_double_indexed():
    # AC3: Meta.indexes must cover is_active, collection_type, status; and those
    # fields must NOT also carry field-level db_index (avoids double-indexing).
    model = _get_model("properties", "Property")
    indexed = set()
    for index in model._meta.indexes:
        if len(index.fields) == 1:
            indexed.add(index.fields[0])
    for name in ("is_active", "collection_type", "status"):
        assert name in indexed, (
            f"Property.Meta.indexes must include an index on '{name}', got {indexed}"
        )
        assert _field(model, name).db_index is False, (
            f"Property.{name} must NOT also set field-level db_index "
            f"(double-index); rely on Meta.indexes only"
        )


# =========================================================================== #
# A4 — Property.features M2M explicit related_name='properties'                #
# =========================================================================== #
def test_property_features_related_name_properties():
    # Property.features reverse accessor must be 'properties' (not default).
    prop = _get_model("properties", "Property")
    f = _field(prop, "features")
    assert f.remote_field.related_name == "properties", (
        f"Property.features related_name must be 'properties', "
        f"got {f.remote_field.related_name!r}"
    )


# =========================================================================== #
# A5 — Inquiry.created_at has field-level db_index (drives ordering/admin)     #
# =========================================================================== #
def test_inquiry_created_at_db_index():
    # Inquiry.created_at must be db_index=True (drives Meta.ordering desc + admin).
    model = _get_model("inquiries", "Inquiry")
    assert _field(model, "created_at").db_index is True, (
        "Inquiry.created_at must set db_index=True"
    )
