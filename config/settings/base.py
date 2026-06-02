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
