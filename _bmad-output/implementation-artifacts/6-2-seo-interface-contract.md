---
story-id: 6-2-seo
title: "Interface Contract — SEO (meta/OG per zapis, sitemap.xml/robots.txt, Schema.org RealEstateListing, GA4)"
phase: RED (Test Architect)
created: 2026-06-03
author: TEA (Test Architect)
status: contract-defined
test-file: tests/test_seo.py
references:
  - _bmad-output/implementation-artifacts/6-2-seo.md            # STORY — autoritativni AC1–AC4 + LOCKED odluke
  - _bmad-output/implementation-artifacts/6-1-dvojezicnost-sr-en-interface-contract.md  # FORMAT predložak
---

# Interface Contract — Story 6.2 (SEO)

Ovaj dokument je RED-faza ugovor: ono što GREEN dev MORA da implementira da bi `tests/test_seo.py`
prošao. Sve odluke su izvedene iz STORY-ja (`6-2-seo.md`) AC1–AC4 + LOCKED Dev Notes i iz postojećih
konvencija (čitano: `base.html`, `property-detail.html`, `config/urls.py`, `config/settings/base.py`,
`core/models.py`, `properties/models.py`, `pages/models.py`, `properties/views.py`).

INVARIJANTA cele priče: **BEZ projektne migracije** (sva polja postoje); `/sitemap.xml` i `/robots.txt`
su **VAN `i18n_patterns`** (nema `/en/` prefiksa); SEO blokovi su jezik-svesni; GA4 se renderuje SAMO kad
`SiteSettings.google_analytics_id` NIJE prazan ni whitespace-only; Facebook Pixel / FR meta se NE renderuju.

---

## 1. Settings — `config/settings/base.py` (AC2 / T1)

- `INSTALLED_APPS` dobija `"django.contrib.sites"` i `"django.contrib.sitemaps"` (oba UGRAĐENA u Django,
  bez novog paketa). Dodati uz ostale `django.contrib.*` app-ove.
- `SITE_ID = 1` (sitemap framework ga zahteva).
- NE dodavati `GOOGLE_ANALYTICS_ID` setting (GA4 čita iz `SiteSettings.google_analytics_id`).
- `config/settings/test.py` nasleđuje `INSTALLED_APPS` iz `base.py` (`from .base import *`) → `django_site`
  migrira u SQLite test DB. Verifikacija: `assert "django.contrib.sites" in settings.INSTALLED_APPS and
  "django.contrib.sitemaps" in settings.INSTALLED_APPS and settings.SITE_ID == 1`.

## 2. Model metoda — `properties/models.py` (AC2/AC3 / T2)

- DODAJ `Property.get_absolute_url(self)`:
  ```python
  def get_absolute_url(self):
      return reverse("property-detail", kwargs={"slug": self.slug})
  ```
- Metoda (NE polje) → **BEZ migracije**. Koristi se na TRI mesta: sitemap `location()`, `og:url`, Schema `url`.

## 3. Novi modul — `core/sitemaps.py` (AC2 / T2)

```python
from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import translation

from properties.models import Property
from pages.models import Page

class PropertySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    def items(self):
        return Property.objects.filter(is_active=True)
    def location(self, obj):
        with translation.override(settings.LANGUAGE_CODE):
            return obj.get_absolute_url()
    def lastmod(self, obj):
        return obj.updated_at

class PageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5
    _slug_to_route = {"about": "about", "international": "international"}
    def items(self):
        return Page.objects.filter(is_active=True, slug__in=["about", "international"])
    def location(self, obj):
        with translation.override(settings.LANGUAGE_CODE):
            return reverse(self._slug_to_route[obj.slug])
```

- `location()` OBA sitemap-a forsira `translation.override(settings.LANGUAGE_CODE)` (SR-determinizam — telo
  sitemap-a NIKAD ne sadrži `/en/`, čak i kad je `translation.activate("en")` aktivan pre requesta).
- `PageSitemap.items()` filtrira `slug__in=["about","international"]` (nepoznat slug nikad ne uđe).
- Inaktivni (`is_active=False`) Property/Page se NE pojavljuju.

## 4. URLs — `config/urls.py` (AC2 / T3)

- VAN `i18n_patterns` (u običnom `urlpatterns`, uz admin/tinymce/i18n):
  ```python
  from django.contrib.sitemaps.views import sitemap
  from core.sitemaps import PropertySitemap, PageSitemap
  sitemaps = {"properties": PropertySitemap, "pages": PageSitemap}
  path("sitemap.xml", sitemap, {"sitemaps": sitemaps},
       name="django.contrib.sitemaps.views.sitemap")
  ```
- `/robots.txt` VAN `i18n_patterns`: `TemplateView.as_view(template_name="robots.txt",
  content_type="text/plain")` ili tanak `HttpResponse(content_type="text/plain")`. Mora sadržati
  `User-agent: *`, `Allow: /`, `Disallow: /<ADMIN_URL>/` (iz `settings.ADMIN_URL`), i `Sitemap:` apsolutni
  URL ka `/sitemap.xml`.
