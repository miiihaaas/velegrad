"""
Base settings shared across all environments (Story 1.1).

Configuration is read from the environment via django-environ. A local `.env`
file (gitignored) is loaded for development; in production the same variables
are provided as real system environment variables.
"""
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# BASE_DIR points at the repo root (flat layout): base.py -> settings -> config -> ROOT
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --------------------------------------------------------------------------- #
# Environment (django-environ)                                                 #
# --------------------------------------------------------------------------- #
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    ADMIN_URL=(str, "velegrad-cms/"),
    STORAGE_BACKEND=(str, "local"),
)

# environ.Env() alone does NOT load the .env file — it only reads existing
# system environment variables. read_env() loads the local .env so dev works.
env.read_env(BASE_DIR / ".env")

# SECRET_KEY is read from the environment — never hardcoded (NFR-5).
SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Admin se montira na ne-podrazumevanoj putanji (NFR-5 / AC8). Ovo je JEDINI
# izvor istine za ADMIN_URL — config/urls.py i testovi ga čitaju odavde.
# .strip("/") čini montiranje robusnim na vodeće/prateće kose crte.
ADMIN_URL = env("ADMIN_URL", default="velegrad-cms/").strip("/")

# Foot-gun guard: an empty/"/" ADMIN_URL normalizes to "" and would mount the
# admin at root "/", silently exposing it (defeats NFR-5). Fail loudly instead.
if not ADMIN_URL:
    raise ImproperlyConfigured(
        "ADMIN_URL normalized to an empty string — the admin would mount at root "
        "'/'. Set ADMIN_URL to a non-empty, non-default path (e.g. 'velegrad-cms/')."
    )

