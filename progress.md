# Progreso del proyecto

Estado del SaaS de agendamiento y plan a seguir. Se actualiza al cerrar cada hito o cada PR importante.

**Corte:** 2026-11-06 · `develop` en `b9f0646` · `main` en M0 (`12343f6`, espera la revisión del encargado).

---

## 1. Resumen en 30 segundos

- **Hecho:** M0 a M7 completos, backend y pantallas: base, multi-negocio, cuentas, Super Admin, Fase 0, catálogo y equipo, motor de disponibilidad y citas, reserva pública, agenda en tiempo real y clientes. De M8 está la base de tareas de Celery.
- **Avance aproximado:** API 35 de 37 grupos de la spec (≈ 95 %); proyecto completo ≈ 75–80 %.
- **Falta:** notificaciones (M8, frente B), comisiones y reportes (M9), endurecimiento y e2e (M10), y el cierre.
- **Siguiente para el frente A:** M9 (comisiones al completar una cita, reportes y CSV).
- **Siguiente para el frente B:** M8 (correo y WhatsApp con `FakeProvider`, recordatorios y `NotificationLog`).
- **Recordatorio obligatorio:** la verificación en dos pasos (2FA) está **apagada en desarrollo** y hay que reactivarla antes de entregar (`pormejorar.md` §33).
- **Urgente:** la rama por defecto de GitHub sigue siendo `main` y ya mandó dos PRs a `main` por error (§7, riesgo 1).

---

## 2. Equipo y forma de trabajo

| | Frente A — motor de agenda | Frente B — producto y UI |
|---|---|---|
| Responsable | Diego (`DiegoA-01`) | Yehiron |
| Apps | `scheduling`, `booking`, `commissions`, `reports`; en la práctica también `tenancy` y `accounts` | `company`, `catalog`, `media`, `notifications`, `platform_admin` y todas las pantallas |

- Una rama por tarea desde `develop`, y **PR hacia `develop`, nunca hacia `main`**. El CI corre en cada PR y se mezcla con el CI en verde.
- Solo el dueño de una app crea migraciones en ella. Si un frente necesita una función en una app ajena, la agrega mínima (solo lectura) y avisa en el PR.
- Antes de empezar una tarea: `git fetch` y revisar los PR abiertos, para no repetir trabajo.
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
| **M4** — Catálogo y equipo | Imágenes WebP; API de empresa, sedes, categorías, servicios, puestos, profesionales y servicios por profesional (B4.1); horarios y bloqueos; pantallas `/empresa`, `/servicios`, `/puestos`, `/equipo`, `/horarios` | Yehiron y Diego | #4, #6, #15–#18, #20, #22 |
| **M5** — Motor y citas | Motor de disponibilidad con caché, citas con estados y reprogramación, `409 slot_taken`; `seed_demo`. **Aceptación:** 20 reservas simultáneas dan 1 cita y 19 rechazos | Diego y Yehiron | #19, #24 |
| **M6** — Reserva pública | API pública con límites por IP y celular, honeypot y captcha opcional; asistente `/reservar`, `/cita/:token`, páginas legales y aviso de cookies | Diego y Yehiron | #21, #25 |
| **M7** — Tiempo real y clientes | SSE `events/` sobre Redis (con el arreglo del 406 en el navegador), API de clientes; pantallas `/agenda`, `/citas` y `/clientes` | Diego y Yehiron | #23, #26, #27 |
| **M8** (parcial) — Base de tareas | `TenantTask`, `delay_on_commit` y `for_each_active_tenant` para Celery Beat | Diego | #29 |

### Qué hay en el código hoy

**Backend** — una app de Django por módulo:

| App | Qué tiene |
|---|---|
| `tenancy` | Negocios, dominios, planes, módulos, RLS, contexto del negocio activo, configuración de agenda y tareas de Celery por negocio |
| `accounts` | Usuarios, roles, sesión, 2FA, recuperación de contraseña, matriz de permisos y `/me/` con permisos |
| `platform_admin` | API del Super Admin, auditoría y `seed_demo` |
| `company` | Empresa, sedes (con sede por defecto) y textos legales limpios de HTML peligroso |
| `catalog` | Categorías, servicios, especialidades, profesionales, servicios por profesional, puestos y funciones para el motor |
| `scheduling` | Horarios, bloqueos, configuración de agenda y el motor de disponibilidad |
| `booking` | Citas, estados, clientes, reserva pública y eventos en tiempo real (SSE) |
| `media` | Imágenes en WebP |
| `commissions`, `notifications`, `reports` | Registradas, sin lógica todavía (M8 y M9) |

