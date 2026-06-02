---
story-id: 1-4-admin-upravljanje-nekretninama-upitima-i-podesavanjima
title: Admin upravljanje nekretninama, upitima i podešavanjima
epic: 1
epic-title: "Setup, CMS modeli i brendiran admin (Faza 1)"
module: "properties, inquiries, core"
status: review
created: 2026-06-02
author: SM (Scrum Master)
fr-coverage: "FR24 (sortable galerija + media management), FR25 (Inquiry list/status workflow), FR26 (SiteSettings pun unos: kontakt/hero/tagline/founder), FR27 (dvojezičan SR/EN unos kroz Unfold fieldset-ove); arh §1.1 (sortable inline, TinyMCE, Dupliraj, preview, dvojezični fieldset-ovi)"
references:
  - _bmad-output/planning-artifacts/epics.md                # Epic 1 / Story 1.4 — IZVOR ISTINE za AC (linije ~246–267)
  - _bmad-output/planning-artifacts/architecture.md          # §1.1 admin implementacioni detalji (sortable inline, TinyMCE, Dupliraj, preview, dvojezični fieldset-ovi), §1.3 i18n polja
  - _bmad-output/planning-artifacts/PRD.md                   # FR24–FR27 (management nekretnina/upita/podešavanja, dvojezičan unos)
  - _bmad-output/implementation-artifacts/sprint-plan.md
  - _bmad-output/implementation-artifacts/1-3-brendiran-admin-i-dashboard.md                     # PRIOR — admin LJUSKA + dashboard (gotovo); 1.4 nadograđuje minimalne ModelAdmin-e
  - _bmad-output/implementation-artifacts/1-3-brendiran-admin-i-dashboard-interface-contract.md  # interface contract 1.3 (Unfold 0.95.0, registracije, singleton)
  - _bmad-output/implementation-artifacts/1-2-cms-modeli-i-migracije.md                          # model definicije: Property, PropertyImage, PropertyFeature, Inquiry, SiteSettings
---

# Story 1.4: Admin upravljanje nekretninama, upitima i podešavanjima

## Opis

As a administrator (klijent),
I want potpunu admin funkcionalnost za nekretnine, upite i podešavanja sa jasnim SR/EN unosom,
So that samostalno upravljam celokupnim sadržajem bez tehničkog znanja.

Ova priča pretvara **minimalne** Unfold `ModelAdmin`-e iz 1.3 (registrovane samo da `reverse()` u dashboard brzim akcijama radi) u **punu management funkcionalnost** (FR24–FR27). Nadovezuje se na:

- **1.2** — svih 6 modela postoji. Sva RichText polja su već realizovana kao `tinymce.models.HTMLField` (podklasa `TextField`), pa WYSIWYG dolazi bez izmene modela — potrebno je samo registrovati `tinymce` app + widget wiring. **Relevantna za 1.4 su SAMO `Property.description_*` i `SiteSettings.founder_bio_*`.** (`Page.content_*` je takođe `HTMLField`, ali `Page` admin NIJE u obimu 1.4 — pominje se samo radi potpunosti; ne dira se.) `PropertyImage` ima `order` (`Meta.ordering=["order"]`) i `is_hero` polja — spremno za sortable inline. `SiteSettings` je singleton sa svim hero/founder/kontakt poljima.
- **1.3** — `django-unfold==0.95.0` instaliran i registrovan iznad `django.contrib.admin`; brend boje (Deep Olive `#4A5240` / Champagne `#C9A96E`), site title/header „Velegrad CMS", dashboard + template override (`templates/admin/index.html`), `SiteSettings` registrovan kao singleton admin (no add kad red postoji, no delete, changelist→change redirect). `Property` i `Inquiry` su registrovani **minimalno** (`unfold.admin.ModelAdmin` bez `list_display`/`fieldsets`/`inlines`) u `properties/admin.py` i `inquiries/admin.py`. Admin je na env `ADMIN_URL` (`/admin/` → 404), CSRF baseline aktivan.

Obim ove priče je **MANAGEMENT funkcionalnost (arh §1.1)**: (1) `PropertyImage` sortable inline u `Property` adminu preko `django-admin-sortable2` (drag&drop reorder po `order`, hero toggle `is_hero`, caption); (2) TinyMCE WYSIWYG (`django-tinymce`) za sva RichText polja (`Property.description_sr/en/fr`, `SiteSettings.founder_bio_sr/en`); (3) admin action „Dupliraj" (kopira polja + features, resetuje slug i slike) + preview mehanizam za `is_active=False` nekretnine (`?preview=1`, vidljiv samo staff-u); (4) `Inquiry` admin sa filterima (status/datum) i izmenom `status`-a; (5) dvojezični SR/EN Unfold fieldset-ovi sa jasnim labelama za `Property` i pun `SiteSettings` unos (kontakt/hero/tagline/founder).

**STROGO van obima (već urađeno ili kasnije):** instalacija/tematizacija Unfold-a, brend boje, dashboard + metrike, login branding, `ADMIN_URL` montaža, `SiteSettings` singleton enforcement (add/delete pravila + changelist redirect) — **sve to je 1.3 i ne dira se** (samo se proširuje `SiteSettingsAdmin` sa fieldset-ovima). Javni `PropertyDetailView` / template-i / forme / view-side gating (`is_active`/`?preview=1` provera u view-u) su **Epik 3** — 1.4 isporučuje samo **admin-stranu** preview-a (link + reusabilan authorization helper); `django-imagekit` WebP/`srcset` rendition (6.3), email notifikacija (5.2), `{% loc %}` template tag (Epik 2/6).

## Acceptance Criteria

