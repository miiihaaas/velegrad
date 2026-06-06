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
# Shared cache — django-redis (Story 6.4 AC6a)                                 #
# --------------------------------------------------------------------------- #
# base.py drži LocMemCache (po-procesu) — OK za dev/test (jedan proces). U prod-u
# Gunicorn vrti VIŠE worker-a, pa po-procesni cache cepa django-ratelimit brojač
# (svaki worker svoj limit → curenje limita). Override-ujemo `default` na DELJENI
# Redis backend vođen env-om (CACHE_URL, alias REDIS_URL). Backend je STRING dotted
# path → Django ga lenjo razrešava, pa import prod.py NE zahteva instaliran
# django_redis (test suite na SQLite-u ostaje zelen bez Redis-a).
# Lokaciju cache-a razrešavamo eksplicitno, jednim lookup-om po env-u (bez ugnežđenog
# eager env() u default-u — django-environ bi unutrašnji env() izvršio i kad je spoljni
# postavljen). Redosled: CACHE_URL ima prednost; ako nije postavljen, koristi se REDIS_URL;
# ako ni jedan nije postavljen, pada na lokalni Redis default (dev/staging na istom hostu).
CACHE_LOCATION = env("CACHE_URL", default=None) or env(  # noqa: F405
    "REDIS_URL", default="redis://127.0.0.1:6379/1"
)  # noqa: F405

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_LOCATION,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Eksplicitno vežemo django-ratelimit za `default` cache alias. Prod override-uje
# `default` na DELJENI Redis (gore), pa je rate-limit brojač konzistentan preko svih
# Gunicorn worker-a. Eksplicitna vrednost štiti od budućeg uvođenja zasebnog cache
# alias-a (npr. odvojen `sessions` cache) — ratelimit ostaje vezan baš za Redis `default`.
RATELIMIT_USE_CACHE = "default"

# --------------------------------------------------------------------------- #
# System checks (Story 6.4 AC6c)                                               #
# --------------------------------------------------------------------------- #
# base.py utišava django_ratelimit.E003/W001 jer LocMemCache nije deljen cache.
# Deljeni Redis cache (gore) obara taj razlog → prod NE sme utišavati te provere.
# Eksplicitno praznimo listu da dev/test utišavanje ne procuri u prod.
SILENCED_SYSTEM_CHECKS = []

# --------------------------------------------------------------------------- #
# Rate-limit key — non-spoofable client IP (Story 6.4 AC6b)                     #
# --------------------------------------------------------------------------- #
# Non-spoofable resolver je core.ratelimit.client_ip_key, a NA NJEGA su DIREKTNO
# vezani @ratelimit dekoratori u pages/views.py i properties/views.py preko
# key="core.ratelimit.client_ip_key" (django-ratelimit 4.x import_string-uje dotted
# putanju i poziva je kao keyfn(group, request)). NEMA `RATELIMIT_KEY` setting-a —
# django-ratelimit 4.x ga NE čita (potvrđeno u django_ratelimit/core.py), pa bi to
# bila mrtva (lažno-umirujuća) konfiguracija.
#
# IPWARE_TRUSTED_PROXY_LIST je sekundarni put unutar resolver-a (primarni je
# Nginx-ov X-Real-IP). Default je localhost Nginx (deploy/nginx.conf proxy-ja sa
# istog hosta).
IPWARE_TRUSTED_PROXY_LIST = env.list("IPWARE_TRUSTED_PROXY_LIST", default=["127.0.0.1"])  # noqa: F405

# --------------------------------------------------------------------------- #
# Email (Story 5.2 / deploy) — SMTP preko Loopia mejl hostinga                  #
# --------------------------------------------------------------------------- #
# Odluka (docs/deploy-handoff.md, 2026-06-05): NE Mailgun. Domen velegradbg.rs je
# na Loopia hostingu čiji SPF (v=spf1 include:spf.loopia.se -all) VEĆ pokriva slanje
# preko Loopia SMTP-a → dobra isporuka bez ikakve DNS izmene.
#
# Svi kredencijali ISKLJUČIVO iz env-a (NFR-5) — NIKAD hardkodovani. EMAIL_HOST /
# EMAIL_HOST_USER / EMAIL_HOST_PASSWORD su FAIL-FAST (bez default-a): django-environ
# diže ImproperlyConfigured pri učitavanju settings-a ako nisu postavljeni (ispravno
# za prod — nepodešen mailer pada odmah na startu, ne tek na prvom SMTP auth fail-u).
EMAIL_BACKEND = env(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST")  # npr. mailcluster.loopia.se  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER")  # ceo mejl, npr. noreply@velegradbg.rs  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")  # lozinka iz Loopia panela  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # 587 STARTTLS (preporuka)  # noqa: F405
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)  # 587 STARTTLS  # noqa: F405
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)  # 465 SSL (alternativa TLS-u)  # noqa: F405

# Send-timeout (~10s) — spor SMTP NE sme zauvek da blokira request thread. Django
# SMTP backend prosleđuje ovo kao socket timeout; sinhrono slanje (async broker je
# VAN MVP obima). Zadržan kontraktni 10s iz Story 6.4 AC4.
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)  # noqa: F405
