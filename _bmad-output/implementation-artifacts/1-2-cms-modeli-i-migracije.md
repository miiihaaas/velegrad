---
story-id: 1-2-cms-modeli-i-migracije
title: CMS modeli i migracije
epic: 1
epic-title: "Setup, CMS modeli i brendiran admin (Faza 1)"
module: "core, properties, inquiries, pages"
status: ready-for-dev
created: 2026-06-02
author: SM (Scrum Master)
fr-coverage: "temelj — svi modeli §5.2; arhitektura §1.3 (dvojezična polja + localized() helper), §2 (granice app-ova)"
references:
  - "docs/Velegrad Estate - Projektni zadatak.docx.md"  # §5.2 — IZVOR ISTINE za polja/relacije
  - _bmad-output/planning-artifacts/architecture.md       # §1.3 i18n polja + localized(), §2 struktura, §1.4 ImageField/imagekit
  - _bmad-output/planning-artifacts/epics.md               # Epic 1 / Story 1.2
  - _bmad-output/planning-artifacts/PRD.md                 # FR kontekst polja
  - _bmad-output/implementation-artifacts/sprint-plan.md
  - _bmad-output/implementation-artifacts/1-1-inicijalizacija-django-projekta-i-okruzenja.md  # skelet na koji se nadovezuje
---

# Story 1.2: CMS modeli i migracije

## Opis

As a developer,
I want sve domenske modele iz zadatka §5.2 implementirane sa migracijama,
So that podaci o nekretninama, upitima i sadržaju imaju trajnu šemu spremnu za admin (1.3/1.4) i frontend (Epik 2+).

Ova priča se nadovezuje na skelet iz **1.1** (app-ovi `core`, `properties`, `inquiries`, `pages` već postoje, prazni). Cilj je definisati **tačno** modele iz **zadatka §5.2** (izvor istine za polja/relacije/tipove — bez izmišljanja polja) i generisati migracije za svaki app, raspoređene po granicama iz arhitekture §2:

- **`core/`** → `SiteSettings` (singleton)
- **`properties/`** → `Property`, `PropertyImage`, `PropertyFeature`
- **`inquiries/`** → `Inquiry` (svi `inquiry_type`)
- **`pages/`** → `Page` (about / why-velegrad / international)

Pored polja, priča isporučuje i model-level detalje koje arhitektura eksplicitno zahteva: dvojezična `_sr`/`_en` polja sa `localized(base)` helperom (arh §1.3), `Property.slug` auto-generaciju iz `title`, i `SiteSettings` singleton enforcement (arh §2).

**Obim — STROGO MODELI + MIGRACIJE.** Ova priča isporučuje SAMO: model klase, polja, relacije, `Meta` (ordering, constraints, indexes, verbose_name), `__str__`, model-level validaciju/menadžere (npr. singleton), `localized()` helper, slug auto-generaciju, i **generisane migracione fajlove** za svaki app.

## Acceptance Criteria

> Mapiranje je 1:1 na zadatak §5.2. Polja se navode tačno kako su tamo definisana; tip polja u zagradi je iz §5.2. Gde §5.2 ne specifikuje `null/blank`, ona se izvode iz semantike "opciono" iz §5.2 (vidi Dev Notes — interpretacije).

- [x] **AC1 — `SiteSettings` model u `core/` (singleton) — §5.2 "Model: SiteSettings".** Postoji `core.models.SiteSettings` sa tačno ovim poljima iz §5.2: `phone_primary` (CharField, `max_length=30`), `whatsapp_number` (CharField, `max_length=20`, format npr. `381601234567`), `email_primary` (EmailField — `max_length` ne primenjuje se, Django default 254), `email_inquiries` (EmailField — kuda stižu upiti; `max_length` ne primenjuje se), `address` (TextField — `max_length` ne primenjuje se), `founder_name` (CharField, `max_length=150`), `founder_title_sr` (CharField, `max_length=150`), `founder_title_en` (CharField, `max_length=150`), `founder_photo` (ImageField), `founder_bio_sr` (RichTextField — `max_length` ne primenjuje se), `founder_bio_en` (RichTextField — `max_length` ne primenjuje se), `hero_headline_sr` (CharField, `max_length=200`), `hero_headline_en` (CharField, `max_length=200`), `hero_cta_text_sr` (CharField, `max_length=80`), `hero_cta_text_en` (CharField, `max_length=80`), `hero_image` (ImageField), `hero_video_url` (URLField, opciono), `google_analytics_id` (CharField, `max_length=50`), `facebook_pixel_id` (CharField, `max_length=50`), `seo_default_title` (CharField, `max_length=70` — SEO), `seo_default_description` (TextField — `max_length` ne primenjuje se). `__str__` vraća smisleno ime (npr. "Podešavanja sajta"); `Meta.verbose_name`/`verbose_name_plural` su srpski.