> AC su izvedeni primarno iz **epics.md Story 1.4** (autoritativnih 5 AC linija), dopunjeni implementacionim detaljima iz **arhitekture §1.1** i FR24–FR27 iz PRD-a. Svaki AC je konkretan i testabilan (Django admin test client sa prijavljenim **superuser**-om nad **SQLite test bazom** — isti pristup kao 1.2/1.3, vidi Dev Notes). Granica prema 1.3 je striktna: 1.3 isporuke (Unfold tema, dashboard, singleton pravila) se NE preispituju, samo se proširuju forme/inline/akcije.

- [x] **AC1 — `PropertyImage` sortable inline u `Property` adminu (epics 1.4, arh §1.1, FR24).** U `properties/admin.py`, `PropertyAdmin` (Unfold `ModelAdmin`) ima `PropertyImage` kao **sortable inline** preko `django-admin-sortable2` (`adminsortable2.admin.SortableTabularInline` ili `SortableStackedInline`), kombinovan sa Unfold inline mixin-om gde je potrebno za stil. Inline:
  - omogućava **drag&drop reorder** koji upisuje `PropertyImage.order` (inline definiše `ordering = ["order"]` i koristi sortable mehanizam paketa);
  - prikazuje/uređuje polja `image`, `caption`, `is_hero` (hero toggle), `order` (order skriven/handle po konvenciji paketa);
  - `PropertyAdmin` deklariše `inlines = [PropertyImageInline]`.
  **Napomena (KRITIČNO za render):** `django-admin-sortable2` zahteva da `"adminsortable2"` bude u `INSTALLED_APPS` (statici za sortable JS/CSS). Paket je u `requirements/base.txt` ali je **bio bare/neinstaliran** — mora se instalirati u venv I bounded-pinovati (vidi T1). **Testabilni kriterijum (svi uslovi MORAJU važiti):**
  - `django-admin-sortable2` je **instaliran** u aktivnom okruženju (import `adminsortable2` ne diže `ImportError`) i **bounded-pinovan** u `requirements/base.txt` (linija za `django-admin-sortable2` ima `>=X,<Y` raspon, NIJE bare ime — usklađeno sa 1.3 AC11 konvencijom kao `django-unfold>=0.95,<0.96`);
  - `"adminsortable2"` je u `INSTALLED_APPS`;
  - `PropertyImageInline` je deklarisan u `PropertyAdmin.inlines`;
  - **(a) Python provera (ne samo HTML):** `PropertyImageInline` je **podklasa/instanca sortable inline tipa iz `adminsortable2`** — assert u Python-u, npr. `issubclass(PropertyImageInline, adminsortable2.admin.SortableInlineAdminMixin)` (ili odgovarajući sortable inline base pinovane verzije). Plain (ne-sortable) inline NE sme proći ovaj uslov;
  - **baseline (stabilno):** GET na `Property` **add** i **change** formu (superuser) vraća HTTP 200 i renderovani HTML sadrži `PropertyImage` inline formset (management form / inline blok za `PropertyImage` — stabilna baseline provera);
  - **(b) sortable-specifični marker u HTML-u:** renderovani HTML sadrži marker koji dolazi **samo** iz aktiviranog sortable mehanizma (npr. `adminsortable`/`sortable`/order-handle klasa ili `data-`atribut koji ubacuje `adminsortable2`, NE puko prisustvo `order` polja);
  - `python manage.py check` čist.

- [x] **AC2 — TinyMCE WYSIWYG za RichText opise (epics 1.4, arh §1.1).** RichText polja koja se uređuju u adminu dobijaju **TinyMCE WYSIWYG** widget preko `django-tinymce`. Pošto su polja u 1.2 već `tinymce.models.HTMLField`, TinyMCE widget se aktivira tako što se `"tinymce"` doda u `INSTALLED_APPS` i TinyMCE URL-ovi (`tinymce.urls`) montiraju u `config/urls.py` (HTMLField automatski koristi `TinyMCE` widget kad je app registrovan). Pokrivena polja: `Property.description_sr`, `description_en`, `description_fr`, i `SiteSettings.founder_bio_sr`, `founder_bio_en`. **Testabilni kriterijum (PRIMARNA, deterministička i verzijski-robusna provera):**
  - `"tinymce"` je u `INSTALLED_APPS`;
  - `tinymce.urls` je **montiran** u `config/urls.py` (`include("tinymce.urls")`) — verifikacija: GET na neku tinymce asset rutu NE vraća 404 (rute postoje). **NAPOMENA:** instalirani `django-tinymce 5.0.0` ima `app_name = None` u `tinymce.urls` — **NEMA `tinymce:` namespace-a**, pa `reverse("tinymce:tinymce-js")` NE postoji i NE sme se koristiti. Stvarna imena ruta su `tinymce-compressor`, `tinymce-filebrowser`, `tinymce-linklist` (NEMA `tinymce-js`). Ako se uopšte koristi `reverse` provera, koristi realno ime BEZ namespace-a, npr. `reverse("tinymce-compressor")` — i tretiraj je kao **opcionu/verzijski-zavisnu** (imena ruta mogu varirati po verziji); primarni dokaz je da asset URL ne 404-uje;
  - **PRIMARNI assert:** GET na `Property` change formu (superuser) vraća HTTP 200 i renderovani HTML sadrži TinyMCE inicijalizaciju za `description_*` polja (textarea sa klasom koja sadrži `tinymce` ili tinymce init script);
  - `python manage.py check` čist; admin se i dalje diže bez `TemplateError`/500.

