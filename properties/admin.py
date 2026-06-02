"""Property admin (Story 1.4 — full management, FR24/FR27, arch §1.1).

Extends the minimal 1.3 registration into full management UX:
  * a sortable PropertyImage gallery inline (django-admin-sortable2),
  * TinyMCE WYSIWYG on the description_* HTMLFields,
  * a "Dupliraj" admin action (copy fields + M2M features, reset slug, new pk,
    no copied images),
  * an admin-side ``?preview=1`` link for not-active properties,
  * bilingual SR/EN grouped fieldsets covering every editable field.
"""
from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin
from django.contrib import admin
from django.utils.html import format_html

from tinymce.models import HTMLField
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin, TabularInline

from properties.models import Property, PropertyImage


class PropertyImageInline(SortableInlineAdminMixin, TabularInline):
    """Drag&drop sortable gallery inline (AC1, FR24).

    The sortable mixin MUST precede the Unfold inline base in the MRO so the
    reorder JS/CSS (the ``adminsortable2/`` static media) is loaded and the
    Unfold styling is preserved.
    """

    model = PropertyImage
    fields = ["image", "caption", "is_hero", "order"]
    ordering = ["order"]
    extra = 0


@admin.register(Property)
class PropertyAdmin(SortableAdminBase, ModelAdmin):
    """Full Property management admin (AC1, AC2, AC3, AC5)."""

    # TinyMCE WYSIWYG for the HTMLField description_* fields (AC2). The minimal
    # 1.3 admin rendered these as plain Unfold textareas; wiring the TinyMCE
    # widget makes ``class="tinymce"`` appear on the change form.
    formfield_overrides = {
        HTMLField: {"widget": TinyMCE},
    }

    list_display = ["title", "status", "collection_type", "location_city", "is_active"]
    list_filter = ["status", "collection_type", "property_type", "is_active", "is_featured"]
    search_fields = ["title", "location_city", "location_district"]
    inlines = [PropertyImageInline]
    actions = ["duplicate_selected"]
    readonly_fields = ["preview_link"]
    filter_horizontal = ["features"]

    fieldsets = (
        (
            "Osnovno",
            {
                "fields": (
                    "title",
                    ("status", "collection_type", "property_type"),
                    ("is_featured", "is_active"),
                    "preview_link",
                )
            },
        ),
        (
            "Lokacija",
            {
                "fields": (
                    ("location_city", "location_district"),
                    "location_address",
                    "show_address",
                    ("latitude", "longitude"),
                )
            },
        ),
        (
            "Cena i površina",
            {
                "fields": (
                    ("price", "price_on_request"),
                    ("area_sqm", "area_total_sqm"),
                    ("bedrooms", "bathrooms"),
                    ("floor", "total_floors"),
                    ("parking_spaces", "year_built"),
                )
            },
        ),
        (
            "Opis (SR)",
            {"fields": ("description_sr",)},
        ),
        (
            "Opis (EN)",
            {"fields": ("description_en",)},
        ),
        (
            "Opis (FR)",
            {"classes": ("collapse",), "fields": ("description_fr",)},
        ),
        (
            "Karakteristike i mediji",
            {
                "fields": (
                    "features",
                    "hero_image",
                    "floor_plan",
                    "virtual_tour_url",
                )
            },
        ),
        (
            "SEO",
            {"fields": ("meta_title", "meta_description")},
        ),
    )

    @admin.display(description="Pregled pre objave")
    def preview_link(self, obj):
        """Render a ``?preview=1`` preview link in the change form (AC3c).

        The public PropertyDetailView arrives in Epic 3; until then we build a
        predictable placeholder URL ``/properties/<slug>/?preview=1`` (staff-only
        gating is enforced by ``properties.preview.can_preview``). The link is
        shown only for not-active properties (active ones are publicly visible).
        """
        if obj is None or getattr(obj, "is_active", True):
            return "—"
        # TODO (Epic 3): replace with reverse("property_detail", args=[obj.slug])
        # once the public detail route exists.
        slug = obj.slug or ""
        url = f"/properties/{slug}/?preview=1"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Pregled pre objave (?preview=1)</a>',
            url,
        )

    @staticmethod
    @admin.action(description="Dupliraj")
    def duplicate_selected(modeladmin, request, queryset):
        """Duplicate each selected Property (AC3a).

        Defined as a ``staticmethod`` (signature ``(modeladmin, request,
        queryset)``) so the admin-actions calling convention is honored both by
        Django (which calls ``func(self, request, queryset)`` off the class) and
        by the contract tests (which fetch the attribute and call it with the
        same three positional args).

        Copies all scalar fields + M2M ``features``, resets the slug (so
        ``save()`` regenerates a collision-safe one), mints a NEW UUID pk, and
        does NOT copy PropertyImage rows. The original stays untouched. Safe to
        run on an already-duplicated property (no IntegrityError).
        """
        for original in queryset:
            features = list(original.features.all())
            original.pk = None
            original.id = None
            original._state.adding = True
            original.slug = ""
            original.title = f"Kopija — {original.title}"
            original.save()
            if features:
                original.features.set(features)
