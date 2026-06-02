---
story-id: 2-2-home-stranica-povezana-sa-bazom
title: "Interface Contract — Home stranica povezana sa bazom"
epic: 2
module: "pages, core, templates"
phase: "RED (Test Architect) — potpisi PRE implementacije"
created: 2026-06-02
author: TEA (Test Architect)
references:
  - _bmad-output/implementation-artifacts/2-2-home-stranica-povezana-sa-bazom.md   # priča (IZVOR ISTINE za AC)
  - _bmad-output/implementation-artifacts/2-1-integracija-dizajn-sistema-i-bazni-layout-interface-contract.md  # 2.1 frame contract
  - docs/OpenDesignFiles/index.html   # markup sekcija A–F (linije 69–296)
  - core/models.py                    # SiteSettings (.load(), .localized()), polja
  - properties/models.py              # Property polja + NOT NULL set
test-file: tests/test_home_page.py
---

# Interface Contract — Story 2.2 (Home povezana sa bazom)

Ovaj dokument zaključava **potpise** koje GREEN-faza (Dev) mora ispoštovati da
bi RED testovi u `tests/test_home_page.py` prešli u zeleno. Sve odluke su
izvedene iz priče 2.2 (LOCKED kriterijumi) i pregledanog markup-a dizajna.

---

## 1. `core/context_processors.py` — `site_settings(request)` (AC6)

**Novi fajl** `core/context_processors.py`:

```python
from core.models import SiteSettings

def site_settings(request):
    """Učini SiteSettings singleton dostupnim u SVAKOM template-u.
    load() radi get_or_create(pk=1) — uvek vraća instancu (nikad None),
    bezbedno i u praznoj bazi. Jedan upit po renderu (MVP; keširanje = Epik 6).
    """
    return {"site_settings": SiteSettings.load()}
```

**Registracija** u `config/settings/base.py` →
`TEMPLATES[0]["OPTIONS"]["context_processors"]` — DODATI red posle postojeća
četiri (debug/request/auth/messages, ne dirati ih):

```python
"core.context_processors.site_settings",
```

Potpis za test: `"core.context_processors.site_settings"` MORA biti element liste
`settings.TEMPLATES[0]["OPTIONS"]["context_processors"]`.

**Jedan izvor istine:** `site_settings` je JEDINI izvor SiteSettings u svim
template-ima (footer u base.html + sve home sekcije). `HomeView` NE dodaje
`context["site"]` i NE poziva ponovo `SiteSettings.load()`.

---

## 2. `pages/views.py` — `HomeView.get_context_data` (AC1–AC3)

`HomeView` ostaje `TemplateView` sa `template_name = "home.html"`. Dodaje SAMO
`featured_properties` u kontekst:

```python
from properties.models import Property

class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured_properties"] = Property.objects.filter(
            is_featured=True, is_active=True
        )[:4]
        return context
```

- **Oba filtera obavezna** (`is_featured=True, is_active=True`) i **`[:4]`**.
- `custom_404` ostaje netaknut.
- SiteSettings (hero/founder/kontakt) NE dolazi iz view-a — samo iz context
  procesora (§1).

---

## 3. `templates/home.html` — sekcije A–F + `extra_css` (AC1–AC5, AC7)

Vrh: `{% extends "base.html" %}` + `{% load static i18n %}`.

`{% block extra_css %}` → `<link rel="stylesheet" href="{% static 'css/pages/home.css' %}">`
(per-stranica; NE u base). Ukloniti 2.1 placeholder `{% block content %}`.

### Konvencija renderovanja sadržaja iz baze (LOCKED)
- Sadržaj iz baze renderuje se **direktno preko `_sr` polja**:
  `{{ site_settings.hero_headline_sr }}`, `{{ site_settings.founder_title_sr }}`,
  `{{ site_settings.founder_bio_sr|safe }}`.
- **NE pozivati `.localized("...")` u `{{ }}`** (Django ne prosleđuje string-arg →
  bug). `.localized()` legitiman SAMO iz Python-a.
- UI copy (labele, naslovi teasera, pillar tekstovi) → `{% trans %}`.

### Konvencija forward-linkova (LOCKED)
Rute `properties`/`private-collection`/`contact` NE postoje. Svi linkovi ka njima
su **HARDKODOVANI APSOLUTNI hrefovi** — `/properties/`, `/private-collection/`,
Contact → `/`. **`{% url %}` na te rute je ZABRANJEN** (NoReverseMatch → 500).

### Placeholder fallback (2.1 obrazac)
```django
{% if site_settings.hero_image %}{{ site_settings.hero_image.url }}{% else %}{% static 'images/placeholders/hero-placeholder.svg' %}{% endif %}
```
Isto za founder (`founder-portrait.svg`) i property kartice (`property-1.svg`..
`property-4.svg`). Putanja MORA biti vidljiva u HTML-u (`<img src>` ili
`background-image:url(...)`) radi testabilnosti.

### Sekcije i markeri (klase iz dizajna — verno preneti)

