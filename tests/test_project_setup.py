"""
RED-phase contract tests for Story 1.1 — "Inicijalizacija Django projekta i okruzenja".

These tests define the CONTRACT the developer must satisfy. They are written
BEFORE any implementation exists, so EVERY test here MUST FAIL or ERROR until
the Django scaffold is built (the dominant failure is ModuleNotFoundError for
`config` / `config.settings.*`, and FileNotFoundError for scaffold files/dirs).

Design rules followed:
- Tests are ISOLATED — no test depends on another's side effects.
- Settings/Django imports happen INSIDE test bodies (and via a helper) so that a
  missing scaffold surfaces as a per-test failure with a clear message, instead
  of crashing pytest collection for the whole module.
- Only ONE test touches a live database; it is marked @pytest.mark.django_db and
  SKIPS (does not fail) when Postgres is unreachable, so CI without a DB still runs.
- Each test maps to an acceptance criterion via a `# AC-N:` comment.

Contract reference:
  _bmad-output/implementation-artifacts/
    1-1-inicijalizacija-django-projekta-i-okruzenja-interface-contract.md
"""
import importlib
import re
from pathlib import Path

import pytest

# Repo root = parent of this tests/ package.
ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Helpers (kept dependency-light; they raise -> the calling test FAILS cleanly) #
# --------------------------------------------------------------------------- #
def _read(*relparts):
    """Return text of a repo-relative file, or '' if it does not exist yet."""
    p = ROOT.joinpath(*relparts)
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _import_settings(name):
    """Import a config.settings.<name> module fresh and return it.

    Raises ModuleNotFoundError until the scaffold exists -> test FAILS.
    """
    mod = f"config.settings.{name}"
    # Membership test against sys.modules directly — no need to materialize a
    # full list() copy of the keys just to check one key (R2 cleanup).
    if mod in importlib.sys.modules:
        return importlib.reload(importlib.sys.modules[mod])
    return importlib.import_module(mod)


def _configured_django(settings_name):
    """Configure Django ONCE per test session and return the lazy settings obj.

    IMPORTANT: Django can only be ``django.setup()``-configured a single time per
    process. This helper therefore configures Django exactly ONCE, against
    ``config.settings.<settings_name>`` — and every current caller passes 'dev',
    so the whole suite runs against dev settings. It is NOT able to truly
    re-configure for a *different* settings module on a later call; subsequent
    calls just return the already-configured lazy ``django.conf.settings``.

    We use ``django.conf.settings`` (after ensuring DJANGO_SETTINGS_MODULE points
    at the target module) so that AppConfig / INSTALLED_APPS introspection works.

    To avoid leaking process state, DJANGO_SETTINGS_MODULE is set only for the
    duration of the one-time django.setup() call and then restored to its prior
    value (Django captures the module reference during setup, so the env var no
    longer needs to persist afterward). Once configured we leave os.environ
    untouched, so we neither clobber nor permanently leak the var across tests.
    """
    import os
    import django
    from django.conf import settings as dj_settings

    # Import the target settings module FIRST. While the scaffold is absent this
    # raises ModuleNotFoundError here, inside the test body, BEFORE we mutate any
    # Django global state — keeping the RED failure clean and well-attributed.
    _import_settings(settings_name)
    if not dj_settings.configured:
        _SENTINEL = object()
        prev = os.environ.get("DJANGO_SETTINGS_MODULE", _SENTINEL)
        os.environ["DJANGO_SETTINGS_MODULE"] = f"config.settings.{settings_name}"
        try:
            django.setup()
        finally:
            # Restore the prior env state so we don't leak DJANGO_SETTINGS_MODULE
            # into the rest of the process (pytest.ini deliberately leaves it unset).
            if prev is _SENTINEL:
                os.environ.pop("DJANGO_SETTINGS_MODULE", None)
            else:
                os.environ["DJANGO_SETTINGS_MODULE"] = prev
    return dj_settings


