---
story-id: 4-1-about-i-international-stranice-iz-cms-a
title: "Interface Contract — About i International stranice iz CMS-a"
epic: 4
module: "pages, templates, config"
phase: RED (TDD) — failing contract definisan PRE implementacije
author: TEA (Test Architect)
created: 2026-06-02
test-file: tests/test_static_pages.py
references:
  - _bmad-output/implementation-artifacts/4-1-about-i-international-stranice-iz-cms-a.md   # IZVOR ISTINE za AC1–AC5 + T1–T6
  - pages/models.py                                                                        # Page (slug unique, title_sr/content_sr required, is_active default True)
  - core/models.py                                                                         # SiteSettings (founder_*/phone/whatsapp/email + .load())
  - pages/views.py                                                                         # trenutno SAMO HomeView + custom_404
  - config/urls.py                                                                         # home/properties/property-detail/ADMIN_URL/tinymce — NEMA /about/ /international/ /contact/
  - docs/OpenDesignFiles/about.html                                                        # about-hero/about-portrait/about-bio/services-list/why-pillar/btn--primary
  - docs/OpenDesignFiles/international.html                                                # intl-hero/intl-intro/timeline 01–06/Pravni okvir/Bankarstvo/Servis preseljenja/section--olive/btn--ghost
---

# Interface Contract — Story 4.1

> Ovaj dokument je MAŠINSKI ugovor između RED-faze testova (`tests/test_static_pages.py`)
> i buduće implementacije (Dev priča). Definiše TAČAN potpis view-a, ruta i template
> sekcija koje testovi asertuju. Implementacija koja zadovolji ovaj ugovor čini RED
> testove zelenim BEZ izmene testova.

---

## 1. View — `PageDetailView` (pages/views.py)

**Dodaje se NOVI view u `pages/views.py`. `HomeView` i `custom_404` se NE diraju. Bez novih migracija.**

### Potpis (LOCKED — fiksni-slug, NE `slug_url_kwarg`)

Rute su FIKSNE (`/about/`, `/international/`) BEZ `<slug>` segmenta u putanji.
Standardni `DetailView` sa `slug_url_kwarg` NE radi (nema `slug` u `kwargs`).
Implementacija bira JEDAN ispravan pristup:

**(a) PREPORUKA — tanak funkcijski view:**
```python
from django.shortcuts import get_object_or_404, render
from .models import Page

def page_view(request, slug, template_name):
    page = get_object_or_404(Page, slug=slug, is_active=True)
    return render(request, template_name, {"page": page})
```

**(b) Alternativa — `DetailView` sa fiksnim slug-om + custom `get_object`:**
```python
class PageDetailView(DetailView):
    model = Page
    context_object_name = "page"
    slug = None  # postavlja se preko as_view(slug=...)
    def get_object(self, queryset=None):
        return get_object_or_404(Page, slug=self.slug, is_active=True)
```

### Gating (LOCKED — `is_active=True` u QUERY-ju)
- `get_object_or_404(Page, slug=<slug>, is_active=True)` → filter je U upitu (NE post-fetch `if`).
- Nepostojeći (ne-seedovan) slug → **404**.
- `Page(is_active=False)` → **404** (uključujući za prijavljenog superusera — `Page` NEMA preview polje).
- `Page(is_active=True)` → **200** sa odgovarajućim template-om.
- **NAMERNO NIJE graciozni „uskoro" placeholder** — ne-seedovan slug je čista 404.

### Kontekst
- `page` → `Page` objekat.
- `site_settings` → već globalan preko `core.context_processors.site_settings` (2.2). **NE re-load-ovati** u view-u.

---

## 2. Rute (config/urls.py) — EKSPLICITNE, BEZ catch-all

Dodaju se DVE eksplicitne rute (oblik zavisi od izbora view-a):

**Ako (a) funkcijski view:**
```python
path("about/", page_view, {"slug": "about", "template_name": "about.html"}, name="about")
path("international/", page_view, {"slug": "international", "template_name": "international.html"}, name="international")
```

**Ako (b) DetailView:**
```python
path("about/", PageDetailView.as_view(slug="about", template_name="about.html"), name="about")
path("international/", PageDetailView.as_view(slug="international", template_name="international.html"), name="international")
```

Invarijante:
- `reverse("about") == "/about/"` i `reverse("international") == "/international/"`.
- **NEMA root catch-all `path("<slug:slug>/", ...)`** (zarobio bi `/properties/`, `/admin/`, `/tinymce/`).
- **NEMA `i18n_patterns`/`/en/` prefiks** (Epik 6) → `GET /en/international/` mora ostati **404**.
- `home`/`properties`/`property-detail`/`ADMIN_URL/`/`tinymce/`/`handler404` se NE diraju.
- Ruta `/contact/` se NE dodaje u 4.1 (Story 4.2) → `GET /contact/` mora ostati **404**.

---

## 3. Template — `templates/about.html` (FLAT layout, NE `templates/pages/`)

- `{% extends "base.html" %}` + `{% load static i18n %}`.
- `{% block extra_css %}` → `css/pages/about.css`.
- `{% block content %}` sekcije (klase verno `docs/OpenDesignFiles/about.html`):

