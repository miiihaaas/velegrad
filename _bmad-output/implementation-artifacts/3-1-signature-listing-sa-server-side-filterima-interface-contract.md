# Interface Contract — Story 3.1: Signature listing sa server-side filterima

> RED-faza ugovor (TDD). Definiše TAČNE potpise/imena koje `tests/test_property_listing.py`
> asertuje PRE implementacije. Dev (GREEN faza) MORA ispoštovati ova imena/ponašanja.
> Izvor istine za AC = story `3-1-signature-listing-sa-server-side-filterima.md` (T7 + LOCKED odluke).

---

## 1. `properties/forms.py` → `PropertyFilterForm`

`class PropertyFilterForm(forms.Form)` — Django forms, **BEZ `django-filter`**. SVA polja `required=False`.

| Polje | Tip | Ograničenja | Mapiranje u view-u |
|---|---|---|---|
| `location` | `CharField` | `required=False` | `location_district__icontains` (i/ili `location_city__icontains`) |
| `property_type` | `ChoiceField` | `choices=[("","")] + Property.PROPERTY_TYPE_CHOICES`, `required=False` | `property_type=` (egzaktno) |
| `status` | `ChoiceField` | `choices` SAMO `for_sale`/`for_rent`/`price_on_request` (MODEL vrednosti), `required=False` | `status=` (egzaktno) |
| `price_min` | `DecimalField` | `min_value=0`, `required=False` | `price__gte=` |
| `price_max` | `DecimalField` | `min_value=0`, `required=False` | `price__lte=` |
| `bedrooms` | `IntegerField` | `min_value=0`, `required=False` | `bedrooms__gte=` (minimum-semantika; „5+" → 5) |
| `keyword` | `CharField` | `max_length=100`, `required=False` | `title__icontains=` (SAMO title) |

- **`clean()` (LOCKED inverzni opseg):** ako su data OBA `price_min` i `price_max` i `price_min > price_max`
  → postavi `cleaned_data["price_min"] = cleaned_data["price_max"] = None` (NE diže `ValidationError`).
- **Bezbednost:** forma je jedina kapija. View NIKAD ne čita sirov `request.GET` u ORM. Filtri se grade
  ISKLJUČIVO iz `form.cleaned_data` (`cleaned_data.get(...)`), samo neprazne vrednosti.
- Garbage ulaz (`price_min=abc`, `bedrooms=xyz`, `status=hack`, `bedrooms=-1`, `price_min=-5`) → to polje
  nevalidno → `cleaned_data` ga izostavlja → filter se preskače. Forma NE diže izuzetak (view radi 200).

## 2. `properties/views.py` → `PropertyListView`

`ListView` (`model=Property`, `template_name="properties.html"`, `context_object_name="properties"`) ili funkcijski view.

**Bazni queryset (UVEK):**
```python
Property.objects.filter(
    collection_type="signature",
    is_active=True,
    status__in=["for_sale", "for_rent", "price_on_request"],
)
```
(ekvivalentno `.exclude(status__in=["sold", "rented"])`). Isključuje `private`/`off_market`/`is_active=False`/`sold`/`rented`.

**Redosled primene (KRITIČNO):**
1. bazni queryset (gore);
2. `form = PropertyFilterForm(request.GET)`; ako `form.is_valid()`, primeni filtre iz `cleaned_data`
   (svaki opcioni, kumulativni AND): `location`, `property_type`, `status`, `price_min`/`price_max`,
   `bedrooms` (`__gte`), `keyword` (`title__icontains`);
3. **`[:12]` slice — POSLE svih filtera** (filtriraj pa odseci). **NE `paginate_by`.**

**Kontekst:** `form` (bound, za zadržavanje vrednosti) + `properties` (lista, max 12).

**Nevalidna forma** → preskoči nevalidne filtre po polju, renderuj bazni listing (200, nikad 500).

## 3. Ruta — `config/urls.py`

`path("properties/", PropertyListView.as_view(), name="properties")` (direktno ili preko `properties/urls.py` include).
- `reverse("properties") == "/properties/"`.
- NE registruje se detalj ruta `/properties/<slug>/` (to je 3.2). Postojeće rute (`home`/`ADMIN_URL`/`tinymce/`) i `handler404` se NE diraju.

## 4. `templates/properties.html`

- `{% extends "base.html" %}` + `{% load static i18n %}`.
- `{% block extra_css %}` → `<link rel="stylesheet" href="{% static 'css/pages/properties.css' %}">`.
- `{% block extra_js %}` → `<script src="{% static 'js/filters.js' %}" defer></script>`.
- `{% block content %}`:
  - **`listing-hero`** (eyebrow „Kolekcija", h1, intro) — UI copy kroz `{% trans %}`.
  - **`filter-bar`** umotan u **`<form method="get" action="">`**. Kontrole sa `name`-ovima
    usklađenim sa formom: `name="location"`, `name="property_type"` (NE `type`), `name="status"`
    (vrednosti = MODEL `for_sale`/`for_rent`/`price_on_request`), `name="price_min"`/`name="price_max"`
    (NE `price-min`/`price-max`), bedrooms = **hidden `<input type="hidden" name="bedrooms">`** (chip JS upisuje vrednost),
    `name="keyword"` text input. `filter-bar__optional` checkboxovi se IZOSTAVLJAJU. „Primeni filtere" = submit;
    „Resetuj filtere" → čist `/properties/`. Vrednosti se zadržavaju iz `request.GET` posle reload-a.
  - **`listing-grid`** sa `{% for p in properties %}` → `property-card`:
    - `property-card__image`: `{% if p.hero_image %}{{ p.hero_image.url }}{% else %}{% static 'images/placeholders/property-1.svg' %}{% endif %}`;
      badge `badge property-card__badge` + `badge--sale`/`badge--rent`/`badge--inquiry` + `get_status_display`.
    - `property-card__title` = `{{ p.title }}` (auto-escape, **BEZ `|safe`**).
    - `property-card__meta`: `get_property_type_display`, `area_sqm` m², `bedrooms` soba.
    - `property-card__price`: `{% if p.price_on_request or p.status == 'price_on_request' %}{% trans "Cena na upit" %}{% else %}€{{ p.price|floatformat:0 }}{% endif %}`.
    - `property-card__cta` „Detaljnije" → **hardkodovan `href="/properties/{{ p.slug }}/"`** (NE `{% url %}`).
    - `{% empty %}` → `listing-empty` poruka („Nema nekretnina koje odgovaraju izabranim filterima.").
- Bez `fetch(`/`XMLHttpRequest`/`/api/` (čist GET reload).

## 5. `filters.js` (adaptacija — AC4)

Client-side hide → GET form submit. Selektori usklađeni: `[name="price-min"]`→`[name="price_min"]`,
`[name="price-max"]`→`[name="price_max"]`, `[name="type"]`→`[name="property_type"]`. Bedrooms chip klik
→ hidden `name="bedrooms"`. Bez `fetch`/XHR.

## 6. Test helpers (`tests/test_property_listing.py`)

- `_get_model(app_label, class_name)` — importuje model dinamički.
- `_make_property(**overrides)` — `Property.objects.create(...)` SVA NOT NULL polja, `hero_image=""`,
  **NE poziva `full_clean()`**. Default: signature/active/for_sale.
- `_get_listing(client, query="")` — GET `/properties/` (+ opcioni query string) → `(resp, html)`.
- `_superuser(django_user_model)` — admin regresija.
- `_admin_index_path()` — iz `settings.ADMIN_URL`.
- Marker brojanja kartica: `html.count('class="property-card"')`.
