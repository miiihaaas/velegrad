---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/planning-artifacts/PRD.md
  - docs/Velegrad Estate - Projektni zadatak.docx.md
  - docs/OpenDesignFiles/
workflowType: 'architecture'
project_name: 'Velegrad Estate'
user_name: 'Mihas'
date: '2026-06-01'
status: 'final'
---

# Velegrad Estate — Arhitektonski dokument (LEAN)

> **Svrha.** Ovaj dokument **ne prepisuje** PRD ni projektni zadatak — on **zaključava otvorene tehničke odluke** iz PRD §2 ("pretpostavke za potvrdu") i daje implementacionim agentima jednoznačan okvir. Za modele/polja referenca je zadatak §5.2, za dizajn `OpenDesignFiles/`, za zahteve PRD §3–§5.
>
> **Zaključano u izvorima (uzeto kao dato):** Python/Django, PostgreSQL, Nginx + Gunicorn, Let's Encrypt, SR (primarni) + EN, Docker opciono, lokalni razvoj → Linux VPS.

---

## 0. Verzije platforme (zaključano)

| Komponenta | Verzija | Razlog |
| :---- | :---- | :---- |
| Python | **3.12** | Stabilna, prisutna na svim aktuelnim Linux VPS distribucijama; podržava Django 5.2. |
| Django | **5.2 LTS** | LTS (podrška do 2028) — bitno za projekat sa malim budžetom i dugim životom bez čestih migracija. |
| PostgreSQL | **16** | Aktuelna stabilna; nativni podržan od strane Django/psycopg3. |
| Node | nije potreban u runtime-u | Dizajn je gotov CSS/JS (vanilla). Bez build koraka, bez Tailwind toolchaina. |

**Frontend napomena:** zadatak §5.1 pominje "Tailwind ili custom CSS" — dizajn je **gotov custom CSS** (`OpenDesignFiles/`), pa Tailwind **otpada**. Nema frontend build pipeline-a; assets se serviraju kao statika.

---

## 1. Pet ključnih odluka (PRD §2)

### 1.1 CMS / Admin — **tematizovani Django admin ("Velegrad CMS"), bez Wagtail-a**

**Odluka:** brendiran Django admin sa `django-unfold` temom. **Ne** Wagtail, **ne** čist (nestilizovan) admin.

**Obrazloženje:**
- **Wagtail otpada** — page-tree/StreamField model rešava problem koji ovde ne postoji. Sadržajni set je fiksan i mali (6 modela, ~3 statične stranice), dizajn je već gotov i bespoke; Wagtail bi udvostručio templating i nametnuo svoj editor preko našeg dizajna, uz veću krivu učenja za klijenta. Veći trošak, nula dobiti za MVP.
- **Čist admin otpada** — zadatak §9 eksplicitno traži premium, brendiran CMS; default Django admin ne prenosi taj utisak i dashboard sa metrikama nije nativan.
- **`django-unfold` pobeđuje** — moderan, MIT licenca, Tailwind-bazirana tema sa podrškom za brand boje, custom dashboard sa karticama/metrikama, čist UX za netehničkog klijenta. Pokriva zadatak §5.3 uz minimalan trud.

**Tačan spisak admin paketa:**

| Paket | Uloga | Mapira na zahtev |
| :---- | :---- | :---- |
| `django-unfold` | Tema (Deep Olive/Champagne brend boje), dashboard sa metrikama, brze akcije | §5.3 Dashboard, premium utisak |
| `django-admin-sortable2` | Drag&drop redosled galerije (`PropertyImage.order`) preko inline-a | §5.3 "Upload fotografija — reorder" |
| `django-tinymce` | WYSIWYG za `RichTextField` opise (TinyMCE) | §5.3 "RichText editor — WYSIWYG" |

> **Zašto TinyMCE, ne CKEditor:** `django-ckeditor` (CKEditor 4) je EOL sa sigurnosnim/licencnim opterećenjem; `django-tinymce` je besplatan, stabilan i aktivno održavan.

