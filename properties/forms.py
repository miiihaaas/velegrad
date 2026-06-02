"""Properties app forms (Story 3.1).

``PropertyFilterForm`` is the SOLE gate for user-supplied filter input on the
public Signature listing (``/properties/``). Plain Django ``forms.Form`` —
deliberately NO ``django-filter`` (arhitektura §1.2). Every field is
``required=False`` so an empty/partial query string is always valid; the view
applies filters ISKLJUČIVO iz ``form.cleaned_data`` (nikad sirov ``request.GET``
u ORM). Invalid/garbage/negative values make the offending field invalid and are
simply skipped by the view (degradirano renderovanje, 200 — nikad 500).
"""
from django import forms

from .models import Property

# Status select nudi SAMO kurirane statuse (MODEL vrednosti) — sold/rented su
# isključeni iz baznog queryseta pa nemaju smisla kao filter opcije.
_FILTER_STATUS_CHOICES = [
    ("for_sale", "Na prodaju"),
    ("for_rent", "Za izdavanje"),
    ("price_on_request", "Cena na upit"),
]


class PropertyFilterForm(forms.Form):
    """Validates the optional GET filter params for the Signature listing."""

    location = forms.CharField(required=False)
    property_type = forms.ChoiceField(
        required=False,
        choices=[("", "")] + Property.PROPERTY_TYPE_CHOICES,
    )
    price_min = forms.DecimalField(required=False, min_value=0)
    price_max = forms.DecimalField(required=False, min_value=0)
    bedrooms = forms.IntegerField(required=False, min_value=0)
    status = forms.ChoiceField(
        required=False,
        choices=[("", "")] + _FILTER_STATUS_CHOICES,
    )
    keyword = forms.CharField(required=False, max_length=100)

    def clean(self):
        """Neutralise an inverted price range (LOCKED) — do NOT raise.

        If both bounds are present and ``price_min > price_max``, set BOTH to
        ``None`` so the view ignores both price filters and the listing still
        renders 200 (a ``ValidationError`` would make the form invalid).
        """
        cleaned = super().clean()
        price_min = cleaned.get("price_min")
        price_max = cleaned.get("price_max")
        if price_min is not None and price_max is not None and price_min > price_max:
            cleaned["price_min"] = None
            cleaned["price_max"] = None
        return cleaned
