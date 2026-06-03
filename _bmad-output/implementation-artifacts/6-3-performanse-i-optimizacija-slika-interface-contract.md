---
story-id: 6-3-performanse-i-optimizacija-slika
artifact: interface-contract
title: Interface Contract — Performanse i optimizacija slika (WebP + responsive srcset preko django-imagekit, lazy-load, storage-agnostic varijante)
status: red-phase
author: TEA (Test Architect)
created: 2026-06-03
test-file: tests/test_image_optimization.py
---

# Interface Contract — Story 6.3 (Performanse i optimizacija slika)

Ovaj dokument je MAŠINSKI UGOVOR koji developer (GREEN faza) mora da zadovolji da bi
`tests/test_image_optimization.py` (RED faza) prošli. Svaka stavka je izvedena iz
LOCKED odluka u
`_bmad-output/implementation-artifacts/6-3-performanse-i-optimizacija-slika.md`
(3-validatorski panel + empirijski imagekit 6.1.0 run). Ono što ovde piše je
NEPREGOVORLJIVO; testovi to direktno verifikuju.

---

## 1. Settings (`config/settings/base.py`)

### 1.1 `imagekit` u INSTALLED_APPS (AC1)
- `"imagekit"` MORA biti član `settings.INSTALLED_APPS` (app label je `imagekit`;
  paket `django-imagekit` je već u `requirements/base.txt` — BEZ novog paketa).
- Pozicija: uz ostale 3rd-party app-ove pre custom (`core`/`properties`/`inquiries`/`pages`).
- `python manage.py check` mora ostati čist; `makemigrations --check --dry-run`
  čist (`imagekit` nema model koji migrira; `ImageSpecField` nije DB kolona).

### 1.2 ImageKit cachefile strategija — OBAVEZAN-ZA-ISPRAVNOST (AC1)
- `settings.IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY == "imagekit.cachefiles.strategies.Optimistic"`.
- Razlog (EMPIRIJSKI, imagekit 6.1.0): default `JustInTime` pri `.url` pristupu
  OTVARA izvorni fajl → `FileNotFoundError`/HTTP 500 na byteless seed-u/dev-u.
  `Optimistic` čini `.url` ČISTOM string operacijom (`source.name` + spec hash):
  bez I/O, bez Celery, bez kreiranja fajla. Ovo je MANDATORY, ne preporuka.
- Dokumentovati izbor komentarom (6.2 stil) sa empirijskim rationale-om.
- Opciono: `IMAGEKIT_CACHE_BACKEND` (ne testira se; `default` LocMemCache je već
  konfigurisan).

### 1.3 MEDIA_URL leading-slash (regression guard)
- Renderovani variant/srcset URL-ovi MORAJU počinjati sa `/` (idealno `"/media/"`).
- `MEDIA_URL` je trenutno `"media/"` (relativni). Ako rendererani `.url` ne dobije
  vodeću kosu crtu, minimalni scoped fix je `MEDIA_URL = "/media/"`. Ovo je
  OČEKIVANA dozvoljena izmena.

---

## 2. Storage (`config/settings/base.py` + `core/storages.py`)

### 2.1 `core/storages.py` pure helper — KANONSKI AC4 dom (AC4)
- NOVI modul `core/storages.py` sa ČISTOM funkcijom koja preslikava
  `STORAGE_BACKEND` ime → DJANGO BACKEND STRING:
  - ulaz `"local"` → `"django.core.files.storage.FileSystemStorage"`
  - ulaz `"s3"`    → `"storages.backends.s3.S3Storage"`
- Funkcija mora biti pozvana DIREKTNO u unit-testu (vraća STRING). Bilo koji od
  ovih naziva je prihvaćen (test ih traži po redu, prvi koji postoji se koristi):
  `default_storage_backend`, `storage_backend_for`, `resolve_storage_backend`,
  `get_default_storage_backend`, `storage_backend`.
  Funkcija prima JEDAN string argument (ime backend-a).
- Razlog za pure-helper: Django `override_settings` NE re-izvršava module-level
  `base.py`, pa se module-level `STORAGES` ne može prebaciti monkeypatch-om env-a
  u test-vremenu → izbor MORA živeti u čistoj funkciji testabilnoj direktno.

### 2.2 `STORAGES` dict (AC4)
- `settings.STORAGES` MORA postojati i imati ključeve `"default"` i `"staticfiles"`.
- `settings.STORAGES["default"]["BACKEND"]` MORA postojati i, pod default env-om
  (`STORAGE_BACKEND="local"`), razrešavati na `FileSystemStorage`
  (NE hardkodovan S3). `default` backend se bira preko helpera iz §2.1.
- `staticfiles` ostaje FS/whitenoise (static NIJE media).

