"""Inquiries app models (Story 1.2).

Defines ``Inquiry`` (§5.2 "Model: Inquiry").
"""
import uuid

from django.db import models


class Inquiry(models.Model):
    """A contact / viewing / private-collection inquiry (§5.2)."""

    INQUIRY_TYPE_CHOICES = [
        ("viewing", "Razgledanje"),
        ("consultation", "Konsultacija"),
        ("private_collection", "Privatna kolekcija"),
        ("general", "Opšte"),
    ]
    STATUS_CHOICES = [
        ("new", "Novo"),
        ("contacted", "Kontaktiran"),
        ("in_progress", "U toku"),
        ("closed", "Zatvoreno"),
    ]
    LANGUAGE_CHOICES = [
        ("sr", "Srpski"),
        ("en", "Engleski"),
        ("fr", "Francuski"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_TYPE_CHOICES)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    message = models.TextField()
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES)
    budget_range = models.CharField(max_length=100, blank=True)
    property_type_wanted = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # GDPR: lični podatak — retention/anonimizacija pre go-live (5.2)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Upit"
        verbose_name_plural = "Upiti"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.inquiry_type}"
