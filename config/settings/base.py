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
    # django-anymail (Story 5.2) — prod Mailgun backend. Bezopasno u dev/test
    # (console/locmem backend ga ignorišu); dokumentovan django-anymail setup.
    "anymail",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # SEO (Story 6.2) — django.contrib.sitemaps generiše /sitemap.xml; zahteva
    # django.contrib.sites (Site.objects.get_current() za apsolutne URL-ove).
    # Oba su UGRAĐENA u Django (bez novog paketa); SITE_ID=1 ih pinuje na default
    # django_site red (Django ugrađena migracija kreira tabelu — NE projektna).
    "django.contrib.sites",
    "django.contrib.sitemaps",
    # django-imagekit (Story 6.3) — keširani WebP + responsive srcset spec-ovi za
    # media slike (app label "imagekit"; paket django-imagekit već u base.txt od
    # Story 1.1). ImageSpecField je non-DB descriptor → BEZ migracije.
    "imagekit",
    # Custom apps
    "core",
    "properties",
    "inquiries",
    "pages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # LocaleMiddleware (Story 6.1) — čita aktivni jezik iz URL prefiksa/sesije/
    # cookie-ja. Django ZAHTEVA da bude STROGO posle SessionMiddleware i STROGO
    # pre CommonMiddleware (CommonMiddleware radi APPEND_SLASH redirekciju koja
    # mora videti već razrešen jezik). i18n_patterns(prefix_default_language=False)
    # u config/urls.py mu daje /en/ prefiks; SR (default) ostaje bez prefiksa.
    "django.middleware.locale.LocaleMiddleware",
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
                # i18n context processor (Story 6.1) — izlaže {{ LANGUAGE_CODE }}
                # (aktivni jezik: "en" pod /en/, "sr" pod SR default) template-ima
                # za <html lang="{{ LANGUAGE_CODE }}">.
                "django.template.context_processors.i18n",
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
# LANGUAGE_CODE MORA biti članica LANGUAGES da bi SR bio istinski no-prefix jezik
# (Story 6.1 bug fix M1). Django izostavlja URL prefiks SAMO kada
# get_language() == LANGUAGE_CODE. Sa "sr-latn" (koje NIJE u LANGUAGES) Locale-
# Middleware za neprefiksiran SR zahtev aktivira "sr", a translate_url('sr') daje
# get_language()=="sr" != "sr-latn" -> Django pogrešno DODAJE /sr/ prefiks. Postavlja-
# njem na "sr" (članica LANGUAGES) SR ostaje bez prefiksa i switcher SR link je tačan.
# localized() koristi get_language()[:2] pa "sr" radi identično; "sr" vs "sr-latn"
# razlika u formatiranju datuma/brojeva je zanemarljiva za ovaj sajt.
# django.contrib.sites SITE_ID (Story 6.2) — sitemap framework ga zahteva za
# apsolutne URL-ove preko Site.objects.get_current(). Default django_site red
# (example.com) je OK za dev/test; prod (Story 6.4) postavlja Site.domain.
SITE_ID = 1

LANGUAGE_CODE = "sr"
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

# Vodeća kosa crta je OBAVEZNA (Story 6.3): django-imagekit renderuje varijanta
# `.url`-ove en masse u <picture>/srcset; sa relativnim "media/" srcset URL-ovi ne
# bi počinjali sa "/" (browser bi ih razrešio relativno na tekuću putanju). "/media/".
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------------------------------- #
# Storage — storage-agnostic backend izbor (Story 6.3, arhitektura §1.4)        #
# --------------------------------------------------------------------------- #
# STORAGES["default"] backend bira `core.storages.default_storage_backend` prema
# STORAGE_BACKEND env-u (l.23, default "local"): "local" → FileSystemStorage,
# "s3" → django-storages S3Storage. django-imagekit WebP varijante prolaze kroz
# isti `default_storage` (IMAGEKIT_DEFAULT_FILE_STORAGE nije postavljen → "default"),
# pa originali I varijante automatski idu na S3 kad Story 6.4 postavi STORAGE_BACKEND=s3
# (+ boto3 + AWS_* — ODLOŽENO; 6.3 garantuje samo storage-agnostic PUT).
# `staticfiles` ostaje Django default FS storage (static NIJE media → ne ide na S3;
# whitenoise/manifest serviranje je Story 6.4 deploy briga, ne 6.3).
from core.storages import default_storage_backend  # noqa: E402

STORAGES = {
    "default": {
        "BACKEND": default_storage_backend(env("STORAGE_BACKEND")),
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# --------------------------------------------------------------------------- #
# django-imagekit — WebP + responsive srcset varijante (Story 6.3, NFR-1)       #
# --------------------------------------------------------------------------- #
# OBAVEZAN-ZA-ISPRAVNOST (empirijski potvrđeno, django-imagekit 6.1.0): default
# strategija JustInTime pri `.url` pristupu OTVARA izvorni fajl → FileNotFoundError/
# HTTP 500 na byteless seed-u/dev-u. Optimistic čini `.url` ČISTOM string operacijom
# (source.name + spec hash): bez I/O, bez Celery, bez kreiranja fajla; stvarno
# generisanje se QUEUE-uje SAMO na save-signal izvora. Zato je `.url`-renderovanje u
# srcset I/O-free i Celery-free. IMAGEKIT_DEFAULT_FILE_STORAGE se NE postavlja →
# imagekit koristi STORAGES["default"] (storage-agnostic, S3-ready).
IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY = "imagekit.cachefiles.strategies.Optimistic"

# Cachefile backend: NIJE postavljen u base (produkcija) — imagekit koristi svoj
# default `Simple` backend, koji SINHRONO generiše varijantu na save-signal izvora
# (Optimistic-ov `on_source_saved` → `generate()` → Simple piše WebP cachefile u
# `default_storage`). U produkciji admin upload ima REALNE bajtove, pa Simple
# uspešno generiše WebP cachefile (arh §1.4) — `.url` ostaje string-safe pod
# Optimistic. (BUG fix Story 6.3: prethodno je ovde bio
# `core.imagekit_backends.DeferredCacheFileBackend` (no-op schedule), pa NIJEDAN
# put nikad nije pisao WebP cachefile → <source srcset> je 404-ovao u produkciji i
# browser je tiho padao nazad na original JPEG/PNG — NFR-1 WebP optimizacija je bila
# funkcionalno INERTNA.) No-op DeferredCacheFileBackend ostaje SAMO za testove
# (config/settings/test.py ga aktivira) gde byteless string-path seed-ovi inače
# dižu FileNotFoundError na .save(). Stvarna WebP konverzija je sada produkciono
# sinhrona; NE uvodi Celery.

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------- #
# Email (Story 5.2)                                                            #
# --------------------------------------------------------------------------- #
# Pošiljalac za oba toka (agentska notifikacija + auto-reply kupcu). Čita se iz
# env-a; base NE postavlja EMAIL_BACKEND — svako okruženje bira svoj (dev=console,
# test=locmem, prod=anymail Mailgun). Override Django placeholdera
# 'webmaster@localhost' brend pošiljaocem.
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="Velegrad Estate <noreply@velegradestate.rs>",
)

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
