---
story-id: 1-1-inicijalizacija-django-projekta-i-okruzenja
title: Inicijalizacija Django projekta i okruženja
epic: 1
epic-title: "Setup, CMS modeli i brendiran admin (Faza 1)"
module: config
status: ready-for-dev
created: 2026-06-01
author: SM (Scrum Master)
fr-coverage: "temelj (arhitektura §0, §2, §3, §4; NFR-5 deo — env / admin path / CSRF)"
references:
  - _bmad-output/planning-artifacts/architecture.md  # §0 verzije, §2 struktura, §3 settings/env, §4 requirements, §7 Docker
  - _bmad-output/planning-artifacts/epics.md           # Epic 1 / Story 1.1
  - _bmad-output/planning-artifacts/PRD.md
  - _bmad-output/implementation-artifacts/sprint-plan.md
---

# Story 1.1: Inicijalizacija Django projekta i okruženja

## Opis

As a developer,
I want inicijalizovan Django projekat sa PostgreSQL bazom, split settings i env konfiguracijom pod Git-om,
So that postoji čvrst, reproducibilan temelj za sav dalji razvoj.

Ovo je **prva priča celog projekta** i čisti je setup zadatak — bez UI-a i bez domenskih modela (modeli stižu u priči 1.2). Cilj je podići skelet Django projekta tačno prema zaključanoj arhitekturi: `config/` paket sa split settings-ima (`base/dev/prod`), app-ovi `core`, `properties`, `inquiries`, `pages`, `django-environ` + `.env`/`.env.example`, `requirements/` (base/dev/prod), PostgreSQL konekcija preko `DATABASE_URL`, Git inicijalizacija sa `.gitignore` (`.env` isključen), i sigurnosni temelj (env-bazirana `ADMIN_URL` putanja + CSRF baseline iz NFR-5).

Tehničke odluke su **zaključane u arhitekturi i ne preispituju se** — ova priča ih samo materijalizuje (verzije §0, struktura §2, settings/env §3, zavisnosti §4).

## Acceptance Criteria

- [x] **AC1 — Verzije platforme (arh §0).** Projekat se pokreće na **Python 3.12**, **Django 5.2** (LTS) i cilja **PostgreSQL 16**. Verzije su fiksirane u `requirements/base.txt` validnim pip pin-om (`Django>=5.2,<5.3`; ekvivalentno `Django~=5.2.0`). Napomena: `Django==5.2.*` NIJE validan pip pin (pip odbacuje `.*` wildcard u `==`), pa se ne koristi.

- [x] **AC2 — Struktura projekta i app-ova (arh §2).** Postoji `config/` paket (settings paket, `urls.py`, `wsgi.py`, `asgi.py`) i kreirani su Django app-ovi **`core`**, **`properties`**, **`inquiries`**, **`pages`** prema strukturi iz arhitekture §2. App-ovi su registrovani u `INSTALLED_APPS` (`base.py`). Foldери `templates/`, `static/`, `locale/`, `media/`, `requirements/` postoje. (Sami modeli, view-ovi i admin sadržaj NISU u obimu ove priče — to je 1.2+.)

- [x] **AC3 — Split settings + izbor okruženja (arh §3).** Settings je paket `config/settings/` sa `base.py`, `dev.py`, `prod.py`. Izbor okruženja ide preko `DJANGO_SETTINGS_MODULE` (`dev` default lokalno). `dev.py` ima `DEBUG=True` i razvojne pogodnosti; `prod.py` ima `DEBUG=False`, `ALLOWED_HOSTS` iz env-a i `SECURE_*` baseline (HSTS uklj. `SECURE_HSTS_INCLUDE_SUBDOMAINS`, SSL redirect, secure/HttpOnly cookies, `SECURE_CONTENT_TYPE_NOSNIFF`, i ostale standardne Django prod sigurnosne postavke) — bez kredencijala u kodu.

- [x] **AC4 — django-environ + .env strategija (arh §3, NFR-5).** `django-environ` čita konfiguraciju iz `.env` (lokalno) i sistemskih env varijabli (prod). U repou postoji `.env.example` šablon sa svim ključnim varijablama bez stvarnih vrednosti: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `ADMIN_URL`, `STORAGE_BACKEND`, `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`, `DEFAULT_FROM_EMAIL`, `GOOGLE_ANALYTICS_ID`. **Nijedan kredencijal nije hardkodovan u kodu** — `SECRET_KEY` se učitava iz env-a.

