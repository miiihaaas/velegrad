"""Inquiries app forms (Story 3.2).

``InquiryForm`` is the agent-contact mini "viewing" form rendered on the public
Property Detail page. It is the gateway for the FIRST DB write in the project.

Security invariants (LOCKED — see story 3.2 AC6 / interface contract §2):
  * ``Meta.fields`` is EXACTLY ``["name", "email", "phone", "message"]`` — the
    sensitive/internal fields (``inquiry_type``/``property``/``status``/
    ``preferred_language``/``budget_range``/``property_type_wanted``/``notes``/
    ``ip_address``) are NEVER form fields, so a client can never set them via
    POST (mass-assignment / tampering prevention). The view sets them
    server-side after ``form.save(commit=False)``.
  * ``website`` is a NON-model honeypot field (``required=False``) — bots that
    blindly fill every input trip it; the view then silently rejects the submit
    (returns the same success branch so the bot sees "success"). It is NOT a
    ``HiddenInput`` (bots skip ``type=hidden``); it is hidden via CSS (.sr-only)
    + ``aria-hidden``/``tabindex=-1``/``autocomplete=off`` in the template.
  * ``message`` stays REQUIRED (model ``TextField`` without ``blank=True``) — the
    server wins over the design's non-required textarea.
"""
from django import forms

from .models import Inquiry


class InquiryForm(forms.ModelForm):
    """Mini viewing inquiry form (4 user fields + a non-model honeypot)."""

    # Honeypot — NON-model field. required=False so a normal (empty) submit is
    # valid; a filled value flags a bot (handled in the view, NOT here, so the
    # honeypot is never disclosed via a form error).
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"tabindex": "-1", "autocomplete": "off", "aria-hidden": "true"}
        ),
    )

    class Meta:
        model = Inquiry
        # EXACTLY these four — see module docstring (tampering prevention).
        fields = ["name", "email", "phone", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "required": True,
                       "placeholder": "Vaše ime"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-input", "type": "tel", "required": True,
                       "placeholder": "+381 6x xxx xxxx"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "required": True,
                       "placeholder": "vas@email.com"}
            ),
            # message is REQUIRED (model TextField, no blank) — mirror that on the
            # widget so the client and server agree.
            "message": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 4, "required": True,
                       "placeholder": "Zainteresovan/a sam za ovu nekretninu..."}
            ),
        }
