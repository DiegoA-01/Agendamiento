# Progreso del proyecto

Estado del SaaS de agendamiento y plan a seguir. Se actualiza al cerrar cada hito o cada PR importante.

**Corte:** 2026-11-11 · `develop` en `3150508` (PR #41) · `main` en M0 (`12343f6`, espera la revisión del encargado).

---

## 1. Resumen en 30 segundos

- **Hecho:** los hitos M0 a M9 completos, con backend y pantallas. De M10 está todo salvo Sentry y el servidor de producción. También están hechas casi todas las mejoras de Fase 1 que salieron de las pruebas manuales (§10).
- **Avance aproximado:** la API cubre los 37 grupos de la spec, y el proyecto completo va en ≈ 90–95 %.
- **Frente A:** no le queda trabajo de backlog. Solo quedan S2, si el encargado la aprueba, y lo que necesita aprobación (§5).
- **Frente B:** le quedan R9, S6 y S8.
- **Antes de entregar:**
  - Reactivar la verificación en dos pasos (2FA), que está **apagada en desarrollo** (`pormejorar.md` §33).
  - Decidir el servidor de producción y Sentry.
  - Pasar la revisión del encargado y hacer el PR de `develop` a `main`.
- **Pruebas sobre `develop`:**
  - Backend: **800**. Frontend: **126**.
  - Playwright: 1 prueba de punta a punta.
  - Todo en verde en el CI.

---

## 2. Equipo y forma de trabajo

| | Frente A — motor de agenda | Frente B — producto y UI |
|---|---|---|
| Responsable | Diego (`DiegoA-01`) | Yehiron |
| Apps | `scheduling`, `booking`, `commissions`, `reports`; en la práctica también `tenancy` y `accounts` | `company`, `catalog`, `media`, `notifications`, `platform_admin` y todas las pantallas |

- **Ramas:**
  - Se crea una rama por tarea desde `develop`.
  - Los PR van **hacia `develop`, nunca hacia `main`**.
  - Se mezcla solo con el CI en verde (backend, frontend y e2e).
- **Push:** el agente de Diego nunca hace push sin una confirmación explícita.
- **Apps del otro frente:**
  - Solo el dueño de una app crea migraciones en ella. Si un frente necesita una función en una app ajena, la agrega mínima y avisa en el PR.
  - Varias tareas de B las hizo el frente A con permiso: pantallas de M9, R5 y R7, la migración de `catalog` de R3 y los conflictos de los PR #37, #38 y #40.
- **Antes de empezar una tarea:** `git fetch`, revisar los PR abiertos y hacer `git pull` de la propia rama, que puede tener merges del otro frente.
- Reglas completas en [`docs/REPARTO.md`](docs/REPARTO.md).

---

## 3. Lo que está hecho

### Línea de tiempo

| Hito | Qué entrega | Quién | PRs |
|---|---|---|---|
| **M0** — Base | Repositorio, Docker Compose (api, worker, beat, web, postgres, redis, caddy), CI, settings, healthcheck, i18n | Diego | #1 |
| **M1** — Tenancy | Negocios, subdominios, middleware por host, RLS de PostgreSQL con rol sin superusuario, módulos por plan | Diego | — |
| **M2** — Cuentas | Roles, login por sesión + CSRF, recuperación de contraseña, 2FA (TOTP), `/me/`, matriz de permisos, Argon2id | Diego | — |
| **M3** — Super Admin | Empresas, planes, tema con contraste WCAG, módulos, dominios propios por DNS, suspensión, auditoría | Diego | — |
| **Fase 0** | Apps y modelos con RLS, anti doble reserva, esqueleto del panel; luego configuración de agenda, `/me/` con permisos, sede por defecto, rutas públicas y polling de Vite | Yehiron y Diego | #2, #3, #10–#14 |
| **M4** — Catálogo y equipo | Imágenes WebP; API de empresa, sedes, categorías, servicios, puestos, profesionales y servicios por profesional; horarios y bloqueos; pantallas `/empresa`, `/servicios`, `/puestos`, `/equipo`, `/horarios` | Yehiron y Diego | #4, #6, #15–#18, #20, #22 |
| **M5** — Motor y citas | Motor de disponibilidad con caché, citas con estados y reprogramación, `409 slot_taken`; `seed_demo`. **Aceptación:** 20 reservas simultáneas dan 1 cita y 19 rechazos | Diego y Yehiron | #19, #24 |
| **M6** — Reserva pública | API pública con límites por IP y celular, honeypot y captcha opcional; asistente `/reservar`, `/cita/:token`, páginas legales y aviso de cookies | Diego y Yehiron | #21, #25 |
| **M7** — Tiempo real y clientes | SSE `events/` sobre Redis, API de clientes; pantallas `/agenda`, `/citas` y `/clientes` | Diego y Yehiron | #23, #26, #27 |
| **M8** — Notificaciones | Base de tareas de Celery por negocio (`TenantTask`); `NotificationLog` idempotente, confirmación, cancelación, reprogramación y recordatorios a 24 h y 2 h, reintentos con paso a correo si falla WhatsApp, `FakeProvider` y `CloudApiProvider` | Diego (base) y Yehiron | #29, #37 |
| **M9** — Comisiones y reportes | `CommissionEntry` inmutable (también por trigger de PostgreSQL) que se crea al completar la cita; ajustes como filas nuevas (solo el propietario); reportes de ventas (por día, semana, mes, profesional o servicio) y de reservas; exportación CSV protegida contra fórmulas; pantalla `/reportes`. **Aceptación:** los valores cuadran con un negocio de prueba calculado a mano | Diego | #31, #33 |
| **M10** — Endurecimiento | Límite de fallos de login por IP y por correo y de recuperaciones de contraseña (Redis); auditoría de ingresos, fallos, cambios de contraseña y 2FA; logs JSON con `request_id` y negocio; scripts `backup.sh` y `restore.sh` cifrados con prueba de restauración (`docs/OPERACION.md`); **Playwright** reservar → completar → comisión, corriendo en el CI | Diego | #36, #39 |
| **Mejoras de Fase 1** (§10) | R1, R2, R3, R4, R5, R7, S1, S3, S4, S5, S10 y S11 | Diego y Yehiron | #32–#35, #38, #40, #41 |

### Qué hay en el código hoy

**Backend** — una app de Django por módulo:

| App | Qué tiene |
|---|---|
| `tenancy` | Negocios, dominios, planes, módulos, RLS, contexto del negocio activo, configuración de agenda y tareas de Celery por negocio |
| `accounts` | Usuarios (con tipo y número de documento), roles, sesión, 2FA, recuperación, matriz de permisos, `/me/`, límite de intentos y la señal `security_event` |
| `platform_admin` | API del Super Admin, auditoría (incluye los eventos de seguridad), uso por negocio (S10), integraciones por negocio (S11) y `seed_demo` |
| `company` | Empresa (con NIT), sedes y textos legales limpios de HTML peligroso |
| `catalog` | Categorías (con "uno por cita", R3), servicios, especialidades, profesionales, servicios por profesional y puestos |
| `scheduling` | Horarios, bloqueos, configuración de agenda, motor de disponibilidad y calendario por estado del día (R7) |
| `booking` | Citas, estados, clientes (sin citas cruzadas, R3), reserva pública, eventos SSE y datos para reportes y notificaciones |
| `commissions` | Comisiones inmutables y ajustes |
| `reports` | Reportes de ventas y reservas, con CSV |
| `notifications` | Correo y WhatsApp, plantillas por idioma y vertical, recordatorios y `NotificationLog` |
| `media` | Imágenes en WebP |

**Frontend** (React):
- **Login:** con 2FA, cambio forzado de contraseña y recuperación.
- **Panel del Super Admin:**
  - Empresas con alta simplificada (S3 y S4) y datos del propietario (S5).
  - Detalle con datos, tema, módulos, dominios, uso (S10) e integraciones (S11).
  - Planes y auditoría.
- **Panel del negocio:** agenda en tiempo real, citas, clientes, servicios, equipo, puestos, horarios, empresa y `/reportes`.
- **Sitio público del negocio:**
  - Portada.
  - Asistente de reserva con fotos de servicios y barberos, detalle del servicio, especialidades, calendario de colores y regla de "elige uno".
  - Gestión de la cita por enlace, páginas legales y aviso de cookies.
- **Idiomas:** textos en español e inglés.

**Calidad:**
- **Pruebas:** **800** en el backend, **126** en el frontend y la prueba de Playwright, en verde sobre `develop`. Ruff, mypy, ESLint, tipos, build y OpenAPI sin avisos.
- **El CI tiene tres trabajos:**
  - `backend`.
  - `frontend`.
  - `e2e`: levanta todo con Docker Compose y corre Playwright, con Chromium en caché y reintentos si falla la descarga.
- **Para probar a mano:** `docker compose exec api python manage.py seed_demo --vertical barbershop` crea un negocio demo completo. El Super Admin entra por `admin.localhost`, no por el dominio del negocio.

---

## 4. Decisiones tomadas

Para no volver a discutirlas. Las que dicen "provisional" se revisan antes de entregar.

| Tema | Decisión | Dónde está documentado |
|---|---|---|
| Autenticación | Sesión por cookie HttpOnly + CSRF, no JWT | `docs/adr/0001-autenticacion-por-sesion.md` |
| Contraseñas | Argon2id con el perfil mínimo de OWASP. Dependencia `argon2-cffi` aprobada | `pormejorar.md` §7 |
| 2FA | Obligatorio para el Super Admin y opcional para el propietario. **Provisional: apagado en desarrollo** (`REQUIRE_TWO_FACTOR=0`) | `pormejorar.md` §5 y §33 |
| Aislamiento | Base compartida + `tenant_id` + RLS forzado, con la app conectada por un rol sin superusuario | `CHANGELOG.md` (M1) |
| Doble reserva | La garantía final es la restricción de exclusión de PostgreSQL; la API revalida antes y responde `409 slot_taken` con sugerencias | `CHANGELOG.md` (M5) |
| Cliente en dos citas | Un mismo cliente no puede tener dos citas activas que se crucen (`409 customer_overlap`); otra persona sí puede tomar esa hora con otro profesional | `CHANGELOG.md` (R3) |
| Servicios por categoría | Cada categoría puede marcarse "uno por cita" (`400 one_per_category`); por defecto no tiene la regla | `CHANGELOG.md` (R3) |
| "Cualquiera" | Se asigna el profesional libre con menos citas ese día; empate por orden alfabético. El cliente no ve quién atiende | `CHANGELOG.md` (M5 y M6) |
| Reserva pública | 10 POST por hora por IP y 5 por celular; IP real detrás de Caddy (`TRUSTED_PROXY_COUNT`); honeypot; captcha opcional | `CHANGELOG.md` (M6) |
| Tiempo real | SSE sobre Redis pub/sub, publicado después del commit; el profesional solo recibe sus citas | `CHANGELOG.md` (M7) |
| Tareas de Celery | Toda tarea de negocio usa `TenantTask` y recibe el id del negocio como primer argumento | `apps/tenancy/tasks.py` |
| Notificaciones | WhatsApp si el plan lo incluye y hay consentimiento; si no, correo. `booking` avisa por señal, sin importar `notifications` | `CHANGELOG.md` (M8) |
| Comisiones | Inmutables: nunca se editan ni se borran; las correcciones son ajustes que guardan la diferencia. Redondeo `ROUND_HALF_UP` | `CHANGELOG.md` (M9) |
| Límite de intentos | 20 fallos por IP y 10 por correo en 15 minutos; 3 recuperaciones por correo | `CHANGELOG.md` (M10) |
| Copias de seguridad | `pg_dump` cifrado con AES-256 y suma sha256; la restauración se prueba en una base aparte | `docs/OPERACION.md` |
| Dependencias | Playwright aprobado (solo desarrollo y CI). Sentry, servidor de producción y `cryptography` siguen sin aprobar | §5 |
| Flujo de Git | Rama por tarea, PR a `develop`, nunca a `main`; `main` solo con revisión del encargado | `docs/REPARTO.md` |

---

## 5. Pendientes y acuerdos

### Por decidir entre los dos o con el encargado
- **Las mejoras marcadas "Cambia la spec" o "Fuera de alcance"** en la §10 (R6, R10, S2, S7, S9 y el wallet de S11) necesitan la aprobación del encargado.
- **Qué pasa al bajar de plan** con los profesionales o sedes que sobran.
- **Precio por profesional en la reserva pública:** hoy el asistente muestra un precio de referencia.

### Aprobaciones de dependencias

| Paquete | Para qué | Estado |
|---|---|---|
| Playwright | Prueba de punta a punta | **Aprobado** y en uso |
| Servidor de producción (`gunicorn`, `uvicorn` o `daphne`) | Producción y SSE: cada agenda abierta ocupa una conexión | Pendiente; decidir antes de desplegar |
| Sentry | Errores en producción (S12) | Pendiente; tiene sentido cuando haya servidor de producción |
| `cryptography` | Cifrar el secreto del 2FA y las credenciales de WhatsApp por negocio | Pendiente |

---

## 6. Plan a seguir

Cada hito se da por terminado con su criterio de aceptación de la spec (§14), no con una fecha.

| Paso | Frente A (Diego) | Frente B (Yehiron) | Estado |
|---|---|---|---|
| **M0 a M9** | — | — | ✓ |
| **M10** | ~~Límites, auditoría de ingresos, logs, copias~~ (#36), ~~Playwright~~ (#39). Falta: servidor de producción y cifrado del secreto 2FA (necesitan aprobación) | Sentry (necesita aprobación), revisión de accesibilidad | Casi listo |
| **Mejoras de Fase 1** | ~~R3, R5, R7, S5, S10~~. S2 solo si se aprueba | ~~R1, R2, R4, S1, S3, S4, S11~~. **Faltan R9, S6 y S8** | En curso (B) |
| **Prueba manual completa** | Recorrer el negocio demo y el Super Admin; confirmar R8 | Lo mismo en celular (375 px) | Pendiente |
| **Cierre** | **Reactivar el 2FA**, resolver los puntos Alta de `pormejorar.md`, revisión del encargado y PR de `develop` a `main` | | Pendiente |

**Orden sugerido:**
1. Yehiron cierra R9, S6 y S8.
2. Llevar al encargado las decisiones de §5 y las mejoras que cambian la spec.
3. Hacer la prueba manual completa.
4. Reactivar el 2FA y correr todas las pruebas con él encendido.
5. Revisar los puntos Alta de `pormejorar.md`: servidor de producción, imágenes en producción, cifrado del 2FA y WhatsApp real.
6. Abrir el PR de `develop` a `main` para la revisión del encargado.

---

## 7. Riesgos y alertas

1. **PRs que se van a `main`.** El #5 y el #28 se mezclaron en `main` por error.
   - Revisar en GitHub que la rama por defecto sea `develop`: Settings → General → Default branch.
   - Al abrir un PR, confirmar siempre que la base sea `develop`.
2. **2FA apagado en desarrollo.** Reactivarlo es obligatorio antes de entregar (`pormejorar.md` §33).
3. **Claves foráneas entre negocios.** RLS impide *ver* datos de otro negocio pero no *enlazarlos*. Cada `services.py` busca los ids recibidos dentro del negocio activo antes de usarlos.
4. **Servidor de desarrollo.** `runserver` no sirve para producción, y cada conexión SSE ocupa un hilo (`pormejorar.md` §4).
5. **Pruebas que dependen de la hora.** Una prueba de R7 fallaba de noche en Bogotá porque usaba la fecha en UTC (ya corregida). Toda prueba con "hoy" o "ayer" debe usar la fecha local del negocio.
6. **CI de punta a punta.**
   - La descarga de Chromium a veces falla por la red del runner. Ya hay caché y reintentos.
   - Si falla igual, reintentar el trabajo `e2e` antes de buscar un error en el código.
   - Si un cambio de pantalla rompe la prueba, revisar los selectores de `frontend/e2e/`.
7. **Docker Desktop en Windows** se apaga con frecuencia. Si aparece el error de `dockerInference`: Quit, volver a abrir y, si sigue, `wsl --shutdown`.
8. **Imágenes en producción.** Falta definir cómo se sirven los archivos subidos (`pormejorar.md` §34).
9. **WhatsApp real.** Necesita plantillas aprobadas por Meta y credenciales cifradas por negocio (`pormejorar.md` §36 y §37). Hasta entonces se usa `FakeProvider`.

---

## 8. Documentos de referencia

| Documento | Para qué |
|---|---|
| [`docs/SPEC-FASE-1-MVP.md`](docs/SPEC-FASE-1-MVP.md) | Qué se construye (la fuente de verdad) |
| [`docs/REPARTO.md`](docs/REPARTO.md) | Quién hace qué y reglas para no chocar |
| [`docs/OPERACION.md`](docs/OPERACION.md) | Copias de seguridad, restauración y logs |
| [`CHANGELOG.md`](CHANGELOG.md) | Qué entró en cada hito, con detalle |
| [`pormejorar.md`](pormejorar.md) | Mejoras y riesgos pendientes, con prioridad |
| [`README.md`](README.md) | Cómo levantar el proyecto y crear el primer Super Admin |
| [`docs/adr/`](docs/adr/) | Decisiones de arquitectura |
| [`CLAUDE.md`](CLAUDE.md) | Reglas para el agente |

## 9. Cómo mantener este archivo

- Actualízalo al cerrar cada hito o cada PR que cambie el estado del proyecto.
- Cada frente escribe solo en sus filas y en sus pendientes.
- Cambia la fecha de **Corte** y el commit de `develop` arriba.

---

## 10. Mejoras propuestas tras las pruebas manuales (2026-11-05)

Salieron de probar el negocio demo y el panel del Super Admin.

**Alcance:**
- **Fase 1**: cabe en la spec y se puede hacer antes del cierre.
- **Cambia la spec**: no está prohibida, pero contradice una decisión de la spec. Necesita aprobación del encargado.
- **Fuera de alcance**: la spec la excluye (§1 o §12). Va a una fase siguiente salvo que el encargado la apruebe.

### Reserva pública (`/reservar`)

| # | Mejora | Quién | Alcance | Estado |
|---|---|---|---|---|
| R1 | Foto en cada servicio | B | Fase 1 | ✓ |
| R2 | Ventana de detalle por servicio (foto, descripción, duración, precio) | B | Fase 1 | ✓ #38 |
| R3 | Un solo servicio por categoría marcada (un corte por cita, pero corte + barba o cejas sí) y un cliente sin citas cruzadas | A y B | Fase 1 | ✓ #41 |
| R4 | Foto de presentación de cada barbero | B | Fase 1 | ✓ |
| R5 | Especialidad de cada barbero en la reserva | A y B | Fase 1 | ✓ #32, #33 |
| R6 | Calificación por barbero | — | **Fuera de alcance** (§12: reseñas) | Para el encargado |
| R7 | Calendario con colores: disponible, lleno, cerrado | A y B | Fase 1 | ✓ #32, #33 |
| R8 | Solo horas libres, sin mostrar quién reservó | — | Ya funcionaba desde M5 | Confirmar en la prueba manual |
| R9 | Todo el flujo en un solo modal, con menos pasos | B | Fase 1 (decisión de UX) | **Pendiente** |
| R10 | Agregar la cita al wallet del celular | — | **Fuera de alcance**. Alternativa: botón "Agregar al calendario" con `.ics` | Para el encargado |

### Super Admin

| # | Mejora | Quién | Alcance | Estado |
|---|---|---|---|---|
| S1 | Selector de idioma solo en el sitio de cada negocio | B | Fase 1 | ✓ #38 |
| S2 | Tipo de negocio con selección múltiple | A y B | **Cambia la spec** (§1: "un campo `vertical`") | Para el encargado |
| S3 | Quitar zona horaria y moneda del alta | B | Fase 1 | ✓ #38 |
| S4 | Quitar el idioma del alta | B | Fase 1 | ✓ #38 |
| S5 | Datos del propietario: documento, NIT y teléfono (la contraseña sigue siendo temporal, por seguridad) | A y B | Fase 1 | ✓ #34 |
| S6 | Resumen de la plataforma: total de negocios, activos, suspendidos, nuevos | B | Fase 1 | **Pendiente** |
| S7 | Soporte con tickets | — | **Nuevo módulo, no está en la spec** | Fase siguiente |
| S8 | Términos y condiciones de la plataforma | B | Fase 1 (texto estático) | **Pendiente** |
| S9 | Pagos de la suscripción | — | **Fuera de alcance** (§1 y §12) | Fase siguiente |
| S10 | Uso del sistema por negocio | A y B | Fase 1 | ✓ #35 |
| S11 | Integraciones por negocio (WhatsApp y correo) | B | Fase 1; wallet fuera de alcance | ✓ #40 |
| S12 | Monitoreo: errores, copias y auditoría | A y B | Fase 1 (M10) | Copias y auditoría ✓ #36; Sentry pendiente de aprobación |
