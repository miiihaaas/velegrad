**VELEGRAD ESTATE**

*Private Advisory for Exceptional Real Estate*

**PROJEKTNI ZADATAK**

Izrada web sajta za premium nekretnine

| Klijent | Velegrad Estate  \- Đjorđije Potpara |
| :---- | :---- |
| **Verzija** | 1.0 |
| **Datum** | Maj 2026\. |
| **Namena** | Interni dokument — developer i klijent |
| **Tehnologije** | Python (Django), PostgreSQL, custom CMS |

*POVERLJIVO – SAMO ZA INTERNU UPOTREBU*

# **1\. Uvod i cilj projekta**

Ovaj dokument predstavlja kompletan projektni zadatak za izradu web sajta Velegrad Estate — boutique luxury platforme za prodaju premium i off-market nekretnina.

Cilj sajta nije klasičan portal za nekretnine. Velegrad Estate pozicioniran je kao privatna adviozrna platforma najvišeg standarda, namenjena kupcu koji ceni diskreciju, ekskluzivnost i lični pristup.

## **1.1 Pozicioniranje brenda**

Boutique luxury real estate advisory — private representation — premium off-market properties.

Klijent koji poseti sajt treba da oseti:

* Ovo nije obična agencija.

* Ovde se radi ozbiljno.

* Ovo je premium privatna usluga.

* Želim direktan kontakt.

## **1.2 Ključni utisak u prvih 5 sekundi**

**Poverenje. Diskrecija. Ekskluzivnost. Premium usluga. Lični pristup.**

Kupac ne sme imati osećaj da je došao na oglasnik — mora imati osećaj privatnog savetnika.

## **1.3 Reference brendova**

| Hero & UX | The Agency (theagencyre.com) |
| :---- | :---- |
| **Tipografija & ton** | Barnes International Realty |
| **Search & filteri** | Sotheby's International Realty |
| **Listing stranica** | The Agency |
| **Property detail** | Sotheby's \+ Compass |
| **Personal brand** | Compass individual agent pages |
| **Off-market sekcija** | Barnes \+ Christie's International |

# **2\. Vizuelni identitet i dizajn sistem**

## **2.1 Mood i ton**

Old money \+ modern luxury \+ boutique advisory.

Vizuelni identitet mora biti: premium / elegant / minimalist / sophisticated / discreet luxury.

Strogo zabranjeno:

* Kič luksuz ili previše zlatnih efekata

* Previše animacija ili letećih efekata

* Generički stock agency izgled

* Klasičan listing portal stil

* Korporativna plava boja

* Agresivna prodajna komunikacija

## **2.2 Paleta boja**

| Deep Olive | \#4A5240 — primarna boja brenda, naslovi, akcenti |
| :---- | :---- |
| **Charcoal Black** | \#1C1C1C — tekst, pozadine |
| **Warm Ivory** | \#F5F0E8 — svetle pozadine, sekcije |
| **Champagne** | \#C9A96E — premium akcentna boja, linije, ikonice |
| **Off-White** | \#FAFAF8 — alternativne sekcije |

## **2.3 Tipografija**

| Naslovi (H1, H2) | Elegant serif — preporuka: Cormorant Garamond ili Playfair Display |
| :---- | :---- |
| **Podnaslovi (H3)** | Clean sans-serif — preporuka: Inter ili DM Sans |
| **Body tekst** | Clean sans-serif — veličina 16–18px, line-height 1.7 |
| **Whitespace** | MNOGO — whitespace je dizajn element, ne praznina |
| **Boja teksta** | Ne crna — koristiti \#1C1C1C ili \#333333 |

Hierarchy: veliki naslovi → srednji podnaslovi → mali body tekst. Nikada ne koristiti Arial, previše bolda ili jarke boje.

## **2.4 Fotografija**

Sajt mora koristiti isključivo premium fotografije — editorial, cinematic, clean, realistic stil.

* Fotografija osnivača (Đorđije Potpara) — professional high-end portrait

* Nekretnine — arhitektonska fotografija profesionalnog kvaliteta

* Nikada jeftine stock slike

* Fullscreen slike — bez kompresije i pixelizacije

## **2.5 UX principi**

* Mnogo whitespace — nikada prenatrpane stranice

* Smooth transitions — fade in, slow scroll

* Subtle mikroanimacije — hover efekti, ne 'leteći' elementi

