---
story-id: 2-1-integracija-dizajn-sistema-i-bazni-layout
title: "Interface Contract — Integracija dizajn sistema i bazni layout"
phase: RED (TDD) — contract precedes implementation
author: TEA (Test Architect)
created: 2026-06-02
test-file: tests/test_base_layout.py
references:
  - _bmad-output/implementation-artifacts/2-1-integracija-dizajn-sistema-i-bazni-layout.md  # IZVOR ISTINE (7 AC, 7 task)
  - docs/OpenDesignFiles/index.html        # head/header/footer markup + CSS kaskada
  - docs/OpenDesignFiles/404.html          # error-page markup + error.css
---

# Interface Contract — Story 2.1

Ovaj dokument definiše **konkretan ugovor** koji Dev (GREEN faza) mora da zadovolji.
Svaki potpis (putanja fajla, ime bloka, CSS klasa, ruta, helper) ovde je **normativan** i
direktno preslikan u `tests/test_base_layout.py`. Imena/struktura su izvedeni iz
pregledanih `docs/OpenDesignFiles/{index.html,404.html,assets/...}`.

---

## 1. `static/` raspored fajlova (deliverable na disku)

Svi fajlovi se **kopiraju** iz `docs/OpenDesignFiles/assets/...` u projektni `static/`
uz očuvanu strukturu (sadržaj se NE menja — dizajn je konačan).

### CSS — globalna kaskada (`static/css/`)
| putanja | uloga |
|---|---|
| `static/css/tokens.css` | CSS varijable (`--color-*`, `--text-body`) — **mora prvi** |
| `static/css/base.css` | reset + `body { font-size: var(--text-body) }` |
| `static/css/layout.css` | grid/layout |
| `static/css/components.css` | dugmad, kartice, nav (touch ≥44px) |
| `static/css/utilities.css` | utility klase |

Redosled kaskade je **load-bearing** (token pre upotrebe): `tokens → base → layout → components → utilities`.

### CSS — per-stranica (`static/css/pages/`) — kopiraju se svi (kaskada celovita), NE uključuju se u base
`home.css`, `about.css`, `contact.css`, `error.css`, `international.css`, `private-collection.css`, `properties.css`, `property-detail.css`

### JS (`static/js/`)
| putanja | uloga | uključeno u base |
|---|---|---|
| `static/js/main.js` | sticky header, hamburger, lang-switcher (visual only) | DA — `<script ... defer>` |
| `static/js/gallery.js` | galerija (per-stranica) | NE (kasniji epici, `{% block extra_js %}`) |
| `static/js/filters.js` | filteri (per-stranica) | NE |
| `static/js/forms.js` | forme (per-stranica) | NE |

### Placeholder SVG-ovi (`static/images/placeholders/`) — svih 9 obavezno
`hero-placeholder.svg`, `founder-portrait.svg`, `property-1.svg`, `property-2.svg`,
`property-3.svg`, `property-4.svg`, `logo.svg`, `floor-plan.svg`, `property-detail-hero.svg`

---

## 2. `templates/base.html`

`{% load static i18n %}` na vrhu. `<html lang="sr">`.

### `<head>` — blokovi (override-abilni)
| blok | default / sadržaj |
|---|---|
| `{% block title %}` | „Velegrad Estate" (default) |
| `{% block meta_description %}` | `<meta name="description" ...>` |
| `{% block og %}` | OG/Twitter meta |
| `{% block schema %}` | JSON-LD Schema.org (prazno spremno za Epik 6) |
| `{% block ga4 %}` | GA4 placeholder (prazno dok GA4 ID ne stigne — TODO) |
| `{% block extra_css %}` | per-stranica `pages/*.css` |

Fiksno u head-u (NE u bloku): `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1.0">`,
Google Fonts `preconnect` + Bodoni Moda / DM Sans link, CSS kaskada preko `{% static %}` u
tačnom redosledu (tokens→base→layout→components→utilities).

