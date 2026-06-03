# -*- coding: utf-8 -*-
"""
RED-phase contract tests for Story 5.2 — "Inquiry pipeline — čuvanje,
notifikacija agentu, auto-reply kupcu, anti-spam".

These tests define the CONTRACT for the EMAIL PIPELINE that closes FR28. Three of
four FR28 components already ship (DB write via create_inquiry from 3.2/4.2/5.1,
and anti-spam: CSRF + honeypot + @ratelimit). 5.2 adds the ONLY remaining part —
two email flows hooked INSIDE create_inquiry (after inquiry.save()):

  (1) notify_agent(inquiry, request=...)   -> SiteSettings.email_inquiries
      (fallback email_primary; skip if both blank), with all inquiry data + an
      ABSOLUTE admin link built via reverse("admin:inquiries_inquiry_change",
      args=[inquiry.pk]) + request.build_absolute_uri;
  (2) send_auto_reply(inquiry)             -> inquiry.email, an
      EmailMultiAlternatives (plain body + a text/html alternative), branded;

orchestrated by send_inquiry_notifications(inquiry, request=...) — each flow in
its OWN try/except (per-flow non-fatal), the whole call non-fatal to the form
submit. create_inquiry calls it after inquiry.save() (local import to avoid a
circular import); the form POST stays a 302 PRG even if mail raises.

They are written BEFORE the feature is built, so EVERY 5.2 contract test in this
module MUST FAIL/ERROR until the Dev implements (GREEN phase):

  * inquiries/emails.py (notify_agent / send_auto_reply / send_inquiry_notifications);
  * the create_inquiry hook after inquiry.save();
  * config/settings/* email backends (base DEFAULT_FROM_EMAIL + 'anymail' in
    INSTALLED_APPS; dev console; test LOCMEM so mail.outbox is populated; prod
    anymail Mailgun from env);
  * BASE_DIR/templates/email/{agent_notification,auto_reply}.{html,txt}.

Design / locked rules (mirrors the 4.2 / 5.1 harness):
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite + LOCMEM
    email backend -> django.core.mail.outbox is populated).
  * Email is sent for ALL inquiry types through ONE seam (create_inquiry) — the
    three views (PropertyDetailView/ContactView/PrivateCollectionView) get email
    without any view change.
  * The agent notification recipient is SiteSettings.email_inquiries (fallback
    email_primary). To make the message count a DETERMINISTIC 2, these tests SEED
    email_inquiries="agent@velegradestate.test" before every send-asserting POST.
  * Sending is NON-FATAL: a mail exception must not 500 the form submit. The two
    flows are isolated (one failing does not suppress the other).
  * TEA does NOT edit the 3 existing test files (test_property_detail.py /
    test_contact_page.py / test_private_collection.py) — the Dev inverts their
    mail.outbox==0 assertions in GREEN (AC6 cross-cutting).
  * Each test maps to an acceptance criterion via an `# ACN:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    5-2-inquiry-pipeline-cuvanje-notifikacija-auto-reply-anti-spam-interface-contract.md
"""
import importlib
import pathlib

import pytest
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import NoReverseMatch, reverse


# --------------------------------------------------------------------------- #
# Model / path helpers — mirror tests/test_contact_page.py + test_private_*    #
# --------------------------------------------------------------------------- #
def _get_model(app_label, class_name):
    module = importlib.import_module(f"{app_label}.models")
    return getattr(module, class_name)


def _try_reverse(name, **kwargs):
    """reverse(name) or None if the route does not exist yet (RED phase)."""
    try:
        return reverse(name, **kwargs)
    except NoReverseMatch:
        return None


def _contact_path():
    return _try_reverse("contact") or "/contact/"


def _pc_path():
    return _try_reverse("private-collection") or "/private-collection/"


def _detail_path(slug):
    return f"/properties/{slug}/"


# The dedicated agent-notification inbox (AC2 recipient). Distinct from
# email_primary so a `to == [...]` assert proves the EXACT field was used.
AGENT_INBOX = "agent@velegradestate.test"
PRIMARY_EMAIL = "kontakt@velegradestate.test"
BUYER_EMAIL = "marko@example.com"
BUYER_NAME = "Marko Markovic"

# LOCKED PrivateCollectionForm ChoiceField labels (value == label, en-dash).
PC_PROPERTY_TYPE = "Stan"
PC_BUDGET = "€500.000 – €1.000.000"


def _seed_site_settings(**overrides):
    """Load the singleton and SEED email_inquiries (the AC2 notification
    recipient). Pass email_inquiries="" / email_primary="" via overrides to
    exercise the fallback / skip branches (AC2)."""
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.email_inquiries = AGENT_INBOX
    obj.email_primary = PRIMARY_EMAIL
    obj.phone_primary = "+381601234567"
    obj.whatsapp_number = "381601234567"
    obj.hero_image = ""
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _inquiry_count():
    return _get_model("inquiries", "Inquiry").objects.count()