- [x] **AC2 — `SiteSettings` singleton enforcement (arh §2).** Model garantuje **tačno jedan red**: pokušaj kreiranja drugog zapisa se sprečava (npr. fiksiran `pk` u `save()` + override `delete()`/menadžer `load()`), tako da je u bazi uvek najviše jedan `SiteSettings`. **`RichTextField` se OBAVEZNO realizuje kao `tinymce.models.HTMLField`** (zavisnost `django-tinymce` već postoji u `base.txt` iz 1.1) — dosledno kroz SVE RichText polja u svim modelima (`founder_bio_*`, `description_*`, `content_*`). `HTMLField` je podklasa `TextField`, pa za prolaz `makemigrations`/`check` **NIJE potrebno** dodavati `'tinymce'` u `INSTALLED_APPS` (registracija TinyMCE app-a i admin widget su tema 1.4; ovde se uvozi samo `HTMLField`).

- [x] **AC3 — `Property` model u `properties/` — §5.2 "Model: Property".** Postoji `properties.models.Property` sa tačno poljima iz §5.2:
  - `id` (UUIDField — primarni ključ, `default=uuid4`, `editable=False`)
  - `title` (CharField, `max_length=200` — naziv nekretnine)
  - `slug` (`SlugField(max_length=255, unique=True)` — URL identifikator, **jedinstven**, auto-generisan kolizijski-bezbedno; vidi AC9)
  - `status` (CharField, `max_length=20`, choices: `for_sale` / `for_rent` / `price_on_request` / `sold` / `rented`)
  - `collection_type` (CharField, `max_length=20`, choices: `signature` / `private` / `off_market`)
  - `property_type` (CharField, `max_length=20`, choices: stan / kuca / penthouse / vila / komercijalno / zemljiste)
  - `location_city` (CharField, `max_length=100`), `location_district` (CharField, `max_length=100`), `location_address` (CharField, `max_length=255`, opciono)
  - `show_address` (BooleanField, `default=False` — da li prikazati adresu)
  - `price` (DecimalField, `max_digits=12`, `decimal_places=2`, `null=True` kad je `price_on_request`), `price_on_request` (BooleanField, `default=False`)
  - `area_sqm` (DecimalField, `max_digits=8`, `decimal_places=2` — stambena m²), `area_total_sqm` (DecimalField, `max_digits=8`, `decimal_places=2` — ukupna m²)
  - `bedrooms` (IntegerField), `bathrooms` (IntegerField), `floor` (IntegerField), `total_floors` (IntegerField), `parking_spaces` (IntegerField — 0 ako nema), `year_built` (IntegerField, opciono)
  - `description_sr` (RichTextField), `description_en` (RichTextField), `description_fr` (RichTextField, opciono — ostaje u modelu, van obima prevoda; arh §1.3)
  - `features` (ManyToManyField → `PropertyFeature`)
  - `hero_image` (ImageField — naslovna), `floor_plan` (FileField — PDF/slika, opciono), `virtual_tour_url` (URLField, opciono)
  - `latitude` (DecimalField, `max_digits=9`, `decimal_places=6` — WGS84, opciono), `longitude` (DecimalField, `max_digits=9`, `decimal_places=6` — WGS84, opciono)
  - `is_featured` (BooleanField, `default=False` — homepage), `is_active` (BooleanField, `default=True` — objavljeno/skriveno; agent kreira kompletan unos, pa je objavljeno po defaultu)
  - `created_at` (DateTimeField, `auto_now_add=True`), `updated_at` (DateTimeField, `auto_now=True`)
  - `meta_title` (CharField, `max_length=70` — SEO), `meta_description` (TextField — SEO; `max_length` ne primenjuje se)
  - `Meta`: smislen `ordering` (npr. `["-created_at"]`), `verbose_name`/`verbose_name_plural` (srpski); `__str__` vraća `title`. **Indeksi (OBAVEZNO, decidno — ne opciono):** `slug` je već indeksiran preko `SlugField` (db_index podrazumevan), a za česte server-side filtere iz arh §1.2 dodaju se indeksi na `is_active`, `collection_type` i `status` (preko `db_index=True` na poljima ili `Meta.indexes`) — odlučeno sada da se izbegne kasnija migracija.