### Body struktura i obavezne klase
- `<header class="site-header" role="banner">`
  - logo link na `/` koristi `{% static 'images/placeholders/logo.svg' %}` (NE inline base64; TODO za klijentski logo IR #4)
  - `<nav class="site-nav" ...>` sa nav linkovima (svi `{% trans %}`)
  - `<div class="lang-switcher hide-mobile">` sa SR/EN dugmadima (`{% trans %}` aria-label)
  - `<button class="mobile-menu-toggle" aria-label="{% trans ... %}" aria-expanded="false">`
- `<div class="mobile-menu" role="dialog">` sa nav linkovima
- `{% block content %}{% endblock %}` — **između** header i footer
- `<footer class="site-footer" role="contentinfo">`
  - `site-footer__contact-info` (statički placeholder; vezivanje na SiteSettings = 2.2)
  - `site-footer__nav` liste (`{% trans %}` labele)
  - `site-footer__copyright` (`{% trans %}`)
  - drugi `lang-switcher`
- pred `</body>`: `<script src="{% static 'js/main.js' %}" defer></script>` pa `{% block extra_js %}`

### i18n — OBAVEZAN `{% trans %}` skup (zaključan, AC3)
`base.html` mora obaviti `{% trans %}`-om: header nav linkove, hamburger `aria-label`,
SR/EN labele oba lang-switcher-a, footer copyright + footer nav labele.
`{% load i18n %}` prisutan.

---

## 3. `templates/404.html`

- **MORA** `{% extends "base.html" %}` (zaključano — nasleđuje `site-header`/`site-footer`).
- `{% load static i18n %}`.
- `{% block extra_css %}` → `<link rel="stylesheet" href="{% static 'css/pages/error.css' %}">` (NE ponovo globalna kaskada).
- `{% block content %}` → `<main class="error-page">` sa `error-page__code` „404", naslov, poruka,
  `error-page__ctas` sa dva dugmeta:
  - „Vratite se na početnu" → `/` (`btn btn--primary`)
  - „Kontaktirajte nas" → contact ruta / `/` fallback (`btn btn--secondary`)
- Oba CTA stringa + 404 poruke kroz `{% trans %}`. `{% load i18n %}` prisutan.
- Standalone 404 (bez okvira) NIJE dozvoljen.

---

## 4. `pages/views.py` + `config/urls.py`

### `pages/views.py`
```python
from django.shortcuts import render
from django.views.generic import TemplateView

class HomeView(TemplateView):           # ILI def home(request): ...
    template_name = "home.html"          # home.html {% extends "base.html" %}, BEZ sadržaja iz baze

def custom_404(request, exception):
    return render(request, "404.html", status=404)
```

### `config/urls.py` (dodaci — postojeće rute NE dirati)
```python
urlpatterns = [
    path("", HomeView.as_view(), name="home"),   # minimalna home ruta (AC7)
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    path("tinymce/", include("tinymce.urls")),
]
handler404 = "pages.views.custom_404"            # zaključano (AC5)
```

### `templates/home.html`
`{% extends "base.html" %}` + `{% block content %}` placeholder. **BEZ** sadržaja iz baze,
**BEZ** `pages/home.css` (per-stranica CSS dolazi u 2.2).

---

## 5. Placeholder fallback obrazac (reusable, AC6)

Konvencija (dokumentovana za 2.2+), demonstrirana na logo-u:
```django
{% if obj.image %}{{ obj.image.url }}{% else %}{% static 'images/placeholders/X.svg' %}{% endif %}
```
U 2.1 logo u header/footer koristi direktno `{% static 'images/placeholders/logo.svg' %}`
(nema `obj`), sa TODO za klijentski SVG logo (IR #4).

---

## 6. Test helpers (`tests/test_base_layout.py`)

| helper | uloga |
|---|---|
| `_admin_index_path()` | mounted admin index iz `settings.ADMIN_URL` (kao 1.3) |
| `_superuser(django_user_model)` | kreira superusera za admin regresiju |
| `_static_dir()` | `Path(settings.BASE_DIR) / "static"` |
| `_template_path(name)` | `Path(settings.BASE_DIR) / "templates" / name` |
| `_read(path)` | bezbedno čitanje template fajla (vraća "" ako fali — clean RED) |

Render testovi GET `/` (javna, bez login-a). 404 test koristi `@override_settings(DEBUG=False)`
+ GET nepostojeće putanje (NE `reverse`). Admin regresija koristi `_admin_index_path()` (NE hardkodovan `/admin/`).
