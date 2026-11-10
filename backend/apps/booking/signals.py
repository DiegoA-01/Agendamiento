"""Señal de cambios de cita (M8).

`booking` no conoce las notificaciones: solo avisa. `notifications` escucha y decide qué mensaje
mandar (confirmación, cancelación o reprogramación). Así ninguna de las dos apps importa los
modelos de la otra, igual que `accounts.signals` con la auditoría.

Argumentos: `kind` (`events.CREATED`, `UPDATED` o `CANCELLED`) y `appointment`. Se envía dentro
de la transacción que hizo el cambio: quien escuche debe encolar su trabajo con `on_commit`.
"""

from django.dispatch import Signal

appointment_changed = Signal()