- [x] **AC4 — `PropertyImage` model u `properties/` — §5.2 "Model: PropertyImage".** Postoji `properties.models.PropertyImage` sa: `id` (AutoField — podrazumevani), `property` (ForeignKey → `Property`, `on_delete=CASCADE`, `related_name` npr. `images`), `image` (ImageField), `caption` (CharField, `max_length=255`, opciono), `order` (IntegerField — redosled prikaza), `is_hero` (BooleanField, `default=False` — naslovna). `Meta.ordering = ["order"]` (podrška za reorder galerije iz 1.4); `__str__` smislen (npr. `f"{property} #{order}"`).

- [x] **AC5 — `PropertyFeature` model u `properties/` — §5.2 "Model: PropertyFeature".** Postoji `properties.models.PropertyFeature` sa: `id` (AutoField), `name_sr` (CharField, `max_length=100` — naziv srpski), `name_en` (CharField, `max_length=100` — naziv engleski), `icon` (CharField, `max_length=50` — ime Feather/Lucide ikonice), `category` (CharField, `max_length=20`, choices: `interior` / `exterior` / `building` / `legal`). `__str__` vraća `name_sr`; `Meta` sa smislenim `ordering` (npr. `["category", "name_sr"]`) i srpskim `verbose_name`.

- [x] **AC6 — `Inquiry` model u `inquiries/` — §5.2 "Model: Inquiry".** Postoji `inquiries.models.Inquiry` sa: `id` (UUIDField — pk, `default=uuid4`, `editable=False`), `property` (ForeignKey → `Property`, `null=True`, `blank=True`, `on_delete` smislen — npr. `SET_NULL` da upit ostane i kad se nekretnina obriše), `inquiry_type` (CharField, `max_length=20`, choices: `viewing` / `consultation` / `private_collection` / `general`), `name` (CharField, `max_length=150`), `email` (EmailField — `max_length` ne primenjuje se), `phone` (CharField, `max_length=30`), `message` (TextField — `max_length` ne primenjuje se), `preferred_language` (CharField, `max_length=5`, choices: `sr` / `en` / `fr`), `budget_range` (CharField, `max_length=100` — za private_collection upite, opciono), `property_type_wanted` (CharField, `max_length=100` — za private_collection upite, opciono), `status` (CharField, `max_length=20`, choices: `new` / `contacted` / `in_progress` / `closed`, default `new`), `notes` (TextField — interni komentari, opciono; `max_length` ne primenjuje se), `created_at` (DateTimeField, `auto_now_add=True`), `ip_address` (GenericIPAddressField — anti-spam, `null=True`/`blank=True`). `Meta.ordering = ["-created_at"]`, srpski `verbose_name`; `__str__` smislen (npr. `f"{name} — {inquiry_type}"`). (Email notifikacija/auto-reply NIJE u ovoj priči — 5.2.)

- [x] **AC7 — `Page` model u `pages/` — §5.2 "Model: Page".** Postoji `pages.models.Page` sa: `slug` (CharField, `max_length=100`, `unique=True`; vrednosti `about`, `why-velegrad`, `international`...), `title_sr` (CharField, `max_length=200`), `title_en` (CharField, `max_length=200`), `content_sr` (RichTextField — `max_length` ne primenjuje se), `content_en` (RichTextField — `max_length` ne primenjuje se), `meta_title` (CharField, `max_length=70`), `meta_description` (TextField — `max_length` ne primenjuje se), `is_active` (BooleanField, `default=True`). `__str__` vraća `slug` ili `title_sr`; srpski `verbose_name`. (Napomena: §5.2 Page nema eksplicitan `id` red — koristi se podrazumevani Django `AutoField` pk.)

