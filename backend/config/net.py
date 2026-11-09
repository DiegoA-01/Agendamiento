"""Datos de red de la petición que usan varias apps."""

from django.conf import settings
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str:
    """IP del cliente detrás de los proxies propios (`TRUSTED_PROXY_COUNT`)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = settings.TRUSTED_PROXY_COUNT
    if forwarded and hops > 0:
        addresses = [address.strip() for address in forwarded.split(",") if address.strip()]
        if addresses:
            return addresses[-min(hops, len(addresses))]
    return request.META.get("REMOTE_ADDR", "")
