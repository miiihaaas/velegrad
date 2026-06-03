---
story-id: 5-1-private-collection-stranica-i-intake-forma
title: "Interface Contract — Private Collection stranica i intake forma"
epic: 5
module: "pages, inquiries, core, templates, config"
phase: RED (TDD) — failing contract definisan PRE implementacije
author: TEA (Test Architect)
created: 2026-06-03
test-file: tests/test_private_collection.py
references:
  - _bmad-output/implementation-artifacts/5-1-private-collection-stranica-i-intake-forma.md   # IZVOR ISTINE za AC1–AC6 + T1–T5
  - _bmad-output/implementation-artifacts/4-2-contact-stranica-sa-formom-i-direktnim-kontaktom-interface-contract.md  # REFERENTNI format + ContactView/ratelimit/PRG obrazac (5.1 prati 1:1)
  - inquiries/forms.py                                                                          # InquiryForm (3.2) — NE diramo; 5.1 DODAJE NOVU PrivateCollectionForm
  - inquiries/services.py                                                                       # create_inquiry(*, form, property, inquiry_type, request=None) — JEDAN write-seam, server-side polja, BEZ email-a (REUTILIZUJE bez izmene)
  - inquiries/models.py                                                                         # Inquiry (inquiry_type CHOICES uklj. 'private_collection'; property_type_wanted/budget_range VEĆ postoje CharField(100, blank); message TextField bez blank; property null=True; preferred_language required; status default 'new'; ip_address)
  - pages/views.py                                                                              # ContactView.post (4.2) — referentni honeypot/CSRF/PRG/create_inquiry/ratelimit obrazac; 5.1 DODAJE PrivateCollectionView
  - config/urls.py                                                                              # home/properties/property-detail/about/international/contact/ADMIN_URL/tinymce — NEMA /private-collection/ (5.1 dodaje)
  - config/settings/base.py                                                                     # 'django_ratelimit' VEĆ u INSTALLED_APPS + SILENCED_SYSTEM_CHECKS (4.2); 5.1 NE menja settings
  - config/settings/test.py                                                                     # RATELIMIT_ENABLE = False VEĆ postavljen (4.2); 5.1 reutilizuje
  - static/css/pages/private-collection.css                                                     # već kopiran (2.1) — pc-hero/pc-hero__subtitle/pc-explanation/pc-form/pc-form__grid/pc-form__full/pc-note
  - docs/OpenDesignFiles/private-collection.html                                                # pc-hero section--dark/pc-hero__subtitle/pc-explanation/pc-form/pc-form__grid (5 polja + select)
---

# Interface Contract — Story 5.1

> Ovaj dokument je MAŠINSKI ugovor između RED-faze testova (`tests/test_private_collection.py`)
> i buduće implementacije (Dev/GREEN faza). Definiše TAČAN potpis forme, view-a, rute, template
> sekcija i servisnog poziva koje testovi asertuju. Implementacija koja zadovolji ovaj ugovor
> čini RED testove zelenim BEZ izmene testova.
>
> **Reuse-first:** 5.1 NE menja `InquiryForm` (3.2) niti `create_inquiry` (3.2) niti `Inquiry`
> model (bez migracija — `property_type_wanted`/`budget_range` već postoje). 5.1 DODAJE NOVU
> `inquiries.forms.PrivateCollectionForm`, `pages.views.PrivateCollectionView`, `config/urls.py`
> rutu i `templates/private-collection.html`. Sva rate-limit infrastruktura je VEĆ tu (4.2).

---

## 1. Forma — `PrivateCollectionForm` (inquiries/forms.py)

**Dodaje se NOVA klasa u `inquiries/forms.py`. `InquiryForm` se NE dira. Bez novih migracija.**

### Potpis (LOCKED — `ModelForm` nad `Inquiry`, honeypot mirror iz `InquiryForm`)

```python
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Inquiry


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


class PrivateCollectionForm(forms.ModelForm):
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"tabindex": "-1", "autocomplete": "off", "aria-hidden": "true"}
        ),
    )
    property_type_wanted = forms.ChoiceField(
        choices=PROPERTY_TYPE_CHOICES, required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    budget_range = forms.ChoiceField(
        choices=BUDGET_CHOICES, required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Inquiry
        fields = ["name", "email", "phone", "property_type_wanted", "budget_range"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", ...}),
            "phone": forms.TextInput(attrs={"class": "form-input", "type": "tel", ...}),
            "email": forms.EmailInput(attrs={"class": "form-input", ...}),
        }
```

