# Progreso del proyecto

Estado del SaaS de agendamiento y plan a seguir. Se actualiza al cerrar cada hito o cada PR importante.

**Corte:** 2026-11-05 · `develop` en `b9f0646` (M0 a M7 completos y la base de tareas de M8) · `main` en M0 (`12343f6`, espera la revisión del encargado).

---

## 1. Resumen en 30 segundos

- **Hecho:** M0 a M3 (base, multi-negocio, cuentas y panel del Super Admin), la **Fase 0** (contratos compartidos) y dos piezas de M4: imágenes en WebP (frente B) y la API de horarios y bloqueos (frente A).
- **En curso:** M4. El frente A termina su parte con la configuración de agenda en `Tenant`; el frente B tiene pendientes empresa, catálogo, equipo, puestos y sus pantallas.
- **Siguiente para el frente A:** configuración de agenda en `Tenant`, `/me/` con permisos y después M5 (motor de disponibilidad).
- **Bloqueante conocido para M4:** al crear un negocio no se crea su sede, y sin sede no se pueden crear profesionales (ver §5).
- **Recordatorio obligatorio:** la verificación en dos pasos (2FA) está **apagada en desarrollo** y hay que reactivarla antes de entregar (`pormejorar.md` §33).

---

## 2. Equipo y forma de trabajo

| | Frente A — motor de agenda | Frente B — producto y UI |
|---|---|---|
| Responsable | Diego (`DiegoA-01`) | Yehiron |
| Apps | `scheduling`, `booking`, `commissions`, `reports` | `company`, `catalog`, `media`, `notifications` y todas las pantallas |

- Una rama por tarea desde `develop`, y **PR hacia `develop`, nunca hacia `main`**. El CI corre en cada PR.
- Solo el dueño de una app crea migraciones en ella.
- Antes de empezar una tarea: `git fetch` y revisar los PR abiertos, para no repetir trabajo.
- Reglas completas en [`docs/REPARTO.md`](docs/REPARTO.md).

---

## 3. Lo que está hecho

### Línea de tiempo

