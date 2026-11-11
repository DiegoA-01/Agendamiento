"""Eventos de citas en tiempo real (M7, spec §9): Redis pub/sub + Server-Sent Events.

Cada cambio de cita publica un mensaje en el canal del negocio (`events:<tenant_id>`) cuando la
transacción ya se confirmó: así la agenda nunca ve una cita que luego se deshizo. El endpoint
`events/` se suscribe a ese canal y reenvía cada mensaje al navegador como SSE.

El streaming corre DESPUÉS de que el middleware desactiva el tenant, por eso el generador no
consulta la base: todo lo que necesita (negocio y alcance) se decide antes de empezar.
"""

import json
import time
from collections.abc import Iterator

import redis
from django.conf import settings
from django.db import transaction

from .signals import appointment_changed

CREATED = "appointment.created"
UPDATED = "appointment.updated"
CANCELLED = "appointment.cancelled"

# Cada cuánto se manda un comentario para que proxies y navegador no corten la conexión.
HEARTBEAT_SECONDS = 15
# El navegador reconecta solo tras este tiempo si la conexión se cae (milisegundos).
RETRY_MS = 3000


def _client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL)


def channel(tenant_id) -> str:
    return f"events:{tenant_id}"


def payload(kind: str, appointment) -> dict:
    """Lo mínimo para que la agenda sepa qué refrescar; los datos completos se piden por la API."""
    return {
        "type": kind,
        "appointment": {
            "id": str(appointment.pk),
            "status": appointment.status,
            "start_at": appointment.start_at.isoformat(),
            "end_at": appointment.end_at.isoformat(),
            "professional_id": str(appointment.professional_id),
            "resource_id": str(appointment.resource_id) if appointment.resource_id else None,
        },
    }


def publish(tenant_id, message: dict) -> None:
    try:
        _client().publish(channel(tenant_id), json.dumps(message))
    except redis.RedisError:
        # Sin Redis la cita igual se guardó; la agenda se pone al día al recargar.
        pass


def notify(kind: str, appointment) -> None:
    """Publica el evento cuando la transacción en curso se confirme (o ya, si no hay una), y avisa
    a las demás apps (notificaciones) con `signals.appointment_changed`."""
    message = payload(kind, appointment)
    tenant_id = appointment.tenant_id
    transaction.on_commit(lambda: publish(tenant_id, message))
    appointment_changed.send(sender="booking", kind=kind, appointment=appointment)


def _sse(message: dict) -> str:
    return f"event: {message['type']}\ndata: {json.dumps(message['appointment'])}\n\n"


def stream(
    tenant_id,
    *,
    professional_id=None,
    heartbeat: float = HEARTBEAT_SECONDS,
    max_seconds: float | None = None,
) -> Iterator[str]:
    """Genera el flujo SSE del negocio. Con `professional_id` solo pasan sus citas (alcance
    "solo lo propio" del profesional, spec §5). `max_seconds` corta el flujo (pruebas)."""
    pubsub = _client().pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel(tenant_id))
    started = time.monotonic()
    last_beat = started
    try:
        # Primero la suscripción, luego el primer envío: nada que se publique después se pierde.
        yield f"retry: {RETRY_MS}\n: conectado\n\n"
        while max_seconds is None or time.monotonic() - started < max_seconds:
            message = pubsub.get_message(timeout=1.0)
            if message and message.get("type") == "message":
                data = json.loads(message["data"])
                owner = data["appointment"]["professional_id"]
                if professional_id is None or owner == str(professional_id):
                    yield _sse(data)
            if time.monotonic() - last_beat >= heartbeat:
                last_beat = time.monotonic()
                yield ": ping\n\n"
    finally:
        pubsub.close()