### Invarijante (LOCKED)
- **`Meta.model == Inquiry`**, **`Meta.fields == ["name", "email", "phone", "property_type_wanted", "budget_range"]`** (TAČNO 5 — `message` NIJE polje).
- **Korisnička (ne-honeypot) polja:** `set(form.fields) - {"website"} == {"name", "email", "phone", "property_type_wanted", "budget_range"}`.
- **Honeypot `website`:** NON-model, `required=False`, `tabindex="-1"`/`autocomplete="off"`/`aria-hidden="true"`; **NE** `HiddenInput`.
- **`property_type_wanted`/`budget_range`:** `forms.ChoiceField`, `required=True`, `forms.Select(attrs={"class": "form-select"})`. Choices = LOCKED literal gore. **Stored value == čitljiva srpska labela** (npr. `"Stan"`, `"€500.000 – €1.000.000"` sa en-dash-om `–`). Prva opcija prazan `""` placeholder → prazan izbor je nevalidan.
- **`inquiry_type`/`property`/`status`/`preferred_language`/`ip_address`/`message`/`notes` NISU form-polja** (server-side ili default).
- **`InquiryForm` NEPROMENJENA** (regresija 3.2/4.2): `set(InquiryForm().fields) - {"website"} == {"name", "email", "phone", "message"}`.

---

## 2. Servis (REUTILIZUJE se BEZ izmene — 3.2)

### `inquiries.services.create_inquiry(*, form, property, inquiry_type, request=None) -> Inquiry` (NEMA izmene)
- `form.save(commit=False)` → kopira form-polja (`name`/`email`/`phone`/`property_type_wanted`/`budget_range`) na instancu; postavi `inquiry_type` (arg), `property` (arg), `status="new"`, `preferred_language="sr"`, `ip_address=request.META.get("REMOTE_ADDR")` → `save()`.
- `message` NIJE form-polje → instanca ima `message=""` (default praznog stringa za `TextField` koji nije nullable); `save()` prolazi (`full_clean()` se NE poziva). Sačuvana vrednost: `message == ""`.
- BEZ email-a (5.2 hook).
- Private Collection poziv: `create_inquiry(form=form, property=None, inquiry_type="private_collection", request=request)`.

---

## 3. View — `PrivateCollectionView` (pages/views.py)

**Dodaje se NOVI view u `pages/views.py`. `HomeView`/`ContactView`/`custom_404`/`page_view` se NE diraju. Bez novih migracija.**

### Potpis (LOCKED — CBV `View`, verno 4.2 `ContactView`)

```python
from inquiries.forms import PrivateCollectionForm
from inquiries.services import create_inquiry


@method_decorator(
    ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post"
)
class PrivateCollectionView(View):
    template_name = "private-collection.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PrivateCollectionForm()})

    def post(self, request):
        form = PrivateCollectionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("website"):          # honeypot filled -> bot
                return redirect(f"{request.path}?sent=1")  # ISTI success branch, BEZ reda
            create_inquiry(
                form=form, property=None,
                inquiry_type="private_collection", request=request,
            )
            return redirect(f"{request.path}?sent=1")       # PRG
        return render(request, self.template_name, {"form": form})  # invalid -> 200 + bound errors
```

### Invarijante (LOCKED)
- **GET** → `render(request, "private-collection.html", {"form": PrivateCollectionForm()})` (HTTP 200). `site_settings` već u kontekstu (2.2) — **NE re-load**. **NEMA `Property` upita** (FR17 — bez nekretnina).
- **POST honeypot:** `form.cleaned_data.get("website")` truthy → `redirect(f"{request.path}?sent=1")` (302) — ISTI success branch, ALI **NULA** redova.
- **POST valid:** `create_inquiry(form=form, property=None, inquiry_type="private_collection", request=request)` → PRG `redirect(f"{request.path}?sent=1")` (302).
- **POST invalid:** `render(...)` (HTTP **200**) sa bound greškama; **NULA** redova.
- **CSRF (Django default):** POST bez tokena (enforce_csrf_checks klijent) → **403**, NULA redova.
- **Server-side polja (tampering prevention):** `inquiry_type="private_collection"`, `property=None`, `status="new"`, `preferred_language="sr"`, `ip_address=REMOTE_ADDR` — POST koji ih ubaci se ignoriše (nisu form-polja). `property_type_wanted`/`budget_range` JESU form-polja (legitiman unos).
- **`message == ""`** (nije form-polje — default).
- **NEMA email-a** (5.2): `len(mail.outbox) == 0` posle valid POST-a.

