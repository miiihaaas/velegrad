---
story-id: 1-3-brendiran-admin-i-dashboard
title: Brendiran admin i dashboard
epic: 1
epic-title: "Setup, CMS modeli i brendiran admin (Faza 1)"
module: "core, config"
status: ready-for-dev
created: 2026-06-02
author: SM (Scrum Master)
fr-coverage: "FR23 (brendiran admin / dashboard sa metrikama); NFR-5 (admin path — već postavljen u 1.1, ovde se ne menja, samo se potvrđuje)"
references:
  - _bmad-output/planning-artifacts/epics.md               # Epic 1 / Story 1.3 — IZVOR ISTINE za AC
  - _bmad-output/planning-artifacts/architecture.md         # §1.1 django-unfold tema + DASHBOARD_CALLBACK, §2 core/admin.py, §3 settings/env
  - _bmad-output/planning-artifacts/PRD.md                  # FR23 (Dashboard — metrike, brze akcije, poslednji upiti)
  - "docs/Velegrad Estate - Projektni zadatak.docx.md"      # §2.2 brend boje (Deep Olive / Champagne), §9 premium CMS utisak
  - "docs/OpenDesignFiles/assets/css/tokens.css"            # brend tokeni (boje) — izvor hex vrednosti
  - _bmad-output/implementation-artifacts/sprint-plan.md
  - _bmad-output/implementation-artifacts/1-1-inicijalizacija-django-projekta-i-okruzenja.md  # ADMIN_URL montaža + CSRF baseline (gotovo)
  - _bmad-output/implementation-artifacts/1-2-cms-modeli-i-migracije.md                        # 6 modela + SiteSettings singleton (gotovo)
---

# Story 1.3: Brendiran admin i dashboard

## Opis

As a administrator (klijent),
I want brendiran "Velegrad CMS" admin sa dashboardom koji prikazuje ključne metrike,
So that na prvi pogled vidim stanje sajta uz očuvan premium utisak i u backendu.

Ova priča pretvara funkcionalan ali nestilizovan Django admin (iz 1.1, montiran na `ADMIN_URL`) u **brendiran "Velegrad CMS"** sa premium utiskom (zadatak §9). Nadovezuje se na:

- **1.1** — admin je već montiran na nestandardnu `ADMIN_URL` putanju, CSRF baseline aktivan, `django-unfold` već je u `requirements/base.txt` (ali NIJE instaliran u venv-u i NIJE u `INSTALLED_APPS`).
- **1.2** — svih 6 modela postoji (`Property`, `PropertyImage`, `PropertyFeature`, `Inquiry`, `SiteSettings`, `Page`); `SiteSettings` je singleton sa `localized()` helperom; dashboard metrike čitaju ove modele preko ORM-a.

Obim ove priče je **admin LJUSKA (shell) + DASHBOARD**: instalacija i konfiguracija `django-unfold` teme (brend boje, naslov/header/site title, login branding), Unfold dashboard landing strana sa karticama metrika (`DASHBOARD_CALLBACK` koji broji nekretnine/upite/featured preko 1.2 modela), **dashboard index template override koji renderuje te kartice/akcije/tabelu iz konteksta callback-a**, brze akcije i tabela poslednjih upita, te registracija `SiteSettings` singleton admina (samo izmena, bez add/delete) i **minimalna registracija `Property`/`Inquiry` admina (obavezna — da `reverse()` na admin rute u brzim akcijama radi)**. Boje se uzimaju iz dizajn tokena: **Deep Olive `#4A5240` / Champagne `#C9A96E`** (arh §1.1, zadatak §2.2, `tokens.css`).