- [x] **AC5 — Requirements (arh §4).** Postoje `requirements/base.txt`, `requirements/dev.txt`, `requirements/prod.txt`. `base.txt` sadrži runtime pakete iz arhitekture §4: `Django>=5.2,<5.3`, `psycopg[binary]`, `django-environ`, `django-unfold`, `django-admin-sortable2`, `django-tinymce`, `Pillow`, `django-imagekit`, `django-storages`, `django-anymail[mailgun]`, `django-ratelimit`, `whitenoise`. **`gunicorn` je produkcijski paket** i pripada `prod.txt` (ne `base.txt`); ako se zadrži u `base.txt`, dokumentuj razlog. `dev.txt` i `prod.txt` rade `-r base.txt` i dodaju samo okruženju-specifične alate (npr. dev tooling u `dev.txt`, `gunicorn` u `prod.txt`). **`boto3`** je odložena zavisnost (potrebna tek kad se aktivira S3 storage preko `django-storages`, arh §1.4) — dodaj je kao zakomentarisan red u `base.txt` da se kasnije ne otkrije kao nedostajuća; sam S3 ostaje van obima ove priče. `pip install -r requirements/dev.txt` prolazi bez grešaka.

- [x] **AC6 — PostgreSQL preko DATABASE_URL (arh §3).** Baza je konfigurisana preko `DATABASE_URL` (parsing kroz `django-environ`), bez razbijenih `HOST/PORT/USER/PASS` u kodu. `python manage.py migrate` uspešno povezuje i kreira ugrađene Django tabele na PostgreSQL-u, a `python manage.py runserver` diže prazan projekat bez greške.

- [x] **AC7 — Git inicijalizacija + .gitignore (arh §3, NFR-5).** Repozitorijum je inicijalizovan (`git init`) sa `.gitignore` koji isključuje `.env`, `__pycache__/`, `*.pyc`, `media/`, `staticfiles/`, lokalni venv i IDE artefakte. **`.env` NIJE praćen Git-om**; `.env.example` JESTE.

- [x] **AC8 — Sigurnosni temelj: ADMIN_URL + CSRF baseline (arh §3, NFR-5).** Admin se montira na **nestandardnu putanju iz `ADMIN_URL` env varijable** (default npr. `velegrad-cms/`, koji NE sme biti `admin/`) u `config/urls.py`. Ovaj AC tvrdi DVE stvari koje moraju biti različite putanje: (a) admin NIJE serviran na default `/admin/`, i (b) admin JESTE serviran na konfigurisanoj `ADMIN_URL` putanji. Montaža mora biti otporna na vodeći/prateći slash u developerski zadatoj vrednosti — normalizuj, npr. `path(f"{env('ADMIN_URL', default='velegrad-cms/').strip('/')}/", admin.site.urls)` (Django `path()` zahteva prateći slash). CSRF middleware (`django.middleware.csrf.CsrfViewMiddleware`) je aktivan u `MIDDLEWARE` kao baseline za buduće forme. (Sama Unfold tema/dashboard se konfiguriše u priči 1.3 — ovde je samo env-bazirana montaža admina i CSRF baseline.)

## Tasks / Subtasks

- [x] **T1 — Bootstrap projekta i app-ova** *(AC1, AC2)*
  - [x] Kreiraj virtualno okruženje (Python 3.12) i instaliraj Django 5.2.
  - [x] `django-admin startproject config .` tako da `config/` bude projekat u root-u (`manage.py` u root-u).
  - [x] Konvertuj flat `config/settings.py` (iz `startproject`) u paket `config/settings/`: obavezno kreiraj `config/settings/__init__.py` (čest Django gotcha — bez njega `config.settings` nije Python paket), pa dodaj `base.py`, `dev.py`, `prod.py` i obriši stari flat `settings.py`.
  - [x] Kreiraj app-ove: `core`, `properties`, `inquiries`, `pages` (`startapp`), bez modela.
  - [x] Kreiraj prazne foldere: `templates/`, `static/`, `locale/`, `media/`, `requirements/`.

