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
