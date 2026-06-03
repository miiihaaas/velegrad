"""Properties app views (Story 3.1).

``PropertyListView`` renders the public Signature listing at ``/properties/``.

Invarijante (LOCKED):
  * Bazni queryset UVEK: ``collection_type="signature"``, ``is_active=True``,
    ``status__in=["for_sale", "for_rent", "price_on_request"]`` (isključuje
    private/off_market/is_active=False/sold/rented).
  * Filtri se grade ISKLJUČIVO iz ``PropertyFilterForm(request.GET).cleaned_data``
    — nikad sirov ``request.GET`` u ORM (bezbednost; keyword = title__icontains,
    parametrizovano, bez raw SQL).
  * ``[:12]`` slice se primenjuje POSLE svih filtera (filtriraj pa odseci) —
    NE ``paginate_by``.
  * Per-field validacija: ``form.is_valid()`` se zove (validira + puni
    ``cleaned_data`` SAMO validnim poljima), pa se svaki filter čita preko
    ``cleaned_data.get(...)`` — VALIDNA polja se primenjuju, NEVALIDNA (npr.
    ?price_min=abc) jednostavno izostaju (preskaču se) dok ostali validni
    filteri i dalje rade. Nevalidan ulaz → 200, nikad 500.
"""
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView
from django_ratelimit.decorators import ratelimit

from inquiries.forms import InquiryForm
from inquiries.services import create_inquiry

from .forms import PropertyFilterForm
from .models import Property
from .preview import can_preview


class PropertyListView(ListView):
    """Server-side filtrirani Signature listing (max 12)."""

    model = Property
    template_name = "properties.html"
    context_object_name = "properties"

    def get_filter_form(self):
        """Instanciraj ``PropertyFilterForm`` JEDNOM (memoizovano).

        Koriste je i ``get_queryset`` i ``get_context_data`` — bez side-effect
        side-channel-a niti dvostruke instancijacije.
        """
        if not hasattr(self, "_filter_form"):
            self._filter_form = PropertyFilterForm(self.request.GET)
        return self._filter_form

    def get_queryset(self):
        qs = Property.objects.filter(
            collection_type="signature",
            is_active=True,
            status__in=["for_sale", "for_rent", "price_on_request"],
        )

        form = self.get_filter_form()
        # is_valid() validira i puni cleaned_data SAMO validnim poljima; nevalidna
        # polja izostaju iz cleaned_data → cleaned_data.get(...) vrati None → filter
        # se preskoči PER POLJE (validni filteri rade i kad je drugo polje smeće).
        form.is_valid()
        cd = form.cleaned_data

        location = cd.get("location")
        if location:
            # Jedan Q() filter (AND nad istom tabelom, bez fan-out-a → bez
            # potrebe za .distinct()).
            qs = qs.filter(
                Q(location_district__icontains=location)
                | Q(location_city__icontains=location)
            )

        property_type = cd.get("property_type")
        if property_type:
            qs = qs.filter(property_type=property_type)

        status = cd.get("status")
        if status:
            qs = qs.filter(status=status)

        # Price-range filtri NE smeju da sakriju "Cena na upit"
        # (price_on_request=True, price=NULL) ponude: NULL ne prolazi
        # price__gte/__lte (SQL NULL poređenje → isključeno), pa OR-ujemo
        # price_on_request da te premium ponude UVEK prežive opseg cene.
        # (cenovno-neobjavljene, ne van-opsega). Q nad istom kolonom + AND
        # ne pravi duplikate, pa .distinct() nije potreban.
        price_min = cd.get("price_min")
        if price_min is not None:
            qs = qs.filter(Q(price__gte=price_min) | Q(price_on_request=True))

        price_max = cd.get("price_max")
        if price_max is not None:
            qs = qs.filter(Q(price__lte=price_max) | Q(price_on_request=True))

        bedrooms = cd.get("bedrooms")
        if bedrooms is not None:
            qs = qs.filter(bedrooms__gte=bedrooms)

        keyword = cd.get("keyword")
        if keyword:
            qs = qs.filter(title__icontains=keyword)

        # [:12] slice — POSLE svih filtera (LOCKED). NE paginate_by.
        return qs[:12]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.get_filter_form()
        return context


@method_decorator(
    ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post"
)
class PropertyDetailView(View):
    """Public Property Detail page + agent-contact mini Inquiry(viewing) form.

    GET resolves via ``get_object_or_404(Property, slug=...)`` then ``can_preview``
    gating (404 for missing / inactive-to-public; staff ``?preview=1`` -> 200).
    POST handles ``InquiryForm`` — the FIRST DB write — with CSRF (Django default),
    a honeypot, server-side fields, and PRG (POST-redirect-GET to ``?sent=1``).

    Security invariants (LOCKED — story 3.2 AC6):
      * ``inquiry_type``/``property``/``status``/``preferred_language`` are set
        SERVER-SIDE (never from POST — those are not InquiryForm fields).
      * a filled honeypot ``website`` -> NO row, but the SAME 302 success branch
        as a real submit (the bot sees "success", learns nothing).
      * NO email send (deferred to 5.2).
    """

    template_name = "property-detail.html"

    def _get_object(self, request, slug):
        # prefetch images + features to collapse the 2 extra queries the detail
        # template triggers (obj.images.all / obj.features.all). Gating below is
        # unchanged (still get_object_or_404 + can_preview).
        obj = get_object_or_404(
            Property.objects.prefetch_related("images", "features"), slug=slug
        )
        # Gating is by is_active / preview — NOT by collection_type.
        if not can_preview(request, obj):
            raise Http404("Property not visible.")
        return obj

    def _build_context(self, obj, form):
        # Defense-in-depth (S2): only expose virtual_tour_url when it is a safe
        # http(s) scheme. Django auto-escape does NOT neutralize a `javascript:`
        # / `data:` scheme inside an href — an admin-entered `javascript:alert(1)`
        # would otherwise become a clickable XSS vector. URLField does not block
        # such schemes, so we gate the value here and the template renders the
        # link only when this is truthy.
        raw_tour = (obj.virtual_tour_url or "").strip()
        safe_tour = raw_tour if raw_tour.lower().startswith(
            ("http://", "https://")
        ) else ""
        return {
            "property": obj,
            "images": obj.images.all(),
            "features": obj.features.all(),
            "form": form,
            "virtual_tour_url": safe_tour,
            # Map renders ONLY when both coords present AND show_address is on.
            "show_map": bool(
                obj.latitude is not None
                and obj.longitude is not None
                and obj.show_address
            ),
        }

    def get(self, request, slug):
        obj = self._get_object(request, slug)
        context = self._build_context(obj, InquiryForm())
        return render(request, self.template_name, context)

    def post(self, request, slug):
        obj = self._get_object(request, slug)
        form = InquiryForm(request.POST)
        if form.is_valid():
            # Honeypot: a filled `website` => silently drop, but return the SAME
            # success branch as a real submit (302 -> ?sent=1) so a bot sees
            # "success". NO row, NO disclosure.
            if form.cleaned_data.get("website"):
                return redirect(f"{request.path}?sent=1")

            # Single reusable write seam (5.2 email hook + Epic 4/5 reuse).
            # Server-side fields (inquiry_type/property/status/preferred_language)
            # + ip_address are set inside create_inquiry — never from POST.
            create_inquiry(
                form=form, property=obj, inquiry_type="viewing", request=request
            )
            return redirect(f"{request.path}?sent=1")

        # Invalid -> re-render (200) with bound form errors; NO row created.
        context = self._build_context(obj, form)
        return render(request, self.template_name, context)