- [x] **AC3 — „Dupliraj" admin akcija + preview pre objave (epics 1.4, arh §1.1).**
  - **(a) Dupliraj:** `PropertyAdmin` ima admin action „Dupliraj" (`actions = ["duplicate_selected"]`) koja za svaku izabranu nekretninu pravi kopiju: **kopira sva polja** (uključujući M2M `features`), ali **resetuje `slug`** (prazan → auto-generiše se kolizijski-bezbedno u `Property.save()` iz 1.2 AC9) i **NE kopira slike** (`PropertyImage` se ne dupliraju — galerija se ponovo unosi). Kopija po konvenciji dobija nov `title` (npr. prefiks „Kopija — ") da je vidljivo razlikovanje; nova nekretnina ima nov UUID `pk`.
  - **(b) Preview (admin strana):** za nekretninu sa `is_active=False`, admin nudi **preview link** ka javnom detail view-u sa `?preview=1` (npr. preko `view_on_site`/`get_preview_url()` helpera ili dugmeta u change formi). Pošto javni `PropertyDetailView` postoji tek u **Epiku 3**, 1.4 isporučuje: (i) admin-side **link/dugme** koji generiše URL `<detail-url>?preview=1` (URL se gradi predvidljivo i testabilno — npr. `reverse` na buduću rutu ako postoji, inače dokumentovan placeholder uz TODO za Epik 3), i (ii) **reusabilan, testabilan authorization helper** (npr. `properties/preview.py::can_preview(request, obj)` ili `Property.is_visible_to(user, preview)`) koji vraća `True` samo kada je `is_active=True` **ILI** je korisnik prijavljen staff i `preview=1` — ovaj helper Epik 3 view koristi za gating. **Napomena o granici:** stvarno serviranje detail strane sa gatingom je Epik 3; 1.4 garantuje da admin daje link i da gating logika postoji kao jedinica koja se testira izolovano.
  **Testabilni kriterijum:**
  - **(a) Dupliraj:** action „Dupliraj" je registrovan u `PropertyAdmin.actions` i, izvršen nad 1 nekretninom (sa features + 1 slikom), kreira tačno jednu novu `Property` sa **različitim** `slug`-om i `pk`-om, **istim** `features` (M2M kopiran), i **bez** kopiranih `PropertyImage` (broj slika nove = 0); originalna nekretnina ostaje netaknuta. Akcija se izvršava **bez `IntegrityError`** čak i kad bi „Kopija — {title}" generisao slug koji se sudara sa postojećim (kolizijski-bezbedan save iz 1.2 AC9 + reset slug-a to pokriva).
  - **(b) Preview helper (boolean matrica):** za `is_active=False` nekretninu vraća `False` za anonimnog/preview=0, `True` za staff + `preview=1`; za `is_active=True` vraća `True` uvek.
  - **(c) Preview link u change formi:** GET na `Property` change formu za nekretninu sa `is_active=False` (superuser) vraća HTTP 200 i renderovani HTML sadrži link/dugme čiji URL sadrži string `?preview=1` (ili dokumentovani placeholder string koji sadrži `?preview=1`). **Provera NE sme zavisiti od toga da li `reverse` razrešava buduću Epik 3 detail rutu** — test asertuje (i) boolean matricu helpera i (ii) prisustvo `?preview=1` linka/placeholdera u HTML-u; NE očekuje se `NoReverseMatch`.

