---
story-id: 6-4-deploy-na-vps-i-obuka-klijenta
artifact: interface-contract
phase: RED (Test Architect — failing tests define the contract; Dev implements GREEN)
author: TEA (Test Architect)
created: 2026-06-04
test-file: tests/test_deploy_production.py
---

# Interface Contract — Story 6.4 (Deploy na VPS i obuka klijenta)

Ovaj dokument definiše KONTRAKT koji Dev mora da zadovolji u GREEN fazi. RED-faza
testovi (`tests/test_deploy_production.py`) su namerno PADAJUĆI dok implementacija
ne postoji. Test suite mora ostati ZELEN na SQLite (`config.settings.test`) — NE
sme tražiti Redis, Postgres, mrežu ni pokretanje servera.

> KRITIČNA GRANICA OBIMA: Većina ACeva ove priče (AC1 provisioning, AC2 TLS/Certbot,
> AC3 cron backup na VPS-u, AC5 server-side provere, AC7 živa obuka) su MANUAL/operativni
> na Hetzner VPS-u i NISU pytest-testabilni. Testovi pokrivaju SAMO površinu koja je
> stvarno implementabilna I lokalno verifikabilna na SQLite-u (prod settings scoping,
> non-spoofable IP resolver, requirements, .env.example, repo deploy artefakti, docs).

---

## 1. RATELIMIT key callable — non-spoofable client IP resolver (AC6b — NAJVIŠA VREDNOST)

- **Lokacija (KANONSKA):** `core/ratelimit.py` (mirror obrasca `core/storages.py` —
  čista, direktno-unit-testabilna funkcija; NE module-level settings kod).
- **Signatura:** `def client_ip_key(group, request) -> str`
  - django-ratelimit key callable potpis je `(group, request)`; vraća STRING koji
    se koristi kao ključ brojača (stvarni klijentski IP).
- **Mehanizam (ZAKLJUČAN):** koristi **`django-ipware`** (`ipware.get_client_ip`)
  sa konfigurisanom listom pouzdanih proxy-ja tako da se stvarni klijentski IP uzme
  sa ISPRAVNE pozicije u `X-Forwarded-For`, a NE spoofable krajnja (najlevlja) vrednost
  koju klijent ubacuje. django-ratelimit 4.x NE integriše ipware automatski → ovaj
  custom callable je obavezan most.
- **Trusted-proxy konfiguracija:** lista pouzdanih proxy IP-jeva (Nginx) čita se iz
  Django settinga `IPWARE_TRUSTED_PROXY_LIST` i prosleđuje
  `get_client_ip(request, proxy_trusted_ips=settings.IPWARE_TRUSTED_PROXY_LIST)`.
  Resolver mora vratiti IP koji je ipware razrešio kao stvarnog klijenta IZA
  pouzdanog proxy-ja.
- **REMOTE_ADDR fallback (OBAVEZAN):** `django-ipware` `get_client_ip` vraća `None`
  kada nema upotrebljive prosleđene adrese (npr. nema `X-Forwarded-For`, ili strict
  brojanje hopova ne prolazi). U tom slučaju resolver MORA pasti na
  `request.META["REMOTE_ADDR"]` (nikad ne sme vratiti `None`/prazno — to bi srušilo
  rate-limit ključ). Tj. `ip = get_client_ip(...)[0] or request.META.get("REMOTE_ADDR", "")`.
- **STRICT-mode semantika (VAŽNO za ispravnu implementaciju i oblik testa):**
  django-ipware poziva python-ipware u **strict** režimu → broj prosleđenih hopova
  mora da se poklopi sa dužinom trusted liste. Za jedan pouzdan Nginx hop, realan
  lanac koji Nginx pravi (`$proxy_add_x_forwarded_for`) je
  `"<real_client>, <trusted_nginx>"` (TAČNO jedan hop pre pouzdanog proxy-ja) i
  resolver vraća `<real_client>`. Ako klijent PREPEND-uje lažnu vrednost, lanac
  postaje `"<spoof>, <real_client>, <trusted_nginx>"` (jedan hop VIŠE) → strict
  odbacuje → fallback na `REMOTE_ADDR` (pouzdani proxy). U OBA slučaja spoof vrednost
  NIKADA nije ključ.
- **Non-spoofable invarijanta (kontrakt koji test proverava):**
  - Realan lanac `HTTP_X_FORWARDED_FOR = "<real_client>, <trusted_nginx>"` → resolver
    vraća `<real_client>` (pozitivan test).
  - Spoof-prepend lanac `HTTP_X_FORWARDED_FOR = "<spoof>, <real_client>, <trusted_nginx>"`
    → resolver NIKADA ne vraća `<spoof>` (negativan/adversarial test).
- **ZABRANJENO:** naivni `key='header:x-forwarded-for'` (trivijalno spoofable) NE sme
  biti rate-limit ključ u produkciji.

