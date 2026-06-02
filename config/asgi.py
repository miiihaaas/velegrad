"""ASGI config for the VELEGRAD project (Story 1.1).

Scaffold artifact — not used in the MVP deploy (Gunicorn/WSGI).
"""
import os

from django.core.asgi import get_asgi_application

# Production entrypoint defaults SAFE: ako prod okruženje zaboravi da izveze
# DJANGO_SETTINGS_MODULE, aplikacija se diže sa prod podešavanjima (DEBUG=False,
# SECURE_* hardening) umesto fail-open dev podešavanja.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_asgi_application()
