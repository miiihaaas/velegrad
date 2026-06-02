---
story-id: 1-2-cms-modeli-i-migracije
title: "CMS modeli i migracije — Interface Contract (TEA RED phase)"
phase: red
author: TEA (Test Architect)
created: 2026-06-02
source-of-truth: "docs/Velegrad Estate - Projektni zadatak.docx.md §5.2"
references:
  - _bmad-output/implementation-artifacts/1-2-cms-modeli-i-migracije.md  # AC1–AC13
  - _bmad-output/planning-artifacts/architecture.md  # §1.3 i18n, §2 app granice
status: red-contract
---

# Story 1.2 — Interface Contract (the executable contract the Dev must satisfy)

This document is the machine-checkable CONTRACT for the 6 CMS models. The RED-phase
tests in `tests/test_models.py` encode it. Until the Dev implements the models, the
new 1.2 tests MUST FAIL (ImportError / AttributeError / assertion). The Story 1.1
suite in `tests/test_project_setup.py` MUST keep passing.

> Source of truth for fields/types/choices is the projektni zadatak §5.2; the
> Django-mandatory parameters (max_length, max_digits, defaults) are fixed by Story
> 1.2 Dev Notes (Tabela 1/2/3) and reproduced below. Do NOT invent or rename fields.

---

## 0. Test-environment decision — `config/settings/test.py`

No local PostgreSQL is available. `config/settings/test.py` inherits from
`config.settings.base` and overrides **only** `DATABASES` to in-memory SQLite:

```python
from .base import *  # noqa
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
```

`pytest.ini` sets `DJANGO_SETTINGS_MODULE = config.settings.test`, activating
pytest-django for the whole suite. Model tests touching the DB use
`@pytest.mark.django_db`. UUID/Decimal fields behave identically on SQLite and
Postgres; real Postgres 16 `migrate` is DEFERRED to pre-deploy (AC12).

TinyMCE note (AC2): `RichTextField` is realized as `tinymce.models.HTMLField`
(a `TextField` subclass). `'tinymce'` need NOT be in `INSTALLED_APPS` for
makemigrations/check/migrate; only `from tinymce.models import HTMLField` is needed.
This is a MANDATE, not a preference: every RichText field (`founder_bio_*`,
`description_*`, `content_*`) is asserted to be specifically an `HTMLField`
instance (test `test_richtext_fields_are_tinymce_htmlfield`), closing the
isinstance(TextField) loophole. `django-tinymce` and `Pillow` (for `ImageField`)
must be installed in the venv — both are declared in `requirements/base.txt`.

---

## 1. `core.SiteSettings` (singleton) — AC1, AC2, AC8

app_label: `core` · `__str__` => a sensible site label (e.g. "Podešavanja sajta").
`Meta.verbose_name` / `verbose_name_plural` in Serbian.

| Field | Type | Params |
| :-- | :-- | :-- |
| `phone_primary` | CharField | max_length=30 |
| `whatsapp_number` | CharField | max_length=20 |
| `email_primary` | EmailField | (no max_length; Django default 254) |
| `email_inquiries` | EmailField | (no max_length) |
| `address` | TextField | (no max_length) |
| `founder_name` | CharField | max_length=150 |
| `founder_title_sr` | CharField | max_length=150 |
| `founder_title_en` | CharField | max_length=150 |
| `founder_photo` | ImageField | upload_to e.g. `site/` |
| `founder_bio_sr` | RichTextField (HTMLField) | (no max_length) |
| `founder_bio_en` | RichTextField (HTMLField) | (no max_length) |
| `hero_headline_sr` | CharField | max_length=200 |
| `hero_headline_en` | CharField | max_length=200 |
| `hero_cta_text_sr` | CharField | max_length=80 |
| `hero_cta_text_en` | CharField | max_length=80 |
| `hero_image` | ImageField | upload_to e.g. `site/` |
| `hero_video_url` | URLField | blank=True (optional) |
| `google_analytics_id` | CharField | max_length=50 |
| `facebook_pixel_id` | CharField | max_length=50 |
| `seo_default_title` | CharField | max_length=70 |
| `seo_default_description` | TextField | (no max_length) |

**Singleton API (AC2):** exactly one row.
- `save()` pins the pk (e.g. `self.pk = 1`) so a second `create()`/`save()` does NOT
  add a 2nd row (it overwrites the single row). `SiteSettings.objects.count() <= 1`
  always.
- `delete()` is a no-op / blocked (do not allow removing the singleton row).
- Class method `load()` returns the single instance (get-or-create on pk=1).

