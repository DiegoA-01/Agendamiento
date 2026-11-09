"""Reportes contra valores calculados a mano (ver la tabla en `tests/reports/shop.py`)."""

import pytest

from apps.commissions import services as commissions
from apps.commissions.models import CommissionEntry
from apps.tenancy import services as tenancy
from apps.tenancy.context import tenant_context
from tests.reports.shop import ReportShop

pytestmark = pytest.mark.django_db

SALES = "/api/v1/reports/sales/"
BOOKINGS = "/api/v1/reports/bookings/"
MARCH = {"from": "2026-03-01", "to": "2026-03-31"}


@pytest.fixture
def shop():
    return ReportShop()


def money(row):
    return (
        row["sales"],
        row["commissions"],
        row["business"],
        row["appointments"],
        row["average_ticket"],
    )


# --- Ventas ------------------------------------------------------------------------------------


def test_march_sales_totals(shop):
    response = shop.client().get(SALES, MARCH)

    assert response.status_code == 200, response.json()
    body = response.json()
    assert (body["from"], body["to"], body["group_by"]) == ("2026-03-01", "2026-03-31", "day")
    # 30.000 + 15.000 + 30.000 + 33.333 + 15.000; 4 citas completadas.
    assert money(body["totals"]) == ("123333.00", "47833.22", "75499.78", 4, "30833.25")


def test_sales_by_day_use_the_business_time_zone(shop):
    rows = shop.client().get(SALES, {**MARCH, "group_by": "day"}).json()["rows"]
    assert [(r["key"], *money(r)) for r in rows] == [
        ("2026-03-02", "75000.00", "30000.00", "45000.00", 2, "37500.00"),
        ("2026-03-09", "33333.00", "11833.22", "21499.78", 1, "33333.00"),
        # 23:30 en Bogotá es 1 de abril en UTC: debe quedar en marzo.
        ("2026-03-31", "15000.00", "6000.00", "9000.00", 1, "15000.00"),
    ]


def test_sales_by_week_and_month(shop):
    client = shop.client()
    weeks = client.get(SALES, {**MARCH, "group_by": "week"}).json()["rows"]
    assert [(r["key"], r["sales"]) for r in weeks] == [
        ("2026-03-02", "75000.00"),
        ("2026-03-09", "33333.00"),
        ("2026-03-30", "15000.00"),
    ]
    months = client.get(
        SALES, {"from": "2026-03-01", "to": "2026-04-30", "group_by": "month"}
    ).json()["rows"]
    assert [(r["key"], r["sales"], r["appointments"]) for r in months] == [
        ("2026-03-01", "123333.00", 4)
    ]


def test_sales_by_professional_and_by_service(shop):
    client = shop.client()
    by_professional = client.get(SALES, {**MARCH, "group_by": "professional"}).json()["rows"]
    assert [(r["label"], *money(r)) for r in by_professional] == [
        ("Ana", "90000.00", "36000.00", "54000.00", 3, "30000.00"),
        ("Luis", "33333.00", "11833.22", "21499.78", 1, "33333.00"),
    ]
    assert by_professional[0]["key"] == str(shop.ana.pk)

    by_service = client.get(SALES, {**MARCH, "group_by": "service"}).json()["rows"]
    assert [(r["label"], r["sales"], r["appointments"]) for r in by_service] == [
        ("Corte", "93333.00", 3),
        ("Barba", "30000.00", 2),
    ]


def test_sales_filters(shop):
    client = shop.client()
    luis = client.get(SALES, {**MARCH, "professional_id": str(shop.luis.pk)}).json()
    assert money(luis["totals"]) == ("33333.00", "11833.22", "21499.78", 1, "33333.00")
    beard = client.get(SALES, {**MARCH, "service_id": str(shop.beard.pk)}).json()
    assert money(beard["totals"]) == ("30000.00", "12000.00", "18000.00", 2, "15000.00")
    category = client.get(SALES, {**MARCH, "category_id": str(shop.cut.category_id)}).json()
    assert category["totals"]["sales"] == "93333.00"


def test_adjustments_are_part_of_the_sales_totals(shop):
    with tenant_context(shop.tenant):
        entry = CommissionEntry.objects.get(appointment=shop.a3)
        commissions.create_adjustment(
            entry, base_amount=entry.base_amount, commission_amount=12000, reason="36 %"
        )

    totals = shop.client().get(SALES, MARCH).json()["totals"]

    # La venta no cambia; la comisión sube 166,78 y el negocio baja lo mismo. Sigue siendo 1 cita.
    assert money(totals) == ("123333.00", "48000.00", "75333.00", 4, "30833.25")