- [x] **AC8 — Dvojezičnost: `_sr`/`_en` polja + `localized(base)` helper (arh §1.3).** Sva dvojezična polja postoje tačno kako stoji u §5.2 (`description_sr`/`_en`/`_fr` na `Property`; `name_sr`/`_en` na `PropertyFeature`; `founder_title_sr`/`_en`, `founder_bio_sr`/`_en`, `hero_headline_sr`/`_en`, `hero_cta_text_sr`/`_en` na `SiteSettings`; `title_sr`/`_en`, `content_sr`/`_en` na `Page`). Modeli sa dvojezičnim sadržajem imaju **robustan** `localized(base)` helper koji (a) bezbedno radi i kada `get_language()` vrati `None` (npr. management komande / neaktivan i18n) — ne sme baciti `TypeError`, (b) vraća **fallback na `_sr`** vrednost kada traženi jezik-atribut ne postoji ILI mu je vrednost prazna, (c) **nikada ne baca izuzetak** za nepodržan/nepoznat jezik. Referentna implementacija:
  ```python
  def localized(self, base):
      lang = (get_language() or "sr")[:2]
      return getattr(self, f"{base}_{lang}", "") or getattr(self, f"{base}_sr", "")
  ```
  AC8 se smatra ispunjenim samo ako je ovo fallback ponašanje **testabilno** dokazano: (i) `get_language()` → `None` ne baca grešku i vraća `_sr` vrednost; (ii) nepodržan jezik (npr. `de`) vraća `_sr` vrednost; (iii) prazan `_en` uz aktivan `en` jezik vraća `_sr` vrednost. `description_fr` ostaje u modelu ali se **ne** uključuje u obim prevoda (UI/sadržaj FR van MVP — arh §1.3). `django-modeltranslation` se NE koristi (arh §1.3).

- [x] **AC9 — `Property.slug` auto-generacija (kolizijski-bezbedna, testabilno).** `slug` se automatski generiše iz `title` (npr. `slugify` u `save()` ako je prazan) i ostaje stabilan; ručno zadat slug se poštuje. Pošto je polje `unique=True` (AC3), generacija mora biti **kolizijski-bezbedna**: pri sudaru sa postojećim slugom dodaje se numerički sufiks (npr. `-2`, `-3`) dok se ne dobije jedinstvena vrednost. **Testabilni kriterijum:** dve `Property` instance sa **istim `title`** rezultuju **različitim** slugovima i **ne** izazivaju `IntegrityError`. (Resetovanje sluga pri "Dupliraj" akciji je admin ponašanje iz 1.4 — ovde samo auto-generacija na modelu.)

- [x] **AC10 — Migracije generisane i čiste (lokalno verifikabilno).** Za svaki app je generisana inicijalna migracija (`python manage.py makemigrations core properties inquiries pages` kreira po jedan `0001_initial.py` u `*/migrations/`). `python manage.py makemigrations --check --dry-run` izlazi **bez** predloženih izmena (nema "nesnimljenih" promena modela). (Test DB je SQLite — vidi Dev Notes.)

- [x] **AC11 — `python manage.py check` prolazi.** `python manage.py check` ne prijavljuje greške (E-nivo). Svi FK/M2M se razrešavaju, choices/Meta validni, app-ovi se učitavaju.

- [x] **AC12 — `migrate` na SQLite test bazi prolazi; Postgres `migrate` verifikabilan-kad-DB-dostupna.** Na lokalnoj SQLite test bazi (`config/settings/test.py` ili `conftest` override — vidi Dev Notes) `python manage.py migrate` kreira sve tabele bez greške i `SiteSettings` singleton se može sačuvati (drugi zapis se odbija). Verifikacija na **PostgreSQL 16** (`migrate` na realnom Postgresu) je odložena do kad baza bude dostupna / pre-deploy; ovaj AC se na Postgresu potvrđuje tek tada (ne blokira lokalni razvoj).