- [x] **T2 — Split settings konfiguracija** *(AC3)*
  - [x] `base.py`: zajedničko. `INSTALLED_APPS` eksplicitno nabraja pun standardni contrib set (`django.contrib.admin`, `django.contrib.auth`, `django.contrib.contenttypes`, `django.contrib.sessions`, `django.contrib.messages`, `django.contrib.staticfiles`) + 4 custom app-a (`core`, `properties`, `inquiries`, `pages`) — da `migrate` uspe. Dalje: `MIDDLEWARE` sa CSRF, `TEMPLATES`, `STATIC`/`MEDIA` putanje, i18n bazni flag-ovi, `AUTH_PASSWORD_VALIDATORS`.
  - [x] `dev.py`: `from .base import *`, `DEBUG=True`, lokalni `ALLOWED_HOSTS`.
  - [x] `prod.py`: `from .base import *`, `DEBUG=False`, `ALLOWED_HOSTS` iz env-a, `SECURE_*` baseline (`SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`, i ostale standardne Django prod sigurnosne postavke).
  - [x] Podesi `DJANGO_SETTINGS_MODULE` default na `config.settings.dev` u `manage.py`/`wsgi.py`/`asgi.py`.

- [x] **T3 — django-environ i .env strategija** *(AC4)*
  - [x] Dodaj inicijalizaciju `environ.Env()` u `base.py`; `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` čitaj iz env-a.
  - [x] **Obavezno** pozovi `env.read_env(BASE_DIR / '.env')` (ili ekvivalent) u `base.py` — samo `environ.Env()` NE učitava `.env` fajl, već čita postojeće sistemske env varijable; bez `read_env` lokalni `.env` se ignoriše.
  - [x] Kreiraj `.env.example` sa svim ključnim varijablama (vrednosti placeholder/prazne): `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `ADMIN_URL`, `STORAGE_BACKEND`, `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`, `DEFAULT_FROM_EMAIL`, `GOOGLE_ANALYTICS_ID`.
  - [x] Kreiraj lokalni `.env` (van Git-a) sa razvojnim vrednostima za pokretanje.

- [x] **T4 — Requirements fajlovi** *(AC5)*
  - [x] `requirements/base.txt` sa runtime paketima iz arhitekture §4, sa validnim pip pin-om za Django: `Django>=5.2,<5.3` (NE `Django==5.2.*` — pip odbacuje `.*` wildcard u `==`).
  - [x] `gunicorn` stavi u `requirements/prod.txt` (produkcijski paket), ne u `base.txt`.
  - [x] Dodaj `boto3` kao zakomentarisan red u `base.txt` (odložena zavisnost za S3 / `django-storages`, arh §1.4) da bude vidljiva kad se kasnije aktivira.
  - [x] `requirements/dev.txt` (`-r base.txt` + dev alati) i `requirements/prod.txt` (`-r base.txt` + `gunicorn`).
  - [x] Verifikuj `pip install -r requirements/dev.txt` bez grešaka.

- [x] **T5 — PostgreSQL konekcija** *(AC6)*
  - [x] Konfiguriši `DATABASES` preko `env.db("DATABASE_URL")` (`django-environ`).
  - [x] Obezbedi lokalnu PostgreSQL 16 bazu i rolu. Minimalni bootstrap (primer): `createdb velegrad` i u `psql`-u `CREATE ROLE velegrad WITH LOGIN PASSWORD 'velegrad'; GRANT ALL PRIVILEGES ON DATABASE velegrad TO velegrad;`. Ovo je najrealniji put greške za AC6 na čistom checkout-u, pa ga dokumentuj.
  - [x] U `.env` postavi odgovarajući `DATABASE_URL` (primer: `DATABASE_URL=postgres://velegrad:velegrad@localhost:5432/velegrad`). Isti red ide kao placeholder u `.env.example` (T3).
  - [x] Pokreni `python manage.py migrate` (ugrađene tabele) i `python manage.py runserver` — projekat se diže bez greške.

