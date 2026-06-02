# Velegrad Estate — LEAN PRD

| | |
| :---- | :---- |
| **Proizvod** | Velegrad Estate — boutique luxury sajt za premium nekretnine |
| **Klijent** | Velegrad Estate — Đorđije Potpara |
| **Verzija PRD** | 1.0 |
| **Datum** | 2026-06-01 |
| **Autor** | John (PM) |
| **Status** | Draft za razvoj |

> **Napomena o izvorima.** Ovaj PRD je namerno kratak. On **ne prepisuje** specifikaciju — sažima je i linkuje na izvore:
> - **Projektni zadatak** (kompletna spec — tech stack, Django modeli, sve stranice, faze): [`docs/Velegrad Estate - Projektni zadatak.docx.md`](../../docs/Velegrad%20Estate%20-%20Projektni%20zadatak.docx.md)
> - **Finalni dizajn** (HTML/CSS/JS, 9 stranica — KONAČAN): [`docs/OpenDesignFiles/`](../../docs/OpenDesignFiles/)
>
> Dizajn je gotov i kopira se u radni folder tokom izrade. Ovaj PRD **ne sadrži UX/dizajn poglavlja** — za sav vizuelni identitet, layout, tokene i komponente referenca je `OpenDesignFiles/`.

---

## 1. Cilj i pozicioniranje

Velegrad Estate je boutique luxury platforma za prodaju premium i off-market nekretnina — **ne** klasičan oglasnik, već privatna advizorna usluga najvišeg standarda. Cilj sajta je da u prvih 5 sekundi prenese poverenje, diskreciju i ekskluzivnost, i da posetioca pretvori u kvalifikovan upit (poziv, WhatsApp, ili formu) ka osnivaču Đorđiju Potpari kao ličnom savetniku. Uspeh se meri premium utiskom i kvalitetom upita, ne brojem funkcionalnosti. (Detaljno pozicioniranje: zadatak §1–§2.)

---

## 2. Obim, ograničenja i ključne odluke

**Zaključano (fiksirano u zadatku):** Python/Django, PostgreSQL, Nginx + Gunicorn, Let's Encrypt (HTTPS), Git; jezici **SR (primarni) + EN**; **Docker NIJE obavezan** (opciono); deployment lokalni razvoj → Linux VPS.

**Pretpostavke za potvrdu (NISU zaključane PRD odluke):** Konkretni paketi i tehnički izbori potvrđuju se pre/na početku implementacije; PRD ne zaključava implementaciju. Sledeće su predlozi koji se verifikuju u arhitekturi:

| Tema | Predlog (za potvrdu) | Napomena |
| :---- | :---- | :---- |
| **CMS / admin** | Prilagođeni, tematizovani **Django admin** ("Velegrad CMS") — **bez Wagtail-a** | "Custom CMS" iz zadatka isporučuje se kao brendiran Django admin. Kandidati: `django-unfold` (tema, boje brenda), `django-admin-sortable2` (redosled galerije), `django-ckeditor`/TinyMCE (WYSIWYG opisi). Pokriva zadatak §5.3 uz minimalan trud. |
| **Listing filter** | **Server-side render** (Django GET parametri, reload) | AJAX/API (`/api/properties/`) iz zadatka §5.5 je **opciono / kasnije**. |
| **FR jezik** | Van obima MVP-a | FR polja (`description_fr`) ostaju u modelu ali se **ne** prevode UI/sadržaj u MVP-u. |
| **Media storage** | **Lokalni FS**, servirano preko Nginx | Apstrahovano kroz Django storage backend → S3 ostaje konfigurabilna opcija (zadatak §5.1). |
| **Email** | SMTP / transakcioni provider (SendGrid/Mailgun) — konfigurabilno | Premium HTML template, ne generički Django email (zadatak §5.6). |

**Van obima MVP-a:** FR lokalizacija, AJAX live-filter, virtual tour authoring, Facebook Pixel (opciono), relocation servis kao zaseban modul.

---

## 3. Funkcionalni zahtevi (po stranicama)

Sve stranice koriste gotov dizajn iz `OpenDesignFiles/`. Funkcionalni zahtev je: napuniti dizajn dinamičnim sadržajem iz baze i povezati forme.

