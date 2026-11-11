"""Plantillas de los mensajes al cliente (spec §10), por idioma y por vertical.

En el MVP se editan solo aquí, en código. Variables: `{customer_name}`, `{service}`,
`{professional}`, `{date}`, `{time}`, `{business}`, `{manage_url}`. El vertical solo cambia la
despedida; el resto del texto es igual para barberías, salones, uñas y spa.
"""

from dataclasses import dataclass

DEFAULT_LANGUAGE = "es"


@dataclass(frozen=True)
class Message:
    subject: str
    body: str


TEMPLATES: dict[str, dict[str, Message]] = {
    "es": {
        "confirmation": Message(
            "Tu cita en {business} está confirmada",
            "Hola, {customer_name}. Tu cita en {business} quedó confirmada:\n"
            "{service} con {professional}, el {date} a las {time}.\n"
            "Para verla o cancelarla: {manage_url}",
        ),
        "reminder": Message(
            "Recordatorio de tu cita en {business}",
            "Hola, {customer_name}. Te recordamos tu cita en {business}:\n"
            "{service} con {professional}, el {date} a las {time}.\n"
            "Si no puedes asistir, cancélala aquí: {manage_url}",
        ),
        "cancellation": Message(
            "Tu cita en {business} fue cancelada",
            "Hola, {customer_name}. Tu cita en {business} del {date} a las {time} "
            "({service}) quedó cancelada.\n"
            "Si quieres, puedes reservar de nuevo cuando quieras.",
        ),
        "reschedule": Message(
            "Tu cita en {business} cambió de horario",
            "Hola, {customer_name}. Tu cita en {business} se movió:\n"
            "{service} con {professional}, ahora el {date} a las {time}.\n"
            "Para verla o cancelarla: {manage_url}",
        ),
    },
    "en": {
        "confirmation": Message(
            "Your appointment at {business} is confirmed",
            "Hi, {customer_name}. Your appointment at {business} is confirmed:\n"
            "{service} with {professional}, on {date} at {time}.\n"
            "To view or cancel it: {manage_url}",
        ),
        "reminder": Message(
            "Reminder of your appointment at {business}",
            "Hi, {customer_name}. This is a reminder of your appointment at {business}:\n"
            "{service} with {professional}, on {date} at {time}.\n"
            "If you cannot make it, cancel it here: {manage_url}",
        ),
        "cancellation": Message(
            "Your appointment at {business} was cancelled",
            "Hi, {customer_name}. Your appointment at {business} on {date} at {time} "
            "({service}) was cancelled.\n"
            "You can book again anytime.",
        ),
        "reschedule": Message(
            "Your appointment at {business} was rescheduled",
            "Hi, {customer_name}. Your appointment at {business} was moved:\n"
            "{service} with {professional}, now on {date} at {time}.\n"
            "To view or cancel it: {manage_url}",
        ),
    },
}

SIGN_OFF: dict[str, dict[str, str]] = {
    "es": {
        "barbershop": "¡Te esperamos en la barbería!",
        "salon": "¡Te esperamos en el salón!",
        "nails": "¡Te esperamos para consentir tus uñas!",
        "spa": "¡Te esperamos para que te relajes!",
    },
    "en": {
        "barbershop": "See you at the barbershop!",
        "salon": "See you at the salon!",
        "nails": "See you for your nails!",
        "spa": "See you for some relaxing time!",
    },
}


def render(kind: str, *, language: str, vertical: str, variables: dict[str, str]) -> Message:
    language = language if language in TEMPLATES else DEFAULT_LANGUAGE
    template = TEMPLATES[language][kind]
    sign_off = SIGN_OFF[language].get(vertical, "")
    body = template.body.format(**variables)
    if sign_off and kind != "cancellation":
        body = f"{body}\n\n{sign_off}"
    return Message(template.subject.format(**variables), body)
