---
generated: 2026-06-01
last_updated: 2026-06-01
project: VELEGRAD (Velegrad Estate)
status: 'active'
tracking_file: sprint-status.yaml
sources:
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/PRD.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-06-01.md
  - docs/Velegrad Estate - Projektni zadatak.docx.md
  - docs/OpenDesignFiles/
---

# Velegrad Estate — Sprint Plan

Prateći dokument uz `sprint-status.yaml`. Obim je **zaključan**: tačno **6 epika / 16 priča**, linearni redosled **1.1 → 6.4** sa backward zavisnostima. Tehničke odluke su zaključane u arhitekturi i **ne preispituju se** ovde. `epics.md` (FR Coverage Map) je **izvor istine** za traceability — ne prozni per-page opis iz PRD-a (IR #3).

## Princip redosleda

Priče se izvršavaju **sekvencijalno**, svaka priča zavisi unazad od prethodnih. Epik se prebacuje u `in-progress` kad se kreira prva priča, u `done` kad sve njegove priče dođu do `done`. Retrospektiva je `optional` po epiku.

## Usklađenost sa fazama razvoja (zadatak §7)

| Epik | Naslov | Faza §7 |
|------|--------|---------|
| 1 | Setup, CMS modeli i brendiran admin | Faza 1 |
| 2 | Frontend dizajn sistem i Home | Faza 2 |
| 3 | Signature listing i Property Detail | Faza 3 |
| 4 | Statične stranice (About, International, Contact) | Faza 4 |
| 5 | Private Collection i inquiry sistem | Faza 5 |
| 6 | Multilingual, SEO, performanse i deploy | Faza 6 + 7 |

## Pregled priča i FR traceability

> FR/NFR pokrivenost preuzeta direktno iz FR Coverage Map u `epics.md` (IR #3).

### Epik 1 — Setup, CMS modeli i brendiran admin *(Faza 1)*
**Pokriva:** FR23, FR24, FR25, FR26, FR27 + temelj (svi modeli §5.2; NFR-5 deo — env/admin path/CSRF).

| Story | Naslov | Status key | FR/NFR |
|-------|--------|-----------|--------|
| 1.1 | Inicijalizacija Django projekta i okruženja | `1-1-inicijalizacija-django-projekta-i-okruzenja` | temelj (arh §0,§2,§3,§4; NFR-5) |
| 1.2 | CMS modeli i migracije | `1-2-cms-modeli-i-migracije` | svi modeli §5.2; arh §1.3 |
| 1.3 | Brendiran admin i dashboard | `1-3-brendiran-admin-i-dashboard` | FR23; NFR-5 (admin path) |
| 1.4 | Admin upravljanje nekretninama, upitima i podešavanjima | `1-4-admin-upravljanje-nekretninama-upitima-i-podesavanjima` | FR24, FR25, FR26, FR27 |

### Epik 2 — Frontend dizajn sistem i Home *(Faza 2)*
**Pokriva:** FR1, FR2, FR3, FR4, FR5, FR6, FR22 + UX-DR1–5, NFR-2 (bazni responsive).

| Story | Naslov | Status key | FR/NFR |
|-------|--------|-----------|--------|
| 2.1 | Integracija dizajn sistema i bazni layout | `2-1-integracija-dizajn-sistema-i-bazni-layout` | FR22, UX-DR1–5, NFR-2 |
| 2.2 | Home stranica povezana sa bazom | `2-2-home-stranica-povezana-sa-bazom` | FR1, FR2, FR3, FR4, FR5, FR6 |

> **IR #1 — i18n od PRVOG template-a (obavezno u Epiku 2):** sve UI stringove pisati kroz `{% trans %}` / `{% loc %}` **već pri pisanju `base.html` i Home template-a**. Language switcher scaffolding takođe ide ovde. Cilj: Epik 6 (6.1) samo **dodaje prevode (`.po`/`.mo`) + `/en/` routing**, bez naknadnog refaktora template-a. Svaki novi template od 2.1 nadalje mora od starta koristiti `{% trans %}`/`{% loc %}` — ne hardkodovati stringove.

### Epik 3 — Signature listing i Property Detail *(Faza 3)*
**Pokriva:** FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16.

| Story | Naslov | Status key | FR/NFR |
|-------|--------|-----------|--------|
| 3.1 | Signature listing sa server-side filterima | `3-1-signature-listing-sa-server-side-filterima` | FR8, FR9 |
| 3.2 | Property Detail stranica | `3-2-property-detail-stranica` | FR10, FR11, FR12, FR13, FR14, FR15, FR16 |

> **IR #2 (deo 1):** Agent Contact Block (FR15) kreira `Inquiry(inquiry_type=viewing)` već ovde — forma **čuva upit u bazu i bez emaila**. Email notifikacija/auto-reply stiže tek u 5.2 (vidi napomenu kod Epika 5).

### Epik 4 — Statične stranice (About, International, Contact) *(Faza 4)*
**Pokriva:** FR7, FR19, FR20, FR21.

| Story | Naslov | Status key | FR/NFR |
|-------|--------|-----------|--------|
| 4.1 | About i International stranice iz CMS-a | `4-1-about-i-international-stranice-iz-cms-a` | FR7, FR19 |
| 4.2 | Contact stranica sa formom i direktnim kontaktom | `4-2-contact-stranica-sa-formom-i-direktnim-kontaktom` | FR20, FR21; NFR-5 (CSRF) |

> **IR #2 (deo 2):** Contact forma (FR20) kreira `Inquiry(inquiry_type=general/consultation)` i **čuva u bazu bez emaila** u ovoj fazi. Agent dotle prati nove upite kroz admin (Upiti tabela iz 1.4). Email je **aditivan** u 5.2.

### Epik 5 — Private Collection i inquiry sistem *(Faza 5)*
**Pokriva:** FR17, FR18, FR28 + NFR-5 deo (rate-limit/honeypot).

| Story | Naslov | Status key | FR/NFR |
|-------|--------|-----------|--------|
| 5.1 | Private Collection stranica i intake forma | `5-1-private-collection-stranica-i-intake-forma` | FR17, FR18; NFR-5 (anti-spam) |
| 5.2 | Inquiry pipeline (čuvanje, notifikacija, auto-reply, anti-spam) | `5-2-inquiry-pipeline-cuvanje-notifikacija-auto-reply-anti-spam` | FR28; FR25 (notifikacija); NFR-5 |

> **IR #2 (sekvenca upita — poznata i namerna):** Forme hvataju upite ranije (Epik 3 viewing, Epik 4 general/consultation), ali **email notifikacija agentu + premium auto-reply kupcu stižu tek u 5.2**. To je očekivano: do 5.2 svi upiti su sigurno sačuvani u bazi (`status=new`) i vidljivi u adminu; 5.2 dodaje email sloj (Mailgun/anymail, dva toka) **iznad** postojećeg snimanja — nije refaktor, već dodatak.

### Epik 6 — Multilingual, SEO, performanse i deploy *(Faza 6 + 7)*
**Pokriva:** bez novih FR-ova — realizuje NFR-1, NFR-3, NFR-4 i finalizuje NFR-2/NFR-5.

| Story | Naslov | Status key | FR/NFR |
|-------|--------|-----------|--------|
| 6.1 | Dvojezičnost SR/EN | `6-1-dvojezicnost-sr-en` | NFR-4 |
| 6.2 | SEO | `6-2-seo` | NFR-3 |
| 6.3 | Performanse i optimizacija slika | `6-3-performanse-i-optimizacija-slika` | NFR-1 |
| 6.4 | Deploy na VPS i obuka klijenta | `6-4-deploy-na-vps-i-obuka-klijenta` | NFR-5 (HTTPS/backup); zadatak §7 Faza 7 (obuka) |

> **Veza sa IR #1:** ako je i18n dosledno primenjen od Epika 2, 6.1 je svedena na `makemessages` → prevod → `compilemessages` + `i18n_patterns` (`prefix_default_language=False`), bez diranja postojećih template-a.

## Eksterna zavisnost — klijentski blokirajući inputi (IR #4)

> **Ovo NIJE kodna priča** i ne ulazi u 16 priča sprinta. Prikuplja se **paralelno sa Epikom 1** i predstavlja eksternu zavisnost za **lansiranje** (gating za Epik 2/3 sadržaj i go-live).

Potrebno od klijenta (Đorđije):
- [ ] Foto osnivača (visoka rezolucija)
- [ ] Logo u SVG formatu
- [ ] Bio osnivača — **SR i EN**
- [ ] Tagline + CTA tekst (hero)
- [ ] Minimum **3 nekretnine** sa fotografijama + cenama (za Signature listing/Home featured)

Tehnički razvoj može teći sa placeholder sadržajem (placeholder SVG fallback iz arhitekture §5), ali **lansiranje je blokirano** dok ovi inputi ne stignu.

## Status tok

- **Epik:** `backlog` → `in-progress` → `done`
- **Story:** `backlog` → `ready-for-dev` → `in-progress` → `review` → `done`
- **Retrospektiva:** `optional` ↔ `done`

Početno stanje: sve priče `backlog`, sve retrospektive `optional` (folder priča još prazan).

## Sledeći koraci

1. Pokreni Epik 1 → kreiraj prvu priču (`create-story` za 1.1) — `epic-1` automatski prelazi u `in-progress`.
2. Paralelno: pošalji klijentu listu blokirajućih inputa (IR #4 gore).
3. Od Epika 2 nadalje: svaki template piši sa `{% trans %}`/`{% loc %}` od prvog reda (IR #1).
4. Statuse ažuriraj u `sprint-status.yaml` kako priče napreduju; re-run sprint-planning osvežava auto-detekciju kad se kreiraju story fajlovi.