### Rate-limit (LOCKED — NFR-5, infra iz 4.2)
- `@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post")` IZNAD `PrivateCollectionView` — dekoriše **samo `post`**.
- `block=True` → preko limita `Ratelimited` → **HTTP 403** (deterministički).
- Rate ZAKLJUČAN: **`5/h`** po IP-u (isto kao `ContactView` 4.2).
- `RATELIMIT_ENABLE = False` u `config/settings/test.py` (VEĆ 4.2) — funkcionalni AC1–AC3 testovi ne padaju; namenski rate-limit test ga uključuje preko `@override_settings(RATELIMIT_ENABLE=True)` + `cache.clear()`.

---

## 4. Ruta (config/urls.py) — EKSPLICITNA, BEZ catch-all

```python
from pages.views import ContactView, HomeView, PrivateCollectionView, page_view
...
path("private-collection/", PrivateCollectionView.as_view(), name="private-collection"),
```

Invarijante:
- `reverse("private-collection") == "/private-collection/"`.
- **`.as_view()`** (CBV — konzistentno sa `ContactView.as_view()`).
- **NEMA root catch-all** `path("<slug:slug>/", ...)` → `GET /nepostojeci-slug/` ostaje **404**.
- **NEMA `i18n_patterns`/`/en/` prefiks** (Epik 6) → `GET /en/private-collection/` → **404**.
- `home`/`properties`/`property-detail`/`about`/`international`/`contact`/`ADMIN_URL/`/`tinymce/`/`handler404` se NE diraju.
- Posledica: 2.2 Home teaser hardkodovan `href="/private-collection/"` sada vodi na živu rutu (200 umesto 404).

---

## 5. Template — `templates/private-collection.html` (FLAT layout, NE `templates/pages/`)

- `{% extends "base.html" %}` + `{% load static i18n %}`.
- `{% block title %}` → `{% trans "Privatna kolekcija" %} — Velegrad Estate`.
- `{% block extra_css %}` → `<link rel="stylesheet" href="{% static 'css/pages/private-collection.css' %}">`.
- `{% block content %}` sekcije (klase verno `docs/OpenDesignFiles/private-collection.html` 64–130):

| Sekcija | Marker (klasa) | Sadržaj | Render |
|---|---|---|---|
| Hero (TAMNA pozadina) | `pc-hero section--dark` | `<h1>{% trans "Privatna kolekcija" %}</h1>` + `pc-hero__subtitle` | `{% trans %}` (NEMA `Page` red) |
| Tekst objašnjenja | `pc-explanation` | paragraf(i) off-market koncepta | `{% trans %}` — **BEZ ijedne nekretnine/cene/adrese** (FR17) |
| Forma | `pc-form` `<form method="post" class="pc-form__grid">` | `{% csrf_token %}` + 5 polja `{{ form.name }}`/`{{ form.email }}`/`{{ form.phone }}`/`{{ form.property_type_wanted }}`/`{{ form.budget_range }}` + honeypot `{{ form.website }}` + submit `btn btn--primary btn--lg` + `form-success` na `?sent=1` + `{{ form.<field>.errors }}` | auto-escape (NE `\|safe`) |
| Labele polja | — | „Ime i prezime" (name), „Email" (email), „Telefon" (phone), „Tip nekretnine" (property_type_wanted), „Budžet" (budget_range) | `{% trans %}` |
| Honeypot | `name="website"` | skriven CSS-om (`.sr-only`/off-screen + `aria-hidden`/`tabindex=-1`) | **NE** `type="hidden"` |
| Success | `form-success` | `{% if request.GET.sent %}<div class="form-success">{% trans "Hvala…" %}</div>{% endif %}` | `{% trans %}` |

### Django field imena (I2) — NE dizajn `name` atributi
- Renderuj `{{ form.property_type_wanted }}` / `{{ form.budget_range }}` → Django renderuje `name="property_type_wanted"` / `name="budget_range"` (donja crta). **NE** hardkoduj dizajnove crtica-imena (`property-type`/`budget`) — pokvarilo bi POST binding i AC2.

### ANTI-LISTING (FR17, KRITIČNA invarijanta)
- HTML **NE** sadrži `property-card` / `listing-grid` markere. Private Collection NIJE listing.

### XSS / trust boundary
- **NEMA `\|safe`** ni na jednom korisničkom polju (Private Collection NEMA admin-curated HTMLField).
- `name="<script>alert(1)</script>"` na invalid re-renderu → `&lt;script&gt;` (escapovano), NE sirov `<script>`.
- **NE `{% loc %}`** (Epik 6); sav UI copy → `{% trans %}`.

