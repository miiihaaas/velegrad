"""Public frontend views (Story 2.1).

Minimalna home ruta renderuje bazni layout (templates/home.html koji
{% extends "base.html" %}), BEZ sadržaja iz baze (to dolazi u Story 2.2).
custom_404 je eksplicitni handler404 koji renderuje premium 404.html unutar
baznog okvira (site-header/site-footer) sa HTTP statusom 404.
"""
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from inquiries.forms import InquiryForm, PrivateCollectionForm
from inquiries.services import create_inquiry
from properties.models import Property

from .models import Page


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # SiteSettings (hero/founder/kontakt) dolazi ISKLJUČIVO preko
        # core.context_processors.site_settings — NE pozivati load() ponovo ovde.
        # FR4: private/off-market kolekcije NIKADA se ne prikazuju na javnoj
        # Home strani. Home featured preview je Signature kolekcija (Epic 2/3),
        # pa eksplicitno filtriramo collection_type='signature'.
        context["featured_properties"] = Property.objects.filter(
            is_featured=True, is_active=True, collection_type="signature"
        )[:4]
        return context


@method_decorator(
    ratelimit(
        key="core.ratelimit.client_ip_key", rate="5/h", method="POST", block=True
    ),
    name="post",
)
class ContactView(View):
    """Public Contact page + 4-field Inquiry(general) form (Story 4.2).

    GET renders ``InquiryForm()`` (sa Contact-prilagođenim message placeholder-om)
    + ``site_settings`` (već globalno preko core.context_processors.site_settings —
    NE re-load-uje se ovde). POST validira ``InquiryForm(request.POST)`` i verno
    prati 3.2 ``PropertyDetailView.post`` obrazac (honeypot/CSRF/PRG/create_inquiry),
    ALI sa ``property=None`` + ``inquiry_type="general"``.

    Security invariants (LOCKED — story 4.2 AC2/AC3):
      * ``inquiry_type``/``property``/``status``/``preferred_language``/``ip_address``
        se postavljaju SERVER-SIDE u ``create_inquiry`` — nikad iz POST-a.
      * popunjen honeypot ``website`` -> NULA redova, ali ISTI 302 ?sent=1 success
        branch kao realan submit (bot vidi "uspeh", ne uči ništa).
      * BEZ slanja email-a (odloženo za 5.2).
      * POST je rate-limitovan na 5/h po IP-u (block=True -> Ratelimited -> 403).
    """

    template_name = "contact.html"

    def _form(self, data=None):
        form = InquiryForm(data)
        # Contact-kontekst: pregazi 3.2 property-specifični placeholder PO INSTANCI
        # (NE menja InquiryForm klasu/Meta — bez migracija, bez uticaja na 3.2).
        form.fields["message"].widget.attrs["placeholder"] = "Vaša poruka…"
        return form

    def get(self, request):
        return render(request, self.template_name, {"form": self._form()})

    def post(self, request):
        form = self._form(request.POST)
        if form.is_valid():
            # Honeypot: popunjen `website` => tiho odbaci, ali vrati ISTI success
            # branch (302 -> ?sent=1) kao realan submit. NULA redova, NULA otkrića.
            if form.cleaned_data.get("website"):
                return redirect(f"{request.path}?sent=1")
            # Jedinstveni write-seam (3.2 reuse): server-side polja + ip_address se
            # postavljaju unutar create_inquiry — nikad iz POST-a. Contact nema
            # Property pa je property=None, inquiry_type="general".
            create_inquiry(
                form=form, property=None, inquiry_type="general", request=request
            )
            return redirect(f"{request.path}?sent=1")  # PRG
        # Invalid -> re-render (200) sa bound greškama; NULA redova.
        return render(request, self.template_name, {"form": form})


@method_decorator(
    ratelimit(
        key="core.ratelimit.client_ip_key", rate="5/h", method="POST", block=True
    ),
    name="post",
)
class PrivateCollectionView(View):
    """Javna Private Collection stranica + 5-poljna Inquiry(private_collection)
    intake forma (Story 5.1).

    GET renderuje ``PrivateCollectionForm()`` + ``site_settings`` (već globalno
    preko core.context_processors.site_settings — NE re-load-uje se ovde). NEMA
    Property upita (FR17 — Private Collection NE prikazuje nekretnine; ovo NIJE
    listing). POST verno prati 4.2 ``ContactView.post`` obrazac (honeypot/CSRF/
    PRG/create_inquiry), ALI sa NOVOM formom, ``property=None`` +
    ``inquiry_type="private_collection"``.

    Security invariants (LOCKED — story 5.1 AC3/AC4):
      * ``inquiry_type``/``property``/``status``/``preferred_language``/``ip_address``
        se postavljaju SERVER-SIDE u ``create_inquiry`` — nikad iz POST-a.
      * ``property_type_wanted``/``budget_range`` JESU form-polja (legitiman unos);
        ``message`` ostaje ``""`` (nije form-polje → default).
      * popunjen honeypot ``website`` -> NULA redova, ali ISTI 302 ?sent=1 success
        branch kao realan submit.
      * BEZ slanja email-a (odloženo za 5.2).
      * POST je rate-limitovan na 5/h po IP-u (block=True -> Ratelimited -> 403).
    """

    template_name = "private-collection.html"

    def get(self, request):
        return render(
            request, self.template_name, {"form": PrivateCollectionForm()}
        )

    def post(self, request):
        form = PrivateCollectionForm(request.POST)
        if form.is_valid():
            # Honeypot: popunjen `website` => tiho odbaci, ali vrati ISTI success
            # branch (302 -> ?sent=1) kao realan submit. NULA redova, NULA otkrića.
            if form.cleaned_data.get("website"):
                return redirect(f"{request.path}?sent=1")
            # Jedinstveni write-seam (3.2 reuse): server-side polja + ip_address se
            # postavljaju unutar create_inquiry — nikad iz POST-a. Private Collection
            # nema konkretnu nekretninu pa je property=None, inquiry_type="private_collection".
            create_inquiry(
                form=form,
                property=None,
                inquiry_type="private_collection",
                request=request,
            )
            return redirect(f"{request.path}?sent=1")  # PRG
        # Invalid -> re-render (200) sa bound greškama; NULA redova.
        return render(request, self.template_name, {"form": form})


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def page_view(request, slug, template_name):
    """Tanak CMS page view (Story 4.1).

    Razrešava Page po fiksnom slug-u (prosleđenom kao kwarg iz eksplicitne rute)
    sa is_active=True gating-om U upitu: nepostojeći ILI is_active=False slug → 404
    (Page NEMA preview polje — gating je čist is_active, ne can_preview). Rute su
    FIKSNE (/about/, /international/) bez <slug> segmenta, pa slug i template_name
    dolaze kao argumenti rute. site_settings je već globalno dostupan preko
    core.context_processors.site_settings (2.2) — NE re-load-uje se ovde.
    """
    page = get_object_or_404(Page, slug=slug, is_active=True)
    return render(request, template_name, {"page": page})