* Brz sajt — target: ispod 2 sekunde load time

* Mobile-first razvoj — premium mobilni UX je obavezan

# **3\. Struktura sajta — pregled stranica**

Sajt se sastoji od sledećih stranica i sekcija:

| 1 | Homepage (Landing page) |
| :---- | :---- |
| **2** | About / Private Advisory |
| **3** | Signature Properties (listing stranica) |
| **4** | Property Detail (pojedinačna nekretnina) |
| **5** | Private Collection (off-market) |
| **6** | Why Velegrad |
| **7** | International Clients |
| **8** | Contact |
| **9** | CMS Admin (interni) |

# **4\. Razrada po stranicama**

## **4.1 Homepage — Landing Page**

Najvažnija stranica sajta. Mora ostaviti premium utisak u prvih 5 sekundi.

### **SEKCIJA A — Hero**

Fullscreen hero (100vh) — video ili ultra premium fotografija. Preporuka: profesionalni portrait osnivača \+ premium nekretnina u pozadini.

**Vizuelni elementi:**

* Fullscreen cinematic image ili video loop bez zvuka

* Overlay — blagi tamni gradient (charcoal, opacity 40–55%)

* Ime i titula: Đorđije Potpara — Founder & Private Advisor

* Tagline — jedna snažna rečenica (serif, veliki font)

* Jedan CTA dugme

**Primer tagline-a (klijent bira):**

* DISKRECIJA. STRUČNOST. REZULTATI.

* Privatno savetovanje za izuzetne nekretnine.

* Exceptional properties. Private representation.

**CTA opcije (klijent bira jednu):**

* ZAKAŽITE PRIVATNE KONSULTACIJE

* POZOVITE DIREKTNO

* ZAKAŽITE RAZGOVOR

**Šta je zabranjeno u hero sekciji:**

* Više od jedne rečenice

* Više od jednog CTA

* Tekst koji objašnjava agenciju

* Logo preview kartica ili listing grid

### **SEKCIJA B — Personal Brand / Private Advisor**

Ovo je srce sajta. Luxury klijenti kupuju poverenje u osobu, ne u firmu. Ova sekcija mora biti snažna i autentična.

**Sadržaj:**

* Premium profesionalna fotografija osnivača — velika, ne mala

* Ime: Đorđije Potpara

* Titula: Founder & Private Advisor, Velegrad Estate

* Kratki positioning tekst — 3–5 rečenica, ton: diskretan, siguran, sofisticiran

* Ne navesti broj godina iskustva, broj transakcija — ton nije prodajni

* Direktni kontakt CTA — poziv ili WhatsApp

**Primer tona teksta:**

*"Velegrad Estate nije agencija za svakoga. Radim sa ograničenim brojem klijenata koji cene diskreciju, duboko poznavanje tržišta i lični pristup. Svaka nekretnina u našem portfoliju prolazi strogi selekcioni process."*

### **SEKCIJA C — Signature Properties (preview)**

Preview 3–4 najekskluzivnijih nekretnina — editorial prikaz, ne listing grid.

* Velike fotografije (ne manje od 400px visine po kartici)

* Naziv nekretnine ili lokacija

* Tip i kvadratura

* Cena ili "Cena na upit"

* CTA: Detaljnije

* Link na kompletnu Signature Properties stranicu

### **SEKCIJA D — Private Collection teaser**

Kratka sekcija koja najavljuje off-market listings. Samo tekst i link — bez konkretnih nekretnina.

**Primer teksta:**

*"Odabrane nekretnine nisu javno oglašene i dostupne su isključivo kvalifikovanim klijentima. Kontaktirajte nas za pristup Private Collection portfoliju."*

### **SEKCIJA E — Why Velegrad (stubovi)**

Minimalistički prikaz 5–6 ključnih vrednosti — ikonice \+ naslov \+ jedna rečenica.

* Diskrecija — Svaki razgovor i svaka transakcija ostaju strogo poverljivi.

* Pregovaranje — Zastupamo isključivo vaše interese.

* Premium mreža — Pristup nekretninama koje nisu javno dostupne.

* Međunarodni klijenti — Iskustvo sa kupcima iz FR, DE, EN tržišta.

* Lični pristup — Radimo sa ograničenim brojem klijenata.

* Pouzdanost — Rezultati koji govore sami za sebe.

### **SEKCIJA F — Contact teaser**