- [x] **AC4 — `Inquiry` admin: filteri status/datum + izmena `status`-a (epics 1.4, FR25).** `inquiries/admin.py` `InquiryAdmin` (Unfold `ModelAdmin`) ima:
  - `list_display` sa korisnim kolonama (npr. `name`, `inquiry_type`, `status`, `created_at`, opciono `property`). **Vezujuće pravilo:** ako se koristi `list_editable = ["status"]`, `status` MORA biti na indeksu ≥ 1 u `list_display` (NE prva kolona — prva kolona je link na change formu), npr. `list_display = ["name", "status", ...]`. **PAŽNJA:** `python manage.py check` NE hvata pouzdano ovaj `list_editable`/`list_display` sukob — on iskoči tek na GET changelist-a (`admin.E124`/runtime), pa test MORA uključiti GET na `Inquiry` changelist (vidi AC4/AC6 testabilni kriterijum);
  - **`list_filter`** koji uključuje **`status`** i **datum** (`created_at` — npr. `DateFieldListFilter` ili Unfold-ov range filter iz `unfold.contrib.filters` ako se koristi);
  - mogućnost **promene `status`-a** upita — minimum kroz change formu; preporučeno i kroz `list_editable = ["status"]` na changelist-u i/ili admin akcije (npr. „Označi kao kontaktiran/zatvoreno");
  - `search_fields` (npr. `name`, `email`, `phone`) i sortiranje po `-created_at` (model već ima `Meta.ordering`).
  **Napomena:** ako se koristi Unfold range/select filter (`unfold.contrib.filters`), ta pod-aplikacija MORA biti dodata u `INSTALLED_APPS` (1.3 ju namerno nije uključivala). **Testabilni kriterijum:** `"status"` je u `InquiryAdmin.list_filter` i datum-filter za `created_at` je prisutan; GET na `Inquiry` changelist (superuser) vraća HTTP 200 i renderovani HTML sadrži filter UI za status (npr. linkovi `?status=new` / `?status=closed`); izmena `status`-a postojećeg upita kroz admin (POST na change ili list_editable) menja vrednost u bazi (`Inquiry.objects.get(pk=...).status` nova vrednost).

- [x] **AC5 — Dvojezičan SR/EN unos kroz Unfold fieldset-ove + pun `SiteSettings` unos (epics 1.4, arh §1.1/§1.3, FR26, FR27).**
  - **(a) `PropertyAdmin` fieldset-ovi:** forma za nekretninu grupiše polja u **Unfold `fieldsets`** sa jasnim SR/EN labelama, tako da su dvojezični parovi vidljivo razdvojeni — npr. fieldset „Opis (SR)" sa `description_sr`, „Opis (EN)" sa `description_en` (i `description_fr` u zasebnoj, van-MVP grupi ili collapsible), plus logičke grupe za osnovne podatke / lokaciju / cenu / medije / SEO. Labela mora jasno označiti jezik (`(SR)` / `(EN)`).
  - **(b) `SiteSettingsAdmin` pun unos (FR26):** `SiteSettingsAdmin` iz 1.3 (singleton: no add kad red postoji, no delete, changelist→change redirect — **NE menjati ta pravila**) se proširuje sa `fieldsets` koji omogućavaju izmenu **svih** grupa polja: Kontakt (`phone_primary`, `whatsapp_number`, `email_primary`, `email_inquiries`, `address`), Osnivač (`founder_name`, `founder_title_sr/en`, `founder_photo`, `founder_bio_sr/en`), Hero/homepage (`hero_headline_sr/en`, `hero_cta_text_sr/en`, `hero_image`, `hero_video_url`), Analitika (`google_analytics_id`, `facebook_pixel_id`), SEO (`seo_default_title`, `seo_default_description`). Dvojezični parovi (`_sr`/`_en`) su grupisani sa jasnim labelama (FR27). **Mapiranje epics/FR26 „tagline/CTA" → stvarna polja modela (1.2):** model `SiteSettings` **NEMA** zasebno `tagline` polje — „tagline" se mapira na `hero_headline_sr/en`, a „CTA" na `hero_cta_text_sr/en` (oba su u Hero/homepage grupi). Ne uvoditi novo polje.
  **Testabilni kriterijum:**
  - **(a) `PropertyAdmin` fieldsets:** `PropertyAdmin.get_fieldsets(...)`/`fieldsets` nije prazan i razvrstava `description_sr` i `description_en` u grupe sa SR/EN oznakom; **dodatno — pokrivenost svih polja:** unija svih polja u `PropertyAdmin.fieldsets` pokriva **SVA** obavezna `Property` polja iz forme (nijedno required model polje nije ćutke ispušteno iz forme — assert da skup polja u fieldset-ovima sadrži sva editabilna `Property` polja, sem onih svesno isključenih poput auto `slug`/`created_at`/`updated_at`).
  - **(b) `SiteSettingsAdmin` fieldsets:** `SiteSettingsAdmin.fieldsets` pokriva sve gore navedene grupe polja (kontakt+hero+founder+analitika+SEO), uključujući `hero_headline_sr/en` (tagline) i `hero_cta_text_sr/en` (CTA).
  - **(c) render:** GET na `Property` change formu i na `SiteSettings` change formu (superuser) vraća HTTP 200 i renderovani HTML sadrži fieldset legende sa SR/EN labelama i input-e za sva navedena polja.

- [x] **AC6 — Regresija: `python manage.py check` čist, admin/dashboard rade, 1.3 ponašanje očuvano.** Posle dodavanja `tinymce`/`adminsortable2` (+ eventualno `unfold.contrib.filters`) u `INSTALLED_APPS`, montaže `tinymce.urls`, i proširenja ModelAdmin-a: `python manage.py check` ne prijavljuje E-nivo greške; `migrate` na SQLite i dalje prolazi (novi paketi ne uvode migracije koje bi pukle — `tinymce`/`adminsortable2` nemaju model migracije koje menjaju postojeću šemu). **1.3 ponašanje se NE sme regresirati:** admin index/dashboard renderuje „Velegrad CMS" + tri metrike + brze akcije + tabelu poslednjih upita (HTTP 200); `/admin/` → 404; `SiteSettings` singleton pravila (`has_add_permission=False` kad red postoji, `has_delete_permission=False`, changelist→change redirect) i dalje važe; `reverse("admin:properties_property_add")` i `reverse("admin:inquiries_inquiry_changelist")` se razrešavaju. **Testabilni kriterijum:** `check` bez grešaka; smoke testovi iz 1.3 (admin index 200 + „Velegrad CMS", `/admin/` 404, singleton ponašanje) i dalje prolaze; GET na `Property`/`Inquiry`/`SiteSettings` change/changelist (superuser) → 200; INSTALLED_APPS sadrži `"tinymce"` i `"adminsortable2"` (i `unfold` i dalje iznad `django.contrib.admin`); `requirements/base.txt` ima **bounded pin** (`>=X,<Y`, NE bare) za OBA paketa `django-admin-sortable2` i `django-tinymce` (1.3 AC11 konvencija). **OPCIONO (NFR-5, CSRF):** POST na „Dupliraj" admin akciju i POST za izmenu `status`-a **bez** validnog CSRF tokena vraćaju HTTP 403 (CSRF zaštita aktivna na novim action/changelist endpoint-ima) — potvrđuje da nove akcije ne zaobilaze CSRF baseline iz 1.3.

## Tasks / Subtasks

