---
story-id: 3-2-property-detail-stranica
artifact: interface-contract
title: "Interface Contract — Property Detail stranica + Inquiry(viewing) mini forma"
module: "properties, inquiries, config, templates"
phase: RED (TDD) — contract precedes implementation
created: 2026-06-02
author: TEA (Test Architect)
source-of-truth: _bmad-output/implementation-artifacts/3-2-property-detail-stranica.md
---

# Interface Contract — Story 3.2

Ovaj dokument je MAŠINSKI UGOVOR između `tests/test_property_detail.py` (RED faza)
i buduće implementacije (Dev). Sve potpise/klase/imena rute treba implementirati
TAČNO ovako da bi RED testovi prešli u GREEN. Izvor istine za AC = story fajl.

PRVA priča koja PIŠE u bazu (`Inquiry`). Bezbednost (CSRF + validacija +
server-side polja + honeypot + auto-escape) je centralna invarijanta.

---

## 1. `properties/views.py` → `PropertyDetailView` (NOVI; NE diraj `PropertyListView`)

Funkcijski view ili `DetailView`. Importi:
`from django.shortcuts import get_object_or_404, redirect, render`;
`from django.http import Http404`; `from .models import Property`;
`from .preview import can_preview`; `from inquiries.forms import InquiryForm`.

### GET (gating + render)
1. `obj = get_object_or_404(Property, slug=slug)` → **nepostojeći slug = 404**.
2. `if not can_preview(request, obj): raise Http404`. Posledica (preview.py 1.4):
   - `is_active=True` → 200 (bilo koji `collection_type`; NE filtrirati po collection).
   - `is_active=False`, anoniman → **404** (čak i sa `?preview=1`).
   - `is_active=False`, autentikovan staff + `?preview=1` → **200** (preview grana).
   - `is_active=False`, staff BEZ `?preview=1` → **404** (eksplicitan opt-in).
3. Render `template_name="property-detail.html"` (extends base).
4. Kontekst: `property`=obj; `images = obj.images.all()` (ordering `order`);
   `features = obj.features.all()`; `form = InquiryForm()`;
   `show_map = bool(obj.latitude is not None and obj.longitude is not None and obj.show_address)`;
   success marker iz `request.GET.get("sent")`. `site_settings` NE re-load-ovati
   (context processor iz 2.2 je jedini izvor).

### POST (Inquiry DB write — PRG)
1. `form = InquiryForm(request.POST)`.
2. **CSRF:** oslanja se na Django default `CsrfViewMiddleware` + `{% csrf_token %}`.
   POST bez tokena = **403** (NE `@csrf_exempt`).
3. Ako `form.is_valid()`:
   - **Honeypot:** ako `form.cleaned_data.get("website")` popunjeno → **NE snimaj**,
     vrati ISTU success granu kao realni submit: `return redirect(f"{request.path}?sent=1")`
     (**HTTP 302**). Bot vidi „uspeh"; `Inquiry.objects.count()` ostaje nepromenjen.
   - Inače: `inquiry = form.save(commit=False)`; postavi SERVER-SIDE (NIKAD iz POST-a):
     `inquiry.inquiry_type = "viewing"`, `inquiry.property = obj`,
     `inquiry.status = "new"`, **`inquiry.preferred_language = "sr"`** (OBAVEZNO —
     required CharField bez DB default-a; izostanak = IntegrityError/ValueError);
     `inquiry.save()`. **NEMA slanja email-a** (5.2).
   - **PRG:** `return redirect(f"{request.path}?sent=1")` (**302**).
4. Ako `not form.is_valid()` → **re-render detalja (200)** sa bound `form` (greške);
   **bez** kreiranja reda.
5. **Tampering invarijanta:** `inquiry_type`/`property`/`status`/`preferred_language`
   NISU u `InquiryForm.fields` → klijentske POST vrednosti se IGNORIŠU; server-side
   vrednosti uvek pobeđuju.

---

## 2. `inquiries/forms.py` → `InquiryForm` (NOVI fajl)

```python
from django import forms
from .models import Inquiry

class InquiryForm(forms.ModelForm):
    website = forms.CharField(required=False)  # honeypot — NE-model polje
    class Meta:
        model = Inquiry
        fields = ["name", "email", "phone", "message"]
```

- `Meta.fields` = TAČNO `["name", "email", "phone", "message"]` — bez
  `inquiry_type`/`property`/`status`/`preferred_language`/`budget_range`/
  `property_type_wanted`/`notes`/`ip_address`.
- Sva 4 model polja efektivno **required** (model nema `blank=True`); `email`
  validiran (`EmailField`); **`message` required** (`TextField` bez blank).
- `website` honeypot je **NE-model** polje, `required=False`, **NE `HiddenInput`**
  (skriva se CSS-om `.sr-only` u template-u + `aria-hidden`/`tabindex=-1`/`autocomplete=off`).
- Widget `attrs` (`form-input`/`form-textarea`, `required` na `message` textarea)
  poželjni radi CSS/klijent-server usaglašenosti.

---

## 3. Ruta — `config/urls.py`

`path("properties/<slug:slug>/", PropertyDetailView.as_view(), name="property-detail")`
(import uz postojeći `PropertyListView`). Dodaj POSLE `properties/` rute. NE diraj
`home`/`ADMIN_URL/`/`tinymce/`/`handler404`.

- `reverse("property-detail", kwargs={"slug": s}) == f"/properties/{s}/"`.

---

## 4. `templates/property-detail.html`

