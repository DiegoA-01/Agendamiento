import datetime as dt
from decimal import Decimal

import pytest
from django.db import DatabaseError, transaction

from apps.commissions import services as commissions
from apps.commissions.models import CommissionEntry, ImmutableEntryError
from apps.tenancy import services as tenancy
from apps.tenancy.context import tenant_context
from tests.booking.factories import AppointmentFactory, AppointmentItemFactory
from tests.reports.shop import ReportShop

pytestmark = pytest.mark.django_db

URL = "/api/v1/commissions/"


@pytest.fixture
def shop():
    return ReportShop()


# --- Cálculo -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("base", "pct", "commission", "business"),
    [
        ("30000.00", "40.00", "12000.00", "18000.00"),
        ("33333.00", "35.50", "11833.22", "21499.78"),  # 11.833,215 sube
        ("10001.00", "12.50", "1250.13", "8750.87"),  # 1.250,125: mitad hacia arriba, no par
        ("25000.00", "0.00", "0.00", "25000.00"),
        ("25000.00", "100.00", "25000.00", "0.00"),
    ],
)
def test_split_rounds_half_up_and_both_parts_add_up_to_the_base(base, pct, commission, business):
    got = commissions.split(Decimal(base), Decimal(pct))
    assert got == (Decimal(commission), Decimal(business))
    assert sum(got) == Decimal(base)


def test_completing_through_the_api_records_one_entry_per_service_with_the_frozen_pct(shop):
    client = shop.client()
    with tenant_context(shop.tenant):
        start = dt.datetime.now(dt.UTC).replace(microsecond=0) + dt.timedelta(hours=1)
        appointment = AppointmentFactory(
            professional=shop.ana,
            start_at=start,
            end_at=start + dt.timedelta(minutes=45),
            status="in_progress",
        )
        AppointmentItemFactory(
            appointment=appointment,
            service=shop.cut,
            price_charged=Decimal("30000"),
            commission_pct_snapshot=Decimal("40"),
        )
        AppointmentItemFactory(
            appointment=appointment,
            service=shop.beard,
            price_charged=Decimal("15000"),
            commission_pct_snapshot=Decimal("25"),  # override del profesional para la barba
        )
        # El porcentaje cambia después de reservar: no afecta la comisión de esta cita.
        shop.ana.default_commission_pct = Decimal("50")
        shop.ana.save()

    response = client.post(f"/api/v1/appointments/{appointment.pk}/complete/")

    assert response.status_code == 200, response.json()
    with tenant_context(shop.tenant):
        entries = {e.service_id: e for e in CommissionEntry.objects.filter(appointment=appointment)}
    assert len(entries) == 2
    cut, beard = entries[shop.cut.pk], entries[shop.beard.pk]
    assert (cut.pct, cut.commission_amount, cut.business_amount) == (
        Decimal("40.00"),
        Decimal("12000.00"),
        Decimal("18000.00"),
    )
    assert (beard.pct, beard.commission_amount, beard.business_amount) == (
        Decimal("25.00"),
        Decimal("3750.00"),
        Decimal("11250.00"),
    )
    assert cut.appointment_start_at == appointment.start_at

    # Completar otra vez es una transición inválida y no duplica nada.
    assert client.post(f"/api/v1/appointments/{appointment.pk}/complete/").status_code == 409
    with tenant_context(shop.tenant):
        assert CommissionEntry.objects.filter(appointment=appointment).count() == 2
        assert commissions.record_for_appointment(appointment)  # idempotente
        assert CommissionEntry.objects.filter(appointment=appointment).count() == 2


@pytest.mark.parametrize("action", ["cancel", "no-show"])
def test_only_completed_appointments_generate_commissions(shop, action):
    client = shop.client()
    with tenant_context(shop.tenant):
        start = dt.datetime.now(dt.UTC).replace(microsecond=0) + dt.timedelta(days=1)
        appointment = AppointmentFactory(
            professional=shop.ana,
            start_at=start,
            end_at=start + dt.timedelta(minutes=30),
            status="confirmed",
        )
        AppointmentItemFactory(appointment=appointment, service=shop.cut)

    assert client.post(f"/api/v1/appointments/{appointment.pk}/{action}/").status_code == 200
    with tenant_context(shop.tenant):
        assert not CommissionEntry.objects.filter(appointment=appointment).exists()


def test_entries_cannot_be_edited_or_deleted_not_even_with_sql(shop):
    with tenant_context(shop.tenant):
        entry = CommissionEntry.objects.filter(appointment=shop.a2).get()
        entry.commission_amount = Decimal("1")
        with pytest.raises(ImmutableEntryError):
            entry.save()
        with pytest.raises(ImmutableEntryError):
            entry.delete()
        with pytest.raises(DatabaseError), transaction.atomic():
            CommissionEntry.objects.filter(pk=entry.pk).update(reason="cambio")
        with pytest.raises(DatabaseError), transaction.atomic():
            CommissionEntry.objects.filter(pk=entry.pk).delete()
        entry.refresh_from_db()
        assert entry.commission_amount == Decimal("12000.00")


# --- Listado -----------------------------------------------------------------------------------


