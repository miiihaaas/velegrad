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
from django.utils.translation import gettext_lazy as _

from .models import Inquiry


# LOCKED choices (Story 5.1 T1) — stored value == čitljiva srpska labela
# (NE kratak kod), tako da admin lead-a prikazuje smislen tekst (Inquiry model
# NEMA `choices` na ovim poljima → bez get_..._display()). Prva opcija je prazan
# "" placeholder + required=True → prazan izbor je nevalidan. UI labele kroz
# gettext_lazy (SR za sada; pun jezički switch je Epik 6 — IR #1).
PROPERTY_TYPE_CHOICES = [
    ("", _("Izaberite…")),
    ("Stan", _("Stan")),
    ("Kuća", _("Kuća")),
    ("Penthouse", _("Penthouse")),
    ("Vila", _("Vila")),
    ("Komercijalno", _("Komercijalno")),
    ("Zemljište", _("Zemljište")),
]
BUDGET_CHOICES = [
    ("", _("Izaberite raspon…")),
    ("Do €500.000", _("Do €500.000")),
    ("€500.000 – €1.000.000", _("€500.000 – €1.000.000")),
    ("€1.000.000 – €2.000.000", _("€1.000.000 – €2.000.000")),
    ("€2.000.000 – €5.000.000", _("€2.000.000 – €5.000.000")),
    ("€5.000.000+", _("€5.000.000+")),
]


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


class PrivateCollectionForm(forms.ModelForm):
    """Private Collection intake forma (Story 5.1 — 5 korisničkih polja + honeypot).

    NOVA forma (NE InquiryForm — 3.2/4.2 je reutilizuju nepromenjenu). ModelForm
    nad Inquiry sa TAČNO 5 polja: name/email/phone/property_type_wanted/
    budget_range. `message`/`inquiry_type`/`property`/`status`/`preferred_language`/
    `ip_address` NISU form-polja (server-side ili default → tampering prevention).

    Security invariants (LOCKED — mirror InquiryForm 3.2):
      * honeypot `website` je NON-model CharField(required=False) — view tiho
        odbacuje popunjen submit (NE form greška). NE HiddenInput (botovi preskaču
        type=hidden); skriven CSS-om (.sr-only) + aria-hidden/tabindex=-1 u template-u.
      * property_type_wanted/budget_range su ChoiceField sa LOCKED choices — stored
        value == čitljiva srpska labela; prazan placeholder "" je nevalidan izbor.
    """

    # Honeypot — NON-model field (identičan obrazac kao InquiryForm).
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"tabindex": "-1", "autocomplete": "off", "aria-hidden": "true"}
        ),
    )
    # property_type_wanted/budget_range: model polja su slobodni CharField(100,
    # blank) BEZ choices → choices se definišu NA FORMI (ChoiceField). Stored
    # value == labela (npr. "Stan", "€500.000 – €1.000.000" sa en-dash-om).
    property_type_wanted = forms.ChoiceField(
        choices=PROPERTY_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    budget_range = forms.ChoiceField(
        choices=BUDGET_CHOICES,
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Inquiry
        # EXACTLY these five — message je NAMERNO izostavljen (FR18 lista 5 polja;
        # message ostaje "" default jer nije form-polje).
        fields = ["name", "email", "phone", "property_type_wanted", "budget_range"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "required": True,
                       "placeholder": "Vaše ime i prezime"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-input", "type": "tel", "required": True,
                       "placeholder": "+381 6x xxx xxxx"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "required": True,
                       "placeholder": "vas@email.com"}
            ),
        }