## 2. Prod CACHES env contract (AC6a)

- **Scoping:** `config/settings/base.py` (i otud naslednici `test`/`dev`) ZADRŽAVAJU
  `LocMemCache` kao `default` — test suite ne sme tražiti Redis.
- **Override:** `config/settings/prod.py` override-uje `CACHES["default"]` na DELJENI
  cache backend vođen env-om.
  - **Env var:** `CACHE_URL` (prihvatljivo i `REDIS_URL` kao alias) → vodi do
    `django_redis.cache.RedisCache` (ZAKLJUČAN default klijent = `django-redis`;
    `pymemcache`/Memcached dokumentovana alternativa).
  - prod.py izvor mora referencirati deljeni backend (`django_redis.cache.RedisCache`
    ILI `RedisCache`) i env (`CACHE_URL`/`REDIS_URL`).
- **Verifikacija (RED test, source/import-assertion):** import `config.settings.base`
  (i `test`) i dalje daje `LocMemCache`; `prod.py` izvor sadrži deljeni-cache override
  vezan za env. (NE traži živi Redis — prati `_import_settings`/`_read` obrazac.)

## 3. SILENCED_SYSTEM_CHECKS (AC6c)

- `base.py` trenutno utišava `django_ratelimit.E003` + `W001` (LocMemCache razlog).
- **Kontrakt:** u PROD kontekstu utišavanje E003/W001 mora biti UKLONJENO (deljeni
  cache obara razlog). Dozvoljeno uslovno: zadržati za dev/test (LocMemCache),
  ukloniti za prod.
- **Verifikacija (RED test):** `prod.py` izvor NE sme ostaviti E003/W001 utišane —
  ili prod.py eksplicitno postavlja `SILENCED_SYSTEM_CHECKS = []` (prazno / bez ratelimit
  unosa), ili je utišavanje uslovljeno tako da prod ne nasleđuje E003/W001. Test asertuje
  da prod modul efektivno NE utišava `django_ratelimit.E003`/`W001`.

## 4. Mailgun send-timeout (AC4)

- **Mehanizam (ZAKLJUČAN):** eksplicitan send-timeout za anymail Mailgun backend preko
  **custom `requests` session-a sa timeout-om** (preporučeno ~10s) ILI
  `ANYMAIL["REQUESTS_TIMEOUT"]` ako verzija anymail-a podržava. Konfiguriše se u
  `config/settings/prod.py`.
- **ZABRANJENO:** Celery / async stek (nema brokera u arhitekturi/requirements).
  Reč `celery` se NE sme pojaviti u prod.py.
- **Verifikacija (RED test, source + settings):** prod.py izvor sadrži dokaz timeout
  konfiguracije (`REQUESTS_TIMEOUT` u `ANYMAIL`, ILI custom `requests.Session` sa
  `timeout`); broj koji liči na ~10s timeout prisutan; `celery` odsutan.

## 5. Novi requirements (prod.txt — NE base.txt)

- `requirements/prod.txt` DODAJE: **`django-redis`** (deljeni cache) i
  **`django-ipware`** (klijentski IP). Oba kao aktivne (ne-komentarisane) linije.
- Ne smeju zagaditi `requirements/base.txt` (mirror obrasca `test_gunicorn_in_prod_not_base`).

## 6. Nove .env varijable (.env.example)

- `.env.example` DODAJE produkcioni cache env: **`CACHE_URL`** (ILI `REDIS_URL`) —
  npr. `redis://127.0.0.1:6379/1`.
- Sve POSTOJEĆE obavezne varijable ostaju (SECRET_KEY, DEBUG, ALLOWED_HOSTS,
  DATABASE_URL, ADMIN_URL, STORAGE_BACKEND, MAILGUN_API_KEY, MAILGUN_SENDER_DOMAIN,
  DEFAULT_FROM_EMAIL, GOOGLE_ANALYTICS_ID) — `tests/test_project_setup.py` ih i dalje
  mora videti (ne dirati taj test).

## 7. Deploy artefakti (repo — versionisani šabloni, BEZ kredencijala)

- **`deploy/gunicorn.service`** (systemd unit): bind na Unix socket; `EnvironmentFile=`;
  `DJANGO_SETTINGS_MODULE=config.settings.prod`; `Restart=always`; non-root `User=`.
- **`deploy/nginx.conf`** (ILI `deploy/nginx-velegrad.conf`): `location /static/` +
  `location /media/` direktno sa diska; `proxy_pass` na gunicorn unix socket;
  `proxy_set_header X-Forwarded-Proto`; `proxy_set_header X-Forwarded-For`.
- **`scripts/backup_db.sh`**: `pg_dump` + retencija + offsite korak.
- **`scripts/backup_media.sh`**: `tar`/`rsync` `media/` + offsite korak.
- **Verifikacija (RED test):** file-existence + content-substring (plain text / shebang).
  Skripte se NE izvršavaju.

