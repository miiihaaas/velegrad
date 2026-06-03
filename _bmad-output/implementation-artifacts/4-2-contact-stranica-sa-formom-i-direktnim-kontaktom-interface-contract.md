---
story-id: 4-2-contact-stranica-sa-formom-i-direktnim-kontaktom
title: "Interface Contract — Contact stranica sa formom i direktnim kontaktom"
epic: 4
module: "pages, inquiries, core, templates, config"
phase: RED (TDD) — failing contract definisan PRE implementacije
author: TEA (Test Architect)
created: 2026-06-03
test-file: tests/test_contact_page.py
references:
  - _bmad-output/implementation-artifacts/4-2-contact-stranica-sa-formom-i-direktnim-kontaktom.md   # IZVOR ISTINE za AC1–AC6 + T1–T6
  - inquiries/forms.py                                                                              # InquiryForm (3.2) — Meta.fields = [name,email,phone,message] + honeypot 'website' (REUTILIZUJE bez izmene)
  - inquiries/services.py                                                                           # create_inquiry(*, form, property, inquiry_type, request=None) — JEDAN write-seam, server-side polja, BEZ email-a
  - inquiries/models.py                                                                             # Inquiry (inquiry_type CHOICES uklj. 'general'; property null=True; preferred_language required; status default 'new'; ip_address)
  - properties/views.py                                                                             # PropertyDetailView.post (3.2) — referentni honeypot/CSRF/PRG/create_inquiry obrazac
  - core/models.py                                                                                  # SiteSettings (phone_primary/whatsapp_number/email_primary/address) + .load()
  - core/context_processors.py                                                                      # site_settings(request) — globalno u svakom template-u (2.2), NE re-load
  - config/urls.py                                                                                  # home/properties/property-detail/about/international/ADMIN_URL/tinymce — NEMA /contact/ (4.2 dodaje)
  - config/settings/base.py                                                                         # INSTALLED_APPS (NEMA 'django_ratelimit' — 4.2 dodaje); NEMA CACHES (implicitni LocMemCache 'default')
  - config/settings/test.py                                                                         # NEMA RATELIMIT_ENABLE (4.2 dodaje = False)
  - static/css/pages/contact.css                                                                    # već kopiran (2.1) — contact-hero*/contact-layout/contact-form/contact-direct*
  - docs/OpenDesignFiles/contact.html                                                               # contact-hero/contact-layout/contact-form (4 polja)/contact-direct (tel/wa.me/mailto/address)
---

# Interface Contract — Story 4.2

> Ovaj dokument je MAŠINSKI ugovor između RED-faze testova (`tests/test_contact_page.py`)
> i buduće implementacije (Dev/GREEN faza). Definiše TAČAN potpis view-a, rute, template
> sekcija, servisnog poziva i settings izmena koje testovi asertuju. Implementacija koja
> zadovolji ovaj ugovor čini RED testove zelenim BEZ izmene testova.
>
> **Reuse-first:** 4.2 NE menja `InquiryForm` (3.2) niti `create_inquiry` (3.2) — reutilizuje
> ih kakvi jesu (bez novih migracija). Jedini novi kod je `pages.views.ContactView`,
> `config/urls.py` ruta, `templates/contact.html`, i config izmene (INSTALLED_APPS +
> `RATELIMIT_ENABLE`).

---

## 1. View — `ContactView` (pages/views.py)

**Dodaje se NOVI view u `pages/views.py`. `HomeView`/`custom_404`/`page_view` se NE diraju. Bez novih migracija.**

### Potpis (LOCKED — CBV `View`, verno 3.2 `PropertyDetailView`)

```python
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django_ratelimit.decorators import ratelimit

from inquiries.forms import InquiryForm
from inquiries.services import create_inquiry


@method_decorator(
    ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post"
)
class ContactView(View):
    template_name = "contact.html"

    def _form(self, data=None):
        form = InquiryForm(data)
        # Contact-kontekst: pregazi 3.2 property-specifični placeholder PO INSTANCI
        # (NE menjaj InquiryForm klasu/Meta — bez migracija, bez uticaja na 3.2).
        form.fields["message"].widget.attrs["placeholder"] = "Vaša poruka…"
        return form

    def get(self, request):
        return render(request, self.template_name, {"form": self._form()})

    def post(self, request):
        form = self._form(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("website"):          # honeypot filled -> bot
                return redirect(f"{request.path}?sent=1")  # ISTI success branch, BEZ reda
            create_inquiry(
                form=form, property=None, inquiry_type="general", request=request
            )
            return redirect(f"{request.path}?sent=1")       # PRG
        return render(request, self.template_name, {"form": form})  # invalid -> 200 + bound errors
```