**`localized(base)` helper** on dual-language bases: `founder_title`, `founder_bio`,
`hero_headline`, `hero_cta_text` (see §7).

---

## 2. `properties.Property` — AC3, AC8, AC9

app_label: `properties` · `__str__` => `title` · `Meta.ordering = ["-created_at"]`,
Serbian verbose_name. Indexes on `is_active`, `collection_type`, `status` (db_index or
Meta.indexes). `slug` already indexed via SlugField.

| Field | Type | Params |
| :-- | :-- | :-- |
| `id` | UUIDField | primary_key=True, default=uuid.uuid4, editable=False |
| `title` | CharField | max_length=200 |
| `slug` | SlugField | max_length=255, unique=True (auto-gen, collision-safe; §9) |
| `status` | CharField | max_length=20, choices (5) |
| `collection_type` | CharField | max_length=20, choices (3) |
| `property_type` | CharField | max_length=20, choices (6) |
| `location_city` | CharField | max_length=100 |
| `location_district` | CharField | max_length=100 |
| `location_address` | CharField | max_length=255, blank=True |
| `show_address` | BooleanField | default=False |
| `price` | DecimalField | max_digits=12, decimal_places=2, null=True, blank=True |
| `price_on_request` | BooleanField | default=False |
| `area_sqm` | DecimalField | max_digits=8, decimal_places=2 |
| `area_total_sqm` | DecimalField | max_digits=8, decimal_places=2 |
| `bedrooms` | IntegerField |  |
| `bathrooms` | IntegerField |  |
| `floor` | IntegerField |  |
| `total_floors` | IntegerField |  |
| `parking_spaces` | IntegerField |  |
| `year_built` | IntegerField | null=True, blank=True (optional) |
| `description_sr` | RichTextField (HTMLField) | (no max_length) |
| `description_en` | RichTextField (HTMLField) | (no max_length) |
| `description_fr` | RichTextField (HTMLField) | blank=True (out of translation scope) |
| `features` | ManyToManyField | -> `PropertyFeature`, blank=True, related_name=`properties` |
| `hero_image` | ImageField | upload_to e.g. `properties/hero/` |
| `floor_plan` | FileField | upload_to e.g. `properties/floorplans/`, blank=True |
| `virtual_tour_url` | URLField | blank=True |
| `latitude` | DecimalField | max_digits=9, decimal_places=6, null=True, blank=True |
| `longitude` | DecimalField | max_digits=9, decimal_places=6, null=True, blank=True |
| `is_featured` | BooleanField | default=False |
| `is_active` | BooleanField | default=True |
| `created_at` | DateTimeField | auto_now_add=True |
| `updated_at` | DateTimeField | auto_now=True |
| `meta_title` | CharField | max_length=70 |
| `meta_description` | TextField | (no max_length) |

**Choices (exact value sets):**
- `status` (5): `for_sale`, `for_rent`, `price_on_request`, `sold`, `rented`
- `collection_type` (3): `signature`, `private`, `off_market`
- `property_type` (6): `stan`, `kuca`, `penthouse`, `vila`, `komercijalno`, `zemljiste`

`localized("description")` helper (§7).

---

## 3. `properties.PropertyImage` — AC4

app_label: `properties` · `Meta.ordering = ["order"]` · `__str__` sensible (e.g.
`f"{property} #{order}"`).

| Field | Type | Params |
| :-- | :-- | :-- |
| `id` | AutoField | (default pk) |
| `property` | ForeignKey | -> `Property`, on_delete=CASCADE, related_name=`images` |
| `image` | ImageField | upload_to e.g. `properties/gallery/` |
| `caption` | CharField | max_length=255, blank=True |
| `order` | IntegerField | (display order) |
| `is_hero` | BooleanField | default=False |

---

## 4. `properties.PropertyFeature` — AC5, AC8

app_label: `properties` · `__str__` => `name_sr` · `Meta.ordering =
["category", "name_sr"]`, Serbian verbose_name.

| Field | Type | Params |
| :-- | :-- | :-- |
| `id` | AutoField | (default pk) |
| `name_sr` | CharField | max_length=100 |
| `name_en` | CharField | max_length=100 |
| `icon` | CharField | max_length=50 |
| `category` | CharField | max_length=20, choices (4) |

**Choices:** `category` (4): `interior`, `exterior`, `building`, `legal`.

`localized("name")` helper (§7).

---

## 5. `inquiries.Inquiry` — AC6

app_label: `inquiries` · `Meta.ordering = ["-created_at"]`, Serbian verbose_name ·
`__str__` sensible (e.g. `f"{name} — {inquiry_type}"`).