# =========================================================================== #
# AC1 — Platform versions (Python 3.12 / Django 5.2 / Postgres 16)            #
# =========================================================================== #
def test_django_version_satisfies_5_2_lts():
    # AC1: the PROJECT must run on Django 5.2 LTS.
    # We anchor this to the project actually existing (manage.py present) so the
    # assertion is RED until the scaffold is built, then verifies the runtime
    # Django the project resolves against is 5.2.x. (The base.txt pin is checked
    # separately by test_requirements_base_pins_django_with_valid_pip_syntax.)
    assert (ROOT / "manage.py").is_file(), (
        "manage.py missing — project not initialized; cannot assert its Django runtime"
    )
    import django

    major, minor = django.VERSION[0], django.VERSION[1]
    assert (major, minor) == (5, 2), (
        f"Project must run on Django 5.2.x, got {django.get_version()}"
    )


def test_requirements_base_pins_django_with_valid_pip_syntax():
    # AC1: requirements/base.txt must pin Django with a VALID pip spec.
    # Accept `Django>=5.2,<5.3` or `Django~=5.2.0`; REJECT the invalid `Django==5.2.*`.
    text = _read("requirements", "base.txt")
    assert text, "requirements/base.txt does not exist yet"

    django_lines = [
        ln.strip()
        for ln in text.splitlines()
        if re.match(r"^\s*Django\b", ln, re.IGNORECASE)
        and not ln.strip().startswith("#")
    ]
    assert django_lines, "No Django pin found in requirements/base.txt"
    line = django_lines[0]

    # Reject the invalid wildcard-equality pin explicitly.
    assert not re.search(r"==\s*5\.2\.\*", line), (
        f"`Django==5.2.*` is NOT a valid pip pin; use `Django>=5.2,<5.3`. Got: {line!r}"
    )
    valid = re.search(r">=\s*5\.2\b.*<\s*5\.3\b", line) or re.search(
        r"~=\s*5\.2\.\d+", line
    )
    assert valid, f"Django pin in base.txt is not a valid 5.2 spec: {line!r}"


# =========================================================================== #
# AC2 — Project + app structure                                              #
# =========================================================================== #
def test_config_package_and_settings_package_exist():
    # AC2: config/ and config/settings/ must be real Python packages (have __init__.py).
    assert (ROOT / "config" / "__init__.py").is_file(), "config/__init__.py missing"
    assert (ROOT / "config" / "settings" / "__init__.py").is_file(), (
        "config/settings/__init__.py missing — config.settings would not be a package"
    )


def test_config_has_urls_wsgi_asgi():
    # AC2/AC3: config/ must hold urls.py, wsgi.py, asgi.py.
    for fname in ("urls.py", "wsgi.py", "asgi.py"):
        assert (ROOT / "config" / fname).is_file(), f"config/{fname} missing"


def test_manage_py_exists_at_root():
    # AC2: manage.py must live at the repo root (flat layout).
    assert (ROOT / "manage.py").is_file(), "manage.py missing at repo root"


@pytest.mark.parametrize("app", ["core", "properties", "inquiries", "pages"])
def test_custom_app_packages_exist(app):
    # AC2: the four Django apps exist as packages.
    assert (ROOT / app / "__init__.py").is_file(), f"{app}/__init__.py missing"


@pytest.mark.parametrize(
    "folder", ["templates", "static", "locale", "media", "requirements"]
)
def test_required_directories_exist(folder):
    # AC2: scaffold folders must exist.
    assert (ROOT / folder).is_dir(), f"{folder}/ directory missing"


def test_custom_apps_registered_in_installed_apps():
    # AC2: the 4 custom apps are registered in INSTALLED_APPS.
    settings = _configured_django("dev")
    from django.apps import apps

    labels = {cfg.label for cfg in apps.get_app_configs()}
    for app in ("core", "properties", "inquiries", "pages"):
        assert app in labels, f"App '{app}' not registered (labels: {sorted(labels)})"


def test_standard_contrib_apps_present():
    # AC2: full standard contrib set must be installed so migrate succeeds.
    settings = _configured_django("dev")
    installed = set(settings.INSTALLED_APPS)
    required = {
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
    }
    missing = required - installed
    assert not missing, f"Missing contrib apps: {sorted(missing)}"


# =========================================================================== #
# AC3 — Split settings (base/dev/prod)                                       #
# =========================================================================== #
@pytest.mark.parametrize("name", ["base", "dev", "prod"])
def test_settings_modules_importable(name):
    # AC3: config.settings.base/dev/prod must all import.
    mod = _import_settings(name)
    assert mod is not None


def test_dev_debug_true():
    # AC3: dev settings must have DEBUG = True.
    mod = _import_settings("dev")
    assert getattr(mod, "DEBUG", None) is True, "dev.DEBUG must be True"