def _make_property(**overrides):
    """Minimal active Property for the viewing (/properties/<slug>/) flow."""
    Property = _get_model("properties", "Property")
    defaults = dict(
        title="Penthouse Email Pipeline",
        status="for_sale",
        collection_type="signature",
        property_type="penthouse",
        location_city="Beograd",
        location_district="Dedinje",
        area_sqm="285.00",
        area_total_sqm="330.00",
        bedrooms=4,
        bathrooms=3,
        floor=6,
        total_floors=6,
        parking_spaces=2,
        year_built=2024,
        price="1250000.00",
        description_sr="<p>Opis</p>",
        description_en="<p>Description</p>",
        hero_image="",
        is_featured=False,
        is_active=True,
    )
    defaults.update(overrides)
    return Property.objects.create(**defaults)


def _viewing_post_data(**overrides):
    """The 4 InquiryForm fields + empty honeypot (viewing -> Property Detail)."""
    data = dict(
        name=BUYER_NAME,
        email=BUYER_EMAIL,
        phone="+381601234567",
        message="Zainteresovan sam za razgledanje.",
        website="",
    )
    data.update(overrides)
    return data


def _general_post_data(**overrides):
    """The 4 InquiryForm fields + empty honeypot (general -> Contact)."""
    data = dict(
        name=BUYER_NAME,
        email=BUYER_EMAIL,
        phone="+381601234567",
        message="Zelim da stupim u kontakt sa savetnikom.",
        website="",
    )
    data.update(overrides)
    return data


def _pc_post_data(**overrides):
    """The 5 PrivateCollectionForm fields + empty honeypot (private_collection)."""
    data = dict(
        name=BUYER_NAME,
        email=BUYER_EMAIL,
        phone="+381601234567",
        property_type_wanted=PC_PROPERTY_TYPE,
        budget_range=PC_BUDGET,
        website="",
    )
    data.update(overrides)
    return data


def _agent_message(outbox):
    """Return the first outbox message addressed to the AGENT_INBOX (or None)."""
    for msg in outbox:
        if AGENT_INBOX in msg.to:
            return msg
    return None


def _buyer_message(outbox):
    """Return the first outbox message addressed to the buyer (or None)."""
    for msg in outbox:
        if BUYER_EMAIL in msg.to:
            return msg
    return None


# =========================================================================== #
# AC1 — A valid POST for EACH inquiry type sends EXACTLY 2 emails               #
#       (agent notification + buyer auto-reply) via the ONE create_inquiry seam #
# =========================================================================== #
@pytest.mark.django_db
def test_viewing_post_creates_inquiry_and_sends_two_emails(client):
    # AC1: a valid viewing POST (/properties/<slug>/) with email_inquiries seeded
    # -> Inquiry.count() +1 AND exactly 2 emails (agent + auto-reply).
    _seed_site_settings()
    prop = _make_property()
    assert _inquiry_count() == 0
    resp = client.post(_detail_path(prop.slug), data=_viewing_post_data())
    assert resp.status_code == 302, (
        f"a valid viewing POST must PRG-redirect (302), got {resp.status_code} (AC1)."
    )
    assert _inquiry_count() == 1, (
        f"a valid viewing POST must create exactly ONE Inquiry, got "
        f"{_inquiry_count()} (AC1)."
    )
    assert len(mail.outbox) == 2, (
        f"a valid viewing POST must send EXACTLY 2 emails (agent notification + "
        f"buyer auto-reply) via the create_inquiry hook, got {len(mail.outbox)} (AC1)."
    )


@pytest.mark.django_db
def test_general_post_creates_inquiry_and_sends_two_emails(client):
    # AC1: a valid general POST (/contact/) with email_inquiries seeded -> +1 row
    # AND exactly 2 emails.
    _seed_site_settings()
    assert _inquiry_count() == 0
    resp = client.post(_contact_path(), data=_general_post_data())
    assert resp.status_code == 302, (
        f"a valid Contact POST must PRG-redirect (302), got {resp.status_code} (AC1)."
    )
    assert _inquiry_count() == 1, (
        f"a valid Contact POST must create exactly ONE Inquiry, got "
        f"{_inquiry_count()} (AC1)."
    )
    assert len(mail.outbox) == 2, (
        f"a valid general POST must send EXACTLY 2 emails (agent + auto-reply), got "
        f"{len(mail.outbox)} (AC1)."
    )


