"""Properties app models (Story 1.2).

Defines ``PropertyFeature``, ``Property`` and ``PropertyImage`` from the
projektni zadatak §5.2.
"""
import uuid

from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from tinymce.models import HTMLField

from core.models import IMAGE_EXTENSIONS, LocalizedMixin, webp_spec


class PropertyFeature(LocalizedMixin, models.Model):
    """A reusable amenity/feature tag (§5.2 "Model: PropertyFeature")."""

    CATEGORY_CHOICES = [
        ("interior", "Enterijer"),
        ("exterior", "Eksterijer"),
        ("building", "Zgrada"),
        ("legal", "Pravno"),
    ]

    # Slug -> ikonica. Mora se poklapati sa granama u
    # templates/properties/_amenity_icon.html. Prazno = generička ikonica.
    ICON_CHOICES = [
        ("air-conditioning", "Klima uređaj"),
        ("underfloor-heating", "Podno grejanje"),
        ("fireplace", "Kamin"),
        ("kitchen", "Ugradna kuhinja"),
        ("wardrobe", "Garderober / vešalica"),
        ("smart-home", "Pametna kuća"),
        ("terrace", "Terasa"),
        ("pool", "Bazen"),
        ("garden", "Vrt / drvo"),
        ("view", "Pogled"),
        ("bbq", "Roštilj"),
        ("elevator", "Lift"),
        ("garage", "Garaža"),
        ("parking", "Parking"),
        ("concierge", "Recepcija / zvonce"),
        ("cctv", "Video nadzor"),
        ("storage", "Ostava / kutija"),
        ("registered", "Uknjiženo (dokument)"),
        ("no-encumbrance", "Bez tereta (štit)"),
        ("permit", "Dozvola (pečat)"),
        ("wine-cellar", "Vinski podrum"),
        ("security", "Obezbeđenje / alarm"),
        ("gym", "Teretana"),
        ("jacuzzi", "Đakuzi / spa"),
        ("intercom", "Interfon"),
        ("sauna", "Sauna"),
    ]

    name_sr = models.CharField("Naziv (SR)", max_length=100)
    name_en = models.CharField("Naziv (EN)", max_length=100)
    icon = models.CharField(
        "Ikonica",
        max_length=50,
        blank=True,
        choices=ICON_CHOICES,
        help_text=(
            "Izaberite ikonicu koja se prikazuje uz karakteristiku na stranici "
            "nekretnine. Ostavite prazno za generičku ikonicu (kvačica)."
        ),
    )
    category = models.CharField(
        "Kategorija", max_length=20, choices=CATEGORY_CHOICES
    )

    class Meta:
        verbose_name = "Karakteristika"
        verbose_name_plural = "Karakteristike"
        ordering = ["category", "name_sr"]

    def __str__(self):
        return self.name_sr


