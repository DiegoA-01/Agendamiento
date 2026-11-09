"""Reportes de ventas y de reservas (spec §11).

Ventas sale de las comisiones: solo una cita completada genera comisión, así que solo eso cuenta
como venta, y los ajustes ya están sumados. Reservas sale de las citas. Un profesional solo ve sus
filas en los dos.
"""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek

from apps.booking import services as booking
from apps.commissions import services as commissions

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

SALES_GROUPS = ("day", "week", "month", "professional", "service")


@dataclass(frozen=True)
class Filters:
    start: dt.date
    end: dt.date
    professional_id: object = None
    service_id: object = None
    category_id: object = None


def _scoped_professional(user, filters: Filters):
    """El profesional que se puede ver: el suyo si su alcance es `own` (ignora lo que pida)."""
    own = commissions.own_professional_id(user)  # 403 si el rol no ve reportes
    return own if own is not None else filters.professional_id


def _sales_metrics(row: dict) -> dict:
    sales = row["sales"] or ZERO
    count = row["appointments"] or 0
    return {
        "sales": sales,
        "commissions": row["commissions"] or ZERO,
        "business": row["business"] or ZERO,
        "appointments": count,
        "average_ticket": (sales / count).quantize(CENT) if count else ZERO,
    }


_SALES_AGGREGATES = {
    "sales": Sum("base_amount"),
    "commissions": Sum("commission_amount"),
    "business": Sum("business_amount"),
    # Citas con al menos una venta; un ajuste de una cita ya contada no suma otra.
    "appointments": Count("appointment_id", distinct=True),
}


def sales_report(user, filters: Filters, group_by: str = "day") -> dict:
    """Totales y filas agrupadas por día, semana, mes, profesional o servicio."""
    start_at, end_at = commissions.local_range(filters.start, filters.end)
    entries = commissions.entries_for(
        user,
        start_at=start_at,
        end_at=end_at,
        professional_id=_scoped_professional(user, filters),
        service_id=filters.service_id,
        category_id=filters.category_id,
    ).order_by()

    totals = _sales_metrics(entries.aggregate(**_SALES_AGGREGATES))

    if group_by == "professional":
        grouped = entries.values(key=F("professional_id"), label=F("professional__display_name"))
    elif group_by == "service":
        grouped = entries.values(key=F("service_id"), label=F("service__name"))
    else:
        trunc = {"day": TruncDate, "week": TruncWeek, "month": TruncMonth}[group_by]
        grouped = entries.annotate(period=trunc("appointment_start_at")).values(key=F("period"))
    rows = []
    for row in grouped.annotate(**_SALES_AGGREGATES).order_by("key"):
        key = row["key"]
        if isinstance(key, dt.datetime):
            key = key.date()
        rows.append(
            {
                "key": str(key),
                "label": row.get("label") or str(key),
                **_sales_metrics(row),
            }
        )
    if group_by in ("professional", "service"):
        rows.sort(key=lambda row: (-row["sales"], row["label"]))
    return {
        "group_by": group_by,
        "from": filters.start,
        "to": filters.end,
        "totals": totals,
        "rows": rows,
    }


# --- Reservas ----------------------------------------------------------------------------------


def _rate(part: int, total: int) -> Decimal:
    """Porcentaje con dos decimales (12.50 = 12,5 %)."""
    return (Decimal(part) * 100 / total).quantize(CENT) if total else ZERO


_STATUS_COUNTS = {
    "total": Count("id"),
    "completed": Count("id", filter=Q(status="completed")),
    "cancelled": Count("id", filter=Q(status="cancelled")),
    "no_show": Count("id", filter=Q(status="no_show")),
    "web": Count("id", filter=Q(source="web")),
}


def _booking_metrics(row: dict) -> dict:
    total = row["total"]
    return {
        "total": total,
        "completed": row["completed"],
        "cancelled": row["cancelled"],
        "no_show": row["no_show"],
        "web": row["web"],
        "cancellation_rate": _rate(row["cancelled"], total),
        "no_show_rate": _rate(row["no_show"], total),
    }


def bookings_report(user, filters: Filters) -> dict:
    """Reservas por mes, por servicio y por profesional, con tasa de cancelación y de no-show.

    Cuenta las citas que empiezan en el rango, en cualquier estado salvo `rescheduled`.
    """
    start_at, end_at = commissions.local_range(filters.start, filters.end)
    appointments = booking.appointments_for_report(
        start_at=start_at,
        end_at=end_at,
        professional_id=_scoped_professional(user, filters),
        service_id=filters.service_id,
        category_id=filters.category_id,
    ).order_by()

    by_month = [
        {
            "key": row["month"].date().isoformat()[:7],
            "label": row["month"].date().isoformat()[:7],
            **_booking_metrics(row),
        }
        for row in appointments.annotate(month=TruncMonth("start_at"))
        .values("month")
        .annotate(**_STATUS_COUNTS)
        .order_by("month")
    ]
    by_professional = [
        {
            "key": str(row["professional_id"]),
            "label": row["professional__display_name"],
            **_booking_metrics(row),
        }
        for row in appointments.values("professional_id", "professional__display_name")
        .annotate(**_STATUS_COUNTS)
        .order_by("-total", "professional__display_name")
    ]
    # Por servicio se cuenta cada servicio de la cita: una cita de corte + barba suma en los dos.
    by_service = [
        {
            "key": str(row["items__service_id"]),
            "label": row["items__service__name"],
            **_booking_metrics(row),
        }
        for row in appointments.values("items__service_id", "items__service__name")
        .annotate(**_STATUS_COUNTS)
        .order_by("-total", "items__service__name")
    ]
    return {
        "from": filters.start,
        "to": filters.end,
        "totals": _booking_metrics(appointments.aggregate(**_STATUS_COUNTS)),
        "by_month": by_month,
        "by_professional": by_professional,
        "by_service": by_service,
    }
