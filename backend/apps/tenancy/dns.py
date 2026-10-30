"""Consulta de registros DNS para verificar dominios propios.

Sin dependencias nuevas: consulta por DNS sobre HTTPS (JSON de Google). Se puede cambiar por otra
implementación con el setting `DNS_RESOLVER` (ruta a una clase con `txt()` y `cname()`); los tests
usan una falsa.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

DOH_URL = "https://dns.google/resolve"
_TYPES = {"TXT": 16, "CNAME": 5}


class DnsLookupError(Exception):
    """No se pudo consultar el DNS (red caída, tiempo agotado, respuesta inválida)."""


class DohResolver:
    timeout = 5

    def _query(self, name: str, record_type: str) -> list[str]:
        url = f"{DOH_URL}?{urllib.parse.urlencode({'name': name, 'type': record_type})}"
        request = urllib.request.Request(url, headers={"Accept": "application/dns-json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise DnsLookupError(str(exc)) from exc
        answers = payload.get("Answer") or []
        return [a["data"] for a in answers if a.get("type") == _TYPES[record_type]]

    def txt(self, name: str) -> list[str]:
        return [value.strip('"') for value in self._query(name, "TXT")]

    def cname(self, name: str) -> list[str]:
        return [value.rstrip(".").lower() for value in self._query(name, "CNAME")]


def get_resolver():
    return import_string(getattr(settings, "DNS_RESOLVER", "apps.tenancy.dns.DohResolver"))()
