"""Non-spoofable rate-limit key callable (Story 6.4 AC6b).

django-ratelimit 4.x NE integriše ipware automatski, a naivni
``key='header:x-forwarded-for'`` je trivijalno spoofable (klijent prepend-uje
proizvoljnu vrednost). Ovaj custom callable je obavezan most: razrešava STVARNI
klijentski IP iza pouzdanog single-hop Nginx proxy-ja, pa rate-limit brojač uvek
koristi pravu adresu i brojač je PO-KLIJENTU (ne deljen bucket).

Wiring: @ratelimit dekoratori u pages/views.py i properties/views.py koriste
``key="core.ratelimit.client_ip_key"``. django-ratelimit 4.x razrešava dotted-path
string ključ preko ``import_string`` i poziva ga kao ``keyfn(group, request)``
(vidi django_ratelimit/core.py: get_usage → ``elif '.' in key: keyfn = import_string(key); value = keyfn(group, request)``).
Potpis ``client_ip_key(group, request) -> str`` tačno odgovara tom kontraktu.
"""
from django.conf import settings
from ipware import get_client_ip


def client_ip_key(group, request):
    """django-ratelimit key callable — vraća non-spoofable klijentski IP kao string.

    Potpis ``(group, request)`` je django-ratelimit key-callable kontrakt; vraća
    STRING koji se koristi kao ključ brojača (po-klijentu).

    Redosled razrešavanja (od najpouzdanijeg ka fallback-u):

    1. ``HTTP_X_REAL_IP`` (PRIMARNI, prod put). Nginx je u deploy/nginx.conf
       podešen sa ``proxy_set_header X-Real-IP $remote_addr;`` na proxied
       location-u. ``$remote_addr`` je DIREKTNI peer Nginx-a = stvarni klijent
       (single-hop deployment). NON-SPOOFABLE jer ``proxy_set_header`` UVEK
       PREGAZI bilo koju klijent-prosleđenu ``X-Real-IP`` vrednost — klijent ne
       može da je kontroliše. Ovo izbegava krhko strict-hop brojanje XFF lanca
       (single-element ``$proxy_add_x_forwarded_for`` lomi ipware strict režim) i
       prazan REMOTE_ADDR preko Unix socket-a.

    2. ``django-ipware`` SAMO ako je ``IPWARE_TRUSTED_PROXY_LIST`` NEPRAZAN
       (strict režim sa eksplicitnom listom pouzdanih proxy-ja). Ako lista nije
       postavljena/prazna, NE pozivamo ipware bez nje — non-strict ipware vraća
       NAJLEVLJU (spoofable) XFF vrednost, što je realan prod misconfig rizik.
       Vrednost prihvatamo samo ako ipware vrati IP (inače padamo na korak 3).

    3. ``REMOTE_ADDR`` (dev/test put — nema Nginx-a) ili ``""``.

    NIKAD ne vraća klijent-kontrolisanu/spoofable vrednost i NIKAD ``None``/prazno
    osim krajnjeg fallback-a kad ni REMOTE_ADDR ne postoji (tada ``""``).
    """
    # 1) PRIMARNI prod put: Nginx-ov X-Real-IP (= $remote_addr, pregažen pa
    #    non-spoofable). request.META ključ za X-Real-IP header je HTTP_X_REAL_IP.
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()

    # 2) Sekundarni put: ipware SAMO sa eksplicitnom trusted-proxy listom (strict).
    #    Bez liste ne ulazimo u non-strict (spoofable leftmost) granu.
    trusted = getattr(settings, "IPWARE_TRUSTED_PROXY_LIST", None)
    if trusted:
        client_ip, _routable = get_client_ip(request, proxy_trusted_ips=trusted)
        if client_ip:
            return client_ip

    # 3) Fallback (dev/test, nema proxy-ja): direktni peer ili prazan string.
    return request.META.get("REMOTE_ADDR", "")
