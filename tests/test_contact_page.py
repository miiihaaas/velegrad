"""
RED-phase contract tests for Story 4.2 — "Contact stranica sa formom i direktnim
kontaktom".

These tests define the CONTRACT for the public Contact page at /contact/ — a
4-field Inquiry form (name/phone/email/message) that writes an
Inquiry(inquiry_type="general") row, plus a direct one-click contact column
(tel:/wa.me/mailto:/address) read from SiteSettings. They are written BEFORE the
feature is built, so EVERY 4.2 test in this module MUST FAIL/ERROR until the Dev
implements (GREEN phase):

  * pages/views.py::ContactView(View) — GET renders InquiryForm() (with a
    Contact-appropriate message placeholder override) + site_settings; POST
    validates InquiryForm(request.POST): a filled honeypot `website` -> the SAME
    302 ?sent=1 success branch but NO row; a valid submit -> create_inquiry(
    form=form, property=None, inquiry_type="general", request=request) then PRG
    302 -> ?sent=1; invalid -> re-render 200 with bound errors. POST is
    rate-limited via @method_decorator(ratelimit(key="ip", rate="5/h",
    method="POST", block=True), name="post");
  * config/urls.py — EXPLICIT route path("contact/", ContactView.as_view(),
    name="contact"), NO root catch-all, NO i18n_patterns;
  * templates/contact.html ({% extends base %} + contact-hero + contact-layout >
    contact-form (4 fields + csrf + hidden honeypot + form-success on ?sent=1) +
    contact-direct (tel/wa.me/mailto/address from site_settings, {% if %}-gated)
    + css/pages/contact.css);
  * config/settings/test.py — RATELIMIT_ENABLE = False (anti-flaky) + the
    'django_ratelimit' INSTALLED_APPS entry / RATELIMIT_ENABLE setting name.

Design / locked rules (mirrors the 2.2 / 3.2 / 4.1 harness):
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * The Inquiry POST reuses the EXACT 3.2 seam (InquiryForm + create_inquiry):
    Meta.fields == [name, email, phone, message] + a non-model honeypot
    `website`; inquiry_type/property/status/preferred_language/ip_address are set
    SERVER-SIDE in create_inquiry (never from POST -> tampering prevention).
  * Contact uses inquiry_type="general" and property=None (Contact has no
    Property). status="new" + preferred_language="sr" come from create_inquiry.
  * No |safe on any user/contact field (Contact has no admin-curated HTMLField).
    Auto-escape is proven via name="<script>alert(1)</script>" on invalid POST.
  * Email: 5.2 SADA šalje preko create_inquiry seam-a — kad je email_inquiries
    seed-ovan, jedan validan Contact POST pošalje 2 mejla (agent + auto-reply).
    Ovi testovi su već invertovani da to potvrde (ne više mail.outbox == 0).
  * django-ratelimit is declared in requirements/base.txt but may NOT be
    installed in the active venv yet (Dev installs it in GREEN). The rate-limit
    decorator import is therefore guarded at module import so the OTHER tests
    still collect; the dedicated rate-limit test errors/fails honestly at RED.
  * Each test maps to an acceptance criterion via an `# ACN:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    4-2-contact-stranica-sa-formom-i-direktnim-kontaktom-interface-contract.md
"""
import importlib

import pytest
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.test import Client, override_settings
from django.urls import NoReverseMatch, reverse


# --------------------------------------------------------------------------- #
# Model / path helpers — mirror tests/test_property_detail.py + test_home_page #
# --------------------------------------------------------------------------- #
def _get_model(app_label, class_name):
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


def _admin_index_path():
    """The mounted admin index path, derived from settings.ADMIN_URL."""
    return "/" + settings.ADMIN_URL.strip("/") + "/"


def _superuser(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass12345",
    )


def _try_reverse(name, **kwargs):
    """reverse(name) or None if the route does not exist yet (RED phase)."""
    try:
        return reverse(name, **kwargs)
    except NoReverseMatch:
        return None


def _contact_path():
    """The contact route path (live in GREEN). Fall back to the locked literal
    so the GET/POST tests still exercise the URL string in RED (404 there)."""
    return _try_reverse("contact") or "/contact/"