- [x] **T1 — Instalacija paketa + INSTALLED_APPS + URL wiring** *(AC1, AC2, AC4, AC6)*
  - [x] **OBAVEZNO — instaliraj nedostajuće management zavisnosti.** Iako su `django-admin-sortable2` i `django-tinymce` navedeni u `requirements/base.txt`, oba su tamo **NEPINOVANI (bare ime)**. Prema poslednjem (neverifikovanom) snapshot-u venv-a, `django-admin-sortable2` **NIJE bio instaliran u aktivnom `.venv`**, dok je `django-tinymce` bio (≈5.0.0) — **stanje venv-a može da odstupa, Dev MORA verifikovati `pip show ...` pre nego što se osloni na to.** Zato:
    - [x] Aktiviraj venv, verifikuj stanje (`pip show django-tinymce`, `pip show django-admin-sortable2`) i izričito instaliraj sortable paket ako nedostaje: `pip install django-admin-sortable2` (AC1 ga tvrdo zahteva za sortable inline — bez njega render galerije puca). Ako `pip show django-tinymce` ne vrati ništa, i njega instaliraj.
  - [x] **OBAVEZNO — bounded pin u `requirements/base.txt` (Story 1.3 AC11 konvencija).** Trenutno su linije 16–17 bare (`django-admin-sortable2`, `django-tinymce`), što krši istu 1.3 AC11 konvenciju koju ova priča referencira (vidi `django-unfold>=0.95,<0.96`). Pinuj OBA paketa na bounded raspon:
    - [x] Verifikuj instaliranu verziju sortable paketa (`pip show django-admin-sortable2`) i pinuj **bounded raspon** kompatibilan sa Django 5.2 + Unfold 0.95.0 (`>=X,<Y` stil, npr. `>=2.x,<2.(x+1)` oko instalirane verzije — NE ostavljati bare ime). Dev bira tačan raspon prema instaliranoj verziji.
    - [x] Verifikuj instaliranu verziju `django-tinymce` (`pip show django-tinymce`) i pinuj na bounded raspon oko nje (ako je ≈5.0.0, npr. `>=5.0,<5.1`; isti 1.3 AC11 stil) — NE pretpostavljati verziju, koristiti stvarnu iz `pip show`.
    - [x] Posle pina, `pip install -r requirements/base.txt` mora proći čisto sa pinovanim rasponima (oba paketa žive u `base.txt`). Ako `requirements/dev.txt` uključuje `-r base.txt`, onda i `pip install -r requirements/dev.txt` prolazi čisto — Dev verifikuje koju datoteku da koristi (izbegni mešanje: pinovi su u `base.txt`).
  - [x] U `config/settings/base.py` `INSTALLED_APPS` dodaj `"adminsortable2"` i `"tinymce"`. Ako za `Inquiry` filtere koristiš Unfold range/select filter, dodaj i `"unfold.contrib.filters"` (i, ako ti treba za forme, `"unfold.contrib.forms"`) — **iznad** `"django.contrib.admin"`, posle `"unfold"`. NE menjaj poziciju `"unfold"` (mora ostati pre `django.contrib.admin`).
  - [x] U `config/urls.py` uključi `tinymce.urls` (npr. `path("tinymce/", include("tinymce.urls"))`) tako da TinyMCE asset/spellcheck rute postoje (AC2).
  - [x] `python manage.py check` → bez grešaka; `migrate` na SQLite i dalje prolazi (AC6).

- [x] **T2 — `Property` sortable inline galerija** *(AC1, FR24)*
  - [x] U `properties/admin.py` definiši `PropertyImageInline` kao sortable inline iz `adminsortable2` (`SortableTabularInline` ili `SortableStackedInline`), kombinovan sa Unfold inline stilom gde treba; `model = PropertyImage`, polja `image`, `caption`, `is_hero`, sa reorder-om po `order` (`ordering = ["order"]`).
  - [x] U `PropertyAdmin` dodaj `inlines = [PropertyImageInline]`. Ako `adminsortable2` zahteva da i sam `PropertyAdmin` bude sortable-aware za inline (per docs pinovane verzije), primeni odgovarajući mixin/atribut.
  - [x] Verifikuj render: GET `Property` add i change forma (superuser) → 200, inline se renderuje sa sortable handle-om.

- [x] **T3 — TinyMCE WYSIWYG za RichText polja** *(AC2)*
  - [x] Pošto su `description_*` i `founder_bio_*` već `HTMLField` (1.2), aktivacija TinyMCE je preko `INSTALLED_APPS` + `tinymce.urls` (T1). Verifikuj da `HTMLField` automatski renderuje TinyMCE widget u change formama; ako je potreban `TINYMCE_DEFAULT_CONFIG` u settings (toolbar/menubar), dodaj minimalan config (Dev-ova odluka, opciono).
  - [x] Render-provera: GET `Property` change forma → HTML sadrži TinyMCE init/`class="tinymce"` za `description_*`; isto za `SiteSettings` `founder_bio_*`.

- [x] **T4 — „Dupliraj" akcija + preview helper** *(AC3, arh §1.1)*
  - [x] U `PropertyAdmin` dodaj admin action `duplicate_selected` (label „Dupliraj") koja: klonira instancu (nov `pk`/UUID), **resetuje `slug=""`** (auto-regeneracija u `save()`), prefiksira `title` (npr. „Kopija — "), kopira M2M `features` (posle `save()`), i **NE** kopira `PropertyImage` zapise. Original ostaje netaknut.
  - [x] Implementiraj reusabilan preview authorization helper (npr. `properties/preview.py::can_preview(request, obj)` ili metoda na modelu) koji vraća `True` ako `is_active=True`, ili ako je `request.user` prijavljen staff i `request.GET.get("preview") == "1"`; inače `False`. Dokumentuj da Epik 3 `PropertyDetailView` koristi ovaj helper za gating.
  - [x] U `PropertyAdmin` dodaj admin-side preview link/dugme (npr. `view_on_site` ili custom button) koji za `is_active=False` nekretninu vodi na `<detail-url>?preview=1`. Pošto detail ruta dolazi u Epiku 3, koristi `reverse` ako ruta postoji, inače dokumentovan placeholder + TODO (NE blokirati priču na Epik 3).

