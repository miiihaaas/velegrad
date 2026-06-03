---
story-id: 6-1-dvojezicnost-sr-en
title: "Interface Contract — Dvojezičnost SR/EN (i18n_patterns, language switcher, gettext UI, {% loc %} za sadržaj iz baze)"
epic: 6
module: "config (urls/settings/middleware), core (templatetags), templates, locale"
phase: RED (TDD) — failing contract definisan PRE implementacije
author: TEA (Test Architect)
created: 2026-06-03
test-file: tests/test_i18n.py
references:
  - _bmad-output/implementation-artifacts/6-1-dvojezicnost-sr-en.md  # IZVOR ISTINE za AC1–AC5 + T1–T7
  - _bmad-output/implementation-artifacts/5-2-inquiry-pipeline-cuvanje-notifikacija-auto-reply-anti-spam-interface-contract.md  # REFERENTNI format (6.1 prati 1:1)
  - config/settings/base.py     # MIDDLEWARE (LocaleMiddleware se DODAJE); LANGUAGE_CODE/USE_I18N/LANGUAGES/LOCALE_PATHS već postoje (nepromenjeni)
  - config/urls.py              # plain path() → wrap u i18n_patterns(prefix_default_language=False); admin/tinymce VAN; set_language fallback VAN
  - core/models.py              # LocalizedMixin.localized(self, base) — aktivni jezik + _sr fallback; {% loc %} ga zove
  - core/templatetags/          # NE POSTOJI — 6.1 kreira __init__.py + i18n_content.py
  - templates/base.html         # <html lang="sr"> → <html lang="{{ LANGUAGE_CODE }}">; switcher <button> → <a href> (translate_url)
  - pages/views.py              # page_view get_object_or_404 — view-ovi se NE diraju
  - properties/models.py        # Property.description_sr/_en (description_en NIJE blank=True); title NIJE lokalizovan
  - pages/models.py             # Page.title_sr/_en + content_sr/_en (title_en/content_en su blank=True)
---

# Interface Contract — Story 6.1

> Ovaj dokument je MAŠINSKI ugovor između RED-faze testova (`tests/test_i18n.py`)
> i buduće implementacije (Dev/GREEN faza). Definiše TAČNE izmene settings/urls/
> templatetag/templates/locale koje testovi asertuju. Implementacija koja zadovolji
> ovaj ugovor čini RED testove zelenim BEZ izmene testova.
>
> **Reuse-first / bez migracija:** 6.1 NE menja nijedan model (`LocalizedMixin`/
> `Property`/`Page`/`SiteSettings`/`PropertyFeature` netaknuti — `_sr/_en` polja i
> `localized()` već postoje). NE dira view-ove. 6.1 DODAJE: `LocaleMiddleware`,
> `i18n_patterns` wrapping, `set_language` fallback, `{% loc %}` tag, switcher
> href/akciju, `.po`/`.mo` prevode i template prelaze na `{% loc %}`.
> **Cross-cutting:** Dev (u GREEN) invertuje 4 postojeća `/en/→404` testa — TEA ih
> NE dira; ovaj fajl ima samo guard test za novo očekivano ponašanje (`/en/contact/ → 200`).

---

## 1. `config/settings/base.py` — `LocaleMiddleware`

**LOCKED izmena:** u `MIDDLEWARE` dodati `"django.middleware.locale.LocaleMiddleware"`
**STROGO posle** `"django.contrib.sessions.middleware.SessionMiddleware"` i **STROGO pre**
`"django.middleware.common.CommonMiddleware"` (Django obavezan redosled: LocaleMiddleware
čita jezik iz sesije/cookie/URL prefiksa i mora pre CommonMiddleware koje radi APPEND_SLASH).

Rezultujući redosled (relevantni isečak):
```
"django.contrib.sessions.middleware.SessionMiddleware",
"django.middleware.locale.LocaleMiddleware",      # ← DODATO (6.1)
"django.middleware.common.CommonMiddleware",
```

- **NE menjati** `LANGUAGE_CODE="sr-latn"`, `USE_I18N=True`, `LANGUAGES=[("sr",…),("en",…)]`,
  `LOCALE_PATHS=[BASE_DIR/"locale"]` — već su ispravni.
