# Interface / Scaffold Contract — Story 1.1: Inicijalizacija Django projekta i okruženja

> **Purpose.** This document is the concrete contract the test suite
> (`tests/test_project_setup.py`) asserts and the Dev must satisfy in the GREEN
> phase. It translates AC1–AC8 of the story + architecture §0/§2/§3/§4/§7 into
> precise, machine-checkable interfaces. It is authored in the RED phase by the
> Test Architect; the implementation does NOT exist yet, so every test currently
> FAILS/ERRORS (dominant cause: `ModuleNotFoundError: config`).

Author: TEA (Test Architect) · Date: 2026-06-01 · Status: red-phase contract

---

## 1. Directory layout (FLAT at repo root — NOT under `apps/`)

```
VELEGRAD/                          # repo root = C:\Programming\dev-bmad\VELEGRAD
├── config/                        # Django project package
│   ├── __init__.py
│   ├── settings/                  # settings PACKAGE (not a flat settings.py)
│   │   ├── __init__.py            # REQUIRED — without it config.settings is not a package
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py                    # scaffold artifact, not used in MVP deploy
├── core/        __init__.py  apps.py        # Django app, no models in 1.1
├── properties/  __init__.py  apps.py
├── inquiries/   __init__.py  apps.py
├── pages/       __init__.py  apps.py
├── templates/                     # directory
├── static/                        # directory
├── locale/                        # directory
├── media/                         # directory (gitignored contents)
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── manage.py
├── .env                           # gitignored — never committed
├── .env.example                   # committed template
└── .gitignore
```

## 2. Settings modules

| Module | Requirement |
| :-- | :-- |
| `config.settings.base` | Imports cleanly. Holds shared config: `INSTALLED_APPS`, `MIDDLEWARE`, `TEMPLATES`, `DATABASES`, STATIC/MEDIA, i18n, `AUTH_PASSWORD_VALIDATORS`. Initializes `environ.Env()` and calls `env.read_env(...)`. `SECRET_KEY` read from env (no hardcoded literal). |
| `config.settings.dev` | `from .base import *`; `DEBUG = True`; local `ALLOWED_HOSTS`. Default `DJANGO_SETTINGS_MODULE` locally. |
| `config.settings.prod` | `from .base import *`; `DEBUG = False`; `ALLOWED_HOSTS` from env; full `SECURE_*` baseline. |

## 3. INSTALLED_APPS (required set)

Contrib (all six, so `migrate` succeeds):
`django.contrib.admin`, `django.contrib.auth`, `django.contrib.contenttypes`,
`django.contrib.sessions`, `django.contrib.messages`, `django.contrib.staticfiles`.

Custom apps (4): `core`, `properties`, `inquiries`, `pages` (accepted either as
bare label `core` or dotted `core` / `core.apps.CoreConfig` — the test matches the
app label, so any registration form that yields these labels passes).

## 4. MIDDLEWARE (required entries)

Must include at minimum:
- `django.middleware.security.SecurityMiddleware`
- `django.contrib.sessions.middleware.SessionMiddleware`
- `django.middleware.common.CommonMiddleware`
- **`django.middleware.csrf.CsrfViewMiddleware`**  ← asserted explicitly (AC8 CSRF baseline)
- `django.contrib.auth.middleware.AuthenticationMiddleware`
- `django.contrib.messages.middleware.MessageMiddleware`
- `django.middleware.clickjacking.XFrameOptionsMiddleware`

## 5. ADMIN_URL contract (AC8) — TWO distinct facts

- Admin is mounted in `config/urls.py` at the path from the `ADMIN_URL` env var,
  normalized for leading/trailing slashes, e.g.
  `path(f"{env('ADMIN_URL', default='velegrad-cms/').strip('/')}/", admin.site.urls)`.
- **(a)** Requesting `/admin/` MUST NOT resolve to the admin (Django returns 404 /
  `Resolver404`) — admin is NOT served on the default path.
