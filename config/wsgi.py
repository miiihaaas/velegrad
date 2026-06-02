"""WSGI config for the VELEGRAD project (Story 1.1)."""
import os

from django.core.wsgi import get_wsgi_application

# Production entrypoint defaults SAFE: ako prod systemd unit zaboravi da izveze
# DJANGO_SETTINGS_MODULE, aplikacija se diže sa prod podešavanjima (DEBUG=False,
# SECURE_* hardening) umesto fail-open dev podešavanja.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_wsgi_application()