- [x] **T5 — `Inquiry` admin: filteri + status workflow** *(AC4, FR25)*
  - [x] U `inquiries/admin.py` proširi `InquiryAdmin`: `list_display` (`name`, `inquiry_type`, `status`, `created_at`, opciono `property`), `list_filter` sa **`status`** i **datum** (`created_at`), `search_fields` (`name`, `email`, `phone`).
  - [x] Omogući izmenu `status`-a: `list_editable = ["status"]` (zahteva da `status` nije prvi u `list_display`) i/ili admin akcije za brzo prebacivanje statusa.
  - [x] Ako koristiš Unfold range filter za datum, potvrdi `"unfold.contrib.filters"` u `INSTALLED_APPS` (T1).
  - [x] Render-provera: GET `Inquiry` changelist → 200 sa status filter UI; izmena `status`-a se snima u bazu.

- [x] **T6 — Dvojezični fieldset-ovi (`Property`) + pun `SiteSettings` unos** *(AC5, FR26, FR27)*
  - [x] U `PropertyAdmin` definiši `fieldsets` koji grupišu polja sa jasnim SR/EN labelama (npr. „Osnovno", „Lokacija", „Cena", „Opis (SR)" → `description_sr`, „Opis (EN)" → `description_en`, „Mediji", „Geo", „SEO", „Status"). `description_fr` u zasebnoj/collapsible grupi (van MVP prevoda).
  - [x] U `SiteSettingsAdmin` (iz `core/admin.py`, 1.3) dodaj `fieldsets` za sve grupe: Kontakt / Osnivač (sa `_sr`/`_en` parovima) / Hero / Analitika / SEO. **NE diraj** `has_add_permission` / `has_delete_permission` / `changelist_view` redirect iz 1.3.
  - [x] Render-provera: GET `Property` i `SiteSettings` change forme → 200 sa vidljivim SR/EN fieldset legendama i svim poljima.

- [x] **T7 — Regresija + verifikacija (1.3 očuvan, 1.4 isporučen)** *(AC1–AC6)*
  - [x] `python manage.py check` čist; `migrate` na SQLite prolazi (AC6).
  - [x] **1.3 regresija (mora i dalje prolaziti):** admin index (superuser GET) → 200 i sadrži „Velegrad CMS" + tri metrike + brze akcije + tabela poslednjih upita; `/admin/` → 404; `SiteSettings` singleton pravila netaknuta (no add kad red postoji, no delete, changelist→change redirect); `reverse` na quick-action rute prolazi.
  - [x] **AC1:** `"adminsortable2"` u `INSTALLED_APPS`; `PropertyImageInline` sortable + u `PropertyAdmin.inlines`; GET `Property` add/change → 200 sa sortable inline markup-om.
  - [x] **AC2:** `"tinymce"` u `INSTALLED_APPS`; `tinymce.urls` montiran; `Property` change forma sadrži TinyMCE za `description_*`.
  - [x] **AC3:** „Dupliraj" kreira kopiju (nov slug/pk, kopirani features, BEZ slika, original netaknut); preview helper vraća tačan boolean po (is_active, staff, preview=1) matrici.
  - [x] **AC4:** `status` + datum u `list_filter`; `Inquiry` changelist → 200 sa status filter UI; izmena `status`-a se snima.
  - [x] **AC5:** `PropertyAdmin.fieldsets` razvrstava `description_sr`/`_en` sa SR/EN labelama; `SiteSettingsAdmin.fieldsets` pokriva kontakt/hero/founder/analitika/SEO; obe change forme → 200.
  - [x] Testovi koriste Django test client + prijavljen **superuser** nad SQLite test bazom; seed preko pytest fixtura/factory-ja (stil iz 1.3 `tests/test_admin_dashboard.py`): **Property sa features + slikom**, **par Inquiry zapisa**, **i jedan `SiteSettings` red** (singleton) — `SiteSettings` red je OBAVEZAN u seed-u da `SiteSettingsAdmin` changelist→change redirect / singleton testovi ne padnu na `ObjectDoesNotExist`.

## Dev Notes

- **Izvor istine za AC = epics.md Story 1.4** (5 AC linija): (1) sortable inline galerija (`django-admin-sortable2`, reorder po `order`, hero toggle, caption); (2) TinyMCE WYSIWYG (`django-tinymce`) za `description_sr/en`; (3) „Dupliraj" action (kopira polja+features, resetuje slug/slike) + preview `?preview=1` za `is_active=False` (staff-only); (4) `Inquiry` filteri status/datum + izmena `status`-a; (5) dvojezični `_sr`/`_en` Unfold fieldset-ovi + pun `SiteSettings` unos (kontakt/hero/tagline/founder). Arhitektura §1.1 ih materijalizuje, ova priča implementira — ne preispituje.

- **GRANICA 1.3 vs 1.4 (KRITIČNO — ne regresirati 1.3).**
  - **1.3 (GOTOVO, ne dirati osim proširenja):** Unfold instalacija + brend boje (`UNFOLD` dict, Deep Olive `"74 82 64"` / Champagne `"201 169 110"`), site title/header „Velegrad CMS", `DASHBOARD_CALLBACK` + `templates/admin/index.html` (metrike/akcije/tabela), login branding, `ADMIN_URL` montaža (`/admin/` 404), `SiteSettings` singleton pravila (`has_add_permission`/`has_delete_permission`/`changelist_view` redirect), minimalna `Property`/`Inquiry` registracija. **Ova priča PROŠIRUJE** `PropertyAdmin`/`InquiryAdmin`/`SiteSettingsAdmin` (inline, fieldsets, akcije, filteri, widget) — ali **NE menja** singleton pravila niti Unfold/dashboard konfiguraciju.
  - **1.4 (OVA priča):** sortable inline, TinyMCE widget, Dupliraj, preview (admin strana + helper), Inquiry filter/status workflow, dvojezični fieldset-ovi, pun SiteSettings unos.
  - **NE u 1.4:** javni `PropertyDetailView`/template-i/forme + view-side preview gating (Epik 3), `django-imagekit` rendition (6.3), email/anti-spam (5.2), `{% loc %}` u template-ima (Epik 2/6).

- **Postojeći admin moduli (čitaj pre izmene):**
  - `core/admin.py` — sadrži `dashboard_callback` (1.3, NE dirati logiku metrika) i `SiteSettingsAdmin` (singleton). U 1.4 se `SiteSettingsAdmin` SAMO proširuje `fieldsets`-ima; add/delete/redirect ostaju.
  - `properties/admin.py` — `PropertyAdmin` je trenutno prazan minimalni `unfold.admin.ModelAdmin` (samo registracija). 1.4 dodaje `inlines`, `actions`, `fieldsets`. Django auto-discover-uje ovaj modul jer je `properties` u INSTALLED_APPS.
  - `inquiries/admin.py` — `InquiryAdmin` prazan minimalni. 1.4 dodaje `list_display`/`list_filter`/`search_fields`/`list_editable`.

- **Unfold + django-admin-sortable2 kompatibilnost (KRITIČNO — konkretan MRO redosled).** Oba paketa nude inline/admin mixine. Per Unfold docs (0.95.0), za sortable inline kombinuj Unfold-ov inline base sa `adminsortable2` sortable inline mixin-om. **Očekivani obrazac (verifikovati naspram docs pinovane verzije):** sortable **mixin ide PRVI u baseimaa**, pa Unfold inline base, npr.:
  ```python
  from adminsortable2.admin import SortableInlineAdminMixin
  from unfold.admin import TabularInline  # ili StackedInline

  class PropertyImageInline(SortableInlineAdminMixin, TabularInline):
      model = PropertyImage
      ordering = ["order"]
  ```
  Roditeljski `PropertyAdmin` možda mora biti sortable-svestan (npr. naslediti `SortableAdminBase`/odgovarajući atribut) **per docs pinovane verzije** — ovo NE over-claim-ovati; tretirati kao „očekivani redosled, verifikovati naspram docs Unfold 0.95.0 / django-admin-sortable2 pinovane verzije". Pogrešan redosled mixina (Unfold base ispred sortable mixina) = polomljen stil ili JS reorder. `"adminsortable2"` MORA biti u `INSTALLED_APPS` (statici). **PAŽNJA (setup gap):** `django-admin-sortable2` je u `requirements/base.txt` ali **NIJE instaliran u aktivnom `.venv`** i tamo je **bare/nepinovan** — T1 obavezno `pip install django-admin-sortable2` + bounded pin (1.3 AC11), inače import/render galerije puca.

- **TinyMCE — minimalna aktivacija (polja su već `HTMLField`).** U 1.2 su sva RichText polja realizovana kao `tinymce.models.HTMLField` upravo da 1.4 dobije WYSIWYG bez izmene modela. Prema poslednjem snapshot-u `django-tinymce` je bio instaliran u venv-u (≈5.0.0) — **Dev verifikuje `pip show django-tinymce` (stanje može odstupati)**; u `requirements/base.txt` je **bare/nepinovan** pa se mora bounded-pinovati (T1, 1.3 AC11). **Napomena o rutama (verzija 5.0.0):** `tinymce.urls` ima `app_name = None` → **bez namespace-a**; rute su `tinymce-compressor`/`tinymce-filebrowser`/`tinymce-linklist` (NEMA `tinymce-js`, NEMA `tinymce:` prefiksa) — vidi AC2. Aktivacija = (a) `"tinymce"` u `INSTALLED_APPS`, (b) `include("tinymce.urls")` u `config/urls.py`. `HTMLField` tada automatski koristi `TinyMCE` widget u admin formama. Opciono `TINYMCE_DEFAULT_CONFIG` za toolbar. Unfold ima `unfold.contrib.forms` za stilizaciju WYSIWYG-a — koristi samo ako je potrebno za izgled (dodaj u INSTALLED_APPS ako ga uvodiš).

- **„Dupliraj" — tačno ponašanje (arh §1.1):** kopira **polja + M2M features**, **resetuje slug** (prazan → `Property.save()` iz 1.2 auto-generiše kolizijski-bezbedno, AC9 1.2), **NE kopira slike** (`PropertyImage`). Implementacija: `obj.pk = None; obj.id = None; obj.slug = ""; obj.title = "Kopija — " + obj.title; obj.save()` pa `new.features.set(original.features.all())`. **UUID pk detalj:** pošto je pk `UUIDField(default=uuid.uuid4)`, postavljanje `obj.pk = None` (`obj.id = None`) tera `save()` da generiše **nov `uuid4`** pri INSERT-u (Django tretira instancu kao novu) — to je prihvatljivo i očekivano. **Dvostruko dupliranje:** ponovno dupliranje već-kopirane nekretnine raste naslov („Kopija — Kopija — {title}") — prihvatljivo za MVP; bitno je da akcija prolazi **bez `IntegrityError`** čak i kad bi „Kopija — {title}" slug iz reset-a/regeneracije udario u postojeći (reset slug-a na `""` + kolizijski-bezbedan save iz 1.2 AC9 to pokrivaju). Slike se svesno ne dupliraju (datoteke/storage) — galerija se unosi iznova.