### Invarijante (LOCKED)
- **GET** → `render(request, "contact.html", {"form": InquiryForm()})` (HTTP 200). `site_settings` već u kontekstu preko `core.context_processors.site_settings` (2.2) — **NE re-load** u view-u.
- **Message placeholder override (PO INSTANCI, GET i invalid-POST re-render):** 3.2 `InquiryForm.message` placeholder „Zainteresovan/a sam za ovu nekretninu…" je property-specifičan; Contact ga pregazi na Contact-prikladan tekst (npr. „Vaša poruka…"). **NE menjati `InquiryForm` klasu/Meta.** Test asertuje da reč „nekretninu" NE curi u Contact render.
- **POST honeypot:** `form.cleaned_data.get("website")` truthy → `redirect(f"{request.path}?sent=1")` — ISTI 302 success branch kao realan submit, ALI **NULA** redova.
- **POST valid:** `create_inquiry(form=form, property=None, inquiry_type="general", request=request)` → PRG `redirect(f"{request.path}?sent=1")` (302).
- **POST invalid:** `render(...)` (HTTP **200**) sa bound greškama; **NULA** redova.
- **CSRF (Django default):** POST bez tokena (enforce_csrf_checks klijent) → **403**, NULA redova. (Nasleđeno iz globalnog `CsrfViewMiddleware` — NE isključivati.)
- **Server-side polja (tampering prevention):** `inquiry_type`/`property`/`status`/`preferred_language`/`ip_address` se NIKAD ne čitaju iz POST-a — `create_inquiry` ih postavlja: `inquiry_type="general"`, `property=None`, `status="new"`, `preferred_language="sr"`, `ip_address=REMOTE_ADDR`. POST koji ubaci `inquiry_type`/`status`/`property`/`preferred_language` se ignoriše (nisu `InquiryForm` polja).
- **NEMA email-a** (5.2): `create_inquiry` već nema `send_mail`; `len(mail.outbox) == 0` posle valid POST-a. NE dodavati email u 4.2.

### Rate-limit (LOCKED — NFR-5, PRVI put u projektu)
- `@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post")` IZNAD `ContactView` klase — dekoriše **samo `post`** (ne `get`, ne `dispatch`).
- `block=True` → preko limita django-ratelimit diže `Ratelimited` koji Django mapira u **HTTP 403** (deterministički; jedini over-limit odgovor je 403, NE graciozni 302).
- Rate je ZAKLJUČAN: **`5/h`** po IP-u.
- **Preduslov:** `django-ratelimit` mora biti instaliran u venv-u (`pip install -r requirements/base.txt`) i importabilan (`import django_ratelimit`) PRE nego što modul radi. Na RED-u paket NIJE instaliran — rate-limit test errors/fails honestly do GREEN-a.

---

## 2. Forma + servis (REUTILIZUJU se BEZ izmene — 3.2)

### `inquiries.forms.InquiryForm` (NEMA izmene)
- `Meta.fields == ["name", "email", "phone", "message"]` (TAČNO 4 korisnička polja — FR20).
- Non-model honeypot `website` (`required=False`, `tabindex="-1"`/`autocomplete="off"`/`aria-hidden="true"`; **NE** `HiddenInput`).
- `inquiry_type`/`property`/`status`/`preferred_language` NISU form polja.
- `message` REQUIRED (model `TextField` bez `blank=True`) — server pobeđuje (prazna poruka → invalid → re-render, NE red).
- **Test invarijanta:** `set(form.fields) - {"website"} == {"name","email","phone","message"}`.

### `inquiries.services.create_inquiry(*, form, property, inquiry_type, request=None) -> Inquiry` (NEMA izmene)
- `form.save(commit=False)` → postavi `inquiry_type` (arg), `property` (arg), `status="new"`, `preferred_language="sr"`, `ip_address=request.META.get("REMOTE_ADDR")` → `save()`.
- BEZ email-a (5.2 hook).
- Contact poziv: `create_inquiry(form=form, property=None, inquiry_type="general", request=request)`.

---

## 3. Ruta (config/urls.py) — EKSPLICITNA, BEZ catch-all

```python
from pages.views import ContactView, HomeView, page_view
...
path("contact/", ContactView.as_view(), name="contact"),
```

Invarijante:
- `reverse("contact") == "/contact/"`.
- **`.as_view()`** (Contact je CBV — konzistentno sa `HomeView.as_view()`/`PropertyDetailView.as_view()`).
- **NEMA root catch-all** `path("<slug:slug>/", ...)`. → `GET /nepostojeci-slug/` ostaje **404**.
- **NEMA `i18n_patterns`/`/en/` prefiks** (Epik 6) → `GET /en/contact/` → **404**.
- `home`/`properties`/`property-detail`/`about`/`international`/`ADMIN_URL/`/`tinymce/`/`handler404` se NE diraju.
- Posledica: 4.1 hardkodovan `href="/contact/"` (About/International CTA) sada vodi na živu rutu (200 umesto 404).