# Distinct SiteSettings sentinels so a render-assert proves the exact field
# reached the HTML (not an incidental substring collision with the leftover 2.1
# static footer placeholders).
PHONE = "+381601234567"
WHATSAPP = "381601234567"
EMAIL = "info@velegradestate.rs"
ADDRESS = "Beograd, Srbija"


def _seed_site_settings(**overrides):
    """Load the singleton and populate the contact fields used by contact-direct.

    Pass blank values via overrides (e.g. phone_primary="") to exercise the
    {% if %} gating (AC4 empty branch).
    """
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.phone_primary = PHONE
    obj.whatsapp_number = WHATSAPP
    obj.email_primary = EMAIL
    obj.address = ADDRESS
    obj.hero_image = ""
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _blank_site_settings():
    """A fully-blank SiteSettings singleton (all contact fields empty)."""
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.phone_primary = ""
    obj.whatsapp_number = ""
    obj.email_primary = ""
    obj.address = ""
    obj.save()
    return obj


def _valid_post_data(**overrides):
    """The 4 user fields + an empty honeypot (mirrors test_property_detail)."""
    data = dict(
        name="Marko Markovic",
        email="marko@example.com",
        phone="+381601234567",
        message="Zelim da stupim u kontakt sa savetnikom.",
        website="",  # honeypot empty -> a real (human) submit
    )
    data.update(overrides)
    return data


def _inquiry_count():
    return _get_model("inquiries", "Inquiry").objects.count()


def _get_contact(client, query=""):
    url = _contact_path()
    if query:
        url = url + "?" + query.lstrip("?")
    resp = client.get(url)
    return resp, resp.content.decode("utf-8")


