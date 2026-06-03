---
story-id: 5-2-inquiry-pipeline-cuvanje-notifikacija-auto-reply-anti-spam
title: "Interface Contract — Inquiry pipeline (čuvanje, notifikacija agentu, auto-reply kupcu, anti-spam)"
epic: 5
module: "inquiries, config, templates/email"
phase: RED (TDD) — failing contract definisan PRE implementacije
author: TEA (Test Architect)
created: 2026-06-03
test-file: tests/test_inquiry_emails.py
references:
  - _bmad-output/implementation-artifacts/5-2-inquiry-pipeline-cuvanje-notifikacija-auto-reply-anti-spam.md  # IZVOR ISTINE za AC1–AC6 + T1–T6
  - _bmad-output/implementation-artifacts/5-1-private-collection-stranica-i-intake-forma-interface-contract.md  # REFERENTNI format (5.2 prati 1:1)
  - inquiries/services.py        # create_inquiry(*, form, property, inquiry_type, request=None) — JEDAN write-seam; 5.2 hook-uje email posle inquiry.save()
  - inquiries/models.py          # Inquiry — name/email/phone/message/inquiry_type/property_type_wanted/budget_range/preferred_language/property/ip_address; PK je UUID (id=UUIDField)
  - core/models.py               # SiteSettings.email_inquiries (primalac notifikacije) + email_primary (fallback); SiteSettings.load() singleton
  - config/settings/base.py      # 5.2 DODAJE DEFAULT_FROM_EMAIL (env) + 'anymail' u INSTALLED_APPS; base NE postavlja EMAIL_BACKEND
  - config/settings/dev.py       # 5.2 DODAJE EMAIL_BACKEND = console.EmailBackend
  - config/settings/test.py      # 5.2 DODAJE EMAIL_BACKEND = locmem.EmailBackend (mail.outbox radi)
  - config/settings/prod.py      # 5.2 DODAJE EMAIL_BACKEND = anymail.backends.mailgun.EmailBackend + ANYMAIL dict iz env-a
  - pages/views.py               # ContactView/PrivateCollectionView/PropertyDetailView svi zovu create_inquiry — view-ovi se NE diraju
  - config/urls.py               # admin montiran na ADMIN_URL → admin reverse putanja sadrži "inquiries/inquiry/"
---

# Interface Contract — Story 5.2

> Ovaj dokument je MAŠINSKI ugovor između RED-faze testova (`tests/test_inquiry_emails.py`)
> i buduće implementacije (Dev/GREEN faza). Definiše TAČAN potpis novog email modula,
> servisni hook, settings izmene i email template-e koje testovi asertuju. Implementacija koja
> zadovolji ovaj ugovor čini RED testove zelenim BEZ izmene testova.
>
> **Reuse-first:** 5.2 NE menja `Inquiry`/`SiteSettings` model (bez migracija), NE menja
> potpis `create_inquiry`, NE dira view-ove. 5.2 DODAJE: `inquiries/emails.py` (dva toka +
> orkestrator), email hook unutar `create_inquiry` (posle `inquiry.save()`), email settinge
> po okruženju i `templates/email/` (HTML + plain-text). Cross-cutting: invertuje 3 postojeća
> `mail.outbox==0` testa (Dev radi u GREEN — TEA ih NE dira).

---

## 1. Novi modul — `inquiries/emails.py`

**Kreira se NOVI modul. Importi (LOCKED):** `logging`, `from django.conf import settings`,
`from django.core.mail import EmailMultiAlternatives`, `from django.template.loader import render_to_string`,
`from django.urls import reverse`, `from core.models import SiteSettings`. `logger = logging.getLogger(__name__)`.

### 1.1 `notify_agent(inquiry, *, request=None)` — tok 1 (agentska notifikacija)
- **Primalac:** `s = SiteSettings.load(); recipient = s.email_inquiries or s.email_primary`.
  Ako je `recipient` prazan → `logger.warning(...)` + `return` (preskoči — BEZ crash-a, BEZ izuzetka).