- **Preview — granica prema Epiku 3 (VAŽNO).** Javni `PropertyDetailView` (`properties/views.py`) **ne postoji još** — dolazi u Epiku 3 (`properties/detail.html`, ruta `/properties/<slug>/`). Zato 1.4 NE može end-to-end testirati serviranje preview strane. 1.4 isporučuje **admin stranu**: (a) link/dugme u change formi ka `?preview=1`, (b) **izolovano testabilan** authorization helper (`can_preview(request, obj)`), koji Epik 3 view importuje. Tako je gating logika napisana i pokrivena testom sada, a Epik 3 je samo poziva u view-u. Ako detail ruta još ne postoji, admin link koristi dokumentovan placeholder URL + TODO; NE uvoditi pun view u 1.4 (van obima).

- **`Inquiry` datum filter — opcije:** Django ugrađeni `("created_at", DateFieldListFilter)` u `list_filter` je dovoljan i NE traži Unfold pod-aplikaciju. Ako želiš bogatiji range filter, koristi `unfold.contrib.filters` (tada dodaj u INSTALLED_APPS). Status izmena: `list_editable = ["status"]` zahteva da `status` postoji u `list_display` i da NIJE prva kolona (prva kolona je link na change). Alternativa/dopuna: admin akcije „Označi kao kontaktiran/U toku/Zatvoreno".