class Property(LocalizedMixin, models.Model):
    """A real-estate listing (§5.2 "Model: Property")."""

    STATUS_CHOICES = [
        ("for_sale", "Na prodaju"),
        ("for_rent", "Za izdavanje"),
        ("price_on_request", "Cena na upit"),
        ("sold", "Prodato"),
        ("rented", "Izdato"),
    ]
    COLLECTION_TYPE_CHOICES = [
        ("signature", "Signature"),
        ("private", "Privatna kolekcija"),
        ("off_market", "Off-market"),
    ]
    PROPERTY_TYPE_CHOICES = [
        ("stan", "Stan"),
        ("kuca", "Kuća"),
        ("penthouse", "Penthouse"),
        ("vila", "Vila"),
        ("komercijalno", "Komercijalno"),
        ("zemljiste", "Zemljište"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField("Naslov", max_length=200)
    slug = models.SlugField("Slug (URL)", max_length=255, unique=True, blank=True)

    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES)
    collection_type = models.CharField(
        "Tip kolekcije", max_length=20, choices=COLLECTION_TYPE_CHOICES
    )
    property_type = models.CharField(
        "Tip nekretnine", max_length=20, choices=PROPERTY_TYPE_CHOICES
    )

    location_city = models.CharField("Grad", max_length=100)
    location_district = models.CharField("Deo grada / opština", max_length=100)
    location_address = models.CharField("Adresa", max_length=255, blank=True)
    show_address = models.BooleanField("Prikaži adresu", default=False)

    price = models.DecimalField(
        "Cena (€)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    price_on_request = models.BooleanField("Cena na upit", default=False)

    area_sqm = models.DecimalField(
        "Stambena površina (m²)", max_digits=8, decimal_places=2
    )
    area_total_sqm = models.DecimalField(
        "Ukupna površina (m²)", max_digits=8, decimal_places=2
    )

    bedrooms = models.IntegerField("Spavaće sobe")
    bathrooms = models.IntegerField("Kupatila")
    floor = models.IntegerField("Sprat")
    total_floors = models.IntegerField("Ukupno spratova")
    parking_spaces = models.IntegerField("Parking mesta")
    year_built = models.IntegerField("Godina izgradnje", null=True, blank=True)

    description_sr = HTMLField("Opis (SR)")
    description_en = HTMLField("Opis (EN)")
    description_fr = HTMLField("Opis (FR)", blank=True)

    features = models.ManyToManyField(
        PropertyFeature,
        blank=True,
        related_name="properties",
        verbose_name="Karakteristike",
    )

    hero_image = models.ImageField(
        "Glavna slika",
        upload_to="properties/hero/",
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )
    # WebP/srcset varijante za hero_image (Story 6.3 — non-DB descriptors).
    hero_image_webp_480 = webp_spec("hero_image", 480)
    hero_image_webp_960 = webp_spec("hero_image", 960)
    hero_image_webp_1440 = webp_spec("hero_image", 1440)

    floor_plan = models.FileField(
        "Osnova (floor plan)",
        upload_to="properties/floorplans/",
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "jpg", "jpeg", "png", "webp"]
            )
        ],
    )
    virtual_tour_url = models.URLField("URL virtuelne ture", blank=True)

    latitude = models.DecimalField(
        "Geografska širina", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        "Geografska dužina", max_digits=9, decimal_places=6, null=True, blank=True
    )

    is_featured = models.BooleanField("Izdvojena", default=False)
    is_active = models.BooleanField("Aktivna", default=True)

    created_at = models.DateTimeField("Kreirano", auto_now_add=True)
    updated_at = models.DateTimeField("Ažurirano", auto_now=True)

    meta_title = models.CharField("Meta naslov (SEO)", max_length=70, blank=True)
    meta_description = models.TextField("Meta opis (SEO)", blank=True)

    class Meta:
        verbose_name = "Nekretnina"
        verbose_name_plural = "Nekretnine"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["collection_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """Kanonska (no-prefix SR) putanja do detail stranice (Story 6.2).

        Metoda (NE polje) → BEZ migracije. Koristi se konzistentno na TRI mesta:
        sitemap location(), og:url i Schema url — sve tri emituju IDENTIČNU
        kanonsku putanju. reverse() razrešava pod aktivnim jezikom; pozivaoci
        koji žele determinističku SR putanju (sitemap) obmotaju ovaj poziv u
        translation.override(settings.LANGUAGE_CODE).
        """
        return reverse("property-detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        """Auto-generate a collision-safe slug from ``title`` when blank."""
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or "nekretnina"
            candidate = base
            suffix = 2
            qs = Property.objects.all()
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.filter(slug=candidate).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class PropertyImage(models.Model):
    """A gallery image attached to a :class:`Property` (§5.2)."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Nekretnina",
    )
    image = models.ImageField(
        "Slika",
        upload_to="properties/gallery/",
        validators=[FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)],
    )
    caption = models.CharField("Opis slike", max_length=255, blank=True)
    order = models.IntegerField("Redosled", default=0)
    is_hero = models.BooleanField("Glavna slika galerije", default=False)

    # WebP/srcset varijante za gallery image (Story 6.3 — non-DB descriptors).
    image_webp_480 = webp_spec("image", 480)
    image_webp_960 = webp_spec("image", 960)
    image_webp_1440 = webp_spec("image", 1440)

    class Meta:
        verbose_name = "Slika nekretnine"
        verbose_name_plural = "Slike nekretnina"
        ordering = ["order"]

    def __str__(self):
        return f"{self.property} #{self.order}"
