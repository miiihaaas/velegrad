"""
RED-phase contract tests for Story 6.4 — "Deploy na VPS i obuka klijenta".

These tests define the CONTRACT the developer must satisfy in the GREEN phase.
They are written BEFORE the production-deploy implementation exists, so every
test here MUST FAIL or ERROR until the Dev wires it up.

SCOPE DISCIPLINE (read the interface contract):
  Most of Story 6.4 (AC1 provisioning, AC2 TLS/Certbot, AC3 cron execution on the
  VPS, AC5 server-side checks, AC7 live training) is MANUAL / VPS — it runs on the
  Hetzner box and is verified operationally, NOT by pytest. We do NOT fake those
  with tests that cannot run locally. These tests cover ONLY the surface that is
  genuinely implementable AND verifiable locally on SQLite:
    - AC6a  prod CACHES shared-cache override (scoped; dev/test keep LocMemCache)
    - AC6b  non-spoofable client-IP resolver (core.ratelimit.client_ip_key) — HIGHEST VALUE
    - AC6c  removal of SILENCED_SYSTEM_CHECKS (E003/W001) in prod
    - AC4   Mailgun send-timeout (custom requests session / REQUESTS_TIMEOUT — NOT Celery)
    - AC5   new prod requirements (django-redis, django-ipware) + new .env vars
    - AC1   deploy artifacts (deploy/gunicorn.service, deploy nginx vhost)
    - AC3   backup scripts (scripts/backup_db.sh, scripts/backup_media.sh)
    - AC7   client handover doc (docs/primopredaja-klijent.md)

Design rules (copied from tests/test_project_setup.py — proven patterns):
  - Tests are ISOLATED.
  - Settings/source imports happen INSIDE test bodies via _import_settings / _read.
  - We do NOT require a live Redis / Postgres / Nginx / server / network.
  - prod-only behaviour is asserted via SOURCE inspection (_read) so a missing
    Redis client or env var does not turn a clean RED into an import crash.
  - Each test maps to an acceptance criterion via a `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    6-4-deploy-na-vps-i-obuka-klijenta-interface-contract.md
"""
import importlib
import re
from pathlib import Path

import pytest

# Repo root = parent of this tests/ package.
ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Helpers (mirror tests/test_project_setup.py)                                 #
# --------------------------------------------------------------------------- #
def _read(*relparts):
    """Return text of a repo-relative file, or '' if it does not exist yet."""
    p = ROOT.joinpath(*relparts)
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _exists(*relparts):
    return ROOT.joinpath(*relparts).is_file()


def _import_settings(name):
    """Import a config.settings.<name> module fresh and return it."""
    mod = f"config.settings.{name}"
    if mod in importlib.sys.modules:
        return importlib.reload(importlib.sys.modules[mod])
    return importlib.import_module(mod)


def _strip_comments(src):
    """Drop full-line and inline `#` comments so source-substring asserts test
    REAL configuration, not a comment that merely mentions the keyword."""
    out = []
    for ln in src.splitlines():
        # naive but sufficient: cut at the first '#'. Settings files here do not
        # use '#' inside string literals for the tokens we assert on.
        out.append(ln.split("#", 1)[0])
    return "\n".join(out)


def _read_nginx_vhost():
    """Return the deploy Nginx vhost text under either accepted filename."""
    for fname in ("nginx.conf", "nginx-velegrad.conf", "velegrad.conf", "nginx"):
        txt = _read("deploy", fname)
        if txt:
            return txt
    return ""


