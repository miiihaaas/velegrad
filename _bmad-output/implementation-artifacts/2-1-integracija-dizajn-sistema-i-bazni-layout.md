---
story-id: 2-1-integracija-dizajn-sistema-i-bazni-layout
title: Integracija dizajn sistema i bazni layout
epic: 2
epic-title: "Frontend dizajn sistem i Home (Faza 2)"
module: "templates, static, config, pages"
status: ready-for-dev
created: 2026-06-02
author: SM (Scrum Master)
fr-coverage: "FR22 (custom premium 404); UX-DR1/UX-DR2/UX-DR3 (integracija konačnog dizajna, base.html sa head/header/footer); NFR-2 (mobile-first 375/768/1280, touch ≥44px, body ≥16px); IR #1 (i18n od prvog template-a — UI stringovi kroz {% trans %})"
references:
  - _bmad-output/planning-artifacts/epics.md                 # Epic 2 / Story 2.1 — IZVOR ISTINE za AC (oko linije 275)
  - _bmad-output/planning-artifacts/architecture.md          # §5 integracija OpenDesignFiles (base.html, static, template mapiranje), §1.3 i18n ({% trans %}/{% loc %}), NFR-2
  - _bmad-output/planning-artifacts/PRD.md                   # FR22 / §3.8 (404), NFR-2 (mobile-first), UX-DR
  - "docs/OpenDesignFiles/index.html"                        # head / header (nav + lang-switcher + hamburger) / footer — izvor base.html markup-a
  - "docs/OpenDesignFiles/404.html"                          # markup error stranice (error-page blok, error.css)
  - "docs/OpenDesignFiles/assets/css/"                        # CSS kaskada: tokens→base→layout→components→utilities→pages/*
  - "docs/OpenDesignFiles/assets/js/"                         # main.js (sticky header, hamburger, lang-switcher), gallery/filters/forms.js
  - "docs/OpenDesignFiles/assets/images/placeholders/"        # placeholder SVG-ovi (fallback za media)
  - _bmad-output/implementation-artifacts/1-3-brendiran-admin-i-dashboard.md  # format priče + test obrazac (Django test client, SQLite, pytest-django)
  - _bmad-output/implementation-artifacts/sprint-status.yaml
---

# Story 2.1: Integracija dizajn sistema i bazni layout

## Opis

As a posetilac,
I want konzistentan premium okvir sajta (header, footer, navigacija) sa integrisanim konačnim dizajnom,
So that svaka stranica deluje kao deo istog boutique brenda.

Ovo je **prva priča Epika 2 (Faza 2)** i prelazak sa „čistog backend-a" (Epik 1: CMS modeli + brendiran admin) na **javni frontend**. Cilj je integrisati **konačan, gotov dizajn sistem** iz `docs/OpenDesignFiles/` u Django i postaviti **bazni layout (`base.html`)** koji će svaka naredna stranica naslediti (`{% extends "base.html" %}`).

Trenutno stanje (nasleđeno):
- `static/` je **prazan** (samo `.gitkeep`); `templates/` ima samo `admin/index.html` (override iz 1.3) + `.gitkeep`. `base.html` i `404.html` **NE postoje** — grade se ovde.
- `config/settings/base.py` već ima `STATIC_URL = "static/"`, `STATICFILES_DIRS = [BASE_DIR / "static"]`, `STATIC_ROOT`, `TEMPLATES["DIRS"] = [BASE_DIR / "templates"]`, `"django.contrib.staticfiles"` u `INSTALLED_APPS`, `LANGUAGES`/`LOCALE_PATHS`/`USE_I18N=True` (iz 1.1) — pa je infrastruktura spremna; ova priča **koristi** je, ne uvodi je iznova.
- `config/urls.py` montira admin na `ADMIN_URL` i `tinymce/`. Custom `handler404` **ne postoji** — dodaje se ovde.
- `pages/` app postoji ali je **prazan** (`models.py`, `apps.py`, bez `views.py`/`urls.py`).