- `GET /sitemap.xml` → 200 XML; `GET /robots.txt` → 200 text/plain.
- `GET /en/sitemap.xml` → 404 I `GET /en/robots.txt` → 404 (van prefiksa).
- `handler404` očuvan.

## 5. Templates (AC1 / T4)

- `base.html` — POSTOJEĆI blokovi se PUNE (ne menjati imena):
  - `{% block title %}` ← `site_settings.seo_default_title|default:"Velegrad Estate"`.
  - `{% block meta_description %}` ← `site_settings.seo_default_description|default:"..."`.
  - `{% block og %}` ← `og:title`/`og:description` iz `seo_default_*`; `og:type="website"`; `og:image`
    APSOLUTNI URL (i za placeholder grananje: `{{ request.scheme }}://{{ request.get_host }}{% static ... %}`).
- `property-detail.html` — override:
  - `{% block title %}` ← `{{ property.meta_title|default:property.title }} — Velegrad Estate`.
  - `{% block meta_description %}` ← `meta_description` ili `{% loc property "description" %}` prošao
    `|striptags|truncatewords:N` (NIKAD sirov HTMLField).
  - `{% block og %}` ← per-property `og:title`/`og:description`; `og:image` APSOLUTNI URL u OBA grananja
    (popunjen `hero_image` I prazan→placeholder); `og:url` = apsolutni `{{ property.get_absolute_url }}`.
  - `{% block schema %}` ← `{{ schema_data|json_script:"schema-org" }}` u `<script type="application/ld+json">`.
- `about.html` / `international.html` — override `{% block title %}` (`page.meta_title|default:...`) +
  `{% block meta_description %}` (`page.meta_description|default:...`).
- **og:image MORA biti apsolutni URL** (`http://`/`https://`/`//`) u OBA grananja; NIKAD sirov `{% static %}`
  ni relativan `/media/`. Pod Django test client-om host je `testserver` → `http://testserver/...`.

## 6. Schema.org — `properties/views.py` `_build_context` + `property-detail.html` (AC3 / T6)

- Schema dict se gradi u VIEW-u (`schema_data = {...}`) i renderuje preko `{{ schema_data|json_script:"schema-org" }}`
  (LOCKED — ručno sklapanje JSON-a u template-u NIJE dozvoljeno).
- Dict: `@context="https://schema.org"`, `@type="RealEstateListing"`, `name` (`meta_title or title`),
  `description` (`meta_description` ili `strip_tags`+`Truncator(...).words(N)` od HTMLField opisa),
  `image` (apsolutni preko `request.build_absolute_uri`), `url` (apsolutni
  `request.build_absolute_uri(property.get_absolute_url())`), uslovni `offers`
  (`{"@type":"Offer","price":...,"priceCurrency":"EUR"}` SAMO kad `price` postoji i `price_on_request=False`).
- SAMO na Property Detail (Home/ostale stranice nemaju RealEstateListing JSON-LD).
- Wrapper za `application/ld+json` je dozvoljen, ali `json_script` ostaje izvor validnog JSON-a; test parsira
  JSON sadržaj `<script ...>...</script>` preko `json.loads`.

## 7. GA4 — `base.html` `{% block ga4 %}` (AC4 / T5)

- Renderuje gtag.js SAMO kad `site_settings.google_analytics_id` NIJE prazan NI whitespace-only.
- Guard na obrezanoj vrednosti: `{% if site_settings.google_analytics_id.strip %}...{% endif %}` (ili strip
  u context processoru).
- `<script async src="https://www.googletagmanager.com/gtag/js?id={{ google_analytics_id }}"></script>` +
  inline `gtag('config', '{{ google_analytics_id|escapejs }}')`.
- Izvor je `SiteSettings.google_analytics_id` (NE settings/env). Prisutno na SVAKOJ stranici (base.html).

---

## Sažetak (interface_contract_summary)

- **urls:** `/sitemap.xml` (GET, 200, XML, VAN i18n), `/robots.txt` (GET, 200, text/plain, VAN i18n),
  `/en/sitemap.xml`→404, `/en/robots.txt`→404.
- **views:** `django.contrib.sitemaps.views.sitemap` (montiran), `PropertyDetailView._build_context`
  (+`schema_data`), `robots.txt` TemplateView/HttpResponse.
- **models:** `Property.get_absolute_url()` (nova metoda, BEZ migracije).
- **modules:** `core/sitemaps.py` (`PropertySitemap`, `PageSitemap`); `templates/robots.txt`;
  izmene `config/settings/base.py` (sites+sitemaps+SITE_ID), `config/urls.py`, `base.html`,
  `property-detail.html`, `about.html`, `international.html`.
