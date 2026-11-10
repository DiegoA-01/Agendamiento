"""Notificaciones al cliente (M8, spec §10 y §14): confirmación, recordatorio, cancelación y
reprogramación; WhatsApp con consentimiento y respaldo por correo; reintentos e idempotencia."""

import datetime as dt

import pytest
from django.core import mail
from django.utils import timezone

from apps.booking import services as booking
from apps.notifications import services, tasks, templates
from apps.notifications.models import NotificationLog
from apps.notifications.providers import FakeProvider
from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_WHATSAPP
from apps.tenancy.context import tenant_context
from config.celery import app
from tests.booking.factories import AppointmentFactory, CustomerFactory
from tests.booking.test_appointments_api import URL, Shop, at, book
from tests.booking.test_public_api import PUBLIC, visitor
from tests.booking.test_public_api import booking as public_booking

pytestmark = pytest.mark.django_db

Kind = NotificationLog.Kind
Channel = NotificationLog.Channel
Status = NotificationLog.Status


@pytest.fixture(autouse=True)
def eager(monkeypatch, settings):
    monkeypatch.setattr(app.conf, "task_always_eager", True)
    monkeypatch.setattr(app.conf, "task_eager_propagates", True)
    settings.WHATSAPP_PROVIDER = "apps.notifications.providers.FakeProvider"
    settings.PUBLIC_SITE_URL = "https://{host}"
    FakeProvider.reset()
    yield
    FakeProvider.reset()


@pytest.fixture
def shop():
    shop = Shop()
    shop.ana = shop.professional("Ana")
    return shop


def enable_whatsapp(tenant):
    tenancy.set_modules(tenant, {MODULE_WHATSAPP: True})


def logs(tenant, **filters):
    with tenant_context(tenant):
        return list(NotificationLog.objects.filter(**filters).order_by("created_at"))


def book_from_panel(shop, django_capture_on_commit_callbacks, **customer):
    client, _ = shop.client()
    payload_customer = {"full_name": "Camila Ríos", "phone": "300 123 4567", **customer}
    with django_capture_on_commit_callbacks(execute=True):
        response = book(shop, client, at(10), shop.ana, customer=payload_customer)
    assert response.status_code == 201, response.json()
    return client, response.json()


# --- Confirmación ------------------------------------------------------------------------------


def test_a_panel_booking_sends_the_confirmation_by_email(shop, django_capture_on_commit_callbacks):
    _, appointment = book_from_panel(
        shop, django_capture_on_commit_callbacks, email="camila@example.com"
    )

    (log,) = logs(shop.tenant)
    assert (log.kind, log.channel, log.status, log.attempts) == (
        Kind.CONFIRMATION, Channel.EMAIL, Status.SENT, 1
    )  # fmt: skip
    assert log.sent_at is not None
    (email,) = mail.outbox
    assert email.to == ["camila@example.com"]
    assert email.subject == f"Tu cita en {shop.tenant.name} está confirmada"
    # Fecha y hora en la zona del negocio, con el nombre del profesional y del servicio.
    assert "Ana" in email.body and shop.service.name in email.body
    assert "a las 10:00" in email.body
    assert f"https://{shop.tenant.slug}." in email.body and "/cita/" in email.body
    assert str(log.appointment_id) == appointment["id"]


def test_without_email_nor_whatsapp_nothing_is_sent(shop, django_capture_on_commit_callbacks):
    book_from_panel(shop, django_capture_on_commit_callbacks)
    assert logs(shop.tenant) == []
    assert mail.outbox == []


def test_a_web_booking_goes_by_whatsapp_when_the_plan_includes_it(
    shop, django_capture_on_commit_callbacks
):
    enable_whatsapp(shop.tenant)
    with django_capture_on_commit_callbacks(execute=True):
        response = visitor(shop).post(
            f"{PUBLIC}/appointments/", public_booking(shop, at(10), shop.ana), format="json"
        )
    assert response.status_code == 201, response.json()

    (log,) = logs(shop.tenant)
    assert (log.channel, log.to, log.status) == (Channel.WHATSAPP, "+573001234567", Status.SENT)
    (sent,) = FakeProvider.sent
    assert sent["to"] == "+573001234567"
    assert sent["manage_url"].endswith(f"/cita/{response.json()['manage_url'].rsplit('/', 1)[-1]}")
    assert mail.outbox == []


def test_whatsapp_needs_consent_for_panel_bookings(shop, django_capture_on_commit_callbacks):
    """Desde el panel, sin que el cliente acepte mensajes, sale por correo y no por WhatsApp."""
    enable_whatsapp(shop.tenant)
    book_from_panel(shop, django_capture_on_commit_callbacks, email="camila@example.com")

    (log,) = logs(shop.tenant)
    assert log.channel == Channel.EMAIL
    assert FakeProvider.sent == []


