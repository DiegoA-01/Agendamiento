# Reparto del trabajo (M4 a M10)

Plan para que dos personas, cada una con su Claude, avancen en paralelo sin pisarse. Estado de partida: M0 a M3 terminados en `develop`.

El camino crítico es **M4 → M5**: casi todo lo demás depende de citas y disponibilidad.

## Estado actual (2026-10-30)

| Pieza | Responsable | Estado |
|---|---|---|
| Fase 0 backend (apps, modelos, migraciones, RLS, fábricas) | Yehiron | **En `develop`** (PR #2) |
| Fase 0 frontend (textos por área, esqueleto del dashboard) | Yehiron | **En `develop`** (PR #3) |
| App `media` (WebP) | Yehiron | **En `develop`** (PR #4) |
| Frente A, M4 (horarios y bloqueos) | Diego | Por empezar |

Pruebas sobre `develop` (`269e801`): 424 en el backend y 51 en el frontend, todas en verde.

**Pendiente que dejó la Fase 0** (ver la sección "Lo que falta de la Fase 0").

## Fase 0: contratos compartidos

La hace **una sola persona** (1 día como máximo), en un PR propio, antes de dividir el trabajo. **La hizo Yehiron.**

1. **Registrar todas las apps que faltan** (`catalog`, `scheduling`, `booking`, `commissions`, `notifications`, `reports`, `media`) en `INSTALLED_APPS` y en `config/urls.py`, con `urls.py` vacíos. Después de esto nadie vuelve a tocar esos dos archivos.
2. **Modelos y migraciones iniciales** de la sección 6 de la spec: `Location`, `ServiceCategory`, `Service`, `Specialty`, `Professional`, `ProfessionalService`, `Resource`, `WorkingHours`, `TimeBlock`, `Customer`, `Appointment` (con la restricción de exclusión) y `AppointmentItem`. Todos heredan de `TenantOwnedModel` y activan RLS.
3. **Dividir los archivos que más chocan**:
   - `es.json` / `en.json` en un archivo por funcionalidad (`locales/es/catalog.json`, etc.).
   - `tests/factories.py` en `tests/<app>/factories.py`.
4. **Esqueleto del dashboard en el frontend**: layout, menú y todas las rutas de la §13 con páginas vacías. Así `App.tsx` queda cerrado.

Mientras tanto, la otra persona avanza en la app `media` (conversión a WebP y variantes de tamaño), que está aislada.

### Lo que falta de la Fase 0

Detectado al revisar lo que entró en `develop`. Cada punto tiene un dueño propuesto; se confirma entre los dos.

| # | Qué falta | Por qué importa | Dueño propuesto | Bloquea |
|---|---|---|---|---|
| 1 | **Configuración de agenda en `Tenant`**: `slot_step_min` (15), `min_notice_min` (60), `max_advance_days` (60), `cancel_min_hours` (2), con sus rangos | La lee el motor de disponibilidad (§8) y la reserva pública (§9) | A (en `tenancy`) | M5 |
| 2 | **Sede por defecto al crear un negocio**: `Professional` y `Resource` exigen una `Location`, pero el alta de empresa (M3) no crea ninguna | Sin ella, en un negocio nuevo no se puede crear ningún profesional ni puesto | B (`company` o el alta en `platform_admin`) | **M4** |
| 3 | **Rutas públicas** de la §13: `/reservar`, `/cita/:token`, `/terminos`, `/privacidad`, `/cookies` | Sin ellas `App.tsx` no queda cerrado y habrá que volver a editarlo | B | M6 |
| 4 | **`/me/` con los permisos del rol**, calculados desde la matriz del backend | Hoy el menú del frontend copia los roles: si cambia la matriz, las dos copias se desincronizan | A (en `accounts`) | — |
| 5 | **Polling de Vite** (`server.watch.usePolling` con `VITE_USE_POLLING=1` en `docker-compose.yml`) | En Docker sobre Windows el navegador muestra código viejo hasta recrear el contenedor `web` | Cualquiera, en un PR propio | — |

Hay una versión de referencia de los puntos 1, 2, 4 y 5 en la rama **local** `feat/f0-contratos` del frente A. No se sube; sirve para copiar lo que haga falta en PRs pequeños.

## Dos frentes

| | **Frente A: motor de agenda** | **Frente B: producto y UI** |
|---|---|---|
| Responsable | Diego (`DiegoA-01`) | Yehiron |
| Apps del backend que le pertenecen | `scheduling`, `booking`, `commissions`, `reports` | `company`, `catalog`, `media`, `notifications` |
| M4 | API de horarios y bloqueos (bloqueo que choca → 409 con las citas en conflicto) | API de company, locations, categorías, servicios, profesionales, puestos y asignación con overrides; imágenes en WebP; pantallas `/empresa`, `/servicios`, `/equipo`, `/puestos`, `/horarios` |
| M5 | Motor de disponibilidad (§8), citas, estados, prueba de 20 POST simultáneos | `seed_demo` (§16), que el frente A necesita para probar |
| M6 | Endpoints públicos de disponibilidad, creación y cancelación por token | Asistente `/reservar`, `/cita/:token`, páginas legales, banner de cookies |
| M7 | Endpoint SSE `events/` sobre Redis | Pantalla `/agenda` (día y semana) consumiendo el SSE, más `/citas` y `/clientes` |
| M8 | — | Notificaciones por email y WhatsApp con FakeProvider, Celery Beat, reintentos |
| M9 | Comisiones al completar, reportes y CSV | Pantalla `/reportes` |
| M10 | Rate limits, puntos Alta de `pormejorar.md` y Playwright, repartidos al final | |

### Apps sin dueño todavía

`tenancy`, `accounts` y `platform_admin` (M0 a M3) no aparecen en la tabla, y la regla 1 exige un dueño por app. **Propuesta:** `tenancy` y `accounts` → frente A (aislamiento, sesiones y seguridad); `platform_admin` → frente B (es sobre todo pantallas). Mientras no se acuerde, cualquier cambio en ellas se avisa al otro antes de hacerlo.

### Dependencias entre frentes (contrato primero)

- **M6 y M7**: el frente B arranca con datos simulados según el OpenAPI que el frente A publica antes de implementar. Cuando el frente A hace merge, se cambia el mock por la API real.
- **Disponibilidad**: el frente A obtiene duraciones y profesionales llamando a `catalog/services.py`, sin importar modelos de `catalog`. El frente B expone esas funciones temprano.
- **Horarios (M4)**: la pantalla `/horarios` (B) consume la API de horarios y bloqueos (A). El frente A publica primero el OpenAPI de esos endpoints.
- **Módulos del plan en la API**: el menú oculta lo que el plan no incluye, pero la protección real es la API. Todo endpoint nuevo lleva `@requires_module(...)` según su módulo (`booking`, `commissions`, `reports`, `notifications_whatsapp`).
- **Claves foráneas entre negocios**: RLS impide ver datos de otro negocio, pero no enlazarlos. Todo `services.py` que reciba ids los busca dentro del tenant activo antes de usarlos (404 si no aparecen).

## Reglas para no chocar

1. **Cada app tiene un dueño.** Solo el dueño crea migraciones en ella. Si necesitas un campo en una app ajena, se le pide al dueño.
2. **Una rama por tarea pequeña** desde `develop`: `feat/m4-catalog-api`, `feat/m5-availability`, etc. PRs cortos (1 o 2 días), revisión cruzada y rebase sobre `develop` cada mañana.
3. **Archivos compartidos** (`shared/ui/primitives.tsx`, `shared/api/types.ts`, `config/api.py`): solo se les agrega código, y en un PR propio y pequeño.
4. **`CHANGELOG.md` y `pormejorar.md`**: cada uno escribe solo en la sección de su hito.
5. **Cada sesión de Claude debe saber su frente.** Al iniciar, indícale "trabajo en el frente A" o "frente B". No debe tocar apps ni migraciones del otro frente sin pedirlo.
6. **Si trabajas en varias tareas a la vez**, usa un git worktree por rama para que tus sesiones de Claude no se pisen entre ellas.
7. **Los pull requests van a `develop`, nunca a `main`.** `main` solo recibe lo que el encargado haya revisado. El CI corre en cada PR.
8. **Antes de empezar una tarea, `git fetch` y revisa las ramas y PRs abiertos.** Así nadie repite trabajo que el otro ya subió. (La Fase 0 llegó a hacerse dos veces por no revisarlo.)
9. **Un PR apunta a `develop`, no a la rama de otro PR.** Si depende de un PR abierto, se espera su merge o se avisa en la descripción y se cambia el destino a `develop` antes de mezclar.
10. **Después de hacer pull de cambios con migraciones o dependencias**, recrea los contenedores: `docker compose up -d --force-recreate api web worker beat`.