def _make_property(**overrides):
    """Minimal active Property for the /properties/<slug>/ regression (AC6)."""
    Property = _get_model("properties", "Property")
    defaults = dict(
        title="Regresija Detalj",
        status="for_sale",
        collection_type="signature",
        property_type="penthouse",
        location_city="Beograd",
        location_district="Dedinje",
        area_sqm="120.00",
        area_total_sqm="140.00",
        bedrooms=3,
        bathrooms=2,
        floor=4,
        total_floors=6,
        parking_spaces=1,
        year_built=2023,
        price="850000.00",
        description_sr="<p>Opis</p>",
        description_en="<p>Description</p>",
        hero_image="",
        is_featured=False,
        is_active=True,
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


def _seed_page(slug, title_sr, content_sr="<p>Sadrzaj</p>", **overrides):
    """Seed a static CMS Page (about/international regression — AC6)."""
    Page = _get_model("pages", "Page")
    defaults = dict(slug=slug, title_sr=title_sr, content_sr=content_sr,
                    is_active=True)
    defaults.update(overrides)
    return Page.objects.create(**defaults)


# =========================================================================== #
# AC1 — Contact /contact/ 200 with the EXACTLY-4-field form                    #
# =========================================================================== #
@pytest.mark.django_db
def test_contact_returns_200_and_uses_template_extending_base(client):
    # AC1: GET /contact/ -> 200, renders contact.html which extends base.html
    # (site-header + site-footer), and loads css/pages/contact.css.
    _seed_site_settings()
    resp, html = _get_contact(client)
    assert resp.status_code == 200, (
        f"GET /contact/ must return 200, got {resp.status_code} (AC1)."
    )
    template_names = [getattr(t, "name", None) for t in resp.templates]
    assert "contact.html" in template_names, (
        f"the contact page must render 'contact.html', got {template_names} (AC1)."
    )
    assert "site-header" in html and "site-footer" in html, (
        "contact.html must extend base.html (site-header + site-footer) (AC1)."
    )
    assert "css/pages/contact.css" in html, (
        "contact.html must load css/pages/contact.css via {% block extra_css %} (AC1)."
    )


@pytest.mark.django_db
def test_contact_renders_hero_and_form_sections(client):
    # AC1: the contact-hero and contact-form design sections render.
    _seed_site_settings()
    resp, html = _get_contact(client)
    assert resp.status_code == 200
    assert 'class="contact-hero"' in html, "the contact-hero section must render (AC1)."
    assert 'class="contact-form"' in html, "the contact-form must render (AC1)."


@pytest.mark.django_db
def test_contact_form_exposes_exactly_four_fields_and_csrf(client):
    # AC1: the form is a <form method="post"> with {% csrf_token %} and EXACTLY
    # the 4 user controls name/phone/email/message.
    _seed_site_settings()
    resp, html = _get_contact(client)
    assert resp.status_code == 200
    assert '<form method="post"' in html or "method='post'" in html.lower(), (
        "the contact form must be a <form method=\"post\"> (AC1)."
    )
    assert "csrfmiddlewaretoken" in html, (
        "the contact form must include {% csrf_token %} (AC1, NFR-5)."
    )
    for name in ("name", "phone", "email", "message"):
        assert f'name="{name}"' in html, (
            f"the contact form must expose a control name=\"{name}\" (AC1)."
        )


@pytest.mark.django_db
def test_contact_honeypot_present_but_not_type_hidden(client):
    # AC1 (anti-spam markup): the honeypot `website` input renders, but it must
    # NOT be type="hidden" (bots skip type=hidden; it is hidden via CSS/.sr-only +
    # aria-hidden/tabindex=-1 instead — mirrors the 3.2 InquiryForm widget).
    _seed_site_settings()
    resp, html = _get_contact(client)
    assert resp.status_code == 200
    assert 'name="website"' in html, (
        "the honeypot 'website' field must render (AC1)."
    )
    w_idx = html.find('name="website"')
    tag_start = html.rfind("<input", 0, w_idx)
    tag_end = html.find(">", w_idx)
    tag = html[tag_start:tag_end + 1]
    assert 'type="hidden"' not in tag, (
        "the honeypot 'website' input must NOT be type=\"hidden\" (bots skip "
        "type=hidden — it is hidden via CSS/.sr-only) (AC1)."
    )


def test_inquiry_form_non_honeypot_fields_are_exactly_four():
    # AC1 (anti-"5th field" invariant): InquiryForm's non-honeypot (model) fields
    # are EXACTLY {name, email, phone, message} — no inquiry_type/budget/etc.
    forms_mod = importlib.import_module("inquiries.forms")
    InquiryForm = getattr(forms_mod, "InquiryForm")
    form = InquiryForm()
    user_fields = set(form.fields) - {"website"}
    assert user_fields == {"name", "email", "phone", "message"}, (
        f"InquiryForm non-honeypot fields must be exactly "
        f"{{name, email, phone, message}}, got {user_fields} (AC1, FR20)."
    )
    for forbidden in ("inquiry_type", "property", "status", "preferred_language"):
        assert forbidden not in form.fields, (
            f"InquiryForm must NOT expose '{forbidden}' as a field (server-side "
            f"only — tampering prevention) (AC1)."
        )


@pytest.mark.django_db
def test_contact_message_placeholder_is_contact_appropriate(client):
    # AC1: the 3.2 message placeholder ("...za ovu nekretninu...") is
    # property-specific and wrong on Contact — the view overrides it per-instance
    # to a Contact-appropriate text. The property-specific phrase must NOT leak.
    _seed_site_settings()
    resp, html = _get_contact(client)
    assert resp.status_code == 200
    assert "nekretninu" not in html, (
        "the Contact message placeholder must be overridden (the 3.2 "
        "property-specific '...za ovu nekretninu...' placeholder must NOT leak "
        "onto the Contact page) (AC1)."
    )


# =========================================================================== #
# AC2 — Valid POST creates Inquiry(general) + CSRF + PRG + tampering + no email #
# =========================================================================== #
@pytest.mark.django_db
def test_contact_post_valid_creates_one_general_inquiry_and_redirects(client):
    # AC2: a valid POST creates EXACTLY ONE Inquiry with the server-set fields
    # (general/new/sr/property=None/ip_address), then PRG-redirects (302) to
    # ?sent=1; following the redirect -> 200 with the form-success message.
    _seed_site_settings()
    Inquiry = _get_model("inquiries", "Inquiry")
    assert _inquiry_count() == 0
    resp = client.post(_contact_path(), data=_valid_post_data())
    assert resp.status_code == 302, (
        f"a valid Contact POST must PRG-redirect (302), got {resp.status_code} (AC2)."
    )
    assert "sent=1" in resp.url, (
        f"the PRG redirect must carry the success marker ?sent=1, got {resp.url!r} (AC2)."
    )
    assert _inquiry_count() == 1, (
        f"a valid POST must create exactly ONE Inquiry, got {_inquiry_count()} (AC2)."
    )
    inq = Inquiry.objects.get()
    assert inq.inquiry_type == "general", (
        "server must set inquiry_type='general' on the Contact form (AC2)."
    )
    assert inq.status == "new", "server must set status='new' (AC2)."
    assert inq.preferred_language == "sr", (
        "server must set preferred_language='sr' (required, no DB default) (AC2)."
    )
    assert inq.property_id is None, (
        "the Contact inquiry must have property=None (Contact has no Property) (AC2)."
    )
    assert inq.ip_address is not None, (
        "create_inquiry must capture ip_address from the request (REMOTE_ADDR) (AC2)."
    )
    assert inq.name == "Marko Markovic"
    assert inq.email == "marko@example.com"
    assert inq.phone == "+381601234567"
    # follow the redirect -> 200 success marker
    follow = client.get(resp.url)
    assert follow.status_code == 200
    assert "form-success" in follow.content.decode("utf-8"), (
        "the GET after ?sent=1 must render the form-success message (PRG) (AC2)."
    )


@pytest.mark.django_db
def test_contact_post_tampering_server_fields_win(client):
    # AC2 (tampering): a POST that ALSO sends inquiry_type/status/property/
    # preferred_language must be IGNORED — the created Inquiry keeps the
    # server-set values (those are not InquiryForm fields).
    _seed_site_settings()
    other = _make_property(title="Tamper Meta")
    Inquiry = _get_model("inquiries", "Inquiry")
    data = _valid_post_data(
        inquiry_type="viewing",
        status="closed",
        property=str(other.id),
        preferred_language="en",
    )
    resp = client.post(_contact_path(), data=data)
    assert resp.status_code == 302, "a (tampered) valid POST still PRG-redirects (AC2)."
    assert _inquiry_count() == 1, "exactly one Inquiry created on a tampered POST (AC2)."
    inq = Inquiry.objects.get()
    assert inq.inquiry_type == "general", (
        "client-supplied inquiry_type must be IGNORED (server sets 'general') (AC2)."
    )
    assert inq.status == "new", (
        "client-supplied status must be IGNORED (server sets 'new') (AC2)."
    )
    assert inq.preferred_language == "sr", (
        "client-supplied preferred_language must be IGNORED (server sets 'sr') (AC2)."
    )
    assert inq.property_id is None, (
        "client-supplied property must be IGNORED (Contact sets property=None) (AC2)."
    )


@pytest.mark.django_db
def test_contact_post_csrf_enforced_403_no_row(client):
    # AC2 (CSRF): an enforce_csrf_checks client POSTing WITHOUT a token -> 403,
    # and NO Inquiry created.
    _seed_site_settings()
    csrf_client = Client(enforce_csrf_checks=True)
    resp = csrf_client.post(_contact_path(), data=_valid_post_data())
    assert resp.status_code == 403, (
        f"a POST without a CSRF token must return 403, got {resp.status_code} (AC2)."
    )
    assert _inquiry_count() == 0, (
        "a CSRF-rejected POST must create NO Inquiry (AC2)."
    )


@pytest.mark.django_db
def test_contact_post_sends_two_emails(client):
    # 5.2 (AC1/AC6 cross-cutting): a valid Contact submit now SENDS 2 emails
    # (agent notification + buyer auto-reply) via the create_inquiry hook. With
    # email_inquiries seeded the agent recipient is deterministic, so the outbox
    # has exactly 2. (Inverted in GREEN from the 4.2 no-email assertion.)
    _seed_site_settings(email_inquiries="agent@velegradestate.test")
    before = len(mail.outbox)
    resp = client.post(_contact_path(), data=_valid_post_data())
    # The submit must actually succeed (302 PRG) — proving the row was written
    # via create_inquiry — and now also send the 2 emails (5.2 hook wired).
    assert resp.status_code == 302, (
        f"a valid Contact POST must PRG-redirect (302) before the email "
        f"assertion is meaningful, got {resp.status_code} (AC2)."
    )
    assert len(mail.outbox) == before + 2, (
        "5.2 must send 2 emails (agent + auto-reply) on a valid Contact submit "
        "via the create_inquiry hook (AC1/AC6)."
    )


@pytest.mark.django_db
def test_contact_post_invalid_email_re_renders_200_no_row(client):
    # AC2: an invalid email re-renders (200) with form errors and creates NO row.
    _seed_site_settings()
    resp = client.post(_contact_path(),
                       data=_valid_post_data(email="not-an-email"))
    assert resp.status_code == 200, (
        f"an invalid POST must re-render (200), got {resp.status_code} (AC2)."
    )
    assert _inquiry_count() == 0, (
        f"an invalid email must create NO Inquiry, got {_inquiry_count()} (AC2)."
    )
    html = resp.content.decode("utf-8")
    assert "errorlist" in html, (
        "the re-rendered bound form must actually display its validation errors "
        "(Django 'errorlist') — a 200 that does not render the form would be a "
        "silent failure (AC2)."
    )


@pytest.mark.django_db
def test_contact_post_blank_message_re_renders_200_no_row(client):
    # AC2: message is REQUIRED (server wins over the design's optional textarea) —
    # a blank message re-renders 200 and creates NO row.
    _seed_site_settings()
    resp = client.post(_contact_path(),
                       data=_valid_post_data(message=""))
    assert resp.status_code == 200, (
        f"a blank message must re-render (200), got {resp.status_code} (AC2)."
    )
    assert _inquiry_count() == 0, (
        "a blank required message must create NO Inquiry (AC2)."
    )
    html = resp.content.decode("utf-8")
    assert "errorlist" in html, (
        "the re-rendered bound form must actually display its validation errors "
        "(Django 'errorlist') — a 200 that does not render the form would be a "
        "silent failure (AC2)."
    )


# =========================================================================== #
# AC3 — Anti-spam: honeypot + rate-limit                                       #
# =========================================================================== #
@pytest.mark.django_db
def test_contact_honeypot_filled_silently_rejected(client):
    # AC3 (honeypot, LOCKED): a POST with the honeypot 'website' filled (a bot)
    # returns the SAME success branch (302 -> ?sent=1) so the bot sees "success" —
    # but NO Inquiry is created.
    _seed_site_settings()
    resp = client.post(_contact_path(),
                       data=_valid_post_data(website="http://spam.example"))
    assert resp.status_code == 302, (
        "a honeypot-filled POST must return the SAME success branch (302) as a "
        f"real submit (so the bot sees 'success'), got {resp.status_code} (AC3)."
    )
    assert "sent=1" in resp.url, (
        "the honeypot success branch must redirect to ?sent=1 (same as a real "
        f"submit), got {resp.url!r} (AC3)."
    )
    assert _inquiry_count() == 0, (
        f"a honeypot-filled POST must create NO Inquiry (silently rejected), got "
        f"{_inquiry_count()} (AC3)."
    )


@override_settings(RATELIMIT_ENABLE=True)
@pytest.mark.django_db
def test_contact_rate_limit_blocks_sixth_post_with_403(client):
    # AC3 (rate-limit, NFR-5 — django-ratelimit @ratelimit(key="ip", rate="5/h",
    # method="POST", block=True)): with RATELIMIT_ENABLE=True and a cleared cache,
    # 6 rapid POSTs from the SAME IP -> the 6th is deterministically blocked with
    # HTTP 403 (block=True -> Ratelimited -> 403), and no more than 5 rows are
    # created (the over-limit POST writes nothing).
    #
    # NOTE: django-ratelimit may not be installed in the venv yet (RED phase —
    # Dev installs it in GREEN). At RED this test errors/fails on the missing
    # route / package; that is the expected RED state.
    _seed_site_settings()
    # Clear the `default` LocMemCache alias django-ratelimit uses, both BEFORE
    # (so a prior test's counter does not pre-trip us) and AFTER (so our 5 hits
    # do not leak into a later test sharing the in-process cache) — isolation.
    cache.clear()
    try:
        statuses = []
        for _ in range(6):
            resp = client.post(_contact_path(), data=_valid_post_data(),
                               REMOTE_ADDR="203.0.113.7")
            statuses.append(resp.status_code)
        # The FIRST 5 (= the 5/h limit) must be ALLOWED (302 PRG) — this guards
        # against a vacuous pass where a misconfigured limit blocks EVERYTHING
        # (which would also satisfy "the 6th is 403" + "rows <= 5").
        assert statuses[:5] == [302, 302, 302, 302, 302], (
            f"the first 5 POSTs from the same IP (within the 5/h limit) must be "
            f"ALLOWED (302 PRG); got status sequence {statuses} (AC3)."
        )
        assert statuses[-1] == 403, (
            f"the 6th rapid POST from the same IP must be rate-limited with HTTP "
            f"403 (block=True -> Ratelimited -> 403, deterministic); got status "
            f"sequence {statuses} (AC3)."
        )
        assert _inquiry_count() == 5, (
            f"exactly the 5/h limit of Inquiry rows may be created — the 5 allowed "
            f"POSTs write a row each and the over-limit 6th writes nothing; got "
            f"{_inquiry_count()} (AC3)."
        )
    finally:
        cache.clear()


def test_test_settings_disable_ratelimit():
    # AC3 (anti-flaky): the default test suite has RATELIMIT_ENABLE = False so the
    # functional AC1/AC2 tests (multiple POSTs) never trip the in-process
    # LocMemCache rate limit. The dedicated rate-limit test re-enables it.
    assert getattr(settings, "RATELIMIT_ENABLE", None) is False, (
        "config/settings/test.py must set RATELIMIT_ENABLE = False (anti-flaky — "
        "the default suite must not trip the rate limit) (AC3)."
    )


def test_django_ratelimit_in_installed_apps():
    # AC3 / AC6 (config): django-ratelimit 4.x requires 'django_ratelimit' in
    # INSTALLED_APPS for `manage.py check` to pass (system checks). The view's
    # @ratelimit decorator also depends on the package being importable.
    assert "django_ratelimit" in settings.INSTALLED_APPS, (
        "'django_ratelimit' must be added to INSTALLED_APPS (django-ratelimit 4.x "
        "system checks; needed for `manage.py check`) (AC3/AC6)."
    )


# =========================================================================== #
# AC4 — Direct one-click contact from SiteSettings                             #
# =========================================================================== #
@pytest.mark.django_db
def test_contact_direct_renders_all_channels_from_site_settings(client):
    # AC4: a fully-seeded SiteSettings renders the contact-direct column with
    # tel:/wa.me/mailto:/address, and the WhatsApp link carries target="_blank" +
    # rel="noopener".
    _seed_site_settings()
    resp, html = _get_contact(client)
    assert resp.status_code == 200
    assert 'class="contact-direct"' in html, "the contact-direct column must render (AC4)."
    assert f'href="tel:{PHONE}"' in html, (
        f"the direct contact must render href=\"tel:{PHONE}\" (one-click call) (AC4)."
    )
    assert f'href="https://wa.me/{WHATSAPP}"' in html, (
        f"the direct contact must render href=\"https://wa.me/{WHATSAPP}\" (AC4)."
    )
    assert f'href="mailto:{EMAIL}"' in html, (
        f"the direct contact must render href=\"mailto:{EMAIL}\" (AC4)."
    )
    assert ADDRESS in html, (
        f"the direct contact must render the seeded address {ADDRESS!r} (AC4)."
    )
    # The WhatsApp anchor must carry the external-link hardening attributes.
    wa_idx = html.find(f"wa.me/{WHATSAPP}")
    tag_start = html.rfind("<a", 0, wa_idx)
    tag_end = html.find(">", wa_idx)
    wa_tag = html[tag_start:tag_end + 1]
    assert 'target="_blank"' in wa_tag, (
        "the WhatsApp link must carry target=\"_blank\" (AC4)."
    )
    assert "noopener" in wa_tag, (
        "the WhatsApp link must carry rel=\"noopener\" (AC4)."
    )


@pytest.mark.django_db
def test_contact_direct_gating_omits_empty_channels(client):
    # AC4 (gating): a fully-blank SiteSettings still renders 200 and the {% if %}
    # guards OMIT every empty tel:/wa.me link (no broken href="tel:" / "wa.me/"
    # with an empty value, no "None").
    _blank_site_settings()
    resp, html = _get_contact(client)
    assert resp.status_code == 200, (
        "GET /contact/ with a blank SiteSettings must still return 200 (the "
        f"{{% if %}} guards prevent a 500), got {resp.status_code} (AC4)."
    )
    assert 'href="tel:"' not in html, (
        "with a blank phone_primary the {% if %} guard must OMIT the empty "
        "href=\"tel:\" link (AC4)."
    )
    assert 'href="https://wa.me/"' not in html, (
        "with a blank whatsapp_number the {% if %} guard must OMIT the empty "
        "href=\"https://wa.me/\" link (AC4)."
    )
    assert 'href="mailto:"' not in html, (
        "with a blank email_primary the {% if %} guard must OMIT the empty "
        "href=\"mailto:\" link (AC4)."
    )
    assert 'class="contact-direct__address"' not in html, (
        "with a blank address the {% if %} guard must OMIT the "
        "contact-direct__address element entirely (no empty address block) (AC4)."
    )


@pytest.mark.django_db
def test_contact_direct_site_settings_fields_are_escaped_no_xss(client):
    # AC4/AC5 (XSS guard, "no |safe on contact fields" invariant): a SiteSettings
    # contact field carrying a <script> payload must render HTML-ESCAPED
    # (&lt;script&gt;), NEVER as a raw executable <script> tag. This guards against
    # a future regression adding |safe to a site_settings contact field.
    payload = "<script>alert(1)</script>"
    _seed_site_settings(phone_primary=payload, address=payload)
    resp, html = _get_contact(client)
    assert resp.status_code == 200
    assert payload not in html, (
        "a SiteSettings contact field must NOT render as a raw <script> (XSS) — "
        "no |safe on contact fields (AC4/AC5)."
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html, (
        "a SiteSettings contact field carrying a <script> payload must be "
        "HTML-escaped (&lt;script&gt;) via {{ }} auto-escape (AC4/AC5)."
    )


# =========================================================================== #
# AC5 — i18n boundary + XSS auto-escape + route                                #
# =========================================================================== #
def test_contact_route_reverses_to_expected_path():
    # AC5: reverse("contact") == "/contact/".
    url = _try_reverse("contact")
    assert url == "/contact/", (
        f"reverse('contact') must equal '/contact/', got {url!r} (AC5)."
    )


@pytest.mark.django_db
def test_en_contact_route_is_404(client):
    # AC5 (i18n boundary): there is NO i18n_patterns / /en/ prefix (Epik 6) ->
    # GET /en/contact/ must be 404.
    resp = client.get("/en/contact/")
    assert resp.status_code == 404, (
        f"GET /en/contact/ must be 404 (no i18n routing in 4.2), got "
        f"{resp.status_code} (AC5)."
    )


@pytest.mark.django_db
def test_contact_invalid_post_escapes_script_in_name(client):
    # AC5 (XSS): a bound re-render after an invalid POST must HTML-escape the
    # user-supplied name (no |safe on form values) — a <script> payload appears as
    # &lt;script&gt;, NOT raw, and NO row is created.
    _seed_site_settings()
    resp = client.post(
        _contact_path(),
        data=_valid_post_data(name="<script>alert(1)</script>", email=""),
    )
    assert resp.status_code == 200, (
        f"an invalid POST must re-render (200), got {resp.status_code} (AC5)."
    )
    html = resp.content.decode("utf-8")
    assert "<script>alert(1)</script>" not in html, (
        "the user-supplied name must NOT render as a raw <script> (XSS) (AC5)."
    )
    assert "&lt;script&gt;" in html, (
        "the user-supplied name must be HTML-escaped (&lt;script&gt;) — no |safe "
        "on form values (AC5)."
    )
    assert _inquiry_count() == 0, (
        "an invalid POST must create NO Inquiry (AC5)."
    )


@pytest.mark.django_db
def test_contact_renders_sr_trans_labels(client):
    # AC5 (i18n): the SR {% trans %}-rendered UI labels appear (active language is
    # SR). The field labels prove the {% trans %} skeleton rendered.
    _seed_site_settings()
    resp, html = _get_contact(client)
    assert resp.status_code == 200
    assert "Ime i prezime" in html, (
        "the SR label 'Ime i prezime' (name) must render via {% trans %} (AC5)."
    )
    assert "Telefon" in html, (
        "the SR label 'Telefon' (phone) must render via {% trans %} (AC5)."
    )
    assert "Poruka" in html, (
        "the SR label 'Poruka' (message) must render via {% trans %} (AC5)."
    )


# =========================================================================== #
# AC6 — Regression (routes, render, existing pages/admin still green)          #
# =========================================================================== #
def test_manage_py_check_passes():
    # AC6: `manage.py check` runs clean after the view/template/url/settings
    # changes (incl. django-ratelimit system checks — a HARD gate).
    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc} (AC6)")


@pytest.mark.django_db
def test_home_still_returns_200(client):
    # AC6 (2.2 regression): GET / still returns 200.
    _seed_site_settings()
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / (Home) must still return 200, got {resp.status_code} (AC6 regression)."
    )


