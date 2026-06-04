# Velegrad CMS — Uputstvo za korišćenje (primopredaja klijentu)

Ovo uputstvo je namenjeno osobi koja održava sajt Velegrad Estate. Pisano je
netehničkim jezikom — sve što vam treba za svakodnevni rad je opisano korak po korak.

---

## 1. Prijava u administraciju (login / ADMIN_URL)

Administracija sajta NIJE na uobičajenoj `/admin/` adresi (iz bezbednosnih razloga).
Pristupa joj se preko tajne putanje koju ste dobili pri primopredaji — vrednost je
podešena u `ADMIN_URL`.

- Otvorite u pregledaču: `https://velegradestate.rs/<vaša-tajna-putanja>/`
- Unesite korisničko ime i lozinku (login forma).
- Ako zaboravite lozinku, kontaktirajte administratora sistema da je resetuje.

Nikada ne delite ovu adresu ni pristupne podatke.

---

## 2. Nekretnine (dodavanje, izmena, preview, duplikovanje)

U levom meniju izaberite **Nekretnine**.

- **Dodavanje:** kliknite na dugme „Dodaj nekretninu" gore desno, popunite polja
  i sačuvajte.
- **Izmena:** kliknite na postojeću nekretninu iz liste, izmenite polja i sačuvajte.
- **Dvojezičan unos:** svako tekstualno polje ima verziju za srpski i za engleski
  (npr. naziv, opis). Popunite OBE verzije — sajt prikazuje odgovarajuću prema
  jeziku koji posetilac koristi.
- **Preview (pregled):** dugme „Pogledaj na sajtu" / preview otvara kako će
  nekretnina izgledati posetiocu pre nego što je objavite.
- **Duplikovanje:** za sličnu nekretninu iskoristite akciju „Dupliraj" iz liste —
  napravi kopiju koju samo doradite, umesto da unosite sve iznova.
- **Tip kolekcije (collection_type):** svaka nekretnina pripada jednoj kolekciji i
  to je VAŽNA odluka:
  - **Signature** — javna, premium ponuda. Prikazuje se svima na sajtu.
  - **Privatna kolekcija (private)** — diskretna ponuda koja NIJE javno izlistana;
    vidljiva je samo posetiocima koji su dobili pristup (npr. preko privatne forme).
  Razlika je ključna: stavite li nekretninu u Privatnu kolekciju, ona se NEĆE
  pojaviti u javnoj listi nekretnina, pa pazite koju vrednost birate.

---

## 3. Slike (upload, drag&drop reorder, hero, WebP)

U okviru nekretnine nalazi se sekcija sa slikama.

- **Upload:** dodajte slike preko dugmeta za otpremanje (upload). Možete dodati više
  slika odjednom.
- **Redosled (reorder):** slike se ređaju metodom drag&drop — uhvatite sliku mišem
  i prevucite je na željeno mesto. Redosled na sajtu prati ovaj redosled.
- **Hero slika:** prva (ili označena kao hero) slika je glavna/naslovna slika
  nekretnine koja se prikazuje najistaknutije.
- **WebP automatski:** sistem sam pravi optimizovane WebP verzije slika radi bržeg
  učitavanja — vi ne radite ništa dodatno, samo otpremite originalnu sliku.
- **Opis slike (caption):** svaka slika ima polje za kratak opis (caption). Nije
  obavezno, ali je korisno — opis pomaže snalaženju i prikazuje se uz sliku. Ako
  unosite caption, po potrebi ga popunite i na srpskom i na engleskom.

---

## 4. Upiti (Inquiry — poruke posetilaca)

Kada posetilac popuni kontakt formu ili upit za nekretninu, poruka se čuva u sekciji
**Upiti** (Inquiry) i istovremeno stiže notifikacija na email.

- Otvorite **Upiti** u meniju da vidite sve pristigle poruke.
- Svaki upit sadrži ime, kontakt i poruku posetioca.
- Upite NE brišite odmah — služe kao evidencija zainteresovanih kupaca.

---

## 5. Podešavanja sajta (SiteSettings)

U sekciji **Podešavanja** (SiteSettings) menjate globalne podatke sajta:

- kontakt telefon i email,
- adresu i podatke u podnožju (footer),
- društvene mreže i ostale opšte informacije,
- **Google Analytics ID (GA4):** polje za merni kod posete (npr. `G-XXXXXXXXXX`).
  Kada ga upišete, sajt automatski počinje da beleži statistiku posete. Ostavite li
  ga praznim, praćenje posete je isključeno. Vrednost dobijate iz Google Analytics
  naloga — u nedoumici je tražite od administratora sistema.

Promene ovde utiču na ceo sajt, pa budite pažljivi.

---

## 6. Dvojezičnost (srpski / engleski — SR/EN)

Sajt je dvojezičan: srpski i engleski.

- Posetilac bira jezik prekidačem (SR/EN) u zaglavlju.
- Za svaki sadržaj (nekretnine, stranice) popunjavate i srpski i engleski tekst.
- Ako engleski tekst nedostaje, prikazaće se prazno na engleskoj verziji — zato uvek
  popunite obe verzije.

---

## 7. Backup i restore (rezervne kopije i vraćanje)

Sistem automatski pravi dnevne rezervne kopije (backup) baze i slika i šalje ih na
udaljenu lokaciju.

- **Backup** se izvršava automatski svake noći (ne morate ništa raditi).
- **Restore (vraćanje):** ako se nešto izgubi, administrator sistema vraća podatke
  iz poslednje rezervne kopije. Vraćanje rade tehnička lica — javite im šta se desilo
  i kada (npr. „greškom obrisana nekretnina jutros").

Backup pokrivaju i bazu (svi tekstovi i podaci) i media folder (sve slike).

- **Offsite odredište:** __________ (upisati dogovoreno: Hetzner Storage Box / drugi
  host). Rezervne kopije se šalju i na ovu udaljenu lokaciju, pa podaci preživljavaju
  i potpuni gubitak servera.

---

## 8. Logovi i restart servisa (logovi / restart)

Ovo rade tehnička lica preko SSH pristupa serveru:

- **Pregled logova:** `journalctl -u velegrad -f` (uživo prati greške aplikacije).
- **Restart aplikacije:** `sudo systemctl restart velegrad`.
- **Status:** `sudo systemctl status velegrad` i `sudo systemctl status nginx`.

Ako sajt „padne" ili se ne učitava, prvi korak je provera ovih komandi i restart.

---

## 9. HTTPS sertifikat (TLS / Certbot)

Sajt koristi HTTPS (zelena brava u pregledaču) preko besplatnog Let's Encrypt
sertifikata izdatog kroz Certbot.

- Sertifikat (TLS) se **automatski obnavlja** — nije potrebna ručna intervencija.
- Provera obnove (tehnička lica): `sudo certbot renew --dry-run`.
- Ako pregledač ikada prijavi da sertifikat nije bezbedan, odmah javite administratoru
  sistema.

---

_Za sva pitanja koja nisu pokrivena ovim uputstvom obratite se administratoru sistema._