### 3.1 Home (`index.html` → `/`)
- Fullscreen hero (slika/video, overlay, ime+titula, jedan tagline, jedan CTA) — sadržaj iz `SiteSettings`.
- Personal Brand sekcija (foto + bio osnivača + direktan kontakt CTA) iz `SiteSettings`.
- Signature Properties preview — 3–4 nekretnine gde `is_featured=True`, editorial prikaz, link na listing.
- Private Collection teaser (samo tekst + link, bez nekretnina).
- **Why Velegrad sekcija** — 6 stubova (ikonica + naslov + rečenica), zadatak §4.1 Sekcija E. Postoji **samo** kao sekcija Home, nije zasebna stranica.
- Contact teaser.

### 3.2 About / Private Advisory (`about.html` → `/about/`)
- Produbljeni personal brand: hero, velika foto, bio (2–3 pasusa), filozofija, servisi, CTA. Sadržaj iz `Page` (slug `about`) + `SiteSettings`.

### 3.3 Signature Properties — listing (`properties.html` → `/properties/`)
- Lista nekretnina `collection_type=signature`, `is_active=True`, **max 12 prikazanih**.
- **Filteri (server-side):** Location, Property Type, Price Range, Bedrooms, Status, Keyword. (Lifestyle filteri opciono.)
- Editorial kartice (hero foto, status badge, naziv/lokacija, tip, m², spavaće sobe, cena ili "Cena na upit", CTA Detaljnije). Grid 2 kol. desktop / 1 kol. mobilni.

### 3.4 Property Detail (`property-detail.html` → `/properties/<slug>/`)
**Najvažnija stranica.** Blokovi (svi iz `Property` + `PropertyImage` + `PropertyFeature`):
- Hero galerija + thumbnail strip + lightbox (keyboard/levo-desno) — JS već u `gallery.js`.
- Osnovno info (sticky sidebar): sva polja iz modela.
- Premium opis (storytelling, `description_sr/en`).
- Features/amenities (ikonice, M2M `PropertyFeature`).
- Floor plan (slika/PDF, ako postoji), Mapa (embed po koordinatama, ako `show_address`/koordinate postoje).
- **Agent Contact Block** (foto, ime, tel one-click, WhatsApp, email, mini forma → `Inquiry` tipa `viewing`).
- Slične nekretnine — max 3 (curated po lokaciji/tipu).

### 3.5 Private Collection (`private-collection.html` → `/private-collection/`)
- Hero (tamna pozadina) + tekst objašnjenja, **bez prikaza nekretnina**.
- Intake forma → `Inquiry` tipa `private_collection`: ime, email, telefon, tip nekretnine, budžet.
- Po slanju: auto-reply kupcu + email notifikacija agentu.

### 3.6 International Clients (`international.html` → `/international/`)
- Sadržajna stranica (uvod, proces kupovine za strance, pravni okvir, finansiranje, CTA). Iz `Page` (slug `international`). Mora postojati i na EN.

### 3.7 Contact (`contact.html` → `/contact/`)
- Forma sa **tačno** 4 polja (ime+prezime, telefon, email, poruka/tip) → `Inquiry` tipa `general`/`consultation`.
- Direktan kontakt: tel one-click, WhatsApp, email, adresa (opciono) — iz `SiteSettings`.

### 3.8 404 (`404.html`)
- Premium custom 404 (dizajn gotov).

### 3.9 CMS Admin ("Velegrad CMS" — tematizovani Django admin)
- **Dashboard:** broj aktivnih nekretnina / novih upita / featured; brze akcije; poslednji upiti.
- **Nekretnine:** lista sa filter/search; dodavanje/izmena; upload galerije drag&drop + reorder + hero; WYSIWYG opisi; dupliranje; toggle `is_active`; preview pre objave.
- **Upiti (Inquiry):** tabela sa filterima (status/datum); detalj + promena statusa; email notifikacija na nov upit.
- **Podešavanja (SiteSettings):** kontakt, hero, tagline/CTA, founder bio/foto.
- **Multilingual unos:** SR i EN polja jasno označena u formama.

**Modeli baze:** `Property`, `PropertyImage`, `PropertyFeature`, `Inquiry`, `SiteSettings`, `Page` — kompletna polja u zadatku §5.2 (uzeti kao dato, ne ponavljati ovde). URL struktura: zadatak §5.4.

---

## 4. Nefunkcionalni zahtevi (NFR)