---

## 4. Template — `templates/contact.html` (FLAT layout, NE `templates/pages/`)

- `{% extends "base.html" %}` + `{% load static i18n %}`.
- `{% block extra_css %}` → `<link rel="stylesheet" href="{% static 'css/pages/contact.css' %}">`.
- `{% block content %}` sekcije (klase verno `docs/OpenDesignFiles/contact.html` 64–122):

| Sekcija | Marker (klasa) | Sadržaj | Render |
|---|---|---|---|
| Hero | `contact-hero` | `<h1>{% trans "Kontakt" %}</h1>` + intro | `{% trans %}` (Contact NEMA `Page` red — sve je `{% trans %}`) |
| Layout | `contact-layout` | dvo-kolonski (forma levo, direktni kontakt desno) | — |
| Forma | `contact-form` `<form method="post">` | `{% csrf_token %}` + 4 polja `{{ form.name }}`/`{{ form.phone }}`/`{{ form.email }}`/`{{ form.message }}` + honeypot `{{ form.website }}` + submit `btn btn--primary btn--lg` + `form-success` na `?sent=1` + `{{ form.<field>.errors }}` | auto-escape (NE `\|safe`) |
| Labele polja | — | „Ime i prezime" (name), „Telefon" (phone), „Email" (email), „Poruka" (message) | `{% trans %}` |
| Honeypot | `name="website"` | skriven CSS-om (`.sr-only`/off-screen + `aria-hidden`/`tabindex=-1`) | **NE** `type="hidden"` |
| Success | `form-success` | `{% if request.GET.sent %}<div class="form-success">{% trans "Hvala…" %}</div>{% endif %}` | `{% trans %}` |
| Direktni kontakt | `contact-direct` | tel/wa.me/mailto/address iz `site_settings`, `{% if %}`-gated | auto-escape (NE `\|safe`) |

### Direktni kontakt — `{% if %}` gating (AC4, LOCKED)
```django
{% if site_settings.phone_primary %}
  <a href="tel:{{ site_settings.phone_primary }}" class="contact-direct__value">{{ site_settings.phone_primary }}</a>
{% endif %}
{% if site_settings.whatsapp_number %}
  <a href="https://wa.me/{{ site_settings.whatsapp_number }}" class="contact-direct__whatsapp btn btn--champagne" target="_blank" rel="noopener">{% trans "Pišite na WhatsApp" %}</a>
{% endif %}
{% if site_settings.email_primary %}
  <a href="mailto:{{ site_settings.email_primary }}" class="contact-direct__value">{{ site_settings.email_primary }}</a>
{% endif %}
{% if site_settings.address %}
  <div class="contact-direct__address">{{ site_settings.address|linebreaksbr }}</div>
{% endif %}
```
- Pun `SiteSettings` → `href="tel:..."`, `href="https://wa.me/..."` (sa `target="_blank"` + `rel="noopener"`), `href="mailto:..."`, adresa.
- Prazan `SiteSettings` → odgovarajući `{% if %}` blok izostaje; **NE** prazan `href="tel:"`/`href="https://wa.me/"`/`href="mailto:"`; stranica i dalje **200**.

### XSS / trust boundary
- **NEMA `\|safe`** ni na jednom korisničkom/kontakt polju (Contact NEMA admin-curated HTMLField kao 4.1 `Page.content_sr`).
- `name="<script>alert(1)</script>"` na invalid re-renderu → mora se renderovati kao `&lt;script&gt;` (escapovano), NE sirov `<script>`.

---

## 5. Settings (config/settings)

### `config/settings/base.py` — INSTALLED_APPS
- **DODAJ `'django_ratelimit'`** u `INSTALLED_APPS` (django-ratelimit 4.x system checks zahtevaju ga da `manage.py check` prođe). Test asertuje `"django_ratelimit" in settings.INSTALLED_APPS`.
- `CACHES`: implicitni `LocMemCache` pod aliasom `default` je prihvatljiv (dev/test); django-ratelimit ga koristi; `cache.clear()` u rate-limit testu cilja taj alias.
- Rate-limit ostaje AKTIVAN u `base`/`dev`/`prod` (NFR-5).