Jednostavna sekcija sa CTA ka contact stranici ili direktnim kontaktom.

## **4.2 About / Private Advisory stranica**

Produbljena verzija personal brand sekcije sa homepage-a. Ovo nije 'O nama' stranica u klasičnom smislu.

**Struktura:**

* Hero — naziv sekcije \+ tagline

* Fotografija osnivača — velika, editorial stil

* Bio tekst — 2–3 paragrafa, premium ton

* Filozofija rada — šta Velegrad Estate znači i kako funkcioniše

* Servisi koje nudimo — diskretno nabrojani

* CTA — Zakažite privatnu konsultaciju

**Ton bio teksta:**

Ne navesti broj godina ili transakcija. Fokus na pristup, vrednosti, diskreciju i ekskluzivnost. Pisati u prvom licu ili trećem, konzistentno.

## **4.3 Signature Properties — Listing stranica**

Ovo nije portal. Ovo je curated collection. Nikada ne prikazivati više od 12 nekretnina odjednom.

### **Filteri — premium UX (referenca: Sotheby's)**

Filteri moraju biti čisti, brzi i premium — ne smeti delovati kao oglasnik.

**Obavezni filteri:**

* Location — grad ili region

* Property Type — stan / kuća / penthouse / vila / komercijalno / zemljište

* Price Range — slider ili dropdownom

* Bedrooms — 1, 2, 3, 4, 5+

* Status — Za prodaju / Za iznajmljivanje / Cena na upit

* Keyword search — slobodan unos

**Opcioni filteri (lifestyle):**

* Waterfront / panoramski pogled

* Penthouse

* Investiciona nekretnina

* Novogradnja

**Zabranjeno:**

* Više od 8 filtera vidljivih odjednom

* Filter koji liči na KupujemProdajem stil

* Dropdowni sa 30+ opcija

### **Prikaz kartica**

Umesto 20 malih kartica — 6 do 12 velikih editorial kartica.

**Svaka kartica sadrži:**

* Hero fotografija — fullwidth kartice, min. 350px visine

* Status badge — diskretno (Za prodaju / Za iznajmljivanje / Cena na upit)

* Naziv nekretnine ili lokacija

* Tip nekretnine

* Kvadratura (m²)

* Broj spavaćih soba

* Cena ili "Cena na upit"

* CTA: Detaljnije  — hover efekat

Grid: 2 kolone na desktopu, 1 kolona na mobilnom. Puno whitespace između kartica.

## **4.4 Property Detail — Pojedinačna nekretnina**

**OVO JE NAJVAŽNIJA STRANICA. Mora izgledati kao luxury brochure, ne kao oglas.**

Referenca: Sotheby's International Realty \+ Compass.

### **Blok 1 — Hero galerija**

* Fullwidth hero fotografija — 100% širine, min. 75vh visine

* Ispod: thumbnail strip sa svim fotografijama

* Klik na thumbnail → lightbox prikaz

* Lightbox: navigacija levo/desno, keyboard support, X za zatvaranje

* Opcija: virtual tour iframe ako postoji

### **Blok 2 — Osnovno info (sticky sidebar na desktopu)**

| Naziv | Naziv nekretnine ili opis lokacije |
| :---- | :---- |
| **Lokacija** | Grad, opština, ulica (po potrebi diskretno) |
| **Tip** | Stan / Kuća / Penthouse / Vila... |
| **Kvadratura** | m² (stambena \+ ukupna) |
| **Spavaće sobe** | Broj |
| **Kupatila** | Broj |
| **Parking** | Da/Ne, broj mesta |
| **Sprat** | Sprat / od ukupno |
| **Godina gradnje** | Opciono |
| **Status** | Za prodaju / Za iznajmljivanje / Cena na upit |
| **Cena** | Cena ili "Cena na upit" |

### **Blok 3 — Premium opis (storytelling)**

Ne 3 reda teksta — već premium storytelling. Minimum 150–300 reči.

Ne pisati: 'Stan se nalazi...' — pisati kao da opisuješ životni stil.

**Primer tona:**

*"Smeštena na poslednjem spratu jedne od najekskluzivnijih adresa u Beogradu, ova penthouse rezidencija nudi panoramski pogled koji definiše pojam urbane privilegije..."*

### **Blok 4 — Features / Amenities**

Ikonice \+ tekst — minimalistički, elegant. Max 2 kolone.