- **(b)** Requesting the configured `ADMIN_URL` path MUST resolve to `admin.site.urls`.
- The default value of `ADMIN_URL` MUST NOT be `admin/` (or `/admin/`, `admin`).

## 6. Environment variables (`.env.example` must list all)

`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `ADMIN_URL`,
`STORAGE_BACKEND`, `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`,
`DEFAULT_FROM_EMAIL`, `GOOGLE_ANALYTICS_ID`.

- `SECRET_KEY` is read from env via `environ`; NO hardcoded key literal in `base.py`.
- `base.py` source contains a `read_env` call (otherwise local `.env` is ignored).

## 7. DATABASES (AC6)

`DATABASES['default']` is built from `DATABASE_URL` via `env.db()` / `environ`.
`ENGINE` resolves to `django.db.backends.postgresql`. No split HOST/PORT/USER/PASS
literals in code. A single live-DB smoke test (`test_database_connection_smoke`)
self-configures Django and opens its OWN connection inside a `try/except`, so it is
SKIPPED (never failed/errored) when no Postgres is reachable. It is deliberately
**NOT** marked `@pytest.mark.django_db`: pytest-django is installed in this venv, and
that marker would hand DB setup to pytest-django's `db` fixture, which CREATES a test
database BEFORE the test body runs — with no reachable Postgres that fixture ERRORS
(and hangs on the connect timeout) instead of skipping. Correspondingly, `pytest.ini`
must NOT set `DJANGO_SETTINGS_MODULE` (that would activate pytest-django and block the
unmarked self-managed connection). See the Test-harness notes below.

## 8. requirements/ layout (AC1, AC5)

- `base.txt` — runtime packages (arch §4): `Django>=5.2,<5.3` (valid pip pin — NOT
  `Django==5.2.*`), `psycopg[binary]`, `django-environ`, `django-unfold`,
  `django-admin-sortable2`, `django-tinymce`, `Pillow`, `django-imagekit`,
  `django-storages`, `django-anymail[mailgun]`, `django-ratelimit`, `whitenoise`.
  `boto3` present as a COMMENTED line (deferred S3 dep). `gunicorn` NOT here.
- `dev.txt` — starts with `-r base.txt`, adds dev tooling.
- `prod.txt` — starts with `-r base.txt`, adds **`gunicorn`** (prod-only).

## 9. .gitignore (AC7)

Must match/exclude: `.env`, `__pycache__/`, `*.pyc`, `media/`, `staticfiles/`,
a local venv (`.venv`/`venv`), IDE artifacts (`.idea/`, `.vscode/`).
`.env` is NOT tracked; `.env.example` IS present in the repo.

## 10. prod SECURE_* baseline (AC3)

`SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`,
`CSRF_COOKIE_SECURE = True`, `SECURE_HSTS_SECONDS > 0`,
`SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, `SECURE_CONTENT_TYPE_NOSNIFF = True`.

---

## Test-harness notes (TEA-owned, shared TDD infra)

- venv at `C:\Programming\dev-bmad\VELEGRAD\.venv` (Python 3.13.0 — see env note; 3.12 launcher unavailable on this host, Django 5.2 supports 3.13).
- `pytest.ini` at repo root: `python_files = test_*.py`, `testpaths = tests`. It deliberately does **not** set `DJANGO_SETTINGS_MODULE` (pytest-django would otherwise abort the whole session in the RED phase, and in GREEN would block the self-managed live-DB smoke test). Each test pins `config.settings.dev` itself via `_configured_django`.
- `pytest-django` is installed in the venv but is intentionally left dormant (no `DJANGO_SETTINGS_MODULE` in `pytest.ini`). No test uses its `db` fixture.
- Test file: `tests/test_project_setup.py`; package marker `tests/__init__.py`.
- Run: `.venv\Scripts\python.exe -m pytest tests/ -v` from repo root.
