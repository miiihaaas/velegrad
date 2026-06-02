---
story-id: 1-3-brendiran-admin-i-dashboard
artifact: interface-contract
phase: RED (tests written, feature NOT implemented)
author: TEA (Test Architect)
created: 2026-06-02
django-unfold-installed: "0.95.0"
---

# Interface Contract — Story 1.3 "Brendiran admin i dashboard"

This contract is the machine-readable target the GREEN-phase Dev must satisfy so
that the RED tests in `tests/test_admin_dashboard.py` turn green. Every name,
path and shape below is asserted (directly or indirectly) by a test. Read it as
the *minimum* interface — the Dev may add more (e.g. richer Unfold keys) as long
as nothing here changes.

> Installed package for the harness: **`django-unfold==0.95.0`** (verified via
> `pip show django-unfold`). AC11 requires a *bounded* pin in
> `requirements/base.txt`; a pin such as `django-unfold>=0.95,<0.96` satisfies
> the version-range test (installed 0.95.0 is inside it). The Dev owns the exact
> bound — the test only asserts a lower **and** upper bound exist and that the
> installed version sits inside the declared range.

---

## 1. INSTALLED_APPS ordering (AC1)

In `config/settings/base.py`:

- `"unfold"` MUST appear in `INSTALLED_APPS`.
- `INSTALLED_APPS.index("unfold")` **<** `INSTALLED_APPS.index("django.contrib.admin")`.
- Only the core `"unfold"` app is required for the 1.3 (dashboard-only) scope.
  `unfold.contrib.*` sub-apps are NOT required by these tests (they are 1.4).
- `python manage.py check` (via `call_command("check")`) MUST pass with no error.

## 2. Test-render prerequisites (Dev Note (a)/(b))

Already true in the current `base.py`, asserted to lock them in:

- `TEMPLATES[0]["OPTIONS"]["context_processors"]` includes
  `"django.template.context_processors.request"`.
- `"django.contrib.staticfiles"` is in `INSTALLED_APPS` and `STATIC_URL` is set
  (truthy).

## 3. UNFOLD settings dict (AC2, AC3)

In `config/settings/base.py`, a module-level dict named `UNFOLD`:

```python
UNFOLD = {
    "SITE_TITLE": "Velegrad CMS",
    "SITE_HEADER": "Velegrad CMS",
    # optional: "SITE_SUBHEADER": "...",
    "DASHBOARD_CALLBACK": "core.admin.dashboard_callback",   # dotted path (see §5)
    "COLORS": {
        "primary": {
            "50":  "...",
            "100": "...",
            "200": "...",
            "300": "...",
            "400": "...",
            "500": "74 82 64",     # Deep Olive #4A5240 — brand center
            "600": "74 82 64",     # (500 and/or 600 carry the brand RGB-channel)
            "700": "...",
            "800": "...",
            "900": "...",
            "950": "...",
        },
        # A secondary/accent scale (key name is Dev's choice — e.g. "secondary"
        # or "base") MUST contain the Champagne RGB-channel "201 169 110"
        # somewhere in its shade values.
    },
}
```

Asserted contract:

- `settings.UNFOLD` is a dict.
- `UNFOLD["SITE_TITLE"]` and `UNFOLD["SITE_HEADER"]` both equal/contain
  `"Velegrad CMS"`.
- `UNFOLD["DASHBOARD_CALLBACK"]` is a dotted string path that imports to a
  callable.
- `UNFOLD["COLORS"]["primary"]` is a dict whose keys cover the full shade scale
  `{"50","100","200","300","400","500","600","700","800","900","950"}` and whose
  values are **space-separated RGB-channel strings** (three integers `0–255`,
  e.g. `"74 82 64"`), **NOT hex** (no `#`).
- The Deep Olive brand value `"74 82 64"` appears at the center of the primary
  scale (key `"500"` and/or `"600"`).
- The Champagne brand value `"201 169 110"` appears somewhere in the `COLORS`
  config (in a secondary/accent scale).

> Hex → RGB-channel: `#4A5240` = `74 82 64`, `#C9A96E` = `201 169 110`.

## 4. SITE_HEADER branding render (AC3, AC7)

