"""Development settings (Story 1.1)."""
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", ".localhost"]

# Email (Story 5.2) — u dev-u poruke se ispisuju u konzolu (ne šalju se stvarno).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