@pytest.mark.django_db
def test_private_collection_post_creates_inquiry_and_sends_two_emails(client):
    # AC1: a valid private_collection POST (/private-collection/) with
    # email_inquiries seeded -> +1 row AND exactly 2 emails.
    _seed_site_settings()
    assert _inquiry_count() == 0
    resp = client.post(_pc_path(), data=_pc_post_data())
    assert resp.status_code == 302, (
        f"a valid Private Collection POST must PRG-redirect (302), got "
        f"{resp.status_code} (AC1)."
    )
    assert _inquiry_count() == 1, (
        f"a valid Private Collection POST must create exactly ONE Inquiry, got "
        f"{_inquiry_count()} (AC1)."
    )
    assert len(mail.outbox) == 2, (
        f"a valid private_collection POST must send EXACTLY 2 emails (agent + "
        f"auto-reply), got {len(mail.outbox)} (AC1)."
    )


@pytest.mark.django_db
def test_email_pipeline_hooked_in_create_inquiry_directly(client):
    # AC1: the pipeline is hooked INSIDE create_inquiry (not in a view) — calling
    # create_inquiry directly with a validated form sends the same 2 emails. This
    # proves all three views get email WITHOUT any view change.
    _seed_site_settings()
    services = importlib.import_module("inquiries.services")
    forms_mod = importlib.import_module("inquiries.forms")
    form = forms_mod.InquiryForm(_general_post_data())
    assert form.is_valid(), f"the helper form data must be valid, got {form.errors!r}."
    inquiry = services.create_inquiry(
        form=form, property=None, inquiry_type="general", request=None
    )
    assert inquiry.pk is not None, "create_inquiry must return a SAVED Inquiry (AC1)."
    assert len(mail.outbox) == 2, (
        f"create_inquiry must send 2 emails (agent + auto-reply) after "
        f"inquiry.save(), got {len(mail.outbox)} (AC1)."
    )


# =========================================================================== #
# AC2 — Agent notification: to == [email_inquiries], data + ABSOLUTE admin link #
#       fallback to email_primary; skip when both blank                        #
# =========================================================================== #
@pytest.mark.django_db
def test_agent_notification_addressed_to_email_inquiries(client):
    # AC2: among the outbox, exactly one message is addressed to email_inquiries
    # (the dedicated agent inbox), NOT email_primary.
    _seed_site_settings()
    client.post(_contact_path(), data=_general_post_data())
    agent = _agent_message(mail.outbox)
    assert agent is not None, (
        f"there must be a notification addressed to email_inquiries "
        f"({AGENT_INBOX!r}); outbox recipients were "
        f"{[m.to for m in mail.outbox]} (AC2)."
    )
    assert agent.to == [AGENT_INBOX], (
        f"the agent notification 'to' must be exactly [{AGENT_INBOX!r}], got "
        f"{agent.to!r} (AC2)."
    )


@pytest.mark.django_db
def test_agent_notification_subject_and_body_contain_inquiry_data(client):
    # AC2: the agent notification subject/body carries the sender name and a
    # recognizable inquiry type (general -> "Opšte" display label).
    _seed_site_settings()
    client.post(_contact_path(), data=_general_post_data())
    agent = _agent_message(mail.outbox)
    assert agent is not None, "the agent notification must be sent (AC2)."
    haystack = agent.subject + "\n" + agent.body
    assert BUYER_NAME in haystack, (
        f"the agent notification subject/body must contain the sender name "
        f"{BUYER_NAME!r}; subject={agent.subject!r} (AC2)."
    )
    assert "Opšte" in haystack, (
        f"the agent notification subject/body must contain the readable inquiry "
        f"type label (general -> 'Opšte'); subject={agent.subject!r} (AC2)."
    )


@pytest.mark.django_db
def test_agent_notification_contains_absolute_admin_link(client):
    # AC2: the notification carries a link to the admin inquiry-change page, built
    # via reverse("admin:inquiries_inquiry_change", args=[pk]) + build_absolute_uri
    # -> the content contains the "inquiries/inquiry/" path segment AND an absolute
    # URL (starts with "http"). The f-string ADMIN_URL variant is forbidden.
    _seed_site_settings()
    client.post(_contact_path(), data=_general_post_data())
    agent = _agent_message(mail.outbox)
    assert agent is not None, "the agent notification must be sent (AC2)."
    html_alts = "".join(
        content for content, mime in getattr(agent, "alternatives", [])
        if mime == "text/html"
    )
    content = agent.body + "\n" + html_alts
    assert "inquiries/inquiry/" in content, (
        "the agent notification must contain the admin change-link path segment "
        "'inquiries/inquiry/' built via reverse('admin:inquiries_inquiry_change') "
        "(NOT a broken f-string ADMIN_URL link) (AC2)."
    )
    # The reverse path is mounted under ADMIN_URL — assert the link is absolute
    # (request.build_absolute_uri produced an http(s):// URL).
    idx = content.find("inquiries/inquiry/")
    scheme_idx = content.rfind("http", 0, idx)
    assert scheme_idx != -1, (
        "the admin link must be ABSOLUTE (start with 'http', via "
        "request.build_absolute_uri) — a bare relative path means build_absolute_uri "
        "was not applied (AC2)."
    )


