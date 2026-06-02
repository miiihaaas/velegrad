---
story-id: 1-4-admin-upravljanje-nekretninama-upitima-i-podesavanjima
artifact: interface-contract
phase: RED (tests written, feature NOT implemented)
author: TEA (Test Architect)
created: 2026-06-02
django-tinymce-installed: "5.0.0"
django-admin-sortable2-installed: "NOT INSTALLED (must pip install in T1)"
---

# Interface Contract — Story 1.4 "Admin upravljanje nekretninama, upitima i podešavanjima"

This contract is the machine-readable target the GREEN-phase Dev must satisfy so
that the RED tests in `tests/test_admin_management.py` turn green. Every name,
path and shape below is asserted (directly or indirectly) by a test. Read it as
the *minimum* interface — the Dev may add more as long as nothing here changes
and the Story 1.3 deliverables (Unfold theme, dashboard, singleton rules) are
NOT regressed.

> Harness snapshot (verified via `pip show`):
> - `django-tinymce==5.0.0` is INSTALLED. Its `tinymce.urls` has
>   `app_name = None` → **no `tinymce:` namespace**; route names are
>   `tinymce-compressor` / `tinymce-filebrowser` / `tinymce-linklist`
>   (there is NO `tinymce-js`). Tests therefore do NOT use
>   `reverse("tinymce:tinymce-js")`.
> - `django-admin-sortable2` is **NOT installed** in the active `.venv`. T1
>   must `pip install django-admin-sortable2` AND bounded-pin it in
>   `requirements/base.txt`. Until installed, `import adminsortable2` raises
>   `ImportError`; the RED tests guard this import so collection does not crash
>   and the failure reads as "feature absent".

---

## 1. Settings changes (AC1, AC2, AC4, AC6)

In `config/settings/base.py`, `INSTALLED_APPS` MUST add (after `"unfold"`,
above/around `"django.contrib.admin"` — `"unfold"` MUST stay before
`"django.contrib.admin"`):

- `"adminsortable2"`  — required so the sortable JS/CSS statics load (AC1).
- `"tinymce"`         — activates the `TinyMCE` widget for `HTMLField` (AC2).
- *(optional)* `"unfold.contrib.filters"` — only if the Dev uses an Unfold
  range/select filter for the Inquiry `created_at` date filter. The built-in
  `("created_at", admin.DateFieldListFilter)` does NOT require it. The tests do
  NOT mandate this sub-app.
- *(optional)* `"unfold.contrib.forms"` — only if needed to style the WYSIWYG.
  Not mandated by tests.

`python manage.py check` MUST still pass (no E-level errors). `"unfold"` MUST
remain before `"django.contrib.admin"`.

## 2. requirements pins (AC1, AC6 — Story 1.3 AC11 convention)

`requirements/base.txt` MUST replace the bare lines with **bounded** pins
(lower AND upper bound, not a bare name):

- `django-admin-sortable2>=X,<Y` — bound around the version the Dev installs
  (e.g. `>=2.2,<2.3`). The installed version must sit inside the declared range.
- `django-tinymce>=5.0,<5.1` — bound around installed `5.0.0`.

Both packages MUST be importable in the active venv (`import adminsortable2`,
`import tinymce` raise no `ImportError`).

## 3. URL wiring (AC2)

In `config/urls.py`, add the TinyMCE URLs include:

```python
path("tinymce/", include("tinymce.urls")),
```

Verification (URLConf-level, NOT a view GET): `reverse("tinymce-compressor")`
and `reverse("tinymce-filebrowser")` MUST resolve once the include is wired.
Tests do NOT assert a `tinymce:` namespace (there is none in 5.0.0 —
`app_name = None`; the real route names are `tinymce-compressor` /
`tinymce-filebrowser` / `tinymce-linklist`).