* Klimatizacija / Podno grejanje / Sauna / Bazen / Lift

* Pametna kuća / Kamin / Terasa / Garaža / Ostava

* Namešten / Polunamešten / Nenamešten

### **Blok 5 — Osnova (Floor Plan)**

Ako postoji: prikaz floor plana kao slike, opcija download PDF.

### **Blok 6 — Mapa**

Diskretna mapa — prikazuje okrug ili ulicu, ne tačnu adresu (po nahođenju klijenta).

* Google Maps embed ili Mapbox

* Custom styled map u tonovima brenda

### **Blok 7 — Agent Contact Block (KLJUČNO)**

**Umesto generic contact forme — lični agent blok. Ovo brutalno podiže konverziju.**

**Sadržaj agent bloka:**

* Fotografija: Đorđije Potpara

* Ime i titula: Đorđije Potpara — Private Advisor

* Direktan poziv — one-click na mobilnom

* WhatsApp CTA

* Email

* Mini kontakt forma: ime, telefon, email, poruka

**CTA opcije:**

* Zakažite privatnu prezentaciju

* Zakažite konsultaciju

### **Blok 8 — Slične nekretnine**

Max 3 kartice — curated preporuka, ne automatski random matching.

## **4.5 Private Collection — Off-Market**

**Ovo gotovo niko na domaćem tržištu ne radi dobro. Ova sekcija drastično podiže perceived value.**

**Koncept:**

Odabrane nekretnine nisu javno oglašene. Dostupne su isključivo kvalifikovanim klijentima koji prođu kratak intake process.

**Struktura stranice:**

* Hero sekcija — tamna pozadina, premium headline

* Tekst objašnjenja — šta je Private Collection i kako funkcioniše

* Forma za pristup — ime, email, telefon, tip nekretnine koji traži, budžet

* Nakon slanja — automatski odgovor \+ ručni follow-up od strane Đorđija

**Primer headline-a:**

**"Private Collection"**

*"Odabrane nekretnine nisu javno oglašene i dostupne su isključivo kvalifikovanim klijentima."*

**Šta se NE prikazuje:**

Nikakve konkretne nekretnine, cene, adrese — samo inquiry forma. Sve ostalo ide direktnom komunikacijom.

## **4.6 Why Velegrad**

Kratka, snažna stranica koja objašnjava diferencijalnu vrednost. Minimalistički vizuelno.

**Stubovi (svaki sa ikonicom i kratkim tekstom):**

| Diskrecija | Svaka transakcija i svaki razgovor ostaju strogo poverljivi. |
| :---- | :---- |
| **Pregovaranje** | Zastupamo isključivo Vaše interese — bez kompromisa. |
| **Premium mreža** | Pristup nekretninama koje nikada neće biti javno oglašene. |
| **Međunarodni klijenti** | Iskustvo sa kupcima i investitorima iz Francuske, Nemačke i UK. |
| **Lični pristup** | Radimo sa ograničenim brojem klijenata. |
| **Pouzdanost** | Dugogodišnje prisustvo na premium segmentu beogradskog tržišta. |

## **4.7 International Clients**

Stranica namenjena stranim kupcima i investitorima. Dostupna na srpskom i engleskom.

**Sadržaj:**

* Kratak uvod — zašto Srbija / Beograd za strane investitore

* Proces kupovine nekretnine za strance — korak po korak

* Pravni okvir — osnove (ne pravni savet)

* Bankarstvo i finansiranje

* Relocation servis — opciono

* CTA — Schedule a consultation (EN)

**Jezici sajta:**

* Srpski (primarni)

* Engleski (obavezan)

Language switcher mora biti diskretan i dostupan sa svakog dela sajta (header).

## **4.8 Contact stranica**

Ultra premium. Ultra jednostavno. Luxury klijent ne želi formular sa 15 polja.

**Forma sadrži TAČNO:**

* Ime i prezime

* Telefon

* Email

* Poruka / Tip upita

**Pored forme — direktni kontakt:**

* Direktan broj telefona — one-click poziv na mobilnom

* WhatsApp dugme — direktno otvara WhatsApp

* Email link

* Adresa (opciono — diskretno)

**Mobilni UX — KRITIČNO:**

Na mobilnom: poziv mora biti one-click. WhatsApp mora biti prominentno vidljiv. Forma mora biti lako popunljiva na telefonu.

# **5\. CMS — Backend razrada**