@pytest.mark.django_db
def test_agent_notification_from_is_default_from_email(client):
    # AC2: the notification 'from' is settings.DEFAULT_FROM_EMAIL.
    _seed_site_settings()
    client.post(_contact_path(), data=_general_post_data())
    agent = _agent_message(mail.outbox)
    assert agent is not None, "the agent notification must be sent (AC2)."
    assert agent.from_email == settings.DEFAULT_FROM_EMAIL, (
        f"the agent notification 'from' must be DEFAULT_FROM_EMAIL "
        f"({settings.DEFAULT_FROM_EMAIL!r}), got {agent.from_email!r} (AC2)."
    )


@pytest.mark.django_db
def test_agent_notification_falls_back_to_email_primary(client):
    # AC2 (fallback): with email_inquiries blank but email_primary set, the agent
    # notification is addressed to email_primary (still 2 emails total).
    _seed_site_settings(email_inquiries="", email_primary=PRIMARY_EMAIL)
    client.post(_contact_path(), data=_general_post_data())
    assert len(mail.outbox) == 2, (
        f"with email_primary set, both emails are sent (notification falls back to "
        f"email_primary + auto-reply), got {len(mail.outbox)} (AC2)."
    )
    primary_msgs = [m for m in mail.outbox if PRIMARY_EMAIL in m.to]
    assert primary_msgs, (
        f"with email_inquiries blank, the agent notification must fall back to "
        f"email_primary ({PRIMARY_EMAIL!r}); outbox recipients were "
        f"{[m.to for m in mail.outbox]} (AC2)."
    )


@pytest.mark.django_db
def test_agent_notification_skipped_when_both_recipients_blank(client):
    # AC2 (skip): with BOTH email_inquiries and email_primary blank, the agent
    # notification is skipped (no crash) — only the buyer auto-reply is sent
    # (len(mail.outbox) == 1).
    _seed_site_settings(email_inquiries="", email_primary="")
    resp = client.post(_contact_path(), data=_general_post_data())
    assert resp.status_code == 302, (
        "a valid POST with no agent recipient must still PRG-redirect (302) — the "
        "skipped notification must not crash the submit (AC2)."
    )
    assert _inquiry_count() == 1, "the Inquiry row must still be created (AC2)."
    assert len(mail.outbox) == 1, (
        f"with both agent recipients blank, only the buyer auto-reply is sent "
        f"(notification skipped), got {len(mail.outbox)} (AC2)."
    )
    assert _buyer_message(mail.outbox) is not None, (
        "the surviving message must be the buyer auto-reply (AC2)."
    )


# =========================================================================== #
# AC3 — Buyer auto-reply: EmailMultiAlternatives (plain + text/html), branded  #
# =========================================================================== #
@pytest.mark.django_db
def test_auto_reply_addressed_to_buyer(client):
    # AC3: the auto-reply 'to' is exactly [inquiry.email] and 'from' is
    # DEFAULT_FROM_EMAIL.
    _seed_site_settings()
    client.post(_contact_path(), data=_general_post_data())
    buyer = _buyer_message(mail.outbox)
    assert buyer is not None, (
        f"there must be an auto-reply addressed to the buyer ({BUYER_EMAIL!r}); "
        f"outbox recipients were {[m.to for m in mail.outbox]} (AC3)."
    )
    assert buyer.to == [BUYER_EMAIL], (
        f"the auto-reply 'to' must be exactly [{BUYER_EMAIL!r}], got {buyer.to!r} (AC3)."
    )
    assert buyer.from_email == settings.DEFAULT_FROM_EMAIL, (
        f"the auto-reply 'from' must be DEFAULT_FROM_EMAIL, got {buyer.from_email!r} (AC3)."
    )


@pytest.mark.django_db
def test_auto_reply_is_multialternatives_with_html_and_plain(client):
    # AC3: the auto-reply is an EmailMultiAlternatives with a non-empty plain-text
    # body AND a text/html alternative.
    _seed_site_settings()
    client.post(_contact_path(), data=_general_post_data())
    buyer = _buyer_message(mail.outbox)
    assert buyer is not None, "the buyer auto-reply must be sent (AC3)."
    assert buyer.body.strip(), (
        "the auto-reply must carry a non-empty plain-text body (from "
        "auto_reply.txt) (AC3)."
    )
    alternatives = getattr(buyer, "alternatives", [])
    html_alts = [c for c, mime in alternatives if mime == "text/html"]
    assert html_alts, (
        f"the auto-reply must be an EmailMultiAlternatives with a text/html "
        f"alternative (.attach_alternative(html, 'text/html')); alternatives were "
        f"{alternatives!r} (AC3)."
    )