**Obim ove priče = BAZNI LAYOUT + DIZAJN INTEGRACIJA + 404 + PLACEHOLDER FALLBACK:**
1. Premeštanje (kopiranje) celokupne CSS kaskade i JS-a iz `docs/OpenDesignFiles/assets/{css,js}` u projektni `static/`, referencirano preko `{% static %}`.
2. Premeštanje placeholder SVG-ova u `static/` i uspostavljanje fallback obrasca za nedostajuće media.
3. `base.html` — izdvojen iz `index.html`: `<head>` sa blokovima (title/meta/OG/Schema/GA4), Google Fonts preconnect+link, CSS kaskada, `header` (logo + `site-nav` + diskretan `lang-switcher` + `mobile-menu-toggle` hamburger), `mobile-menu`, `footer` (brend/kontakt/nav/copyright), `main.js` na dnu. Blokovi koje stranice popunjavaju (`{% block content %}`, `{% block extra_css %}`, `{% block extra_js %}`, `{% block title %}`, meta blokovi).
4. Custom premium `404.html` (iz `404.html` dizajna, `error.css`) + `handler404` u `config.urls`.
5. Sve **UI stringove** u template-ima pisati kroz `{% trans %}` od starta (IR #1) — `{% load i18n %}`. Pun dvojezični prelaz (i18n_patterns, `.po`/`.mo`, language switcher koji stvarno menja jezik) je **Epik 6**; ovde je language switcher **diskretan UI element** (markup + main.js vizuelno ponašanje iz dizajna), bez funkcionalnog set_language routinga.

**STROGO van obima → 2.2 i kasniji Epici (vidi Dev Notes — Granica):**
- **Home sadržaj iz baze (hero/founder/featured/Why Velegrad iz `SiteSettings`/`Property`)** = **Story 2.2** (`home.html` / `HomeView`). U 2.1 NE pravimo `HomeView` sa punim sadržajem; dozvoljeno je samo minimalno (vidi AC6) da `/` ne baci 500 i da se base layout može vizuelno verifikovati.
- **Konkretne stranice** (about/contact/listing/detail/international/private-collection) = **Epici 3–5**; njihovi `pages/*.css` se kopiraju u `static/` (kaskada je celovita) ali se template-i NE prave ovde.
- **Pun i18n** (i18n_patterns, set_language, `.po`/`.mo`, `{% loc %}` za sadržaj iz baze) = **Epik 6**. Ovde samo `{% trans %}` higijena na UI stringovima + markup language switchera.
- **`gallery.js`/`filters.js`/`forms.js`** se kopiraju u `static/` (deo kaskade) ali se uključuju per-stranica (`{% block extra_js %}`) u kasnijim Epicima; u `base.html` ide samo `main.js`.

## Acceptance Criteria

> AC su izvedeni primarno iz **epics.md Story 2.1** (autoritativna lista — pet Given/When/Then linija), dopunjeni arhitekturom §5/§1.3, PRD FR22/NFR-2 i konkretnim imenima fajlova/klasa iz `docs/OpenDesignFiles/`. Svaki AC je konkretan i testabilan (Django test client + SQLite test baza, pytest-django — vidi Dev Notes). Reference na klase/strukturu su iz pregledanog dizajna: `site-header`, `site-nav`, `lang-switcher`, `mobile-menu-toggle`, `mobile-menu`, `site-footer`, `error-page`.

- [x] **AC1 — CSS kaskada i JS u `static/`, referencirani preko `{% static %}` (epics 2.1 AC1, arh §5, UX-DR1/UX-DR3).** Celokupni dizajn assets se kopira iz `docs/OpenDesignFiles/assets/{css,js}` u projektni `static/` uz očuvanu strukturu:
  - CSS (tačan redosled kaskade): `static/css/tokens.css` → `base.css` → `layout.css` → `components.css` → `utilities.css`, plus `static/css/pages/{home,about,contact,error,international,private-collection,properties,property-detail}.css`.
  - JS: `static/js/main.js`, `gallery.js`, `filters.js`, `forms.js`.
  - U `base.html` se globalna kaskada (`tokens→base→layout→components→utilities`) i `main.js` referenciraju isključivo preko `{% static %}` (NE hardkodovani putevi, NE relativni `assets/...` iz dizajna). `main.js` `<script>` tag nosi `defer` atribut (verno dizajnu — `index.html` linija 341).
  **Testabilni kriterijum:** svi gore navedeni fajlovi postoje u `static/` (test asertuje postojanje na disku — npr. `(settings.BASE_DIR / "static/css/tokens.css").exists()` za ključne fajlove kaskade); GET `/` (ili render `base.html`) vraća HTML koji sadrži `href`/`src` ka `{% static %}` razrešenim URL-ovima u tačnom redosledu kaskade (`tokens.css` pre `base.css` pre `layout.css` ...), i `main.js` `src` (sa `defer` atributom u istom `<script>` tagu).

- [x] **AC2 — `base.html` sa `<head>` blokovima + header + footer (epics 2.1 AC2, arh §5, UX-DR2).** `templates/base.html` je izdvojen iz `index.html` i sadrži:
  - `<html lang="...">` (sr default), `<head>`: `charset`, `viewport`, Google Fonts (`preconnect` + Bodoni Moda / DM Sans link), CSS kaskada preko `{% static %}`.
  - **Override-abilni blokovi u head-u:** `{% block title %}` (default „Velegrad Estate"), `{% block meta_description %}`, `{% block og %}` (OG/Twitter meta), `{% block schema %}` (JSON-LD Schema.org), `{% block ga4 %}` (Google Analytics 4 — placeholder/uslovno, prazno dok GA4 ID ne stigne), `{% block extra_css %}` (za `pages/*.css`).
  - **Header (`<header class="site-header" role="banner">`):** logo (link na `/`), `site-nav` glavna navigacija, **diskretan** `lang-switcher` (SR | EN dugmad, `hide-mobile`), `mobile-menu-toggle` hamburger (`aria-label`, `aria-expanded`).
  - **`mobile-menu`** (`role="dialog"`) sa nav linkovima (struktura iz dizajna).
  - **Footer (`<footer class="site-footer" role="contentinfo">`):** brend/logo, `site-footer__contact-info`, nav liste, `site-footer__copyright`, drugi `lang-switcher`.
  - `{% block content %}` između header-a i footer-a; `main.js` (+ `{% block extra_js %}`) pred `</body>`.
  **Testabilni kriterijum:** render `base.html` (ili GET `/` u 2.1 minimal home) → HTML sadrži `class="site-header"`, `class="site-nav"`, `class="lang-switcher"`, `class="mobile-menu-toggle"` (sa `aria-expanded`), `class="site-footer"`; sadrži `<title>` i meta description; sadrži oba bloka (header pre `{% block content %}`, footer posle). Dete-template koji `{% extends "base.html" %}` i override-uje `{% block title %}` menja `<title>`.

- [x] **AC3 — i18n higijena: UI stringovi kroz `{% trans %}` od prvog template-a (IR #1, arh §1.3).** Svaki UI string u `base.html`/`404.html` (navigacija, dugmad, footer labele, language switcher `aria-label`-i, error poruke) je obavijen `{% trans %}` (template-i imaju `{% load i18n %}`). Sadržaj iz baze (Epik 2.2+) ide preko `_sr`/`_en` polja / `{% loc %}` — ali u 2.1 nema sadržaja iz baze u `base.html`. Pun i18n routing (i18n_patterns, set_language, `.po`/`.mo`) je Epik 6 — ovde samo string-marking.
  **Testabilni kriterijum:** `base.html` i `404.html` sadrže `{% load i18n %}`. IR #1 (arh §1.3) traži da SVI UI stringovi budu obeleženi — pa NIJE „Dev bira"; sledeći minimalni skup je OBAVEZAN i mora biti `{% trans %}`-obavijen i pokriven asercijom:
  - header navigacioni linkovi (`site-nav` stavke),
  - hamburger `aria-label` (`mobile-menu-toggle`),
  - SR/EN labele oba language switcher-a,
  - footer copyright (`site-footer__copyright`) i footer nav labele,
  - oba 404 CTA dugmeta („Vratite se na početnu", „Kontaktirajte nas").

  Test asertuje da su ti stringovi obeleženi (npr. čitanjem template fajla — prisustvo `{% trans` u blizini odgovarajućih markera; ILI odsustvo neobeleženih varijanti ključnih stringova u izvoru). `python manage.py check` prolazi (template-i validni). (Napomena: bez `.po`/`.mo` `{% trans %}` vraća sam string — render i dalje radi.)

- [x] **AC4 — Responsive / mobile-first: 375 / 768 / 1280px, touch ≥44px, body ≥16px (epics 2.1 AC3, NFR-2).** Integrisani dizajn je mobile-first i poštuje NFR-2:
  - `<meta name="viewport" content="width=device-width, initial-scale=1.0">` u `base.html`.
  - Body tekst ≥16px (dizajn `--text-body: 1rem` = 16px; `base.css` postavlja `body { font-size: var(--text-body) }`, a na ≥1280px `--text-body-lg` 18px) — kaskada se mora učitati u tačnom redosledu (AC1) da tokeni stignu pre upotrebe.
  - Touch targets (dugmad, nav linkovi, hamburger, lang-switcher) ≥44px — obezbeđuje dizajn (`components.css`/`layout.css`); 2.1 mora samo verno preneti markup (klase) iz dizajna, bez „skraćivanja".
  - Hamburger `mobile-menu-toggle` se pojavljuje na užim breakpointima, `lang-switcher.hide-mobile` se skriva na mobilnom (iz dizajna).
  **Testabilni kriterijum:** `base.html` sadrži tačan `viewport` meta tag; CSS kaskada je učitana u redosledu iz AC1 (tokeni pre ostalog); test asertuje da je `viewport` meta prisutan i da su `mobile-menu-toggle` i `lang-switcher.hide-mobile` klase prisutne u markup-u. (Vizuelna provera breakpointa/≥44px je manuelni QA korak naveden u DoD — automatski test verifikuje markup/meta/kaskadu, ne piksele.)

- [x] **AC5 — Custom premium `404.html` preko `handler404` (epics 2.1 AC4, FR22, PRD §3.8, arh §5).** Isporučuje se `templates/404.html` (premium dizajn iz `docs/OpenDesignFiles/404.html`: `error-page` blok — `<main class="error-page">`, `error-page__code` „404", naslov, poruka, `error-page__ctas` sa dugmetom „Vratite se na početnu" → `/` i „Kontaktirajte nas" → contact ruta) i registruje se **custom `handler404`** u `config/urls.py`.
  - **404 template MORA `{% extends "base.html" %}`** (NIJE opcija — zaključano): error stranica nasleđuje isti `site-header` + `site-footer` okvir kao i sve ostale stranice, radi konzistentnosti brenda. `error-page` sadržaj ide u `{% block content %}`, a `pages/error.css` se učitava preko `{% block extra_css %}` (`{% static 'css/pages/error.css' %}`). **Standalone 404 (bez header/footer okvira) NIJE dozvoljen** — iako je izvorni `docs/OpenDesignFiles/404.html` standalone (bez header/footer, sa sopstvenom CSS kaskadom), markup se MORA restrukturirati u base-extending template (vidi T5), a ne kopirati doslovno.
  - **handler404 = eksplicitan view (zaključano):** `pages/views.py` `def custom_404(request, exception): return render(request, "404.html", status=404)` i `handler404 = "pages.views.custom_404"` u `config/urls.py`. (`pages` je u `INSTALLED_APPS`; eksplicitan view daje jasan `status=404` i jedan dosledan put — NE oslanjati se na Django-ov implicitni default handler.)
  - Linkovi koriste `{% url %}` gde rute postoje, inače `/` apsolutno; nikako hardkodovan `.html`.
  **Testabilni kriterijum:** GET nepostojećeg URL-a (npr. `/nepostojeca-stranica/`) sa `DEBUG=False` vraća **HTTP 404** i renderovani HTML sadrži (a) „404" i `error-page` markup (premium template, ne Django default „Not Found"), I (b) `site-header` I `site-footer` (dokaz da 404 nasleđuje base okvir — standalone template ne bi prošao ovaj test). (Napomena za test: Django servira custom `handler404` samo kad je `DEBUG=False`; test mora postaviti `DEBUG=False` / `override_settings(DEBUG=False)` i koristiti validan `ALLOWED_HOSTS` koji sadrži `testserver` — vidi Dev Notes.)

- [x] **AC6 — Placeholder SVG fallback za nedostajuće media (epics 2.1 AC5, arh §5).** SVIH 9 placeholder SVG-ova iz `docs/OpenDesignFiles/assets/images/placeholders/` se kopira u `static/images/placeholders/` (kompletna lista, bez izostavljanja): `hero-placeholder.svg`, `founder-portrait.svg`, `property-1.svg`, `property-2.svg`, `property-3.svg`, `property-4.svg`, `logo.svg`, `floor-plan.svg`, `property-detail-hero.svg`. Uspostavlja se **fallback obrazac** koji se koristi kad `ImageField` media URL ne postoji: tj. template helper / custom template tag / `{% if obj.image %}{{ obj.image.url }}{% else %}{% static 'images/placeholders/...' %}{% endif %}` konvencija, dokumentovana za upotrebu u 2.2+. U 2.1 se isporučuje: (a) SVG fajlovi u `static/images/placeholders/`, (b) **reusable mehanizam** fallback-a (npr. `{% include %}` partial, custom tag, ili jasno dokumentovan inline obrazac u Dev Notes) koji se demonstrira bar na jednom mestu (logo u header/footer ili hero placeholder). `base.html` logo koristi `{% static %}` placeholder dok klijentski SVG logo (IR #4) ne stigne — sa TODO komentarom.
  **Testabilni kriterijum:** SVIH 9 placeholder SVG-ova postoji u `static/images/placeholders/` (test asertuje postojanje SVIH na disku — `hero-placeholder.svg`, `founder-portrait.svg`, `property-1.svg`, `property-2.svg`, `property-3.svg`, `property-4.svg`, `logo.svg`, `floor-plan.svg`, `property-detail-hero.svg`); render `base.html` koristi `{% static %}` placeholder za logo (HTML sadrži `images/placeholders/logo.svg` u `src`-u, ILI dokumentovani fallback obrazac je prisutan i pokriven jednostavnim render testom).

- [x] **AC7 — `base.html` se renderuje, `/` ne puca, `python manage.py check` čist (regresija).** Da bi se base layout mogao vizuelno i test-validirati, postoji **minimalna home ruta**: `/` mapira na laku view koja renderuje template koji `{% extends "base.html" %}` (npr. privremeni `home.html` sa `{% block content %}` placeholder-om, ILI direktni `TemplateView`) — **bez sadržaja iz baze** (to je 2.2). `python manage.py check` prolazi; admin (Epik 1) i `tinymce/` rute i dalje rade (nepromenjene); `migrate` na SQLite i dalje prolazi (ova priča ne uvodi migracije). Static kaskada se razrešava pod test client-om (`{% static %}` daje `href`-ove; `collectstatic` NIJE potreban za render — vidi Dev Notes).
  **Testabilni kriterijum:** GET `/` (test client) → **HTTP 200** i HTML sadrži `site-header` i `site-footer` (base layout renderovan); `python manage.py check` izlazi bez grešaka; GET admin index na `ADMIN_URL` i dalje → 200; GET `/admin/` i dalje → 404 (regresija iz 1.3 očuvana).

## Tasks / Subtasks

- [x] **T1 — Premesti CSS kaskadu i JS u `static/`** *(AC1, AC4)*
  - [x] Kopiraj `docs/OpenDesignFiles/assets/css/*.css` → `static/css/` (tokens, base, layout, components, utilities) uz očuvanu strukturu.
  - [x] Kopiraj `docs/OpenDesignFiles/assets/css/pages/*.css` → `static/css/pages/` (home, about, contact, error, international, private-collection, properties, property-detail).
  - [x] Kopiraj `docs/OpenDesignFiles/assets/js/*.js` → `static/js/` (main, gallery, filters, forms).
  - [x] NE menjaj sadržaj CSS/JS-a (dizajn je konačan); samo premesti. (Reference na `assets/...` unutar CSS-a, npr. fontovi/slike, proveriti — ako CSS referencira relativne putanje, uskladiti sa `static/` strukturom ili ostaviti kako jeste ako su apsolutne/inline.)

- [x] **T2 — Premesti placeholder SVG-ove + fallback obrazac** *(AC6)*
  - [x] Kopiraj SVIH 9 `docs/OpenDesignFiles/assets/images/placeholders/*.svg` → `static/images/placeholders/`: `hero-placeholder.svg`, `founder-portrait.svg`, `property-1.svg`, `property-2.svg`, `property-3.svg`, `property-4.svg`, `logo.svg`, `floor-plan.svg`, `property-detail-hero.svg` (svi obavezni — T7 asertuje postojanje svih).
  - [x] Uspostavi reusable fallback mehanizam (preporuka: kratak `{% if obj.image %}...{% else %}{% static 'images/placeholders/X.svg' %}{% endif %}` obrazac ILI custom template tag) i dokumentuj ga u Dev Notes za 2.2+.
  - [x] Demonstriraj fallback na logo-u u header/footer (`{% static 'images/placeholders/logo.svg' %}` + TODO za klijentski logo, IR #4).

- [x] **T3 — Konfiguracija static/templates u settings (verifikacija)** *(AC1, AC2, AC7)*
  - [x] Potvrdi u `config/settings/base.py`: `STATIC_URL`, `STATICFILES_DIRS = [BASE_DIR / "static"]`, `STATIC_ROOT`, `TEMPLATES["DIRS"] = [BASE_DIR / "templates"]`, `"django.contrib.staticfiles"` u `INSTALLED_APPS`, `"django.template.context_processors.request"` u context_processors — sve već postoji iz 1.1/1.3; dodaj SAMO ako nešto nedostaje (ne diraj postojeće).
  - [x] (Bez `collectstatic` u dev/test — `{% static %}` razrešava URL-ove direktno.)

- [x] **T4 — `base.html`** *(AC2, AC3, AC4)*
  - [x] Kreiraj `templates/base.html`. `{% load static i18n %}` na vrhu.
  - [x] `<head>`: charset, `viewport` (`width=device-width, initial-scale=1.0`), Google Fonts preconnect+link (Bodoni Moda + DM Sans, iz dizajna), CSS kaskada preko `{% static %}` u redosledu `tokens→base→layout→components→utilities`, pa `{% block extra_css %}`.
  - [x] Head blokovi: `{% block title %}`, `{% block meta_description %}`, `{% block og %}`, `{% block schema %}`, `{% block ga4 %}` (prazno/uslovno dok GA4 ID ne stigne — TODO).
  - [x] Header: `site-header` (logo link `/`, `site-nav`, diskretan `lang-switcher` sa SR|EN dugmadima i `hide-mobile`, `mobile-menu-toggle` sa `aria-label`/`aria-expanded`), `mobile-menu` dialog. Sve UI labele kroz `{% trans %}`.
  - [x] `{% block content %}{% endblock %}` između header i footer.
  - [x] Footer: `site-footer` (brend/logo, kontakt info, nav liste, copyright, drugi lang-switcher). UI labele kroz `{% trans %}`. (Kontakt podaci kao statički placeholder u 2.1; vezivanje na `SiteSettings` je 2.2 — ostavi TODO.)
  - [x] Pred `</body>`: `<script src="{% static 'js/main.js' %}" defer></script>` pa `{% block extra_js %}`. (`defer` verno prati izvorni dizajn — `docs/OpenDesignFiles/index.html` linija 341 učitava `main.js` sa `defer`-om; main.js je null-guarded pa ne puca ni bez njega, ali se markup mora poklopiti sa dizajnom.)
  - [x] Zameni inline base64 logo iz dizajna `{% static %}` placeholder logom (T2) — ne kopiraj base64 blob.

- [x] **T5 — Custom `404.html` + `handler404`** *(AC5, AC3)*
  - [x] Kreiraj `templates/404.html` koji **MORA `{% extends "base.html" %}`** (zaključano AC5 — nasleđuje `site-header`/`site-footer`). **NE kopiraj doslovno** `docs/OpenDesignFiles/404.html` — izvorni dizajn je **standalone** (nema header/footer, ima sopstvenu punu CSS kaskadu). Dev **restrukturira** markup:
    - Premesti `error-page` blok (`<main class="error-page">`, `error-page__code` „404", naslov, poruka, `error-page__ctas`) iz standalone fajla u `{% block content %}` base-extending template-a.
    - Premesti error-specifične stilove u `{% block extra_css %}` → `<link rel="stylesheet" href="{% static 'css/pages/error.css' %}">` (NE ponovo učitavaj globalnu kaskadu — base je već daje).
    - CTA dugmad preko `{% url %}` / `/` (ne hardkodovan `.html`). `{% load static i18n %}` + `{% trans %}` na svim stringovima.
  - [x] Registruj **eksplicitan** `handler404` (zaključano AC5): u `pages/views.py` `def custom_404(request, exception): return render(request, "404.html", status=404)`, pa `handler404 = "pages.views.custom_404"` u `config/urls.py`. (`pages` je u `INSTALLED_APPS`; ovo je jedini normativni put — ne oslanjati se na Django implicitni default.)

- [x] **T6 — Minimalna home ruta (samo da base layout živi; sadržaj je 2.2)** *(AC7)*
  - [x] Dodaj `/` rutu u `config/urls.py` (ili preko `pages/urls.py` include). Najlakše: privremeni `home.html` koji `{% extends "base.html" %}` sa placeholder `{% block content %}`, serviran preko `TemplateView.as_view(template_name="home.html")` ILI lake `pages.views.home`.
  - [x] **Bez sadržaja iz baze** — to je 2.2. Ostavi jasan TODO/komentar „Home sadržaj iz SiteSettings/Property → Story 2.2".
  - [x] Minimalni `home.html` u 2.1 **NE uključuje** `pages/home.css` preko `{% block extra_css %}` — bazni layout bez per-stranica CSS-a je dovoljan da se verifikuje kaskada. (`pages/*.css` se uključuju per-stranica u kasnijim Epicima/2.2 kada stranica dobije pravi sadržaj.)
  - [x] Potvrdi da admin (`ADMIN_URL`) i `tinymce/` rute ostaju nepromenjene; `/admin/` i dalje 404.

- [x] **T7 — Verifikacija (render + static + 404 + regresija)** *(AC1–AC7)*
  - [x] Novi test fajl u ROOT `tests/` (npr. `tests/test_base_layout.py`), pytest-django, `config.settings.test` (SQLite, in-memory).
  - [x] **Static postojanje:** asertuj da ključni fajlovi postoje na disku — `static/css/tokens.css`, `base.css`, `layout.css`, `components.css`, `utilities.css`, `static/js/main.js`, i SVIH 9 placeholder SVG-ova u `static/images/placeholders/`: `hero-placeholder.svg`, `founder-portrait.svg`, `property-1.svg`, `property-2.svg`, `property-3.svg`, `property-4.svg`, `logo.svg`, `floor-plan.svg`, `property-detail-hero.svg` (AC1, AC6).
  - [x] **Base render:** GET `/` → 200; HTML sadrži `site-header`, `site-nav`, `lang-switcher`, `mobile-menu-toggle`, `site-footer`; CSS `href`-ovi se pojavljuju u redosledu kaskade (tokens pre base pre layout...) — konkretna asercija nad pozicijama, npr. `html.index("tokens.css") < html.index("base.css") < html.index("layout.css")`; `main.js` `src` prisutan I njegov `<script>` tag sadrži `defer`; `viewport` meta prisutan (AC1, AC2, AC4, AC7).
  - [x] **i18n higijena:** `base.html` i `404.html` sadrže `{% load i18n %}` i `{% trans %}` (čitanje template fajla ili render bez greške) (AC3).
  - [x] **Block override:** child template (ili inline) koji extend-uje base i menja `{% block title %}` → `<title>` se menja (AC2).
  - [x] **404:** `override_settings(DEBUG=False)` (+ `ALLOWED_HOSTS` sadrži `testserver`) → GET `/nepostojeca/` → HTTP 404 i HTML sadrži „404"/`error-page` **I** `site-header` **I** `site-footer` (dokaz da 404 extend-uje base, ne standalone) (AC5).
  - [x] **Regresija:** GET admin index (`ADMIN_URL`, superuser) → 200; GET `/admin/` → 404; `python manage.py check` čist (AC7).

## Dev Notes

- **Izvor istine za AC = epics.md Story 2.1** (pet Given/When/Then linija oko linije 275): (1) CSS kaskada `tokens→base→layout→components→utilities→pages/*` + JS u `static/` preko `{% static %}`; (2) `base.html` sa head/header (nav + diskretan language switcher + hamburger)/footer; (3) responsive 375/768/1280, touch ≥44px, body ≥16px; (4) custom premium `404.html` preko handlera; (5) placeholder SVG fallback. Arhitektura §5 daje template mapiranje i static obrazac; §1.3 nameće `{% trans %}` od prvog template-a (IR #1).

- **GRANICA 2.1 vs 2.2 vs Epici 3–6 (KRITIČNO — pažljivo razdvojiti):**
  - **U 2.1 (OVA priča) = OKVIR:** dizajn assets → `static/`, `base.html` (head/header/footer skelet sa blokovima), custom `404` + handler, placeholder SVG fallback obrazac, minimalna `/` ruta da layout živi, `{% trans %}` higijena. **NE puni sadržaj iz baze.**
  - **U 2.2 (NE ovde) = HOME SADRŽAJ:** `HomeView`/`home.html` puni hero/founder/featured/Why Velegrad iz `SiteSettings`/`Property` (FR1–FR6). U 2.1 `/` je samo placeholder okvir; footer kontakt podaci su statički placeholder (vezivanje na `SiteSettings` je 2.2).
  - **`core/context_processors.py` (site_settings) se NE pravi u 2.1.** Stiže u Story 2.2 kada se `SiteSettings` vrednosti ubacuju u template kontekst (npr. footer kontakt iz baze). U 2.1 footer kontakt je **statički placeholder** u `base.html` — ne dodavati kontekst procesor ovde (sprečava 2.2 iznenađenje i nepotrebno proširenje obima).
  - **U Epicima 3–5 (NE ovde) = konkretne stranice:** about/contact/listing/detail/international/private-collection template-i. Njihovi `pages/*.css` i `gallery/filters/forms.js` se KOPIRAJU u `static/` (kaskada je celovita), ali se template-i i view-ovi NE prave u 2.1. U `base.html` ide samo `main.js`; ostali JS-evi se uključuju per-stranica preko `{% block extra_js %}`.
  - **U Epiku 6 (NE ovde) = PUN i18n + SEO + perf:** `i18n_patterns`, `set_language`/`{% translate_url %}`, `.po`/`.mo`, `{% loc %}` za sadržaj iz baze, funkcionalan language switcher, GA4 ID, Schema/OG vrednosti. U 2.1: language switcher je **markup + main.js vizuelno ponašanje** (iz dizajna, prebacuje `is-active` klasu — NE menja stvarni jezik); GA4/Schema/OG su **prazni blokovi** spremni za punjenje. Pravilo: ako je *string-marking + skelet bloka* → 2.1; ako je *stvarno prevođenje/routing/SEO vrednosti* → Epik 6.

- **Stanje okruženja (nasleđeno, NE menjati osim ako AC izričito traži):**
  - FLAT layout, bez Docker-a; venv `.venv\Scripts\python.exe` (Windows — `python`, ne `python3`).
  - `config/settings/base.py` već ima `STATIC_URL`, `STATICFILES_DIRS=[BASE_DIR/"static"]`, `STATIC_ROOT`, `TEMPLATES["DIRS"]=[BASE_DIR/"templates"]`, `APP_DIRS=True`, `"django.contrib.staticfiles"`, context processor `request`, `LANGUAGES`/`LOCALE_PATHS`/`USE_I18N=True`. Ova priča KORISTI to; ne uvodi iznova. Proveri samo da ништa ne fali pre nego što dodaš.
  - `config/urls.py` montira admin na `ADMIN_URL` + `tinymce/`. Dodaješ `/` rutu i `handler404` — NE diraj postojeće rute.
  - `pages/` app postoji (`models.py`, `apps.py`), bez `views.py`/`urls.py` — kreiraš ih ako biraš pages-based home/404 view.

- **CSS kaskada — redosled je load-bearing:** `tokens.css` MORA pre `base.css` (CSS varijable `--color-*`, `--text-body` itd. se definišu u tokens, koriste svuda). Redosled `tokens→base→layout→components→utilities→pages/*` je iz `index.html` (link redosled) i arh §5 — ne menjati. `pages/*.css` se uključuje per-stranica preko `{% block extra_css %}`, NE globalno u base.

- **Body ≥16px / touch ≥44px (NFR-2) već u dizajnu:** `tokens.css` ima `--text-body: 1rem` (16px), `base.css` postavlja `body { font-size: var(--text-body) }` i na `@media (min-width: 1280px)` diže na `--text-body-lg` (18px). Dugmad/nav touch ≥44px obezbeđuje `components.css`/`layout.css`. Zadatak 2.1 je da **verno prenese markup/klase** iz dizajna (ne da reimplementira CSS) — pa ako se kaskada učita u redosledu, NFR-2 je zadovoljen. Automatski test verifikuje markup + viewport meta + redosled kaskade; piksel/breakpoint provera (375/768/1280, ≥44px) je manuelni QA korak (DoD).

- **Language switcher u 2.1 = diskretan UI, NE funkcionalan routing:** dizajn (`main.js` „Language Switcher (visual only)") samo prebacuje `is-active` klasu — ne menja jezik. Markup (`lang-switcher` SR|EN + `aria-label`) ide u header (`hide-mobile`) i footer. Stvarni `set_language`/`i18n_patterns` je Epik 6. Drži ovu granicu — ne implementiraj routing ovde.

- **404 — layout, handler, DEBUG i test (KRITIČNO):**
  - **Layout zaključan (extends base):** `templates/404.html` MORA `{% extends "base.html" %}` da nasledi `site-header`/`site-footer` (konzistentnost brenda). Izvorni `docs/OpenDesignFiles/404.html` je **standalone** (bez okvira, sopstvena kaskada) — NE kopirati doslovno; restrukturirati: `error-page` blok u `{% block content %}`, `pages/error.css` u `{% block extra_css %}` (NE ponovo učitavati globalnu kaskadu — base je daje). Test asertuje `site-header` I `site-footer` u 404 HTML-u (standalone bi pao test).
  - **Handler zaključan (eksplicitan view):** jedini normativni put je `pages/views.py` `def custom_404(request, exception): return render(request, "404.html", status=404)` + `handler404 = "pages.views.custom_404"` u `config/urls.py`. (`pages` je već u `INSTALLED_APPS`.) NE oslanjati se na Django implicitni default — eksplicitan view daje jasan `status=404` i jedan dosledan put.
  - **DEBUG i test:** Django renderuje custom `handler404` SAMO kad je `DEBUG=False`. Sa `DEBUG=True` (dev/test default) dobijaš Django-ov debug 404, ne premium template. Zato 404 test mora `@override_settings(DEBUG=False)` i obezbediti da `ALLOWED_HOSTS` sadrži `testserver` (test.py već ima `["localhost","127.0.0.1","testserver"]`). Proveri da `raise_request_exception`/`client.raises_request_exception` ne maskira (Django test client default ok za 404).

- **Static pod test client-om:** `{% static %}` razrešava URL-ove iz `STATIC_URL` — NE traži `collectstatic` ni postojanje fajla na disku za RENDER (template tag samo gradi string `href`). Zato render testovi rade bez `collectstatic`. Postojanje fajlova se testira odvojeno (`Path.exists()` nad `static/...`), jer kopiranje assets-a JESTE deliverable (AC1/AC6). `ManifestStaticFilesStorage` se NE koristi u test/dev (koristi se default), pa nema hash-manifest problema.

- **Inline base64 logo iz dizajna — NE kopirati:** `index.html` ima ogroman inline base64 PNG logo u header/footer. U `base.html` zameni ga `{% static 'images/placeholders/logo.svg' %}` (placeholder iz dizajna) + TODO za klijentski SVG logo (IR #4 eksterni input, možda još nije stigao — ne blokirati priču na čekanju).

- **i18n (IR #1):** od OVOG template-a UI stringovi idu kroz `{% trans %}` (sprint-status napomena IR #1). U 2.1 NE praviti `.po`/`.mo` ni `i18n_patterns` (to je Epik 6) — samo string-marking. Bez `.mo` fajlova `{% trans "X" %}` vraća „X" (identitet), pa render radi normalno. `LANGUAGE_CODE="sr-latn"`, `LANGUAGES=[("sr",...),("en",...)]` su već u base.py.

- **Testovi — ROOT `tests/`, pytest-django, SQLite (env odluka, isto kao 1.2/1.3):** lokalni PostgreSQL NIJE dostupan. Testovi koriste **Django test client** nad **SQLite in-memory** (`config/settings/test.py`, `pytest.ini` → `DJANGO_SETTINGS_MODULE=config.settings.test`). Prati obrazac iz `tests/test_admin_dashboard.py` (login superuser, GET render, asercije nad HTML-om). Novi fajl npr. `tests/test_base_layout.py`. Za render `base.html` nije potreban login (javna stranica), za admin regresiju jeste superuser.

- **ADMIN_URL u regresionom testu:** T7 admin-regresioni test MORA izvesti admin putanju iz `settings.ADMIN_URL` na isti način kao 1.3 testovi — vidi `tests/test_admin_dashboard.py` helper `_admin_index_path()` (gradi mounted admin index path iz `settings.ADMIN_URL`). NE hardkodovati `/admin/` kao admin putanju — env konfiguriše stvarni admin path, pa hardkodovan put pravi krhak test. (`/admin/` se i dalje očekuje da vraća 404 — to je regresija iz 1.3, NE stvarna admin ruta.)

- **Granica sa Story 1.3 admin override-om:** `templates/admin/index.html` (dashboard override iz 1.3) ostaje netaknut. Novi `base.html`/`404.html`/`home.html` su FRONTEND template-i — ne dele ništa sa admin template-ima i ne smeju uticati na admin render (Unfold). Proveri da dodavanje `base.html` u `templates/` ne hvata admin (admin koristi `admin/index.html`, ne `base.html`).

- **Git poruke na engleskom** (zadatak §9) — ali ova priča je samo spec; commit radi dev priča.

## Definition of Done

- [x] CSS kaskada (`tokens, base, layout, components, utilities` + `pages/*`) i JS (`main, gallery, filters, forms`) kopirani u `static/{css,js}` uz očuvanu strukturu; globalna kaskada + `main.js` u `base.html` referencirani preko `{% static %}` u tačnom redosledu (AC1).
- [x] SVIH 9 placeholder SVG-ova kopirano u `static/images/placeholders/` (`hero-placeholder`, `founder-portrait`, `property-1..4`, `logo`, `floor-plan`, `property-detail-hero`); uspostavljen reusable fallback obrazac za nedostajuće media i demonstriran (logo u header/footer) (AC6).
- [x] `templates/base.html` izdvojen iz dizajna: `<head>` sa override-abilnim blokovima (title/meta/OG/Schema/GA4/extra_css), header (logo + `site-nav` + diskretan `lang-switcher` + `mobile-menu-toggle`), `mobile-menu`, footer (`site-footer`), `{% block content %}`, `main.js` + `{% block extra_js %}` na dnu (AC2).
- [x] Svi UI stringovi u `base.html`/`404.html` obeleženi `{% trans %}` (`{% load i18n %}`); bez sadržaja iz baze u base layout-u (IR #1) (AC3).
- [x] Mobile-first poštovan: `viewport` meta prisutan, kaskada učitana u redosledu (body ≥16px iz tokena), touch/nav klase verno prenete iz dizajna; manuelni QA na 375/768/1280 i touch ≥44px potvrđen (AC4).
- [x] Custom premium `templates/404.html` (`error-page` markup) koji `{% extends "base.html" %}` + `handler404` u `config/urls.py`; GET nepostojećeg URL-a sa `DEBUG=False` → HTTP 404 sa premium markup-om (ne Django default) renderovanim UNUTAR base okvira (`site-header` + `site-footer`), konzistentno sa zaključanim AC5 (AC5).
- [x] Minimalna `/` ruta renderuje `base.html` okvir (bez sadržaja iz baze — to je 2.2); GET `/` → 200 sa `site-header`/`site-footer` (AC7).
- [x] `python manage.py check` čist; admin (`ADMIN_URL`) i `/admin/`→404 regresija očuvana; `migrate` na SQLite i dalje prolazi; novi testovi u ROOT `tests/` prolaze (AC7, T7).
- [x] **Obim ispoštovan:** isporučen SAMO okvir (static integracija + base.html + 404 + placeholder fallback + minimalni home); Home sadržaj iz baze (2.2), konkretne stranice (Epici 3–5) i pun i18n/SEO (Epik 6) NISU dirani (vidi Dev Notes — Granica).