**Admin implementacioni detalji:**
- `PropertyImage` kao **sortable inline** unutar `Property` admina (hero toggle + reorder + caption).
- **Dashboard** preko Unfold `DASHBOARD_CALLBACK`: aktivne nekretnine, novi upiti (`status=new`), featured; brze akcije "Dodaj nekretninu" / "Upiti".
- **Duplikovanje** nekretnine: admin action "Dupliraj" (kopira polja + features, resetuje slug/slike).
- **Preview pre objave:** `is_active=False` + admin link na detail view sa `?preview=1` (vidljiv samo prijavljenom staff korisniku).
- **Dvojezičan unos:** SR/EN polja grupisana u Unfold fieldset-ovima sa jasnim labelama (vidi §1.3).
- **Admin putanja:** nestandardna, iz env (`ADMIN_URL`, default npr. `velegrad-cms/`) — zadatak §5.8.

### 1.2 Listing filter — **server-side (GET reload) za MVP**

**Odluka:** filteri se primenjuju **server-side** preko GET query parametara sa page reload-om. AJAX/API (`/api/properties/`, zadatak §5.5) je **van obima MVP-a**.

**Obrazloženje:** max 12 nekretnina, premium "curated" osećaj — reload je trenutan i neprimetan na tako malom skupu. Server-side render je SEO-friendly (filtrirani URL-ovi su indeksabilni), jednostavniji, bez API sloja i bez duplikovanja logike.

**Implementacija:**
- `PropertyListView` čita validirane GET parametre (`location`, `type`, `price_min`/`price_max`, `bedrooms`, `status`, `q`) i gradi queryset.
- Lagana `PropertyFilterForm` (Django forms) za validaciju + render kontrola; **bez** `django-filter` (hand-rolled je ovde manji i potpuno pod kontrolom dizajna).
- Postojeći `filters.js` zadržava UX (price slider, dropdown ponašanje) ali **submituje formu** (GET) — bez XHR-a.
- Queryset: `collection_type='signature'`, `is_active=True`, `[:12]`.

### 1.3 i18n — **Django ugrađeni i18n + eksplicitna dvojezična polja u modelu (bez `django-modeltranslation`)**

**Odluka (nameće je sama šema):** modeli u zadatku §5.2 **već imaju eksplicitna dvojezična polja** (`description_sr`/`description_en`, `title_sr`/`title_en`, `content_sr`/`content_en`, `founder_bio_sr`/`founder_bio_en`, `hero_headline_sr`/`hero_headline_en`...). Zato:

- **Sadržaj iz baze** → eksplicitna `_sr`/`_en` polja (kako su definisana). **`django-modeltranslation` se NE koristi** — duplirao bi/konfliktovao sa već postojećim poljima.
- **UI stringovi** (dugmad, labele, navigacija, poruke) → Django `gettext` (`{% trans %}` / `_()`), `.po`/`.mo` fajlovi, `locale/sr/` i `locale/en/`.
- **Routing** → `i18n_patterns` sa `prefix_default_language=False`: SR (default) bez prefiksa (`/properties/`), EN sa `/en/` prefiksom (`/en/properties/`). `LocaleMiddleware` aktivan.
- **Language switcher** (header, diskretan) → linkuje na ekvivalentni URL na drugom jeziku (preko `{% translate_url %}` / `set_language` view).
- **Pristup dvojezičnom sadržaju** → helper na modelu, npr. `def localized(self, base)` koji vraća `getattr(self, f"{base}_{get_language()[:2]}")` sa fallbackom na `_sr`. Template tag `{% loc property "description" %}` za čist template.
- **FR van obima** — `description_fr` ostaje u modelu (zadatak §5.2) ali se UI/sadržaj **ne** prevodi (PRD §2).

### 1.4 Media storage — **lokalni FS + Nginx, apstrahovano kroz django-storages (S3 opcija)**

**Odluka:** media na lokalnom file sistemu (`MEDIA_ROOT`), servirano preko Nginx-a u produkciji. Storage backend apstrahovan kroz `django-storages` tako da se prebacivanje na S3 radi **samo env varijablama**, bez izmene koda.

**Implementacija:**
- `STORAGES["default"]` bira backend prema `STORAGE_BACKEND` env varijabli: `local` (default, `FileSystemStorage`) ili `s3` (`storages.backends.s3.S3Storage` + `boto3`).
- **Dev:** Django servira media (`MEDIA_URL`).
- **Prod:** Nginx `location /media/` servira fajlove direktno sa diska (ne kroz Gunicorn) — brzo, bez opterećenja app servera.
- **WebP/responsive** (NFR-1): varijante slika preko `django-imagekit` (keširani spec-ovi: WebP + više širina za `srcset`), upisuju se kroz **isti** storage backend → automatski rade i sa S3.
- **Napomena na zadatak §5.8 "media ne servirati direktno":** misli se "ne kroz Django app server" — Nginx serviranje statičkih media fajlova je ispravan, preporučen obrazac. Property foto su javne; nema privatnih media koje bi tražile X-Accel zaštitu u MVP-u.