### 2.3 ImageKit cachefile storage NIJE hardkodovan FS (AC4)
- `IMAGEKIT_DEFAULT_FILE_STORAGE` SME biti: (a) nepostavljen, ILI (b) jednak
  `"default"`. NE sme biti hardkodovan `FileSystemStorage` string.
- Tako varijante prolaze kroz isti `default_storage` → S3-ready.

### 2.4 S3 ODLOŽEN za 6.4 (AC4 / regression)
- `STORAGE_BACKEND` default ostaje `"local"`.
- `boto3` ostaje KOMENTARISAN u `requirements/base.txt` (test_project_setup zelen).
- AWS_* env varijable se NE postavljaju.

---

## 3. ImageKit spec-ovi / varijante (`properties/`, `core/`)

### 3.1 Mehanizam — LOCKED (AC1, AC3)
- Dozvoljen je SAMO `ImageSpecField` (atribut modela) ILI registrovani `ImageSpec`
  renderovan u template-u preko spec-ovog **`.url`** (string operacija, I/O-free
  pod Optimistic).
- ⛔ ZABRANJENO: `{% generateimage %}`/`{% thumbnail %}` bez eksplicitnih
  `width=`/`height=` html atributa — pristupaju `.width`/`.height` → otvaraju
  cachefile → HTTP 500 na byteless ČAK I pod Optimistic.
- Ručna Pillow konverzija van ImageKit-a NIJE dozvoljena.

### 3.2 Format i širine (AC1, AC3)
- Format-literal `"WEBP"` (JEDAN token kroz celu priču; NE `"WebP"`).
- Bar DVE širine za responsive `srcset` (preporuka 480/960/1440 — usklađeno sa
  NFR-2 breakpointima 375/768/1280). Širine definisane JEDNOM (konstanta) za
  doslednost `srcset` deskriptora.
- Polja koja dobijaju WebP/srcset varijante: `Property.hero_image`,
  `PropertyImage.image`, `SiteSettings.hero_image`, `SiteSettings.founder_photo`.
- `ImageSpecField`/registrovani spec NIJE DB kolona → BEZ migracije.

---

## 4. Template-i (`home.html`, `properties.html`, `property-detail.html`, `about.html`)

### 4.1 `<picture>` markup za media slike (AC1, AC3)
- Za svaku NEPRAZNU media sliku, `<img>` se zamenjuje:
  ```
  <picture>
    <source type="image/webp" srcset="<v480> 480w, <v960> 960w[, <v1440> 1440w]">
    <img src="<original-ili-srednja-varijanta>" alt="..." [loading="lazy"]>
  </picture>
  ```
- `<source>` MORA imati `type="image/webp"` i `srcset` sa BAR DVE `NNNw` širine.
- `srcset` URL-ovi grade se preko spec `.url` (string-safe) i počinju sa `/`.
- Svaki `<img>` ZADRŽAVA `alt` (a11y; postojeći testovi asertuju `alt`).

### 4.2 Lazy-load mapiranje (AC2)
- ISPOD-fold (`loading="lazy"`): property-card (`home.html`, `properties.html`),
  thumbnail-strip (`property-detail.html`), founder portret (`about.html`,
  `home.html` advisor).
- ABOVE-fold (NEMA `loading="lazy"` — eager default, atribut izostavljen):
  `home.html` hero, `property-detail.html` detail-hero.

### 4.3 `sizes` na detail-hero — standalone AC3
- `property-detail.html` detail-hero `<picture>`/`<img>` MORA imati `sizes`
  atribut (npr. `sizes="100vw"`) tako da mobilni bira manju varijantu.

### 4.4 Placeholder grananje (AC1)
- Kad je media polje prazno (`hero_image=""`, nema `founder_photo`), renderuje se
  POSTOJEĆI `{% static %}` SVG placeholder kao običan `<img>` — BEZ WebP `<source>`,
  BEZ ImageKit poziva, BEZ 500.

### 4.5 GRANICE (NE DIRATI) — 6.2 SEO i 3.2 galerija
- `og:image` (`property-detail.html` l.44) i Schema `image` ostaju PUN
  `hero_image.url` (sadrži source filename, npr. `x.jpg`). NE menjati na varijantu.
- Thumbnail `data-full` ostaje PUNA `img.image.url` (gallery.js lightbox/dedup).
- Lightbox `<img src="">` (l.289) i `base.html` logo SVG se NE diraju.

---

## 5. Regression invarijante
- SR (`GET /`) i EN (`GET /en/`) → 200.
- `tests/test_seo.py` zelen (og:image i dalje sadrži source filename).
- `tests/test_property_detail.py` zelen (`data-full` očuvan).
- `tests/test_base_layout.py`/`tests/test_home_page.py` zeleni (`<picture><img>`
  zadržava `alt`).
- `tests/test_project_setup.py` zelen (boto3 komentarisan; imagekit/storages aktivni).
- `python manage.py check` čist; BEZ projektnih migracija; BEZ novog paketa.
</content>
</invoke>