@pytest.mark.django_db
def test_auto_reply_html_is_branded(client):
    # AC3: the HTML alternative is branded — it contains the brand marker
    # "Velegrad" and a recognizable Serbian phrase ("Hvala").
    _seed_site_settings()
    client.post(_contact_path(), data=_general_post_data())
    buyer = _buyer_message(mail.outbox)
    assert buyer is not None, "the buyer auto-reply must be sent (AC3)."
    html = "".join(
        c for c, mime in getattr(buyer, "alternatives", []) if mime == "text/html"
    )
    assert "Velegrad" in html, (
        "the auto-reply HTML must contain the brand marker 'Velegrad' (AC3)."
    )
    full = buyer.subject + "\n" + buyer.body + "\n" + html
    assert "Hvala" in full, (
        "the auto-reply must contain a branded Serbian phrase like 'Hvala' "
        "(thank-you / confirmation tone) (AC3)."
    )


@pytest.mark.django_db
def test_auto_reply_html_escapes_user_name_no_xss(client):
    # AC3 (XSS): a name="<script>alert(1)</script>" must render HTML-ESCAPED in the
    # auto-reply HTML alternative (&lt;script&gt;), NEVER as a raw <script> tag
    # (no |safe on user input — {{ }} auto-escape).
    _seed_site_settings()
    payload = "<script>alert(1)</script>"
    client.post(_contact_path(), data=_general_post_data(name=payload))
    buyer = _buyer_message(mail.outbox)
    assert buyer is not None, "the buyer auto-reply must be sent (AC3)."
    html = "".join(
        c for c, mime in getattr(buyer, "alternatives", []) if mime == "text/html"
    )
    assert payload not in html, (
        "the user-supplied name must NOT render as a raw <script> in the auto-reply "
        "HTML (XSS) — no |safe on user input (AC3)."
    )
    assert "&lt;script&gt;" in html, (
        "the user-supplied name carrying a <script> payload must be HTML-escaped "
        "(&lt;script&gt;) via {{ }} auto-escape (AC3)."
    )


# =========================================================================== #
# AC4 — Backend per environment + no hardcoded credentials                     #
# =========================================================================== #
def test_test_settings_use_locmem_email_backend():
    # AC4: config.settings.test must set EMAIL_BACKEND to LOCMEM so mail.outbox is
    # populated (NOT console, which prints but leaves the outbox empty).
    #
    # NOTE: pytest-django itself FORCES a locmem backend at runtime regardless of
    # what test.py declares, so asserting settings.EMAIL_BACKEND alone would be a
    # permanent false-green (it would pass before the Dev edits test.py). We keep
    # the runtime invariant assert (it guards what AC1-AC3 actually rely on) AND
    # additionally assert the test.py SOURCE declares locmem, so this test gives a
    # real RED signal until T2 adds the line.
    assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend", (
        "the active EMAIL_BACKEND must be the locmem backend so mail.outbox works "
        f"(AC1-AC3 depend on it); got {settings.EMAIL_BACKEND!r} (AC4)."
    )
    test_src = (
        pathlib.Path(settings.BASE_DIR) / "config" / "settings" / "test.py"
    ).read_text(encoding="utf-8")
    assert "django.core.mail.backends.locmem.EmailBackend" in test_src, (
        "config/settings/test.py must EXPLICITLY set "
        'EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend" (AC4) — '
        "do not rely on pytest-django's implicit override."
    )


def test_default_from_email_is_set():
    # AC4: DEFAULT_FROM_EMAIL is configured in base settings (env-based) — the
    # sender for both email flows. We assert it is non-empty AND that base.py has
    # NOT left Django's built-in placeholder ("webmaster@localhost"): the latter
    # is always present, so a bare "non-empty" check would be a permanent
    # false-green. Requiring base.py to override it gives a real RED signal until
    # T2 sets DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Velegrad ...").
    value = getattr(settings, "DEFAULT_FROM_EMAIL", "")
    assert value, (
        "config/settings/base.py must set a non-empty DEFAULT_FROM_EMAIL "
        "(env-based default) — the sender for both email flows (AC4)."
    )
    assert value != "webmaster@localhost", (
        "config/settings/base.py must OVERRIDE Django's built-in placeholder "
        "DEFAULT_FROM_EMAIL ('webmaster@localhost') with the env-based brand "
        "sender (e.g. 'Velegrad <noreply@...>') (AC4)."
    )


def test_anymail_in_installed_apps():
    # AC4 (LOCKED): 'anymail' is added to INSTALLED_APPS (documented django-anymail
    # setup; harmless in dev/test as console/locmem ignore it).
    assert "anymail" in settings.INSTALLED_APPS, (
        "'anymail' must be added to INSTALLED_APPS (LOCKED django-anymail setup) (AC4)."
    )


def test_anymail_importable():
    # AC4 (smoke): the django-anymail[mailgun] package is installed (v15.0) so the
    # prod Mailgun backend reference resolves.
    import anymail  # noqa: F401