- (Preporuka za `<html lang>`, vidi §4) dodati `"django.template.context_processors.i18n"`
  u `TEMPLATES["OPTIONS"]["context_processors"]` ILI obezbediti `LANGUAGE_CODE` u template-u
  preko `{% get_current_language %}` / `request.LANGUAGE_CODE` — bilo koji put je prihvatljiv,
  bitno je da `{{ LANGUAGE_CODE }}` razreši na aktivni jezik.

**Testovi koji ovo asertuju:** `test_locale_middleware_is_between_session_and_common`.

---

## 2. `config/urls.py` — `i18n_patterns(prefix_default_language=False)` + `set_language`

**LOCKED struktura:**
- Import: `from django.conf.urls.i18n import i18n_patterns` (uz postojeći `from django.urls import include, path`).
- **Lokalizabilne rute** (`home` `""`, `properties`, `property-detail`, `about`,
  `international`, `contact`, `private-collection`) **wrap-ovati u**
  `i18n_patterns(<rute>, prefix_default_language=False)`. → SR (default sr-latn) bez prefiksa;
  EN dobija `/en/` prefiks.
- **OSTAJU VAN `i18n_patterns` (običan `urlpatterns`, bez `/en/`):**
  - `path(f"{settings.ADMIN_URL}/", admin.site.urls)` — admin (NFR-5, deterministička putanja).
  - `path("tinymce/", include("tinymce.urls"))`.
  - `path("i18n/", include("django.conf.urls.i18n"))` — daje `set_language` view kao
    **opcioni fallback** (registrovan VAN prefiksa). **Switcher ga NE koristi** (vidi §4 — switcher je LOCKED na `{% translate_url %}` GET linkove).
- Zadržati `handler404 = "pages.views.custom_404"`.

**Invarijanta (prefix_default_language=False):** `reverse("home")=="/"`,
`reverse("about")=="/about/"`, `reverse("contact")=="/contact/"`,
`reverse("properties")=="/properties/"` (SR bez prefiksa). Ako bilo koji `reverse()`
dobije `/sr/` ili `/en/` prefiks → `prefix_default_language` je pogrešno postavljen (popravi
settings, NE test).

**Testovi koji ovo asertuju:** `test_sr_routes_return_200_no_prefix`,
`test_en_routes_return_200_with_prefix`, `test_localizable_reverses_have_no_en_prefix`,
`test_admin_stays_outside_i18n_patterns`, `test_set_language_fallback_is_registered_outside_prefix`,
`test_en_contact_route_is_200_guard`, `test_contact_post_under_en_prefix_redirects_and_creates_inquiry`.

---

## 3. `core/templatetags/i18n_content.py` — `{% loc %}` simple_tag

**Kreiraju se DVA nova fajla:**
- `core/templatetags/__init__.py` (prazan).
- `core/templatetags/i18n_content.py`.

**LOCKED potpis i ponašanje:**
```python
from django import template
from django.utils.translation import get_language

register = template.Library()


@register.simple_tag
def loc(obj, base):
    if hasattr(obj, "localized"):
        return obj.localized(base)            # primarni put (svi dvojezični modeli)
    lang = (get_language() or "sr")[:2]        # robustan fallback ako obj nema localized
    return getattr(obj, f"{base}_{lang}", "") or getattr(obj, f"{base}_sr", "")
```

- Pozива `obj.localized(base)` → aktivni jezik (`_en` pod EN) sa **fallbackom na `_sr`**.
- **Rezultat je auto-escape-ovan** (`simple_tag` NE markuje kao safe) — `|safe` se primenjuje
  EKSPLICITNO u template-u SAMO na admin-curated HTMLField-ove preko obrasca
  `{% loc obj "base" as var %}{{ var|safe }}` (filter se NE može direktno na tag —
  `{% loc %}|safe` je sintaksno nemoguće).
- **Razrešava SAMO `sr`/`en`** (`get_language()[:2]`); `_fr` se NIKADA ne renderuje
  (FR nije u `LANGUAGES`; fallback uvek vodi na `_sr`).
