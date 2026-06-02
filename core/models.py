"""Core app models (Story 1.2).

Holds the site-wide singleton ``SiteSettings`` (projektni zadatak §5.2).
"""
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import get_language

from tinymce.models import HTMLField

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]


class LocalizedMixin(models.Model):
    """Abstract mixin providing the ``localized(base)`` language helper.

    Shared by every dual-language model (``SiteSettings``, ``Property``,
    ``PropertyFeature``, ``Page``). ``abstract = True`` means this adds NO DB
    table and NO migration of its own.
    """

    class Meta:
        abstract = True

    def localized(self, base):
        """Return the active-language value for ``base`` with ``_sr`` fallback.

        Robust against ``get_language()`` returning ``None`` (i18n inactive),
        unsupported languages, and empty target values.
        """
        lang = (get_language() or "sr")[:2]
        return getattr(self, f"{base}_{lang}", "") or getattr(self, f"{base}_sr", "")


class SiteSettings(LocalizedMixin, models.Model):
    """Singleton holding global site configuration (§5.2 "Model: SiteSettings").

    Exactly one row is ever stored: ``save()`` pins ``pk=1`` and ``delete()`` is
    a no-op, so ``SiteSettings.objects.count() <= 1`` always holds. Use
    :meth:`load` to fetch (or lazily create) the canonical instance.
    """

    # Kontakt
    phone_primary = models.CharField(max_length=30, blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    email_primary = models.EmailField(blank=True)
    email_inquiries = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Osnivač
    founder_name = models.CharField(max_length=150, blank=True)
    founder_title_sr = models.CharField(max_length=150, blank=True)
    founder_title_en = models.CharField(max_length=150, blank=True)
    founder_photo = models.ImageField(
        upload_to="site/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )
    founder_bio_sr = HTMLField(blank=True)
    founder_bio_en = HTMLField(blank=True)

    # Hero / homepage
    hero_headline_sr = models.CharField(max_length=200, blank=True)
    hero_headline_en = models.CharField(max_length=200, blank=True)
    hero_cta_text_sr = models.CharField(max_length=80, blank=True)
    hero_cta_text_en = models.CharField(max_length=80, blank=True)
    hero_image = models.ImageField(
        upload_to="site/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )
    hero_video_url = models.URLField(blank=True)

    # Analitika
    google_analytics_id = models.CharField(max_length=50, blank=True)
    facebook_pixel_id = models.CharField(max_length=50, blank=True)

    # SEO
    seo_default_title = models.CharField(max_length=70, blank=True)
    seo_default_description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Podešavanja sajta"
        verbose_name_plural = "Podešavanja sajta"

    def __str__(self):
        return "Podešavanja sajta"

    def save(self, *args, **kwargs):
        """Pin the primary key so only one row can ever exist.

        ``objects.create()`` calls ``save(force_insert=True)``; for the
        singleton we must instead upsert the pinned ``pk=1`` row, so any
        force-insert/force-update hints are dropped.
        """
        self.pk = 1
        kwargs.pop("force_insert", None)
        kwargs.pop("force_update", None)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Block deletion of the singleton row.

        Returns the standard Django ``(count, {})`` tuple shape (zero rows
        deleted) instead of ``None`` so callers that unpack the result do not
        break.
        """
        return (0, {})

    @classmethod
    def load(cls):
        """Return the single ``SiteSettings`` instance, creating it if needed."""
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj
