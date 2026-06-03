"""ImageKit cachefile backend koji ODLAŽE generisanje varijanti — bez Celery
(Story 6.3).

⚠️ Ovaj modul uvozi ``imagekit`` (čije ``__init__`` instancira AppConf koji čita
``settings``), pa se NE sme uvoziti u vreme konstrukcije settings-a. Referencira se
SAMO kao string (``IMAGEKIT_DEFAULT_CACHEFILE_BACKEND =
"core.imagekit_backends.DeferredCacheFileBackend"``) — imagekit ga uvozi lenjivo,
posle ``apps.ready``, kada su settings i AppConf default-i već primenjeni.
"""
from imagekit.cachefiles.backends import BaseAsync


class DeferredCacheFileBackend(BaseAsync):
    """Cachefile backend koji odlaže generisanje varijanti (bez Celery).

    Story 6.3 koristi OBAVEZNU ``Optimistic`` strategiju: ``.url`` je čista string
    operacija (``source.name`` + spec hash), ali ``on_source_saved`` poziva
    ``generate()``. Sa default sinhronim ``Simple`` backend-om to bi OTVORILO
    izvorni fajl pri svakom ``save()`` → ``FileNotFoundError`` na byteless seed-u
    (testovi seed-uju string putanje BEZ realnih bajtova) i pri svakom admin
    upload-u pre nego što fajl postoji na disku.

    ``BaseAsync`` razdvaja zakazivanje generisanja od ``.url`` renderovanja
    (``is_async=True`` → ``.url``/``__bool__`` NE proveravaju postojanje fajla).
    ``schedule_generation`` je NO-OP: varijanta se NE generiše sinhrono na save
    (NE otvara fajl, NE traži Celery worker). Stvarna WebP konverzija je lazy/
    deploy briga (Story 6.4) — renderovani ``.url`` u ``<source srcset>`` je uvek
    I/O-free i Celery-free.
    """

    def schedule_generation(self, file, force=False):
        # NO-OP: ne generiši sinhrono (izbegava otvaranje izvora na save), bez
        # task queue. Generisanje je odloženo — `.url` ostaje string-safe.
        return
