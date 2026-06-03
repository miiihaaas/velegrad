# Seed data migration for Story 4.1 — populates the two CMS-driven static pages
# (Page slug="about", slug="international") so /about/ and /international/ resolve
# (pages.views.page_view -> get_object_or_404(Page, slug=..., is_active=True)).
#
# Idempotent: uses get_or_create so it NEVER clobbers admin-edited content if the
# row already exists. Content prose is ported from docs/OpenDesignFiles/{about,
# international}.html (the CMS-driven slice rendered via {% loc page "content" %}):
#   * about        -> the bio + "Kako radimo" (filozofija rada) prose.
#   * international -> the introductory paragraph (intl-intro).
# Static design chrome (services-list, why-pillar, timeline 01-06, "Pravni okvir"
# etc.) stays in the templates as {% trans %} markup — NOT in content_*.
#
# EN copy: the design files provide SR-only prose for these slices, so title_en /
# content_en are left blank ("") — LocalizedMixin.localized() falls back to _sr
# (arch §1.3). Admins can refine all of this in the TinyMCE admin afterwards.
from django.db import migrations


ABOUT_TITLE_SR = "Privatno savetovanje"
ABOUT_CONTENT_SR = (
    "<p>Ovde dolazi biografski tekst o osnivaču, njegovom pristupu tržištu "
    "premium nekretnina, filozofiji rada i profesionalnom putu. Ton je miran, "
    "siguran i bez prodajnog pritiska.</p>"
    "<p>Drugi paragraf biografije detaljnije opisuje iskustvo rada sa zahtevnim "
    "klijentima i poznavanje beogradskog tržišta nekretnina na najvišem nivou.</p>"
    "<h2>Kako radimo</h2>"
    "<p>Svakom klijentu pristupamo lično i sa punom posvećenošću. Selekcioni "
    "proces za nekretnine je pažljiv i diskretan, a ograničen broj klijenata je "
    "ono što garantuje kvalitet i pažnju koju zaslužuje svaka saradnja.</p>"
)
ABOUT_META_TITLE = "Privatno savetovanje — Velegrad Estate"
ABOUT_META_DESCRIPTION = (
    "Privatno savetovanje za premium nekretnine u Beogradu. Diskrecija, "
    "pregovaranje u ime klijenta i pristup off-market portfoliju."
)

INTL_TITLE_SR = "Međunarodni klijenti"
INTL_CONTENT_SR = (
    "<p>Beograd postaje jedna od najinteresantnijih destinacija za međunarodne "
    "investitore u nekretnine. Kombinacija pristupačnih cena u poređenju sa "
    "zapadnoevropskim prestonicama, rastućeg tržišta i strateškog geografskog "
    "položaja čini Srbiju privlačnom za kupce iz Francuske, Nemačke, Ujedinjenog "
    "Kraljevstva i šire.</p>"
)
INTL_META_TITLE = "Međunarodni klijenti — Velegrad Estate"
INTL_META_DESCRIPTION = (
    "Vodič za međunarodne kupce i investitore. Kupovina premium nekretnina u "
    "Srbiji — pravni okvir, finansiranje i kompletna podrška."
)

SEED_SLUGS = ("about", "international")


def seed_static_pages(apps, schema_editor):
    """Create Page(about) and Page(international) if they do not already exist."""
    Page = apps.get_model("pages", "Page")

    Page.objects.get_or_create(
        slug="about",
        defaults={
            "title_sr": ABOUT_TITLE_SR,
            "title_en": "",
            "content_sr": ABOUT_CONTENT_SR,
            "content_en": "",
            "meta_title": ABOUT_META_TITLE,
            "meta_description": ABOUT_META_DESCRIPTION,
            "is_active": True,
        },
    )
    Page.objects.get_or_create(
        slug="international",
        defaults={
            "title_sr": INTL_TITLE_SR,
            "title_en": "",
            "content_sr": INTL_CONTENT_SR,
            "content_en": "",
            "meta_title": INTL_META_TITLE,
            "meta_description": INTL_META_DESCRIPTION,
            "is_active": True,
        },
    )


def unseed_static_pages(apps, schema_editor):
    """Safe reverse: delete the seeded rows only if they exist (no-op otherwise)."""
    Page = apps.get_model("pages", "Page")
    Page.objects.filter(slug__in=SEED_SLUGS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_static_pages, unseed_static_pages),
    ]