| Field | Type | Params |
| :-- | :-- | :-- |
| `id` | UUIDField | primary_key=True, default=uuid.uuid4, editable=False |
| `property` | ForeignKey | -> `Property`, null=True, blank=True, on_delete=SET_NULL |
| `inquiry_type` | CharField | max_length=20, choices (4) |
| `name` | CharField | max_length=150 |
| `email` | EmailField | (no max_length) |
| `phone` | CharField | max_length=30 |
| `message` | TextField | (no max_length) |
| `preferred_language` | CharField | max_length=5, choices (3) |
| `budget_range` | CharField | max_length=100, blank=True |
| `property_type_wanted` | CharField | max_length=100, blank=True |
| `status` | CharField | max_length=20, choices (4), default=`new` |
| `notes` | TextField | blank=True (no max_length) |
| `created_at` | DateTimeField | auto_now_add=True |
| `ip_address` | GenericIPAddressField | null=True, blank=True |

**Choices:**
- `inquiry_type` (4): `viewing`, `consultation`, `private_collection`, `general`
- `status` (4): `new`, `contacted`, `in_progress`, `closed` — default `new`
- `preferred_language` (3): `sr`, `en`, `fr`

---

## 6. `pages.Page` — AC7, AC8

app_label: `pages` · `__str__` => `slug` (or `title_sr`) · Serbian verbose_name.
Default `AutoField` pk (no explicit `id` in §5.2).

| Field | Type | Params |
| :-- | :-- | :-- |
| `slug` | CharField | max_length=100, unique=True |
| `title_sr` | CharField | max_length=200 |
| `title_en` | CharField | max_length=200 |
| `content_sr` | RichTextField (HTMLField) | (no max_length) |
| `content_en` | RichTextField (HTMLField) | (no max_length) |
| `meta_title` | CharField | max_length=70 |
| `meta_description` | TextField | (no max_length) |
| `is_active` | BooleanField | default=True |

`localized("title")` and `localized("content")` helpers (§7).

---

## 7. `localized(base)` helper — AC8 (signature + fallback contract)

Signature: `def localized(self, base: str) -> str`. Reference implementation:

```python
from django.utils.translation import get_language

def localized(self, base):
    lang = (get_language() or "sr")[:2]
    return getattr(self, f"{base}_{lang}", "") or getattr(self, f"{base}_sr", "")
```

Contract (all three paths must be testably true):
1. `get_language()` is `None` (management commands / i18n inactive) => no `TypeError`;
   returns the `_sr` value.
2. Unsupported/unknown language (e.g. `de`) => returns the `_sr` value (no exception).
3. Active language present but the target `_<lang>` value is empty/blank => falls back
   to the `_sr` value.

Present on every dual-language model: `Property.localized("description")`,
`PropertyFeature.localized("name")`, `Page.localized("title"|"content")`,
`SiteSettings.localized("founder_title"|"founder_bio"|"hero_headline"|"hero_cta_text")`.
`django-modeltranslation` is NOT used. `description_fr` stays in the model but is out
of translation scope.

**Implementation note (refactor):** `localized()` is provided by a single abstract
mixin `core.models.LocalizedMixin` (`Meta.abstract = True`, so it adds NO table and
NO migration). `SiteSettings`, `Property`, `PropertyFeature` and `Page` inherit it
(`class X(LocalizedMixin, models.Model)`). `properties`/`pages` import the mixin from
`core` (core has no reverse dependency → no circular import). The method body /
fallback contract is unchanged.

---

## 8. `Property.slug` auto-generation — AC9 (collision-safe)

- On `save()`, when `slug` is empty it is generated from `title` via `slugify`.
- A manually supplied slug is respected (not overwritten).
- Because `slug` is `unique=True`, generation is collision-safe: on a clash with an
  existing slug, append a numeric suffix (`-2`, `-3`, …) until unique.
- Testable: two `Property` instances with the SAME `title` => two DIFFERENT slugs and
  NO `IntegrityError`.

---

## 9. SiteSettings singleton API — AC2

- `save()` pins pk (e.g. `pk=1`) => second create/save does not add a second row.
- `load()` classmethod returns the single instance.
- `delete()` blocked/no-op. Invariant: `SiteSettings.objects.count() <= 1`.

---

## 10. Migrations / check — AC10, AC11

- One `0001_initial.py` per app (`core`, `properties`, `inquiries`, `pages`).
- `makemigrations --check --dry-run` reports NO changes.
- `manage.py check` reports no E-level errors.
- (These tests run via `call_command(..., settings=config.settings.test)`; they FAIL
  in RED because models/migrations are absent.)