@pytest.mark.django_db
def test_listing_still_returns_200(client):
    # AC6 (3.1 regression): GET /properties/ listing still 200.
    _seed_site_settings()
    _make_property(title="Listing Regresija", status="for_sale")
    resp = client.get("/properties/")
    assert resp.status_code == 200, (
        f"GET /properties/ (listing) must still return 200, got "
        f"{resp.status_code} (AC6 regression)."
    )


@pytest.mark.django_db
def test_property_detail_still_returns_200(client):
    # AC6 (3.2 regression): a seeded active /properties/<slug>/ still 200.
    _seed_site_settings()
    prop = _make_property(title="Detalj Regresija", is_active=True)
    resp = client.get(f"/properties/{prop.slug}/")
    assert resp.status_code == 200, (
        f"GET /properties/{prop.slug}/ must still return 200, got "
        f"{resp.status_code} (AC6 regression)."
    )


@pytest.mark.django_db
def test_about_and_international_still_return_200(client):
    # AC6 (4.1 regression): seeded /about/ and /international/ still 200, and their
    # hardcoded /contact/ CTA now points at a LIVE route (no longer 404).
    _seed_site_settings()
    _seed_page("about", "O nama")
    _seed_page("international", "Medjunarodni klijenti")
    resp_about = client.get("/about/")
    assert resp_about.status_code == 200, (
        f"GET /about/ must still return 200, got {resp_about.status_code} (AC6)."
    )
    resp_intl = client.get("/international/")
    assert resp_intl.status_code == 200, (
        f"GET /international/ must still return 200, got {resp_intl.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_contact_route_now_200_not_404(client):
    # AC6: GET /contact/ is now 200 (4.2 revives the route the 4.1 guard test
    # asserted was 404). This is the deliberate inversion of the 4.1
    # test_contact_route_still_404 guard (Dev updates that 4.1 test in GREEN — T5).
    _seed_site_settings()
    resp = client.get("/contact/")
    assert resp.status_code == 200, (
        f"GET /contact/ must now return 200 (4.2 revives the route), got "
        f"{resp.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_admin_index_still_200_for_superuser(client, django_user_model):
    # AC6 (1.3 regression): the branded admin index still returns 200.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index at {_admin_index_path()} must still return 200 (AC6 regression)."
    )


@pytest.mark.django_db
def test_default_admin_path_still_404(client):
    # AC6 (1.3 regression): GET /admin/ stays 404 (admin mounts on ADMIN_URL).
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must still return 404, got {resp.status_code} (AC6 regression)."
    )


@pytest.mark.django_db
def test_no_root_catch_all_unknown_slug_404(client):
    # AC6: a non-existent root path -> 404 (proving there is NO root catch-all
    # path("<slug>/") added alongside the /contact/ route).
    _seed_site_settings()
    resp = client.get("/nepostojeci-slug/")
    assert resp.status_code == 404, (
        "a non-existent root path must return 404 (no root catch-all), got "
        f"{resp.status_code} (AC6)."
    )