def test_a_professional_sees_only_their_sales(shop):
    client = shop.client("professional", professional=shop.ana)
    body = client.get(
        SALES, {**MARCH, "professional_id": str(shop.luis.pk), "group_by": "professional"}
    ).json()
    assert money(body["totals"]) == ("90000.00", "36000.00", "54000.00", 3, "30000.00")
    assert [r["label"] for r in body["rows"]] == ["Ana"]


def test_an_empty_range_returns_zeros(shop):
    body = shop.client().get(SALES, {"from": "2026-05-01", "to": "2026-05-31"}).json()
    assert money(body["totals"]) == ("0.00", "0.00", "0.00", 0, "0.00")
    assert body["rows"] == []


def test_sales_csv(shop):
    response = shop.client().get(f"{SALES}export/", {**MARCH, "group_by": "professional"})
    assert response.status_code == 200
    assert "ventas-2026-03-01-2026-03-31.csv" in response["Content-Disposition"]
    lines = response.content.decode("utf-8").lstrip("﻿").strip().splitlines()
    assert lines == [
        "professional,ventas,comisiones,negocio,citas,ticket_promedio",
        "Ana,90000.00,36000.00,54000.00,3,30000.00",
        "Luis,33333.00,11833.22,21499.78,1,33333.00",
        "TOTAL,123333.00,47833.22,75499.78,4,30833.25",
    ]


def test_unknown_group_is_rejected(shop):
    response = shop.client().get(SALES, {**MARCH, "group_by": "year"})
    assert response.status_code == 400
    assert "group_by" in response.json()["fields"]


# --- Reservas ----------------------------------------------------------------------------------


def bookings(row):
    return (
        row["total"],
        row["completed"],
        row["cancelled"],
        row["no_show"],
        row["cancellation_rate"],
        row["no_show_rate"],
    )


def test_march_bookings_exclude_rescheduled_ones(shop):
    body = shop.client().get(BOOKINGS, MARCH).json()
    # a1..a5 (a7 reprogramada no cuenta): 4 completadas, 1 cancelada = 20 %.
    assert bookings(body["totals"]) == (5, 4, 1, 0, "20.00", "0.00")
    assert [(r["label"], r["total"]) for r in body["by_professional"]] == [("Ana", 3), ("Luis", 2)]
    # Una cita con corte + barba cuenta en los dos servicios.
    assert [(r["label"], r["total"]) for r in body["by_service"]] == [("Corte", 4), ("Barba", 2)]


def test_bookings_by_month_and_rates(shop):
    body = shop.client().get(BOOKINGS, {"from": "2026-03-01", "to": "2026-04-30"}).json()
    # 6 citas: 1 cancelada (16,67 %) y 1 no-show (16,67 %).
    assert bookings(body["totals"]) == (6, 4, 1, 1, "16.67", "16.67")
    assert [(r["key"], *bookings(r)) for r in body["by_month"]] == [
        ("2026-03", 5, 4, 1, 0, "20.00", "0.00"),
        ("2026-04", 1, 0, 0, 1, "0.00", "100.00"),
    ]
    luis = [r for r in body["by_professional"] if r["label"] == "Luis"][0]
    assert bookings(luis) == (3, 1, 1, 1, "33.33", "33.33")


def test_bookings_filter_by_service_counts_each_appointment_once(shop):
    body = shop.client().get(BOOKINGS, {**MARCH, "service_id": str(shop.beard.pk)}).json()
    assert body["totals"]["total"] == 2  # a1 y a5


def test_a_professional_sees_only_their_bookings(shop):
    body = shop.client("professional", professional=shop.luis).get(BOOKINGS, MARCH).json()
    assert bookings(body["totals"]) == (2, 1, 1, 0, "50.00", "0.00")


def test_bookings_csv(shop):
    response = shop.client().get(f"{BOOKINGS}export/", MARCH)
    lines = response.content.decode("utf-8").lstrip("﻿").strip().splitlines()
    assert lines[0].startswith("agrupacion,nombre,total")
    assert "mes,2026-03,5,4,1,0,0,20.00,0.00" in lines
    assert lines[-1] == "total,TOTAL,5,4,1,0,0,20.00,0.00"


# --- Acceso ------------------------------------------------------------------------------------


@pytest.mark.parametrize("url", [SALES, BOOKINGS, f"{SALES}export/", f"{BOOKINGS}export/"])
def test_receptionist_cannot_see_reports(shop, url):
    assert shop.client("receptionist").get(url, MARCH).status_code == 403


@pytest.mark.parametrize("url", [SALES, BOOKINGS])
def test_reports_need_the_module(shop, url):
    tenancy.set_modules(shop.tenant, {"reports": False})
    response = shop.client().get(url, MARCH)
    assert response.status_code == 403
    assert response.json()["code"] == "module_disabled"


def test_reports_never_mix_businesses(shop):
    other = ReportShop()
    body = other.client().get(SALES, MARCH).json()
    assert body["totals"]["sales"] == "123333.00"  # solo las suyas, no el doble
