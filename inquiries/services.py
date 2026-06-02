"""Inquiries app service seam (Story 3.2 — code-review refactor).

``create_inquiry`` is the single, reusable write-path for an ``Inquiry`` row.
It is extracted from ``PropertyDetailView.post`` so later stories reuse ONE seam:

  * Story 5.2 hooks the email notification / auto-reply here (NOT here yet).
  * Epic 4/5 contact + private-collection forms reuse this same function.

Security invariants (LOCKED — mirrors story 3.2 AC6):
  * ``inquiry_type``/``property``/``status``/``preferred_language`` are set
    SERVER-SIDE here (never from the bound form / POST) — tampering prevention.
  * ``preferred_language`` is a required CharField with NO DB default; omitting
    it would IntegrityError/ValueError on ``save()`` — so it is always set.
  * ``ip_address`` is captured from the request when provided (anti-abuse for
    5.2). GDPR: it is PII — retention/anonymization is 5.2 scope.
  * NO email send here (deferred to 5.2).
"""
from __future__ import annotations

from .models import Inquiry


def create_inquiry(*, form, property, inquiry_type, request=None) -> Inquiry:
    """Persist an :class:`Inquiry` from a validated ``InquiryForm``.

    The caller MUST have already validated ``form`` (``form.is_valid()``).
    Server-side fields are set here — never trusted from the client POST.

    Args:
        form: a validated ``InquiryForm`` (bound, ``is_valid()`` True).
        property: the ``Property`` the inquiry is about.
        inquiry_type: the server-chosen type (e.g. ``"viewing"``).
        request: optional ``HttpRequest`` — when given, ``ip_address`` is
            captured from ``REMOTE_ADDR`` (anti-abuse, 5.2 retention scope).

    Returns:
        The saved ``Inquiry`` instance.
    """
    inquiry = form.save(commit=False)
    # SERVER-SIDE only (never from POST) — tampering prevention.
    inquiry.inquiry_type = inquiry_type
    inquiry.property = property
    inquiry.status = "new"
    # Required CharField with NO DB default — omitting it would
    # IntegrityError/ValueError on save().
    inquiry.preferred_language = "sr"
    if request is not None:
        # PII (GDPR) — captured for 5.2 anti-abuse; retention/anonymization 5.2.
        inquiry.ip_address = request.META.get("REMOTE_ADDR")
    inquiry.save()
    # NO email send here (5.2).
    return inquiry
