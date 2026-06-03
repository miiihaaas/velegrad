"""Shared pytest fixtures for the VELEGRAD test suite.

Story 6.1 introduced i18n_patterns + LocaleMiddleware. Django's LocaleMiddleware
ACTIVATES the request language (e.g. "en" for a GET /en/...) in thread-local
translation state and does NOT deactivate it on response. Under pytest-django's
function-scoped ``client`` (no Django ``TestCase.setUp`` reset), that active
language LEAKS into the next test — making a module-level ``reverse("home")`` in a
later test return ``/en/`` instead of ``/`` (the SR no-prefix path).

This autouse fixture resets the thread-local translation state after every test,
restoring the deterministic default (LANGUAGE_CODE) so route/reverse assertions are
order-independent. It is test infrastructure only — it changes no production code.
"""
import pytest
from django.utils import translation


@pytest.fixture(autouse=True)
def _reset_active_language():
    """Deactivate any leaked active language after each test."""
    yield
    translation.deactivate()