- A logged-in superuser GET on the resolved admin index returns HTTP 200 and the
  rendered HTML contains `"Velegrad CMS"` and does NOT contain the default
  `"Django administration"`.
- GET on the resolved `ADMIN_URL` login page (anonymous) returns HTTP 200 and the
  HTML contains the `SITE_HEADER` text (`"Velegrad CMS"`).
- GET `/admin/` returns HTTP 404 (mount unchanged from 1.1).

The admin path used by tests is derived the same way the app does it:
`settings.ADMIN_URL` (already normalized, no slashes) → path is
`f"/{settings.ADMIN_URL}/"`.

## 5. dashboard_callback contract (AC4, AC5)

Dotted path `core.admin.dashboard_callback` (the value of
`UNFOLD["DASHBOARD_CALLBACK"]`). Signature:

```python
def dashboard_callback(request, context):
    ...
    return context
```

It MUST be defensive (no exception on an empty DB — it runs on every admin index
GET) and MUST set these context keys:

| Context key            | Value                                                              |
| :--------------------- | :---------------------------------------------------------------- |
| active count           | `Property.objects.filter(is_active=True).count()`                 |
| new-inquiries count    | `Inquiry.objects.filter(status="new").count()`                    |
| featured count         | `Property.objects.filter(is_featured=True).count()`               |
| add-property quick URL | `reverse("admin:properties_property_add")`                        |
| inquiries quick URL    | `reverse("admin:inquiries_inquiry_changelist")`                   |
| latest inquiries       | `Inquiry.objects.order_by("-created_at")[:5]`                      |

The tests do NOT import the callback or assert key names directly (to keep RED
failures reading as "feature absent" rather than import/KeyError noise). They
assert on the **rendered admin index HTML** produced via the template override
(§6). The Dev picks the exact context key names; only the *rendered output* is
contracted.

## 6. Dashboard index template override (AC9)

Deliverable: `templates/admin/index.html` (overrides the Django/Unfold admin
index that Unfold renders) OR an equivalent Unfold dashboard template override
per the pinned-version docs. `BASE_DIR / "templates"` is already in
`TEMPLATES["DIRS"]`. The template MUST read the callback context keys and render:

- The three metric numbers (active / new / featured) — with seed data
  `3 / 2 / 1`, those three digit strings appear in the HTML.
- Two quick-action anchors whose `href` equals the two `reverse()` URLs.
- A table of the latest ≤5 inquiries (name / type / status / date), or an
  empty-state message when there are none.

## 7. Models registered in admin (AC10, AC8)

In `core/admin.py` (and/or app `admin.py` modules):

- `Property` (app `properties`) registered → `reverse("admin:properties_property_add")`
  and `reverse("admin:properties_property_changelist")` resolve (no
  `NoReverseMatch`).
- `Inquiry` (app `inquiries`) registered →
  `reverse("admin:inquiries_inquiry_changelist")` and
  `reverse("admin:inquiries_inquiry_add")` resolve.
- `django.contrib.admin.site._registry` contains both `Property` and `Inquiry`.
- Logged-in superuser GET on the Property and Inquiry changelists → HTTP 200.
- Registration is MINIMAL (no rich list_display/filters — that is 1.4).

## 8. SiteSettings singleton admin (AC6)

`SiteSettings` (app `core`) registered as an Unfold `ModelAdmin` whose model
admin instance satisfies:

- `modeladmin.has_add_permission(request)` returns `False` when a `SiteSettings`
  row exists (`return not SiteSettings.objects.exists()`), `True` on an empty DB.
- `modeladmin.has_delete_permission(request)` returns `False` (always).
- GET on the `SiteSettings` changelist (`admin:core_sitesettings_changelist`) for
  a superuser, with the singleton row present, returns HTTP 302 redirecting to
  the change view of that single row
  (`admin:core_sitesettings_change` with the row pk).

## 9. requirements pin (AC11)

`requirements/base.txt` pins `django-unfold` with BOTH a lower and an upper
bound (e.g. `django-unfold>=0.95,<0.96`), not a bare `django-unfold`. The
installed version (`0.95.0`) must satisfy the declared range.
