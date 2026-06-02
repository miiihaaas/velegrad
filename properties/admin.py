"""Property admin registration (Story 1.3, architecture §2).

MINIMAL Unfold ModelAdmin so the named admin routes exist and the dashboard
quick-action ``reverse("admin:properties_property_add")`` resolves (AC10).
Django auto-discovers this module because ``properties`` is in INSTALLED_APPS.

Rich list_display / filters / forms are out of scope here (Story 1.4).
"""
from django.contrib import admin

from unfold.admin import ModelAdmin

from properties.models import Property


@admin.register(Property)
class PropertyAdmin(ModelAdmin):
    """Minimal registration so the quick-action routes resolve (AC10).

    Rich changelist/form UX is Story 1.4.
    """