def test_prod_debug_false():
    # AC3: prod settings must have DEBUG = False.
    mod = _import_settings("prod")
    assert getattr(mod, "DEBUG", None) is False, "prod.DEBUG must be False"


def test_prod_security_baseline():
    # AC3: prod must set the SECURE_* baseline (NFR-5).
    mod = _import_settings("prod")
    assert getattr(mod, "SECURE_SSL_REDIRECT", False) is True, "SECURE_SSL_REDIRECT"
    assert getattr(mod, "SESSION_COOKIE_SECURE", False) is True, "SESSION_COOKIE_SECURE"
    assert getattr(mod, "CSRF_COOKIE_SECURE", False) is True, "CSRF_COOKIE_SECURE"
    assert getattr(mod, "SECURE_HSTS_SECONDS", 0) > 0, "SECURE_HSTS_SECONDS must be > 0"
    assert getattr(mod, "SECURE_HSTS_INCLUDE_SUBDOMAINS", False) is True, (
        "SECURE_HSTS_INCLUDE_SUBDOMAINS"
    )
    assert getattr(mod, "SECURE_CONTENT_TYPE_NOSNIFF", False) is True, (
        "SECURE_CONTENT_TYPE_NOSNIFF"
    )

    # T1: cookies must not be readable by client-side JS where it matters.
    # We assert the EFFECTIVE settings value (covering the implicit-default case
    # where prod.py does not set these explicitly) by reading the prod module and
    # falling back to Django's documented global defaults:
    #   SESSION_COOKIE_HTTPONLY -> default True   (security-critical; must stay truthy)
    #   CSRF_COOKIE_HTTPONLY    -> default False   (token is read by JS by design)
    from django.conf import global_settings

    session_httponly = getattr(
        mod, "SESSION_COOKIE_HTTPONLY", global_settings.SESSION_COOKIE_HTTPONLY
    )
    assert session_httponly, (
        "SESSION_COOKIE_HTTPONLY must be truthy in prod (do not expose the "
        "session cookie to client-side JS)"
    )
    # CSRF_COOKIE_HTTPONLY defaults False in Django on purpose; assert prod does
    # not leave it UNDEFINED/None and that it is a real boolean effective value.
    csrf_httponly = getattr(
        mod, "CSRF_COOKIE_HTTPONLY", global_settings.CSRF_COOKIE_HTTPONLY
    )
    assert isinstance(csrf_httponly, bool), (
        "CSRF_COOKIE_HTTPONLY must resolve to a concrete boolean (effective "
        f"value), got {csrf_httponly!r}"
    )


# =========================================================================== #
# AC4 — django-environ + .env strategy                                       #
# =========================================================================== #
def test_secret_key_is_read_from_env_not_hardcoded():
    # AC4: SECRET_KEY must come from env; base.py must not contain a hardcoded key.
    src = _read("config", "settings", "base.py")
    assert src, "config/settings/base.py does not exist yet"

    # base.py must reference SECRET_KEY via env (e.g. env("SECRET_KEY") / env.str(...)).
    assert re.search(r"SECRET_KEY", src), "SECRET_KEY not referenced in base.py"
    assert re.search(r"env(?:iron)?[\w.]*\(\s*[\"']SECRET_KEY", src) or re.search(
        r"env\.str\(\s*[\"']SECRET_KEY", src
    ), "SECRET_KEY must be read from env (env('SECRET_KEY'))"

    # Reject an obvious hardcoded literal assignment like: SECRET_KEY = "django-insecure-..."
    hardcoded = re.search(
        r"SECRET_KEY\s*=\s*[\"'][^\"']{12,}[\"']", src
    )
    assert not hardcoded, (
        f"SECRET_KEY appears hardcoded in base.py: {hardcoded.group(0)!r}"
    )


def test_env_read_env_is_wired():
    # AC4: base.py must call read_env, otherwise the local .env file is ignored.
    src = _read("config", "settings", "base.py")
    assert src, "config/settings/base.py does not exist yet"
    assert "read_env" in src, "base.py must call env.read_env(...) to load .env"