Sajt koristi sopstveni CMS OneTouch razvijen u Python-u (Django framework). CMS je namenjen klijentu za samostalno upravljanje sadržajem bez tehničkog znanja.

## **5.1 Tehnički stack**

| Backend framework | Python — Django |
| :---- | :---- |
| **Baza podataka** | PostgreSQL |
| **Media storage** | AWS S3 ili lokalni file system (konfigurabilno) |
| **Admin interfejs** | Custom Django admin ili Django Wagtail CMS |
| **Frontend** | Django templates \+ Tailwind CSS ili custom CSS |
| **Deployment** | Linux server, Nginx, Gunicorn |
| **SSL** | Let's Encrypt — HTTPS obavezan |
| **Verzionisanje** | Git (GitHub ili GitLab) |

## **5.2 Django modeli — baza podataka**

### **Model: Property (Nekretnina)**

Centralni model sistema. Svaka nekretnina je jedan zapis u bazi.

**Polja modela:**

| id | UUID — primarni ključ |
| :---- | :---- |
| **title** | CharField(200) — naziv nekretnine |
| **slug** | SlugField — URL identifikator (auto-generisan) |
| **status** | CharField — choices: for\_sale / for\_rent / price\_on\_request / sold / rented |
| **collection\_type** | CharField — choices: signature / private / off\_market |
| **property\_type** | CharField — stan / kuca / penthouse / vila / komercijalno / zemljiste |
| **location\_city** | CharField — grad |
| **location\_district** | CharField — opština / okrug |
| **location\_address** | CharField — tačna adresa (opciono, prikazuje se po izboru) |
| **show\_address** | BooleanField — da li prikazati adresu na sajtu |
| **price** | DecimalField — cena u EUR, null ako price\_on\_request |
| **price\_on\_request** | BooleanField — prikazuje 'Price upon request' |
| **area\_sqm** | DecimalField — stambena površina m² |
| **area\_total\_sqm** | DecimalField — ukupna površina m² |
| **bedrooms** | IntegerField |
| **bathrooms** | IntegerField |
| **floor** | IntegerField — sprat |
| **total\_floors** | IntegerField — ukupno spratova |
| **parking\_spaces** | IntegerField — 0 ako nema |
| **year\_built** | IntegerField — opciono |
| **description\_sr** | RichTextField — opis na srpskom |
| **description\_en** | RichTextField — opis na engleskom |
| **description\_fr** | RichTextField — opis na francuskom, opciono |
| **features** | ManyToManyField → PropertyFeature |
| **hero\_image** | ImageField — naslovna fotografija |
| **floor\_plan** | FileField — osnova (PDF ili slika), opciono |
| **virtual\_tour\_url** | URLField — link za virtual tour, opciono |
| **latitude** | DecimalField — za mapu, opciono |
| **longitude** | DecimalField — za mapu, opciono |
| **is\_featured** | BooleanField — prikazati na homepage |
| **is\_active** | BooleanField — objavljeno/skriveno |
| **created\_at** | DateTimeField — auto |
| **updated\_at** | DateTimeField — auto |
| **meta\_title** | CharField — SEO naslov |
| **meta\_description** | TextField — SEO opis |

### **Model: PropertyImage (Galerija)**

| id | AutoField |
| :---- | :---- |
| **property** | ForeignKey → Property (on\_delete=CASCADE) |
| **image** | ImageField |
| **caption** | CharField — opciono |
| **order** | IntegerField — redosled prikaza |
| **is\_hero** | BooleanField — označava naslovnu fotografiju |

### **Model: PropertyFeature (Karakteristike)**

| id | AutoField |
| :---- | :---- |
| **name\_sr** | CharField — naziv na srpskom |
| **name\_en** | CharField — naziv na engleskom |
| **icon** | CharField — ime Feather/Lucide ikonice |
| **category** | CharField — choices: interior / exterior / building / legal |

### **Model: Inquiry (Upit)**

Svaki kontakt sa sajta čuva se u bazi.

| id | UUID |
| :---- | :---- |
| **property** | ForeignKey → Property, null=True (opšti upit ili uz nekretninu) |
| **inquiry\_type** | CharField — choices: viewing / consultation / private\_collection / general |
| **name** | CharField |
| **email** | EmailField |
| **phone** | CharField |
| **message** | TextField |
| **preferred\_language** | CharField — sr/en/fr |
| **budget\_range** | CharField — za private collection upite |
| **property\_type\_wanted** | CharField — za private collection upite |
| **status** | CharField — new / contacted / in\_progress / closed |
| **notes** | TextField — interni komentari agenta |
| **created\_at** | DateTimeField |
| **ip\_address** | GenericIPAddressField — za spam zaštitu |

