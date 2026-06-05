"""Pages app models (Story 1.2).

Defines ``Page`` for static CMS content (§5.2 "Model: Page").
"""
from django.db import models

from tinymce.models import HTMLField

from core.models import LocalizedMixin


class Page(LocalizedMixin, models.Model):
    """A bilingual static content page (§5.2)."""

    slug = models.CharField("Slug (URL)", max_length=100, unique=True)
    title_sr = models.CharField("Naslov (SR)", max_length=200)
    title_en = models.CharField("Naslov (EN)", max_length=200, blank=True)
    content_sr = HTMLField("Sadržaj (SR)")
    content_en = HTMLField("Sadržaj (EN)", blank=True)
    meta_title = models.CharField("Meta naslov (SEO)", max_length=70, blank=True)
    meta_description = models.TextField("Meta opis (SEO)", blank=True)
    is_active = models.BooleanField("Aktivna", default=True)

    class Meta:
        verbose_name = "Stranica"
        verbose_name_plural = "Stranice"

    def __str__(self):
        return self.slug