**Frontend** (React):
- Login con 2FA, cambio forzado de contraseña y recuperación.
- Panel del Super Admin: empresas, detalle (datos, tema, módulos, dominios), planes y auditoría.
- Panel del negocio con menú según los permisos de `/me/`: agenda (día y semana, en tiempo real), citas con acciones según estado, clientes, servicios, equipo, puestos, horarios y empresa. Falta `/reportes` (M9).
- Sitio público del negocio: portada, asistente de reserva de 5 pasos, gestión de la cita por enlace, páginas legales y aviso de cookies.
- Textos en español e inglés.

**Calidad:**
- Pruebas: **672** en el backend y **107** en el frontend, en verde sobre `develop`. Ruff, mypy, ESLint, tipos y build limpios.
- Pruebas destacadas: aislamiento entre negocios (ORM y RLS), concurrencia de reservas, SSE, límites de la reserva pública y tareas de Celery por negocio.
- El CI valida además la documentación OpenAPI sin avisos.
- Para probar a mano: `docker compose exec api python manage.py seed_demo --vertical barbershop` crea un negocio demo completo.

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
| Caché de disponibilidad | Redis por negocio, profesional y fecha, con una versión por negocio que sube en cada cambio de agenda | `CHANGELOG.md` (M5) |
| "Cualquiera" | Se asigna el profesional libre con menos citas ese día; empate por orden alfabético. El cliente no ve quién atiende | `CHANGELOG.md` (M5 y M6) |
| Reserva pública | 10 POST por hora por IP y 5 por celular; IP real detrás de Caddy (`TRUSTED_PROXY_COUNT`); honeypot; captcha opcional sin dependencias nuevas | `CHANGELOG.md` (M6) |
| Tiempo real | SSE sobre Redis pub/sub, publicado después del commit; el profesional solo recibe sus citas | `CHANGELOG.md` (M7) |
| Tareas de Celery | Toda tarea de negocio usa `TenantTask` y recibe el id del negocio como primer argumento | `apps/tenancy/tasks.py` |
| Flujo de Git | Rama por tarea, PR a `develop`, nunca a `main`; `main` solo con revisión del encargado | `docs/REPARTO.md` |

---

## 5. Pendientes y acuerdos

### Por decidir entre los dos o con el encargado
- **Las mejoras de la §10** marcadas "Cambia la spec" o "Fuera de alcance" necesitan la aprobación del encargado.
- **Qué pasa al bajar de plan** con los profesionales o sedes que sobran.
- **Si las comisiones tienen pantalla propia** o se ven dentro de `/reportes` (M9).
- **Precio por profesional en la reserva pública:** hoy el asistente muestra un precio de referencia porque la API pública no da el precio propio de cada profesional.

### Aprobaciones de dependencias

| Paquete | Para qué | Decidir antes de |
|---|---|---|
| Servidor de producción (`gunicorn`, `uvicorn` o `daphne`) | Producción y SSE: cada agenda abierta ocupa una conexión | M10 |
| Librería de cifrado (`cryptography`) | Credenciales de WhatsApp y secreto 2FA | M8 |
| Playwright | Pruebas de extremo a extremo (las exige la spec) | M10 |

---

## 6. Plan a seguir

Cada hito se da por terminado con su criterio de aceptación de la spec (§14), no con una fecha.