- **Pošiljalac (`from`):** `settings.DEFAULT_FROM_EMAIL`.
- **Admin link (LOCKED na robustan pristup):** `path = reverse("admin:inquiries_inquiry_change", args=[inquiry.pk])`
  (daje putanju koja sadrži segment `inquiries/inquiry/` i ispravan `ADMIN_URL` prefiks);
  apsolutni URL preko `request.build_absolute_uri(path)` kad je `request` prosleđen (→ počinje sa `http`).
  Ako je `request` None → relativni `reverse(...)` put (bez `build_absolute_uri`).
  **ZABRANJENO:** f-string `f"{settings.ADMIN_URL}/inquiries/inquiry/{inquiry.pk}/change/"` (ADMIN_URL bez vodećeg slash-a → pokvaren link).
- **Kontekst:** `inquiry.name`, `inquiry.email`, `inquiry.phone`, `inquiry.get_inquiry_type_display()`,
  `inquiry.message`, `inquiry.property_type_wanted`, `inquiry.budget_range`, `inquiry.property`, admin link.
- **Render + slanje:** `text = render_to_string("email/agent_notification.txt", ctx)`,
  `html = render_to_string("email/agent_notification.html", ctx)`;
  `msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [recipient])`;
  `msg.attach_alternative(html, "text/html")`; `msg.send()`.
- **Subject** sadrži tip upita + ime: npr. `f"Nov upit ({inquiry.get_inquiry_type_display()}) — {inquiry.name}"`.

