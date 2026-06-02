"""Pages app models (Story 1.2).

Defines ``Page`` for static CMS content (§5.2 "Model: Page").
"""
from django.db import models

from tinymce.models import HTMLField

from core.models import LocalizedMixin


class Page(LocalizedMixin, models.Model):
    """A bilingual static content page (§5.2)."""

    slug = models.CharField(max_length=100, unique=True)
    title_sr = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    content_sr = HTMLField()
    content_en = HTMLField(blank=True)
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Stranica"
        verbose_name_plural = "Stranice"

    def __str__(self):
        return self.slug
