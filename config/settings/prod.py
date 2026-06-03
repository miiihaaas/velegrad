"""Production settings (Story 1.1) — SECURE_* baseline per NFR-5."""
from .base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = env("ALLOWED_HOSTS")  # noqa: F405

# --------------------------------------------------------------------------- #
# Security baseline (NFR-5)                                                     #
# --------------------------------------------------------------------------- #
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --------------------------------------------------------------------------- #
# Email (Story 5.2) — django-anymail Mailgun backend                           #
# --------------------------------------------------------------------------- #
# Kredencijali ISKLJUČIVO iz env-a (NFR-5) — NIKAD hardkodovani.
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

ANYMAIL = {
    "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),  # noqa: F405
    "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN"),  # noqa: F405
}
# Contract assert (AC4/NFR-5): prod mora čitati ključ iz env-a — env("MAILGUN_API_KEY").
# Fail-fast: BEZ default="" — django-environ podiže ImproperlyConfigured pri učitavanju
# settings-a ako MAILGUN_API_KEY / MAILGUN_SENDER_DOMAIN nisu postavljeni (ispravno za
# prod: nepodešen mailer pada odmah na startu, ne tek na prvom Mailgun 401 pri slanju).
# NAPOMENA (Story 6.4 — TRACKED): sinhrono slanje preko anymail Mailgun backend-a NEMA
# send-timeout (anymail nema REQUESTS_TIMEOUT). Pri deploy-u (Story 6.4) OBAVEZNO dodati
# send timeout — custom requests session ili prebacivanje slanja u async (Celery) — jer
# spor Mailgun može blokirati request thread bez timeout-a.
