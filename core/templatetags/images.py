"""``{% picture %}`` template tag (Story 6.3 — WebP + responsive srcset).

Centralizuje ``<picture><source type="image/webp" srcset="..."><img></picture>``
markup za svaku upload-ovanu media sliku (~7 <img> lokacija: home hero/founder/
kartice, properties kartice, property-detail hero/thumbnails, about portret).

Mehanizam (LOCKED, I2 — empirijski potvrđeno django-imagekit 6.1.0): WebP varijanta-
URL-ovi se grade SAMO preko ImageSpecField-ovog ``.url`` (čista string operacija pod
OBAVEZNOM Optimistic strategijom — bez I/O, bez otvaranja fajla, bez 500 na byteless).
NIKAD se ne pristupa ``.width``/``.height`` (te bi otvorile cachefile → 500).

Kad je media polje prazno, renderuje se POSTOJEĆI ``{% static %}`` SVG placeholder kao
običan ``<img>`` — BEZ WebP ``<source>``, BEZ ImageKit poziva (SVG je vektor; ImageKit
se NE poziva na prazno polje).

Granice: og:image/Schema image (6.2) i thumbnail ``data-full`` (3.2 gallery.js)
koriste PUN ``.url`` direktno u template-u — NE prolaze kroz ovaj tag.
"""
from django import template
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from core.models import SRCSET_WIDTHS

register = template.Library()


@register.simple_tag
def picture(image_field, alt, placeholder, css_class="", sizes="", lazy=False):
    """Renderuj ``<picture>`` sa WebP/srcset za neprazno ``image_field``, inače
    SVG placeholder ``<img>``.

    Args:
        image_field: izvorni ImageField (npr. ``property.hero_image``). Ako je
            falsy (prazno polje) → renderuje se placeholder grana.
        alt: ``alt`` tekst (a11y — uvek prisutan).
        placeholder: static putanja do SVG placeholdera (npr.
            ``"images/placeholders/hero-placeholder.svg"``).
        css_class: opciona klasa na ``<img>``.
        sizes: opcioni ``sizes`` atribut (npr. ``"100vw"`` na above-fold hero).
        lazy: ako True → ``loading="lazy"`` (ispod fold-a); inače izostavljen
            (above-fold eager default — NE lazy, izbegava LCP regresiju).
    """
    class_attr = format_html(' class="{}"', css_class) if css_class else ""
    loading_attr = mark_safe(' loading="lazy"') if lazy else ""
    sizes_attr = format_html(' sizes="{}"', sizes) if sizes else ""

    # Prazno media polje → postojeći SVG placeholder (bez ImageKit poziva).
    if not image_field:
        return format_html(
            '<img{} src="{}" alt="{}"{}{}>',
            class_attr, static(placeholder), alt, sizes_attr, loading_attr,
        )

    # Neprazno → <picture> sa WebP <source srcset> (spec .url je string-safe).
    instance = image_field.instance
    base = image_field.field.name
    srcset_parts = []
    for width in SRCSET_WIDTHS:
        spec = getattr(instance, f"{base}_webp_{width}")
        srcset_parts.append((spec.url, width))
    srcset = format_html_join(
        ", ", "{} {}w", ((url, width) for url, width in srcset_parts)
    )
    # `sizes` ide SAMO na <source> (ima srcset); na fallback <img> (bez srcset-a)
    # `sizes` je po HTML spec-u ignorisan -> izostavljamo ga (R1, DRY/no-noise).
    return format_html(
        '<picture>'
        '<source type="image/webp" srcset="{}"{}>'
        '<img{} src="{}" alt="{}"{}>'
        '</picture>',
        srcset, sizes_attr,
        class_attr, image_field.url, alt, loading_attr,
    )