- [x] **AC13 — Field-level smoke verifikacija (contract, ne samo migracije).** Pošto AC10–AC12 dokazuju samo da migracije/`check`/`migrate` prolaze — a NE da su polja/choices/relacije zaista tačni (dev bi mogao izostaviti ili preimenovati polje i i dalje proći) — postoji model smoke test koji instancira/inspekcijom proverava svaki model i tvrdi ključni ugovor:
  - svaki od 6 modela (`SiteSettings`, `Property`, `PropertyImage`, `PropertyFeature`, `Inquiry`, `Page`) postoji sa očekivanim poljima;
  - broj/vrednosti `choices` za: `Property.status`, `Property.collection_type`, `Property.property_type`, `Inquiry.inquiry_type`, `Inquiry.status`, `Inquiry.preferred_language`, `PropertyFeature.category`;
  - relacije: `PropertyImage.property` → `Property` sa `on_delete=CASCADE`; `Inquiry.property` → `Property` sa `on_delete=SET_NULL` i `null=True`; `Property.features` M2M → `PropertyFeature`;
  - UUID primarni ključevi na `Property` i `Inquiry`;
  - `unique=True` na `Page.slug` i (preporučeno) `Property.slug`.
  > Napomena za TEA/Dev: ovo je **spec ugovora** — sam test piše Dev/TEA u priči implementacije; SM ovde ne piše test, samo definiše šta test mora da tvrdi.

## Tasks / Subtasks

- [x] **T1 — `core` / SiteSettings (singleton)** *(AC1, AC2, AC8)*
  - [x] U `core/models.py` definiši `SiteSettings` sa svim poljima iz §5.2 (AC1), srpski `verbose_name`/`__str__`.
  - [x] Implementiraj singleton: fiksiran `pk` u `save()`, blokiran `delete()` ili menadžer `load()`/`get_solo()` (AC2).
  - [x] Dodaj `localized(base)` helper za `founder_title`, `founder_bio`, `hero_headline`, `hero_cta_text` sa fallbackom na `_sr` (AC8).
  - [x] Odluči realizaciju `RichTextField` (`TextField` ili `tinymce.models.HTMLField`) — dosledno kroz sve modele (vidi Dev Notes).

- [x] **T2 — `properties` / PropertyFeature** *(AC5, AC8)*
  - [x] Definiši `PropertyFeature` (AC5) sa `category` choices i `name_sr`/`name_en`.
  - [x] Dodaj `localized("name")` helper (AC8). Definiši pre `Property` ili koristi string referencu u M2M.

- [x] **T3 — `properties` / Property** *(AC3, AC8, AC9)*
  - [x] Definiši `Property` sa SVIM poljima iz §5.2 (AC3): UUID pk, choices (`status`, `collection_type`, `property_type`), media polja (ImageField/FileField), geo (`latitude`/`longitude`), SEO, timestamps.
  - [x] M2M `features` → `PropertyFeature`.
  - [x] `localized("description")` helper sa fallbackom na `_sr`; `description_fr` ostaje van obima prevoda (AC8).
  - [x] Slug auto-generacija iz `title` u `save()` uz jedinstvenost (AC9).
  - [x] `Meta`: `ordering`, `verbose_name`, indeksi za česte filtere (`is_active`, `collection_type`, `status`).

- [x] **T4 — `properties` / PropertyImage** *(AC4)*
  - [x] Definiši `PropertyImage` (FK CASCADE → `Property`, `related_name="images"`, `image`, `caption`, `order`, `is_hero`), `Meta.ordering=["order"]` (AC4).

- [x] **T5 — `inquiries` / Inquiry** *(AC6)*
  - [x] Definiši `Inquiry` sa svim poljima iz §5.2 (AC6): UUID pk, FK → `Property` (`null=True`, `SET_NULL`), choices (`inquiry_type`, `status` default `new`, `preferred_language` = `sr`/`en`/`fr`), `ip_address`, `created_at`.
  - [x] `Meta.ordering=["-created_at"]`, srpski `verbose_name`, `__str__`.

- [x] **T6 — `pages` / Page** *(AC7, AC8)*
  - [x] Definiši `Page` (AC7): `slug` unique, `title_sr`/`_en`, `content_sr`/`_en`, `meta_*`, `is_active`.
  - [x] `localized("title")` i `localized("content")` helperi sa fallbackom na `_sr` (AC8).

- [x] **T7 — Generisanje i provera migracija** *(AC10, AC11)*
  - [x] `python manage.py makemigrations core properties inquiries pages` → po jedan `0001_initial.py`.
  - [x] `python manage.py makemigrations --check --dry-run` → bez predloženih izmena (AC10).
  - [x] `python manage.py check` → bez grešaka (AC11).

- [x] **T8 — Verifikacija migracija na test bazi** *(AC12)*
  - [x] `python manage.py migrate` na SQLite test bazi → sve tabele kreirane bez greške.
  - [x] Sanity provera singletona (npr. u shell-u/testu): drugi `SiteSettings.objects.create()` ne stvara drugi red.
  - [x] Dokumentuj da je Postgres `migrate` odložen do dostupnosti baze (ne blokira ovu priču).

