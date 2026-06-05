# Seed data migration — popunjava katalog PropertyFeature standardnim setom
# karakteristika (amenity tagova) grupisanih po CATEGORY_CHOICES
# (interior/exterior/building/legal). Bez ovog kataloga je `Property.features`
# picker prazan; admin (properties.admin.PropertyFeatureAdmin) omogućava klijentu
# da kasnije doda/uredi dodatne oznake.
#
# Idempotentno: get_or_create po (category, name_sr) — NIKAD ne pregazi ručno
# uređene/dodate oznake. EN nazivi su popunjeni; `icon` je slug (trenutno se
# prikazuje generička ikonica, vrednost je rezervisana za buduće setove).
from django.db import migrations


# (category, name_sr, name_en, icon)
FEATURES = [
    # Enterijer
    ("interior", "Klima uređaj", "Air conditioning", "air-conditioning"),
    ("interior", "Podno grejanje", "Underfloor heating", "underfloor-heating"),
    ("interior", "Kamin", "Fireplace", "fireplace"),
    ("interior", "Ugradna kuhinja", "Fitted kitchen", "kitchen"),
    ("interior", "Walk-in garderober", "Walk-in closet", "wardrobe"),
    ("interior", "Pametna kuća", "Smart home", "smart-home"),
    # Eksterijer
    ("exterior", "Terasa", "Terrace", "terrace"),
    ("exterior", "Bazen", "Swimming pool", "pool"),
    ("exterior", "Vrt", "Garden", "garden"),
    ("exterior", "Pogled", "View", "view"),
    ("exterior", "Roštilj prostor", "BBQ area", "bbq"),
    # Zgrada
    ("building", "Lift", "Elevator", "elevator"),
    ("building", "Garaža", "Garage", "garage"),
    ("building", "Parking mesto", "Parking space", "parking"),
    ("building", "Recepcija", "Concierge", "concierge"),
    ("building", "Video nadzor", "CCTV", "cctv"),
    ("building", "Ostava", "Storage room", "storage"),
    # Pravno
    ("legal", "Uknjiženo", "Registered title", "registered"),
    ("legal", "Bez tereta", "No encumbrances", "no-encumbrance"),
    ("legal", "Građevinska dozvola", "Building permit", "permit"),
]


def seed_features(apps, schema_editor):
    """Kreiraj standardne karakteristike ako već ne postoje (po category+name_sr)."""
    PropertyFeature = apps.get_model("properties", "PropertyFeature")
    for category, name_sr, name_en, icon in FEATURES:
        PropertyFeature.objects.get_or_create(
            category=category,
            name_sr=name_sr,
            defaults={"name_en": name_en, "icon": icon},
        )


def unseed_features(apps, schema_editor):
    """Bezbedan reverse: briše samo seed-ovane (category, name_sr) parove."""
    PropertyFeature = apps.get_model("properties", "PropertyFeature")
    for category, name_sr, _name_en, _icon in FEATURES:
        PropertyFeature.objects.filter(
            category=category, name_sr=name_sr
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0003_alter_propertyfeature_icon"),
    ]

    operations = [
        migrations.RunPython(seed_features, unseed_features),
    ]
