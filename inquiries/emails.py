"""Inquiry email pipeline (Story 5.2).

Dva email toka koja se hook-uju unutar ``create_inquiry`` (posle ``inquiry.save()``):

  * :func:`notify_agent` — notifikacija agentu (``SiteSettings.email_inquiries``,
    fallback ``email_primary``; preskoči ako su oba prazna). Sadrži sve podatke
    upita + APSOLUTAN admin link (``reverse("admin:inquiries_inquiry_change")`` +
    ``request.build_absolute_uri``).
  * :func:`send_auto_reply` — brendiran auto-reply kupcu (``inquiry.email``).

Orkestrator :func:`send_inquiry_notifications` poziva oba toka, SVAKI u svom
``try/except`` (per-flow non-fatal): pad jednog NE potiskuje drugi, a celina je
non-fatal po request-u (mail greška ne sme da 500-uje form submit).
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from core.models import SiteSettings

logger = logging.getLogger(__name__)


def notify_agent(inquiry, *, request=None):
    """Pošalji agentsku notifikaciju o novom upitu (tok 1).

    Primalac je ``SiteSettings.email_inquiries`` (fallback ``email_primary``).
    Ako su oba prazna, slanje se preskače (warning + return; bez izuzetka).
    """
    site = SiteSettings.load()
    recipient = site.email_inquiries or site.email_primary
    if not recipient:
        logger.warning(
            "notify_agent preskočen: ni email_inquiries ni email_primary nisu "
            "postavljeni u SiteSettings (upit %s neće biti notifikovan).",
            inquiry.pk,
        )
        return

    # Admin link (LOCKED robustan pristup) — reverse daje putanju sa segmentom
    # 'inquiries/inquiry/' i ispravnim ADMIN_URL prefiksom; build_absolute_uri
    # ga čini apsolutnim kad je request prosleđen.
    path = reverse("admin:inquiries_inquiry_change", args=[inquiry.pk])
    admin_url = request.build_absolute_uri(path) if request is not None else path

    ctx = {
        "inquiry": inquiry,
        "name": inquiry.name,
        "email": inquiry.email,
        "phone": inquiry.phone,
        "inquiry_type_display": inquiry.get_inquiry_type_display(),
        "message": inquiry.message,
        "property_type_wanted": inquiry.property_type_wanted,
        "budget_range": inquiry.budget_range,
        "property": inquiry.property,
        "admin_url": admin_url,
    }

    # Subject se gradi ISKLJUČIVO iz fiksnog/poverljivog teksta — get_inquiry_type_display()
    # dolazi iz fiksnih model choices (bez newline-a). User-kontrolisani inquiry.name se NE
    # stavlja u subject (header injection / BadHeaderError → tihi gubitak notifikacije);
    # ime ostaje u BODY-ju gde je auto-escape-ovano.
    subject = f"Nov upit — {inquiry.get_inquiry_type_display()} (Velegrad Estate)"
    text = render_to_string("email/agent_notification.txt", ctx)
    html = render_to_string("email/agent_notification.html", ctx)

    msg = EmailMultiAlternatives(
        subject, text, settings.DEFAULT_FROM_EMAIL, [recipient]
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


def send_auto_reply(inquiry):
    """Pošalji brendiran auto-reply kupcu (tok 2) na ``inquiry.email``."""
    ctx = {
        "inquiry": inquiry,
        "name": inquiry.name,
    }

    subject = "Hvala na Vašem upitu — Velegrad Estate"
    text = render_to_string("email/auto_reply.txt", ctx)
    html = render_to_string("email/auto_reply.html", ctx)

    msg = EmailMultiAlternatives(
        subject, text, settings.DEFAULT_FROM_EMAIL, [inquiry.email]
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


def send_inquiry_notifications(inquiry, *, request=None):
    """Orkestrator — pozovi oba toka, SVAKI u sopstvenom ``try/except``.

    Per-flow non-fatal (interface contract §1.3): pad jednog toka ne potiskuje
    drugi; nijedan izuzetak se NE re-raise-uje (celina non-fatal po request-u).
    """
    try:
        notify_agent(inquiry, request=request)
    except Exception:  # noqa: BLE001 — per-flow non-fatal (LOCKED)
        logger.exception(
            "notify_agent pao za upit %s (notifikacija agentu nije poslata).",
            inquiry.pk,
        )

    try:
        send_auto_reply(inquiry)
    except Exception:  # noqa: BLE001 — per-flow non-fatal (LOCKED)
        logger.exception(
            "send_auto_reply pao za upit %s (auto-reply kupcu nije poslat).",
            inquiry.pk,
        )