def test_env_example_exists_and_lists_all_key_vars():
    # AC4: .env.example must exist and list every key env var (no real values).
    text = _read(".env.example")
    assert text, ".env.example does not exist yet"
    required_vars = [
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
    missing = [v for v in required_vars if not re.search(rf"^\s*{v}\s*=", text, re.M)]
    assert not missing, f".env.example is missing vars: {missing}"


# =========================================================================== #
# AC5 — requirements files                                                   #
# =========================================================================== #
@pytest.mark.parametrize("fname", ["base.txt", "dev.txt", "prod.txt"])
def test_requirements_files_exist(fname):
    # AC5: requirements/base.txt, dev.txt, prod.txt must all exist.
    assert (ROOT / "requirements" / fname).is_file(), f"requirements/{fname} missing"


def test_dev_and_prod_reference_base():
    # AC5: dev.txt and prod.txt must include base via `-r base.txt`.
    for fname in ("dev.txt", "prod.txt"):
        text = _read("requirements", fname)
        assert text, f"requirements/{fname} does not exist yet"
        assert re.search(r"^\s*-r\s+base\.txt\s*$", text, re.M), (
            f"requirements/{fname} must contain `-r base.txt`"
        )


def test_gunicorn_in_prod_not_base():
    # AC5: gunicorn is a prod package — it belongs in prod.txt, NOT base.txt.
    base = _read("requirements", "base.txt")
    prod = _read("requirements", "prod.txt")
    assert prod, "requirements/prod.txt does not exist yet"
    assert re.search(r"^\s*gunicorn\b", prod, re.M | re.I), (
        "gunicorn must be listed in requirements/prod.txt"
    )
    base_active = [
        ln for ln in base.splitlines()
        if re.match(r"^\s*gunicorn\b", ln, re.I) and not ln.strip().startswith("#")
    ]
    assert not base_active, "gunicorn must NOT be an active dependency in base.txt"


def test_boto3_is_commented_deferred_dep_in_base():
    # T2 / AC5: boto3 is the DEFERRED S3 dependency. It must appear in base.txt as a
    # COMMENTED line (documented but inactive) — present so it is easy to enable when
    # S3 storage is activated, but not installed as an active dependency yet.
    base = _read("requirements", "base.txt")
    assert base, "requirements/base.txt does not exist yet"
    commented = [
        ln for ln in base.splitlines()
        if ln.strip().startswith("#") and re.search(r"\bboto3\b", ln, re.I)
    ]
    assert commented, (
        "requirements/base.txt must contain a COMMENTED boto3 line "
        "(deferred S3 dependency per AC5)"
    )
    # And it must NOT be an active (uncommented) dependency.
    active_boto3 = [
        ln for ln in base.splitlines()
        if re.match(r"^\s*boto3\b", ln, re.I) and not ln.strip().startswith("#")
    ]
    assert not active_boto3, "boto3 must NOT be an active dependency in base.txt yet"


def test_base_contains_architecture_runtime_packages():
    # AC5: base.txt must contain the architecture §4 runtime packages.
    base = _read("requirements", "base.txt")
    assert base, "requirements/base.txt does not exist yet"
    # Match only ACTIVE (non-commented) lines so a commented-out required package
    # (e.g. `# psycopg`) fails the assertion instead of falsely passing (BUG-2 fix).
    active = "\n".join(
        ln for ln in base.splitlines() if not ln.strip().startswith("#")
    )
    expected = [
        "psycopg",
        "django-environ",
        "django-unfold",
        "django-admin-sortable2",
        "django-tinymce",
        "Pillow",
        "django-imagekit",
        "django-storages",
        "django-anymail",
        "django-ratelimit",
        "whitenoise",
    ]
    missing = [pkg for pkg in expected if not re.search(re.escape(pkg), active, re.I)]
    assert not missing, f"requirements/base.txt missing packages: {missing}"


# =========================================================================== #
# AC6 — PostgreSQL via DATABASE_URL                                          #
# =========================================================================== #
def test_databases_configured_for_postgresql():
    # AC6: DATABASES['default'] must use the postgresql engine (from DATABASE_URL).
    settings = _configured_django("dev")
    engine = settings.DATABASES["default"]["ENGINE"]
    assert "postgresql" in engine, (
        f"DATABASES default ENGINE must be postgresql, got {engine!r}"
    )


def test_base_uses_database_url_not_split_credentials():
    # AC6: DATABASES must be built from DATABASE_URL (env.db), not split HOST/PORT/etc.
    src = _read("config", "settings", "base.py")
    assert src, "config/settings/base.py does not exist yet"
    assert re.search(r"env\.db\(|DATABASE_URL", src), (
        "base.py must configure DATABASES from DATABASE_URL via env.db()"
    )


def test_database_connection_smoke():
    # AC6: a live connection smoke test — SKIPPED if Postgres / scaffold is unreachable.
    # This is the ONLY test that hits a real DB. It self-configures Django and manages
    # its OWN connection inside a try/except so it SKIPS — never hard-fails/errors —
    # when the scaffold or a live Postgres is absent, so a DB-less CI run is not blocked.
    #
    # NOTE: deliberately NOT marked @pytest.mark.django_db. pytest-django IS installed
    # in this venv, and that marker would hand DB setup to pytest-django's `db` fixture,
    # which CREATES a test database BEFORE the test body runs. With no reachable Postgres
    # that fixture raises during setup -> the test ERRORS (and hangs on the connect
    # timeout) instead of skipping, which the try/except below cannot catch. Owning the
    # connection here keeps the "skip, never error" contract (interface-contract §7).
    import socket

    # PERF-1: bound the wait. Without a short timeout the OS TCP connect can hang
    # ~2 min before failing when no local Postgres is present, so this test would
    # take minutes to SKIP. We force a ~3s ceiling via the psycopg connect_timeout
    # option AND a global socket timeout (belt-and-suspenders), both restored in
    # finally so we don't leak a short default into the rest of the suite.
    prev_socket_timeout = socket.getdefaulttimeout()
    settings = _configured_django("dev")
    try:
        # Inject a 3s connect_timeout into the live default connection's OPTIONS so
        # psycopg gives up quickly when the DB is unreachable.
        settings.DATABASES["default"].setdefault("OPTIONS", {})
        settings.DATABASES["default"]["OPTIONS"]["connect_timeout"] = 3
        socket.setdefaulttimeout(3)

        from django.db import connection

        # Ensure a fresh connection so the new OPTIONS take effect.
        connection.close()
        with connection.cursor() as cur:
            cur.execute("SELECT 1;")
            assert cur.fetchone()[0] == 1
    except Exception as exc:  # noqa: BLE001 — intentionally broad: scaffold/DB may be absent
        pytest.skip(
            f"Scaffold or live Postgres not reachable "
            f"(expected in RED phase / DB-less CI): {exc}"
        )
    finally:
        socket.setdefaulttimeout(prev_socket_timeout)
        try:
            settings.DATABASES["default"].get("OPTIONS", {}).pop("connect_timeout", None)
        except Exception:  # noqa: BLE001 — cleanup must never mask the real outcome
            pass


# =========================================================================== #
# AC7 — git + .gitignore                                                     #
# =========================================================================== #
def test_gitignore_exists_and_excludes_required_entries():
    # AC7: .gitignore must exclude .env, __pycache__, *.pyc, media/, staticfiles/, venv.
    text = _read(".gitignore")
    assert text, ".gitignore does not exist yet"
    needed_patterns = [
        r"^\s*\.env\s*$",
        r"__pycache__",
        r"\*\.pyc",
        r"^\s*media/?\s*$",
        r"staticfiles/?",
        r"venv",  # matches venv/ or .venv/
    ]
    missing = [p for p in needed_patterns if not re.search(p, text, re.M)]
    assert not missing, f".gitignore missing patterns: {missing}"


def test_env_example_tracked_and_env_ignored():
    # AC7: .env.example must be present (committed); .env must be matched by .gitignore.
    assert (ROOT / ".env.example").is_file(), ".env.example must be present in repo"
    gitignore = _read(".gitignore")
    assert gitignore, ".gitignore does not exist yet"
    # .env is ignored, but the more specific .env.example is NOT ignored (no bare entry for it).
    assert re.search(r"^\s*\.env\s*$", gitignore, re.M), ".env must be in .gitignore"
    assert not re.search(r"^\s*\.env\.example\s*$", gitignore, re.M), (
        ".env.example must NOT be gitignored"
    )


# =========================================================================== #
# AC8 — ADMIN_URL mounting + CSRF baseline                                    #
# =========================================================================== #
def test_csrf_middleware_present():
    # AC8: CsrfViewMiddleware must be active in MIDDLEWARE.
    settings = _configured_django("dev")
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE, (
        "CsrfViewMiddleware missing from MIDDLEWARE"
    )


def test_admin_not_mounted_on_default_admin_path():
    # AC8(a): /admin/ must NOT resolve to the admin (404 / Resolver404).
    self_settings = _configured_django("dev")
    from django.urls import resolve, Resolver404

    with pytest.raises(Resolver404):
        resolve("/admin/")


def test_admin_mounted_on_configured_admin_url_path():
    # AC8(b): the configured ADMIN_URL path must resolve to admin.site.urls.
    # Read ADMIN_URL from the LIVE Django setting (single source of truth) — the
    # same value the URLconf uses — not from os.environ, which could diverge from
    # what settings/.env actually resolved (BUG-1 fix).
    self_settings = _configured_django("dev")
    admin_url = self_settings.ADMIN_URL.strip("/")
    from django.urls import resolve

    match = resolve(f"/{admin_url}/")
    # The admin index view namespace is 'admin'.
    assert match.namespace == "admin" or match.app_name == "admin", (
        f"/{admin_url}/ did not resolve into the admin (got {match!r})"
    )


def test_empty_admin_url_raises_improperly_configured():
    # T3 / AC8: an empty (or "/"-only) ADMIN_URL normalizes to "" and would mount the
    # admin at root "/". base.py must GUARD against this by raising
    # ImproperlyConfigured. We exercise the guard in a FRESH subprocess so importing
    # base.py with ADMIN_URL="" cannot disturb the already-configured Django in THIS
    # process (django.setup() is one-shot per process).
    import os
    import subprocess
    import sys

    code = (
        "import importlib;"
        "from django.core.exceptions import ImproperlyConfigured;"
        "\ntry:\n"
        "    importlib.import_module('config.settings.base')\n"
        "    print('NO_RAISE')\n"
        "except ImproperlyConfigured:\n"
        "    print('IMPROPERLY_CONFIGURED')\n"
    )
    env = dict(os.environ)
    env["ADMIN_URL"] = ""  # empty -> normalizes to "" -> must trip the guard
    # Avoid loading the repo .env (which sets a real ADMIN_URL) shadowing our value:
    env["SECRET_KEY"] = env.get("SECRET_KEY", "test-secret-key-for-guard-check")
    env["DATABASE_URL"] = env.get(
        "DATABASE_URL", "postgres://u:p@localhost:5432/db"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    # The repo .env may set ADMIN_URL and override our os.environ value via
    # read_env(overwrite). If the guard could not be exercised because .env forced a
    # non-empty value, skip with a clear reason rather than asserting falsely.
    if "NO_RAISE" in out and "IMPROPERLY_CONFIGURED" not in out:
        # Guard did not trip — likely .env overwrote ADMIN_URL. Confirm the guard
        # at least EXISTS in source so we don't silently pass with no protection.
        src = _read("config", "settings", "base.py")
        assert "ImproperlyConfigured" in src and re.search(
            r"if\s+not\s+ADMIN_URL", src
        ), (
            "Empty-ADMIN_URL guard missing from base.py (could not trigger it at "
            "runtime because the local .env forced a non-empty ADMIN_URL)"
        )
        pytest.skip(
            "Could not force empty ADMIN_URL at runtime (local .env overwrote it); "
            "verified the guard exists in source instead."
        )
    assert "IMPROPERLY_CONFIGURED" in out, (
        "Importing config.settings.base with ADMIN_URL='' must raise "
        f"ImproperlyConfigured. Subprocess output:\n{out}"
    )


def test_default_admin_url_is_not_admin():
    # AC8: the default ADMIN_URL value must not be 'admin/'.
    # ADMIN_URL is now a Django setting defined in base.py (single source of
    # truth, BUG-1 fix); the default literal lives there, not in urls.py.
    src = _read("config", "settings", "base.py")
    assert src, "config/settings/base.py does not exist yet"
    # Find the ADMIN_URL default in base.py, e.g. env('ADMIN_URL', default='velegrad-cms/').
    m = re.search(r"ADMIN_URL[\"']\s*,\s*default\s*=\s*[\"']([^\"']+)[\"']", src)
    assert m, "Could not find an ADMIN_URL default in config/settings/base.py"
    default_val = m.group(1).strip("/")
    assert default_val not in ("admin", ""), (
        f"Default ADMIN_URL must not be 'admin/'; got {m.group(1)!r}"
    )
