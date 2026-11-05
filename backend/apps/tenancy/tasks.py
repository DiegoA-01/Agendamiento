"""Tareas de Celery con el negocio activo (M8, spec §4.5: "los workers fijan el tenant al inicio
de cada tarea").

Toda tarea de negocio usa `TenantTask` como base y recibe el id del negocio como PRIMER argumento:

    from celery import shared_task
    from apps.tenancy.tasks import TenantTask

    @shared_task(base=TenantTask, name="notifications.send_confirmation")
    def send_confirmation(tenant_id, appointment_id):
        appointment = Appointment.objects.get(pk=appointment_id)  # ya filtra por el negocio
        ...

    # desde un services.py, dentro de la transacción que crea la cita:
    tasks.delay_on_commit(send_confirmation, tenant, appointment.pk)

Dentro de la tarea el ORM y RLS ven solo ese negocio, igual que en una petición. Al terminar (bien,
con error o con reintento) el worker vuelve a quedar sin negocio, así la siguiente tarea del mismo
proceso no hereda el anterior. Si el negocio ya no existe o está suspendido, la tarea no corre.
"""

import logging
from typing import Any

from celery import Task, shared_task
from django.db import transaction

from . import services
from .context import tenant_context
from .models import Tenant

logger = logging.getLogger(__name__)


class TenantTask(Task):
    """Base de las tareas de negocio: activa el tenant del primer argumento durante la tarea."""

    abstract = True

    def __call__(self, tenant_id, *args: Any, **kwargs: Any) -> Any:
        tenant = services.get_tenant(tenant_id)
        if tenant is None or tenant.status != Tenant.Status.ACTIVE:
            # Negocio borrado o suspendido: no se le envía nada ni se tocan sus datos.
            logger.info(
                "Tarea omitida: negocio inactivo",
                extra={"task": self.name, "tenant_id": str(tenant_id)},
            )
            return None
        with tenant_context(tenant):
            return super().__call__(tenant_id, *args, **kwargs)


def delay_on_commit(task: Task, tenant, *args: Any, **kwargs: Any) -> None:
    """Encola la tarea cuando la transacción en curso se confirme (o ya, si no hay una).

    Así el worker nunca procesa una cita que al final no se guardó, ni la lee antes de que exista.
    """
    tenant_id = str(tenant.pk)
    transaction.on_commit(lambda: task.delay(tenant_id, *args, **kwargs))


def active_tenant_ids() -> list[str]:
    """Negocios activos (la tabla de negocios no tiene RLS: se lee sin contexto)."""
    return [
        str(pk)
        for pk in Tenant.objects.filter(
            status=Tenant.Status.ACTIVE, deleted_at__isnull=True
        ).values_list("pk", flat=True)
    ]


@shared_task(name="tenancy.for_each_active_tenant")
def for_each_active_tenant(task_name: str, *args: Any) -> int:
    """Encola `task_name` una vez por cada negocio activo. Pensada para Celery Beat:

        CELERY_BEAT_SCHEDULE = {
            "recordatorios": {
                "task": "tenancy.for_each_active_tenant",
                "schedule": 300,
                "args": ["notifications.send_reminders"],
            },
        }

    Cada negocio corre en su propia tarea, con su propio contexto: un error en uno no frena a
    los demás. Devuelve cuántas tareas encoló.
    """
    from config.celery import app

    task = app.tasks[task_name]
    if not isinstance(task, TenantTask):
        # Una tarea sin `TenantTask` recibiría el id del negocio sin activarlo (o se llamaría a
        # sí misma): se rechaza en vez de correr con datos de nadie.
        raise ValueError(f"'{task_name}' no usa TenantTask.")
    tenant_ids = active_tenant_ids()
    for tenant_id in tenant_ids:
        task.delay(tenant_id, *args)
    return len(tenant_ids)