### **Model: SiteSettings (Podešavanja sajta)**

Singleton model za globalna podešavanja.

| phone\_primary | CharField |
| :---- | :---- |
| **whatsapp\_number** | CharField — format: 381601234567 |
| **email\_primary** | EmailField |
| **email\_inquiries** | EmailField — kuda stižu upiti |
| **address** | TextField |
| **founder\_name** | CharField |
| **founder\_title\_sr** | CharField |
| **founder\_title\_en** | CharField |
| **founder\_photo** | ImageField |
| **founder\_bio\_sr** | RichTextField |
| **founder\_bio\_en** | RichTextField |
| **hero\_headline\_sr** | CharField |
| **hero\_headline\_en** | CharField |
| **hero\_cta\_text\_sr** | CharField |
| **hero\_cta\_text\_en** | CharField |
| **hero\_image** | ImageField |
| **hero\_video\_url** | URLField — opciono |
| **google\_analytics\_id** | CharField |
| **facebook\_pixel\_id** | CharField |
| **seo\_default\_title** | CharField |
| **seo\_default\_description** | TextField |

### **Model: Page (Statične stranice)**

| slug | CharField — unique (about, why-velegrad, international...) |
| :---- | :---- |
| **title\_sr** | CharField |
| **title\_en** | CharField |
| **content\_sr** | RichTextField |
| **content\_en** | RichTextField |
| **meta\_title** | CharField |
| **meta\_description** | TextField |
| **is\_active** | BooleanField |

## **5.3 CMS Admin interfejs**

Admin panel mora biti jednostavan i intuitivan za klijenta koji nema tehničko znanje.

### **Dashboard — početni ekran**

* Pregled: broj aktivnih nekretnina / novih upita / featured nekretnina

* Brze akcije: Dodaj nekretninu / Pogledaj upite

* Poslednji upiti (tabela sa statusom)

### **Upravljanje nekretninama**

* Listanje svih nekretnina sa filter / search

* Dodavanje nove nekretnine — wizard ili dugačka forma

* Upload fotografija — drag & drop, reorder, označiti hero

* RichText editor za opise — WYSIWYG (TinyMCE ili Quill)

* Duplikovanje nekretnine — za sličan listing

* Brzo aktiviranje / deaktiviranje (toggle)

* Preview na sajtu pre objavljivanja

### **Upravljanje upitima (Inquiries)**

* Tabela svih upita sa filterima: status / datum

* Detalj upita — sve info \+ akcija: promeni status (pročitana / nepročitana)

* Email notifikacija pri novom upitu (na konfigurisanu email adresu)

### **Podešavanja sajta**

* Izmena svih podataka iz SiteSettings modela

* Upload hero fotografije ili video URL

* Izmena tagline-a i CTA teksta

* Izmena kontakt podataka

### **Multilingual upravljanje**

* Svaki sadržaj unosi se na srpskom i engleskom (minimum)

* Jasno označena polja po jeziku u admin formi

## **5.4 URL struktura**

