"""Preview authorization helper (Story 1.4 AC3b).

This module isolates the gating logic for previewing not-yet-published
properties. Story 1.4 delivers ONLY the admin side (a ``?preview=1`` link in the
Property change form) plus this reusable, unit-tested helper.

Epic 3's public ``PropertyDetailView`` (``properties/views.py``, route
``/properties/<slug>/``) will import ``can_preview`` and call it to decide
whether to serve a not-active property to the current request.
"""


def can_preview(request, obj) -> bool:
    """Return True iff ``obj`` may be shown to the current request.

    True when the property is publicly visible (``is_active=True``), OR when an
    authenticated staff user explicitly requested a preview (``?preview=1``).
    False otherwise.
    """
    if getattr(obj, "is_active", False):
        return True
    user = getattr(request, "user", None)
    return bool(
        user is not None
        and user.is_authenticated
        and user.is_staff
        and request.GET.get("preview") == "1"
    )