| Hito | Qué entrega | Quién | Estado |
|---|---|---|---|
| **M0** — Base | Repositorio, Docker Compose (api, worker, beat, web, postgres, redis, caddy), CI, settings, healthcheck, i18n base | Diego | En `main` y `develop` |
| **M1** — Tenancy | Negocios, subdominios, middleware por host, RLS de PostgreSQL con rol sin superusuario, módulos por plan | Diego | En `develop` |
| **M2** — Cuentas | Usuario propio, roles, login por sesión + CSRF, recuperación de contraseña, 2FA (TOTP), `/me/`, matriz de permisos, contraseñas con Argon2id | Diego | En `develop` |
| **M3** — Super Admin | API y panel: empresas, planes, tema con contraste WCAG, módulos, dominios propios verificados por DNS, suspensión, auditoría; propietario con contraseña temporal | Diego | En `develop` |
| **Fase 0** — Contratos compartidos | Apps registradas, modelos de la §6 con migraciones y RLS, anti doble reserva, fábricas y textos divididos, esqueleto del dashboard | Yehiron (PR #2 y #3) | En `develop` |
| **M4** (parcial) — Imágenes | App `media`: subida de imágenes convertidas a WebP con variantes de 200, 800 y 1600 px | Yehiron (PR #4) | En `develop` |
| **M4** (parcial) — Horarios y bloqueos | `GET/PUT professionals/{id}/working-hours/`, CRUD `time-blocks/` con 409 si chocan con citas, alcance "solo lo propio" para el profesional, fechas en la zona del negocio | Diego (PR #6) | En `develop` |

### Qué hay en el código hoy

**Backend** — una app de Django por módulo:

| App | Qué tiene |
|---|---|
| `tenancy` | Negocios, dominios, planes, módulos, RLS y contexto del negocio activo |
| `accounts` | Usuarios, roles, sesión, 2FA, recuperación y cambio de contraseña, matriz de permisos |
| `platform_admin` | API del Super Admin y registro de auditoría |
| `company` | Datos de la empresa y sedes (`Location`) |
| `catalog` | Categorías, servicios, especialidades, profesionales, servicios por profesional y puestos (modelos y un `services.py` mínimo de lectura) |
| `scheduling` | Horarios de trabajo y bloqueos de agenda, con su API (`working-hours/`, `time-blocks/`) |
| `booking` | Clientes, citas y servicios de cada cita, con la restricción anti doble reserva (modelos y `overlapping_appointments`) |
| `media` | Subida de imágenes a WebP (`POST /api/v1/media/`) |
| `commissions`, `notifications`, `reports` | Registradas y vacías |

**Frontend** (React):
- Login con 2FA, cambio forzado de contraseña y recuperación.
- Panel del Super Admin completo: empresas, detalle (datos, tema, módulos, dominios), planes y auditoría.
- Esqueleto del panel del negocio: menú según rol y plan, y las 9 secciones de la spec vacías (agenda, citas, clientes, servicios, equipo, puestos, horarios, reportes, empresa).
- Textos en español e inglés, divididos por área.

**Calidad:**
- Pruebas: **454** en el backend y **51** en el frontend, todas en verde sobre `develop`. Ruff, mypy, ESLint y tipos limpios.
- Prueba guardiana: falla si una tabla de negocio queda sin RLS.
- El CI valida además la documentación OpenAPI sin avisos.

---

## 4. Decisiones tomadas

Para no volver a discutirlas. Las que dicen "provisional" se revisan antes de entregar.

| Tema | Decisión | Dónde está documentado |
|---|---|---|
| Autenticación | Sesión por cookie HttpOnly + CSRF, no JWT | `docs/adr/0001-autenticacion-por-sesion.md` |
| Contraseñas | Argon2id con el perfil mínimo de OWASP (19 MiB). Dependencia `argon2-cffi` aprobada | `pormejorar.md` §7 |
| 2FA | Obligatorio para el Super Admin y opcional para el propietario. **Provisional: apagado en desarrollo** (`REQUIRE_TWO_FACTOR=0`). Producción no arranca con él apagado | `pormejorar.md` §5 y §33 |
| QR del 2FA | Sin QR: clave manual (la librería de QR no está en la lista) | `pormejorar.md` §25 |
| Aislamiento | Base compartida + `tenant_id` + RLS forzado, con la app conectada por un rol sin superusuario | `CHANGELOG.md` (M1) |
| Dominios propios | Verificación por registro TXT, consultado por DNS sobre HTTPS (Google), sin dependencias nuevas | `pormejorar.md` §26 |
| Suspender un negocio | Bloquea todo su acceso (403) y conserva los datos. Modo "solo lectura" pendiente | `pormejorar.md` §11 |
| Planes | Editar un plan no cambia los módulos de los negocios que ya lo usan, salvo que se pida. Cambiar el plan de un negocio sí los reinicia | `CHANGELOG.md` (M3) |
| Flujo de Git | Rama por tarea, PR a `develop`, nunca a `main`; `main` solo con revisión del encargado | `docs/REPARTO.md` |

---

## 5. Pendientes antes de seguir con M4

### Lo que falta de la Fase 0

| # | Qué falta | Por qué importa | Dueño propuesto | Bloquea |
|---|---|---|---|---|
| 1 | **Sede por defecto al crear un negocio** | `Professional` y `Resource` exigen una sede; sin ella no se crea ninguno | B | **M4** |
| 2 | **Configuración de agenda en `Tenant`** (`slot_step_min`, `min_notice_min`, `max_advance_days`, `cancel_min_hours`) | La necesita el motor de disponibilidad | A | M5 |
| 3 | **Rutas públicas** (`/reservar`, `/cita/:token`, páginas legales) | Sin ellas `App.tsx` no queda cerrado | B | M6 |
| 4 | **`/me/` con los permisos del rol** | Hoy el menú copia la matriz de roles en el frontend | A | — |
| 5 | **Polling de Vite** en Docker sobre Windows | Sin él, el navegador muestra código viejo hasta recrear el contenedor `web` | Cualquiera | — |

La rama **local** `feat/f0-contratos` (no subida) tiene una versión de referencia de los puntos 2, 4 y 5 para copiar en PRs pequeños.

### Acuerdos pendientes entre los dos
- **Dueños de `tenancy`, `accounts` y `platform_admin`.** Propuesta: los dos primeros para A y el tercero para B.
- **Funciones del catálogo que usa el motor de agenda** (tarea B4.1): duración total con overrides, profesionales que ofrecen un conjunto de servicios, si hace falta puesto, precio y comisión por profesional.
- **Qué pasa al bajar de plan** con los profesionales o sedes que sobran.
- **Si el módulo `commissions` tiene pantalla propia** o se ve dentro de `/reportes`.

### Documentación por subir
- `docs/PLAN-DESARROLLO.md` (tareas numeradas) y `docs/CONTRATOS.md` solo existen en la rama local `feat/f0-contratos`. Hay que adaptarlos a la Fase 0 de Yehiron antes de subirlos.

---

## 6. Plan a seguir

El camino crítico es **M4 → M5**: casi todo lo demás depende de citas y disponibilidad. Cada hito se da por terminado con su criterio de aceptación de la spec (§14), no con una fecha.

| Hito | Frente A (Diego) | Frente B (Yehiron) | Criterio de aceptación |
|---|---|---|---|
| **M4** | ~~Horarios y bloqueos (A4.1 a A4.4)~~ hecho en el PR #6; configuración de agenda en `Tenant`; `/me/` con permisos | Sede por defecto; funciones del catálogo para A (B4.1); API de empresa, sedes, catálogo, profesionales y puestos; límites del plan; pantallas `/empresa`, `/servicios`, `/equipo`, `/puestos`, `/horarios` | CRUD completo con permisos; imágenes en WebP |
| **M5** | Configuración de agenda; motor de disponibilidad (§8) con caché; crear cita con revalidación; estados y reprogramación; API de citas del dashboard; prueba de concurrencia | `seed_demo` (primera tarea, A lo necesita); terminar pantallas de M4; preparar mocks de M6 | 20 POST simultáneos al mismo hueco: 1 cita y 19 respuestas 409 |
| **M6** | API pública: empresa, servicios, profesionales, días y horarios disponibles, crear cita (consentimiento, límites, honeypot) y gestión por token | Asistente `/reservar`, `/cita/:token`, páginas legales, banner de cookies | Reserva completa en móvil en menos de 60 s; la cancelación respeta la ventana |
| **M7** | Endpoint SSE con el negocio activo dentro del streaming; API de clientes | `/agenda` en vista de día y semana con SSE, `/citas` y `/clientes` | Una cita creada en la web aparece en la agenda abierta sin recargar |
| **M8** | Clase base de tareas de Celery con el negocio activo | Notificaciones por correo y WhatsApp (FakeProvider), recordatorios con Celery Beat, reintentos, credenciales cifradas | Confirmación y recordatorio registrados en `NotificationLog`; reintentos probados |
| **M9** | Comisiones al completar una cita, reportes de ventas y reservas, exportación CSV (puede empezar al terminar M5) | Pantalla `/reportes` | Los valores cuadran con casos calculados a mano |
| **M10** | Límites de intentos, auditoría de inicios de sesión, cifrado del secreto 2FA, copias de seguridad, servidor de producción | Pruebas e2e con Playwright, accesibilidad, logs y Sentry | Playwright cubre reservar → completar → comisión |
| **Cierre** | **Reactivar el 2FA**, revisar los puntos Alta de `pormejorar.md`, revisión del encargado y PR de `develop` a `main` | | Sin puntos Alta abiertos |

### Dependencias que deciden el orden
- **A necesita de B:** las funciones del catálogo (B4.1) antes del motor de M5, y `seed_demo` al empezar M5.
- **B necesita de A:** el OpenAPI de horarios antes de la pantalla `/horarios`, y el OpenAPI público antes del asistente de M6.
- **Contrato primero:** quien publica un API lo describe en OpenAPI antes de implementarlo, para que el otro avance con datos simulados.

### Aprobaciones de dependencias que conviene decidir pronto

| Paquete | Para qué | Decidir antes de |
|---|---|---|
| Servidor de producción (`gunicorn`, `uvicorn` o `daphne`) | Tiempo real y producción | M7 |
| Librería de cifrado (`cryptography`) | Credenciales de WhatsApp y secreto 2FA | M8 |
| `@testing-library/react` y `jsdom` | Pruebas de pantallas | M4 (frente B) |
| Playwright | Pruebas de extremo a extremo (las exige la spec) | M10 |

---

## 7. Riesgos y alertas

1. **2FA apagado en desarrollo.** Reactivarlo es obligatorio antes de entregar (`pormejorar.md` §33).
2. **Claves foráneas entre negocios.** RLS impide *ver* datos de otro negocio pero no *enlazarlos*. Cada `services.py` debe buscar los ids recibidos dentro del negocio activo antes de usarlos.
3. **Servidor de desarrollo.** Los contenedores usan `runserver`, que no sirve para producción (`pormejorar.md` §4).
4. **PR con destino equivocado.** GitHub propone `main` como base: el PR #5 se mezcló ahí por error y `main` se devolvió a M0. El PC de Diego tiene un hook local `pre-push` que rechaza los push a `main` (conviene que Yehiron ponga el mismo), y hay que revisar "base: develop" antes de crear el PR (`docs/REPARTO.md`, regla 11).
5. **Docker Desktop en Windows** se apaga con frecuencia. Si aparece el error de `dockerInference`: Quit, volver a abrir y, si sigue, `wsl --shutdown`.
6. **Imágenes en producción.** Falta definir cómo se sirven los archivos subidos (`pormejorar.md` §34).
7. **Copias de seguridad.** No existen todavía; deben estar antes de tener un negocio piloto (`pormejorar.md` §23).

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