- Učitava se preko `{% load i18n_content %}` (`core` je u `INSTALLED_APPS`, `APP_DIRS=True`).

**Testovi koji ovo asertuju:** `test_loc_tag_renders_active_language`,
`test_loc_tag_falls_back_to_sr_when_en_empty`, `test_localized_helper_matches_active_language`
(+ svi AC4 render testovi koji prolaze kroz template-e).

---

## 4. `templates/base.html` — `<html lang>` + language switcher

**LOCKED izmene:**
- **`<html lang="sr">` → `<html lang="{{ LANGUAGE_CODE }}">`** (l.2). Pod `/en/` renderuje
  `lang="en"`, pod SR (default) renderuje `lang="sr"` (aktivni jezik se razrešava na `"sr"`,
  NE `"sr-latn"`, jer `sr-latn` nije u `LANGUAGES`). `LANGUAGE_CODE` obezbediti preko i18n
  context processora / `{% get_current_language as LANGUAGE_CODE %}` / `request.LANGUAGE_CODE`.
- **Switcher (LOCKED — `{% translate_url %}` GET `<a href>` linkovi, NE `set_language` POST forma):**
  oba switchera (header `lang-switcher hide-mobile` l.58–62 + footer `lang-switcher` l.119–123)
  `<button data-lang=...>` → `<a href="{% translate_url 'en' %}" class="lang-switcher__btn …">EN</a>`
  i `<a href="{% translate_url 'sr' %}" class="lang-switcher__btn …">SR</a>`.
  `translate_url` čuva tekuću putanju i samo dodaje/skida `/en/` prefiks
  (`/ ↔ /en/`, `/properties/ ↔ /en/properties/`).
  - **Čist GET link — BEZ forme, BEZ `{% csrf_token %}`** (nema CSRF zamke; test client
    preskoči CSRF a prod POST bi vratio 403).
  - **Očuvati TAČNO container klase:** `class="lang-switcher hide-mobile"` (header, ×1) i
    `class="lang-switcher"` (footer, ×1); linkovi idu UNUTAR tih kontejnera. Zadržati
    `lang-switcher__btn` klasu na anchor-ima i `{% trans "SR" %}`/`{% trans "EN" %}` labele.
  - `is-active` izvesti iz aktivnog jezika (NE hardkodovano na SR).
- **NE dirati** nav placeholder linkove `href="#"` (l.49–54, l.76–80) — navigacija, van obima 6.1.

**Testovi koji ovo asertuju:** `test_sr_render_has_html_lang_sr`, `test_en_render_has_html_lang_en`,
`test_switcher_uses_get_anchor_links_not_post_form`, `test_switcher_links_to_en_equivalent_from_sr_page`,
`test_switcher_links_back_to_sr_equivalent_from_en_page`, `test_switcher_container_classes_preserved`.
(Plus regresija: postojeći `tests/test_base_layout.py::test_two_lang_switchers_present` mora ostati zelen.)

### Template sadržaj iz baze → `{% loc %}` (AC4, T5)
- `home.html`: `hero_headline`/`hero_cta_text`/`founder_title` → `{% loc site_settings "…" %}` (plain);
  `founder_bio` → `{% loc site_settings "founder_bio" as v %}{{ v|safe }}` (HTMLField).
- `about.html`: `title` → `{% loc page "title" %}`; `content` → `{% loc page "content" as v %}{{ v|safe }}`;
  `founder_title` → `{% loc site_settings "founder_title" %}`.
- `international.html`: `title` → `{% loc page "title" %}`; `content` → `{% loc page "content" as v %}{{ v|safe }}`.
- `property-detail.html`: `description` → `{% loc property "description" as v %}{{ v|safe }}`;
  feature `f.name` → `{% loc f "name" %}`; `founder_title` → `{% loc site_settings "founder_title" %}`.
- **`property.title` OSTAJE `{{ property.title }}`** (jedno polje); `properties.html` `{{ p.title }}` ostaje plain.
- `|safe` SAMO na admin-curated HTMLField-ovima (`content`/`description`/`founder_bio`); `_fr` se NE renderuje.