- **Dvojezični fieldset-ovi (FR27, arh §1.3):** koriste se eksplicitna `_sr`/`_en` polja iz 1.2 (NE `django-modeltranslation`). Grupisanje je puki admin `fieldsets` sa jasnim labelama jezika `(SR)`/`(EN)`. `Property.description_fr` ostaje dostupan u formi ali van fokusa prevoda (zasebna/collapsible grupa). UI labele koriste Django admin i18n + model `verbose_name` (postavljeni u 1.2); `{% trans %}`/`{% loc %}` u template-ima je Epik 2/6, NE ovde.

- **`SiteSettings` pun unos (FR26):** sva polja iz modela (1.2) raspoređena u logičke `fieldsets` u `SiteSettingsAdmin`. Singleton pravila iz 1.3 (`has_add_permission`/`has_delete_permission`/changelist redirect) se **ne menjaju** — samo se dodaje layout forme. RichText `founder_bio_sr/en` dobijaju TinyMCE (AC2). **„tagline/CTA" mapiranje (epics/FR26):** model NEMA zasebno `tagline` polje — tagline = `hero_headline_sr/en`, CTA = `hero_cta_text_sr/en` (Hero/homepage grupa). Ne uvoditi novo polje za tagline.

- **Baza za verifikaciju — SQLite test (env odluka, isto kao 1.2/1.3):** lokalni PostgreSQL NIJE dostupan. Admin testovi = Django test client + prijavljen **superuser** nad SQLite test bazom (`config/settings/test.py` + `pytest-django`). `tinymce`/`adminsortable2` nemaju problematične migracije (statici/widget, ne menjaju postojeću šemu). Seed (Property + features + slika, Inquiry zapisi) preko pytest fixtura/factory-ja — stil iz `tests/test_admin_dashboard.py` (1.3).

- **Render preduslovi (nasleđeno iz 1.3, već zadovoljeno — potvrditi):** `"django.template.context_processors.request"` u `TEMPLATES[0]["OPTIONS"]["context_processors"]` (jeste), `"django.contrib.staticfiles"` + `STATIC_URL` (jeste). TinyMCE/sortable JS+CSS se serviraju kao `{% static %}` (test client renderuje `href`-ove bez `collectstatic`).

- **`reverse()` umesto hardkodovanih admin URL-ova:** zadržati iz 1.3 — sve admin akcije/linkove preko `reverse("admin:<app>_<model>_<action>")` (radi bez obzira na `ADMIN_URL`).

- **Git poruke na engleskom** (zadatak §9) — ali ova priča je samo spec; commit radi dev priča.

## Definition of Done

- [x] `PropertyImage` je sortable inline (`django-admin-sortable2`) u `PropertyAdmin`: drag&drop reorder po `order`, `is_hero` toggle, `caption`; `"adminsortable2"` u INSTALLED_APPS; `Property` add/change forma → 200 (AC1, FR24).
- [x] TinyMCE WYSIWYG aktivan za `Property.description_sr/en/fr` i `SiteSettings.founder_bio_sr/en`: `"tinymce"` u INSTALLED_APPS, `tinymce.urls` montiran; change forme renderuju TinyMCE (AC2).
- [x] „Dupliraj" admin akcija kopira polja + `features`, **resetuje slug** i **ne kopira slike**, original netaknut, nova nekretnina nov UUID (AC3, arh §1.1).
- [x] Preview: admin-side link ka `?preview=1` + izolovano testabilan `can_preview(request, obj)` helper (staff+preview=1 ili `is_active=True`); view-side gating dokumentovan kao Epik 3 (AC3).
- [x] `InquiryAdmin`: `list_filter` sa `status` + datum, izmena `status`-a (change/`list_editable`/akcije), `list_display`/`search_fields`; `Inquiry` changelist → 200 (AC4, FR25).
- [x] `PropertyAdmin` i `SiteSettingsAdmin` imaju dvojezične/grupisane `fieldsets` sa jasnim SR/EN labelama; `SiteSettings` pun unos (kontakt/hero/founder/analitika/SEO) (AC5, FR26, FR27).
- [x] **1.3 očuvan (NE regresiran):** Unfold tema/brend boje/dashboard/metrike/login branding/`ADMIN_URL` 404 i `SiteSettings` singleton pravila i dalje rade (AC6).
- [x] `python manage.py check` čist; `migrate` na SQLite prolazi; admin/change/changelist forme renderuju bez `TemplateError`/500 (AC6).
- [x] **Obim ispoštovan:** isporučena SAMO management funkcionalnost (inline/TinyMCE/Dupliraj/preview-admin/Inquiry filteri/fieldsets); javni detail view + view-side gating (Epik 3), imagekit (6.3), email (5.2), `{% loc %}` (Epik 2/6) NISU dirani.
