---
stepsCompleted: [1, 2, 3, 4]
status: 'final'
inputDocuments:
  - _bmad-output/planning-artifacts/PRD.md
  - _bmad-output/planning-artifacts/architecture.md
  - docs/Velegrad Estate - Projektni zadatak.docx.md
  - docs/OpenDesignFiles/
---

# Velegrad Estate - Epic Breakdown

## Overview

Ovaj dokument daje kompletnu razradu epika i priča za **Velegrad Estate**, dekomponujući zahteve iz LEAN PRD-a (§5), zaključane tehničke odluke iz arhitekture (§0–§7) i specifikacije projektnog zadatka (modeli §5.2, URL §5.4, faze §7) u implementabilne priče. Dizajn iz `docs/OpenDesignFiles/` je **konačan** — priče ga integrišu, ne preispituju.

> **Princip:** ovaj dokument **ne prepisuje** modele, dizajn ni arhitektonske odluke — **referencira** izvore. Polja modela → zadatak §5.2. Tokeni/komponente → `OpenDesignFiles/`. Tehničke odluke → arhitektura §1–§7.

## Requirements Inventory

### Functional Requirements

Izvedeno iz PRD §3 (po stranicama) i §5 (epici/priče).

**Home (`/`):**
- FR1: Fullscreen hero (slika/video, dark overlay, ime+titula, jedan tagline, jedan CTA) — sadržaj iz `SiteSettings`.
- FR2: Personal Brand sekcija (foto osnivača + bio + direktan kontakt CTA) iz `SiteSettings`.
- FR3: Signature Properties preview — 3–4 nekretnine `is_featured=True`, editorial prikaz, link na listing.
- FR4: Private Collection teaser — samo tekst + link, bez prikaza nekretnina.
- FR5: Why Velegrad sekcija — 6 stubova (ikonica + naslov + rečenica); postoji samo kao sekcija Home.
- FR6: Contact teaser — CTA ka kontaktu / direktnom kontaktu.

**About (`/about/`):**
- FR7: About / Private Advisory stranica (hero, velika foto, bio 2–3 pasusa, filozofija, servisi, CTA) iz `Page(slug=about)` + `SiteSettings`.

**Signature Properties listing (`/properties/`):**
- FR8: Lista `collection_type=signature`, `is_active=True`, max 12 prikazanih, editorial kartice (hero foto, status badge, naziv/lokacija, tip, m², spavaće sobe, cena/"Cena na upit", CTA), grid 2 kol. desktop / 1 mob.
- FR9: Server-side filteri: Location, Property Type, Price Range, Bedrooms, Status, Keyword (GET reload).

**Property Detail (`/properties/<slug>/`):**
- FR10: Hero galerija + thumbnail strip + lightbox (klik, keyboard levo/desno, X, swipe).
- FR11: Sticky info sidebar — sva relevantna polja iz `Property`.
- FR12: Premium storytelling opis (`description_sr`/`description_en`).
- FR13: Features/amenities — M2M `PropertyFeature` (ikonice + naziv, max 2 kolone).
- FR14: Floor plan (slika/PDF ako postoji) + mapa (Leaflet po koordinatama, prikaz po `show_address`).
- FR15: Agent Contact Block — foto, ime/titula, one-click tel, WhatsApp, email, mini forma → `Inquiry(inquiry_type=viewing)`.
- FR16: Slične nekretnine — max 3, curated (po lokaciji/tipu).

**Private Collection (`/private-collection/`):**
- FR17: Hero (tamna pozadina) + tekst objašnjenja, bez prikaza nekretnina.
- FR18: Intake forma → `Inquiry(inquiry_type=private_collection)`: ime, email, telefon, `property_type_wanted`, `budget_range`.

**International (`/international/`):**
- FR19: Sadržajna stranica iz `Page(slug=international)`, mora postojati i na EN.

**Contact (`/contact/`):**
- FR20: Forma sa tačno 4 polja (ime i prezime, telefon, email, poruka/tip) → `Inquiry(inquiry_type=general/consultation)`.
- FR21: Direktni kontakt — one-click tel, WhatsApp, email, adresa (opciono) iz `SiteSettings`.

**404:**
- FR22: Premium custom 404 (dizajn gotov).

**CMS Admin ("Velegrad CMS"):**
- FR23: Dashboard — metrike (aktivne nekretnine / novi upiti / featured), brze akcije, poslednji upiti.
- FR24: Nekretnine — lista filter/search, dodavanje/izmena, galerija drag&drop reorder + hero toggle, WYSIWYG opisi, dupliranje, toggle `is_active`, preview pre objave.
- FR25: Upiti — tabela sa filterima (status/datum), detalj + promena statusa, email notifikacija na nov upit.
- FR26: SiteSettings — izmena kontakta, hero, tagline/CTA, founder bio/foto.
- FR27: Multilingual unos — SR i EN polja jasno označena u admin formama.

**Inquiry sistem (cross-cutting):**
- FR28: Inquiry pipeline — čuvanje svih tipova u bazu, email notifikacija agentu, auto-reply kupcu (premium HTML template), anti-spam (rate limit + honeypot + `ip_address`).

### NonFunctional Requirements

Iz PRD §4 (detalji: zadatak §5.7–5.8, §6).