| Hito | Frente A (Diego) | Frente B (Yehiron) | Criterio de aceptación | Estado |
|---|---|---|---|---|
| **M0 a M7** | — | — | Cumplidos | ✓ |
| **M8** | ~~Base de tareas de Celery~~ (PR #29) | Correo y WhatsApp (`FakeProvider`), recordatorios a 24 h y 2 h con Celery Beat, reintentos, `NotificationLog`, credenciales cifradas | Confirmación y recordatorio registrados en `NotificationLog`; reintentos probados | En curso (B) |
| **M9** | Comisiones al completar una cita (inmutables; las correcciones son entradas de ajuste), reportes de ventas y de reservas, CSV | Pantalla `/reportes` | Los valores cuadran con casos calculados a mano | Siguiente (A) |
| **M10** | Límites de intentos de login, auditoría de ingresos, cifrado del secreto 2FA, copias de seguridad, servidor de producción | Playwright, accesibilidad, logs y Sentry | Playwright cubre reservar → completar → comisión | Pendiente |
| **Cierre** | **Reactivar el 2FA**, resolver los puntos Alta de `pormejorar.md`, revisión del encargado y PR de `develop` a `main` | | Sin puntos Alta abiertos | Pendiente |

Las mejoras de Fase 1 de la §10 se hacen junto con M9 (frente A) y M8 (frente B).

---

## 7. Riesgos y alertas

1. **PRs que se van a `main`.** La rama por defecto de GitHub sigue siendo `main`: el PR #5 y el #28 se mezclaron ahí por error y `main` se devolvió a M0 las dos veces. **Cambiar ya** en GitHub: Settings → General → Default branch → `develop`. El PC de Diego tiene además un hook `pre-push` que rechaza los push a `main`.
2. **2FA apagado en desarrollo.** Reactivarlo es obligatorio antes de entregar (`pormejorar.md` §33).
3. **Claves foráneas entre negocios.** RLS impide *ver* datos de otro negocio pero no *enlazarlos*. Cada `services.py` busca los ids recibidos dentro del negocio activo antes de usarlos.
4. **Servidor de desarrollo.** `runserver` no sirve para producción y cada conexión SSE ocupa un hilo (`pormejorar.md` §4).
5. **Una prueba intermitente.** Tras recrear los contenedores, una corrida dio 1 fallo en 672 que no se pudo reproducir. Si vuelve, identificarla.
6. **Docker Desktop en Windows** se apaga con frecuencia. Si aparece el error de `dockerInference`: Quit, volver a abrir y, si sigue, `wsl --shutdown`.
7. **Imágenes en producción.** Falta definir cómo se sirven los archivos subidos (`pormejorar.md` §34).
8. **Copias de seguridad.** No existen todavía; deben estar antes de tener un negocio piloto (`pormejorar.md` §23).

---

## 8. Documentos de referencia

| Documento | Para qué |
|---|---|
| [`docs/SPEC-FASE-1-MVP.md`](docs/SPEC-FASE-1-MVP.md) | Qué se construye (la fuente de verdad) |
| [`docs/REPARTO.md`](docs/REPARTO.md) | Quién hace qué y reglas para no chocar |
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

Salieron de probar el negocio demo y el panel del Super Admin. Cada una indica qué existe ya, quién la haría y si cabe en el alcance de la Fase 1.

**Alcance:**
- **Fase 1**: cabe en la spec y se puede hacer antes del cierre.
- **Cambia la spec**: no está prohibida, pero contradice una decisión de la spec. Necesita aprobación del encargado.
- **Fuera de alcance**: la spec la excluye (§1 o §12). Va a una fase siguiente salvo que el encargado la apruebe.

### Reserva pública (`/reservar`)

| # | Mejora | Qué existe hoy | Quién | Alcance |
|---|---|---|---|---|
| R1 | Foto en cada servicio | La API ya guarda y expone la imagen del servicio (M4, `image_id`); el panel ya la sube | B (mostrarla en la reserva) | Fase 1 |
| R2 | Modal de detalle por servicio (foto, descripción, duración, precio) | La API pública ya trae esos datos | B | Fase 1 |
| R3 | Combinar servicios con reglas: un solo corte por cita, pero corte + barba o cejas sí | Hoy se pueden elegir varios servicios sin reglas (máximo 10) | A (regla en la API: por ejemplo "máximo uno por categoría" marcado en la categoría, y validación al crear la cita) y B (campo en `/servicios` y en el asistente) | Fase 1, necesita migración en `catalog` |
| R4 | Foto de presentación de cada barbero | La API ya guarda la foto del profesional (M4) y la pública la expone | B (mostrarla) | Fase 1 |
| R5 | Especialidad de cada barbero en la reserva | Las especialidades existen (M4), pero la API pública no las expone | A (agregarlas a `public/professionals/`) y B | Fase 1 |
| R6 | Calificación por barbero | `Professional.rating_avg` existe como campo reservado, sin uso | — | **Fuera de alcance** (§12: reseñas) |
| R7 | Calendario que marque con colores los días disponibles y los ocupados | `public/availability/days/` devuelve solo los días con horario libre | A (devolver el estado de cada día: libre, lleno o cerrado) y B (colores) | Fase 1 |
| R8 | Solo horas libres, sin dejar reservar las ocupadas, y sin mostrar quién reservó | Ya funciona: los horarios salen del motor (M5), la doble reserva la impide la base de datos, y con "cualquiera" no se muestra el profesional. Ningún cliente ve datos de otros | — | Hecho; verificar en la prueba manual |
| R9 | Todo el flujo en un solo modal, con menos pasos | El asistente tiene 5 pasos en páginas | B | Fase 1 (decisión de UX) |
| R10 | Agregar la cita al wallet del celular | — | — | **Fuera de alcance** (§1 y §12: wallet). Alternativa dentro de alcance: botón "Agregar al calendario" con un archivo `.ics` |

### Super Admin

| # | Mejora | Qué existe hoy | Quién | Alcance |
|---|---|---|---|---|
| S1 | Quitar el selector de idioma del panel del Super Admin y dejarlo solo en el sitio de cada negocio | El selector aparece en todos los paneles | B | Fase 1 |
| S2 | Tipo de negocio con selección múltiple, en píldoras con checkbox | `Tenant.vertical` admite un solo valor | A (modelo y migración en `tenancy`) y B (formulario) | **Cambia la spec** (§1: "un campo `vertical`") |
| S3 | Quitar zona horaria y moneda del alta de negocio | Se piden en el formulario; tienen valores por defecto (`America/Bogota`, `COP`) | B (ocultarlos y usar los valores por defecto) | Fase 1 |
| S4 | Quitar el idioma del alta; el idioma lo elige el visitante en el sitio del negocio | El negocio tiene idioma por defecto y el sitio ya trae selector | B | Fase 1 |
| S5 | Datos del propietario al crear el negocio: tipo y número de documento (CC), RUT/NIT, teléfono y contraseña | Se pide correo y nombre; la contraseña es temporal y se cambia al primer ingreso | A (`accounts`: documento y teléfono) y B (formulario) | Fase 1. Ojo: que el Super Admin escriba la contraseña del propietario es menos seguro que la temporal actual; conviene mantener la temporal o un enlace para que el propietario la defina |
| S6 | Dashboard del estado de la plataforma: total de negocios, activos, suspendidos, nuevos | Hay listado con filtros, sin resumen | B (pantalla) y quien sea dueño de `platform_admin` (API de métricas) | Fase 1 |
| S7 | Soporte: categorías, tickets, sesiones de soporte y quién atiende cada ticket | — | — | **Nuevo módulo, no está en la spec**. Fase siguiente |
| S8 | Términos y condiciones de la plataforma | Cada negocio tiene sus textos legales; la plataforma no | B | Fase 1 (texto estático) |
| S9 | Pagos de la suscripción: pagados, pendientes, vencidos y fallidos | — | — | **Fuera de alcance** (§1: precios del software; §12: Wompi y facturación). Fase siguiente |
| S10 | Uso del sistema por negocio (citas, reservas web, usuarios, último ingreso) | Los datos existen en la base | A (API de métricas) y B (pantalla) | Fase 1, después de M9 |
| S11 | Integraciones por negocio: cómo le funcionan WhatsApp, correo y wallet | `NotificationLog` llega en M8 | B (con M8) | Fase 1 para WhatsApp y correo; wallet fuera de alcance |
| S12 | Monitoreo: errores del sistema, copias de seguridad y auditoría | La auditoría ya existe (M3); errores (Sentry) y copias de seguridad están en M10 | A y B en M10 | Fase 1 (M10) |

### Qué hacer con esta lista

1. **Llevar al encargado** las marcadas "Cambia la spec" o "Fuera de alcance" (R6, R10, S2, S7, S9 y el wallet de S11). Ninguna se programa sin su aprobación.
2. **Las de Fase 1** se reparten así:
   - **Frente A**: R3, R5, R7, S2 (si se aprueba), S5 y S10, junto con M9.
   - **Frente B**: R1, R2, R4, R9, S1, S3, S4, S6, S8 y S11, junto con M8 y la pantalla `/reportes`.
3. **R8** ya está cubierto por el backend; solo hay que confirmarlo en la próxima prueba manual.
