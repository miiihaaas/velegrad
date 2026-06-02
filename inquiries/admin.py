"""Inquiry admin (Story 1.4 — FR25, AC4).

Adds the management UX: useful list columns, status + date filters, inline
status editing on the changelist, and search across name/email/phone.
"""
from django.contrib import admin

from unfold.admin import ModelAdmin

from inquiries.models import Inquiry


class StatusListFilter(admin.SimpleListFilter):
    """Status filter that emits clean ``?status=<value>`` query links (AC4).

    The default choices filter for a field would emit ``status__exact=`` query
    keys; the contract/tests expect a plain ``status=new`` filter URL, so we use
    an explicit ``parameter_name = "status"``.
    """

    title = "Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return Inquiry.STATUS_CHOICES

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(status=value)
        return queryset


@admin.register(Inquiry)
class InquiryAdmin(ModelAdmin):
    """Inquiry list/status workflow (AC4, FR25)."""

    # 'status' deliberately NOT the first column (first column is the change
    # link); required for list_editable (admin.E124).
    list_display = ["name", "status", "inquiry_type", "email", "phone", "created_at"]
    list_editable = ["status"]
    # ONLY the custom StatusListFilter for status: it renders clean
    # ?status=<value> links. The bare "status" string would additionally register
    # Django's ChoicesFieldListFilter (emitting ?status__exact= links), producing a
    # SECOND, duplicate "Status" filter panel in the Unfold sidebar — a UX defect.
    list_filter = [StatusListFilter, ("created_at", admin.DateFieldListFilter)]
    search_fields = ["name", "email", "phone"]
    ordering = ["-created_at"]