- NFR-1: **Performanse** — load < 2s desktop, < 3s na 4G; WebP, lazy load, responsive `srcset`.
- NFR-2: **Mobile-first** — breakpointi 375/768/1280px; touch targets ≥44px; body ≥16px; one-click `tel:`/`wa.me:`/`mailto:`; swipe galerija.
- NFR-3: **SEO** — meta title/description per nekretnina i stranica; Open Graph; `sitemap.xml`; `robots.txt`; Schema.org `RealEstateListing`; GA4.
- NFR-4: **Multilingual** — SR (primarni) + EN; diskretan language switcher u headeru; `/en/` prefix (Django i18n).
- NFR-5: **Sigurnost** — HTTPS (Let's Encrypt); CSRF na svim formama; rate-limit na contact/inquiry; admin na nestandardnoj putanji (`ADMIN_URL`); kredencijali u env; redovan backup; media servirana preko Nginx (ne kroz app server).

### Additional Requirements

Zaključane tehničke odluke iz arhitekture (uzeti kao dato, primeniti — ne preispitivati).

- **Platforme (§0):** Python 3.12, Django 5.2 LTS, PostgreSQL 16; bez Node/frontend build pipeline-a (dizajn je gotov custom CSS).
- **Struktura app-ova (§2):** `config` (settings paket, urls, wsgi), `core` (SiteSettings singleton, context processors, storages, sitemaps, templatetags, Unfold dashboard), `properties`, `inquiries`, `pages`.
- **Settings/env (§3):** split settings `base/dev/prod`, `django-environ`, `.env` van git-a (+ `.env.example`); env varijable za sve kredencijale.
- **Admin (§1.1):** `django-unfold` (Deep Olive/Champagne tema, dashboard `DASHBOARD_CALLBACK`), `django-admin-sortable2` (sortable inline galerija), `django-tinymce` (WYSIWYG RichText); duplikovanje kao admin action; preview preko `is_active=False` + `?preview=1` za staff; admin na `ADMIN_URL`.
- **Listing filter (§1.2):** server-side `PropertyListView` + `PropertyFilterForm` (Django forms, bez `django-filter`); `filters.js` submituje GET (bez XHR); queryset `signature` + `is_active=True` + `[:12]`.
- **i18n (§1.3):** Django `gettext` za UI (`{% trans %}`, `.po`/`.mo`, `locale/sr/`+`locale/en/`); sadržaj iz eksplicitnih `_sr`/`_en` polja (bez `django-modeltranslation`); `i18n_patterns` sa `prefix_default_language=False`; `localized()` helper + `{% loc %}` template tag; `LocaleMiddleware`; `description_fr` ostaje u modelu ali van obima prevoda.
- **Media (§1.4):** `django-storages` apstrakcija (`STORAGE_BACKEND`=local default / s3 opcija); `django-imagekit` za WebP + `srcset` varijante; prod Nginx servira `/media/`.
- **Email (§1.5):** Mailgun preko `django-anymail[mailgun]`; dev `console.EmailBackend`; dva toka (notifikacija agentu + auto-reply kupcu) u `inquiries/emails.py`; HTML + plain-text template-i pod `templates/email/`.
- **Anti-spam (§4):** `django-ratelimit` + honeypot polje u formama.
- **Mapa (§4):** Leaflet (CSS/JS vendorovan u `static/`), bez Python paketa i API ključa.
- **Static (§4, §5):** `whitenoise` kao fallback; prod primarno Nginx `collectstatic`.
- **Deploy (§6):** venv + `gunicorn` (systemd) + Nginx reverse proxy + Certbot/Let's Encrypt; backup (`pg_dump` cron + media `tar`/`rsync`); Mailgun SPF/DKIM verifikacija; staging pre review-a; **Docker NE za MVP** (§7).

### UX Design Requirements

Dizajn u `OpenDesignFiles/` je **KONAČAN** — ovo su zadaci **integracije** gotovog dizajna u Django (arhitektura §5), ne dizajniranje.

- UX-DR1: **Integracija design sistema** — kopirati `OpenDesignFiles/assets/css/{tokens,base,layout,components,utilities}.css` + `pages/*.css` u projektni `static/`, zadržati kaskadu učitavanja; reference preko `{% static %}`.
- UX-DR2: **Bazni layout** — izdvojiti zajedničko u `base.html`: `<head>` (meta/OG/Schema/GA4 blokovi), header (nav + diskretan language switcher + hamburger meni), footer.
- UX-DR3: **JS moduli** — integrisati `main.js`, `gallery.js` (lightbox — FR10), `filters.js` (GET submit — FR9), `forms.js` (validacija formi); bez build koraka, vanilla.
- UX-DR4: **9 HTML → Django template-i** — svaka stranica `{% extends "base.html" %}` i puni blokove iz konteksta (mapiranje HTML→template→URL po arhitekturi §5); placeholder SVG-ovi (`assets/images/placeholders/`) zamenjuju se `ImageField` media URL-ovima sa fallbackom.
- UX-DR5: **Brending admina** — Deep Olive (`#4A5240`) / Champagne (`#C9A96E`) brend boje primenjene u `django-unfold` temi (premium utisak, zadatak §9).

### FR Coverage Map

Mapiranje svakog FR-a na epik (nijedan FR nije ispušten). NFR-ovi su navedeni uz primarni epik realizacije; mobile-first (NFR-2) i sigurnost (NFR-5) su cross-cutting i verifikuju se kroz više epika.

- FR1 → Epic 2 — Home hero iz SiteSettings
- FR2 → Epic 2 — Home Personal Brand sekcija
- FR3 → Epic 2 — Home featured preview (is_featured)
- FR4 → Epic 2 — Home Private Collection teaser
- FR5 → Epic 2 — Home Why Velegrad sekcija (6 stubova)
- FR6 → Epic 2 — Home Contact teaser
- FR7 → Epic 4 — About / Private Advisory (Page+SiteSettings)
- FR8 → Epic 3 — Signature listing (max 12, editorial kartice)
- FR9 → Epic 3 — Server-side filteri
- FR10 → Epic 3 — Property Detail galerija + lightbox
- FR11 → Epic 3 — Property Detail sticky info
- FR12 → Epic 3 — Property Detail storytelling opis
- FR13 → Epic 3 — Property Detail features (PropertyFeature)
- FR14 → Epic 3 — Property Detail floor plan + mapa (Leaflet)
- FR15 → Epic 3 — Agent Contact Block (→ Inquiry viewing)
- FR16 → Epic 3 — Slične nekretnine (max 3)
- FR17 → Epic 5 — Private Collection stranica (hero+tekst)
- FR18 → Epic 5 — Private Collection intake forma
- FR19 → Epic 4 — International Clients (Page, SR+EN)
- FR20 → Epic 4 — Contact forma (4 polja)
- FR21 → Epic 4 — Contact direktni kontakt (SiteSettings)
- FR22 → Epic 2 — Custom 404 template/handler
- FR23 → Epic 1 — CMS Dashboard sa metrikama
- FR24 → Epic 1 — CMS Nekretnine (galerija reorder, WYSIWYG, dupliranje, toggle, preview)
- FR25 → Epic 1 — CMS Upiti (filteri, status, notifikacija)
- FR26 → Epic 1 — CMS SiteSettings
- FR27 → Epic 1 — CMS multilingual unos (SR/EN polja)
- FR28 → Epic 5 — Inquiry pipeline (čuvanje, email, anti-spam)

**NFR pokrivenost:** NFR-1 → Epic 6 (6.3); NFR-3 → Epic 6 (6.2); NFR-4 → Epic 6 (6.1, sa switcher scaffolding-om u Epic 2); NFR-2 → Epic 2 (bazni responsive) + verifikacija kroz Epic 3/4/5; NFR-5 → Epic 1 (admin path, env, CSRF) + Epic 5 (rate-limit forme) + Epic 6 (HTTPS, backup, deploy).

## Epic List

> 6 epika, usklađenih sa fazama razvoja iz projektnog zadatka §7 (PRD §5). Svaki epik isporučuje zaokruženu vrednost i ne zahteva budući epik da bi funkcionisao.

### Epic 1: Setup, CMS modeli i brendiran admin
*Faza 1.* Klijent dobija radni Django projekat sa bazom i brendiranim "Velegrad CMS" adminom kojim samostalno upravlja celokupnim sadržajem (nekretnine, upiti, podešavanja) — bez tehničkog znanja, pre nego što ijedan javni ekran postoji.
**FRs covered:** FR23, FR24, FR25, FR26, FR27 (+ temelj: svi modeli §5.2, NFR-5 deo — env/admin path/CSRF)

### Epic 2: Frontend dizajn sistem i Home
*Faza 2.* Posetilac vidi premium Home stranicu sa integrisanim konačnim dizajnom (header sa language switcher-om, footer, hamburger), napunjenu dinamičnim sadržajem iz baze, uključujući Why Velegrad sekciju i custom 404.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR22 (+ UX-DR1–5, NFR-2 bazni responsive)

### Epic 3: Signature listing i Property Detail
*Faza 3.* Posetilac pretražuje curated katalog (max 12, server-side filteri) i otvara najvažniju stranicu — Property Detail kao luxury brošuru sa galerijom/lightbox, storytelling opisom, mapom i Agent Contact Block-om koji generiše upit.
**FRs covered:** FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16

### Epic 4: Statične stranice (About, International, Contact)
*Faza 4.* Posetilac dobija produbljen personal-brand narativ (About), vodič za strane kupce (International) i ultra-jednostavnu Contact stranicu sa direktnim one-click kontaktom i formom od 4 polja.
**FRs covered:** FR7, FR19, FR20, FR21

### Epic 5: Private Collection i inquiry sistem
*Faza 5.* Kvalifikovani posetilac šalje off-market intake upit; svi tipovi upita (sa cele platforme) se čuvaju, agent dobija notifikaciju, kupac premium auto-reply, uz anti-spam zaštitu.
**FRs covered:** FR17, FR18, FR28 (+ NFR-5 deo — rate-limit/honeypot)

### Epic 6: Multilingual, SEO, performanse i deploy
*Faza 6 + 7.* Sajt postaje dvojezičan (SR/EN), SEO-optimizovan i brz, i odlazi u produkciju na VPS sa HTTPS, backup-om i obukom klijenta.
**FRs covered:** — (realizuje NFR-1, NFR-3, NFR-4 i finalizuje NFR-2/NFR-5; bez novih FR-ova)

---

## Epic 1: Setup, CMS modeli i brendiran admin

*Faza 1. Klijent dobija radni Django projekat sa bazom i brendiranim "Velegrad CMS" adminom kojim samostalno upravlja celokupnim sadržajem.*

### Story 1.1: Inicijalizacija Django projekta i okruženja

As a developer,
I want inicijalizovan Django projekat sa PostgreSQL bazom, split settings i env konfiguracijom pod Git-om,
So that postoji čvrst, reproducibilan temelj za sav dalji razvoj.

**Acceptance Criteria:**

**Given** čist repozitorijum, **When** se projekat inicijalizuje, **Then** postoji `config/` sa split settings (`base/dev/prod`) i `DJANGO_SETTINGS_MODULE` bira okruženje, **And** app-ovi `core`, `properties`, `inquiries`, `pages` su kreirani prema strukturi (arhitektura §2, §3).

**Given** zaključane platforme, **When** se podese verzije, **Then** projekat radi na Python 3.12 / Django 5.2 LTS / PostgreSQL 16 (arhitektura §0).

**Given** env strategiju, **When** se učitavaju podešavanja, **Then** `django-environ` čita `.env` (van git-a) uz `.env.example` šablon, **And** nijedan kredencijal nije u kodu (arhitektura §3, NFR-5).

**Given** requirements, **When** se instaliraju zavisnosti, **Then** `requirements/{base,dev,prod}.txt` sadrže pakete iz arhitekture §4.

**Given** bazu, **When** se pokrene `migrate` i `runserver`, **Then** konekcija na PostgreSQL preko `DATABASE_URL` uspeva i prazan projekat se diže bez greške.

**Reference:**
- **Dizajn:** — (nema UI)
- **Model §5.2:** — (bez modela u ovoj priči)
- **Arhitektura:** §0 verzije platforme, §2 struktura app-ova, §3 settings/env, §4 requirements

### Story 1.2: CMS modeli i migracije

As a developer,
I want sve domenske modele iz zadatka §5.2 implementirane sa migracijama,
So that podaci o nekretninama, upitima i sadržaju imaju trajnu šemu spremnu za admin i frontend.

**Acceptance Criteria:**

**Given** specifikaciju §5.2, **When** se modeli kreiraju, **Then** `Property`, `PropertyImage`, `PropertyFeature`, `Inquiry`, `SiteSettings`, `Page` postoje sa poljima tačno kako su definisana (bez izmišljanja polja), **And** raspoređeni su po app-ovima (`core`→SiteSettings, `properties`→Property/PropertyImage/PropertyFeature, `inquiries`→Inquiry, `pages`→Page) prema §2.

**Given** dvojezičnu šemu, **When** se definišu polja, **Then** eksplicitna `_sr`/`_en` polja postoje kako stoji u §5.2, **And** `description_fr` ostaje u modelu ali van obima prevoda (arhitektura §1.3).

**Given** pristup dvojezičnom sadržaju, **When** se čita lokalizovano polje, **Then** model ima `localized(base)` helper sa fallbackom na `_sr` (arhitektura §1.3).

**Given** SiteSettings kao singleton, **When** se pokuša drugi zapis, **Then** model garantuje tačno jedan red (arhitektura §2).

**Given** migracije, **When** se pokrene `makemigrations` + `migrate`, **Then** sve tabele se kreiraju bez grešaka i `Property.slug` se auto-generiše.

**Reference:**
- **Dizajn:** —
- **Model §5.2:** svi (Property, PropertyImage, PropertyFeature, Inquiry, SiteSettings, Page)
- **Arhitektura:** §1.3 dvojezična polja + `localized()` helper, §2 granice app-ova

### Story 1.3: Brendiran admin i dashboard

As a administrator (klijent),
I want brendiran "Velegrad CMS" admin sa dashboardom koji prikazuje ključne metrike,
So that na prvi pogled vidim stanje sajta uz očuvan premium utisak i u backendu.

**Acceptance Criteria:**

**Given** Unfold temu, **When** otvorim admin, **Then** primenjene su brend boje Deep Olive `#4A5240` / Champagne `#C9A96E` (arhitektura §1.1, zadatak §2.2).

**Given** dashboard, **When** učitam početni ekran, **Then** vidim broj aktivnih nekretnina (`is_active=True`), novih upita (`status=new`) i featured nekretnina, preko Unfold `DASHBOARD_CALLBACK` (arhitektura §1.1, FR23).

**Given** brze akcije, **When** sam na dashboardu, **Then** postoje prečice "Dodaj nekretninu" i "Upiti", **And** prikazana je tabela poslednjih upita.

**Given** sigurnost, **When** pristupam adminu, **Then** admin je na nestandardnoj putanji iz `ADMIN_URL` env varijable (arhitektura §1.1, NFR-5).

**Reference:**
- **Dizajn:** brend tokeni iz `OpenDesignFiles/assets/css/tokens.css` (boje)
- **Model §5.2:** Property, Inquiry (izvor metrika)
- **Arhitektura:** §1.1 Unfold dashboard (`DASHBOARD_CALLBACK`), NFR-5 admin path

### Story 1.4: Admin upravljanje nekretninama, upitima i podešavanjima

As a administrator (klijent),
I want potpunu admin funkcionalnost za nekretnine, upite i podešavanja sa jasnim SR/EN unosom,
So that samostalno upravljam celokupnim sadržajem bez tehničkog znanja.

**Acceptance Criteria:**

**Given** Property admin, **When** uređujem nekretninu, **Then** galerija `PropertyImage` je sortable inline (drag&drop reorder po `order`, hero toggle `is_hero`, caption) preko `django-admin-sortable2` (arhitektura §1.1, FR24).

**Given** RichText opise, **When** uređujem `description_sr/en`, **Then** dostupan je TinyMCE WYSIWYG (`django-tinymce`) (arhitektura §1.1).

**Given** dupliranje i preview, **When** izaberem action "Dupliraj", **Then** kopiraju se polja + features a resetuju slug i slike; **And** kad je `is_active=False`, staff vidi detalj preko `?preview=1` dok javnost ne (arhitektura §1.1).

**Given** Inquiry admin, **When** otvorim upite, **Then** tabela ima filtere status/datum i mogu promeniti `status` upita (FR25).

**Given** dvojezičan unos, **When** popunjavam forme, **Then** `_sr`/`_en` polja su grupisana u Unfold fieldset-ovima sa jasnim labelama (arhitektura §1.1/§1.3, FR27), **And** SiteSettings forma omogućava izmenu kontakta/hero/tagline/founder (FR26).

**Reference:**
- **Dizajn:** — (admin, Unfold tema)
- **Model §5.2:** Property, PropertyImage, Inquiry, SiteSettings
- **Arhitektura:** §1.1 (sortable inline galerija, TinyMCE, duplikovanje, preview, dvojezični fieldset-ovi)

---

## Epic 2: Frontend dizajn sistem i Home

*Faza 2. Posetilac vidi premium Home sa integrisanim konačnim dizajnom, napunjen dinamičnim sadržajem iz baze.*

### Story 2.1: Integracija dizajn sistema i bazni layout

As a posetilac,
I want konzistentan premium okvir sajta (header, footer, navigacija) sa integrisanim konačnim dizajnom,
So that svaka stranica deluje kao deo istog boutique brenda.

**Acceptance Criteria:**

**Given** OpenDesignFiles assets, **When** se integrišu, **Then** CSS kaskada `tokens→base→layout→components→utilities→pages/*` i JS (`main.js`, `gallery.js`, `filters.js`, `forms.js`) su u `static/` i referencirani preko `{% static %}` (arhitektura §5, UX-DR1/UX-DR3).

**Given** zajedničke elemente, **When** se gradi `base.html`, **Then** sadrži `<head>` (meta/OG/Schema/GA4 blokove), header (nav + diskretan language switcher + hamburger) i footer (arhitektura §5, UX-DR2).

**Given** responsive zahtev, **When** se prikaže na 375/768/1280px, **Then** layout se prilagođava, touch targets ≥44px, body ≥16px (NFR-2).

**Given** nepostojeći URL, **When** se pristupi, **Then** prikazuje se premium `404.html` preko custom handlera (FR22, zadatak §9).

**Given** nedostatak medija, **When** se renderuje slika, **Then** placeholder SVG iz `assets/images/placeholders/` služi kao fallback (arhitektura §5).

**Reference:**
- **Dizajn:** `OpenDesignFiles/assets/css/*`, `assets/js/*`, `404.html` (+ header/footer iz svih stranica)
- **Model §5.2:** SiteSettings (kontakt/footer podaci)
- **Arhitektura:** §5 integracija dizajna (base.html, static, template mapiranje), NFR-2

### Story 2.2: Home stranica povezana sa bazom

As a posetilac,
I want premium Home stranicu napunjenu dinamičnim sadržajem iz baze,
So that u prvih 5 sekundi osetim poverenje, diskreciju i ekskluzivnost.

**Acceptance Criteria:**

**Given** hero, **When** učitam Home, **Then** prikazuje se fullscreen hero (slika/video, overlay, ime+titula, jedan tagline, jedan CTA) iz `SiteSettings` (`hero_*`, `founder_*`) (FR1, zadatak §4.1-A).

**Given** Personal Brand, **When** skrolujem, **Then** sekcija prikazuje `founder_photo`, bio i kontakt CTA iz `SiteSettings` (FR2).

**Given** featured, **When** se renderuje preview, **Then** 3–4 nekretnine sa `is_featured=True` su prikazane editorial stilom sa linkom na listing (FR3).

**Given** teaser sekcije, **When** skrolujem, **Then** Private Collection teaser prikazuje samo tekst + link bez nekretnina (FR4), **And** Contact teaser ima CTA ka kontaktu (FR6).

**Given** Why Velegrad, **When** dođem do te sekcije, **Then** prikazano je 6 stubova (ikonica + naslov + rečenica) kao sekcija Home, ne zasebna stranica (FR5).

**Reference:**
- **Dizajn:** `index.html` (+ `velegrad-estate.html` za Why Velegrad sekciju)
- **Model §5.2:** SiteSettings (hero/founder polja), Property (`is_featured`)
- **Arhitektura:** §5 template integracija, §1.3 `{% loc %}` za dvojezičan sadržaj

---

## Epic 3: Signature listing i Property Detail

*Faza 3. Srce kataloga — curated listing sa server-side filterima i najvažnija stranica Property Detail.*

### Story 3.1: Signature listing sa server-side filterima

As a posetilac,
I want curated listu nekretnina sa brzim premium filterima,
So that lako pronađem nekretnine koje me zanimaju bez osećaja oglasnika.

**Acceptance Criteria:**

**Given** listing, **When** otvorim `/properties/`, **Then** prikazane su nekretnine `collection_type=signature`, `is_active=True`, max 12, kao editorial kartice (hero foto, status badge, naziv/lokacija, tip, m², spavaće sobe, cena/"Cena na upit", CTA) u gridu 2 kol. desktop / 1 mob. (FR8, zadatak §4.3).

**Given** filtere, **When** primenim Location / Property Type / Price Range / Bedrooms / Status / Keyword, **Then** queryset se filtrira server-side preko GET parametara i reloada (arhitektura §1.2, FR9).

**Given** validaciju, **When** se obrade parametri, **Then** `PropertyFilterForm` (Django forms, bez `django-filter`) validira ulaz (arhitektura §1.2).

**Given** UX filtera, **When** koristim kontrole (price slider, dropdown), **Then** `filters.js` submituje formu kao GET bez XHR-a (arhitektura §1.2).

**Given** `price_on_request=True`, **When** se renderuje kartica, **Then** prikazuje "Cena na upit" umesto cene.

**Reference:**
- **Dizajn:** `properties.html`
- **Model §5.2:** Property (collection_type, status, property_type, location_city, price, price_on_request, area_sqm, bedrooms, hero_image, is_active)
- **Arhitektura:** §1.2 server-side filter (`PropertyListView`, `PropertyFilterForm`, `filters.js` GET)

### Story 3.2: Property Detail stranica

As a potencijalni kupac,
I want detaljnu luxury-brošuru stranicu nekretnine sa galerijom i direktnim kontaktom agenta,
So that se "zaljubim" u nekretninu i lako pošaljem upit za razgledanje.

**Acceptance Criteria:**

**Given** hero galeriju, **When** otvorim detalj, **Then** prikazani su hero + thumbnail strip + lightbox sa navigacijom levo/desno, keyboard i X (preko `gallery.js`), **And** na touchu radi swipe (FR10, NFR-2).

**Given** osnovne info, **When** gledam sidebar, **Then** sticky panel prikazuje relevantna polja iz `Property` (FR11), **And** opis je storytelling `description_sr/en` preko `{% loc %}` (FR12, arhitektura §1.3).

**Given** features, **When** se renderuju, **Then** `PropertyFeature` (M2M) prikazani su sa ikonicama u max 2 kolone (FR13).

**Given** floor plan i mapu, **When** postoje, **Then** floor plan (slika/PDF) i Leaflet mapa po `latitude/longitude` se prikazuju u skladu sa `show_address` (FR14, arhitektura §4 Leaflet).

**Given** Agent Contact Block, **When** želim kontakt, **Then** blok ima foto/ime, one-click `tel:`, WhatsApp, email i mini formu koja kreira `Inquiry(inquiry_type=viewing)` (FR15, NFR-2).

**Given** slične nekretnine, **When** dođem do dna, **Then** prikazano je max 3 curated nekretnine (FR16).

**Reference:**
- **Dizajn:** `property-detail.html`
- **Model §5.2:** Property (sva polja), PropertyImage, PropertyFeature, Inquiry (viewing), SiteSettings (agent kontakt)
- **Arhitektura:** §1.3 `{% loc %}`, §4 Leaflet mapa, §5 `gallery.js` lightbox

---

## Epic 4: Statične stranice (About, International, Contact)

*Faza 4. Personal-brand narativ (About), vodič za strane kupce (International) i ultra-jednostavan Contact.*

### Story 4.1: About i International stranice iz CMS-a

As a posetilac,
I want sadržajne stranice About i International upravljane iz CMS-a, dvojezično,
So that razumem ko stoji iza Velegrada i kako funkcioniše kupovina za strance.

**Acceptance Criteria:**

**Given** About, **When** otvorim `/about/`, **Then** prikazani su hero, velika foto, bio (2–3 pasusa), filozofija, servisi i CTA iz `Page(slug=about)` + `SiteSettings` (FR7, zadatak §4.2).

**Given** International, **When** otvorim `/international/`, **Then** sadržaj (uvod, proces kupovine, pravni okvir, finansiranje, CTA) dolazi iz `Page(slug=international)` (FR19, zadatak §4.7).

**Given** dvojezičnost, **When** prebacim jezik, **Then** prikazuje se `content_sr`/`content_en` odgovarajuće sa fallbackom (arhitektura §1.3), **And** International postoji i na `/en/`.

**Given** oba slug-a, **When** se učitaju, **Then** `PageDetailView` razrešava stranicu po slug-u i prikazuje samo `is_active=True` (arhitektura §2 pages app).

**Reference:**
- **Dizajn:** `about.html`, `international.html`
- **Model §5.2:** Page (slug, title_sr/en, content_sr/en, meta_*), SiteSettings (About founder/kontakt)
- **Arhitektura:** §2 pages app (`PageDetailView`), §1.3 i18n

### Story 4.2: Contact stranica sa formom i direktnim kontaktom

As a potencijalni klijent,
I want ultra-jednostavnu Contact stranicu sa formom od 4 polja i one-click kontaktom,
So that bez frikcije stupim u direktan kontakt sa savetnikom.

**Acceptance Criteria:**

**Given** formu, **When** otvorim `/contact/`, **Then** forma ima tačno 4 polja (ime i prezime, telefon, email, poruka/tip) (FR20, zadatak §4.8).

**Given** slanje, **When** pošaljem formu, **Then** kreira se `Inquiry(inquiry_type=general/consultation)` uz CSRF zaštitu (NFR-5).

**Given** direktni kontakt, **When** gledam stranicu, **Then** prikazani su one-click `tel:`, WhatsApp (`wa.me`), `mailto:` i adresa (opciono) iz `SiteSettings` (FR21, NFR-2).

**Given** mobilni, **When** sam na telefonu, **Then** poziv i WhatsApp su one-click i prominentni, input polja velika (NFR-2, zadatak §6).

**Reference:**
- **Dizajn:** `contact.html`
- **Model §5.2:** Inquiry (general/consultation), SiteSettings (phone_primary, whatsapp_number, email_primary, address)
- **Arhitektura:** §1.5 inquiry handling (povezuje Epic 5.2), NFR-5 CSRF, §1.3 i18n UI

---

## Epic 5: Private Collection i inquiry sistem

*Faza 5. Off-market lead capture i centralizovan inquiry pipeline za sve forme platforme.*

### Story 5.1: Private Collection stranica i intake forma

As a kvalifikovani posetilac,
I want diskretnu Private Collection stranicu sa intake formom,
So that zatražim pristup off-market portfoliju bez javnog izlaganja nekretnina.

**Acceptance Criteria:**

**Given** stranicu, **When** otvorim `/private-collection/`, **Then** prikazani su hero (tamna pozadina) + tekst objašnjenja, bez ijedne prikazane nekretnine/cene/adrese (FR17, zadatak §4.5).

**Given** formu, **When** je popunim, **Then** polja su ime, email, telefon, tip nekretnine (`property_type_wanted`) i budžet (`budget_range`) (FR18).

**Given** slanje, **When** pošaljem, **Then** kreira se `Inquiry(inquiry_type=private_collection)` (FR18).

**Given** zaštitu, **When** se forma submituje, **Then** CSRF + honeypot + rate-limit su aktivni (arhitektura §4, NFR-5).

**Reference:**
- **Dizajn:** `private-collection.html`
- **Model §5.2:** Inquiry (private_collection, property_type_wanted, budget_range)
- **Arhitektura:** §1.5 email tok (realizuje se u 5.2), §4 anti-spam, NFR-5

### Story 5.2: Inquiry pipeline (čuvanje, notifikacija, auto-reply, anti-spam)

As a agent (Đorđije),
I want da svaki upit sa platforme bude sačuvan, da odmah dobijem notifikaciju, a kupac auto-reply,
So that nijedan lead nije izgubljen i kupac odmah oseti premium uslugu.

**Acceptance Criteria:**

**Given** bilo koji tip forme, **When** se upit pošalje, **Then** `Inquiry` se čuva sa `inquiry_type`, `ip_address` i `status=new` (FR28).

**Given** notifikaciju, **When** stigne nov upit, **Then** agent dobija email na `SiteSettings.email_inquiries` sa podacima upita + linkom na admin (arhitektura §1.5, FR25/FR28).

**Given** auto-reply, **When** je upit primljen, **Then** kupac dobija brendiran HTML email (premium ton) poslat preko `EmailMultiAlternatives` (arhitektura §1.5).

**Given** provajdera, **When** se šalje u produkciji, **Then** koristi se Mailgun (`django-anymail`), a u dev-u `console.EmailBackend` (arhitektura §1.5).

**Given** anti-spam, **When** bot popuni honeypot ili pređe rate-limit, **Then** upit se odbija (`django-ratelimit` + honeypot) (arhitektura §4, NFR-5).

**Reference:**
- **Dizajn:** — (email template-i pod `templates/email/`)
- **Model §5.2:** Inquiry (svi tipovi), SiteSettings (email_inquiries)
- **Arhitektura:** §1.5 Mailgun/anymail dva toka, §4 ratelimit + honeypot

---

## Epic 6: Multilingual, SEO, performanse i deploy

*Faza 6 + 7. SR/EN, optimizacija i produkcija na VPS-u sa obukom klijenta.*

### Story 6.1: Dvojezičnost SR/EN

As a strani posetilac,
I want sajt na engleskom uz srpski,
So that razumem ponudu na svom jeziku.

**Acceptance Criteria:**

**Given** routing, **When** otvorim `/en/...`, **Then** EN ima `/en/` prefiks a SR je default bez prefiksa (`i18n_patterns`, `prefix_default_language=False`) (arhitektura §1.3, NFR-4).

**Given** switcher, **When** kliknem language switcher u headeru, **Then** vodi na ekvivalentni URL na drugom jeziku (arhitektura §1.3).

**Given** UI stringove, **When** prebacim jezik, **Then** dugmad/labele/navigacija su prevedeni preko `gettext` (`.po`/`.mo`, `locale/sr/` + `locale/en/`) (arhitektura §1.3).

**Given** sadržaj iz baze, **When** prikazujem, **Then** `_sr`/`_en` polja se prikazuju po jeziku sa fallbackom na `_sr` (arhitektura §1.3), **And** FR sadržaj se ne prevodi (van obima MVP).

**Reference:**
- **Dizajn:** language switcher iz headera (svi HTML)
- **Model §5.2:** sva `_sr`/`_en` polja (Property, Page, SiteSettings, PropertyFeature)
- **Arhitektura:** §1.3 i18n (gettext + `i18n_patterns` + `localized()` helper)

### Story 6.2: SEO

As a vlasnik sajta,
I want SEO optimizaciju svake stranice i nekretnine,
So that sajt bude vidljiv na pretraživačima i deljiv na društvenim mrežama.

**Acceptance Criteria:**

**Given** meta, **When** se renderuje stranica/nekretnina, **Then** `meta_title`/`meta_description` per zapis i Open Graph tagovi su prisutni (NFR-3; polja `meta_*` iz §5.2).

**Given** sitemap/robots, **When** se pristupi `/sitemap.xml` i `/robots.txt`, **Then** sadrže Property + Page URL-ove (`django.contrib.sitemaps`) (arhitektura §4, NFR-3).

**Given** strukturne podatke, **When** se renderuje Property Detail, **Then** Schema.org `RealEstateListing` markup je prisutan (NFR-3).

**Given** analitiku, **When** se učita stranica, **Then** GA4 je integrisan preko `SiteSettings.google_analytics_id` (NFR-3).

**Reference:**
- **Dizajn:** `<head>` blokovi iz `base.html` (Story 2.1)
- **Model §5.2:** Property/Page (meta_title, meta_description), SiteSettings (google_analytics_id, seo_default_*)
- **Arhitektura:** §4 `django.contrib.sitemaps`, §5 SEO tagovi u `base.html`

### Story 6.3: Performanse i optimizacija slika

As a posetilac na mobilnom,
I want brzo učitavanje sa optimizovanim slikama,
So that premium utisak nije narušen čekanjem.

**Acceptance Criteria:**

**Given** slike, **When** se prikažu, **Then** serviraju se WebP varijante sa responsive `srcset` (`django-imagekit`, keširano) (arhitektura §1.4, NFR-1).

**Given** lazy load, **When** skrolujem, **Then** slike ispod fold-a se učitavaju lenjo (NFR-1).

**Given** target, **When** merim, **Then** load < 2s desktop / < 3s na 4G (NFR-1).

**Given** storage, **When** se generišu varijante, **Then** prolaze kroz isti `django-storages` backend (radi i sa S3) (arhitektura §1.4).

**Reference:**
- **Dizajn:** `<img>` obrasci iz dizajna (svi HTML)
- **Model §5.2:** Property.hero_image, PropertyImage.image, SiteSettings.hero_image/founder_photo
- **Arhitektura:** §1.4 `django-imagekit` + `django-storages`, NFR-1

### Story 6.4: Deploy na VPS i obuka klijenta

As a vlasnik sajta,
I want sajt u produkciji na VPS-u sa HTTPS, backup-om i obukom,
So that sajt radi pouzdano i samostalno ga održavam kroz CMS.

**Acceptance Criteria:**

**Given** server, **When** se deplojuje, **Then** Ubuntu LTS + venv + Gunicorn (systemd) + Nginx reverse proxy, sa `/static/` i `/media/` serviranim direktno sa diska (arhitektura §6, NFR-5).

**Given** TLS, **When** se pristupi sajtu, **Then** Let's Encrypt sertifikat (Certbot) sa HTTP→HTTPS redirect i HSTS (arhitektura §6, NFR-5).

**Given** backup, **When** prođe dan, **Then** `pg_dump` (cron, retencija) + media `tar`/`rsync` se izvršavaju (arhitektura §6).

**Given** email, **When** se prvi put šalje u produkciji, **Then** Mailgun domen je verifikovan (SPF/DKIM) (arhitektura §6).

**Given** prod sigurnost, **When** je `DEBUG=False`, **Then** `ALLOWED_HOSTS`, secure cookies, CSRF, rate-limit i admin path su aktivni (arhitektura §6, NFR-5), **And** Docker se ne koristi za MVP (arhitektura §7).

**Given** produkcijski rate-limit iza Nginx-a, **When** se deplojuje sa više Gunicorn worker-a, **Then** django-ratelimit mora (a) koristiti **deljeni cache backend** (Redis/Memcached) za `default` cache ili namenski `ratelimit` cache alias — umesto per-process `LocMemCache` iz MVP-a — tako da je brojač upita deljen među svim worker-ima, i (b) čitati **stvarni klijentski IP iza proxy-ja** preko `X-Forwarded-For` (pouzdani-proxy konfiguracija / `django-ipware` ili odgovarajući `RATELIMIT` IP meta key), uz Nginx `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` — umesto `REMOTE_ADDR` koji iza Nginx-a vraća deljeni proxy IP. Ovo je produkcionizacija rate-limita koji je Story 4.2 namerno pustio na `LocMemCache` + `REMOTE_ADDR` za jedno-procesni MVP (gde su `SILENCED_SYSTEM_CHECKS` `django_ratelimit.E003/W001` svesno utišani); prelazak na deljeni cache obara potrebu za tim utišavanjem (NFR-5, Story 4.2).

**Given** primopredaju, **When** se preda klijentu, **Then** klijent je obučen za samostalan rad u CMS-u (zadatak §7 Faza 7).

**Reference:**
- **Dizajn:** —
- **Model §5.2:** —
- **Arhitektura:** §3 prod settings, §6 deploy pipeline (Nginx/Gunicorn/Certbot/backup/Mailgun), §7 bez Dockera za MVP