- [x] **T6 — Git i .gitignore** *(AC7)*
  - [x] `git init` u root-u.
  - [x] Kreiraj `.gitignore` (Python/Django): `.env`, `__pycache__/`, `*.pyc`, `media/`, `staticfiles/`, venv folder, `.idea/`, `.vscode/`.
  - [x] Verifikuj da `.env` nije u `git status` (ignorisan), a `.env.example` jeste praćen.
  - [x] Inicijalni commit skeleta.

- [x] **T7 — Env-bazirana ADMIN_URL putanja + CSRF baseline** *(AC8)*
  - [x] U `config/urls.py` montiraj `admin.site.urls` na putanju iz `ADMIN_URL`, sa normalizacijom slash-eva da radi bez obzira na vodeći/prateći slash u zadatoj vrednosti, npr. `path(f"{env('ADMIN_URL', default='velegrad-cms/').strip('/')}/", admin.site.urls)`. Default `ADMIN_URL` ne sme biti `admin/`.
  - [x] Potvrdi da je `CsrfViewMiddleware` prisutan u `MIDDLEWARE` (baseline za buduće forme).
  - [x] Verifikuj: zahtev na default `/admin/` vraća **HTTP 404** (URL nije montiran — ne redirect ni login stranica); zahtev na konfigurisani `ADMIN_URL` vraća admin login ekran.

## Dev Notes

- **Granice obima:** ova priča isporučuje SAMO skelet i okruženje. Modeli, migracije domenskih tabela, Unfold tema/dashboard i bilo koji frontend dolaze u kasnijim pričama (1.2 modeli, 1.3 brendiran admin/dashboard, 1.4 admin funkcionalnost, Epik 2 frontend). `ADMIN_URL` montaža ovde je samo sigurnosni temelj (NFR-5), ne tematizacija.
- **Docker — NIJE u obimu (arh §7).** Iako je inicijalni kontekst orkestratora pominjao Docker/docker-compose (app/db/redis), **arhitektura §7 eksplicitno preporučuje NE koristiti Docker za MVP** (direktan venv + systemd + Nginx; epics.md Story 6.4 AC to potvrđuje: „Docker se ne koristi za MVP"). Arhitektura je izvor istine i ne preispituje se, pa Docker artefakti **nisu deo ove priče**. Opcioni Docker put je dokumentovan i odložen (arh §7) — može se dodati aditivno kasnije bez rewrite-a (settings/env strategija §3 je već kompatibilna). Slično, **Redis nije runtime zavisnost MVP-a** (nije u listi zavisnosti arh §4 i nema Celery u obimu).
- **Verzije (arh §0):** Python 3.12, Django 5.2 LTS, PostgreSQL 16. Node nije potreban (dizajn je gotov custom CSS, bez build pipeline-a).
- **Settings izbor:** `DJANGO_SETTINGS_MODULE=config.settings.dev` lokalno, `config.settings.prod` na VPS-u.
- **Bez kredencijala u kodu:** `SECRET_KEY` i svi tajni podaci isključivo iz env-a (NFR-5, zadatak §5.8).
- **`asgi.py`:** postoji u skeletu (`startproject`), ali se NE koristi u MVP deploy-u (Gunicorn/WSGI). Ostavljen je kao scaffold artefakt.
- **Temelj bez wiring-a (scope napomena):** `whitenoise` u `base.txt` i `STORAGE_BACKEND` u `.env.example` su prisutni kao temelj, ali se NE povezuju u ovoj priči — wiring (static serving / izbor storage backend-a) dolazi u kasnijim pričama.
- **First-run bez `.env`:** ako `.env` nedostaje ili nema `SECRET_KEY`, `django-environ` diže `ImproperlyConfigured` na startu — očekivano ponašanje; popunjen `.env` (iz `.env.example`) je preduslov za `migrate`/`runserver`.

## Definition of Done

- [x] Svi AC (AC1–AC8) zadovoljeni i ručno verifikovani.
- [x] `pip install -r requirements/dev.txt`, `migrate` i `runserver` prolaze bez grešaka na čistom checkout-u sa popunjenim `.env`.
- [x] `.env` ignorisan u Git-u; `.env.example` u repou sa svim ključnim varijablama.
- [x] Admin dostupan samo preko `ADMIN_URL` putanje; `/admin/` ne radi.
- [x] Inicijalni Git commit skeleta napravljen.
