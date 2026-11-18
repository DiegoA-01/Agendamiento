# Progreso del proyecto

Estado del SaaS de agendamiento y plan a seguir. Se actualiza al cerrar cada hito o cada PR importante.

**Corte:** 2026-11-18 · `develop` en `579b29c` (PR #74) · `main` en M0 (`12343f6`, espera la revisión del encargado). La rama por defecto de GitHub es `develop`.

---

## 1. Resumen en 30 segundos

- **Hecho:**
  - Los hitos M0 a M9 completos, con backend y pantallas. De M10 está todo salvo Sentry y el servidor de producción.
  - **Todas las mejoras de Fase 1** que salieron de las pruebas manuales (§10).
  - Del 2026-11-11 al 2026-11-18, 28 PRs más (#47 a #74, §11):
    - 2FA reactivado con códigos de recuperación.
    - Rediseño completo de la reserva pública, de los tres paneles y de la portada.
    - **Tres estilos de reserva** que elige el Super Admin.
    - Panel del barbero.
    - Horarios con descansos.
    - Comisiones por cita.
- **Avance aproximado:** la API cubre los 37 grupos de la spec, y el proyecto completo va en ≈ 97 %.
- **Backlog:**
  - A ningún frente le queda trabajo de Fase 1.
  - Quedan las decisiones que necesitan aprobación (§5) y las protecciones de datos de clientes de la Ley 1581, propuestas y sin hacer (§5).
- **Antes de entregar:**
  - Decidir el servidor de producción y Sentry.
  - La prueba manual completa (`docs/PRUEBA-MANUAL.md`).
  - Pasar la revisión del encargado y hacer el PR de `develop` a `main`.
- **Pruebas sobre `develop`:**
  - Backend: **826**. Frontend: **150**.
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
- **Push:** el agente de Diego nunca hace push sin una confirmación explícita en ese mismo turno.
- **Idioma:** el agente responde siempre en español.
- **Apps del otro frente:**
  - Solo el dueño de una app crea migraciones en ella. Si un frente necesita una función en una app ajena, la agrega mínima y avisa en el PR.
  - Varias tareas de B las hizo el frente A con permiso: pantallas de M9, R5 y R7, la migración de `catalog` de R3, S6, S8 y R9, los conflictos de los PR #37, #38 y #40, y todo el rediseño de pantallas de §11.
  - Desde el 2026-11-11 Diego también toma el trabajo de B ("lo que le tocaba a Yehiron lo voy a hacer yo").
- **Antes de empezar una tarea:** `git fetch`, revisar los PR abiertos y hacer `git pull` de la propia rama, que puede tener merges del otro frente.
- **PRs en paralelo:** dos PRs abiertos a la vez casi siempre chocan en el `CHANGELOG.md`, porque los dos agregan arriba. Se resuelve trayendo `develop` a la rama y dejando las dos entradas.
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
| **Mejoras de Fase 1** (§10) | R1 a R5, R7, R9, S1, S3 a S6, S8, S10 y S11 | Diego y Yehiron | #32–#35, #38, #40, #41, #43, #45, #46 |
| **Seguridad y diseño** (§11) | 2FA reactivado y códigos de recuperación; rediseño de la reserva, los paneles y la portada; tres estilos de reserva; panel del barbero; horarios con descansos; comisiones por cita | Diego (A y B) | #47–#74 |

### Qué hay en el código hoy

**Backend** — una app de Django por módulo:

| App | Qué tiene |
|---|---|
| `tenancy` | Negocios, dominios, planes, módulos, RLS, contexto del negocio activo, configuración de agenda (cancelación por defecto hasta 1 hora antes), **estilo de la página de reservas** (`public_style`) y tareas de Celery por negocio |
| `accounts` | Usuarios (con tipo y número de documento), roles, sesión, 2FA con **10 códigos de recuperación**, recuperación de contraseña, matriz de permisos, `/me/`, límite de intentos y la señal `security_event` |
| `platform_admin` | API del Super Admin, auditoría (incluye los eventos de seguridad y el cambio de estilo), resumen de la plataforma (S6), uso por negocio (S10), integraciones por negocio (S11) y `seed_demo` |
| `company` | Empresa (con NIT), sedes y textos legales limpios de HTML peligroso |
| `catalog` | Categorías ("uno por cita" encendido por defecto, R3), servicios, especialidades, profesionales, servicios por profesional y puestos |
| `scheduling` | Horarios (varias franjas por día; el hueco entre franjas es un **descanso**), bloqueos, configuración de agenda, motor de disponibilidad y calendario por estado del día (R7) |
| `booking` | Citas (con **"para quién"**, `attendee_name`), estados, clientes (sin citas cruzadas para la misma persona), reserva pública, **descansos públicos** (`/public/availability/breaks/`), cancelación por enlace, eventos SSE y datos para reportes y notificaciones |
| `commissions` | Comisiones inmutables y ajustes; CSV detallado por servicio o **por cita** (`group=appointment`) |
| `reports` | Reportes de ventas y reservas, con CSV |
| `notifications` | Correo y WhatsApp, plantillas por idioma y vertical, recordatorios y `NotificationLog` |
| `media` | Imágenes en WebP |

**Frontend** (React):
- **Login:**
  - Con 2FA, códigos de recuperación, cambio forzado de contraseña y recuperación.
  - Todos los campos de contraseña tienen un **ojo** para ver lo escrito.
  - El login del Super Admin va en vidrio verde y el de cada negocio en café, como su panel.
- **Sin selector de idioma:**
  - El sitio público y el panel del negocio usan el idioma configurado del negocio.
  - El Super Admin y las pantallas de acceso van en español.
- **Condiciones de uso de la plataforma** (S8): página `/condiciones-de-uso` en los dos hosts. Es un borrador que debe revisar un abogado.
- **Panel del Super Admin** (vidrio blanco con verde metalizado y barra lateral oscura de vidrio líquido):
  - Resumen de la plataforma (S6), empresas, alta simplificada (S3, S4, S5).
  - Detalle de cada empresa con datos, tema y **estilo de la reserva**, módulos, dominios, uso (S10) e integraciones (S11).
  - Planes, auditoría y seguridad con los códigos de recuperación.
  - Las acciones de riesgo piden confirmación en una ventana.
- **Panel del negocio** (vidrio con café metalizado, cuero y blanco):
  - **Inicio:** ventas del mes, citas de hoy, ticket promedio, reservas web, ventas por mes y por servicio.
  - **Agenda:**
    - En tiempo real, con bloques de color por estado y líneas cada media hora.
    - Las canceladas se ven atenuadas.
  - **Citas:**
    - Pestañas por profesional; dentro de cada uno, separadas por día ("Hoy", "Mañana") con las pendientes.
    - El barbero solo ve lo suyo, sin pestañas.
  - **Clientes, servicios, equipo y puestos.**
  - **Horarios:**
    - Cada día tiene jornada y descansos en ámbar, con una barra del día.
    - Hay una barra que avisa los cambios sin guardar.
  - **Empresa.**
  - **Reportes:** comisiones con **una fila por cita**, ajustes sumados y detalle por servicio.
  - **Movimiento:** el menú y los botones se animan. La barra lateral se desplaza sin barra gris, con una flecha de vidrio.
- **Panel del barbero:**
  - Es el mismo panel con menos secciones: agenda, citas, servicios, equipo, horarios y reportes, solo con lo suyo.
  - En el demo local hay una cuenta para Andrés; la contraseña está en `.local/`.
- **Sitio público del negocio:**
  - **Tres estilos que elige el Super Admin:**
    - **Esmeralda:** verde oscuro metalizado con dorado.
    - **Barbería clásica:** carbón, vino y latón, con el poste de barbero girando.
    - **Salón de belleza:** rosa piel, perla y oro rosa.
    - En «Automático» se toma el estilo según el tipo de negocio.
  - **Portada a pantalla completa:**
    - Un celular inclinado hace la reserva solo y, al confirmar, la **tarjeta de la cita** sale de él.
    - Debajo van los pasos sincronizados con el celular y la lista de servicios con precios.
  - **Reserva en una ventana de 3 pasos** (R9), con animaciones y sin barra de desplazamiento:
    - Servicios, con uno por categoría y la opción de **"Reservar otra cita para alguien más"**.
    - Profesional, día y hora, con los **descansos en ámbar**.
    - Datos del cliente.
    - Confirmación con un sello animado.
  - **«Tu cita»:** la cita como **tarjeta de billetera** (chip, brillo, inclinación 3D). Se cancela hasta 1 hora antes.
  - Páginas legales y aviso de cookies.
  - En toda la app aparece la **mano** al pasar el cursor por los botones.
- **Idiomas:** todos los textos en español e inglés.

**Calidad:**
- **Pruebas:**
  - **826** en el backend, **150** en el frontend y la prueba de Playwright, en verde sobre `develop`.
  - Ruff, mypy, ESLint, Prettier, tipos, build y OpenAPI sin avisos.
- **El CI tiene tres trabajos:**
  - `backend`.
  - `frontend`.
  - `e2e`: levanta todo con Docker Compose y corre Playwright, con Chromium en caché y reintentos si falla la descarga.
- **Para probar a mano:**
  - `docker compose exec api python manage.py seed_demo --vertical barbershop` crea un negocio demo completo.
  - El Super Admin entra por `admin.localhost:8080`, no por el dominio del negocio.
  - La lista de comprobación está en `docs/PRUEBA-MANUAL.md`.

---

## 4. Decisiones tomadas

Para no volver a discutirlas. Las que dicen "provisional" se revisan antes de entregar.

| Tema | Decisión | Dónde está documentado |
|---|---|---|
| Autenticación | Sesión por cookie HttpOnly + CSRF, no JWT | `docs/adr/0001-autenticacion-por-sesion.md` |
| Contraseñas | Argon2id con el perfil mínimo de OWASP. Dependencia `argon2-cffi` aprobada | `pormejorar.md` §7 |
| 2FA | Obligatorio para el Super Admin y opcional para el propietario. Encendido también en desarrollo desde el 2026-11-11 (`REQUIRE_TWO_FACTOR=1`). 10 códigos de recuperación de un solo uso, guardados con SHA-256; se regeneran en `/seguridad` | `pormejorar.md` §2, §5 y §33 |
| Aislamiento | Base compartida + `tenant_id` + RLS forzado, con la app conectada por un rol sin superusuario | `CHANGELOG.md` (M1) |
| Doble reserva | La garantía final es la restricción de exclusión de PostgreSQL; la API revalida antes y responde `409 slot_taken` con sugerencias | `CHANGELOG.md` (M5) |
| Cliente en dos citas | Una misma persona no puede tener dos citas activas que se crucen (`409 customer_overlap`). Se compara por cliente **y** por "para quién" (`attendee_name`): un papá puede reservar para él y para su hijo a la misma hora | `CHANGELOG.md` (R3 y "citas para otra persona") |
| Servicios por categoría | "Uno por cita" (`400 one_per_category`) viene **encendido por defecto** en todas las categorías desde el 2026-11-12; el dueño lo puede apagar | `CHANGELOG.md` |
| Cancelación por el cliente | Por enlace, desde la confirmación o desde «Tu cita», hasta `cancel_min_hours` antes; por defecto **1 hora** | `CHANGELOG.md` |
| "Cualquiera" | Se asigna el profesional libre con menos citas ese día; empate por orden alfabético. El cliente no ve quién atiende ni sus descansos | `CHANGELOG.md` (M5 y M6) |
| Descansos | No hay modelo nuevo: un descanso es el hueco entre dos franjas del mismo día. La pantalla de horarios arma las franjas a partir de la jornada y los descansos | `CHANGELOG.md` |
| Reserva pública | 10 POST por hora por IP y 5 por celular; IP real detrás de Caddy (`TRUSTED_PROXY_COUNT`); honeypot; captcha opcional | `CHANGELOG.md` (M6) |
| Idioma | Sin selector en ninguna pantalla: el sitio público y el panel del negocio usan el idioma del negocio; el Super Admin y el acceso van en español. Esto deja sin efecto S1 | `CHANGELOG.md` |
| Aspecto del sitio público | **Estilos cerrados que elige el Super Admin** (`emerald`, `barbershop`, `salon`; vacío = según el tipo de negocio). Los colores de tema del negocio ya no se aplican al sitio público. Los negocios que existían quedaron en `emerald` | `CHANGELOG.md` |
| Aspecto de los paneles | Super Admin: vidrio blanco con verde metalizado. Negocio: vidrio con café metalizado, cuero y blanco. Las reglas de "sin degradados ni sombras" del skill de diseño ceden ante el metalizado y el vidrio que pidió el cliente, marcados con `taste-skill-ignore` | `CHANGELOG.md` |
| Comisiones | Inmutables: nunca se editan ni se borran; las correcciones son ajustes que guardan la diferencia. Redondeo `ROUND_HALF_UP`. Se guardan **por servicio** (spec §11), pero el reporte y el CSV las muestran **por cita**, con los ajustes sumados | `CHANGELOG.md` (M9 y "comisiones por cita") |
| Tiempo real | SSE sobre Redis pub/sub, publicado después del commit; el profesional solo recibe sus citas | `CHANGELOG.md` (M7) |
| Tareas de Celery | Toda tarea de negocio usa `TenantTask` y recibe el id del negocio como primer argumento | `apps/tenancy/tasks.py` |
| Notificaciones | WhatsApp si el plan lo incluye y hay consentimiento; si no, correo. `booking` avisa por señal, sin importar `notifications` | `CHANGELOG.md` (M8) |
| Límite de intentos | 20 fallos por IP y 10 por correo en 15 minutos; 3 recuperaciones por correo | `CHANGELOG.md` (M10) |
| Copias de seguridad | `pg_dump` cifrado con AES-256 y suma sha256; la restauración se prueba en una base aparte | `docs/OPERACION.md` |
| Dependencias | Playwright aprobado (solo desarrollo y CI). Sentry, servidor de producción y `cryptography` siguen sin aprobar | §5 |
| Reserva | Ventana de 3 pasos encima de la portada (`<dialog>` nativo); `/reservar` abre la misma ventana | `CHANGELOG.md` (R9) |
| Condiciones de uso | Texto fijo en las traducciones (`terms.json`), igual para todos los negocios; borrador pendiente de abogado | `CHANGELOG.md` (S8) |
| Flujo de Git | Rama por tarea, PR a `develop`, nunca a `main`; `main` solo con revisión del encargado. `develop` es la rama por defecto de GitHub | `docs/REPARTO.md` |

---

## 5. Pendientes y acuerdos

### Por decidir entre los dos o con el encargado
- **Las mejoras marcadas "Cambia la spec" o "Fuera de alcance"** en la §10 (R6, R10, S2, S7, S9 y el wallet de S11) necesitan la aprobación del encargado.
- **Qué pasa al bajar de plan** con los profesionales o sedes que sobran.
- **Precio por profesional en la reserva pública:** hoy el asistente muestra un precio de referencia.
- **Condiciones de uso (S8):** que un abogado revise el borrador antes de abrir la plataforma a negocios reales.
- **Cuentas del equipo desde el panel** (`pormejorar.md` §39): hoy las cuentas de recepción y de barbero se crean por comando (`docs/PRUEBA-MANUAL.md` §5).
- **Protecciones de datos de clientes (Ley 1581),** propuestas el 2026-11-17 y **sin hacer**:
  1. El permiso de WhatsApp solo lo da el cliente. El personal solo puede quitarlo, y la fecha de autorización no se edita.
  2. "Eliminar" un cliente debe **anonimizar** sus datos, no solo ocultarlos. Las citas y comisiones se conservan.
  3. Registro de quién cambió nombre, celular o correo.
  4. Aviso de no guardar datos sensibles en las notas.
  5. Más adelante: descargar los datos de un cliente.
- **Colores de tema por negocio:** con los estilos de reserva ya no se usan en el sitio público. Decidir si el editor de colores del Super Admin se quita o se deja solo para el logo.
- **Estilos ligados al plan:** se propuso que Barbería clásica o Salón sean del plan Pro. No se decidió.

### Aprobaciones de dependencias

| Paquete | Para qué | Estado |
|---|---|---|
| Playwright | Prueba de punta a punta | **Aprobado** y en uso |
| Servidor de producción (`gunicorn`, `uvicorn` o `daphne`) | Producción y SSE: cada agenda abierta ocupa una conexión | Pendiente; decidir antes de desplegar |
| Sentry | Errores en producción (S12) | Pendiente; tiene sentido cuando haya servidor de producción |
| `cryptography` | Cifrar el secreto del 2FA y las credenciales de WhatsApp por negocio | Pendiente |

### Material de venta
- **Video para historia de Instagram** (2026-11-17):
  - 1080×1920, 58 s, sin audio. Se grabó de la app real: portada, reserva paso a paso y tarjeta de la cita.
  - Está en `.local/barberia-demo-historia.mp4`, que no se sube al repositorio.
  - Las citas de prueba que creó la grabación (a nombre de "Laura Gómez") quedaron canceladas.

---

## 6. Plan a seguir

Cada hito se da por terminado con su criterio de aceptación de la spec (§14), no con una fecha.

| Paso | Frente A (Diego) | Frente B (Yehiron) | Estado |
|---|---|---|---|
| **M0 a M9** | — | — | ✓ |
| **M10** | ~~Límites, auditoría de ingresos, logs, copias~~ (#36), ~~Playwright~~ (#39). Falta: servidor de producción y cifrado del secreto 2FA (necesitan aprobación) | Sentry (necesita aprobación), revisión de accesibilidad | Casi listo |
| **Mejoras de Fase 1** | ~~R3, R5, R7, S5, S10~~ y, por B, ~~S6, S8, R9~~. S2 solo si se aprueba | ~~R1, R2, R4, S1, S3, S4, S11~~ | ✓ |
| **Seguridad y diseño** (§11) | ~~2FA y códigos~~, ~~rediseño de reserva, paneles y portada~~, ~~estilos de reserva~~, ~~panel del barbero~~, ~~descansos~~, ~~comisiones por cita~~ | Hecho por A | ✓ |
| **Protecciones Ley 1581** | Permiso de WhatsApp, anonimizar al eliminar, registro de cambios, aviso en notas | | Propuesto; falta el visto bueno |
| **Prueba manual completa** | Recorrer el negocio demo, el panel del barbero y el Super Admin con los 3 estilos; confirmar R8 | Lo mismo en celular (375 px) | Pendiente |
| **Cierre** | Resolver los puntos Alta de `pormejorar.md`, revisión del encargado y PR de `develop` a `main` | | En curso |

**Orden sugerido:**
1. Llevar al encargado las decisiones de §5: mejoras que cambian la spec, el borrador de las condiciones de uso, las cuentas del equipo, las protecciones de la Ley 1581 y los estilos por plan.
2. Hacer la prueba manual completa con `docs/PRUEBA-MANUAL.md`, en computador y celular, con los tres estilos.
3. Revisar los puntos Alta de `pormejorar.md` que quedan: servidor de producción, imágenes en producción, cifrado del 2FA y WhatsApp real.
4. Abrir el PR de `develop` a `main` para la revisión del encargado.

---

## 7. Riesgos y alertas

1. **PRs que se van a `main`.** El #5, el #28 y el #44 (S8) se mezclaron en `main` por error. Las tres veces `main` se devolvió a M0; con el #44, S8 entró a `develop` por un PR nuevo (#45).
   - Desde el 2026-11-11 la rama por defecto de GitHub es `develop`, así que los PR nuevos ya la proponen como base.
   - Al abrir un PR, confirmar igual que la base sea `develop`.
   - Conviene proteger `main` en Settings → Branches (PR con aprobación obligatoria).
2. **2FA.** Ya está encendido. Cada quien debe poner `REQUIRE_TWO_FACTOR=1` en su `.env` local; el Super Admin activa el 2FA con una app de autenticación en su siguiente login. Si se pierde el celular: `docker compose exec api python manage.py reset_2fa --email <correo>`. Por el 2FA, el agente no puede entrar solo al Super Admin para probar pantallas: las prueba con tests de componente.
3. **Migraciones nuevas.** Después de mezclar #73 hay que correr `migrate` (`tenancy.0004_tenant_public_style`). Avisar a Yehiron.
4. **Claves foráneas entre negocios.** RLS impide *ver* datos de otro negocio pero no *enlazarlos*. Cada `services.py` busca los ids recibidos dentro del negocio activo antes de usarlos.
5. **Servidor de desarrollo.** `runserver` no sirve para producción, y cada conexión SSE ocupa un hilo (`pormejorar.md` §4).
6. **Pruebas que dependen de la hora.** Toda prueba con "hoy" o "ayer" debe usar la fecha local del negocio, no la UTC (pasó con R7 y con la separación por día de Citas).
7. **Formato y saltos de línea.**
   - En Windows, `core.autocrlf` y Prettier dejan muchos archivos "modificados" solo por los saltos de línea.
   - Antes de un commit, se agregan solo los archivos con cambios reales: `git diff --ignore-cr-at-eol --numstat`.
   - El CI corre `prettier --check` sobre lo que está en el commit. Un archivo editado a mano después de pasar Prettier lo hace fallar (pasó con `index.css` en #62).
8. **CI de punta a punta.**
   - La descarga de Chromium a veces falla por la red del runner. Ya hay caché y reintentos.
   - Si un cambio de pantalla rompe la prueba, revisar los selectores de `frontend/e2e/`. El campo de contraseña se busca con `exact: true`, porque el botón del ojo («Mostrar contraseña») también contiene la palabra.
   - En local, Playwright necesita `PW_CHANNEL=chrome` para usar el Chrome instalado.
   - Vitest 5 guarda en `node_modules/.vitest-cache` la lista de archivos de traducción. Si una prueba no ve un archivo nuevo, borra esa carpeta.
9. **Docker Desktop en Windows** se apaga con frecuencia (pasó varias veces esta semana). Si la app no responde: abrir Docker Desktop, esperar a que arranque y correr `docker compose up -d`. Si aparece el error de `dockerInference`: Quit, volver a abrir y, si sigue, `wsl --shutdown`.
10. **Imágenes en producción.** Falta definir cómo se sirven los archivos subidos (`pormejorar.md` §34).
11. **WhatsApp real.** Necesita plantillas aprobadas por Meta y credenciales cifradas por negocio (`pormejorar.md` §36 y §37). Hasta entonces se usa `FakeProvider`.
12. **Datos de clientes.** Hoy el personal puede marcar el permiso de WhatsApp y "Eliminar" solo oculta al cliente. Ver las protecciones propuestas en §5 antes de usar la plataforma con clientes reales.

---

## 8. Documentos de referencia

| Documento | Para qué |
|---|---|
| [`docs/SPEC-FASE-1-MVP.md`](docs/SPEC-FASE-1-MVP.md) | Qué se construye (la fuente de verdad) |
| [`docs/REPARTO.md`](docs/REPARTO.md) | Quién hace qué y reglas para no chocar |
| [`docs/OPERACION.md`](docs/OPERACION.md) | Copias de seguridad, restauración y logs |
| [`docs/PRUEBA-MANUAL.md`](docs/PRUEBA-MANUAL.md) | Lista para la prueba manual completa y cómo crear cuentas del equipo |
| [`CHANGELOG.md`](CHANGELOG.md) | Qué entró en cada hito y en cada PR, con detalle |
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
| R3 | Un solo servicio por categoría marcada (un corte por cita, pero corte + barba o cejas sí) y un cliente sin citas cruzadas | A y B | Fase 1 | ✓ #41; por defecto en todas las categorías desde #52 |
| R4 | Foto de presentación de cada barbero | B | Fase 1 | ✓ |
| R5 | Especialidad de cada barbero en la reserva | A y B | Fase 1 | ✓ #32, #33 |
| R6 | Calificación por barbero | — | **Fuera de alcance** (§12: reseñas) | Para el encargado |
| R7 | Calendario con colores: disponible, lleno, cerrado | A y B | Fase 1 | ✓ #32, #33 |
| R8 | Solo horas libres, sin mostrar quién reservó | — | Ya funcionaba desde M5 | Confirmar en la prueba manual |
| R9 | Todo el flujo en una ventana, con menos pasos (de 5 a 3) | B (hecha por A) | Fase 1 | ✓ #46 |
| R10 | Agregar la cita al wallet del celular | — | **Fuera de alcance**. Hecho a cambio: «Tu cita» se ve como tarjeta de billetera (#66), sin pase de Apple o Google. Alternativa pendiente: botón "Agregar al calendario" con `.ics` | Para el encargado |

### Super Admin

| # | Mejora | Quién | Alcance | Estado |
|---|---|---|---|---|
| S1 | Selector de idioma solo en el sitio de cada negocio | B | Fase 1 | ✓ #38; **retirado en #60**: ya no hay selector en ninguna pantalla |
| S2 | Tipo de negocio con selección múltiple | A y B | **Cambia la spec** (§1: "un campo `vertical`") | Para el encargado |
| S3 | Quitar zona horaria y moneda del alta | B | Fase 1 | ✓ #38 |
| S4 | Quitar el idioma del alta | B | Fase 1 | ✓ #38 |
| S5 | Datos del propietario: documento, NIT y teléfono (la contraseña sigue siendo temporal, por seguridad) | A y B | Fase 1 | ✓ #34 |
| S6 | Resumen de la plataforma: total de negocios, activos, suspendidos, nuevos | B (hecha por A) | Fase 1 | ✓ #43 |
| S7 | Soporte con tickets | — | **Nuevo módulo, no está en la spec** | Fase siguiente |
| S8 | Términos y condiciones de la plataforma | B (hecha por A) | Fase 1 (texto estático) | ✓ #45 (borrador para revisar con abogado) |
| S9 | Pagos de la suscripción | — | **Fuera de alcance** (§1 y §12) | Fase siguiente |
| S10 | Uso del sistema por negocio | A y B | Fase 1 | ✓ #35 |
| S11 | Integraciones por negocio (WhatsApp y correo) | B | Fase 1; wallet fuera de alcance | ✓ #40 |
| S12 | Monitoreo: errores, copias y auditoría | A y B | Fase 1 (M10) | Copias y auditoría ✓ #36; Sentry pendiente de aprobación |

---

## 11. Seguridad, rediseño y producto (2026-11-11 a 2026-11-18)

Todo lo hizo el frente A (Diego), también lo de pantallas, con permiso. Cada PR tiene su entrada en el `CHANGELOG.md`.

### Seguridad y documentación

| PR | Qué cambió |
|---|---|
| #47 | `progress.md` al día con S6, S8 y R9 |
| #48 | 2FA reactivado en desarrollo (`REQUIRE_TWO_FACTOR=1`) |
| #49 | **Códigos de recuperación del 2FA:** 10 de un solo uso, guardados con SHA-256, se regeneran en `/seguridad` y se pueden descargar (`POST /auth/2fa/recovery-codes/`) |
| #50 | `docs/PRUEBA-MANUAL.md` (lista para la prueba manual completa) y `pormejorar.md` §39 (cuentas del equipo desde el panel) |

### Reserva pública

| PR | Qué cambió |
|---|---|
| #51 | Rediseño de la reserva con el estilo de la referencia: resumen fijo arriba, pasos claros y botón principal siempre a mano |
| #52 | "Uno por categoría" encendido por defecto en todas las categorías; **"Reservar otra cita para alguien más"** (campo `attendee_name`, una persona no puede tener dos citas cruzadas, pero un papá sí reserva para él y su hijo a la misma hora) |
| #53 | **Cancelar la cita desde la confirmación**, hasta 1 hora antes (nuevo valor por defecto de `cancel_min_hours`) |
| #56 | Botones del sitio público con efecto vidrio al pasar el cursor; "Reservar otra cita" como botón |
| #61 | **Portada a pantalla completa** con un celular que enseña a reservar paso a paso; el sitio público pasa a un estilo fijo blanco con vidrio y verde metalizado |
| #65 | **Ojo para ver la contraseña** en todos los campos; **mano** al pasar el cursor por los botones en toda la app; **ventana de reserva animada** (entra flotando, pasos escalonados, opciones que rebotan, sello de confirmación) y sin barra de desplazamiento; la prueba e2e busca el campo «Contraseña» exacto |
| #66 | **«Tu cita» como tarjeta de billetera** en verde metalizado: chip dorado, destello holográfico, inclinación 3D con el mouse; «Cancelar mi cita» se enciende en óxido rojo |
| #69 | **Portada en esmeralda metalizado:** fondo verde oscuro con luces, nombre con brillo, el celular hace la reserva solo y **la tarjeta sale del celular** al confirmar; pasos en franja crema; servicios con hover metalizado |
| #73 | **Tres estilos de reserva** que elige el Super Admin: Esmeralda, Barbería clásica (poste de barbero girando, cuero y latón) y Salón de belleza (rosa piel, perla y oro rosa); campo `Tenant.public_style` con migración; «Automático» según el tipo de negocio |

### Paneles

| PR | Qué cambió |
|---|---|
| #54 | **Super Admin con vidrio** en blanco, negro y verde metalizado |
| #55 | Acciones de riesgo con **ventana de confirmación** y color óxido; login y condiciones de uso del Super Admin con vidrio |
| #57 | Panel del negocio con vidrio y rojo metalizado; página **Inicio** con los números del mes |
| #58 | Sin selector de idioma en el panel del negocio; **agenda más legible** (bloques por estado, líneas de media hora, sin barras internas) |
| #59 | Panel del negocio en púrpura metalizado suave con **barra lateral de vidrio líquido**; login del negocio con el mismo vidrio |
| #60 | **Sin selector de idioma en ninguna pantalla** (login, sitio público, reserva, condiciones); el idioma lo pone el negocio |
| #62 | La barra lateral del panel **se desplaza** con zoom o en pantallas bajas; luego sin barra gris, con bordes que se desvanecen y una flecha de vidrio; más vidrio líquido en la barra oscura del Super Admin; arreglo de formato de Prettier para el CI |
| #63 | **Más movimiento:** opciones del menú que entran escalonadas y se corren al pasar el cursor, barra superior en vidrio líquido, botones que suben y cambian de color (los «Eliminar» se encienden en rojo, variante `dangerGhost`) |
| #64 | **Panel del dueño en café metalizado, cuero y blanco** (reemplaza el púrpura); tarjeta de ventas del mes en cuero |
| #74 | El selector de estilo del Super Admin marca la opción elegida (anillo verde y check) y la guardada («Guardado»), con enlace para ver la página de reservas |

### Agenda, citas, horarios y comisiones

| PR | Qué cambió |
|---|---|
| #67 | **Horarios con jornada y descansos:** caja ámbar por descanso, barra del día, validaciones; en la reserva aparece la fila **«Descanso 13:00 – 14:00 · no se puede reservar»** (endpoint `GET /api/v1/public/availability/breaks/`) |
| #68 | Horarios **avisa los cambios sin guardar** (barra ámbar pegada abajo y aviso del navegador al salir) |
| #70 | **Citas separadas por profesional** con pestañas por persona |
| #71 | **Comisiones con una fila por cita:** servicios juntos, ajustes sumados («Incluye ajuste +2.000»), detalle por servicio al abrir la fila; CSV por cita (`group=appointment`) |
| #72 | **Agenda con las canceladas a la vista** (atenuadas y tachadas); en Citas, separación **por día** con pendientes; el barbero ya no ve pestañas |

### Fuera del repositorio

- **Cuenta de barbero en el demo local:** Andrés (`andres@demo-barbershop.test`), rol profesional, enlazado a su perfil. La contraseña está en `.local/credenciales-barbero.txt`.
- **Video para Instagram:** `.local/barberia-demo-historia.mp4` (§5).
- **Mockups de diseño aprobados:** Super Admin verde, panel púrpura y luego café, portada esmeralda, Barbería clásica y Salón de belleza. Quedaron como imágenes de trabajo, no en el repositorio.