---

## 5. `locale/sr/` + `locale/en/` — `.po`/`.mo`

**LOCKED artefakti:**
- `locale/sr/LC_MESSAGES/django.po` + `locale/en/LC_MESSAGES/django.po` — generisani
  (`manage.py makemessages -l sr -l en`), **postoje i NISU prazni**.
- **EN `msgstr` popunjeni** za ključne UI labele (npr. „Kontakt"→„Contact", „Početna"→„Home",
  „Detaljnije"→„Details", „Cena na upit"→„Price on request", „soba"→„rooms"…). SR `msgstr`
  mogu ostati prazni (fallback na `msgid`, koji je srpski) — fokus je EN.
- `locale/sr/LC_MESSAGES/django.mo` + `locale/en/LC_MESSAGES/django.mo` — kompajlirani
  (`manage.py compilemessages`), **postoje** (čekirani u git — CI ne pokreće `compilemessages`).
- **`gettext("Kontakt") == "Contact"`** pod `activate("en")` (zavisi od kompajliranog `.mo`).

**Testovi koji ovo asertuju:** `test_locale_po_files_exist_and_non_empty`, `test_locale_mo_files_exist`,
`test_gettext_translates_ui_label_under_en`, `test_en_render_contains_translated_ui_label`.

---

## 6. Mapiranje AC → testovi

| AC | Predmet | Testovi |
|----|---------|---------|
| AC1 | Routing (i18n_patterns, LocaleMiddleware, reverse, admin VAN) | `test_sr_routes_return_200_no_prefix`, `test_en_routes_return_200_with_prefix`, `test_localizable_reverses_have_no_en_prefix`, `test_locale_middleware_is_between_session_and_common`, `test_admin_stays_outside_i18n_patterns` |
| AC2 | Switcher (translate_url GET linkovi) + `<html lang>` | `test_sr_render_has_html_lang_sr`, `test_en_render_has_html_lang_en`, `test_switcher_uses_get_anchor_links_not_post_form`, `test_switcher_links_to_en_equivalent_from_sr_page`, `test_switcher_links_back_to_sr_equivalent_from_en_page`, `test_switcher_container_classes_preserved`, `test_set_language_fallback_is_registered_outside_prefix` |
| AC3 | gettext UI prevodi (.po/.mo) | `test_locale_po_files_exist_and_non_empty`, `test_locale_mo_files_exist`, `test_gettext_translates_ui_label_under_en`, `test_en_render_contains_translated_ui_label` |
| AC4 | DB sadržaj kroz `{% loc %}` (_sr fallback) | `test_property_description_localizes_to_en`, `test_property_description_localizes_to_sr`, `test_property_description_falls_back_to_sr_when_en_empty`, `test_page_title_falls_back_to_sr_when_en_empty`, `test_page_title_localizes_to_en_when_set`, `test_loc_tag_renders_active_language`, `test_loc_tag_falls_back_to_sr_when_en_empty`, `test_localized_helper_matches_active_language` |
| AC5 | Cross-cutting `/en/→404` inverzija + form POST pod `/en/` | `test_en_contact_route_is_200_guard`, `test_contact_post_under_en_prefix_redirects_and_creates_inquiry` (+ Dev u GREEN invertuje 4 postojeća testa) |

---

## 7. Cross-cutting napomena (Dev u GREEN, NE TEA)

Dev u GREEN fazi invertuje 4 postojeća `/en/→404` testa (status `404` → `200`) i preimenuje ih:
- `tests/test_contact_page.py::test_en_contact_route_is_404`
- `tests/test_private_collection.py::test_en_private_collection_route_is_404`
- `tests/test_static_pages.py::test_en_international_returns_404_no_i18n_patterns`
- `tests/test_static_pages.py::test_en_about_returns_404_no_i18n_patterns`

`reverse()` testovi (npr. `test_about_route_reverses_to_expected_path`) OSTAJU NEPROMENJENI i zeleni.
Ovaj kontrakt fajl SAMO kodira novo očekivano ponašanje preko guard testa
`test_en_contact_route_is_200_guard` (i ne dira tuđe test fajlove).
