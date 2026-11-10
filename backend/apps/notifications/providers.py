"""Canales de envío (spec §10): correo con el `EmailBackend` de Django y WhatsApp Business Cloud
API detrás de la interfaz `WhatsAppProvider`, con `FakeProvider` para desarrollo y pruebas.

Cada `send` devuelve normalmente o lanza `DeliveryError`; los reintentos los hace la tarea.
"""

import json
import urllib.error
import urllib.request
from typing import Protocol

from django.conf import settings
from django.core.mail import send_mail
from django.utils.module_loading import import_string


class DeliveryError(Exception):
    """El proveedor no aceptó el mensaje (red caída, credenciales malas, número inválido…)."""


def send_email(*, to: str, subject: str, body: str) -> None:
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except Exception as exc:  # SMTP, SES o cualquier backend: todo error cuenta como fallo
        raise DeliveryError(str(exc)) from exc


class WhatsAppProvider(Protocol):
    def send(self, *, to: str, body: str, manage_url: str) -> None: ...


class FakeProvider:
    """No sale a internet: guarda los mensajes en memoria (desarrollo y pruebas).

    `fail_next` permite simular fallos para probar los reintentos y el respaldo por correo.
    """

    sent: list[dict[str, str]] = []
    fail_next: int = 0

    def send(self, *, to: str, body: str, manage_url: str) -> None:
        if FakeProvider.fail_next > 0:
            FakeProvider.fail_next -= 1
            raise DeliveryError("Fallo simulado de WhatsApp.")
        FakeProvider.sent.append({"to": to, "body": body, "manage_url": manage_url})

    @classmethod
    def reset(cls) -> None:
        cls.sent = []
        cls.fail_next = 0


class CloudApiProvider:
    """WhatsApp Business Cloud API de Meta, sin dependencias nuevas (urllib).

    Manda un mensaje de texto con el enlace de la cita. Ojo: fuera de la ventana de 24 h de una
    conversación, Meta exige plantillas aprobadas; ver `pormejorar.md`.
    """

    def send(self, *, to: str, body: str, manage_url: str) -> None:
        token = settings.WHATSAPP_TOKEN
        phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        if not token or not phone_number_id:
            raise DeliveryError("WhatsApp no está configurado.")
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{phone_number_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "text",
            "text": {"preview_url": True, "body": body},
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status >= 300:
                    raise DeliveryError(f"WhatsApp respondió {response.status}.")
        except urllib.error.URLError as exc:
            raise DeliveryError(str(exc)) from exc


def whatsapp_provider() -> WhatsAppProvider:
    return import_string(settings.WHATSAPP_PROVIDER)()