- [x] **T9 — Field-level smoke verifikacija (contract za TEA/Dev)** *(AC13)*
  - [x] Definiši/izvrši model smoke test koji inspekcijom tvrdi: postojanje svih 6 modela i ključnih polja; `choices` count/vrednosti (`status`, `collection_type`, `property_type`, `inquiry_type`, `Inquiry.status`, `preferred_language`, `PropertyFeature.category`); relacije (`PropertyImage.property`→CASCADE, `Inquiry.property`→SET_NULL & `null=True`, `Property.features` M2M→`PropertyFeature`); UUID pk na `Property`/`Inquiry`; `unique=True` na `Page.slug` i `Property.slug`.
  - [x] Napomena: sam test piše Dev/TEA u priči implementacije — SM definiše samo ugovor (AC13).

## Dev Notes

- **Izvor istine za polja = zadatak §5.2.** Arhitektura (§1.3, §2) i epics.md **referenciraju** §5.2, ne prepisuju ga. Polja, tipovi i choices iznad su transkripcija iz `docs/Velegrad Estate - Projektni zadatak.docx.md` §5.2. **Ne izmišljati polja** i ne menjati tipove.
- **Granice app-ova (arh §2):** `core`→`SiteSettings`, `properties`→`Property`/`PropertyImage`/`PropertyFeature`, `inquiries`→`Inquiry`, `pages`→`Page`. App-ovi već postoje iz 1.1 (prazni `models.py`).

- **OBAVEZNI Django parametri (blokiraju `makemigrations` ako nedostaju).** §5.2 daje samo tip polja; Django zahteva dodatne parametre. Vrednosti dole su **deo specifikacije ove priče** — dev ih primenjuje doslovno. Ne menjaju imena/tipove/choices iz §5.2, samo dodaju tehnički obavezne parametre.

- **Tabela 1 — `DecimalField` preciznost (`max_digits` / `decimal_places`).** `DecimalField` BEZ ova dva parametra → `makemigrations` baca `TypeError` (blokira AC10). Sva `DecimalField` polja:

  | Polje | Model | `max_digits` | `decimal_places` | Napomena |
  | :---- | :---- | :----: | :----: | :---- |
  | `price` | Property | 12 | 2 | cena u EUR (do 9.999.999.999,99) |
  | `area_sqm` | Property | 8 | 2 | stambena m² |
  | `area_total_sqm` | Property | 8 | 2 | ukupna m² |
  | `latitude` | Property | 9 | 6 | WGS84 (-90..90 sa 6 dec.) |
  | `longitude` | Property | 9 | 6 | WGS84 (-180..180 sa 6 dec.) |

- **Tabela 2 — `CharField` `max_length` (OBAVEZNO za svaki `CharField`/`SlugField`).** Django `CharField`/`SlugField` BEZ `max_length` → `makemigrations` greška (AC10). `TextField`/`EmailField`/`URLField`/`RichTextField` NE koriste `max_length` (eksplicitno izostaviti — Django default `EmailField`=254, `URLField`=200). Vrednosti:

  | Model | Polje | `max_length` |
  | :---- | :---- | :----: |
  | Property | `title` | 200 |
  | Property | `slug` (SlugField) | 255 |
  | Property | `status` | 20 |
  | Property | `collection_type` | 20 |
  | Property | `property_type` | 20 |
  | Property | `location_city` | 100 |
  | Property | `location_district` | 100 |
  | Property | `location_address` | 255 |
  | Property | `meta_title` | 70 |
  | PropertyImage | `caption` | 255 |
  | PropertyFeature | `name_sr` | 100 |
  | PropertyFeature | `name_en` | 100 |
  | PropertyFeature | `icon` | 50 |
  | PropertyFeature | `category` | 20 |
  | Inquiry | `inquiry_type` | 20 |
  | Inquiry | `name` | 150 |
  | Inquiry | `phone` | 30 |
  | Inquiry | `preferred_language` | 5 |
  | Inquiry | `budget_range` | 100 |
  | Inquiry | `property_type_wanted` | 100 |
  | Inquiry | `status` | 20 |
  | SiteSettings | `phone_primary` | 30 |
  | SiteSettings | `whatsapp_number` | 20 |
  | SiteSettings | `founder_name` | 150 |
  | SiteSettings | `founder_title_sr` | 150 |
  | SiteSettings | `founder_title_en` | 150 |
  | SiteSettings | `hero_headline_sr` | 200 |
  | SiteSettings | `hero_headline_en` | 200 |
  | SiteSettings | `hero_cta_text_sr` | 80 |
  | SiteSettings | `hero_cta_text_en` | 80 |
  | SiteSettings | `google_analytics_id` | 50 |
  | SiteSettings | `facebook_pixel_id` | 50 |
  | SiteSettings | `seo_default_title` | 70 |
  | Page | `slug` (CharField) | 100 |
  | Page | `title_sr` | 200 |
  | Page | `title_en` | 200 |
  | Page | `meta_title` | 70 |

  **NE koriste `max_length` (Text/Email/URL/RichText):** SiteSettings `email_primary`, `email_inquiries` (EmailField), `address`, `seo_default_description`, `founder_bio_sr`, `founder_bio_en` (Text/RichText), `hero_video_url` (URLField); Property `description_sr`/`_en`/`_fr` (RichText), `meta_description` (Text), `virtual_tour_url` (URLField); Inquiry `email` (EmailField), `message`, `notes` (Text); Page `content_sr`/`_en` (RichText), `meta_description` (Text).