`{% extends "base.html" %}` + `{% load static i18n %}`.

### `{% block extra_css %}`
`css/pages/property-detail.css` (+ Leaflet CSS). NE drugi page CSS.

### `{% block content %}` sekcije i klase
- **Hero** `<section class="detail-hero">` sa `<img>` (MORA `<img>`, ne svg/bg):
  `{% if property.hero_image %}{{ property.hero_image.url }}{% else %}{% static 'images/placeholders/property-1.svg' %}{% endif %}`.
- **Thumbnail strip** `thumbnail-strip` > `thumbnail-strip__item` po `images`:
  `<img src="{{ img.image.url }}" data-full="{{ img.image.url }}">`, `is-active` na
  `forloop.first`. Prazno → izostavljeno (graceful). **Seed RAZLIČITI URL-ovi**
  (gallery.js dedup po URL-u).
- **Sidebar** `<aside class="detail-sidebar">`: `badge` (status mapiranje),
  `detail-sidebar__title`=`title`, `detail-sidebar__location`=district/city,
  `detail-sidebar__price` (`€{{ property.price|floatformat:0 }}` ili „Cena na upit"
  kad `price_on_request`/`status=='price_on_request'`), `def-table` redovi (Tip/
  Stambena/Ukupna površina/Spavaće/Kupatila/Parking/Sprat/Godina — `year_built`
  red samo `{% if property.year_built %}`).
- **Opis** `detail-description`: `{{ property.description_sr|safe }}` (jedini `|safe`).
- **Features** `amenity-grid` > `amenity-item` po `features`: ikona `f.icon` +
  `{{ f.name_sr }}` (plain, escape; NE `|safe`, NE `.localized()`). Prazno → izostavljeno.
- **Floor plan** `detail-floorplan`: `{% if property.floor_plan %}` → UVEK link
  „Preuzmi floor plan" `<a href="{{ property.floor_plan.url }}">` (img ILI PDF; bez
  `endswith`). Prazno → izostavljeno.
- **Mapa**: `{% if show_map %}<div id="property-map" data-lat="{{ property.latitude }}" data-lng="{{ property.longitude }}">...</div>{% else %}<p>...Tačna adresa dostupna na upit...</p>{% endif %}`.
  `location_address` SAMO `{% if property.show_address %}` (privatnost).
- **Lightbox** (kraj content): `.lightbox[role=dialog][aria-modal=true]` sa
  `.lightbox__close`, `.lightbox__nav.lightbox__prev`, `.lightbox__img`,
  `.lightbox__nav.lightbox__next`, `.lightbox__counter` (TAČNO gallery.js selektori).
- **Agent blok** `agent-block`: avatar (`founder_photo`/inicijali), info
  (`founder_name`/`founder_title_sr`), `agent-block__links`
  (`tel:`/`https://wa.me/`/`mailto:` iz `site_settings`, prazna polja `{% if %}`).
- **Mini forma** `agent-block__form` `<form method="post" action="">` + `{% csrf_token %}`
  + `name`/`phone`/`email`/`message` + honeypot `{{ form.website }}` (`.sr-only` wrapper)
  + **TAČNO JEDAN** `<button type="submit">` „Zakažite privatnu prezentaciju".
  Success: `{% if request.GET.sent %}<div class="form-success">...</div>{% endif %}`.

### `{% block extra_js %}`
`js/gallery.js` (+ Leaflet JS + map init sa `typeof L !== 'undefined'` guard).
**SAMO ovo.**

### Markup guards (LOCKED — KRITIČNO)
- HTML **NE sme** sadržati `data-validate` (skinuto sa inquiry forme — forms.js hijack).
- HTML **NE sme** učitavati `js/forms.js` (samo gallery.js + Leaflet).
- Tekst „konsultacij" se NE pojavljuje (drugo dugme uklonjeno → Epik 4.2).

---

## 5. JS ugovori (van test client domena — referenca za Dev)

- **gallery.js** (postoji): `.detail-hero img` (index 0), `.thumbnail-strip__item img[data-full]`,
  `.lightbox__img/__prev/__next/__close/__counter`. Dedup po URL-u → seed RAZLIČITE URL.
  T6 dodaje touch swipe (`touchstart`/`touchend` delta → next/prev).
- **Leaflet init guard (OBAVEZAN):**
  `if (typeof L !== 'undefined' && el && el.dataset.lat && el.dataset.lng) { ... }`.
  Blokiran/offline Leaflet → nema mape, nema `ReferenceError`. Koordinate kroz
  `data-lat`/`data-lng` (NE inline u `<script>`).

---

## 6. Bezbednosne invarijante (assertuje test)

| Invarijanta | Očekivano |
|---|---|
| CSRF (POST bez tokena, `enforce_csrf_checks`) | 403, `count()==0` |
| Validacija (prazan/neispravan email/message) | 200 re-render, `count()==0` |
| Server-side polja (tampering POST) | `viewing`/`obj`/`new`/`sr` pobeđuju |
| Honeypot popunjen | 302 success grana, `count()==0` |
| Auto-escape (`title='<script>'`) | `&lt;script&gt;`, NE sirov `<script>` |
| `|safe` | SAMO `description_sr` |
| Email | NEMA slanja (5.2); `len(mail.outbox)==0` ako se proverava |

---

## 7. Regresioni guardovi

`manage.py check` čist; GET `/` → 200 (Home); GET `/properties/` → 200 (listing);
admin index (superuser) → 200; `/admin/` → 404; **3.2 NE uvodi migracije modela**.