| Sekcija | Marker (klasa) | Sadržaj | Render |
|---|---|---|---|
| Hero | `about-hero` / `about-hero__tagline` | `<h1>{{ page.title_sr }}</h1>` | auto-escape (NE `\|safe`) |
| Velika foto | `about-portrait` / `about-portrait__img` | `founder_photo.url` ili `founder-portrait.svg` | `{% if site_settings.founder_photo %}…{% else %}{% static '…founder-portrait.svg' %}{% endif %}` |
| Bio + filozofija | `about-bio` | `{{ page.content_sr\|safe }}` (admin-curated HTMLField — zamenjuje 3× `[KLIJENT DOSTAVLJA]`) | `\|safe` |
| Founder ime/titula | — | `{{ site_settings.founder_name }}`, `{{ site_settings.founder_title_sr }}` | auto-escape (NE `\|safe`, NE `.localized()` u `{{ }}`) |
| Servisi | `services-list` | statički UI copy iz dizajna | `{% trans %}` skelet |
| Zašto Velegrad | `why-pillar` / `why-pillar__icon` | 6× pillar (statički, inline SVG) | `{% trans %}` skelet — **NE `pillars-grid`/`pillar` (to su HOME klase)** |
| CTA | `btn--primary` | h2 + dugme | `<a href="/contact/">` (HARDKODOVAN — NE `{% url 'contact' %}`) |

**Anti-„osiromašena stranica":** render MORA sadržati `class="services-list"` marker I `class="why-pillar` marker (statičke sekcije, klasno-skopirani markeri — ne goli substring), ne samo hero + `content_sr`.

---

## 4. Template — `templates/international.html`

- `{% extends "base.html" %}` + `{% load static i18n %}`.
- `{% block extra_css %}` → `css/pages/international.css`.
- `{% block content %}` sekcije (klase verno `docs/OpenDesignFiles/international.html`):

| Sekcija | Marker (klasa/tekst) | Sadržaj | Render |
|---|---|---|---|
| Hero | `intl-hero` / `intl-hero__tagline` | `<h1>{{ page.title_sr }}</h1>` | auto-escape |
| Uvod | `intl-intro` | `{{ page.content_sr\|safe }}` (JEDINI `[KLIJENT DOSTAVLJA]` blok) | `\|safe` |
| Proces — timeline | `timeline` / `timeline__step` / `timeline__number` / `timeline__content` | KURIRAN 6-korak (`01`…`06`) + h3 + opisi | `{% trans %}` skelet — **NE gurati u `content_sr`** |
| Tematske sekcije | „Pravni okvir" / „Bankarstvo i finansiranje" / „Servis preseljenja" | kurirana zaglavlja | `{% trans %}` skelet |
| CTA | `section--olive` / `btn--ghost` | h2 + dugme | `<a href="/contact/">` (HARDKODOVAN) |

**Anti-„osiromašena stranica":** render MORA sadržati `class="timeline` marker + `timeline__step` + skopirani koraci `timeline__number">01<` I `timeline__number">06<` (prvi i poslednji korak — markeri vezani za `timeline__number` markup, ne goli „01"/„06" substring koji bi mogao false-pass na godini/telefonu/koordinatama) + bar zaglavlje „Pravni okvir".

---

## 5. Bezbednost (XSS trust boundary)

- `\|safe` ISKLJUČIVO na `page.content_sr` (admin-curated TinyMCE HTMLField, single-tenant).
- SVE plain CharField (`page.title_sr`, `site_settings.founder_name`, `founder_title_sr`) → standardni `{{ }}` auto-escape, BEZ `\|safe`.
- `title_sr="<script>alert(1)</script>"` → mora se renderovati kao `&lt;script&gt;…` (escapovano).
- `content_sr="<p>ok</p>"` → mora se renderovati kao sirov `<p>ok</p>` (NE escapovano).

---

## 6. Helperi (tests/test_static_pages.py — izvedeni iz test_home_page.py / test_admin_dashboard.py)

- `_get_model(app_label, class_name)` — importlib lookup (izbegava rani import).
- `_seed_page(slug, title_sr, content_sr, is_active=True, **ov)` — `Page.objects.create(...)`; `title_sr` I `content_sr` UVEK postavljeni (inače IntegrityError); `title_en`/`content_en` default `""`.
- `_seed_site_settings(**ov)` — `SiteSettings.load()` → set founder/kontakt → `founder_photo=""` (placeholder grana) → `.save()`.
- `_make_property(**ov)` — minimalni `Property.objects.create(...)` (regresija `/properties/<slug>/`).
- `_superuser(django_user_model)` — superuser fixture (admin regresija + AC3 inactive-staff-still-404).
- `_admin_index_path()` — `/{ADMIN_URL}/` (admin regresija).
- `_try_reverse(name)` — `reverse` ili `None` (NoReverseMatch u RED fazi).
- `_get_about(client)` / `_get_intl(client)` — `(resp, html)`.
- `FOUNDER_NAME` / `FOUNDER_TITLE` (sa `&` za escape-asert) — distinct sentinel vrednosti.

---

## 7. Regresione invarijante (AC5)

- `python manage.py check` čist.
- `GET /` → 200; `GET /properties/` → 200; `GET /properties/<slug>/` (seedovan aktivan) → 200.
- admin index (superuser) → 200; `GET /admin/` → 404.
- `GET /contact/` → 404 (4.2 još nije isporučen).
- `GET /nepostojeci-slug/` → 404 (NEMA catch-all).
- `GET /en/international/` → 404 (NEMA i18n routing).
- Bez novih migracija (samo view/template/URL).