**STROGO van obima → 1.4** (vidi Dev Notes — Granica 1.3 vs 1.4): bogata management funkcionalnost (sortable inline galerija preko `django-admin-sortable2`, TinyMCE WYSIWYG widget, „Dupliraj" akcija, preview pre objave, Inquiry status workflow sa filterima/search, bogat `list_display`/`list_filter`/`search_fields` za Property i Inquiry, dvojezični fieldset-ovi za unos). U 1.3 se `Property` i `Inquiry` registruju **minimalno ALI OBAVEZNO** — minimalan `ModelAdmin` (samo onoliko koliko treba da imenovane admin rute `admin:properties_property_add` i `admin:inquiries_inquiry_changelist` postoje i da `reverse()` u brzim akcijama ne padne uz `NoReverseMatch` → 500). Dashboard metrike i dalje broje preko ORM-a, ali registracija je **neophodna** za quick-action `reverse()` linkove; bogat changelist/forma UX ostaje 1.4. (`Page` se može ostaviti neregistrovan u 1.3 — nije referenciran nijednim quick-action linkom.)

## Acceptance Criteria

> AC su izvedeni primarno iz **epics.md Story 1.3** (autoritativna lista), dopunjeni Unfold specifičnostima iz **arhitekture §1.1** i FR23 iz PRD-a. Svaki AC je konkretan i testabilan (admin test client sa prijavljenim staff/superuser korisnikom; SQLite test baza — vidi Dev Notes).

- [x] **AC1 — `django-unfold` instaliran i registrovan PRE `django.contrib.admin` (arh §1.1, §4).** `django-unfold` je instaliran u venv (`pip install -r requirements/dev.txt` — paket već postoji u `base.txt` iz 1.1) i dodat u `INSTALLED_APPS` u `config/settings/base.py`. Po Unfold dokumentaciji, `"unfold"` (i sve obavezne Unfold pod-aplikacije koje projekat koristi, npr. `"unfold.contrib.filters"`, `"unfold.contrib.forms"` ako se koriste) moraju stajati **iznad** `"django.contrib.admin"` u `INSTALLED_APPS`. **Testabilni kriterijum:** u listi `INSTALLED_APPS` indeks `"unfold"` < indeks `"django.contrib.admin"`; `python manage.py check` prolazi bez grešaka.

- [x] **AC2 — Brend boje teme: Deep Olive `#4A5240` / Champagne `#C9A96E` (epics 1.3, arh §1.1, zadatak §2.2).** U `config/settings/base.py` postoji `UNFOLD` settings dict u kome je definisana `COLORS` paleta izvedena iz brend tokena: Deep Olive `#4A5240` (primarni/akcenat) i Champagne `#C9A96E` (sekundarni/akcenat), usklađeno sa `tokens.css`. **Važno (format):** modern `django-unfold` (vidi pin u AC11) očekuje `UNFOLD["COLORS"]` kao dict skala nijansi po boji, sa ključevima `50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950`, čije su vrednosti **space-separated RGB-channel stringovi** (npr. `"74 82 64"`), **NE hex**. Zato se hex `#4A5240` ne može asertovati direktno — koristi se RGB-channel ekvivalent. Izvedene brend RGB-channel vrednosti: **Deep Olive `#4A5240` → `"74 82 64"`**, **Champagne `#C9A96E` → `"201 169 110"`**. **Testabilni kriterijum:** `UNFOLD["COLORS"]["primary"]` je dict skale nijansi koja pokriva ključeve `50`–`950`, a njena centralna nijansa (`"500"` i/ili `"600"`) jednaka je RGB-channel stringu izvedenom iz brend hex-a Deep Olive — `"74 82 64"` (Champagne `"201 169 110"` se pojavljuje kao akcent/sekundarna nijansa u skali per Unfold dokumentaciji pinovane verzije). Tačni nazivi/struktura ključeva su per Unfold docs pinovane verzije, ali brend RGB-channel vrednosti MORAJU biti prisutne u skali. (Render-provera: GET admin index → HTTP 200 sa primenjenim Unfold stilovima.)

- [x] **AC3 — Brendiranje ljuske: site title / header „Velegrad CMS" (FR23, zadatak §9).** `UNFOLD` dict postavlja `SITE_TITLE` i `SITE_HEADER` (i opciono `SITE_SUBHEADER`) na „Velegrad CMS" (ili ekvivalentan brend naslov), tako da se u `<title>` i u zaglavlju admina prikazuje brendiran naziv umesto default „Django administration". Logo/branding se vezuje gde Unfold to podržava (`SITE_ICON`/`SITE_LOGO`); ako klijentski logo (IR #4 eksterni input) još nije dostupan, koristi se tekstualni brend naslov + placeholder, sa TODO komentarom za zamenu logom. **Testabilni kriterijum:** GET na admin index (prijavljen staff) vraća HTML koji sadrži „Velegrad CMS" i NE sadrži default „Django administration" string u zaglavlju.

- [x] **AC4 — Dashboard metrike preko `DASHBOARD_CALLBACK` (epics 1.3, arh §1.1, FR23).** `UNFOLD["DASHBOARD_CALLBACK"]` pokazuje na callable (npr. `core.admin.dashboard_callback` ili `core.dashboard.callback`) koji u kontekst dodaje **tačno ove tri metrike**, izračunate preko ORM-a nad 1.2 modelima:
  - broj **aktivnih nekretnina**: `Property.objects.filter(is_active=True).count()`;
  - broj **novih upita**: `Inquiry.objects.filter(status="new").count()`;
  - broj **featured nekretnina**: `Property.objects.filter(is_featured=True).count()`.
  Dashboard landing strana (Unfold index) prikazuje ove tri vrednosti kao kartice/brojčane pokazatelje. **Napomena (KRITIČNO):** `DASHBOARD_CALLBACK` samo UBacuje ove ključeve u kontekst — on ih NE renderuje sam; renderovanje kartica zahteva dashboard index template override (vidi AC9). **Testabilni kriterijum:** sa seed podacima (npr. 3 aktivne / 1 neaktivna nekretnina, 2 `status=new` / 1 `status=closed` upit, 1 featured), GET na admin index (prijavljen staff) vraća **HTTP 200** i renderovani HTML sadrži tačne brojeve `3`, `2`, `1` u tri kartice metrika (asertuje se nad HTML-om odgovora, ne samo nad povratnom vrednošću callback-a).

- [x] **AC5 — Brze akcije + tabela poslednjih upita (epics 1.3, FR23).** Na dashboardu postoje **prečice/brze akcije** „Dodaj nekretninu" (link na Property add formu u adminu) i „Upiti" (link na Inquiry changelist), **And** prikazana je **tabela poslednjih upita** — konkretno **poslednjih 5 po `-created_at`** (`Inquiry.objects.order_by("-created_at")[:5]`): ime, tip upita, status, datum. Linkovi koriste `reverse()` na admin URL-ove (ne hardkodovan put — radi i kad se `ADMIN_URL` promeni). Brze akcije i tabela se prikazuju kroz dashboard index template override (vidi AC9); same vrednosti iz konteksta callback-a se ne renderuju automatski. **Testabilni kriterijum:** GET na admin index (prijavljen staff, sa seed `Inquiry` zapisima) vraća **HTTP 200**, a renderovani HTML sadrži `href` ka Property add ruti i ka Inquiry changelist ruti (vrednosti dobijene iz `reverse()`), i sadrži redove tabele iz najnovijih `Inquiry` zapisa (ime/tip/status/datum) — odnosno prazno-stanje poruku kad upita nema. Asercija se vrši nad HTML-om odgovora.

- [x] **AC6 — `SiteSettings` singleton admin: samo izmena (no add / no delete) (FR26 deo — registracija; puni unos je 1.4).** `SiteSettings` je registrovan u `core/admin.py` kao Unfold `ModelAdmin` koji poštuje singleton iz 1.2. Precizna implementacija singleton-a:
  - **(a) `has_add_permission`** vraća `return not SiteSettings.objects.exists()` — pošto `SiteSettings.load()` iz 1.2 automatski kreira singleton red, add je blokiran čim red postoji, a dozvoljen je samo na potpuno praznoj bazi (robustnije od oslanjanja na fiksni pk).
  - **(b) `has_delete_permission`** uvek vraća `False` (singleton se ne briše).
  - **(c) Single-edit UX:** override `changelist_view` tako da, kada jedini red postoji, preusmeri (redirect) direktno na change view tog reda — npr. `redirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))` — tako da korisnik ne vidi changelist sa jednim redom nego odmah formu za izmenu.

  **Napomena o granici:** ovde se isporučuje SAMO registracija + add/delete pravila + single-edit redirect; bogat dvojezični fieldset layout za sva hero/founder/kontakt polja je **1.4 (FR26/FR27)**. **Testabilni kriterijum:** za prijavljenog superuser-a, na `SiteSettings` changelist/add ruti `has_add_permission` je `False` kad singleton postoji, delete dugme/akcija nisu dostupni, a GET na `SiteSettings` changelist preusmerava (redirect) na change view jedinog reda.

- [x] **AC7 — Admin dostupan SAMO na `ADMIN_URL`, premium ljuska na login ekranu (NFR-5; nasleđeno iz 1.1, potvrđuje se ovde).** Admin je i dalje montiran isključivo na nestandardnu `ADMIN_URL` putanju (iz 1.1) — ova priča NE menja montažu, samo je potvrđuje da brendiranje ne probija na default `/admin/`. Login ekran nosi Unfold brending (boje/naslov) ako ga Unfold podržava. **Napomena (precizno):** Unfold login strana renderuje `UNFOLD["SITE_HEADER"]` (i/ili logo), a NE mora nužno sadržati literalni `SITE_TITLE` string — login header je vođen ključem `SITE_HEADER`. **Testabilni kriterijum:** GET na `/admin/` vraća **HTTP 404** (ostaje kao jest); GET na konfigurisani `ADMIN_URL` vraća **HTTP 200** i renderuje BRENDIRAN Unfold login (npr. prisustvo Unfold login markup-a / brend teksta iz `SITE_HEADER` u zaglavlju), umesto zahtevanja tačnog literalnog stringa „Velegrad CMS" ako taj string na login strani vodi ključ koji Unfold ne izlaže (`SITE_HEADER` je ključ koji vodi login header).

- [x] **AC8 — `python manage.py check` čist i admin se diže bez greške (regresija).** Posle dodavanja Unfold-a i `UNFOLD` dict-a, `python manage.py check` ne prijavljuje greške (E-nivo). Admin index, login i registrovani changelist-ovi (`SiteSettings`, i bilo koji minimalno registrovani model) renderuju se bez `TemplateError`/`500`. Postojeće 1.2 migracije i `migrate` na SQLite test bazi i dalje prolaze (Unfold ne uvodi migracije koje bi pukle). Pored toga, za prijavljenog superuser-a **`Inquiry` i `Property` changelist rade** (GET → HTTP 200) — smoke provera registrovanih changelist-ova (premešteno iz AC6, koji sada ostaje fokusiran na `SiteSettings` singleton ponašanje). **Testabilni kriterijum:** `check` izlazi bez grešaka; admin smoke test (login + GET index) vraća 200; GET na `Inquiry` i `Property` changelist (superuser) vraća 200.

- [x] **AC9 — Dashboard index template override koji RENDERUJE kontekst callback-a (arh §1.1, FR23).** Pošto `DASHBOARD_CALLBACK` samo ubacuje ključeve u kontekst (a ne renderuje ih), isporučuje se **dashboard index template override** koji čita ključeve iz konteksta callback-a (brojevi metrika; quick-action URL-ovi dobijeni `reverse()`-om; `latest_inquiries`) i renderuje: **tri kartice metrika**, **dve brze akcije (linkovi)** i **tabelu poslednjih upita**. Konkretan deliverable je `templates/admin/index.html` (override Django admin index-a koji Unfold koristi) **ILI** odgovarajući Unfold dashboard template override (`templates/unfold/...`) prema mehanizmu dokumentovanom za pinovanu Unfold verziju (vidi AC11) — Dev bira tačan put po dokumentaciji pinovane verzije, ali template MORA čitati i renderovati gore navedene ključeve iz konteksta. Direktorijum sa template-ima mora biti u `TEMPLATES["DIRS"]` (ili app templates) da bi override imao prednost. **Testabilni kriterijum:** GET na admin index (prijavljen staff) vraća HTTP 200 i renderovani HTML stvarno sadrži tri broja metrika, oba quick-action `href`-a i redove tabele poslednjih upita (tj. AC4 i AC5 asercije prolaze zahvaljujući ovom template-u, ne samo zato što callback vraća vrednosti).

- [x] **AC10 — Minimalna ALI OBAVEZNA registracija `Property`/`Inquiry` admina kao preduslov za quick-action `reverse()` (arh §2).** `Property` i `Inquiry` MORAJU biti registrovani u adminu kao minimalan Unfold `ModelAdmin` u 1.3 — samo onoliko da imenovane admin rute `admin:properties_property_add` i `admin:inquiries_inquiry_changelist` postoje, kako `reverse()` u brzim akcijama (AC5) ne bi bacio `NoReverseMatch` i srušio admin index sa 500. Bogat `list_display`/`list_filter`/`search_fields`/forme/akcije ostaju 1.4. **Testabilni kriterijum:** `reverse("admin:properties_property_add")` i `reverse("admin:inquiries_inquiry_changelist")` se uspešno razrešavaju (ne bacaju `NoReverseMatch`); GET na obe rute za prijavljenog superuser-a vraća HTTP 200.

- [x] **AC11 — `django-unfold` pinovan na poznato-dobru verziju; `COLORS` config pisan po toj verziji (arh §1.1).** `django-unfold` se pinuje u `requirements/base.txt` na poznato-dobar opseg (npr. `django-unfold>=0.43,<0.44` — ili tekući poznato-dobar minor koji Dev verifikuje `pip`-om), a `UNFOLD["COLORS"]` konfiguracija (AC2) se piše prema **dokumentovanom COLORS API-ju te pinovane verzije** (modern Unfold očekuje skale nijansi sa RGB-channel string vrednostima — vidi AC2). **Testabilni kriterijum:** `requirements/base.txt` sadrži pinovani `django-unfold` sa gornjom i donjom granicom; instalirana verzija je unutar tog opsega; `python manage.py check` prolazi i admin index se renderuje sa tom verzijom.

## Tasks / Subtasks

- [x] **T1 — Instalacija i registracija Unfold-a** *(AC1, AC8)*
  - [x] Aktiviraj venv i `pip install -r requirements/dev.txt` (povlači `django-unfold` koji je već u `base.txt` iz 1.1). Ako Unfold zahteva dodatne pin-ove, ažuriraj `base.txt` minimalno (ne menjati ostale pakete).
  - [x] U `config/settings/base.py` dodaj `"unfold"` (i obavezne `unfold.contrib.*` pod-aplikacije koje koristiš — npr. `unfold.contrib.filters`, `unfold.contrib.forms`) u `INSTALLED_APPS` **iznad** `"django.contrib.admin"`.
  - [x] `python manage.py check` → bez grešaka (AC8).

- [x] **T2 — `UNFOLD` settings dict: brend boje + ljuska** *(AC2, AC3, AC7)*
  - [x] U `config/settings/base.py` dodaj `UNFOLD = { ... }` dict.
  - [x] `SITE_TITLE` / `SITE_HEADER` (i opciono `SITE_SUBHEADER`) = „Velegrad CMS" (AC3).
  - [x] `COLORS` paleta sa Deep Olive `#4A5240` (primarni) i Champagne `#C9A96E` (sekundarni), usklađeno sa `tokens.css` (AC2). Unfold `COLORS["primary"]` je dict skale nijansi (ključevi `50`–`950`) sa **RGB-channel string vrednostima** (`"R G B"`), NE hex. Postavi centralnu nijansu (`"500"`/`"600"`) na brend RGB-channel `"74 82 64"` (Deep Olive); Champagne `"201 169 110"` koristi kao sekundarni/akcent ton. Ostale međunijanse izvedi (svetlije/tamnije) po Unfold docs pinovane verzije (AC11).
  - [x] `SITE_ICON`/`SITE_LOGO` (login + sidebar branding) — koristi placeholder/tekst dok klijentski SVG logo (IR #4) ne stigne; ostavi TODO (AC3, AC7).

- [x] **T3 — Dashboard callback (metrike)** *(AC4)*
  - [x] Implementiraj `dashboard_callback(request, context)` u `core/` (npr. `core/admin.py` ili `core/dashboard.py`) koji u `context` ubacuje tri metrike preko ORM-a: aktivne (`is_active=True`), novi upiti (`status="new"`), featured (`is_featured=True`).
  - [x] Poveži ga preko `UNFOLD["DASHBOARD_CALLBACK"] = "core.admin.dashboard_callback"` (tačan dotted path).
  - [x] (Sam callback samo puni kontekst — stvarni render kartica radi template override iz T6.)

- [x] **T4 — Minimalna (OBAVEZNA) registracija `Property`/`Inquiry` + brze akcije + tabela poslednjih upita** *(AC5, AC10)*
  - [x] **OBAVEZNO PRE quick-action linkova:** registruj `Property` i `Inquiry` u adminu kao minimalan Unfold `ModelAdmin` (`@admin.register(...)` ili `admin.site.register(...)`) — samo onoliko da imenovane rute `admin:properties_property_add` i `admin:inquiries_inquiry_changelist` postoje. Bez ovoga `reverse()` baca `NoReverseMatch` i admin index puca sa 500. Bogat `list_display`/`list_filter`/`search_fields`/forme su 1.4 — ovde NE.
  - [x] U dashboard kontekst dodaj linkove „Dodaj nekretninu" (`reverse("admin:properties_property_add")`) i „Upiti" (`reverse("admin:inquiries_inquiry_changelist")`).
  - [x] U kontekst dodaj `latest_inquiries = Inquiry.objects.order_by("-created_at")[:5]` i (preko template override-a iz T6) prikaži tabelu (ime, tip, status, datum) sa prazno-stanje porukom kad nema upita.

- [x] **T5 — `SiteSettings` singleton admin** *(AC6)*
  - [x] U `core/admin.py` registruj `SiteSettings` kao Unfold `ModelAdmin`.
  - [x] `has_add_permission` → `False` kad singleton zapis postoji; `has_delete_permission` → `False` (AC6).
  - [x] Osnovni single-edit (bez bogatih dvojezičnih fieldset-ova — to je 1.4).

- [x] **T6 — Dashboard index template override (render kartica/akcija/tabele)** *(AC9, AC4, AC5)*
  - [x] Kreiraj template override za dashboard index — konkretno `templates/admin/index.html` (override Django/Unfold admin index-a) **ILI** Unfold dashboard template (`templates/unfold/...`) prema dokumentaciji pinovane Unfold verzije (AC11). Dev bira tačan put po dokumentaciji, ali bira JEDAN i dosledan.
  - [x] Osiguraj da je direktorijum sa template-ima u `TEMPLATES["DIRS"]` (ili odgovarajući app `templates/`) tako da override ima prednost nad podrazumevanim.
  - [x] U template-u pročitaj i renderuj ključeve iz konteksta callback-a: tri broja metrika → tri kartice; quick-action URL-ove (`reverse()`) → dva linka („Dodaj nekretninu" / „Upiti"); `latest_inquiries` → tabela (ime/tip/status/datum) sa prazno-stanje porukom.

- [x] **T7 — Pin `django-unfold` u `base.txt`** *(AC11)*
  - [x] U `requirements/base.txt` pinuj `django-unfold` na poznato-dobar opseg (npr. `django-unfold>=0.43,<0.44` — ili tekući poznato-dobar minor koji verifikuješ `pip`-om). Napiši `UNFOLD["COLORS"]` (T2) prema COLORS API-ju te verzije.

- [x] **T8 — Verifikacija (admin smoke + metrike)** *(AC2–AC11)*
  - [x] **Preduslovi za render testova (uradi PRE smoke/metric testova):** verifikuj/dodaj `"django.template.context_processors.request"` u `TEMPLATES[0]["OPTIONS"]["context_processors"]`; potvrdi `"django.contrib.staticfiles"` u `INSTALLED_APPS` + `STATIC_URL` postavljen (bez `collectstatic`); testovi kreiraju i prijavljuju SUPERUSER-a; potvrdi da je `dashboard_callback` defanzivan (ne pada na praznoj bazi) jer se izvršava na svaki admin index GET. (vidi Dev Notes — Preduslovi za render admin testova)
  - [x] Admin smoke test (Django test client, SQLite test baza): kreiraj superuser, GET admin index → 200 i sadrži „Velegrad CMS"; GET `/admin/` → 404 (AC3, AC7).
  - [x] Test metrika (render): seed (3 aktivne/1 neaktivna `Property`, 2 `new`/1 `closed` `Inquiry`, 1 featured) → GET admin index HTML sadrži brojeve `3 / 2 / 1` u karticama (asercija nad HTML-om odgovora, ne samo nad callback povratnom vrednošću) (AC4, AC9).
  - [x] Test brzih akcija (render): GET admin index HTML sadrži `href` ka add-property ruti i ka inquiry-changelist ruti (iz `reverse()`) + redove poslednjih upita / prazno-stanje poruku (AC5, AC9).
  - [x] Test registracije (preduslov): `reverse("admin:properties_property_add")` i `reverse("admin:inquiries_inquiry_changelist")` se razrešavaju bez `NoReverseMatch`; GET obe rute (superuser) → 200 (AC10).
  - [x] Test singletona u adminu: `has_add_permission=False` kad zapis postoji (`not SiteSettings.objects.exists()`), `has_delete_permission=False`, i GET na `SiteSettings` changelist preusmerava (redirect) na change view jedinog reda (AC6).
  - [x] Test changelist smoke: GET na `Inquiry` i `Property` changelist (superuser) → 200 (AC8).
  - [x] Test pina: `requirements/base.txt` sadrži pinovan `django-unfold` (gornja+donja granica); instalirana verzija je u opsegu (AC11).
  - [x] `python manage.py check` čist; `migrate` na SQLite i dalje prolazi (AC8).

## Dev Notes

- **Izvor istine za AC = epics.md Story 1.3.** Tri eksplicitne AC linije iz epics-a su: (1) brend boje Deep Olive `#4A5240` / Champagne `#C9A96E`; (2) dashboard sa brojem aktivnih nekretnina, novih upita (`status=new`) i featured preko `DASHBOARD_CALLBACK`; (3) brze akcije „Dodaj nekretninu" / „Upiti" + tabela poslednjih upita; (4) admin na `ADMIN_URL`. Arhitektura §1.1 dopunjava Unfold specifičnosti; ova priča ih materijalizuje, ne preispituje.

- **GRANICA 1.3 vs 1.4 (KRITIČNO — pažljivo razdvojiti).**
  - **U 1.3 (OVA priča) = admin LJUSKA + DASHBOARD:** instalacija/konfiguracija Unfold teme (boje, logo/branding, site title/header), Unfold dashboard landing (kartice metrika preko `DASHBOARD_CALLBACK` + **dashboard index template override** koji te metrike/akcije/tabelu zaista renderuje, vidi AC9), brze akcije, tabela poslednjih upita, login branding, i registracija `SiteSettings` singleton admina (single-edit, no add/delete). `Property` i `Inquiry` se registruju **minimalno ALI OBAVEZNO** (minimalan `ModelAdmin`) — bez njihove registracije imenovane admin rute ne postoje i `reverse("admin:properties_property_add")` / `reverse("admin:inquiries_inquiry_changelist")` bacaju `NoReverseMatch`, čime admin index puca sa 500. Dashboard metrike se čitaju preko ORM-a (brojanje ne traži registraciju), ali quick-action `reverse()` linkovi traže. `Page` može ostati neregistrovan u 1.3 (nije referenciran quick-action linkom).
  - **U 1.4 (NE ovde) = MANAGEMENT funkcionalnost (FR24–FR27):** sortable inline galerija (`django-admin-sortable2`), TinyMCE WYSIWYG widget wiring (`django-tinymce`), „Dupliraj" admin akcija, preview pre objave (`?preview=1`), Inquiry list/status workflow sa filterima/search, bogat `list_display`/`list_filter`/`search_fields` za Property i Inquiry, dvojezični fieldset-ovi za SR/EN unos, pun `SiteSettings` unos (kontakt/hero/tagline/founder). **NE implementirati ovo u 1.3.** Pravilo: ako se radi o *uređivanju/upravljanju sadržajem*, to je 1.4; ako se radi o *izgledu ljuske + pregledu metrika*, to je 1.3.

- **Stanje okruženja (nasleđeno, NE menjati):**
  - **Single-tenant** real-estate CMS, flat layout (`core`/`properties`/`inquiries`/`pages` u root-u), bez Docker-a.
  - Admin je iz **1.1** već montiran na env `ADMIN_URL` putanju (default npr. `velegrad-cms/`), `/admin/` vraća 404, CSRF baseline aktivan. Ova priča **ne dira** montažu — samo je potvrđuje (AC7).
  - Iz **1.2** postoji svih 6 modela; `SiteSettings` je singleton (`load()`/`get_solo()` + fiksan pk) sa `localized()` helperom. Dashboard čita `Property`/`Inquiry` preko ORM-a.

- **`django-unfold` JOŠ NIJE instaliran u venv-u.** Paket je u `requirements/base.txt` iz 1.1, ali nije u `INSTALLED_APPS` niti instaliran. Dev MORA: (a) `pip install -r requirements/dev.txt`, (b) dodati `"unfold"` (+ obavezne `unfold.contrib.*` pod-aplikacije koje koristi) **iznad** `"django.contrib.admin"` u `INSTALLED_APPS` — Unfold to eksplicitno zahteva (override admin template-a). Pogrešan redosled = nestilizovan admin / template konflikt.

- **`unfold.contrib.*` — instaliraj samo ono što koristiš (obim 1.3):** za DASHBOARD-only obim priče 1.3 dovoljna je core `"unfold"` aplikacija. Pod-aplikacije `"unfold.contrib.filters"` / `"unfold.contrib.forms"` potrebne su SAMO ako stvarno koristiš te funkcionalnosti (bogati filteri / forme), a to je 1.4. Zato 1.3 treba da uključi u `INSTALLED_APPS` samo ono što koristi — izbegavaj over-install pod-aplikacija koje 1.3 ne dodiruje.

- **Preduslovi za render admin testova (da smoke/metric testovi zaista prođu na SQLite test bazi):** Unfold template-i imaju nekoliko zahteva koje Dev mora ispuniti pre nego što test client uspešno renderuje admin HTML:
  - **(a)** `TEMPLATES[0]["OPTIONS"]["context_processors"]` MORA sadržati `"django.template.context_processors.request"` (Unfold template-i ga zahtevaju) — Dev verifikuje/dodaje ga u `config/settings/base.py`.
  - **(b)** `"django.contrib.staticfiles"` mora biti prisutan u `INSTALLED_APPS` i `STATIC_URL` postavljen, da `{% static %}` u Unfold template-ima razreši pod test client-om (NIJE potreban `collectstatic` — test client renderuje HTML, a static su samo `href`-ovi).
  - **(c)** Testovi kreiraju i prijavljuju **SUPERUSER-a** (izbegava flakiness oko per-model permisija).
  - **(d)** **KRITIČNO:** `DASHBOARD_CALLBACK` se izvršava na SVAKI admin index GET — izuzetak u callback-u 500-ira ceo admin index. Zato callback mora biti defanzivan (ne sme pući na praznoj bazi / nedostajućim podacima).

- **Brend boje — izvor i format:** hex vrednosti Deep Olive `#4A5240` i Champagne `#C9A96E` dolaze iz `docs/OpenDesignFiles/assets/css/tokens.css` (arh §1.1, zadatak §2.2). **KRITIČNO:** modern `django-unfold` (pinovan, AC11) ne prima hex u `COLORS` — očekuje skalu nijansi (ključevi `50`–`950`) gde su vrednosti **space-separated RGB-channel stringovi** (`"R G B"`). Izvedene brend vrednosti: **Deep Olive `#4A5240` → `"74 82 64"`**, **Champagne `#C9A96E` → `"201 169 110"`**. Brend ton ide u centar skale (`"500"`/`"600"`), ostale nijanse se izvode; tačni nazivi/struktura ključeva su per Unfold docs pinovane verzije, ali brend RGB-channel vrednosti MORAJU biti u skali. Zato se AC2 asertuje nad RGB-channel stringom, ne nad hex-om.

- **`django-unfold` PIN (AC11):** Unfold je dosad bio nepinovan; pinovati ga u `requirements/base.txt` na poznato-dobar opseg (npr. `django-unfold>=0.43,<0.44`, ili tekući poznato-dobar minor koji Dev verifikuje `pip show django-unfold`). `COLORS` API i dashboard template override mehanizam (AC9) pisati prema dokumentaciji TAČNO te pinovane verzije — Unfold menja template/COLORS detalje između verzija.

- **Dashboard render (AC9) — KRITIČNO:** `DASHBOARD_CALLBACK` SAMO ubacuje ključeve u kontekst; ne renderuje kartice/akcije/tabelu. Render zahteva template override (`templates/admin/index.html` ili `templates/unfold/...` per pinovane verzije) koji čita te ključeve (brojevi, quick-action URL-ovi, `latest_inquiries`) i ispisuje ih u HTML. Bez ovog template-a dashboard je prazan iako callback radi.

- **i18n napomena (van obima ovde):** sadržajni stringovi se počinju prevoditi tek od Epika 2 template-a (sprint-plan IR #1). Admin UI labele koriste Django ugrađenu admin i18n + `verbose_name`/`verbose_name_plural` koji su već postavljeni na modelima u 1.2 — u ovoj priči se NE dodaje `{% trans %}`/`gettext` infrastruktura. Dvojezični fieldset-ovi za unos su 1.4.

- **Baza za verifikaciju — SQLite test (env odluka, isto kao 1.2):** lokalni PostgreSQL NIJE dostupan. Admin testovi koriste **Django test client** sa prijavljenim staff/superuser korisnikom nad **SQLite test bazom** (`config/settings/test.py` + `pytest-django`). Realni Postgres je odložen do dostupnosti/pre-deploy. Unfold ne unosi sopstvene migracije koje bi ovo ugrozile.

- **Seed podaci za testove (preporuka, ne obavezno):** za konzistentnost sa postojećim stilom u `tests/test_models.py`, preporuka je seed podatke (Property/Inquiry za metrike) napraviti preko pytest fixtura/factory-ja umesto `TestCase.setUp`/`loaddata`; tačan mehanizam je Dev-ova odluka.

- **`reverse()` umesto hardkodovanih admin URL-ova:** brze akcije moraju koristiti `reverse("admin:<app>_<model>_<action>")` da rade bez obzira na vrednost `ADMIN_URL` (koja je env-konfigurabilna iz 1.1). Ovo **OBAVEZNO** zahteva da su `Property` i `Inquiry` registrovani u adminu (minimalan `ModelAdmin`) da bi imenovane admin rute postojale — u suprotnom `reverse()` baca `NoReverseMatch`, a kako se poziva u dashboard kontekstu/template-u, admin index puca sa **500**. Registracija je zato preduslov (prerequisite) za AC5/AC10, nije opcija.

- **Logo / klijentski branding (IR #4 eksterni input):** klijentski SVG logo je eksterna zavisnost koja se prikuplja paralelno (sprint-plan IR #4) i možda još NIJE stigao. Dok ne stigne, koristi tekstualni „Velegrad CMS" naslov + placeholder ikonu sa TODO komentarom — NE blokirati priču na čekanju loga.

- **Git poruke na engleskom** (zadatak §9) — ali ova priča je samo spec; commit radi dev priča.

## Definition of Done

- [x] `django-unfold` instaliran i `"unfold"` (+ potrebne `unfold.contrib.*`) u `INSTALLED_APPS` **iznad** `"django.contrib.admin"` (AC1).
- [x] `django-unfold` pinovan u `requirements/base.txt` na poznato-dobar opseg; `COLORS`/template override pisani po toj verziji (AC11).
- [x] `UNFOLD` settings dict u `config/settings/base.py` sa brend bojama (RGB-channel skala: Deep Olive `"74 82 64"` / Champagne `"201 169 110"`, NE hex) i brend naslovom „Velegrad CMS" (site title/header) (AC2, AC3).
- [x] Dashboard index template override (`templates/admin/index.html` ili `templates/unfold/...`) renderuje kartice/akcije/tabelu iz konteksta callback-a (AC9).
- [x] Dashboard landing RENDERUJE tri metrike (aktivne nekretnine / novi upiti `status=new` / featured) preko `DASHBOARD_CALLBACK` + template override, sa tačnim brojevima u HTML-u nad seed podacima (AC4, AC9).
- [x] `Property` i `Inquiry` registrovani minimalno ALI OBAVEZNO (preduslov za quick-action `reverse()` — bez 500) (AC10).
- [x] Dashboard ima brze akcije „Dodaj nekretninu" i „Upiti" (preko `reverse()`) i tabelu poslednjih upita, renderovane u HTML-u (AC5, AC9).
- [x] `SiteSettings` registrovan kao singleton admin: bez add (kad zapis postoji) i bez delete, single-edit (AC6).
- [x] Admin dostupan SAMO na `ADMIN_URL` (`/admin/` → 404), login ekran brendiran; montaža iz 1.1 nije promenjena (AC7).
- [x] `python manage.py check` čist; admin index/login/changelist se renderuju bez greške; `migrate` na SQLite i dalje prolazi (AC8).
- [x] **Obim ispoštovan:** isporučena SAMO admin ljuska + dashboard + SiteSettings singleton registracija; sortable galerija / TinyMCE / „Dupliraj" / preview / Inquiry status workflow / bogat list_display / dvojezični fieldset-ovi NISU dirani (to je 1.4 — vidi Dev Notes Granica 1.3 vs 1.4).