## 8. Klijentska primopredaja/obuka dokumentacija (AC7)

- **Putanja:** `docs/primopredaja-klijent.md` (srpski, netehnički ton).
- **Pokriva teme (test = postojanje + ključne reči):** login / `ADMIN_URL`,
  nekretnine, slike / reorder, upiti, SiteSettings, dvojezičnost,
  backup / restore, logovi / restart, TLS.

---

## MANUAL / VPS (NIJE pytest) — operativno verifikovano, ne automatizovanim testom

Ovi ACevi se izvršavaju i verifikuju ručno NA Hetzner VPS-u (DoD/operativni koraci),
NE pytest-om. Ne pišu se testovi koji bi tražili Postgres, živi server, Nginx, systemd
ili mrežu.

- **AC1 (operativni deo)** — VPS provisioning: Ubuntu LTS, non-root app korisnik,
  Python 3.13 (deadsnakes/source; 3.12 fallback), PostgreSQL 16, Nginx; `migrate`
  protiv stvarne PostgreSQL 16 (PRVI PUT — kritičan rizik); `collectstatic`;
  `manage.py check --deploy`; `curl -I` static/media served-by-nginx.
- **AC2** — Certbot/Let's Encrypt sertifikat, HTTP→HTTPS redirect, auto-renew timer,
  `certbot renew --dry-run`, HSTS header na HTTPS, bez redirect petlje.
- **AC3 (izvršenje)** — cron unosi (`crontab -l`), ne-prazan `pg_dump`, TEST-RESTORE u
  scratch bazu, offsite liveness (log poslednjeg cron run-a).
- **AC4 (DNS deo)** — Mailgun domen „Verified" (SPF/DKIM), deliverability test inquiry.
- **AC5 (server deo)** — `manage.py check --deploy` na serveru, `GET /admin/`→404,
  `GET /<ADMIN_URL>/`→200, pogrešan Host→400, git-grep za hardkodovane kredencijale.
- **AC6 (runtime deo)** — Redis kao sistemski servis na 127.0.0.1:6379; multi-worker
  Gunicorn deli rate-limit brojač (429 posle praga); `manage.py check` (prod) bez E003/W001.
- **AC7 (živa obuka)** — sprovedena obuka klijenta; klijent samostalno demonstrira
  end-to-end zadatak; staging odluka zabeležena.
- **NFR-1 (T10)** — Lighthouse/PageSpeed na prod-u; `generateimages`.

---

## Test inventar (tests/test_deploy_production.py)

| # | AC | Tip | Šta proverava |
|---|----|-----|---------------|
| 1 | AC6a | unit/source | base import → LocMemCache (dev/test ne traže Redis) |
| 2 | AC6a | unit/source | test settings → LocMemCache |
| 3 | AC6a | source | prod.py override-uje CACHES na deljeni backend |
| 4 | AC6a | source | prod.py deljeni cache vezan za env (CACHE_URL/REDIS_URL) |
| 5 | AC6a | negative | prod.py CACHES default NIJE LocMemCache |
| 6 | AC6b | unit/security | client_ip_key callable postoji + potpis (group, request) |
| 7 | AC6b | security | realan lanac `<real_client>, <trusted_nginx>` → vraća `<real_client>` (strict, jedan hop) |
| 8 | AC6b | security | čisti zahtev bez XFF → REMOTE_ADDR fallback (ipware vraća None) |
| 9 | AC6b | negative | spoof-prepend `<spoof>, <real>, <nginx>` → resolver NIKADA ne vraća `<spoof>` |
| 10 | AC6b | source | prod RATELIMIT key callable ožičen na core.ratelimit.client_ip_key |
| 11 | AC6c | source/negative | prod NE utišava django_ratelimit.E003/W001 |
| 12 | AC6c | source | base i dalje sme zadržati utišavanje (dev/test LocMemCache) |
| 13 | AC4 | source | prod.py konfiguriše Mailgun send-timeout (~10s) |
| 14 | AC4 | negative | prod.py NE uvodi Celery/async |
| 15 | AC5 | source | prod.txt sadrži django-redis |
| 16 | AC5 | source | prod.txt sadrži django-ipware |
| 17 | AC5 | negative | django-redis/ipware NE u base.txt |
| 18 | AC5 | source | .env.example dodaje CACHE_URL/REDIS_URL |
| 19 | AC5 | source | .env.example zadržava sve postojeće obavezne var |
| 20 | AC1 | existence | deploy/gunicorn.service postoji + sadržaj |
| 21 | AC1 | existence | deploy nginx vhost postoji + sadržaj (XFF/XFP/proxy_pass) |
| 22 | AC3 | existence | scripts/backup_db.sh postoji + pg_dump + offsite |
| 23 | AC3 | existence | scripts/backup_media.sh postoji + media + offsite |
| 24 | AC7 | existence | docs/primopredaja-klijent.md postoji + pokriva sve teme |