### 1.5 Email — **Mailgun (django-anymail) + premium HTML template-i**

**Odluka:** transakcioni email preko **Mailgun-a**, integrisan kroz `django-anymail[mailgun]`. Premium HTML template-i renderovani iz Django-a (ne generički Django email).

**Obrazloženje:** Mailgun ima besplatan/jeftin tier dovoljan za zapreminu upita, odličnu deliverability i čistu integraciju; `django-anymail` daje jedinstven API + tracking i lako prebacivanje providera ako zatreba.

**Implementacija:**
- `EMAIL_BACKEND = anymail.backends.mailgun.EmailBackend`; `MAILGUN_API_KEY` + `MAILGUN_SENDER_DOMAIN` iz env-a. **Dev:** `console.EmailBackend`.
- **Dva toka** na novi `Inquiry` (signal/servis u `inquiries` app):
  1. **Notifikacija agentu** → `SiteSettings.email_inquiries`, sa svim podacima upita + linkom na admin.
  2. **Auto-reply kupcu** → brendiran HTML (potvrda prijema, premium ton).
- Template-i pod `templates/email/` (HTML + plain-text alternativa), slanje preko `EmailMultiAlternatives`.
- **Deliverability:** zahteva SPF/DKIM verifikaciju domena na Mailgun-u (deploy checklist, §6).

---

## 2. Struktura Django projekta

```
velegrad/
├── config/                      # Django projekat (settings paket, urls, wsgi)
│   ├── settings/
│   │   ├── base.py              # zajedničko
│   │   ├── dev.py               # lokalni razvoj
│   │   └── prod.py              # VPS
│   ├── urls.py                  # i18n_patterns, sitemaps, admin (env putanja)
│   └── wsgi.py
├── core/                        # zajedničko + SiteSettings
│   ├── models.py                # SiteSettings (singleton)
│   ├── context_processors.py    # site_settings, language u svakom template-u
│   ├── storages.py              # storage backend izbor (local/S3)
│   ├── sitemaps.py              # Property + Page sitemap
│   ├── templatetags/            # {% loc %} dvojezični helper, SEO tagovi
│   └── admin.py                 # Unfold dashboard, SiteSettings admin
├── properties/                  # Property, PropertyImage, PropertyFeature
│   ├── models.py
│   ├── views.py                 # PropertyListView (server-side filter), PropertyDetailView
│   ├── forms.py                 # PropertyFilterForm
│   └── admin.py                 # sortable inline galerija, TinyMCE, duplikovanje
├── inquiries/                   # Inquiry + email + anti-spam
│   ├── models.py
│   ├── forms.py                 # contact / viewing / private_collection forme
│   ├── views.py                 # form handleri (CSRF, rate-limit)
│   ├── emails.py                # notifikacija agentu + auto-reply
│   └── admin.py
├── pages/                       # Page (about, why-velegrad, international)
│   ├── models.py
│   └── views.py                 # PageDetailView po slug-u
├── templates/                   # base.html + page template-i + email/
├── static/                      # iz OpenDesignFiles/ (css, js, fonts, images)
├── locale/                      # sr/, en/ (.po/.mo)
├── media/                       # upload (dev); prod servira Nginx
├── manage.py
├── requirements/                # base.txt, dev.txt, prod.txt
└── .env                         # NIJE u git-u
```

**Granice app-ova (zašto baš ove):**
- **`core`** — `SiteSettings` (singleton) je globalni i ne pripada nijednom domenu; ovde i deljeni templating, context processori, storage, sitemap, i18n helperi.
- **`properties`** — srce kataloga (Property/PropertyImage/PropertyFeature), listing + detail.
- **`inquiries`** — sav lead-capture (svi `inquiry_type`), email i anti-spam izolovani na jedno mesto.
- **`pages`** — `Page` model i statične stranice; razdvojeno od kataloga jer ima drugačiji životni ciklus sadržaja.

