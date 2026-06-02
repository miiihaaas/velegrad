"""Inquiry admin registration (Story 1.3, architecture §2).

MINIMAL Unfold ModelAdmin so the named admin routes exist and the dashboard
quick-action ``reverse("admin:inquiries_inquiry_changelist")`` resolves (AC10).
Django auto-discovers this module because ``inquiries`` is in INSTALLED_APPS.

Rich list_display / filters / forms are out of scope here (Story 1.4).
"""
from django.contrib import admin

from unfold.admin import ModelAdmin

from inquiries.models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(ModelAdmin):
    """Minimal registration so the Inquiry routes resolve (AC10)."""
