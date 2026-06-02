r"""Demo seed za lokalni pregled u pretraživaču (Story 1.4 admin).

Generiše:
  * superuser (admin / Velegrad2026!) ako ne postoji
  * PropertyFeature katalog (dvojezičan)
  * 6 nekretnina (signature + private, razni tipovi) sa hero slikom + galerijom
  * popunjen SiteSettings (kontakt / osnivač / hero / analitika / SEO)
  * nekoliko Inquiry zapisa (razni statusi)

Slike se generišu LOKALNO preko Pillow-a (nema potrebe za internetom) — validni
JPEG-ovi sa brend-bojama i oznakom tipa/lokacije, da galerija i "Dupliraj" imaju
realan sadržaj za pregled.

Pokretanje (iz korena projekta, sa SQLite za lokalni pregled):
    $env:DATABASE_URL = "sqlite:///dev-local.sqlite3"
    .\.venv\Scripts\python.exe manage.py migrate
    .\.venv\Scripts\python.exe scripts\seed_demo.py

Re-runnable: briše postojeće Property/PropertyImage/PropertyFeature/Inquiry pre
ponovnog kreiranja (SiteSettings se samo ažurira — singleton).
"""
import io
import os
import sys

import django

# --- Django bootstrap ---------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

# Robustan UTF-8 stdout (Windows konzola je podrazumevano cp1250).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from core.models import SiteSettings  # noqa: E402
from inquiries.models import Inquiry  # noqa: E402
from properties.models import Property, PropertyFeature, PropertyImage  # noqa: E402

OLIVE = (74, 82, 64)
OLIVE_DARK = (40, 44, 34)
CHAMPAGNE = (201, 169, 110)
CREAM = (235, 232, 225)