def test_settings_have_no_hardcoded_mailgun_key():
    # AC4 (NFR-5): the config/settings/ source must not contain a literal Mailgun
    # API key — credentials come from env (env("MAILGUN_API_KEY")). We assert there
    # is no hardcoded assignment of a key literal, and that the prod module reads
    # MAILGUN_API_KEY from env.
    settings_dir = pathlib.Path(settings.BASE_DIR) / "config" / "settings"
    prod_src = (settings_dir / "prod.py").read_text(encoding="utf-8")
    base_src = (settings_dir / "base.py").read_text(encoding="utf-8")
    combined = prod_src + "\n" + base_src
    # A real Mailgun key is "key-<32 hex>". Assert no such literal is present.
    import re
    assert not re.search(r"key-[0-9a-fA-F]{16,}", combined), (
        "config/settings/ must NOT contain a hardcoded Mailgun API key — read it "
        "from env (NFR-5) (AC4)."
    )
    assert 'env("MAILGUN_API_KEY")' in prod_src or "env('MAILGUN_API_KEY')" in prod_src, (
        "config/settings/prod.py must read MAILGUN_API_KEY from env "
        "(env(\"MAILGUN_API_KEY\")) — never hardcoded (AC4)."
    )
    # Fail-fast (Dev A #4): prod must NOT mask a misconfigured Mailgun key with a
    # default="" — an empty key would pass check/startup but 401 at send time.
    # django-environ must raise ImproperlyConfigured at settings load if it is unset.
    assert not re.search(r'env\(\s*["\']MAILGUN_API_KEY["\']\s*,\s*default\s*=', prod_src), (
        "config/settings/prod.py must NOT pass default=\"\" to "
        "env(\"MAILGUN_API_KEY\") — prod must fail-fast (ImproperlyConfigured) when "
        "the key is unset, not silently 401 at send time (AC4/NFR-5)."
    )


# =========================================================================== #
# AC5 — Non-fatal sending + per-flow isolation + anti-spam regression          #
# =========================================================================== #
@pytest.mark.django_db
def test_send_failure_is_non_fatal_to_form_submit(client, monkeypatch):
    # AC5 (non-fatal): if the underlying mailer raises, the form POST still
    # returns 302 ?sent=1 and the Inquiry row is still saved (lead not lost).
    #
    # IMPORTANT (mock target vs LOCKED design): the non-fatal try/except lives
    # INSIDE send_inquiry_notifications (per-flow, interface contract §1.3) —
    # create_inquiry calls the orchestrator WITHOUT its own try/except. So we
    # must NOT replace send_inquiry_notifications itself (that would strip the
    # only try/except and let the error propagate -> 500). Instead we make the
    # LOWER layer raise (EmailMultiAlternatives.send), exactly as story T6
    # prescribes: the orchestrator's per-flow except then swallows it and the
    # submit stays a 302 PRG. This keeps the test satisfiable against the
    # locked GREEN implementation.
    _seed_site_settings()
    # Import the mailer the email module sends through and make .send() raise.
    from django.core.mail import EmailMultiAlternatives

    calls = {"n": 0}

    def _boom(*args, **kwargs):
        calls["n"] += 1
        raise RuntimeError("simulated provider outage")

    monkeypatch.setattr(EmailMultiAlternatives, "send", _boom)
    resp = client.post(_contact_path(), data=_general_post_data())
    # The hook MUST actually have fired (mailer invoked at least once) — this is
    # what makes the test RED until create_inquiry wires send_inquiry_notifications
    # after inquiry.save(); without the hook the mailer is never called.
    assert calls["n"] >= 1, (
        "create_inquiry must invoke the email pipeline after inquiry.save() — the "
        "patched mailer was never called, so the 5.2 hook is not wired (AC5)."
    )
    assert resp.status_code == 302, (
        "a mail failure must NOT 500 the submit — the POST must still PRG-redirect "
        f"(302), got {resp.status_code} (AC5)."
    )
    assert "sent=1" in resp.url, (
        f"the submit must still carry ?sent=1 despite the mail failure, got "
        f"{resp.url!r} (AC5)."
    )
    assert _inquiry_count() == 1, (
        "the Inquiry row must still be saved despite the mail failure (lead not "
        "lost — save() happens before the email hook) (AC5)."
    )


