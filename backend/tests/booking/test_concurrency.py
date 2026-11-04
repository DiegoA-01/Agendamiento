"""Criterio de aceptación de M5 (spec §14): 20 POST simultáneos al mismo hueco crean 1 cita y
19 reciben 409.

Corre con transacciones reales (`transaction=True`) y un hilo por petición, cada uno con su propia
conexión a PostgreSQL: así las inserciones compiten de verdad y quien decide es la restricción de
exclusión, no el orden de ejecución de la prueba.
"""

import threading
from collections import Counter

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.booking.models import Appointment
from apps.tenancy.context import tenant_context

from .test_appointments_api import URL, Shop, at

REQUESTS = 20


@pytest.mark.django_db(transaction=True)
def test_twenty_simultaneous_bookings_of_the_same_slot_create_exactly_one():
    shop = Shop()
    ana = shop.professional()
    clients = [shop.client("receptionist")[0] for _ in range(REQUESTS)]
    payload = shop.payload(at(9), ana)
    barrier = threading.Barrier(REQUESTS)
    statuses: list[int] = []
    lock = threading.Lock()

    def post(client: APIClient) -> None:
        try:
            barrier.wait()
            response = client.post(URL, payload, format="json")
            with lock:
                statuses.append(response.status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=post, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert Counter(statuses) == {201: 1, 409: REQUESTS - 1}
    with tenant_context(shop.tenant):
        assert Appointment.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_with_any_professional_simultaneous_bookings_fill_each_professional_once():
    """Con "cualquiera" y 3 profesionales libres, 10 reservas simultáneas al mismo hueco dan 3
    citas (una por profesional) y 7 respuestas 409."""
    shop = Shop()
    for name in ("Ana", "Beto", "Carla"):
        shop.professional(name)
    clients = [shop.client("receptionist")[0] for _ in range(10)]
    payload = shop.payload(at(9))
    barrier = threading.Barrier(len(clients))
    statuses: list[int] = []
    lock = threading.Lock()

    def post(client: APIClient) -> None:
        try:
            barrier.wait()
            response = client.post(URL, payload, format="json")
            with lock:
                statuses.append(response.status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=post, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert Counter(statuses) == {201: 3, 409: 7}
    with tenant_context(shop.tenant):
        assert Appointment.objects.values("professional_id").distinct().count() == 3