### 1.2 `send_auto_reply(inquiry)` — tok 2 (auto-reply kupcu)
- **Primalac:** `[inquiry.email]`. **Pošiljalac:** `settings.DEFAULT_FROM_EMAIL`.
- **`EmailMultiAlternatives`** sa plain-text `body` (`email/auto_reply.txt`) + HTML alternativom
  (`email/auto_reply.html` preko `.attach_alternative(html, "text/html")`); brendiran (sadrži „Velegrad").
- **Subject** brendiran: npr. „Hvala na Vašem upitu — Velegrad Estate".
- **XSS:** korisnički unos (ime) kroz `{{ }}` auto-escape — **bez `|safe`**.

### 1.3 `send_inquiry_notifications(inquiry, *, request=None)` — orkestrator (JEDNA tačka koju zove `create_inquiry`)
- **NON-FATAL + PER-FLOW (LOCKED):** svaki tok u SOPSTVENOM `try/except Exception`:
  jedan `try/except` oko `notify_agent(inquiry, request=request)` i ZASEBAN oko `send_auto_reply(inquiry)`.
  Svaki `except` radi `logger.exception(...)` i **NE re-raise-uje**. Pad jednog toka NE potiskuje drugi,
  a celina je non-fatal po request-u. **NE umotavati oba u jedan zajednički try/except.**

---

## 2. Servisni hook — `inquiries/services.py::create_inquiry`

- **Potpis NEPROMENJEN:** `create_inquiry(*, form, property, inquiry_type, request=None) -> Inquiry`.
- Posle `inquiry.save()` i pre `return inquiry`: **lokalni import** `from .emails import send_inquiry_notifications`
  (izbegava circular import `emails → core.models`), zatim `send_inquiry_notifications(inquiry, request=request)`.
- Server-side logika (`inquiry_type`/`property`/`status="new"`/`preferred_language="sr"`/`ip_address`) NEPROMENJENA.
- `create_inquiry` UVEK vraća sačuvani `inquiry` (mail greška se ne propagira — non-fatal već u orkestratoru).

---

## 3. Email settinzi po okruženju (`config/settings/`)

| Modul | Izmena (LOCKED) |
|---|---|
| `base.py` | `DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Velegrad <noreply@velegrad.example>")`; **dodaj `'anymail'` u `INSTALLED_APPS`**. base NE postavlja `EMAIL_BACKEND`. |
| `dev.py` | `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"` |
| `test.py` | `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` (KRITIČNO — puni `mail.outbox`; NE console) |
| `prod.py` | `EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"` + `ANYMAIL = {"MAILGUN_API_KEY": env("MAILGUN_API_KEY"), "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN")}` |

- Kredencijali ISKLJUČIVO iz env-a (django-environ) — **NIKAD hardkodovani** (NFR-5).
- `import anymail` radi (v15.0 instaliran). `.env.example` već ima `MAILGUN_API_KEY`/`MAILGUN_SENDER_DOMAIN`/`DEFAULT_FROM_EMAIL`.

---

## 4. Email template-i — `templates/email/` (GLOBALNI `BASE_DIR/templates/email/`, NE `inquiries/templates/`)

- **Lokacija LOCKED:** `BASE_DIR/templates/email/` (razrešava se preko `TEMPLATES["DIRS"]`).
- `agent_notification.txt` + `agent_notification.html` — sva polja upita + admin link; `{% load i18n %}`, UI copy kroz `{% trans %}`; HTML inline-CSS.
- `auto_reply.txt` + `auto_reply.html` — premium brendiran ton; sadrži „Velegrad" + „Hvala"; HTML inline-CSS (brend boje); **bez `|safe`** na korisničkom unosu.
- Bez eksternog CSS/`<link>` (email klijenti ga ignorišu).

---

## 5. Ponašanje po toku (testabilne invarijante)

- **AC1:** Validan POST za SVAKI tip (`viewing` /properties/<slug>/, `general` /contact/, `private_collection` /private-collection/) sa seedovanim `SiteSettings.email_inquiries` → `Inquiry.count()` +1 **I** `len(mail.outbox) == 2` (notifikacija agentu + auto-reply).
- **AC2:** Notifikacija agentu: `to == [SiteSettings.email_inquiries]`; subject/body sadrži ime + tip; sadržaj sadrži admin link koji sadrži `inquiries/inquiry/` i počinje sa `http`. Prazan `email_inquiries` + postavljen `email_primary` → notifikacija na `email_primary`. Oba prazna → notifikacija preskočena (`len(mail.outbox) == 1` — samo auto-reply).
- **AC3:** Auto-reply: `to == [inquiry.email]`, `EmailMultiAlternatives` sa `("...", "text/html")` u `alternatives`; `body` (plain) nije prazan; HTML sadrži „Velegrad". XSS: `name="<script>alert(1)</script>"` → HTML alternativa sadrži `&lt;script&gt;`, NE sirov `<script>`.
- **AC4:** `settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"`; `settings.DEFAULT_FROM_EMAIL` postavljen; `"anymail" in settings.INSTALLED_APPS`; `import anymail` radi; NEMA hardkodovanog Mailgun ključa u izvoru `config/settings/`.
- **AC5:** Non-fatal — mock `send_inquiry_notifications` (ili niži mailer) da raise → POST i dalje 302 `?sent=1` + red sačuvan. Per-flow — mock SAMO `notify_agent` da raise → `send_auto_reply` se SVEJEDNO šalje (`mail.outbox` ima auto-reply na `inquiry.email`) + 302. Anti-spam: honeypot POST → bez reda i bez email-a.
- **AC6:** TEA NE dira 3 postojeća test fajla (Dev invertuje u GREEN). Opcioni regresijski test: private_collection POST sa seedovanim `email_inquiries` → `len(mail.outbox) == 2`.

---

## 6. Interface Contract — sažetak (machine-readable)

- **module:** `inquiries.emails` (NOVI).
- **functions:**
  - `notify_agent(inquiry, *, request=None)` — to=`email_inquiries or email_primary`; skip ako oba prazna; `EmailMultiAlternatives` + admin link (`reverse("admin:inquiries_inquiry_change", args=[inquiry.pk])` + `request.build_absolute_uri`).
  - `send_auto_reply(inquiry)` — to=`inquiry.email`; `EmailMultiAlternatives` HTML+plain; brendiran.
  - `send_inquiry_notifications(inquiry, *, request=None)` — orkestrator; PER-FLOW non-fatal (svaki tok sopstveni try/except).
  - `inquiries.services.create_inquiry` — poziva `send_inquiry_notifications(inquiry, request=request)` posle `inquiry.save()` (lokalni import); potpis nepromenjen; non-fatal.
- **settings:** `base.DEFAULT_FROM_EMAIL` (env) + `'anymail'` u INSTALLED_APPS; `dev` console; `test` locmem; `prod` anymail Mailgun + `ANYMAIL` dict iz env-a; bez hardkodovanih kredencijala.
- **templates:** `BASE_DIR/templates/email/agent_notification.{html,txt}` + `auto_reply.{html,txt}` (inline-CSS, `{% trans %}`, bez `|safe` na korisničkom unosu, brend marker „Velegrad").