> RED-phase note (CORRECTED — verified against THIS Unfold admin):
> 1. **Do NOT GET the tinymce asset views.** `/tinymce/compressor/` 500s
>    (renders a missing `tinymce/tiny_mce_gzip.js` template) and
>    `/tinymce/filebrowser/` 500s (reverses the optional `filebrowser` app).
>    With `DEBUG=True` the Django test client RE-RAISES these, so a GET would
>    ERROR after implementation. The mount is therefore verified with
>    `reverse(...)` (route resolvable) — NOT by hitting the view.
> 2. **The `class="tinymce"` widget marker IS a valid RED signal here.** Unfold's
>    `ModelAdmin` maps `models.TextField → UnfoldAdminTextareaWidget` via
>    `formfield_overrides`, and `HTMLField` subclasses `TextField`, so the
>    minimal 1.3 admin renders `description_*` / `founder_bio_*` as a PLAIN Unfold
>    textarea — `class="tinymce"` is ABSENT today (verified). The 1.4 delta is
>    wiring the TinyMCE widget explicitly on the admin (e.g.
>    `formfield_overrides = {HTMLField: {"widget": TinyMCE}}`, or
>    `unfold.contrib.forms`' `WysiwygWidget`) PLUS `"tinymce"` in
>    `INSTALLED_APPS`. Only then does `class="tinymce"` appear.
> 3. **Do NOT assert a served `/static/...` asset.** In this project the test
>    client routes through `config.urls`, which mounts NO staticfiles view, so
>    EVERY `/static/...` path 404s under the test client — even stock
>    `admin`/`unfold` assets. Such an assertion is unsatisfiable; the AC2 render
>    tests rely on the `class="tinymce"` marker + the `reverse()` mount check.

## 4. `properties/admin.py` — PropertyImageInline (AC1, FR24)

A sortable inline class:

```python
from adminsortable2.admin import SortableInlineAdminMixin
from unfold.admin import TabularInline  # or StackedInline

class PropertyImageInline(SortableInlineAdminMixin, TabularInline):
    model = PropertyImage
    fields = ["image", "caption", "is_hero", "order"]   # order may be hidden/handle
    ordering = ["order"]
    extra = 0
```

Asserted contract:

- `PropertyImageInline` is a **subclass of**
  `adminsortable2.admin.SortableInlineAdminMixin` (Python-level `issubclass`).
  A plain (non-sortable) inline MUST NOT satisfy this.
- `PropertyImageInline.model is PropertyImage`.
- `PropertyImageInline` is present in `PropertyAdmin.inlines`.
- The rendered `Property` add AND change form (superuser GET) is HTTP 200 and
  contains the `PropertyImage` inline formset (a stable baseline marker such as
  the `images-...` management-form prefix / inline block).
- The rendered `Property` change form contains a **sortable-specific marker**
  injected only by an active sortable mechanism — specifically the package's
  static media path `adminsortable2/` (its reorder JS/CSS, emitted via the
  sortable inline's `Media`). NOTE: the bare word `sortable` is NOT used as the
  marker because it can appear elsewhere (e.g. inside a Property title/slug);
  `adminsortable2/` appears only when the sortable inline Media is loaded.

The parent `PropertyAdmin` may need to be sortable-aware per the pinned-version
docs (e.g. inherit `adminsortable2.admin.SortableAdminBase`); the Dev applies
whatever the pinned version requires so the sortable marker renders.

## 5. `properties/admin.py` — PropertyAdmin (AC1, AC3, AC5)

```python
@admin.register(Property)
class PropertyAdmin(SortableAdminBase, ModelAdmin):   # base order per pinned docs
    inlines = [PropertyImageInline]
    actions = ["duplicate_selected"]
    fieldsets = (...)          # see §8

    def duplicate_selected(self, request, queryset): ...
    duplicate_selected.short_description = "Dupliraj"
```

Asserted contract:

- `"duplicate_selected"` is in `PropertyAdmin.actions`.
- `PropertyAdmin.inlines` contains `PropertyImageInline`.
- `PropertyAdmin.get_fieldsets(request, obj=None)` (or `.fieldsets`) is non-empty
  and groups `description_sr` / `description_en` under SR / EN labelled groups
  (see §8 for full-field coverage).

## 6. The "Dupliraj" action — signature & behavior (AC3a)

`PropertyAdmin.duplicate_selected(self, request, queryset)` — for each selected
`Property`:

- Copies **all scalar fields** (incl. status/collection/type/location/price/
  area/etc.).
- Copies the M2M `features` (after the new row is saved).
- **Resets `slug=""`** so `Property.save()` (1.2 AC9) auto-generates a
  collision-safe slug.
- Sets a NEW UUID pk (`obj.pk = None; obj.id = None` → `save()` mints a fresh
  `uuid4` on INSERT).
- Prefixes `title` (e.g. `"Kopija — " + title`) so duplicates are visibly
  distinct.
- Does **NOT** copy `PropertyImage` rows (the new property has 0 images).
- Leaves the original property untouched.
- Runs **without `IntegrityError`**, even when duplicating an already-duplicated
  property (title grows `"Kopija — Kopija — ..."`; slug reset + collision-safe
  save covers any slug clash).

## 7. Preview authorization helper (AC3b)

Concrete location/signature (Epic 3's `PropertyDetailView` will import this):

```python
# properties/preview.py
def can_preview(request, obj) -> bool:
    """True iff the property is publicly visible OR a staff user requested a
    preview. Used by the Epic 3 detail view for gating."""
    if getattr(obj, "is_active", False):
        return True
    user = getattr(request, "user", None)
    return bool(
        user is not None
        and user.is_authenticated
        and user.is_staff
        and request.GET.get("preview") == "1"
    )
```

Boolean matrix asserted:

| obj.is_active | user                | preview | result |
| :------------ | :------------------ | :------ | :----- |
| True          | anonymous           | (any)   | True   |
| True          | staff               | (any)   | True   |
| False         | anonymous           | "0"/missing | False |
| False         | anonymous           | "1"     | False  |
| False         | staff               | "0"/missing | False |
| False         | staff               | "1"     | True   |
| False         | authenticated non-staff | "1" | False  |

The Property change form for an `is_active=False` property MUST render a
link/button whose URL (or a documented placeholder string) contains `?preview=1`.
Tests do NOT depend on `reverse()` resolving a future Epic 3 detail route.

## 8. `properties/admin.py` — fieldsets (AC5a)

`PropertyAdmin.fieldsets` groups fields with explicit SR / EN language labels:

- A group whose label contains `(SR)` includes `description_sr`.
- A group whose label contains `(EN)` includes `description_en`.
- `description_fr` lives in its own / collapsible group (out of MVP focus).
- The **union of all fields across all fieldsets** MUST cover every editable
  `Property` field, except deliberately excluded auto fields
  (`slug`, `created_at`, `updated_at`, and the auto `id`). So none of:
  `title, status, collection_type, property_type, location_city,
  location_district, location_address, show_address, price, price_on_request,
  area_sqm, area_total_sqm, bedrooms, bathrooms, floor, total_floors,
  parking_spaces, year_built, description_sr, description_en, description_fr,
  features, hero_image, floor_plan, virtual_tour_url, latitude, longitude,
  is_featured, is_active, meta_title, meta_description` is silently dropped.

## 9. `inquiries/admin.py` — InquiryAdmin (AC4, FR25)

```python
@admin.register(Inquiry)
class InquiryAdmin(ModelAdmin):
    list_display = ["name", "status", "inquiry_type", "created_at"]  # status NOT first
    list_editable = ["status"]
    list_filter = ["status", ("created_at", admin.DateFieldListFilter)]
    search_fields = ["name", "email", "phone"]
```

Asserted contract:

- `"status"` is in `list_filter`.
- A date filter for `created_at` is present in `list_filter` (either
  `"created_at"` or a `("created_at", <Filter>)` tuple).
- If `list_editable` is used and contains `"status"`, then in `list_display`
  `status` is NOT the first column (index ≥ 1). The Inquiry changelist GET
  (superuser) MUST return HTTP 200 (this is what surfaces the
  `admin.E124`/runtime `list_editable` vs first-column conflict — `check` does
  NOT catch it reliably).
- `search_fields` includes `name`, `email`, `phone`.
- The changelist HTML renders status filter UI (`?status=new` / `?status=closed`
  filter links).
- Changing an inquiry's `status` via the admin (POST to change form OR
  list_editable POST) persists to the DB.

## 10. `core/admin.py` — SiteSettingsAdmin fieldsets (AC5b, FR26/FR27)

EXTENDS the 1.3 singleton admin with `fieldsets`. **DO NOT change** the 1.3
singleton rules: `has_add_permission` (False when a row exists),
`has_delete_permission` (always False), `changelist_view` (redirect to the
single row's change view).

`SiteSettingsAdmin.fieldsets` MUST cover all groups:

- **Kontakt:** `phone_primary, whatsapp_number, email_primary, email_inquiries,
  address`
- **Osnivač:** `founder_name, founder_title_sr, founder_title_en, founder_photo,
  founder_bio_sr, founder_bio_en`
- **Hero/homepage:** `hero_headline_sr, hero_headline_en` (tagline),
  `hero_cta_text_sr, hero_cta_text_en` (CTA), `hero_image, hero_video_url`
- **Analitika:** `google_analytics_id, facebook_pixel_id`
- **SEO:** `seo_default_title, seo_default_description`

The `SiteSettings` change form (superuser GET) returns HTTP 200 and renders
inputs for all of the above plus SR/EN labelled groups.

## 11. Regression — Story 1.3 preserved (AC6)

- `python manage.py check` clean.
- No unapplied migrations on the SQLite test DB (`tinymce`/`adminsortable2`
  introduce no schema-breaking migrations).
- Admin index (superuser GET) → 200 and contains `"Velegrad CMS"`.
- GET `/admin/` → 404.
- `SiteSettings` singleton rules unchanged (no add when row exists, no delete,
  changelist → change redirect).
- `reverse("admin:properties_property_add")` and
  `reverse("admin:inquiries_inquiry_changelist")` resolve.
- `"tinymce"` and `"adminsortable2"` in `INSTALLED_APPS`; `"unfold"` still before
  `"django.contrib.admin"`.

## 12. Security baseline (AC6 optional, NFR-5)

- POST to the "Dupliraj" admin action endpoint **without** a valid CSRF token →
  HTTP 403.
- POST to the Inquiry changelist (list_editable status change) **without** a
  valid CSRF token → HTTP 403.
- Anonymous GET on the Property changelist / Inquiry changelist redirects to the
  admin login (302) — admin is not exposed to anonymous users.