def _active_requirement_lines(text):
    """Non-comment, non-blank requirement lines."""
    return [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


# =========================================================================== #
# AC6a — Production shared cache, SCOPED (dev/test keep LocMemCache)           #
# =========================================================================== #
def test_base_cache_remains_locmem_so_test_suite_needs_no_redis():
    # AC6a: importing config.settings.base must still yield LocMemCache for the
    # `default` alias — the test/dev suite MUST NOT require a live Redis.
    base = _import_settings("base")
    backend = base.CACHES["default"]["BACKEND"]
    assert backend.endswith("locmem.LocMemCache"), (
        f"base.py default cache must stay LocMemCache (scoping discipline), got {backend!r}"
    )


def test_test_settings_cache_remains_locmem():
    # AC6a: config.settings.test (what pytest runs against) must keep LocMemCache.
    tst = _import_settings("test")
    backend = tst.CACHES["default"]["BACKEND"]
    assert backend.endswith("locmem.LocMemCache"), (
        f"test settings default cache must stay LocMemCache, got {backend!r}"
    )


def test_prod_overrides_caches_to_shared_backend():
    # AC6a: prod.py must OVERRIDE CACHES["default"] to a SHARED backend
    # (django-redis). Source assertion — does NOT require a live Redis.
    src = _strip_comments(_read("config", "settings", "prod.py"))
    assert src, "config/settings/prod.py does not exist"
    assert re.search(r"\bCACHES\b", src), (
        "prod.py must override CACHES with a shared cache backend (AC6a)"
    )
    assert re.search(r"RedisCache|django_redis", src), (
        "prod.py CACHES override must use a shared backend "
        "(django_redis.cache.RedisCache) — not the per-process LocMemCache"
    )


def test_prod_shared_cache_is_env_driven():
    # AC6a: the shared cache must be driven by an env var (CACHE_URL / REDIS_URL),
    # never a hardcoded location — credentials/locations come from env (NFR-5).
    src = _strip_comments(_read("config", "settings", "prod.py"))
    assert src, "config/settings/prod.py does not exist"
    assert re.search(r"CACHE_URL|REDIS_URL", src), (
        "prod.py shared cache must read its location from env (CACHE_URL/REDIS_URL)"
    )


def test_prod_default_cache_is_not_locmem():
    # AC6a (negative): prod.py must NOT leave the default cache on per-process
    # LocMemCache — that is exactly the multi-worker rate-limit leak this story fixes.
    src = _strip_comments(_read("config", "settings", "prod.py"))
    assert src, "config/settings/prod.py does not exist"
    # prod must REDEFINE CACHES (own override block) AND that block must not be
    # LocMemCache. We require BOTH: a CACHES assignment present in prod's own
    # source, and no LocMemCache assignment surviving there. (A prod.py that
    # merely inherits base's LocMemCache without overriding therefore FAILS.)
    assert re.search(r"^\s*CACHES\s*=", src, re.M), (
        "prod.py must define its own CACHES override (not inherit base LocMemCache)"
    )
    assert "LocMemCache" not in src, (
        "prod.py must not assign LocMemCache to the default cache "
        "(shared cache required for multi-worker rate-limit)"
    )


# =========================================================================== #
# AC6b — Non-spoofable client-IP resolver (HIGHEST-VALUE TEST)                 #
# =========================================================================== #
# The trusted Nginx proxy address used across the IP tests below.
_TRUSTED_PROXY = "10.0.0.1"


def _make_request(xff=None, x_real_ip=None, remote_addr="127.0.0.1"):
    """Build a fake request with optional X-Forwarded-For / X-Real-IP headers.

    X-Real-IP simulates what Nginx sets via ``proxy_set_header X-Real-IP
    $remote_addr;`` — i.e. the trustworthy direct-peer value Nginx OVERWRITES on
    every request (a client-supplied X-Real-IP can never reach the app).
    """
    from django.test import RequestFactory

    rf = RequestFactory()
    headers = {}
    if xff is not None:
        headers["HTTP_X_FORWARDED_FOR"] = xff
    if x_real_ip is not None:
        headers["HTTP_X_REAL_IP"] = x_real_ip
    req = rf.get("/", REMOTE_ADDR=remote_addr, **headers)
    return req


def _trust_proxy(settings):
    """Point ipware's trusted-proxy list at our fake Nginx for the duration of a test."""
    settings.IPWARE_TRUSTED_PROXY_LIST = [_TRUSTED_PROXY]


def test_client_ip_key_callable_exists_with_ratelimit_signature():
    # AC6b: a custom RATELIMIT key callable must live at core.ratelimit.client_ip_key
    # with the django-ratelimit (group, request) signature.
    import inspect

    mod = importlib.import_module("core.ratelimit")
    fn = getattr(mod, "client_ip_key", None)
    assert callable(fn), "core.ratelimit.client_ip_key must be a callable"
    params = list(inspect.signature(fn).parameters)
    assert len(params) == 2, (
        f"client_ip_key must take (group, request) per django-ratelimit, got {params!r}"
    )


@pytest.mark.django_db
def test_client_ip_key_returns_real_client_from_x_real_ip(settings):
    # AC6b (SECURITY — the core contract / PROD PATH): in the REALISTIC single-hop
    # Nginx deployment, Nginx sets `proxy_set_header X-Real-IP $remote_addr;` where
    # $remote_addr is the direct peer = the REAL client. The resolver's PRIMARY path
    # MUST return that X-Real-IP value verbatim — NOT REMOTE_ADDR (which over a unix
    # socket is loopback/empty), NOT any XFF position. It is non-spoofable because
    # Nginx OVERWRITES any client-supplied X-Real-IP on every request.
    _trust_proxy(settings)
    real_client = "203.0.113.7"
    # Nginx also forwards XFF; X-Real-IP is the authoritative direct-peer value.
    req = _make_request(
        xff=f"{real_client}, {_TRUSTED_PROXY}",
        x_real_ip=real_client,
        remote_addr="",  # unix socket → empty REMOTE_ADDR in real prod
    )

    from core.ratelimit import client_ip_key

    resolved = client_ip_key("ip", req)
    assert resolved == real_client, (
        f"resolver must return the real client from Nginx X-Real-IP "
        f"({real_client!r}), got {resolved!r}"
    )


@pytest.mark.django_db
def test_client_ip_key_falls_back_to_remote_addr_without_proxy_headers(settings):
    # AC6b: a direct request (dev/test — no Nginx, so no X-Real-IP and no XFF) must
    # resolve to REMOTE_ADDR, never crash and never a spoofable value.
    _trust_proxy(settings)
    req = _make_request(xff=None, x_real_ip=None, remote_addr="198.51.100.23")

    from core.ratelimit import client_ip_key

    resolved = client_ip_key("ip", req)
    assert resolved == "198.51.100.23", (
        f"with no proxy headers the resolver must use REMOTE_ADDR, got {resolved!r}"
    )


@pytest.mark.django_db
def test_client_ip_key_is_not_spoofable_by_leftmost_header(settings):
    # AC6b (NEGATIVE/SECURITY — the adversarial spoof case): an attacker PREPENDS a
    # forged X-Forwarded-For value AND attempts to supply a fake X-Real-IP. But in the
    # real single-hop deployment Nginx OVERWRITES X-Real-IP with $remote_addr (the
    # real client), so the value that actually reaches the app is the trustworthy one.
    # We simulate that prod reality: X-Real-IP == real client (Nginx-set), while XFF
    # still carries the attacker's prepended spoof. The resolver MUST return EXACTLY
    # the trusted X-Real-IP and NEVER the spoofed leftmost XFF value.
    _trust_proxy(settings)
    spoof = "6.6.6.6"
    real_client = "203.0.113.50"
    # Attacker prepends `spoof` to XFF; Nginx then sets X-Real-IP to the real peer.
    req = _make_request(
        xff=f"{spoof}, {real_client}, {_TRUSTED_PROXY}",
        x_real_ip=real_client,  # Nginx overwrote any client-supplied X-Real-IP
        remote_addr=_TRUSTED_PROXY,
    )

    from core.ratelimit import client_ip_key

    resolved = client_ip_key("ip", req)
    assert resolved == real_client, (
        f"resolver must return EXACTLY the Nginx-trusted X-Real-IP "
        f"({real_client!r}), got {resolved!r}"
    )
    assert resolved != spoof, (
        f"resolver returned the client-spoofed leftmost XFF value {spoof!r} — "
        "it is spoofable and must not be used as the rate-limit key"
    )


@pytest.mark.django_db
def test_client_ip_key_no_trusted_list_never_returns_spoofable_leftmost(settings):
    # AC6b (NEGATIVE/MISCONFIG): if there is no X-Real-IP (no Nginx) AND
    # IPWARE_TRUSTED_PROXY_LIST is unset/empty, the resolver MUST NOT fall through to
    # ipware non-strict mode (which returns the spoofable LEFTMOST XFF). It must fall
    # back to REMOTE_ADDR (the direct peer) and NEVER the attacker-supplied value.
    settings.IPWARE_TRUSTED_PROXY_LIST = []
    spoof = "6.6.6.6"
    peer = "198.51.100.99"
    req = _make_request(xff=f"{spoof}, 203.0.113.1", x_real_ip=None, remote_addr=peer)

    from core.ratelimit import client_ip_key

    resolved = client_ip_key("ip", req)
    assert resolved != spoof, (
        f"with no trusted-proxy list the resolver must NOT return the spoofable "
        f"leftmost XFF value {spoof!r}, got {resolved!r}"
    )
    assert resolved == peer, (
        f"with no proxy config the resolver must fall back to REMOTE_ADDR "
        f"({peer!r}), got {resolved!r}"
    )


def test_views_wire_ratelimit_key_to_custom_callable():
    # AC6b: the @ratelimit decorators on the public POST views must wire the rate-limit
    # key to the custom non-spoofable callable via its dotted path — NOT a phantom
    # RATELIMIT_KEY setting (django-ratelimit 4.x does not read that) and NOT key="ip".
    pages_src = _strip_comments(_read("pages", "views.py"))
    props_src = _strip_comments(_read("properties", "views.py"))
    assert pages_src and props_src, "view sources missing"

    dotted = r'key\s*=\s*["\']core\.ratelimit\.client_ip_key["\']'
    # pages/views.py has TWO rate-limited views (Contact + PrivateCollection).
    assert len(re.findall(dotted, pages_src)) >= 2, (
        "pages/views.py must wire BOTH @ratelimit decorators to "
        'key="core.ratelimit.client_ip_key"'
    )
    # properties/views.py has ONE (PropertyDetailView).
    assert re.search(dotted, props_src), (
        'properties/views.py must wire @ratelimit to key="core.ratelimit.client_ip_key"'
    )

    # The naive spoofable header key and the old simple key="ip" must be gone.
    combined = pages_src + "\n" + props_src
    assert not re.search(r"header:x-forwarded-for", combined, re.I), (
        "naive spoofable key='header:x-forwarded-for' must NOT be used"
    )
    assert not re.search(r'key\s*=\s*["\']ip["\']', combined), (
        'the rate-limited views must no longer use the simple key="ip" — it does '
        "not resolve the real client behind Nginx; use the custom callable"
    )


def test_prod_references_custom_ratelimit_resolver_and_no_phantom_key():
    # AC6b: prod settings must still reference the custom resolver (via the trusted
    # proxy list it feeds) and MUST NOT carry the phantom RATELIMIT_KEY setting that
    # django-ratelimit 4.x ignores (dead, falsely-reassuring config).
    src = _strip_comments(_read("config", "settings", "prod.py"))
    assert src, "config/settings/prod.py does not exist"
    assert "IPWARE_TRUSTED_PROXY_LIST" in src, (
        "prod.py must configure IPWARE_TRUSTED_PROXY_LIST for the resolver's "
        "secondary path"
    )
    assert not re.search(r"^\s*RATELIMIT_KEY\s*=", src, re.M), (
        "prod.py must NOT set the phantom RATELIMIT_KEY — django-ratelimit 4.x does "
        "not read it; the key is wired on the view decorators instead"
    )


# =========================================================================== #
# AC6c — SILENCED_SYSTEM_CHECKS removed in prod                               #
# =========================================================================== #
def test_prod_does_not_silence_ratelimit_checks():
    # AC6c (NEGATIVE): once a shared cache is in place, prod must NOT silence
    # django_ratelimit.E003 / W001. SOURCE-inspection (mirrors the other prod-only
    # assertions): importing prod.py would require a local .env (MAILGUN_* etc.) and
    # crash on a CI box without it. We assert on the STRIPPED prod source instead — it
    # must set SILENCED_SYSTEM_CHECKS but NOT carry the django_ratelimit E003/W001
    # entries that would re-silence the checks the shared cache exists to satisfy.
    src = _strip_comments(_read("config", "settings", "prod.py"))
    assert src, "config/settings/prod.py does not exist"
    assert re.search(r"^\s*SILENCED_SYSTEM_CHECKS\s*=", src, re.M), (
        "prod.py must explicitly set SILENCED_SYSTEM_CHECKS (clear the dev/test "
        "silencing so it does not leak into prod)"
    )
    offenders = [
        c
        for c in ("django_ratelimit.E003", "django_ratelimit.W001")
        if c in src
    ]
    assert not offenders, (
        "prod must NOT silence django_ratelimit E003/W001 once the shared cache "
        f"is configured (shared cache removes the reason), found: {offenders}"
    )


def test_base_may_keep_silencing_for_dev_test_locmem():
    # AC6c: base/test (LocMemCache) is allowed to keep the silencing — this test
    # documents the scoping contract: the silencing is OK for the LocMem context,
    # but must be conditional/removed for prod (asserted above). Here we simply
    # confirm the prod override is what changes behaviour, by asserting prod.py
    # source touches SILENCED_SYSTEM_CHECKS (sets it explicitly / conditionally).
    src = _strip_comments(_read("config", "settings", "prod.py"))
    assert src, "config/settings/prod.py does not exist"
    assert "SILENCED_SYSTEM_CHECKS" in src, (
        "prod.py must explicitly address SILENCED_SYSTEM_CHECKS (clear it / make it "
        "conditional) so the dev/test silencing does not leak into prod (AC6c)"
    )


# =========================================================================== #
# AC4 — Mailgun send-timeout (custom requests session / REQUESTS_TIMEOUT)      #
# =========================================================================== #
def test_prod_configures_mailgun_send_timeout():
    # AC4: prod.py must configure an explicit send timeout for the anymail Mailgun
    # backend — via ANYMAIL["REQUESTS_TIMEOUT"] or a custom requests.Session timeout.
    src = _strip_comments(_read("config", "settings", "prod.py"))
    assert src, "config/settings/prod.py does not exist"
    has_anymail_timeout = re.search(r"REQUESTS_TIMEOUT", src)
    has_session_timeout = re.search(r"requests", src, re.I) and re.search(
        r"timeout", src, re.I
    )
    assert has_anymail_timeout or has_session_timeout, (
        "prod.py must configure a Mailgun send-timeout (ANYMAIL['REQUESTS_TIMEOUT'] "
        "or a custom requests session with a timeout) — anymail has no default timeout"
    )


def test_prod_mailgun_timeout_is_roughly_ten_seconds():
    # AC4: the configured timeout must be a sane finite value — exactly 10s is the
    # recommended/contract value. We assert the timeout resolves to 10 by importing
    # the prod module's effective ANYMAIL config (source regex would miss the
    # MAILGUN_SEND_TIMEOUT indirection). Accept >=5 as the lower sanity bound but
    # require the contract value of exactly 10 for this story.
    prod = _import_settings("prod")
    anymail = getattr(prod, "ANYMAIL", {})
    timeout = anymail.get("REQUESTS_TIMEOUT")
    assert timeout is not None, (
        "prod ANYMAIL must set REQUESTS_TIMEOUT (Mailgun has no default send-timeout)"
    )
    # Support a scalar (10) or a (connect, read) tuple — take the max for the bound.
    value = max(timeout) if isinstance(timeout, (list, tuple)) else timeout
    assert value >= 5, f"Mailgun send-timeout must be a sane >=5s value, got {timeout!r}"
    assert value == 10, (
        f"Mailgun send-timeout must be exactly 10s per the story contract, got {timeout!r}"
    )


def test_prod_does_not_introduce_celery():
    # AC4 (NEGATIVE): Celery / async sending is EXPLICITLY out of MVP scope (no broker).
    # The timeout must be solved with a requests session — NOT by adding Celery.
    # We strip comments first: the existing TRACKED note in prod.py legitimately
    # mentions the word "Celery" in prose, and the Dev must not be forced to delete
    # an explanatory comment to satisfy this guard. The contract is "no REAL Celery
    # config/import" — so assert on the de-commented source only.
    src = _strip_comments(_read("config", "settings", "prod.py"))
    assert src, "config/settings/prod.py does not exist"
    assert not re.search(r"\bcelery\b", src, re.I), (
        "Celery must NOT appear in prod.py code — async email is out of MVP scope; "
        "use a custom requests session timeout instead"
    )


# =========================================================================== #
# AC5 — new prod requirements (django-redis, django-ipware), not in base       #
# =========================================================================== #
def test_prod_requirements_add_django_redis():
    # AC5: requirements/prod.txt must add django-redis (shared cache client).
    prod = _read("requirements", "prod.txt")
    assert prod, "requirements/prod.txt does not exist"
    assert any(
        re.match(r"^django-redis\b", ln, re.I) for ln in _active_requirement_lines(prod)
    ), "requirements/prod.txt must list django-redis (shared cache backend)"


def test_prod_requirements_add_django_ipware():
    # AC5: requirements/prod.txt must add django-ipware (non-spoofable client IP).
    prod = _read("requirements", "prod.txt")
    assert prod, "requirements/prod.txt does not exist"
    assert any(
        re.match(r"^django-ipware\b", ln, re.I)
        for ln in _active_requirement_lines(prod)
    ), "requirements/prod.txt must list django-ipware (client IP resolver)"


def test_new_prod_packages_do_not_pollute_base():
    # AC5: django-redis / django-ipware are prod-only — they must NOT appear as
    # active dependencies in base.txt.
    base = _read("requirements", "base.txt")
    assert base, "requirements/base.txt does not exist"
    active = _active_requirement_lines(base)
    for pkg in ("django-redis", "django-ipware"):
        assert not any(re.match(rf"^{re.escape(pkg)}\b", ln, re.I) for ln in active), (
            f"{pkg} must NOT be an active dependency in base.txt (prod-only)"
        )


# =========================================================================== #
# AC5 — .env.example new prod vars (and existing vars preserved)               #
# =========================================================================== #
def test_env_example_adds_cache_url():
    # AC5: .env.example must add the production cache env var (CACHE_URL / REDIS_URL).
    text = _read(".env.example")
    assert text, ".env.example does not exist"
    assert re.search(r"^\s*(CACHE_URL|REDIS_URL)\s*=", text, re.M), (
        ".env.example must add CACHE_URL (or REDIS_URL) for the production shared cache"
    )


def test_env_example_preserves_all_existing_required_vars():
    # AC5: adding new vars must NOT drop any existing required var
    # (tests/test_project_setup.py also depends on these).
    text = _read(".env.example")
    assert text, ".env.example does not exist"
    required = [
        "SECRET_KEY",
        "DEBUG",
        "ALLOWED_HOSTS",
        "DATABASE_URL",
        "ADMIN_URL",
        "STORAGE_BACKEND",
        "MAILGUN_API_KEY",
        "MAILGUN_SENDER_DOMAIN",
        "DEFAULT_FROM_EMAIL",
        "GOOGLE_ANALYTICS_ID",
    ]
    missing = [v for v in required if not re.search(rf"^\s*{v}\s*=", text, re.M)]
    assert not missing, f".env.example dropped existing required vars: {missing}"


# =========================================================================== #
# AC1 — deploy artifacts: gunicorn systemd unit + nginx vhost                  #
# =========================================================================== #
def test_gunicorn_systemd_unit_exists_and_sane():
    # AC1: deploy/gunicorn.service must exist as a versioned (no-credentials) template.
    txt = _read("deploy", "gunicorn.service")
    assert txt, "deploy/gunicorn.service does not exist"
    assert re.search(r"unix:", txt), "gunicorn unit must bind a Unix socket (unix:...)"
    assert re.search(r"EnvironmentFile\s*=", txt), (
        "gunicorn unit must load env via EnvironmentFile="
    )
    assert "config.settings.prod" in txt, (
        "gunicorn unit must set DJANGO_SETTINGS_MODULE=config.settings.prod"
    )
    assert re.search(r"Restart\s*=\s*always", txt), "gunicorn unit must Restart=always"
    assert re.search(r"User\s*=\s*\w+", txt) and not re.search(
        r"User\s*=\s*root\b", txt
    ), "gunicorn unit must run as a non-root User="


def test_nginx_vhost_exists_and_serves_static_media_with_proxy_headers():
    # AC1/AC6: nginx vhost must serve /static/ and /media/ from disk, proxy_pass to
    # the gunicorn socket, and forward X-Forwarded-Proto + X-Forwarded-For.
    txt = _read_nginx_vhost()
    assert txt, "deploy/nginx.conf (or nginx-velegrad.conf) does not exist"
    assert re.search(r"location\s+/static/", txt), "nginx must serve location /static/"
    assert re.search(r"location\s+/media/", txt), "nginx must serve location /media/"
    assert re.search(r"proxy_pass\b", txt), "nginx must proxy_pass to gunicorn"
    assert re.search(r"X-Forwarded-Proto", txt), (
        "nginx must set X-Forwarded-Proto (SECURE_PROXY_SSL_HEADER depends on it)"
    )
    assert re.search(r"X-Forwarded-For", txt), (
        "nginx must set X-Forwarded-For (AC6 real client IP)"
    )


# =========================================================================== #
# AC3 — backup scripts (repo artifacts; not executed)                         #
# =========================================================================== #
def test_backup_db_script_exists_and_covers_pg_dump_and_offsite():
    # AC3: scripts/backup_db.sh must exist (pg_dump + retention + offsite step).
    txt = _read("scripts", "backup_db.sh")
    assert txt, "scripts/backup_db.sh does not exist"
    assert txt.lstrip().startswith("#!"), "backup_db.sh must have a shebang"
    assert re.search(r"pg_dump\b", txt), "backup_db.sh must run pg_dump"
    assert re.search(r"rsync|scp|s3|offsite|storage box", txt, re.I), (
        "backup_db.sh must include an offsite copy step (rsync/scp/s3/storage box)"
    )


def test_backup_media_script_exists_and_covers_media_and_offsite():
    # AC3: scripts/backup_media.sh must exist (tar/rsync of media/ + offsite).
    txt = _read("scripts", "backup_media.sh")
    assert txt, "scripts/backup_media.sh does not exist"
    assert txt.lstrip().startswith("#!"), "backup_media.sh must have a shebang"
    assert re.search(r"\bmedia\b", txt), "backup_media.sh must back up the media/ dir"
    assert re.search(r"\btar\b|rsync", txt), "backup_media.sh must use tar or rsync"
    assert re.search(r"rsync|scp|s3|offsite|storage box", txt, re.I), (
        "backup_media.sh must include an offsite copy step"
    )


# =========================================================================== #
# AC7 — client handover / training doc                                        #
# =========================================================================== #
def test_client_handover_doc_exists_and_covers_required_topics():
    # AC7: docs/primopredaja-klijent.md must exist and cover the required topics
    # (login/ADMIN_URL, nekretnine, slike/reorder, upiti, SiteSettings,
    # dvojezičnost, backup/restore, logovi/restart, TLS).
    txt = _read("docs", "primopredaja-klijent.md")
    assert txt, "docs/primopredaja-klijent.md does not exist"
    low = txt.lower()
    required_topics = {
        "login/ADMIN_URL": ("admin_url", "prijav", "login"),
        "nekretnine": ("nekretnin",),
        "slike/reorder": ("slik", "reorder", "redosled"),
        "upiti": ("upit", "inquiry"),
        "SiteSettings": ("sitesettings", "podešavanj", "podesavanj"),
        "dvojezičnost": ("dvojezi", "srpski", "engleski", "en/sr", "sr/en"),
        "backup/restore": ("backup", "restore", "vraćanj", "vracanj"),
        "logovi/restart": ("log", "restart", "journalctl", "systemctl"),
        "TLS": ("tls", "https", "sertifikat", "certbot"),
    }
    missing = [
        topic
        for topic, needles in required_topics.items()
        if not any(n in low for n in needles)
    ]
    assert not missing, f"primopredaja-klijent.md missing topics: {missing}"