@pytest.mark.django_db
def test_per_flow_isolation_auto_reply_sent_when_notify_agent_raises(client, monkeypatch):
    # AC5 (per-flow isolation): if ONLY notify_agent raises, send_auto_reply STILL
    # runs (mail.outbox has the buyer auto-reply) AND the POST is still 302. The two
    # flows are each wrapped in their OWN try/except inside the orchestrator.
    _seed_site_settings()
    emails_mod = importlib.import_module("inquiries.emails")

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated agent-notification failure")

    monkeypatch.setattr(emails_mod, "notify_agent", _boom)
    resp = client.post(_contact_path(), data=_general_post_data())
    assert resp.status_code == 302, (
        "a failing notify_agent must not 500 the submit (per-flow non-fatal), got "
        f"{resp.status_code} (AC5)."
    )
    buyer = _buyer_message(mail.outbox)
    assert buyer is not None, (
        "send_auto_reply must STILL run when notify_agent raises (each flow in its "
        f"own try/except); outbox recipients were {[m.to for m in mail.outbox]} (AC5)."
    )
    assert buyer.to == [BUYER_EMAIL], (
        "the surviving message must be the buyer auto-reply, addressed to "
        f"inquiry.email; got {buyer.to!r} (AC5)."
    )


@pytest.mark.django_db
def test_honeypot_post_creates_no_row_and_sends_no_email(client):
    # AC5 (anti-spam regression): a honeypot-filled POST is silently dropped — NO
    # Inquiry row AND NO email (the email hook lives in create_inquiry, which the
    # honeypot branch never calls).
    _seed_site_settings()
    resp = client.post(
        _contact_path(), data=_general_post_data(website="http://spam.example")
    )
    assert resp.status_code == 302, (
        "a honeypot-filled POST must return the same success branch (302) (AC5)."
    )
    assert _inquiry_count() == 0, (
        "a honeypot-filled POST must create NO Inquiry (silently rejected) (AC5)."
    )
    assert len(mail.outbox) == 0, (
        f"a honeypot-filled POST must send NO email (no create_inquiry call), got "
        f"{len(mail.outbox)} (AC5)."
    )


@override_settings(RATELIMIT_ENABLE=True)
@pytest.mark.django_db
def test_rate_limit_blocks_sixth_post_and_caps_emails(client):
    # AC5 (anti-spam regression): with RATELIMIT_ENABLE=True and a cleared cache, 6
    # rapid POSTs from the same IP -> the 6th is blocked (403); the over-limit POST
    # writes no row and sends no email (so at most 5 rows -> at most 10 emails).
    _seed_site_settings()
    cache.clear()
    try:
        statuses = []
        for _ in range(6):
            resp = client.post(
                _contact_path(), data=_general_post_data(), REMOTE_ADDR="203.0.113.9"
            )
            statuses.append(resp.status_code)
        assert statuses[:5] == [302, 302, 302, 302, 302], (
            f"the first 5 POSTs (within the 5/h limit) must be allowed (302); got "
            f"{statuses} (AC5)."
        )
        assert statuses[-1] == 403, (
            f"the 6th rapid POST from the same IP must be rate-limited (403); got "
            f"{statuses} (AC5)."
        )
        assert _inquiry_count() == 5, (
            f"exactly 5 rows may be created (the over-limit 6th writes nothing); got "
            f"{_inquiry_count()} (AC5)."
        )
        assert len(mail.outbox) == 10, (
            f"only the 5 allowed POSTs send email (2 each = 10); the blocked 6th "
            f"sends none; got {len(mail.outbox)} (AC5)."
        )
    finally:
        cache.clear()


# =========================================================================== #
# AC6 — Cross-cutting note (TEA does NOT edit the 3 files) + an extra guard     #
# =========================================================================== #
@pytest.mark.django_db
def test_private_collection_post_with_seed_sends_two_emails(client):
    # AC6: the private_collection flow (the file whose _seed_site_settings seeds NO
    # email field) sends 2 emails ONLY when email_inquiries is seeded — this is the
    # case that would be 1 without the seed. TEA does NOT edit test_private_collection.py;
    # the Dev inverts its mail.outbox==0 assertion in GREEN.
    _seed_site_settings()
    resp = client.post(_pc_path(), data=_pc_post_data())
    assert resp.status_code == 302, (
        f"a valid private_collection POST must PRG-redirect (302), got "
        f"{resp.status_code} (AC6)."
    )
    assert len(mail.outbox) == 2, (
        f"with email_inquiries seeded, a private_collection POST sends 2 emails "
        f"(agent + auto-reply); without the seed it would be 1 — proving the "
        f"AC6 PRECONDITION, got {len(mail.outbox)} (AC6)."
    )


