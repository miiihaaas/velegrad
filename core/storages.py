"""Storage backend selection helper (Story 6.3, arhitektura §2).

Pure helper koji preslikava ``STORAGE_BACKEND`` env ime → Django storage BACKEND
string. Ovo je KANONSKI dom za izbor backend-a (AC4): Django ``override_settings``
NE re-izvršava module-level kod u ``config/settings/base.py``, pa se module-level
``STORAGES`` dict NE može prebaciti monkeypatch-ovanjem env-a u test-vremenu —
zato izbor MORA živeti u čistoj funkciji koja se unit-testira direktno.

``STORAGES["default"]`` u ``base.py`` poziva ovaj helper sa ``STORAGE_BACKEND``
env vrednošću. Tako i originali I django-imagekit WebP varijante (koje prolaze
kroz isti ``default_storage``) idu na isti backend → automatski rade i sa S3 kad
Story 6.4 postavi ``STORAGE_BACKEND=s3`` (+ boto3 + AWS_* kredencijali).
"""

LOCAL_BACKEND = "django.core.files.storage.FileSystemStorage"
S3_BACKEND = "storages.backends.s3.S3Storage"


def default_storage_backend(name):
    """Vrati Django storage BACKEND string za dato ``STORAGE_BACKEND`` ime.

    ``"s3"`` → django-storages ``S3Storage``; sve ostalo (uključujući ``"local"``)
    → Django ugrađeni ``FileSystemStorage`` (default-safe).

    PURE helper bez Django/imagekit zavisnosti — uvozi se u ``base.py`` u vreme
    konstrukcije settings-a, pa NE sme importovati ništa što čita ``settings``.
    """
    if name == "s3":
        return S3_BACKEND
    return LOCAL_BACKEND