| Sek. | Klase / markeri (test-anchor) | Sadržaj |
|------|-------------------------------|---------|
| **A — Hero** (AC1) | `class="hero"`, `hero__bg`, `hero__overlay`, `hero__content`, `hero__kicker`, `hero__tagline`, `hero__cta` | kicker = `founder_name` + `founder_title_sr`; tagline = `hero_headline_sr`; CTA tekst = `hero_cta_text_sr` href `/`; bg `hero_image` ili `hero-placeholder.svg` |
| **B — Advisor** (AC2) | `section section--ivory`, `class="advisor"`, `advisor__portrait`, `advisor__name`, `advisor__title`, `advisor__text`, `advisor__contact` | portrait = `founder_photo` ili `founder-portrait.svg`; name = `founder_name`; title = `founder_title_sr`; bio = `founder_bio_sr|safe`; `tel:{{ phone_primary }}` + `https://wa.me/{{ whatsapp_number }}` |
| **C — Featured** (AC3) | `properties-preview__header`, `properties-preview__grid`, `properties-preview__footer`, `link-arrow`, `class="property-card"` (po jednom marker po kartici) | `{% for p in featured_properties %}` → kartica (image+badge, `property-card__title`=title, `property-card__meta` type/area/bedrooms, `property-card__price` ili „Cena na upit", `property-card__cta` href `/properties/`); header `link-arrow` href `/properties/`; footer btn href `/properties/`; `{% empty %}` → diskretna „uskoro" poruka (BEZ lažnih kartica) |
| **D — Private teaser** (AC4) | `section section--dark`, `class="private-teaser"` | eyebrow + h2 + paragraf + btn href `/private-collection/`. NULA `property-card`. Sav copy `{% trans %}` |
| **E — Why Velegrad** (AC5) | `section section--ivory`, `class="pillars-grid"`, **6× `class="pillar"`** (`pillar__icon`, `pillar__title`, `pillar__text`) | 6 stubova: Diskrecija, Pregovaranje, Premium mreža, Međunarodni klijenti, Lični pristup, Pouzdanost. Sav copy `{% trans %}`; inline SVG iz dizajna |
| **F — Contact teaser** (AC4) | `class="contact-teaser"`, `contact-teaser__links` | eyebrow + h2 + text + linkovi „Zakažite razgovor" href `/` i „Pozovite direktno" `tel:{{ phone_primary }}`. BEZ `<form>` |

**Price/status (LOCKED logika):** „Cena na upit" kada `p.price_on_request` ILI
`p.status == "price_on_request"`; inače formatirana `price`. Badge preko
`p.get_status_display` ili inline mapiranje (`badge--sale`/`badge--rent`/`badge--inquiry`).

**Marker za brojanje kartica (LOCKED):** test broji `html.count('class="property-card"')`.
Svaka kartica MORA imati TAČNO jedan `class="property-card"` atribut (klasa-string
ne sme stajati i na deci kartice) da bi `== 4` / `== 0` bilo stabilno.

---

## 4. `templates/base.html` — footer rebind na `site_settings` (AC6)

Zameniti statički `site-footer__contact-info` blok (linije ~93–99) vrednostima iz
`site_settings`; ukloniti 2.1 TODO komentar. `{% if %}` štit oko praznih polja:

```django
<div class="site-footer__contact-info">
  {% if site_settings.address %}<span>{{ site_settings.address }}</span>{% endif %}
  {% if site_settings.phone_primary %}<a href="tel:{{ site_settings.phone_primary }}">{{ site_settings.phone_primary }}</a>{% endif %}
  {% if site_settings.email_primary %}<a href="mailto:{{ site_settings.email_primary }}">{{ site_settings.email_primary }}</a>{% endif %}
  {% if site_settings.whatsapp_number %}<a href="https://wa.me/{{ site_settings.whatsapp_number }}" target="_blank" rel="noopener">WhatsApp</a>{% endif %}
</div>
```

Test-anchori (iz seedovanog SiteSettings): `tel:+381601234567`,
`mailto:info@velegradestate.rs`, `wa.me/381601234567`, `Beograd` u footer HTML-u.

**NE dirati** header/nav/lang-switcher/mobile-menu/logo/CSS-JS kaskadu (2.1).

---

## 5. Test seed helperi (`tests/test_home_page.py`)

- `_seed_site_settings(**overrides)`: `SiteSettings.load()` + popuni
  `hero_headline_sr`, `hero_cta_text_sr`, `founder_name`, `founder_title_sr`,
  `founder_bio_sr="<p>Test bio</p>"`, `phone_primary`, `whatsapp_number`,
  `email_primary`, `address`; `hero_image=""`/`founder_photo=""` (placeholder grana).
- `_make_property(**overrides)`: popuni SVA NOT NULL polja (`title`, `status`,
  `collection_type`, `property_type`, `location_city`, `location_district`,
  `area_sqm`, `area_total_sqm`, `bedrooms`, `bathrooms`, `floor`, `total_floors`,
  `parking_spaces`, `description_sr`, `description_en`); `hero_image=""` (prolazi na
  SQLite, → placeholder grana).
- `_seed_featured()`: 4× `is_featured=True, is_active=True` + 1× `is_featured=False`
  + 1× `is_featured=True, is_active=False`; jedna featured sa `price_on_request=True`.
- `_superuser(django_user_model)`, `_admin_index_path()` — mirror 2.1/1.3.

---

## 6. Granica (van obima 2.2)

Listing `/properties/` (Epik 3.1), Property Detail (3.2), Contact forma (Epik 4),
Private Collection stranica/forma (Epik 5), pun i18n/`{% loc %}`/`{% url %}` rebind
(Epik 6) — NISU u 2.2. Teaseri su samo tekst/link/CTA.

## 7. Namerno razbijena 2.1 testa (Dev GREEN-faza)

2.2 namerno dodaje `css/pages/home.css` na `/`, što obara:
- `tests/test_base_layout.py::test_home_does_not_include_pages_css_globally`
- `tests/test_base_layout.py::test_home_does_not_include_any_pages_css_globally`

Dev ih ažurira u GREEN fazi (dozvoljena, opravdana izmena). TEA ih NE dira.
