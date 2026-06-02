"""Admin registrations + dashboard callback (Story 1.3).

Scope: the branded "Velegrad CMS" admin SHELL + DASHBOARD only.
  * ``dashboard_callback`` feeds the metric/quick-action/latest-inquiries
    context consumed by ``templates/admin/index.html`` (AC4/AC5/AC9).
  * ``SiteSettings`` is registered as a singleton admin (no add when a row
    exists, no delete, changelist -> change-view redirect) (AC6).

The MINIMAL ``Property`` and ``Inquiry`` ModelAdmins live in their own apps'
admin modules (``properties/admin.py`` / ``inquiries/admin.py``, architecture
§2); this module only READS those models for the dashboard metrics below.

Rich list_display / filters / forms / fieldsets are out of scope here (1.4).
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from tinymce.models import HTMLField
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin

from core.models import SiteSettings
from inquiries.models import Inquiry
from properties.models import Property


def dashboard_callback(request, context):
    """Inject dashboard metrics, quick-action URLs and latest inquiries.

    Runs on every admin index GET, so it must be DEFENSIVE: it never raises on
    an empty DB. The template override (``admin/index.html``) renders these keys
    into the metric cards, quick-action links and the latest-inquiries table.
    """
    try:
        active_count = Property.objects.filter(is_active=True).count()
        featured_count = Property.objects.filter(is_featured=True).count()
        new_inquiries_count = Inquiry.objects.filter(status="new").count()
        latest_inquiries = list(Inquiry.objects.order_by("-created_at")[:5])
    except Exception:  # pragma: no cover - defensive; never 500 the index
        active_count = 0
        featured_count = 0
        new_inquiries_count = 0
        latest_inquiries = []

    try:
        add_property_url = reverse("admin:properties_property_add")
    except Exception:  # pragma: no cover - defensive
        add_property_url = ""
    try:
        inquiries_url = reverse("admin:inquiries_inquiry_changelist")
    except Exception:  # pragma: no cover - defensive
        inquiries_url = ""

    context.update(
        {
            "velegrad_active_count": active_count,
            "velegrad_new_inquiries_count": new_inquiries_count,
            "velegrad_featured_count": featured_count,
            "velegrad_add_property_url": add_property_url,
            "velegrad_inquiries_url": inquiries_url,
            "velegrad_latest_inquiries": latest_inquiries,
        }
    )
    return context


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    """Singleton admin: edit only, no add (once a row exists), no delete (AC6).

    Story 1.4 EXTENDS this with grouped SR/EN fieldsets covering the full
    settings (FR26/FR27) and TinyMCE on founder_bio_* (AC2). The 1.3 singleton
    rules (no add when a row exists, no delete, changelist->change redirect) are
    NOT touched.
    """

    # TinyMCE WYSIWYG for the founder_bio_* HTMLFields (AC2).
    formfield_overrides = {
        HTMLField: {"widget": TinyMCE},
    }

    fieldsets = (
        (
            "Kontakt",
            {
                "fields": (
                    "phone_primary",
                    "whatsapp_number",
                    "email_primary",
                    "email_inquiries",
                    "address",
                )
            },
        ),
        (
            "Osnivač",
            {
                "fields": (
                    "founder_name",
                    ("founder_title_sr", "founder_title_en"),
                    "founder_photo",
                    "founder_bio_sr",
                    "founder_bio_en",
                )
            },
        ),
        (
            "Hero / homepage",
            {
                "fields": (
                    ("hero_headline_sr", "hero_headline_en"),
                    ("hero_cta_text_sr", "hero_cta_text_en"),
                    "hero_image",
                    "hero_video_url",
                )
            },
        ),
        (
            "Analitika",
            {"fields": ("google_analytics_id", "facebook_pixel_id")},
        ),
        (
            "SEO",
            {"fields": ("seo_default_title", "seo_default_description")},
        ),
    )

    def has_add_permission(self, request):
        # Allowed only on a completely empty DB; blocked once the singleton row
        # exists (SiteSettings.load() auto-creates it).
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Single-edit UX: when the singleton row exists, skip the one-row
        # changelist and redirect straight to its change form.
        obj = SiteSettings.objects.first()
        if obj is not None:
            return redirect(
                reverse("admin:core_sitesettings_change", args=[obj.pk])
            )
        return super().changelist_view(request, extra_context)
