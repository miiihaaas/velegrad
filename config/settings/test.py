"""
Test settings (Story 1.2).

The local/CI environment has NO PostgreSQL available, but the Story 1.2 model
tests need a real database to exercise model behavior (singleton enforcement,
slug auto-generation, @pytest.mark.django_db). This module inherits everything
from ``base`` and overrides ONLY ``DATABASES`` to use an in-memory SQLite
database, so pytest-django can create/destroy a throwaway test DB with zero
external dependencies.

Env decision (Story 1.2 AC10-AC13 / Dev Notes): real PostgreSQL 16 ``migrate``
verification is DEFERRED until a DB is available / pre-deploy. UUIDField and
DecimalField work identically on SQLite and Postgres, so the schema contract is
faithfully exercised here.

This module is wired in via ``DJANGO_SETTINGS_MODULE = config.settings.test``
in pytest.ini, which activates pytest-django for the whole suite.
"""
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Override the Postgres DATABASES from base with an in-memory SQLite DB so the
# test suite is fully self-contained (no Postgres needed in this environment).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Anti-flaky (Story 4.2 AC3): django-ratelimit-ov LocMemCache 'default' alias
# persistira po-procesu kroz testove → bez ovog flag-a bi AC1/AC2 funkcionalni
# testovi (više POST-ova) nasumično padali na rate-limit (5/h po IP-u). Namenski
# rate-limit test ga privremeno UKLJUČUJE preko @override_settings(RATELIMIT_ENABLE=True).
RATELIMIT_ENABLE = False

# Email (Story 5.2) — locmem backend puni django.core.mail.outbox tako da
# email contract testovi (AC1–AC3) mogu da asertuju poslate poruke. NE oslanjati
# se na pytest-django implicitni override; izvor mora eksplicitno da ga deklariše.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Imagekit cachefile backend — SAMO za testove (Story 6.3 BUG fix). Produkcija
# (base.py) NE postavlja ovo → koristi imagekit default `Simple` (sinhrono generiše
# WebP cachefile iz realnih admin-upload bajtova). Test suite, međutim, seed-uje
# slike kao byteless STRING putanje (npr. hero_image="properties/hero/x.jpg" BEZ
# bajtova); Optimistic-ov `on_source_saved` → `generate()` bi sa Simple backend-om
# OTVORIO nepostojeći izvor i digao FileNotFoundError na .save(). No-op
# DeferredCacheFileBackend (BaseAsync sa no-op schedule_generation) razdvaja save od
# generisanja i čini markup-only testove (.url string-op) deterministicki bezbednim.
IMAGEKIT_DEFAULT_CACHEFILE_BACKEND = "core.imagekit_backends.DeferredCacheFileBackend"