# =========================================================================== #
# T3 (batch-fix robustness / coverage) — non-mandatory hardening tests         #
#   added by the Dev/TEA batch-fix pass. They do NOT weaken the AC1-AC6 suite. #
# =========================================================================== #
@pytest.mark.django_db
def test_header_injection_in_name_is_non_fatal_and_row_saved(client):
    # T3 (header-injection robustness): a name carrying CR/LF + a forged "Bcc:"
    # header must NOT break the pipeline. M3 removed inquiry.name from the subject,
    # so no BadHeaderError can occur from the name anymore; the body auto-escapes
    # it. The submit must still 302 and the Inquiry row must be saved (email send
    # is non-fatal regardless). Optionally the buyer auto-reply still goes out.
    _seed_site_settings()
    malicious_name = "Foo\r\nBcc: attacker@evil.com"
    resp = client.post(_contact_path(), data=_general_post_data(name=malicious_name))
    assert resp.status_code == 302, (
        "a valid POST whose name carries CR/LF + a forged Bcc header must still "
        f"PRG-redirect (302) — the pipeline must not break, got {resp.status_code} (T3)."
    )
    assert _inquiry_count() == 1, (
        "the Inquiry row must be saved even when the name carries injection bytes "
        "(save() precedes the non-fatal email hook) (T3)."
    )
    # M3 keeps the name out of the subject, so the pipeline completes cleanly and
    # the buyer auto-reply still goes out (proving no BadHeaderError aborted it).
    buyer = _buyer_message(mail.outbox)
    assert buyer is not None, (
        "the buyer auto-reply must still be sent — a CR/LF name must not trigger "
        f"BadHeaderError now that M3 removed name from the subject; outbox recipients "
        f"were {[m.to for m in mail.outbox]} (T3)."
    )
    # And the forged header bytes must NOT have leaked into a real recipient header.
    assert "attacker@evil.com" not in (buyer.to + buyer.cc + buyer.bcc), (
        "the forged 'Bcc: attacker@evil.com' must NOT become a real recipient (T3)."
    )


@pytest.mark.django_db
def test_notify_agent_with_request_none_builds_relative_admin_path(client):
    # T3 (request=None admin link): calling create_inquiry directly with request=None
    # and email_inquiries seeded -> notify_agent uses reverse() only (no
    # build_absolute_uri), producing a RELATIVE admin path. The body must contain
    # the "inquiries/inquiry/" segment and must NOT require an http host.
    _seed_site_settings()
    services = importlib.import_module("inquiries.services")
    forms_mod = importlib.import_module("inquiries.forms")
    form = forms_mod.InquiryForm(_general_post_data())
    assert form.is_valid(), f"the helper form data must be valid, got {form.errors!r}."
    inquiry = services.create_inquiry(
        form=form, property=None, inquiry_type="general", request=None
    )
    assert inquiry.pk is not None, "create_inquiry must return a SAVED Inquiry (T3)."
    agent = _agent_message(mail.outbox)
    assert agent is not None, (
        "the agent notification must be sent even with request=None (T3)."
    )
    html_alts = "".join(
        content for content, mime in getattr(agent, "alternatives", [])
        if mime == "text/html"
    )
    content = agent.body + "\n" + html_alts
    assert "inquiries/inquiry/" in content, (
        "with request=None the admin link must still carry the reverse() path "
        "segment 'inquiries/inquiry/' (relative is fine — no build_absolute_uri) (T3)."
    )
    # The None-request branch must NOT have crashed trying to build an absolute URI;
    # the row exists and the agent message was produced, which proves it.


@pytest.mark.django_db
def test_agent_notification_content_for_viewing_includes_property(client):
    # T3 (agent-notification CONTENT — viewing): a viewing inquiry has a Property; the
    # agent email body must carry the inquiry data + a property reference.
    _seed_site_settings()
    prop = _make_property()
    client.post(_detail_path(prop.slug), data=_viewing_post_data())
    agent = _agent_message(mail.outbox)
    assert agent is not None, "the agent notification must be sent for viewing (T3)."
    html_alts = "".join(
        content for content, mime in getattr(agent, "alternatives", [])
        if mime == "text/html"
    )
    content = agent.subject + "\n" + agent.body + "\n" + html_alts
    assert BUYER_NAME in content, (
        f"the viewing agent notification must carry the sender name {BUYER_NAME!r} (T3)."
    )
    assert prop.title in content, (
        f"the viewing agent notification must reference the Property ({prop.title!r}) "
        "the inquiry is about (T3)."
    )


@pytest.mark.django_db
def test_agent_notification_content_for_private_collection_includes_wanted_fields(client):
    # T3 (agent-notification CONTENT — private_collection): the agent email must carry
    # the buyer's property_type_wanted and budget_range values.
    _seed_site_settings()
    client.post(_pc_path(), data=_pc_post_data())
    agent = _agent_message(mail.outbox)
    assert agent is not None, (
        "the agent notification must be sent for private_collection (T3)."
    )
    html_alts = "".join(
        content for content, mime in getattr(agent, "alternatives", [])
        if mime == "text/html"
    )
    content = agent.subject + "\n" + agent.body + "\n" + html_alts
    assert PC_PROPERTY_TYPE in content, (
        f"the private_collection agent notification must carry property_type_wanted "
        f"({PC_PROPERTY_TYPE!r}); content was {content!r} (T3)."
    )
    assert PC_BUDGET in content, (
        f"the private_collection agent notification must carry budget_range "
        f"({PC_BUDGET!r}); content was {content!r} (T3)."
    )