# --------------------------------------------------------------------------- #
# Applications                                                                 #
# --------------------------------------------------------------------------- #
INSTALLED_APPS = [
    # django-unfold MUST precede django.contrib.admin so it can override the
    # admin templates / admin site (Story 1.3 AC1). Only the core "unfold" app is
    # needed: TinyMCE is wired directly via formfield_overrides (1.4), so no
    # unfold.contrib.* sub-app (e.g. unfold.contrib.forms' WysiwygWidget) is used.
    "unfold",
    "adminsortable2",
    "tinymce",
    # django-ratelimit 4.x system checks zahtevaju ga u INSTALLED_APPS da
    # `manage.py check` prođe (Story 4.2 NFR-5 — ContactView POST rate-limit).
    "django_ratelimit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Custom apps
    "core",
    "properties",
    "inquiries",
    "pages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --------------------------------------------------------------------------- #
# Database — PostgreSQL via DATABASE_URL (AC6)                                  #
# --------------------------------------------------------------------------- #
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# --------------------------------------------------------------------------- #
# Cache — `default` alias (Story 4.2 — django-ratelimit backend)               #
# --------------------------------------------------------------------------- #
# django-ratelimit drži brojače u `default` cache alias-u. LocMemCache je
# po-procesu (ne deljen među worker-ima), pa django-ratelimit 4.x diže
# E003/W001 ("not a shared cache"). Za single-tenant dev/test deployment
# (jedan proces, mali saobraćaj — MVP odluka) LocMemCache je prihvatljiv i
# deterministicki za rate-limit, pa eksplicitno utišavamo te dve provere da
# `manage.py check` prođe. (Prod sa više worker-a bi prešao na Redis/Memcached.)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# MVP (jedno-procesni) odluka. Produkciona granica je TRACKED u Story 6.4 AC:
# prelazak na deljeni cache (Redis/Memcached) + čitanje stvarnog klijentskog IP-a
# iza Nginx-a (X-Forwarded-For). Prelazak na deljeni cache obara ovo utišavanje.
SILENCED_SYSTEM_CHECKS = [
    "django_ratelimit.E003",
    "django_ratelimit.W001",
]

# --------------------------------------------------------------------------- #
# Password validation                                                          #
# --------------------------------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# --------------------------------------------------------------------------- #
# Internationalization                                                         #
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = "sr-latn"
TIME_ZONE = "Europe/Belgrade"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("sr", "Srpski"),
    ("en", "English"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# --------------------------------------------------------------------------- #
# Static & media                                                               #
# --------------------------------------------------------------------------- #
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Forward-compat (Django 6.0): forms.URLField will default to assuming 'https'.
# Opting in now silences RemovedInDjango60Warning emitted when admin forms render
# URLField inputs (e.g. virtual_tour_url, hero_video_url) and matches the future
# default behaviour.
FORMS_URLFIELD_ASSUME_HTTPS = True

# --------------------------------------------------------------------------- #
# django-unfold admin theme (Story 1.3)                                        #
# --------------------------------------------------------------------------- #
# Brand colors from the design tokens (zadatak §2.2, tokens.css):
#   Deep Olive  #4A5240  -> RGB-channel "74 82 64"  (primary, brand center)
#   Champagne   #C9A96E  -> RGB-channel "201 169 110" (secondary / accent)
# Modern django-unfold expects COLORS as shade scales (keys 50-950) whose values
# are space-separated RGB-channel strings, NOT hex. Shades are derived around the
# brand tone (lighter -> darker).
UNFOLD = {
    "SITE_TITLE": "Velegrad CMS",
    "SITE_HEADER": "Velegrad CMS",
    "SITE_SUBHEADER": "Administracija",
    # TODO: zameniti tekstualni brending klijentskim SVG logom (IR #4) kad stigne.
    "DASHBOARD_CALLBACK": "core.admin.dashboard_callback",
    "COLORS": {
        # Deep Olive primary scale (#4A5240 = "74 82 64" at the center).
        "primary": {
            "50": "242 243 240",
            "100": "224 227 219",
            "200": "197 202 186",
            "300": "162 170 147",
            "400": "120 130 104",
            "500": "74 82 64",
            "600": "74 82 64",
            "700": "60 67 52",
            "800": "48 53 42",
            "900": "39 43 34",
            "950": "23 26 20",
        },
        # Champagne secondary / accent scale (#C9A96E = "201 169 110").
        "secondary": {
            "50": "250 246 239",
            "100": "244 236 222",
            "200": "233 217 191",
            "300": "221 196 156",
            "400": "201 169 110",
            "500": "201 169 110",
            "600": "181 148 88",
            "700": "151 121 70",
            "800": "122 98 59",
            "900": "100 81 50",
            "950": "54 43 26",
        },
    },
}

# NO-OP belt-and-suspenders guard (verified against django-unfold 0.95.0).
#
# Unfold's ``get_config`` builds the live theme by deep-merging UNFOLD over
# CONFIG_DEFAULTS via ``merge_dicts``, which DEEP-COPIES every leaf — so the
# normalization of COLORS channel strings (e.g. "201 169 110" -> "rgb(201, 169,
# 110)") happens on the merged COPY and never touches ``settings.UNFOLD``. In
# 0.95.0 ``secondary`` is ALSO already a key in CONFIG_DEFAULTS["COLORS"], so the
# setdefault() calls below are redundant on both counts.
#
# We keep this loop purely as a forward-compatibility guard: were a FUTURE Unfold
# to stop deep-copying (returning live references to our scale dicts), pre-seeding
# every custom scale key as an empty dict in the defaults would force the merge to
# recurse and produce a fresh copy, keeping ``settings.UNFOLD`` pristine. It is
# NOT load-bearing today. Best-effort: never fail settings import if Unfold's
# internals change. (Regression covered in tests/test_admin_dashboard.py.)
try:  # pragma: no cover - defensive guard around a 3rd-party internal
    from unfold import settings as _unfold_settings

    for _scale_name in UNFOLD["COLORS"]:
        _unfold_settings.CONFIG_DEFAULTS["COLORS"].setdefault(_scale_name, {})
except Exception:  # pragma: no cover
    pass