| / | Homepage |
| :---- | :---- |
| **/about/** | About / Private Advisory |
| **/properties/** | Signature Properties listing |
| **/properties/\<slug\>/** | Property Detail |
| **/private-collection/** | Off-Market / Private Collection |
| **/why-velegrad/** | Why Velegrad |
| **/international/** | International Clients |
| **/contact/** | Contact |
| **/en/** | Engleski prefix (i18n routing) |
| **/admin/** | Django admin — zaštićen |

## **5.5 API endpointi (opciono / AJAX)**

Za dinamičan filter na listing stranici bez page reload:

| GET /api/properties/ | Lista nekretnina sa filterima (query params) |
| :---- | :---- |
| **GET /api/properties/\<slug\>/** | Detalji jedne nekretnine |
| **POST /api/inquiries/** | Slanje upita sa sajta |
| **GET /api/settings/** | Javna podešavanja sajta (kontakt info itd.) |

## **5.6 Email notifikacije**

* Pri svakom novom upitu → email na konfigurisan adresu (inquiries email)

* Auto-reply kupcu — potvrda prijema upita

* Email template mora biti premium — ne generički Django email

* Koristiti SendGrid, Mailgun ili SMTP

## **5.7 SEO i performanse**

* Meta title i description — per nekretnina i per stranica

* Open Graph tagovi — za deljenje na društvenim mrežama

* Sitemap.xml — automatski generisan

* Robots.txt — konfigurisati

* Image optimization — WebP konverzija, lazy loading

* Schema.org markup — RealEstateListing tip

* Google Analytics 4 integracija

* Facebook Pixel integracija (opciono)

## **5.8 Sigurnost**

* HTTPS obavezan (Let's Encrypt SSL)

* Django CSRF zaštita na svim formama

* Rate limiting na contact i inquiry forme (anti-spam)

* Admin panel na nestandardnoj putanji ili IP ograničen

* Media fajlovi — ne servirati direktno, koristiti Django whitenoise ili Nginx

* Environment varijable za sve kredencijale — nikada u kodu

* Redovni backup baze podataka

# **6\. Mobilni UX — posebni zahtevi**

**Mobilna verzija nije afterthought — razvija se mobile-first.**

* Breakpointi: 375px (mobile) / 768px (tablet) / 1280px+ (desktop)

* Hero sekcija: fullscreen, tagline čitljiv na malom ekranu

* Navigacija: hamburger menu — clean, ne generički

* Poziv: one-click tel: link na svim kontakt elementima

* WhatsApp: prominentno dugme na mobilnom

* Galerija: swipe navigacija na touch uređajima

* Forme: large input fields, keyboard-appropriate input types

* Font size: minimum 16px za body tekst (Google standard)

* Touch targets: minimum 44x44px za sve interaktivne elemente

* Loading speed: target ispod 3 sekunde na 4G

# **7\. Faze razvoja i rokovi**

| Faza 1 | Setup: Django projekat, baza, CMS modeli, admin panel  |
| :---- | :---- |
| **Faza 2** | Frontend: dizajn sistem, komponente, homepage  |
| **Faza 3** | Listing & Property Detail stranice  |
| **Faza 4** | Statične stranice: About, Why, International, Contact  |
| **Faza 5** | Private Collection i inquiry sistem  |
| **Faza 6** | Multilingual (SR / EN), SEO, performance  |
| **Faza 7** | Testiranje, QA, deploy, obuka klijenta  |

Ukupno: 30 dana za kompletan projekat uz redovnu komunikaciju sa klijentom.

# **8\. Materijali koje obezbeđuje klijent**

Za uspešnu izradu sajta, klijent je obavezan da dostavi sledeće materijale pre ili tokom razvoja:

## **8.1 Obavezno (pre početka)**

* Profesionalna fotografija osnivača — high-end portrait, minimum 3 varijante

* Logo Velegrad Estate — SVG format

* Tekst za bio / About sekciju (srpski i engleski)

* Tagline i CTA tekst (iz ponuđenih opcija ili vlastiti)

* Kontakt podaci: telefon, WhatsApp, email, adresa

## **8.2 Za listing (pre lansiranja)**

* Minimum 3 nekretnine za Signature Properties sa svim podacima i fotografijama

* Fotografije nekretnina — professional quality, minimum 8–15 po nekretnini

* Opisi nekretnina na srpskom i prevodi na EN

* Cene ili potvrda za Cena na upit

## **8.3 Opciono**

* Video materijal za hero sekciju

* Floor planovi za nekretnine

* Virtual tour linkovi

# **9\. Ključne napomene za developera**

**Ovo nije klasičan IDX-style portal. Primarni cilj je premium utisak, ne broj funkcionalnosti.**

* Prioritet je uvek vizuelni kvalitet i premium osećaj nad količinom features-a

* Nikakav generički Django admin template na frontendu — custom dizajn obavezan

* Sve fotografije moraju biti optimizovane: WebP, lazy load, responsive srcset

* Svaki CTA na mobilnom mora biti one-click akcija (tel:, wa.me, mailto:)

* Ne praviti generičke error stranice — 404 mora biti premium

* Pre svakog review-a sa klijentom — staging server obavezan

* Git commit poruke moraju biti jasne i na engleskom

Pitanja developera i komunikacija sa klijentom idu isključivo kroz dogovoreni kanal.

*— Kraj dokumenta —*

Velegrad Estate © 2026 — Poverljivo