def _font(size):
    """Najbolji dostupni TrueType font na Windows-u, uz fallback na default."""
    for name in ("segoeui.ttf", "arial.ttf", "tahoma.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_image(label, sublabel, *, tint=OLIVE, w=1600, h=1066):
    """Vrati JPEG bajtove placeholder fotografije sa labelom."""
    img = Image.new("RGB", (w, h), tint)
    d = ImageDraw.Draw(img)
    # diskretne "sobe/prozori" linije za malo teksture
    for x in range(0, w, 220):
        d.line([(x, 0), (x, h)], fill=(tint[0] + 10, tint[1] + 10, tint[2] + 10), width=2)
    # donja traka + tekst
    d.rectangle([0, h - 280, w, h], fill=OLIVE_DARK)
    d.text((60, h - 230), label, fill=CHAMPAGNE, font=_font(96))
    d.text((64, h - 110), sublabel, fill=CREAM, font=_font(46))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def reset():
    print("→ Brišem postojeće demo podatke (Property / PropertyImage / Feature / Inquiry)...")
    PropertyImage.objects.all().delete()
    Inquiry.objects.all().delete()
    Property.objects.all().delete()
    PropertyFeature.objects.all().delete()


def superuser():
    User = get_user_model()
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@velegrad.rs", "Velegrad2026!")
        print("→ Superuser kreiran: admin / Velegrad2026!")
    else:
        print("→ Superuser 'admin' već postoji (lozinka nepromenjena).")


def features():
    data = [
        ("Bazen", "Pool", "pool", "exterior"),
        ("Privatni lift", "Private elevator", "elevator", "building"),
        ("Panoramska terasa", "Panoramic terrace", "terrace", "exterior"),
        ("Garaža (2 mesta)", "Garage (2 spots)", "garage", "building"),
        ("Pametna kuća", "Smart home", "smart", "interior"),
        ("Kamin", "Fireplace", "fireplace", "interior"),
        ("Uređen vrt", "Landscaped garden", "garden", "exterior"),
        ("Pogled na reku", "River view", "view", "exterior"),
        ("Podno grejanje", "Underfloor heating", "heating", "interior"),
        ("Obezbeđenje 24/7", "24/7 security", "security", "building"),
        ("Vinski podrum", "Wine cellar", "wine", "interior"),
        ("Uknjiženo", "Clear title", "legal", "legal"),
    ]
    objs = {}
    for sr, en, icon, cat in data:
        objs[sr] = PropertyFeature.objects.create(
            name_sr=sr, name_en=en, icon=icon, category=cat
        )
    print(f"→ Kreirano {len(objs)} karakteristika.")
    return objs


def properties(feat):
    """(podaci, lista feature naziva, lista (caption) galerije)."""
    specs = [
        dict(
            title="Penthouse Dorćol — Panorama",
            status="for_sale", collection_type="signature", property_type="penthouse",
            location_city="Beograd", location_district="Dorćol",
            location_address="Cara Dušana 00", show_address=False,
            price="1250000.00", area_sqm="210.00", area_total_sqm="265.00",
            bedrooms=3, bathrooms=3, floor=8, total_floors=8, parking_spaces=2,
            year_built=2021, is_featured=True, is_active=True,
            feats=["Privatni lift", "Panoramska terasa", "Pametna kuća", "Pogled na reku"],
            desc_sr="<p>Ekskluzivni penthouse na vrhu kultne zgrade na Dorćolu, sa "
                    "panoramskom terasom i pogledom na ušće. Vrhunski materijali, "
                    "privatni lift i potpuna privatnost.</p>",
            desc_en="<p>An exclusive top-floor penthouse in Dorćol with a panoramic "
                    "terrace overlooking the river confluence. Premium finishes, "
                    "private elevator and complete privacy.</p>",
        ),
        dict(
            title="Vila Dedinje — Rezidencija",
            status="for_sale", collection_type="signature", property_type="vila",
            location_city="Beograd", location_district="Dedinje",
            price="3400000.00", area_sqm="540.00", area_total_sqm="1200.00",
            bedrooms=6, bathrooms=5, floor=0, total_floors=3, parking_spaces=4,
            year_built=2018, is_featured=True, is_active=True,
            feats=["Bazen", "Uređen vrt", "Vinski podrum", "Obezbeđenje 24/7", "Garaža (2 mesta)"],
            desc_sr="<p>Reprezentativna vila na elitnom Dedinju, na placu od 12 ari, "
                    "sa grejanim bazenom, vinskim podrumom i prostranim vrtom. "
                    "Idealna porodična rezidencija najvišeg ranga.</p>",
            desc_en="<p>A signature villa in elite Dedinje on a 1,200 m² plot, with a "
                    "heated pool, wine cellar and landscaped garden. The ultimate "
                    "family residence.</p>",
        ),
        dict(
            title="Stan Vračar — Klasika",
            status="for_sale", collection_type="signature", property_type="stan",
            location_city="Beograd", location_district="Vračar",
            price="420000.00", area_sqm="96.00", area_total_sqm="104.00",
            bedrooms=2, bathrooms=2, floor=3, total_floors=5, parking_spaces=1,
            year_built=1936, is_featured=False, is_active=True,
            feats=["Kamin", "Podno grejanje", "Uknjiženo"],
            desc_sr="<p>Renoviran trosoban stan u srcu Vračara, u zaštićenoj "
                    "predratnoj zgradi. Visoki plafoni, originalni parket i kamin.</p>",
            desc_en="<p>A renovated two-bedroom apartment in the heart of Vračar, in a "
                    "protected pre-war building. High ceilings, original parquet and a "
                    "fireplace.</p>",
        ),
        dict(
            title="Kuća Zlatibor — Planinski mir",
            status="for_sale", collection_type="signature", property_type="kuca",
            location_city="Zlatibor", location_district="Centar",
            price="690000.00", area_sqm="240.00", area_total_sqm="800.00",
            bedrooms=4, bathrooms=3, floor=0, total_floors=2, parking_spaces=3,
            year_built=2020, is_featured=True, is_active=True,
            feats=["Kamin", "Uređen vrt", "Pogled na reku", "Podno grejanje"],
            desc_sr="<p>Moderna planinska kuća na Zlatiboru, na 200m od centra, sa "
                    "panoramskim pogledom i velikom terasom. Savršen spoj prirode i "
                    "luksuza.</p>",
            desc_en="<p>A modern mountain house on Zlatibor, 200m from the center, with "
                    "panoramic views and a large terrace. A perfect blend of nature and "
                    "luxury.</p>",
        ),
        dict(
            title="Penthouse Beograd na vodi",
            status="price_on_request", collection_type="signature", property_type="penthouse",
            location_city="Beograd", location_district="Savski venac",
            price=None, price_on_request=True,
            area_sqm="185.00", area_total_sqm="220.00",
            bedrooms=3, bathrooms=2, floor=32, total_floors=34, parking_spaces=2,
            year_built=2023, is_featured=True, is_active=True,
            feats=["Privatni lift", "Pogled na reku", "Pametna kuća", "Obezbeđenje 24/7"],
            desc_sr="<p>Penthouse na 32. spratu kule Beograda na vodi, sa "
                    "neprekinutim pogledom na Savu. Cena na upit — diskrecija "
                    "zagarantovana.</p>",
            desc_en="<p>A 32nd-floor penthouse in the Belgrade Waterfront tower, with an "
                    "uninterrupted view of the Sava. Price on request — discretion "
                    "guaranteed.</p>",
        ),
        dict(
            title="Apartman Kotor — Stari grad (uskoro)",
            status="for_sale", collection_type="private", property_type="stan",
            location_city="Kotor", location_district="Stari grad",
            price="850000.00", area_sqm="120.00", area_total_sqm="130.00",
            bedrooms=2, bathrooms=2, floor=2, total_floors=3, parking_spaces=0,
            year_built=1700, is_featured=False, is_active=False,  # NEAKTIVNA → za preview link
            feats=["Pogled na reku", "Uknjiženo", "Kamin"],
            desc_sr="<p>Kameni apartman u UNESCO-zaštićenom Starom gradu Kotora, sa "
                    "pogledom na zaliv. <strong>Još nije objavljen</strong> — za pregled "
                    "preko admin preview linka.</p>",
            desc_en="<p>A stone apartment in Kotor's UNESCO-protected Old Town, "
                    "overlooking the bay. <strong>Not yet published</strong> — viewable "
                    "via the admin preview link.</p>",
        ),
    ]
    gallery_caps = ["Dnevni boravak", "Kuhinja", "Master spavaća soba", "Terasa"]
    created = []
    for s in specs:
        feats = s.pop("feats")
        desc_sr = s.pop("desc_sr")
        desc_en = s.pop("desc_en")
        p = Property(description_sr=desc_sr, description_en=desc_en, **s)
        type_label = dict(Property.PROPERTY_TYPE_CHOICES)[s["property_type"]]
        hero_bytes = make_image(type_label, f"{s['location_district']}, {s['location_city']}")
        p.hero_image.save(f"hero-{p.title[:20]}.jpg", ContentFile(hero_bytes), save=False)
        p.save()
        p.features.set([feat[name] for name in feats])
        for i, cap in enumerate(gallery_caps):
            img_bytes = make_image(cap, s["title"], tint=(OLIVE[0] + i * 6, OLIVE[1] + i * 4, OLIVE[2] + i * 3))
            pi = PropertyImage(property=p, caption=cap, order=i, is_hero=(i == 0))
            pi.image.save(f"g-{p.title[:14]}-{i}.jpg", ContentFile(img_bytes), save=True)
        created.append(p)
        print(f"   • {p.title}  [{type_label}, {'AKTIVNA' if p.is_active else 'NEAKTIVNA'}]")
    print(f"→ Kreirano {len(created)} nekretnina (svaka: hero + {len(gallery_caps)} galerijskih slika).")
    return created


def settings_singleton():
    s = SiteSettings.load()
    s.phone_primary = "+381 11 123 4567"
    s.whatsapp_number = "+381641234567"
    s.email_primary = "kontakt@velegrad.rs"
    s.email_inquiries = "upiti@velegrad.rs"
    s.address = "Knez Mihailova 00, 11000 Beograd, Srbija"
    s.founder_name = "Marko Velegrad"
    s.founder_title_sr = "Osnivač i glavni savetnik"
    s.founder_title_en = "Founder & Principal Advisor"
    s.founder_bio_sr = ("<p>Sa preko 15 godina u luksuznom real-estate segmentu, Marko "
                        "vodi diskretne transakcije za najzahtevnije klijente.</p>")
    s.founder_bio_en = ("<p>With over 15 years in luxury real estate, Marko leads "
                        "discreet transactions for the most demanding clients.</p>")
    s.hero_headline_sr = "Kuratorska kolekcija izuzetnih nekretnina"
    s.hero_headline_en = "A curated collection of exceptional properties"
    s.hero_cta_text_sr = "Istražite kolekciju"
    s.hero_cta_text_en = "Explore the collection"
    s.hero_image.save("site-hero.jpg", ContentFile(make_image("VELEGRAD", "Boutique Real Estate", w=1920, h=1080)), save=False)
    s.founder_photo.save("founder.jpg", ContentFile(make_image("Marko Velegrad", "Osnivač", tint=OLIVE_DARK, w=800, h=1000)), save=False)
    s.google_analytics_id = "G-DEMO12345"
    s.seo_default_title = "Velegrad — Boutique nekretnine"
    s.seo_default_description = ("Kuratorska kolekcija izuzetnih nekretnina u Srbiji i regionu. "
                                "Diskrecija, ekskluzivnost, poverenje.")
    s.save()
    print("→ SiteSettings popunjen (kontakt / osnivač / hero / analitika / SEO).")


def inquiries(props):
    by_title = {p.title: p for p in props}
    data = [
        ("viewing", "Jelena Đorđević", "jelena@example.com", "+381601112233",
         "Zainteresovana sam za razgledanje penthousea na Dorćolu.", "sr", "new",
         "Penthouse Dorćol — Panorama"),
        ("private_collection", "Nikola Petrović", "nikola@example.com", "+381641002003",
         "Tražim diskretnu vilu na Dedinju, budžet do 4M EUR.", "sr", "contacted",
         "Vila Dedinje — Rezidencija"),
        ("consultation", "Anna Schmidt", "anna@example.de", "+4915123456",
         "I'd like a consultation about investment properties in Belgrade.", "en", "in_progress",
         None),
        ("viewing", "Marko Ilić", "marko.ilic@example.com", "+381652220011",
         "Da li je stan na Vračaru i dalje dostupan?", "sr", "closed",
         "Stan Vračar — Klasika"),
        ("general", "Sophie Martin", "sophie@example.fr", "+33612345678",
         "Bonjour, je cherche un chalet à Zlatibor.", "fr", "new",
         "Kuća Zlatibor — Planinski mir"),
    ]
    n = 0
    for itype, name, email, phone, msg, lang, status, ptitle in data:
        Inquiry.objects.create(
            inquiry_type=itype, name=name, email=email, phone=phone, message=msg,
            preferred_language=lang, status=status,
            property=by_title.get(ptitle),
        )
        n += 1
    print(f"→ Kreirano {n} upita (statusi: new / contacted / in_progress / closed).")


if __name__ == "__main__":
    print("=" * 60)
    print("VELEGRAD demo seed")
    print("=" * 60)
    superuser()
    reset()
    feat = features()
    props = properties(feat)
    settings_singleton()
    inquiries(props)
    print("=" * 60)
    print("✅ Gotovo. Pokreni server pa otvori /velegrad-cms/")
    print("   Login: admin / Velegrad2026!")
    print("=" * 60)
