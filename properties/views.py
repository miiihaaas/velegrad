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
from django.views.generic import ListView

from .forms import PropertyFilterForm
from .models import Property


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