### `config/settings/test.py` — anti-flaky
- **DODAJ `RATELIMIT_ENABLE = False`** (posle `DATABASES` override-a). Razlog: LocMemCache persistira po-procesu kroz testove → bez flag-a AC1/AC2 funkcionalni testovi (više POST-ova) bi nasumično padali na rate-limit. Test asertuje `settings.RATELIMIT_ENABLE is False`.
- Namenski rate-limit test ga privremeno UKLJUČUJE preko `@override_settings(RATELIMIT_ENABLE=True)` + `cache.clear()`.

---

## 6. Helperi (tests/test_contact_page.py — izvedeni iz test_property_detail.py / test_home_page.py)

- `_get_model(app_label, class_name)` — importlib lookup (izbegava rani import).
- `_contact_path()` — `reverse("contact")` ili literal `"/contact/"` fallback (RED faza — ruta još ne postoji).
- `_try_reverse(name)` — `reverse` ili `None` (NoReverseMatch u RED fazi).
- `_seed_site_settings(**ov)` — `SiteSettings.load()` → set `phone_primary`/`whatsapp_number`/`email_primary`/`address` → `.save()`.
- `_blank_site_settings()` — `SiteSettings.load()` sa svim kontakt poljima `""` (AC4 gating granica).
- `_valid_post_data(**ov)` — dict `name`/`email`/`phone`/`message` + honeypot `website=""`.
- `_inquiry_count()` — `Inquiry.objects.count()` (DB-write marker).
- `_get_contact(client, query="")` — `(resp, html)`.
- `_make_property(**ov)` — minimalni aktivni `Property` (regresija `/properties/<slug>/`).
- `_seed_page(slug, title_sr, ...)` — `Page.objects.create(...)` (regresija `/about/` + `/international/`).
- `_superuser(django_user_model)` / `_admin_index_path()` — admin regresija.
- Sentineli: `PHONE`/`WHATSAPP`/`EMAIL`/`ADDRESS` (distinct vrednosti za render-asert).

---

## 7. Regresione invarijante (AC6)

- `python manage.py check` čist (uklj. django-ratelimit system checks — tvrd gate).
- `GET /` → 200; `GET /properties/` → 200; `GET /properties/<slug>/` (seedovan aktivan) → 200.
- `GET /about/` → 200; `GET /international/` → 200 (seedovani `Page` redovi); njihov CTA `href="/contact/"` SADA živ (200).
- **`GET /contact/` → 200** (4.2 oživljava rutu — NIJE više 404 kao u 4.1 guard testu).
- admin index (superuser) → 200; `GET /admin/` → 404.
- `GET /en/contact/` → 404 (NEMA i18n routing).
- `GET /nepostojeci-slug/` → 404 (NEMA root catch-all).
- Bez novih migracija (samo view/template/URL + INSTALLED_APPS + test-settings flag).
- **JEDINA namerno izmenjena postojeća asertacija:** `tests/test_static_pages.py::test_contact_route_still_404` (~l.767) — Dev/GREEN je invertuje na `/contact/ → 200` (ili premešta u 4.2 set). Svi OSTALI postojeći testovi ostaju zeleni nepromenjeni.

---

## 8. Interface Contract — sažetak (machine-readable)

- **urls:** `path("contact/", ContactView.as_view(), name="contact")` — `reverse("contact") == "/contact/"`; bez catch-all; bez i18n_patterns.
- **views:** `pages.views.ContactView(View)` — `template_name="contact.html"`; `get` (render `InquiryForm()` + placeholder override) / `post` (honeypot silent-drop → `?sent=1`; valid → `create_inquiry(form, property=None, inquiry_type="general", request)` → PRG `?sent=1`; invalid → render 200); `@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post")`.
- **models:** `inquiries.Inquiry` (REUTILIZUJE — `inquiry_type="general"`, `property=None`, `status="new"`, `preferred_language="sr"`, `ip_address`); bez izmene/migracije. `core.SiteSettings` (čita `phone_primary`/`whatsapp_number`/`email_primary`/`address`).
- **services:** `inquiries.services.create_inquiry(*, form, property, inquiry_type, request=None)` (REUTILIZUJE bez izmene — server-side polja, bez email-a).
- **forms:** `inquiries.forms.InquiryForm` (REUTILIZUJE bez izmene — `Meta.fields=[name,email,phone,message]` + honeypot `website`).
- **templates:** `templates/contact.html` (FLAT) — `contact-hero` + `contact-layout` > `contact-form` (4 polja + csrf + honeypot + form-success) + `contact-direct` (tel/wa.me/mailto/address, `{% if %}`-gated); `css/pages/contact.css`.
- **settings:** `config/settings/base.py` INSTALLED_APPS += `'django_ratelimit'`; `config/settings/test.py` += `RATELIMIT_ENABLE = False`.
