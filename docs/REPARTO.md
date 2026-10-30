# Reparto del trabajo (M4 a M10)

Plan para que dos personas, cada una con su Claude, avancen en paralelo sin pisarse. Estado de partida: M0 a M3 terminados en `develop`.

El camino crítico es **M4 → M5**: casi todo lo demás depende de citas y disponibilidad.

## Fase 0: contratos compartidos

La hace **una sola persona** (1 día como máximo), en un PR propio, antes de dividir el trabajo:

1. **Registrar todas las apps que faltan** (`catalog`, `scheduling`, `booking`, `commissions`, `notifications`, `reports`, `media`) en `INSTALLED_APPS` y en `config/urls.py`, con `urls.py` vacíos. Después de esto nadie vuelve a tocar esos dos archivos.
2. **Modelos y migraciones iniciales** de la sección 6 de la spec: `Location`, `ServiceCategory`, `Service`, `Specialty`, `Professional`, `ProfessionalService`, `Resource`, `WorkingHours`, `TimeBlock`, `Customer`, `Appointment` (con la restricción de exclusión) y `AppointmentItem`. Todos heredan de `TenantOwnedModel` y activan RLS.
3. **Dividir los archivos que más chocan**:
   - `es.json` / `en.json` en un archivo por funcionalidad (`locales/es/catalog.json`, etc.).
   - `tests/factories.py` en `tests/<app>/factories.py`.
4. **Esqueleto del dashboard en el frontend**: layout, menú y todas las rutas de la §13 con páginas vacías. Así `App.tsx` queda cerrado.

Mientras tanto, la otra persona avanza en la app `media` (conversión a WebP y variantes de tamaño), que está aislada.

## Dos frentes

| | **Frente A: motor de agenda** | **Frente B: producto y UI** |
|---|---|---|
| Responsable | Diego (sugerido) | Juan (sugerido) |
| Apps del backend que le pertenecen | `scheduling`, `booking`, `commissions`, `reports` | `company`, `catalog`, `media`, `notifications` |
| M4 | API de horarios y bloqueos (bloqueo que choca → 409 con las citas en conflicto) | API de company, locations, categorías, servicios, profesionales, puestos y asignación con overrides; imágenes en WebP; pantallas `/empresa`, `/servicios`, `/equipo`, `/puestos`, `/horarios` |
| M5 | Motor de disponibilidad (§8), citas, estados, prueba de 20 POST simultáneos | `seed_demo` (§16), que el frente A necesita para probar |
| M6 | Endpoints públicos de disponibilidad, creación y cancelación por token | Asistente `/reservar`, `/cita/:token`, páginas legales, banner de cookies |
| M7 | Endpoint SSE `events/` sobre Redis | Pantalla `/agenda` (día y semana) consumiendo el SSE, más `/citas` y `/clientes` |
| M8 | — | Notificaciones por email y WhatsApp con FakeProvider, Celery Beat, reintentos |
| M9 | Comisiones al completar, reportes y CSV | Pantalla `/reportes` |
| M10 | Rate limits, puntos Alta de `pormejorar.md` y Playwright, repartidos al final | |

### Dependencias entre frentes (contrato primero)

- **M6 y M7**: el frente B arranca con datos simulados según el OpenAPI que el frente A publica antes de implementar. Cuando el frente A hace merge, se cambia el mock por la API real.
- **Disponibilidad**: el frente A obtiene duraciones y profesionales llamando a `catalog/services.py`, sin importar modelos de `catalog`. El frente B expone esas funciones temprano.

## Reglas para no chocar

1. **Cada app tiene un dueño.** Solo el dueño crea migraciones en ella. Si necesitas un campo en una app ajena, se le pide al dueño.
2. **Una rama por tarea pequeña** desde `develop`: `feat/m4-catalog-api`, `feat/m5-availability`, etc. PRs cortos (1 o 2 días), revisión cruzada y rebase sobre `develop` cada mañana.
3. **Archivos compartidos** (`shared/ui/primitives.tsx`, `shared/api/types.ts`, `config/api.py`): solo se les agrega código, y en un PR propio y pequeño.
4. **`CHANGELOG.md` y `pormejorar.md`**: cada uno escribe solo en la sección de su hito.
5. **Cada sesión de Claude debe saber su frente.** Al iniciar, indícale "trabajo en el frente A" o "frente B". No debe tocar apps ni migraciones del otro frente sin pedirlo.
6. **Si trabajas en varias tareas a la vez**, usa un git worktree por rama para que tus sesiones de Claude no se pisen entre ellas.