---

## 6. Helperi (tests/test_private_collection.py — izvedeni iz test_contact_page.py / test_home_page.py)

- `_get_model(app_label, class_name)` — importlib lookup (izbegava rani import).
- `_pc_path()` — `reverse("private-collection")` ili literal `"/private-collection/"` fallback (RED faza).
- `_try_reverse(name)` — `reverse` ili `None` (NoReverseMatch u RED fazi).
- `_seed_site_settings(**ov)` — `SiteSettings.load()` (footer u base.html koristi `site_settings`).
- `_valid_post_data(**ov)` — dict `name`/`email`/`phone`/`property_type_wanted="Stan"`/`budget_range="€500.000 – €1.000.000"` (LOCKED choices) + honeypot `website=""`.
- `_inquiry_count()` — `Inquiry.objects.count()` (DB-write marker).
- `_get_pc(client, query="")` — `(resp, html)`.
- `_make_property(**ov)` — minimalni aktivni `Property` (regresija `/properties/<slug>/` + tampering `property=<id>`).
- `_seed_page(slug, title_sr, ...)` — `Page.objects.create(...)` (regresija `/about/` + `/international/`).
- `_superuser(django_user_model)` / `_admin_index_path()` — admin regresija.

---

## 7. Regresione invarijante (AC6)

- `python manage.py check` čist (uklj. django-ratelimit system checks — tvrd gate, infra iz 4.2).
- `GET /` → 200 (Home teaser `href="/private-collection/"` sada živ).
- `GET /properties/` → 200; `GET /properties/<slug>/` (seedovan aktivan) → 200.
- `GET /about/` → 200; `GET /international/` → 200 (seedovani `Page` redovi).
- `GET /contact/` → 200 (4.2 nepromenjen).
- **`GET /private-collection/` → 200** (5.1 oživljava rutu).
- admin index (superuser) → 200; `GET /admin/` → 404.
- `GET /en/private-collection/` → 404 (NEMA i18n routing).
- `GET /nepostojeci-slug/` → 404 (NEMA root catch-all).
- Bez novih migracija. Postojeći `test_property_detail.py` (3.2) + `test_contact_page.py` (4.2) + `test_home_page.py` (2.2) ostaju zeleni nepromenjeni. **NEMA inverzije guard testa** (nijedan postojeći test ne asertuje `/private-collection/ → 404`).

---

## 8. Interface Contract — sažetak (machine-readable)

- **urls:** `path("private-collection/", PrivateCollectionView.as_view(), name="private-collection")` — `reverse("private-collection") == "/private-collection/"`; bez catch-all; bez i18n_patterns.
- **views:** `pages.views.PrivateCollectionView(View)` — `template_name="private-collection.html"`; `get` (render `PrivateCollectionForm()`, NEMA `Property` upita) / `post` (honeypot silent-drop → `?sent=1`; valid → `create_inquiry(form, property=None, inquiry_type="private_collection", request)` → PRG `?sent=1`; invalid → render 200); `@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post")`.
- **models:** `inquiries.Inquiry` (REUTILIZUJE — `inquiry_type="private_collection"`, `property=None`, `status="new"`, `preferred_language="sr"`, `message=""`, `property_type_wanted`/`budget_range` iz forme, `ip_address`); bez izmene/migracije. `core.SiteSettings` (footer u base.html).
- **services:** `inquiries.services.create_inquiry(*, form, property, inquiry_type, request=None)` (REUTILIZUJE bez izmene — server-side polja, bez email-a).
- **forms:** `inquiries.forms.PrivateCollectionForm(ModelForm)` (NOVA — `Meta.model=Inquiry`, `Meta.fields=[name,email,phone,property_type_wanted,budget_range]` + honeypot `website`; `property_type_wanted`/`budget_range` `ChoiceField` sa LOCKED choices, value==srpska labela). `inquiries.forms.InquiryForm` NEPROMENJENA (`Meta.fields=[name,email,phone,message]` + honeypot).
- **templates:** `templates/private-collection.html` (FLAT) — `pc-hero section--dark` + `pc-explanation` (BEZ nekretnina, FR17) + `pc-form` (5 polja + csrf + skriven honeypot + form-success na `?sent=1`); `css/pages/private-collection.css`.
- **settings:** NEMA izmena (django_ratelimit + RATELIMIT_ENABLE=False već iz 4.2).