def test_owner_lists_march_commissions_in_local_time(shop):
    client = shop.client()

    response = client.get(URL, {"from": "2026-03-01", "to": "2026-03-31"})

    assert response.status_code == 200, response.json()
    rows = response.json()["results"]
    # a1 (2 servicios), a2, a3, a5 (23:30 del 31 de marzo en Bogotá); a4, a6 y a7 no cuentan.
    assert [(r["professional_name"], r["service_name"]) for r in rows] == [
        ("Ana", "Corte"),
        ("Ana", "Barba"),
        ("Ana", "Corte"),
        ("Luis", "Corte"),
        ("Ana", "Barba"),
    ]
    assert sum(Decimal(r["commission_amount"]) for r in rows) == Decimal("47833.22")
    assert rows[-1]["appointment_start_at"] == "2026-03-31T23:30:00-05:00"

    april = client.get(URL, {"from": "2026-04-01", "to": "2026-04-30"}).json()["results"]
    assert april == []


def test_a_professional_only_sees_their_commissions_even_asking_for_others(shop):
    client = shop.client("professional", professional=shop.luis)

    response = client.get(
        URL, {"from": "2026-03-01", "to": "2026-03-31", "professional_id": str(shop.ana.pk)}
    )

    assert response.status_code == 200
    assert response.json()["results"] == []
    mine = client.get(URL, {"from": "2026-03-01", "to": "2026-03-31"}).json()["results"]
    assert [r["commission_amount"] for r in mine] == ["11833.22"]


def test_a_professional_without_a_linked_profile_sees_nothing(shop):
    client = shop.client("professional")
    response = client.get(URL, {"from": "2026-03-01", "to": "2026-03-31"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_receptionist_cannot_see_commissions(shop):
    response = shop.client("receptionist").get(URL)
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_commissions_need_the_module(shop):
    tenancy.set_modules(shop.tenant, {"commissions": False})
    response = shop.client().get(URL)
    assert response.status_code == 403
    assert response.json()["code"] == "module_disabled"


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"from": "2026-03-31", "to": "2026-03-01"}, "to"),
        ({"from": "2025-01-01", "to": "2026-03-01"}, "to"),
        ({"from": "marzo"}, "start"),
    ],
)
def test_invalid_ranges_are_rejected(shop, params, field):
    response = shop.client().get(URL, params)
    assert response.status_code == 400
    assert field in response.json()["fields"]


def test_csv_export_has_bom_and_neutralizes_formulas(shop):
    with tenant_context(shop.tenant):
        shop.luis.display_name = '=HYPERLINK("http://x")'
        shop.luis.save()

    response = shop.client().get(f"{URL}export/", {"from": "2026-03-01", "to": "2026-03-31"})

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "comisiones.csv" in response["Content-Disposition"]
    text = response.content.decode("utf-8")
    assert text.startswith("﻿fecha_cita,tipo,profesional")
    lines = text.strip().splitlines()
    assert len(lines) == 6  # cabecera + 5 servicios
    assert any("'=HYPERLINK" in line for line in lines)
    assert "2026-03-31 23:30,entry,Ana,Barba,15000.00,40.00,6000.00,9000.00," in lines


# --- Ajustes -----------------------------------------------------------------------------------


def test_owner_adjusts_a_commission_and_the_original_stays_untouched(shop):
    client = shop.client()
    with tenant_context(shop.tenant):
        entry = CommissionEntry.objects.get(appointment=shop.a3)

    response = client.post(
        f"{URL}{entry.pk}/adjustments/",
        {"base_amount": "33333.00", "commission_amount": "12000.00", "reason": "Pacto 36 %"},
        format="json",
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["kind"] == "adjustment"
    assert body["adjusts_id"] == str(entry.pk)
    assert body["base_amount"] == "0.00"
    assert body["commission_amount"] == "166.78"
    assert body["business_amount"] == "-166.78"
    with tenant_context(shop.tenant):
        entry.refresh_from_db()
        assert entry.commission_amount == Decimal("11833.22")

    # Un segundo ajuste parte de lo ya corregido.
    second = client.post(
        f"{URL}{entry.pk}/adjustments/",
        {"base_amount": "30000.00", "commission_amount": "12000.00", "reason": "Descuento"},
        format="json",
    ).json()
    assert (second["base_amount"], second["commission_amount"]) == ("-3333.00", "0.00")

    same = client.post(
        f"{URL}{entry.pk}/adjustments/",
        {"base_amount": "30000.00", "commission_amount": "12000.00", "reason": "Otra vez"},
        format="json",
    )
    assert same.status_code == 400
    assert same.json()["code"] == "invalid_adjustment"


@pytest.mark.parametrize("role", ["admin", "professional", "receptionist"])
def test_only_the_owner_can_adjust(shop, role):
    with tenant_context(shop.tenant):
        entry = CommissionEntry.objects.get(appointment=shop.a3)
    response = shop.client(role).post(
        f"{URL}{entry.pk}/adjustments/",
        {"base_amount": "33333.00", "commission_amount": "0.00", "reason": "x"},
        format="json",
    )
    assert response.status_code == 403


def test_adjustments_validate_amounts_and_entries_of_other_businesses_are_404(shop):
    client = shop.client()
    with tenant_context(shop.tenant):
        entry = CommissionEntry.objects.get(appointment=shop.a3)
    too_much = client.post(
        f"{URL}{entry.pk}/adjustments/",
        {"base_amount": "100.00", "commission_amount": "200.00", "reason": "x"},
        format="json",
    )
    assert too_much.status_code == 400

    other = ReportShop()
    with tenant_context(other.tenant):
        foreign = CommissionEntry.objects.filter(appointment=other.a3).get()
    response = client.post(
        f"{URL}{foreign.pk}/adjustments/",
        {"base_amount": "1.00", "commission_amount": "0.00", "reason": "x"},
        format="json",
    )
    assert response.status_code == 404