- **Tabela 3 — `BooleanField` `default` (OBAVEZNO za non-interaktivni `makemigrations`).** `BooleanField` bez `default` → `makemigrations` traži interaktivni unos ili pada u CI (blokira AC10). Dosledna politika: nekretnina/stranica je **objavljena po defaultu** (agent kreira kompletan unos pre snimanja), sve ostalo `False`.

  | Model | Polje | `default` | Obrazloženje |
  | :---- | :---- | :----: | :---- |
  | Property | `is_active` | `True` | objavljeno po defaultu (agent unosi kompletan zapis) |
  | Property | `is_featured` | `False` | featured je svesna odluka |
  | Property | `show_address` | `False` | adresa skrivena dok se ne uključi |
  | Property | `price_on_request` | `False` | cena se podrazumevano prikazuje |
  | PropertyImage | `is_hero` | `False` | hero se eksplicitno bira |
  | Page | `is_active` | `True` | stranica objavljena po defaultu (dosledno sa Property) |
- **Dvojezičnost (arh §1.3):** koriste se **eksplicitna `_sr`/`_en` polja** iz §5.2; `django-modeltranslation` se NE koristi (duplirao bi/konfliktovao). `localized(base)` helper mora biti **robustan** (vidi AC8): `lang = (get_language() or "sr")[:2]; return getattr(self, f"{base}_{lang}", "") or getattr(self, f"{base}_sr", "")` — obrađuje `get_language()` → `None`, fallback na `_sr` kada atribut nedostaje ili je prazan, i ne baca grešku za nepodržan jezik. `{% loc %}` template tag i UI `gettext` su Epik 2/6 — **nisu** u ovoj priči (ovde samo model helper). `description_fr` ostaje u modelu ali van obima prevoda.
- **`RichTextField` realizacija (MANDAT, ne preporuka):** Django nema ugrađen `RichTextField`. SVA RichText polja (`description_*`, `founder_bio_*`, `content_*`) se **OBAVEZNO** realizuju kao `tinymce.models.HTMLField` — dosledno kroz sve modele. Zavisnost `django-tinymce` već postoji u `base.txt` iz 1.1. Ključno: `HTMLField` je podklasa `TextField`, pa za prolaz `makemigrations`/`check`/`migrate` **NIJE** potrebno dodavati `'tinymce'` u `INSTALLED_APPS` (uvozi se samo `from tinymce.models import HTMLField`); registracija TinyMCE app-a i WYSIWYG admin widget su tema 1.4 i ne diraju model. Ovim admin 1.4 dobija WYSIWYG bez ikakve izmene modela.
- **Singleton `SiteSettings` (arh §2):** enforce tačno jedan red (fiksan `pk=1` u `save()`, blokiran `delete()`, `load()`/`get_solo()` klasna metoda). Admin "samo izmena, bez dodavanja drugog" je tema 1.3/1.4 — ovde je enforcement na **modelu**.
- **Slug:** auto-generacija iz `title` (`slugify`) kad je prazan; polje je `unique=True`, pa kolizije rešavati numeričkim sufiksom (`-2`, `-3`...) dok se ne dobije jedinstvena vrednost (AC9 — testabilno: dva ista `title` → dva različita sluga, bez `IntegrityError`). Reset sluga pri "Dupliraj" je admin akcija iz 1.4.
- **SEO meta single-language (odložena odluka, NE menja se u 1.2):** `Property.meta_title`/`meta_description` i `Page.meta_title`/`meta_description` su **jednojezična** po §5.2 (kako i stoji u modelu). Dvojezičan SEO meta je poznato ograničenje §5.2 koje se revidira u priči **6.2 (SEO)** — ovde se NE dodaju `_sr`/`_en` varijante; flag kao deferred decision.
- **`PropertyImage.is_hero` jedinstvenost-po-nekretnini (opciono):** pravilo "tačno jedna hero slika po `Property`" enforce-uje se na **admin nivou (1.4)**; opciono se može dodati model `clean()`/`UniqueConstraint(condition=Q(is_hero=True))` — nije obavezno za ovu priču i ne treba over-engineer-ovati.
- **OUT OF SCOPE (kasnije priče):** admin tematizacija/registracija i Unfold dashboard (1.3), sortable inline galerija / TinyMCE widget / duplikovanje / preview (1.4), view-ovi/template-i/forme (Epik 2+), `django-imagekit` WebP/`srcset` renditioni iznad pukog `ImageField`/`FileField` (6.3), inquiry email notifikacija/auto-reply i anti-spam rate-limit/honeypot (5.2). **Minimalna `admin.register` NIJE potrebna ovde** — admin se radi u 1.3/1.4 (arh §1.1 vezuje admin za posebne priče).
- **Media polja (arh §1.4):** `ImageField`/`FileField` se definišu standardno (`upload_to` po modelu, npr. `properties/hero/`, `properties/gallery/`, `properties/floorplans/`, `site/`). `django-storages`/S3 i `django-imagekit` varijante su van obima (apstrakcija je spremna iz 1.1; aktivacija kasnije). `Pillow` (iz 1.1) je dovoljan za `ImageField`.
- **Baza za verifikaciju — SQLite test (env odluka):** lokalni PostgreSQL NIJE dostupan u ovom okruženju. Pytest/`migrate` provere idu na **SQLite test bazu** (preko `config/settings/test.py` ili `conftest` override). Zato su AC10/AC11 (makemigrations/check) i AC12 (migrate na SQLite) lokalno verifikabilni; realni Postgres 16 `migrate` je odložen do kad baza bude dostupna / pre-deploy (arh §0/§6). **Napomena na UUID/DecimalField:** rade i na SQLite i na Postgresu — nema rizika za šemu pri ovom transferu.
- **Veza sa 1.1:** `INSTALLED_APPS` već sadrži 4 custom app-a (1.1 AC2), pa `makemigrations <app>` odmah radi. `DJANGO_SETTINGS_MODULE` lokalno = `config.settings.dev` (ili `.test` za test run).
- **Git poruke na engleskom** (zadatak §9) — ali ova priča je samo spec; commit radi dev priča.

## Definition of Done

- [x] Svih 6 modela iz §5.2 definisano u tačnim app-ovima sa tačnim poljima/tipovima/choices (AC1, AC3–AC7), bez izmišljenih polja.
- [x] `SiteSettings` je singleton (najviše jedan red), `Property.slug` se auto-generiše, `localized()` helper sa `_sr` fallbackom postoji na svim dvojezičnim modelima (AC2, AC8, AC9).
- [x] `makemigrations` generisao po jedan `0001_initial.py` za `core`/`properties`/`inquiries`/`pages`; `makemigrations --check --dry-run` čist (AC10).
- [x] `python manage.py check` bez grešaka (AC11).
- [x] `migrate` na SQLite test bazi kreira sve tabele bez greške; Postgres `migrate` zabeležen kao odložen-do-DB (AC12).
- [x] Field-level smoke test (contract) tvrdi tačnost polja/choices/relacija/UUID pk/`unique` slugova za svih 6 modela (AC13).
- [x] Obim ispoštovan: SAMO modeli + migracije; admin/view/template/email/imagekit nisu dirani (vidi Dev Notes — OUT OF SCOPE).