---

## 3. Settings / env strategija

- **Split settings** (`base` / `dev` / `prod`), izbor preko `DJANGO_SETTINGS_MODULE`.
- **`django-environ`** čita `.env` (dev) i sistemske env varijable (prod). **Nijedan kredencijal nije u kodu** (zadatak §5.8).
- **`.env` van git-a** (`.gitignore`), sa `.env.example` šablonom u repou.
- **Prod secret management:** `.env` na VPS-u sa restriktivnim pravima (`chmod 600`, vlasnik app korisnik), učitan u systemd unit (`EnvironmentFile=`). `DEBUG=False`, `ALLOWED_HOSTS`, `SECURE_*` (HSTS, SSL redirect, secure cookies) uključeni u `prod.py`.

**Ključne env varijable:** `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `ADMIN_URL`, `STORAGE_BACKEND` (+ `AWS_*` ako S3), `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`, `DEFAULT_FROM_EMAIL`, `GOOGLE_ANALYTICS_ID`.

---

## 4. Ključne zavisnosti (requirements)

| Paket | Razlog |
| :---- | :---- |
| `Django==5.2.*` | Framework (LTS). |
| `psycopg[binary]` | PostgreSQL adapter (psycopg3, preporučen za Django 5.x). |
| `django-environ` | `.env` / env varijable, `DATABASE_URL` parsing. |
| `gunicorn` | WSGI app server (zadatak §5.1). |
| `django-unfold` | Brendiran admin + dashboard (odluka §1.1). |
| `django-admin-sortable2` | Reorder galerije u adminu (§1.1). |
| `django-tinymce` | WYSIWYG za RichText opise (§1.1). |
| `Pillow` | Obrada `ImageField` slika. |
| `django-imagekit` | WebP + responsive `srcset` varijante, keširano (NFR-1). |
| `django-storages` | Apstrakcija storage backenda, S3 opcija (§1.4). |
| `django-anymail[mailgun]` | Mailgun email integracija (§1.5). |
| `django-ratelimit` | Rate-limit na contact/inquiry forme, anti-spam (NFR-5). |
| `whitenoise` | Static fallback (prod primarno servira Nginx; whitenoise daje sigurnu rezervu/jednostavnost). |

**Ugrađeno u Django (bez paketa):** `django.contrib.sitemaps` (sitemap.xml), i18n/gettext, CSRF, `django.contrib.admin`. **Frontend:** Leaflet (CSS/JS, vendorovan u `static/`) za mapu — bez Python paketa, bez API ključa.

> **Anti-spam dopuna:** uz `django-ratelimit` koristi se i **honeypot polje** u formama (skriveno polje koje botovi popunjavaju) — jeftina dodatna zaštita bez CAPTCHA frikcije na premium formi.

---

## 5. Integracija OpenDesignFiles/ u Django

Dizajn je **konačan** i ne preispituje se — samo se "puni" dinamičnim sadržajem.

**Assets (CSS/JS/fonts/images):**
- `OpenDesignFiles/assets/{css,js}` → kopirati u projektni `static/`. Reference preko `{% static %}`.
- `collectstatic` u prod-u → Nginx servira `location /static/` direktno.
- Struktura ostaje: `tokens.css` → `base.css` → `layout.css` → `components.css` → `pages/*.css`; JS: `main.js`, `gallery.js` (lightbox — PRD §3.4), `filters.js` (listing GET), `forms.js` (validacija).

**Templates (9 HTML → Django template-i):**
- Izdvojiti zajedničko iz HTML-a u **`base.html`**: `<head>` (meta/OG/Schema blokovi, GA4), header (nav + diskretan language switcher + hamburger), footer.
- Svaka stranica → template koji `{% extends "base.html" %}` i puni blokove iz konteksta:

| HTML | Template / View | URL |
| :---- | :---- | :---- |
| `index.html` | `home.html` / HomeView | `/` |
| `about.html` | `pages/about.html` / PageDetailView(`about`) | `/about/` |
| `properties.html` | `properties/list.html` / PropertyListView | `/properties/` |
| `property-detail.html` | `properties/detail.html` / PropertyDetailView | `/properties/<slug>/` |
| `private-collection.html` | `inquiries/private_collection.html` | `/private-collection/` |
| `international.html` | `pages/international.html` / PageDetailView | `/international/` |
| `contact.html` | `inquiries/contact.html` | `/contact/` |
| `velegrad-estate.html` | (Why Velegrad — **sekcija na Home**, PRD §3.1) | — |
| `404.html` | `404.html` (custom handler) | — |

- **Placeholder SVG-ovi** (`assets/images/placeholders/`) zamenjuju se `ImageField` media URL-ovima; gde nema slike, fallback na placeholder.
- **Statički tekst** u HTML-u → `{% trans %}` (UI) ili polja iz `SiteSettings`/`Page`/`Property` (sadržaj).

---

## 6. Deploy pipeline (VPS)

**Cilj:** lokalni razvoj → Linux VPS (Ubuntu LTS), bez Docker-a (vidi §7).

1. **Server:** Ubuntu LTS, `python3.12-venv`, PostgreSQL 16, Nginx. App korisnik bez root-a.
2. **Kod:** `git clone` → venv → `pip install -r requirements/prod.txt` → `.env` (chmod 600) → `migrate` → `collectstatic`.
3. **Gunicorn (systemd):** `gunicorn.service` (+ socket) sluša na Unix socket-u; `EnvironmentFile=/path/.env`; auto-restart.
4. **Nginx (reverse proxy):**
   - `location /static/` i `location /media/` → serviraju se direktno sa diska.
   - sve ostalo → proxy na Gunicorn socket.
   - gzip/brotli, cache headeri za statiku, security headeri.
5. **TLS:** Certbot (Nginx plugin) → Let's Encrypt sertifikat, auto-renew (systemd timer). HTTP→HTTPS redirect.
6. **Backup:**
   - **Baza:** dnevni `pg_dump` preko cron-a, retencija (npr. 7 dnevnih + 4 nedeljna), kopija van servera.
   - **Media:** dnevni `tar`/`rsync` `media/` foldera (ili automatski ako se pređe na S3).
7. **Mailgun:** verifikacija domena (SPF/DKIM/MX) pre prvog produkcijskog slanja.
8. **Staging:** zadatak §9 traži staging pre svakog review-a — isti VPS, zaseban subdomen/instanca ili poddirektorijum sa odvojenom bazom.

**Sigurnosni checklist (NFR-5 / zadatak §5.8):** `DEBUG=False`, HSTS + SSL redirect, secure/HTTPOnly cookies, CSRF na svim formama, rate-limit + honeypot na upitima, admin na nestandardnoj putanji, svi kredencijali u env-u, redovan backup.

---

## 7. Docker — finalna preporuka: **NE za MVP** (opcioni put dokumentovan)

**Preporuka:** za MVP **ne** koristiti Docker. Direktan venv + systemd + Nginx je jednostavniji, lakši na resursima na jednom VPS-u, i brži do produkcije — što odgovara malom budžetu/roku ovog projekta.

**Obrazloženje:**
- Jedan servis (Django) + Postgres + Nginx na jednoj mašini — Docker tu dodaje sloj orkestracije bez stvarne koristi.
- Manja potrošnja RAM/CPU na skromnom VPS-u; jednostavniji debug i logovi.
- Zadatak eksplicitno kaže "Docker NIJE obavezan".

**Kada pređi na Docker (dokumentovan put):** ako kasnije zatreba paritet okruženja, lakši onboarding više developera, ili migracija/skaliranje — dodati `Dockerfile` (Gunicorn) + `docker-compose.yml` (web + db + nginx). Settings i env strategija (§3) su već kompatibilni, pa je prelaz aditivan, ne rewrite.

---

## 8. Šta NIJE u obimu (referenca, ne ponavljanje)

Modeli i polja: **zadatak §5.2**. Dizajn/tokeni/komponente: **`OpenDesignFiles/`**. Detalji sadržaja stranica: **PRD §3**. NFR detalji: **zadatak §5.7–5.8, §6**.

**Odloženo (van MVP, PRD §2):** FR lokalizacija, AJAX live-filter + `/api/` sloj, virtual tour authoring, Facebook Pixel, S3 (apstrakcija spremna, ne aktivirana), Docker.

---

*Kraj arhitektonskog dokumenta. Sve odluke iz PRD §2 su zaključane; otvorena pitanja (email provider, mapa) razrešena sa klijentom: Mailgun + Leaflet/OSM.*