| # | NFR | Cilj / izvor |
| :---- | :---- | :---- |
| NFR-1 | **Performanse** | Load < 2s (desktop), < 3s na 4G. WebP, lazy load, responsive `srcset`. |
| NFR-2 | **Mobile-first** | Breakpointi 375/768/1280px; touch targets ≥44px; body ≥16px; one-click `tel:`/`wa.me:`/`mailto:`; swipe galerija. |
| NFR-3 | **SEO** | Meta title/description per nekretnina i stranica; Open Graph; `sitemap.xml`; `robots.txt`; Schema.org `RealEstateListing`; GA4. |
| NFR-4 | **Multilingual** | SR (primarni) + EN; diskretan language switcher u headeru; `/en/` prefix (Django i18n). |
| NFR-5 | **Sigurnost** | HTTPS (Let's Encrypt); CSRF na svim formama; rate-limit na contact/inquiry (anti-spam); admin na nestandardnoj putanji; kredencijali u env varijablama; redovan backup baze; media ne servirati direktno. |

(Detalji: zadatak §5.7, §5.8, §6.)

---

## 5. Epici i priče (visok nivo)

> 6 epica, usklađenih sa fazama razvoja (zadatak §7). Priče su na visokom nivou — **ne** detaljni story fajlovi.

### Epik 1 — Setup, CMS modeli i admin
*Faza 1. Cilj: radni Django projekat + baza + brendiran admin kojim klijent upravlja sadržajem.*
- 1.1 Inicijalizacija Django projekta, PostgreSQL, env konfiguracija, Git.
- 1.2 Implementacija svih modela (`Property`, `PropertyImage`, `PropertyFeature`, `Inquiry`, `SiteSettings`, `Page`) + migracije.
- 1.3 Tematizovani admin + dashboard sa metrikama.
- 1.4 Admin funkcionalnost: nekretnine (galerija drag&drop reorder, WYSIWYG opisi, dupliranje, toggle, preview), upiti i SiteSettings.

### Epik 2 — Frontend dizajn sistem i Home
*Faza 2. Cilj: integrisan dizajn iz OpenDesignFiles + dinamičan Home (uklj. Why Velegrad sekciju).*
- 2.1 Integracija dizajn sistema (`OpenDesignFiles/` assets: tokeni, base, layout, komponente) + bazni layout: header (nav, language switcher), footer, hamburger meni.
- 2.2 Home stranica povezana sa bazom (hero, personal brand, featured preview, Why Velegrad sekcija, teaser sekcije).

### Epik 3 — Listing i Property Detail
*Faza 3. Cilj: srce kataloga.*
- 3.1 Signature Properties listing + server-side filteri (Location/Type/Price/Bedrooms/Status/Keyword), max 12, editorial kartice.
- 3.2 Property Detail: galerija + lightbox, sticky info, storytelling opis, features, floor plan, mapa, Agent Contact Block, slične nekretnine (max 3).

### Epik 4 — Statične stranice
*Faza 4. Cilj: About, International, Contact.*
- 4.1 About / Private Advisory i International Clients iz `Page` + `SiteSettings`.
- 4.2 Contact stranica + forma (4 polja) + direktni kontakt elementi.

### Epik 5 — Private Collection i inquiry sistem
*Faza 5. Cilj: off-market lead capture.*
- 5.1 Private Collection stranica (hero + tekst, bez nekretnina) + intake forma.
- 5.2 Inquiry pipeline: čuvanje u bazu (svi tipovi), email notifikacija agentu, auto-reply kupcu (premium template), anti-spam (rate limiting + IP zapis).

### Epik 6 — Multilingual, SEO, performanse i deploy
*Faza 6 + 7. Cilj: SR/EN, optimizacija, produkcija.*
- 6.1 i18n SR/EN: `/en/` routing, language switcher, prevodi UI + dvojezičan sadržaj iz modela.
- 6.2 SEO: meta/OG per stranica i nekretnina, sitemap, robots, Schema.org, GA4.
- 6.3 Performanse: WebP konverzija, lazy load, `srcset`, keširanje.
- 6.4 Deploy na VPS: Nginx + Gunicorn + Let's Encrypt, media preko Nginx, backup; obuka klijenta. (Docker opciono.)

---

## 6. Materijali od klijenta

Blokirajući unosi pre lansiranja (zadatak §8): foto osnivača, logo (SVG), bio SR/EN, tagline/CTA, kontakt podaci; min. 3 nekretnine sa 8–15 foto + opisi SR/EN + cene. Opciono: hero video, floor planovi, virtual tour linkovi.

---

*Kraj PRD-a. Za sve što nije ovde — referenca je projektni zadatak i `OpenDesignFiles/`.*