def test_without_the_whatsapp_module_web_bookings_go_by_email(
    shop, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        visitor(shop).post(
            f"{PUBLIC}/appointments/", public_booking(shop, at(10), shop.ana), format="json"
        )
    (log,) = logs(shop.tenant)
    assert (log.channel, log.to) == (Channel.EMAIL, "camila@example.com")


# --- Cancelación, reprogramación y otros cambios ------------------------------------------------


def test_cancel_and_reschedule_notify_the_customer(shop, django_capture_on_commit_callbacks):
    client, appointment = book_from_panel(
        shop, django_capture_on_commit_callbacks, email="camila@example.com"
    )
    with django_capture_on_commit_callbacks(execute=True):
        moved = client.post(
            f"{URL}{appointment['id']}/reschedule/",
            {"start_at": at(11).isoformat(), "professional_id": str(shop.ana.pk)},
            format="json",
        ).json()
    with django_capture_on_commit_callbacks(execute=True):
        client.post(f"{URL}{moved['id']}/cancel/", {"reason": "Viaje"}, format="json")

    kinds = [(log.kind, str(log.appointment_id)) for log in logs(shop.tenant)]
    assert kinds == [
        (Kind.CONFIRMATION, appointment["id"]),
        (Kind.RESCHEDULE, moved["id"]),
        (Kind.CANCELLATION, moved["id"]),
    ]
    assert "a las 11:00" in mail.outbox[1].body
    assert mail.outbox[2].subject.endswith("fue cancelada")


def test_starting_or_completing_does_not_message_the_customer(
    shop, django_capture_on_commit_callbacks
):
    client, appointment = book_from_panel(
        shop, django_capture_on_commit_callbacks, email="camila@example.com"
    )
    with django_capture_on_commit_callbacks(execute=True):
        client.post(f"{URL}{appointment['id']}/start/")
        client.post(f"{URL}{appointment['id']}/complete/")
    assert [log.kind for log in logs(shop.tenant)] == [Kind.CONFIRMATION]


# --- Idempotencia, reintentos y respaldo ---------------------------------------------------------


def test_the_same_message_is_never_sent_twice(shop):
    with tenant_context(shop.tenant):
        appointment = AppointmentFactory(
            professional=shop.ana, customer=CustomerFactory(email="c@example.com")
        )
        first = services.schedule(Kind.CONFIRMATION, appointment.pk)
        second = services.schedule(Kind.CONFIRMATION, appointment.pk)
        tasks.deliver.delay(str(shop.tenant.pk), str(first.pk))
        tasks.deliver.delay(str(shop.tenant.pk), str(first.pk))  # Celery puede repetir una tarea
    assert second is None
    assert len(mail.outbox) == 1


def scheduled_log(shop, **customer):
    with tenant_context(shop.tenant):
        appointment = AppointmentFactory(
            professional=shop.ana, customer=CustomerFactory(**customer)
        )
        return services.schedule(Kind.CONFIRMATION, appointment.pk)


def test_whatsapp_is_retried_and_succeeds_on_the_third_attempt(shop):
    enable_whatsapp(shop.tenant)
    FakeProvider.fail_next = 2
    log = scheduled_log(shop, marketing_consent=True)
    with tenant_context(shop.tenant):
        outcomes = [services.attempt_delivery(log) for _ in range(4)]
    assert outcomes == [services.RETRY, services.RETRY, services.SENT, services.SENT]
    assert (log.status, log.attempts, log.error) == (Status.SENT, 3, "")
    assert len(FakeProvider.sent) == 1  # el cuarto llamado no reenvía


def test_whatsapp_falls_back_to_email_after_three_failures(
    shop, django_capture_on_commit_callbacks
):
    enable_whatsapp(shop.tenant)
    FakeProvider.fail_next = 3
    log = scheduled_log(shop, marketing_consent=True, email="c@example.com")
    with tenant_context(shop.tenant), django_capture_on_commit_callbacks(execute=True):
        outcomes = [services.attempt_delivery(log) for _ in range(3)]
    assert outcomes == [services.RETRY, services.RETRY, services.FAILED]
    whatsapp, email = logs(shop.tenant)
    assert (whatsapp.channel, whatsapp.status, whatsapp.attempts) == (
        Channel.WHATSAPP, Status.FAILED, 3
    )  # fmt: skip
    assert "Fallo simulado" in whatsapp.error
    assert (email.channel, email.status, email.body) == (Channel.EMAIL, Status.SENT, whatsapp.body)
    assert mail.outbox[0].to == ["c@example.com"]


def test_an_email_that_keeps_failing_ends_as_failed(shop, monkeypatch):
    def broken(*args, **kwargs):
        raise ConnectionError("SMTP caído")

    monkeypatch.setattr("apps.notifications.providers.send_mail", broken)
    log = scheduled_log(shop, email="c@example.com")
    with tenant_context(shop.tenant):
        outcomes = [services.attempt_delivery(log) for _ in range(3)]
    assert outcomes[-1] == services.FAILED
    assert (log.status, log.attempts, log.error) == (Status.FAILED, 3, "SMTP caído")
    assert logs(shop.tenant, channel=Channel.WHATSAPP) == []  # un correo no tiene respaldo


def test_the_task_waits_longer_before_each_retry(shop, monkeypatch):
    enable_whatsapp(shop.tenant)
    FakeProvider.fail_next = 1
    log = scheduled_log(shop, marketing_consent=True)
    retries = []

    class Retry(Exception):
        pass

    def fake_retry(**kwargs):
        retries.append(kwargs)
        return Retry()

    monkeypatch.setattr(tasks.deliver, "retry", fake_retry)
    with pytest.raises(Retry):
        tasks.deliver(str(shop.tenant.pk), str(log.pk))
    assert retries == [{"countdown": 60}]
    assert tasks.deliver(str(shop.tenant.pk), str(log.pk)) == services.SENT


def test_the_retry_wait_grows():
    assert [tasks.backoff_seconds(n) for n in (1, 2, 3)] == [60, 120, 240]


# --- Recordatorios ------------------------------------------------------------------------------


def test_reminders_go_out_24h_and_2h_before_only_once(
    shop, settings, django_capture_on_commit_callbacks
):
    settings.NOTIFICATION_REMINDER_HOURS = [24, 2]
    now = timezone.now().replace(microsecond=0)
    with tenant_context(shop.tenant):
        customer = CustomerFactory(email="c@example.com")
        tomorrow = AppointmentFactory(
            professional=shop.ana,
            customer=customer,
            start_at=now + dt.timedelta(hours=23, minutes=50),
        )
        soon = AppointmentFactory(
            professional=shop.ana,
            customer=customer,
            start_at=now + dt.timedelta(hours=1, minutes=45),
        )
        AppointmentFactory(  # dentro de 5 h: todavía no le toca ningún recordatorio
            professional=shop.ana, customer=customer, start_at=now + dt.timedelta(hours=5)
        )
        AppointmentFactory(  # cancelada: no se le recuerda
            professional=shop.ana,
            customer=customer,
            start_at=now + dt.timedelta(hours=23, minutes=40),
            status="cancelled",
        )

    with django_capture_on_commit_callbacks(execute=True):
        assert tasks.send_reminders.delay(str(shop.tenant.pk)).get() == 2
    with django_capture_on_commit_callbacks(execute=True):
        assert tasks.send_reminders.delay(str(shop.tenant.pk)).get() == 0  # Beat vuelve a correr

    reminders = logs(shop.tenant, kind=Kind.REMINDER)
    assert {(str(r.appointment_id), r.dedupe_key.split(":")[2]) for r in reminders} == {
        (str(tomorrow.pk), "24h"),
        (str(soon.pk), "2h"),
    }
    assert all(r.status == Status.SENT for r in reminders)
    assert mail.outbox[0].subject.startswith("Recordatorio de tu cita")


def test_reminders_are_scheduled_by_celery_beat():
    from django.conf import settings

    entry = settings.CELERY_BEAT_SCHEDULE["notifications-reminders"]
    assert entry["task"] == "tenancy.for_each_active_tenant"
    assert entry["args"] == ["notifications.send_reminders"]


def test_a_suspended_business_gets_no_messages(shop):
    with tenant_context(shop.tenant):
        appointment = AppointmentFactory(
            professional=shop.ana, customer=CustomerFactory(email="c@example.com")
        )
        log = services.schedule(Kind.CONFIRMATION, appointment.pk)
    tenancy.suspend_tenant(shop.tenant)
    tasks.deliver.delay(str(shop.tenant.pk), str(log.pk))
    assert mail.outbox == []


# --- Plantillas ---------------------------------------------------------------------------------


def test_templates_follow_the_language_and_the_vertical():
    variables = {
        "customer_name": "Laura",
        "service": "Manicure",
        "professional": "Ana",
        "date": "Monday, November 9",
        "time": "10:00 AM",
        "business": "Nails Co",
        "manage_url": "https://x/cita/abc",
    }
    message = templates.render("confirmation", language="en", vertical="nails", variables=variables)
    assert message.subject == "Your appointment at Nails Co is confirmed"
    assert "Manicure with Ana, on Monday, November 9 at 10:00 AM" in message.body
    assert message.body.endswith("See you for your nails!")
    # Un idioma sin plantillas cae al español.
    assert templates.render(
        "reminder", language="pt", vertical="barbershop", variables=variables
    ).body.endswith("¡Te esperamos en la barbería!")


def test_dates_are_written_in_the_business_language():
    value = dt.datetime(2026, 11, 9, 15, 30)
    assert services.format_date(value, "es") == "lunes 9 de noviembre"
    assert services.format_date(value, "en") == "Monday, November 9"
    assert (services.format_time(value, "es"), services.format_time(value, "en")) == (
        "15:30", "3:30 PM"
    )  # fmt: skip


def test_reminder_lookup_only_reads_confirmed_appointments(shop):
    now = timezone.now()
    with tenant_context(shop.tenant):
        confirmed = AppointmentFactory(professional=shop.ana, start_at=now + dt.timedelta(hours=1))
        AppointmentFactory(
            professional=shop.ana,
            start_at=now + dt.timedelta(hours=1, minutes=30),
            status="pending",
        )
        assert booking.confirmed_starting_between(now, now + dt.timedelta(hours=2)) == [
            confirmed.pk
        ]
