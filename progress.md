# Progreso del proyecto

Estado del SaaS de agendamiento y plan a seguir. Se actualiza al cerrar cada hito o cada PR importante.

**Corte:** 2026-10-30 · `develop` en `269e801` · `main` en M0 (espera la revisión del encargado).

---

## 1. Resumen en 30 segundos

- **Hecho:** M0 a M3 (base, multi-negocio, cuentas y panel del Super Admin), la **Fase 0** (contratos compartidos) y la primera pieza de M4 (imágenes en WebP).
- **En curso:** M4, que se divide en dos frentes que trabajan en paralelo.
- **Siguiente para el frente A:** la API de horarios y bloqueos (tarea A4.1 en adelante).
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

### Qué hay en el código hoy

**Backend** — una app de Django por módulo:

| App | Qué tiene |
|---|---|
| `tenancy` | Negocios, dominios, planes, módulos, RLS y contexto del negocio activo |
| `accounts` | Usuarios, roles, sesión, 2FA, recuperación y cambio de contraseña, matriz de permisos |
| `platform_admin` | API del Super Admin y registro de auditoría |
| `company` | Datos de la empresa y sedes (`Location`) |
| `catalog` | Categorías, servicios, especialidades, profesionales, servicios por profesional y puestos (solo modelos) |
| `scheduling` | Horarios de trabajo y bloqueos de agenda (solo modelos) |
| `booking` | Clientes, citas y servicios de cada cita, con la restricción anti doble reserva (solo modelos) |
| `media` | Subida de imágenes a WebP (`POST /api/v1/media/`) |
| `commissions`, `notifications`, `reports` | Registradas y vacías |

**Frontend** (React):
- Login con 2FA, cambio forzado de contraseña y recuperación.
- Panel del Super Admin completo: empresas, detalle (datos, tema, módulos, dominios), planes y auditoría.
- Esqueleto del panel del negocio: menú según rol y plan, y las 9 secciones de la spec vacías (agenda, citas, clientes, servicios, equipo, puestos, horarios, reportes, empresa).
- Textos en español e inglés, divididos por área.

**Calidad:**
- Pruebas: **424** en el backend y **51** en el frontend, todas en verde sobre `269e801`. Ruff, mypy, ESLint y tipos limpios.
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
- `docs/REPARTO.md` actualizado y este `progress.md` están en la rama `docs/reparto-estado`, sin commit.
- `docs/PLAN-DESARROLLO.md` (tareas numeradas) y `docs/CONTRATOS.md` solo existen en la rama local `feat/f0-contratos`. Hay que adaptarlos a la Fase 0 de Yehiron antes de subirlos.

---

## 6. Plan a seguir

El camino crítico es **M4 → M5**: casi todo lo demás depende de citas y disponibilidad. Cada hito se da por terminado con su criterio de aceptación de la spec (§14), no con una fecha.

| Hito | Frente A (Diego) | Frente B (Yehiron) | Criterio de aceptación |
|---|---|---|---|
| **M4** | Contrato OpenAPI de horarios y bloqueos (A4.1); API de horarios (A4.2); bloqueos con 409 si chocan con citas (A4.3); permisos "solo lo propio" (A4.4) | Sede por defecto; funciones del catálogo para A (B4.1); API de empresa, sedes, catálogo, profesionales y puestos; límites del plan; pantallas `/empresa`, `/servicios`, `/equipo`, `/puestos`, `/horarios` | CRUD completo con permisos; imágenes en WebP |
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
4. **Docker Desktop en Windows** se apaga con frecuencia. Si aparece el error de `dockerInference`: Quit, volver a abrir y, si sigue, `wsl --shutdown`.
5. **Imágenes en producción.** Falta definir cómo se sirven los archivos subidos (`pormejorar.md` §34).
6. **Copias de seguridad.** No existen todavía; deben estar antes de tener un negocio piloto (`pormejorar.md` §23).

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
