# -*- coding: utf-8 -*-
"""
RED-phase contract tests for Story 5.1 — "Private Collection stranica i intake
forma".

These tests define the CONTRACT for the public Private Collection page at
/private-collection/ — a hero (dark background) + explanation text WITH NO
property/price/address shown (FR17 — this is NOT a listing), plus a 5-field
intake form (name/email/phone/property_type_wanted/budget_range) that writes an
Inquiry(inquiry_type="private_collection") row. They are written BEFORE the
feature is built, so EVERY 5.1 contract test in this module MUST FAIL/ERROR
until the Dev implements (GREEN phase):

  * inquiries/forms.py::PrivateCollectionForm(ModelForm) — Meta.model=Inquiry,
    Meta.fields=[name,email,phone,property_type_wanted,budget_range] + a
    NON-model honeypot `website` (required=False, NOT HiddenInput).
    property_type_wanted & budget_range are forms.ChoiceField with the LOCKED
    Serbian-label choices (stored value == readable label, e.g. "Stan",
    "€500.000 – €1.000.000"). The existing InquiryForm is UNCHANGED;
  * pages/views.py::PrivateCollectionView(View) — GET renders
    PrivateCollectionForm(); POST: filled honeypot `website` -> the SAME 302
    ?sent=1 success branch but NO row; a valid submit -> create_inquiry(
    form=form, property=None, inquiry_type="private_collection", request=request)
    then PRG 302 -> ?sent=1; invalid -> re-render 200 with bound errors. NO
    Property query (FR17). POST is rate-limited via @method_decorator(ratelimit(
    key="ip", rate="5/h", method="POST", block=True), name="post");
  * config/urls.py — EXPLICIT route path("private-collection/",
    PrivateCollectionView.as_view(), name="private-collection"), NO root
    catch-all, NO i18n_patterns;
  * templates/private-collection.html ({% extends base %} + pc-hero section--dark
    + pc-explanation (NO listing) + pc-form (5 fields + csrf + hidden honeypot +
    form-success on ?sent=1) + css/pages/private-collection.css).

Design / locked rules (mirrors the 4.2 harness — tests/test_contact_page.py):
  * DB / client tests are @pytest.mark.django_db (pytest-django via
    DJANGO_SETTINGS_MODULE = config.settings.test, in-memory SQLite).
  * 5.1 reuses the 3.2 write-seam (create_inquiry) but introduces a NEW form:
    PrivateCollectionForm.Meta.fields == [name, email, phone,
    property_type_wanted, budget_range] + a non-model honeypot `website`;
    inquiry_type/property/status/preferred_language/ip_address are set
    SERVER-SIDE in create_inquiry (never from POST -> tampering prevention).
  * Private Collection uses inquiry_type="private_collection" and property=None.
    status="new" + preferred_language="sr" + message="" come from the seam.
  * No |safe on any user field (Private Collection has no admin-curated
    HTMLField). Auto-escape is proven via name="<script>alert(1)</script>".
  * Email: 5.2 SADA šalje preko create_inquiry seam-a — kad je email_inquiries
    seed-ovan, jedan validan private_collection POST pošalje 2 mejla (agent +
    auto-reply). Ovi testovi su već invertovani da to potvrde (ne više
    mail.outbox == 0).
  * The rate-limit decorator / django-ratelimit infra is already installed
    (4.2). RATELIMIT_ENABLE=False in test settings keeps the functional tests
    from tripping; the dedicated rate-limit test re-enables it.
  * Each test maps to an acceptance criterion via an `# ACN:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    5-1-private-collection-stranica-i-intake-forma-interface-contract.md
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
# Model / path helpers — mirror tests/test_contact_page.py + test_home_page    #
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


def _pc_path():
    """The private-collection route path (live in GREEN). Fall back to the
    locked literal so the GET/POST tests still exercise the URL string in RED
    (404 there)."""
    return _try_reverse("private-collection") or "/private-collection/"


def _seed_site_settings(**overrides):
    """Load the SiteSettings singleton (base.html footer reads site_settings via
    the 2.2 context processor — keep a row present so the page renders)."""
    SiteSettings = _get_model("core", "SiteSettings")
    obj = SiteSettings.load()
    obj.hero_image = ""
    obj.founder_photo = ""
    for key, value in overrides.items():
        setattr(obj, key, value)
    obj.save()
    return obj


# LOCKED choice literals — copied VERBATIM from the story's CHOICES LITERAL (T1).
# The select stores the readable Serbian label as the value (value == label).
# NOTE the en-dash (–, U+2013) in the budget ranges — POST values MUST match the
# form's allowed ChoiceField choices exactly or the bound form rejects them.
PROPERTY_TYPE_VALUE = "Stan"
BUDGET_VALUE = "€500.000 – €1.000.000"


def _valid_post_data(**overrides):
    """The 5 user fields + an empty honeypot. property_type_wanted/budget_range
    MUST be one of the LOCKED ChoiceField labels or the form rejects them."""
    data = dict(
        name="Marko Markovic",
        email="marko@example.com",
        phone="+381601234567",
        property_type_wanted=PROPERTY_TYPE_VALUE,
        budget_range=BUDGET_VALUE,
        website="",  # honeypot empty -> a real (human) submit
    )
    data.update(overrides)
    return data


def _inquiry_count():
    return _get_model("inquiries", "Inquiry").objects.count()


def _get_pc(client, query=""):
    url = _pc_path()
    if query:
        url = url + "?" + query.lstrip("?")
    resp = client.get(url)
    return resp, resp.content.decode("utf-8")


def _make_property(**overrides):
    """Minimal active Property for the /properties/<slug>/ regression (AC6) and
    the tampering POST (property=<id>) (AC3)."""
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
# AC1 — Private Collection /private-collection/ 200, hero+explanation, NO       #
#       properties shown (FR17 anti-listing)                                   #
# =========================================================================== #
@pytest.mark.django_db
def test_private_collection_returns_200_and_uses_template_extending_base(client):
    # AC1: GET /private-collection/ -> 200, renders private-collection.html which
    # extends base.html (site-header + site-footer), and loads the page CSS.
    _seed_site_settings()
    resp, html = _get_pc(client)
    assert resp.status_code == 200, (
        f"GET /private-collection/ must return 200, got {resp.status_code} (AC1)."
    )
    template_names = [getattr(t, "name", None) for t in resp.templates]
    assert "private-collection.html" in template_names, (
        f"the page must render 'private-collection.html', got {template_names} (AC1)."
    )
    assert "site-header" in html and "site-footer" in html, (
        "private-collection.html must extend base.html (site-header + "
        "site-footer) (AC1)."
    )
    assert "css/pages/private-collection.css" in html, (
        "private-collection.html must load css/pages/private-collection.css via "
        "{% block extra_css %} (AC1)."
    )


@pytest.mark.django_db
def test_private_collection_renders_dark_hero_and_explanation(client):
    # AC1: the pc-hero (dark background) + pc-explanation design sections render,
    # with the SR title "Privatna kolekcija".
    _seed_site_settings()
    resp, html = _get_pc(client)
    assert resp.status_code == 200
    assert "pc-hero" in html, "the pc-hero section must render (AC1)."
    assert "section--dark" in html, (
        "the hero must carry the section--dark (dark background) class (AC1, FR17)."
    )
    assert "Privatna kolekcija" in html, (
        "the hero <h1> must render the SR title 'Privatna kolekcija' (AC1)."
    )
    assert "pc-explanation" in html, (
        "the pc-explanation (off-market concept) section must render (AC1)."
    )


@pytest.mark.django_db
def test_private_collection_shows_no_properties_anti_listing(client):
    # AC1 (FR17 — KRITIČNA invarijanta): the Private Collection page is NOT a
    # listing — it renders NO property/price/address. The listing markers
    # (property-card / listing-grid) must be ABSENT from the HTML.
    _seed_site_settings()
    # Even with active properties in the DB, the page must NOT list any (the view
    # makes no Property query — FR17).
    _make_property(title="Off Market Tajna", collection_type="private")
    _make_property(title="Signature Vidljiv", collection_type="signature")
    resp, html = _get_pc(client)
    assert resp.status_code == 200
    assert "property-card" not in html, (
        "the Private Collection page must NOT render a 'property-card' (FR17 — "
        "no properties shown; this is NOT a listing) (AC1)."
    )
    assert "listing-grid" not in html, (
        "the Private Collection page must NOT render a 'listing-grid' (FR17 — "
        "this is NOT a listing) (AC1)."
    )


# =========================================================================== #
# AC2 — Intake form with EXACTLY 5 fields + csrf + honeypot; NEW form;          #
#       InquiryForm unchanged (regression)                                     #
# =========================================================================== #
@pytest.mark.django_db
def test_private_collection_form_exposes_exactly_five_fields_and_csrf(client):
    # AC2: GET renders a pc-form <form method="post"> with {% csrf_token %} and
    # EXACTLY the 5 user controls name/email/phone/property_type_wanted/
    # budget_range.
    _seed_site_settings()
    resp, html = _get_pc(client)
    assert resp.status_code == 200
    assert "pc-form" in html, "the pc-form section must render (AC2)."
    assert '<form method="post"' in html or "method='post'" in html.lower(), (
        "the intake form must be a <form method=\"post\"> (AC2)."
    )
    assert "csrfmiddlewaretoken" in html, (
        "the intake form must include {% csrf_token %} (AC2, NFR-5)."
    )
    for name in ("name", "email", "phone", "property_type_wanted", "budget_range"):
        assert f'name="{name}"' in html, (
            f"the intake form must expose a control name=\"{name}\" (Django field "
            f"name, NOT the design's dashed name) (AC2)."
        )


@pytest.mark.django_db
def test_private_collection_honeypot_present_but_not_type_hidden(client):
    # AC2 (anti-spam markup): the honeypot `website` input renders, but it must
    # NOT be type="hidden" (bots skip type=hidden; it is hidden via CSS/.sr-only
    # + aria-hidden/tabindex=-1 instead — mirrors the InquiryForm widget).
    _seed_site_settings()
    resp, html = _get_pc(client)
    assert resp.status_code == 200
    assert 'name="website"' in html, (
        "the honeypot 'website' field must render (AC2)."
    )
    w_idx = html.find('name="website"')
    tag_start = html.rfind("<input", 0, w_idx)
    tag_end = html.find(">", w_idx)
    tag = html[tag_start:tag_end + 1]
    assert 'type="hidden"' not in tag, (
        "the honeypot 'website' input must NOT be type=\"hidden\" (bots skip "
        "type=hidden — it is hidden via CSS/.sr-only) (AC2)."
    )


def test_private_collection_form_non_honeypot_fields_are_exactly_five():
    # AC2 (NEW form): PrivateCollectionForm's non-honeypot fields are EXACTLY
    # {name, email, phone, property_type_wanted, budget_range} — no message /
    # inquiry_type / status / property (server-side or default).
    forms_mod = importlib.import_module("inquiries.forms")
    PrivateCollectionForm = getattr(forms_mod, "PrivateCollectionForm")
    form = PrivateCollectionForm()
    user_fields = set(form.fields) - {"website"}
    assert user_fields == {
        "name", "email", "phone", "property_type_wanted", "budget_range",
    }, (
        f"PrivateCollectionForm non-honeypot fields must be exactly {{name, "
        f"email, phone, property_type_wanted, budget_range}}, got {user_fields} "
        f"(AC2, FR18)."
    )
    for forbidden in ("message", "inquiry_type", "property", "status",
                      "preferred_language"):
        assert forbidden not in form.fields, (
            f"PrivateCollectionForm must NOT expose '{forbidden}' as a field "
            f"(server-side / default only — tampering prevention) (AC2)."
        )


def test_private_collection_form_meta_model_and_fields_locked():
    # AC2: PrivateCollectionForm is a ModelForm over Inquiry with the LOCKED
    # Meta.fields list (exactly 5, in this order — message is NOT included).
    forms_mod = importlib.import_module("inquiries.forms")
    PrivateCollectionForm = getattr(forms_mod, "PrivateCollectionForm")
    Inquiry = _get_model("inquiries", "Inquiry")
    assert PrivateCollectionForm.Meta.model is Inquiry, (
        "PrivateCollectionForm.Meta.model must be Inquiry (AC2)."
    )
    assert list(PrivateCollectionForm.Meta.fields) == [
        "name", "email", "phone", "property_type_wanted", "budget_range",
    ], (
        "PrivateCollectionForm.Meta.fields must be exactly [name, email, phone, "
        f"property_type_wanted, budget_range], got "
        f"{list(PrivateCollectionForm.Meta.fields)} (AC2, FR18)."
    )


def test_private_collection_choice_fields_carry_locked_choices():
    # AC2/AC3: property_type_wanted & budget_range are ChoiceFields whose allowed
    # values are the LOCKED readable Serbian labels (value == label), including
    # the en-dash budget range. The empty "" placeholder is the first choice.
    forms_mod = importlib.import_module("inquiries.forms")
    PrivateCollectionForm = getattr(forms_mod, "PrivateCollectionForm")
    form = PrivateCollectionForm()
    pt_values = [v for v, _label in form.fields["property_type_wanted"].choices]
    bg_values = [v for v, _label in form.fields["budget_range"].choices]
    assert pt_values[0] == "", (
        "property_type_wanted's first choice must be the empty '' placeholder "
        "(empty selection -> invalid) (AC2)."
    )
    assert "Stan" in pt_values, (
        "property_type_wanted must allow the LOCKED label 'Stan' (value == "
        f"label), got {pt_values} (AC2)."
    )
    assert bg_values[0] == "", (
        "budget_range's first choice must be the empty '' placeholder (AC2)."
    )
    assert "€500.000 – €1.000.000" in bg_values, (
        "budget_range must allow the LOCKED label '€500.000 – €1.000.000' (note "
        f"the en-dash; value == label), got {bg_values} (AC2)."
    )


def test_inquiry_form_unchanged_regression():
    # AC2 (REGRESSION): the existing InquiryForm (3.2/4.2) is UNCHANGED — its
    # non-honeypot fields stay exactly {name, email, phone, message}. 5.1 adds a
    # NEW form, it must NOT touch InquiryForm.
    forms_mod = importlib.import_module("inquiries.forms")
    InquiryForm = getattr(forms_mod, "InquiryForm")
    form = InquiryForm()
    user_fields = set(form.fields) - {"website"}
    assert user_fields == {"name", "email", "phone", "message"}, (
        f"InquiryForm non-honeypot fields must remain exactly {{name, email, "
        f"phone, message}} (5.1 must NOT modify it), got {user_fields} (AC2 "
        f"regression)."
    )


# =========================================================================== #
# AC3 — Valid POST creates Inquiry(private_collection) + fields saved + CSRF +  #
#       PRG + tampering + no email                                             #
# =========================================================================== #
@pytest.mark.django_db
def test_private_collection_post_valid_creates_one_inquiry_and_redirects(client):
    # AC3: a valid POST creates EXACTLY ONE Inquiry with the server-set fields
    # (private_collection/new/sr/property=None/ip_address) AND the form-supplied
    # property_type_wanted/budget_range saved, message="", then PRG-redirects
    # (302) to ?sent=1; following the redirect -> 200 with form-success.
    _seed_site_settings()
    Inquiry = _get_model("inquiries", "Inquiry")
    assert _inquiry_count() == 0
    resp = client.post(_pc_path(), data=_valid_post_data())
    assert resp.status_code == 302, (
        f"a valid POST must PRG-redirect (302), got {resp.status_code} (AC3)."
    )
    assert "sent=1" in resp.url, (
        f"the PRG redirect must carry the success marker ?sent=1, got "
        f"{resp.url!r} (AC3)."
    )
    assert _inquiry_count() == 1, (
        f"a valid POST must create exactly ONE Inquiry, got {_inquiry_count()} (AC3)."
    )
    inq = Inquiry.objects.get()
    assert inq.inquiry_type == "private_collection", (
        "server must set inquiry_type='private_collection' (AC3)."
    )
    assert inq.status == "new", "server must set status='new' (AC3)."
    assert inq.preferred_language == "sr", (
        "server must set preferred_language='sr' (required, no DB default) (AC3)."
    )
    assert inq.property_id is None, (
        "Private Collection inquiry must have property=None (FR17 — no specific "
        "Property) (AC3)."
    )
    assert inq.ip_address is not None, (
        "create_inquiry must capture ip_address from the request (REMOTE_ADDR) (AC3)."
    )
    # The two select values must be SAVED verbatim (LOCKED labels, not codes).
    assert inq.property_type_wanted == "Stan", (
        f"property_type_wanted must be saved as the LOCKED label 'Stan', got "
        f"{inq.property_type_wanted!r} (AC3)."
    )
    assert inq.budget_range == "€500.000 – €1.000.000", (
        f"budget_range must be saved as the LOCKED label '€500.000 – €1.000.000' "
        f"(en-dash), got {inq.budget_range!r} (AC3)."
    )
    # message is NOT a form field -> stays the empty-string default (no migration,
    # no seam change). This guards against a regression adding message to the form.
    assert inq.message == "", (
        f"message must stay '' (not a PrivateCollectionForm field -> default), "
        f"got {inq.message!r} (AC3)."
    )
    assert inq.name == "Marko Markovic"
    assert inq.email == "marko@example.com"
    assert inq.phone == "+381601234567"
    # follow the redirect -> 200 success marker
    follow = client.get(resp.url)
    assert follow.status_code == 200
    assert "form-success" in follow.content.decode("utf-8"), (
        "the GET after ?sent=1 must render the form-success message (PRG) (AC3)."
    )


@pytest.mark.django_db
def test_private_collection_post_tampering_server_fields_win(client):
    # AC3 (tampering): a POST that ALSO sends inquiry_type/status/property/
    # preferred_language must be IGNORED — the created Inquiry keeps the
    # server-set values (those are not PrivateCollectionForm fields).
    _seed_site_settings()
    other = _make_property(title="Tamper Meta")
    Inquiry = _get_model("inquiries", "Inquiry")
    data = _valid_post_data(
        inquiry_type="viewing",
        status="closed",
        property=str(other.id),
        preferred_language="en",
    )
    resp = client.post(_pc_path(), data=data)
    assert resp.status_code == 302, "a (tampered) valid POST still PRG-redirects (AC3)."
    assert _inquiry_count() == 1, "exactly one Inquiry created on a tampered POST (AC3)."
    inq = Inquiry.objects.get()
    assert inq.inquiry_type == "private_collection", (
        "client-supplied inquiry_type must be IGNORED (server sets "
        "'private_collection') (AC3)."
    )
    assert inq.status == "new", (
        "client-supplied status must be IGNORED (server sets 'new') (AC3)."
    )
    assert inq.preferred_language == "sr", (
        "client-supplied preferred_language must be IGNORED (server sets 'sr') (AC3)."
    )
    assert inq.property_id is None, (
        "client-supplied property must be IGNORED (server sets property=None) (AC3)."
    )


@pytest.mark.django_db
def test_private_collection_post_csrf_enforced_403_no_row(client):
    # AC3 (CSRF): an enforce_csrf_checks client POSTing WITHOUT a token -> 403,
    # and NO Inquiry created.
    _seed_site_settings()
    csrf_client = Client(enforce_csrf_checks=True)
    resp = csrf_client.post(_pc_path(), data=_valid_post_data())
    assert resp.status_code == 403, (
        f"a POST without a CSRF token must return 403, got {resp.status_code} (AC3)."
    )
    assert _inquiry_count() == 0, (
        "a CSRF-rejected POST must create NO Inquiry (AC3)."
    )


@pytest.mark.django_db
def test_private_collection_post_sends_two_emails(client):
    # 5.2 (AC1/AC6 cross-cutting): a valid private_collection submit now SENDS 2
    # emails (agent notification + buyer auto-reply) via the create_inquiry hook.
    # This file's _seed_site_settings seeds NO email field, so we MUST pass
    # email_inquiries here — without it the agent recipient would be blank and
    # only the auto-reply (1 email) would be sent. (Inverted in GREEN from the
    # 5.1 no-email assertion.)
    _seed_site_settings(email_inquiries="agent@velegradestate.test")
    before = len(mail.outbox)
    resp = client.post(_pc_path(), data=_valid_post_data())
    assert resp.status_code == 302, (
        f"a valid POST must PRG-redirect (302) before the email assertion is "
        f"meaningful, got {resp.status_code} (AC3)."
    )
    assert len(mail.outbox) == before + 2, (
        "5.2 must send 2 emails (agent + auto-reply) on a valid private_collection "
        "submit via the create_inquiry hook (AC1/AC6)."
    )


@pytest.mark.django_db
def test_private_collection_post_invalid_email_re_renders_200_no_row(client):
    # AC3: an invalid email re-renders (200) with form errors and creates NO row.
    _seed_site_settings()
    resp = client.post(_pc_path(), data=_valid_post_data(email="not-an-email"))
    assert resp.status_code == 200, (
        f"an invalid POST must re-render (200), got {resp.status_code} (AC3)."
    )
    assert _inquiry_count() == 0, (
        f"an invalid email must create NO Inquiry, got {_inquiry_count()} (AC3)."
    )
    html = resp.content.decode("utf-8")
    assert "errorlist" in html, (
        "the re-rendered bound form must display its validation errors (Django "
        "'errorlist') — a 200 that does not render the form would be a silent "
        "failure (AC3)."
    )


@pytest.mark.django_db
def test_private_collection_post_empty_select_re_renders_200_no_row(client):
    # AC3: the empty "" placeholder choice on a required ChoiceField is invalid —
    # an empty property_type_wanted re-renders 200 and creates NO row.
    _seed_site_settings()
    resp = client.post(_pc_path(), data=_valid_post_data(property_type_wanted=""))
    assert resp.status_code == 200, (
        f"an empty (placeholder) property_type_wanted must re-render (200), got "
        f"{resp.status_code} (AC3)."
    )
    assert _inquiry_count() == 0, (
        "an empty required select must create NO Inquiry (AC3)."
    )


@pytest.mark.django_db
def test_private_collection_post_empty_budget_range_re_renders_200_no_row(client):
    # AC3 (symmetric to the empty property_type_wanted case): with a VALID
    # property_type_wanted ("Stan") but the empty "" placeholder on the required
    # budget_range ChoiceField, the bound form is invalid -> re-renders 200 with
    # its errorlist and creates NO row.
    _seed_site_settings()
    resp = client.post(
        _pc_path(),
        data=_valid_post_data(property_type_wanted="Stan", budget_range=""),
    )
    assert resp.status_code == 200, (
        f"an empty (placeholder) budget_range must re-render (200), got "
        f"{resp.status_code} (AC3)."
    )
    html = resp.content.decode("utf-8")
    assert "errorlist" in html, (
        "the re-rendered bound form must display its validation errors (Django "
        "'errorlist') for the empty required budget_range (AC3)."
    )
    assert _inquiry_count() == 0, (
        "an empty required select must create NO Inquiry (AC3)."
    )


# =========================================================================== #
# AC4 — Anti-spam: honeypot + rate-limit                                       #
# =========================================================================== #
@pytest.mark.django_db
def test_private_collection_honeypot_filled_silently_rejected(client):
    # AC4 (honeypot, LOCKED): a POST with the honeypot 'website' filled (a bot)
    # returns the SAME success branch (302 -> ?sent=1) so the bot sees "success" —
    # but NO Inquiry is created.
    _seed_site_settings()
    resp = client.post(_pc_path(),
                       data=_valid_post_data(website="http://spam.example"))
    assert resp.status_code == 302, (
        "a honeypot-filled POST must return the SAME success branch (302) as a "
        f"real submit (so the bot sees 'success'), got {resp.status_code} (AC4)."
    )
    assert "sent=1" in resp.url, (
        "the honeypot success branch must redirect to ?sent=1 (same as a real "
        f"submit), got {resp.url!r} (AC4)."
    )
    assert _inquiry_count() == 0, (
        f"a honeypot-filled POST must create NO Inquiry (silently rejected), got "
        f"{_inquiry_count()} (AC4)."
    )


@override_settings(RATELIMIT_ENABLE=True)
@pytest.mark.django_db
def test_private_collection_rate_limit_blocks_sixth_post_with_403(client):
    # AC4 (rate-limit, NFR-5 — django-ratelimit @ratelimit(key="ip", rate="5/h",
    # method="POST", block=True)): with RATELIMIT_ENABLE=True and a cleared cache,
    # 6 rapid POSTs from the SAME IP -> the 6th is deterministically blocked with
    # HTTP 403 (block=True -> Ratelimited -> 403), and exactly 5 rows are created
    # (the over-limit POST writes nothing).
    _seed_site_settings()
    # Clear the `default` LocMemCache alias django-ratelimit uses, both BEFORE
    # (so a prior test's counter does not pre-trip us) and AFTER (so our 5 hits
    # do not leak into a later test sharing the in-process cache) — isolation.
    cache.clear()
    try:
        statuses = []
        for _ in range(6):
            resp = client.post(_pc_path(), data=_valid_post_data(),
                               REMOTE_ADDR="203.0.113.7")
            statuses.append(resp.status_code)
        # The FIRST 5 (= the 5/h limit) must be ALLOWED (302 PRG) — this guards
        # against a vacuous pass where a misconfigured limit blocks EVERYTHING.
        assert statuses[:5] == [302, 302, 302, 302, 302], (
            f"the first 5 POSTs from the same IP (within the 5/h limit) must be "
            f"ALLOWED (302 PRG); got status sequence {statuses} (AC4)."
        )
        assert statuses[-1] == 403, (
            f"the 6th rapid POST from the same IP must be rate-limited with HTTP "
            f"403 (block=True -> Ratelimited -> 403, deterministic); got status "
            f"sequence {statuses} (AC4)."
        )
        assert _inquiry_count() == 5, (
            f"exactly the 5/h limit of Inquiry rows may be created — the 5 allowed "
            f"POSTs write a row each and the over-limit 6th writes nothing; got "
            f"{_inquiry_count()} (AC4)."
        )
    finally:
        cache.clear()


def test_test_settings_disable_ratelimit():
    # AC4 (anti-flaky): the default test suite has RATELIMIT_ENABLE = False (set
    # in 4.2) so the functional AC1/AC3 tests (multiple POSTs) never trip the
    # in-process LocMemCache rate limit. The dedicated rate-limit test re-enables it.
    assert getattr(settings, "RATELIMIT_ENABLE", None) is False, (
        "config/settings/test.py must set RATELIMIT_ENABLE = False (anti-flaky) (AC4)."
    )


def test_django_ratelimit_in_installed_apps():
    # AC4 / AC6 (config): django-ratelimit 4.x requires 'django_ratelimit' in
    # INSTALLED_APPS for `manage.py check` to pass; the @ratelimit decorator also
    # depends on the package being importable. (Infra is from 4.2 — 5.1 reuses it.)
    assert "django_ratelimit" in settings.INSTALLED_APPS, (
        "'django_ratelimit' must be in INSTALLED_APPS (infra from 4.2) (AC4/AC6)."
    )


# =========================================================================== #
# AC5 — i18n boundary + XSS auto-escape + route                                #
# =========================================================================== #
def test_private_collection_route_reverses_to_expected_path():
    # AC5: reverse("private-collection") == "/private-collection/".
    url = _try_reverse("private-collection")
    assert url == "/private-collection/", (
        f"reverse('private-collection') must equal '/private-collection/', got "
        f"{url!r} (AC5)."
    )


@pytest.mark.django_db
def test_en_private_collection_route_is_404(client):
    # AC5 (i18n boundary): there is NO i18n_patterns / /en/ prefix (Epik 6) ->
    # GET /en/private-collection/ must be 404.
    resp = client.get("/en/private-collection/")
    assert resp.status_code == 404, (
        f"GET /en/private-collection/ must be 404 (no i18n routing in 5.1), got "
        f"{resp.status_code} (AC5)."
    )


@pytest.mark.django_db
def test_private_collection_invalid_post_escapes_script_in_name(client):
    # AC5 (XSS): a bound re-render after an invalid POST must HTML-escape the
    # user-supplied name (no |safe on form values) — a <script> payload appears as
    # &lt;script&gt;, NOT raw, and NO row is created.
    _seed_site_settings()
    resp = client.post(
        _pc_path(),
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
def test_private_collection_renders_sr_trans_labels(client):
    # AC5 (i18n): the SR {% trans %}-rendered UI labels appear (active language is
    # SR). The field labels prove the {% trans %} skeleton rendered.
    _seed_site_settings()
    resp, html = _get_pc(client)
    assert resp.status_code == 200
    assert "Tip nekretnine" in html, (
        "the SR label 'Tip nekretnine' (property_type_wanted) must render via "
        "{% trans %} (AC5)."
    )
    assert "Budžet" in html, (
        "the SR label 'Budžet' (budget_range) must render via {% trans %} (AC5)."
    )


# =========================================================================== #
# AC6 — Regression (routes, render, existing pages/admin/forms still green)    #
# =========================================================================== #
def test_manage_py_check_passes():
    # AC6: `manage.py check` runs clean after the view/template/url/form changes
    # (incl. django-ratelimit system checks — a HARD gate).
    try:
        call_command("check", verbosity=0)
    except SystemCheckError as exc:
        pytest.fail(f"manage.py check reported errors: {exc} (AC6)")


@pytest.mark.django_db
def test_home_still_returns_200(client):
    # AC6 (2.2 regression): GET / still 200 — its hardcoded Private Collection
    # teaser href="/private-collection/" now points at a LIVE route.
    _seed_site_settings()
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / (Home) must still return 200, got {resp.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_listing_still_returns_200(client):
    # AC6 (3.1 regression): GET /properties/ listing still 200.
    _seed_site_settings()
    _make_property(title="Listing Regresija", status="for_sale")
    resp = client.get("/properties/")
    assert resp.status_code == 200, (
        f"GET /properties/ (listing) must still return 200, got "
        f"{resp.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_property_detail_still_returns_200(client):
    # AC6 (3.2 regression): a seeded active /properties/<slug>/ still 200 (its
    # InquiryForm/create_inquiry are unchanged by 5.1).
    _seed_site_settings()
    prop = _make_property(title="Detalj Regresija", is_active=True)
    resp = client.get(f"/properties/{prop.slug}/")
    assert resp.status_code == 200, (
        f"GET /properties/{prop.slug}/ must still return 200, got "
        f"{resp.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_about_and_international_still_return_200(client):
    # AC6 (4.1 regression): seeded /about/ and /international/ still 200.
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
def test_contact_still_returns_200(client):
    # AC6 (4.2 regression): GET /contact/ still 200 (ContactView + InquiryForm
    # unchanged by 5.1).
    _seed_site_settings()
    resp = client.get("/contact/")
    assert resp.status_code == 200, (
        f"GET /contact/ must still return 200, got {resp.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_private_collection_route_now_200_not_404(client):
    # AC6: GET /private-collection/ is now 200 (5.1 registers the route the 2.2
    # Home teaser hardcoded href targets). No prior guard test asserted 404 here.
    _seed_site_settings()
    resp = client.get("/private-collection/")
    assert resp.status_code == 200, (
        f"GET /private-collection/ must now return 200 (5.1 registers the route), "
        f"got {resp.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_admin_index_still_200_for_superuser(client, django_user_model):
    # AC6 (1.3 regression): the branded admin index still returns 200.
    _superuser(django_user_model)
    client.login(username="admin", password="pass12345")
    resp = client.get(_admin_index_path())
    assert resp.status_code == 200, (
        f"admin index at {_admin_index_path()} must still return 200 (AC6)."
    )


@pytest.mark.django_db
def test_default_admin_path_still_404(client):
    # AC6 (1.3 regression): GET /admin/ stays 404 (admin mounts on ADMIN_URL).
    resp = client.get("/admin/")
    assert resp.status_code == 404, (
        f"/admin/ must still return 404, got {resp.status_code} (AC6)."
    )


@pytest.mark.django_db
def test_no_root_catch_all_unknown_slug_404(client):
    # AC6: a non-existent root path -> 404 (proving there is NO root catch-all
    # path("<slug>/") added alongside the /private-collection/ route).
    _seed_site_settings()
    resp = client.get("/nepostojeci-slug/")
    assert resp.status_code == 404, (
        "a non-existent root path must return 404 (no root catch-all), got "
        f"{resp.status_code} (AC6)."
    )
