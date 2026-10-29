# SPEC Fase 1 (MVP) — SaaS de agendamiento para barberías y salones

Documento para alimentar a Claude Code. Alcance: **solo Fase 1**. Todo lo demás está en "Fuera de alcance".
Fuente de producto: documento "SaaS de Agendamiento para Barberías y Salones — Especificación de Producto".

## 0. Reglas para el agente (copiar a CLAUDE.md)

- Idioma de UI: español (default) e inglés; todo texto visible pasa por i18n desde el primer commit. Código, nombres de modelos y endpoints en inglés.
- Nunca escribir una consulta de negocio sin filtrar por tenant. Todo modelo de negocio hereda de `TenantOwnedModel`.
- Fechas en UTC en base de datos; conversión a la zona horaria del tenant solo en serialización y UI.
- Dinero como `DecimalField(max_digits=12, decimal_places=2)`; moneda por tenant (default COP). Nunca float.
- Cada módulo es una app Django independiente; una app no importa modelos de otra salvo por su `services.py` público.
- Toda lógica de negocio en `services.py`, no en vistas ni serializers.
- Cada tarea termina con tests pasando (`pytest`) y migraciones incluidas.
- No agregar dependencias fuera de la lista de la sección 2 sin pedirlo.
- No implementar nada de la sección 12 (fuera de alcance).

## 1. Decisiones tomadas (confirmar o corregir antes de codificar)

| Tema | Decisión asumida |
| --- | --- |
| Hosting | Incluido en la suscripción; no se modela en el producto |
| Cliente final | Reserva como invitado (sin cuenta); se identifica por celular |
| Anticipos / Wompi | Fuera del MVP; el modelo deja el campo `deposit_required` sin usar |
| Wallet | Fuera del MVP |
| Tiempo real | SSE para refrescar la agenda del dashboard |
| Idiomas | es y en |
| Aislamiento | Base compartida + `tenant_id` + RLS de PostgreSQL |
| Verticales | Un campo `vertical` en Tenant (`barbershop`, `salon`, `nails`, `spa`) que solo cambia etiquetas y servicios de ejemplo |
| Precios del software | Fuera de alcance; el plan solo habilita módulos y límites |

## 2. Stack

- Backend: Python 3.12, Django 5, Django REST Framework, drf-spectacular (OpenAPI), psycopg 3.
- Tareas: Celery + Redis (broker y caché), Celery Beat.
- DB: PostgreSQL 16 con extensión `btree_gist`.
- Tiempo real: SSE (endpoint streaming sobre Redis pub/sub).
- Imágenes: Pillow; el backend convierte toda imagen subida a WebP y genera variantes (thumb 200 px, medium 800 px, large 1600 px).
- Frontend: React 18 + TypeScript + Vite + Tailwind + TanStack Query + react-router + i18next + React Hook Form + Zod.
- Infra: Docker Compose (api, worker, beat, web, postgres, redis, caddy). Caddy emite TLS automático.
- Calidad: pytest, pytest-django, factory_boy, ruff, mypy (backend); vitest, eslint, prettier (frontend); GitHub Actions.

## 3. Estructura del repositorio

```
/backend
  /config            settings (base, dev, prod), urls, celery.py
  /apps
    /tenancy         Tenant, Domain, Plan, TenantModule, middleware, RLS
    /accounts        User, Role, auth, recuperación de contraseña, 2FA (superadmin)
    /platform_admin  API y vistas del Super Admin
    /company         datos de empresa, tema, términos, locations
    /catalog         Category, Service, Professional, Resource, ProfessionalService
    /scheduling      WorkingHours, TimeBlock, motor de disponibilidad
    /booking         Customer, Appointment, AppointmentItem, estados, API pública
    /commissions     CommissionEntry, cálculo y reportes
    /notifications   plantillas, NotificationLog, canales email y whatsapp
    /reports         ventas y reservas con filtros
    /media           subida y conversión a WebP
  /tests
/frontend
  /src
    /app             router, providers
    /features        platform, dashboard, booking, auth
    /shared          api client, i18n, ui, theme
/docker-compose.yml
/Caddyfile
```

## 4. Multi-tenancy

1. `Tenant`: `id (uuid)`, `name`, `slug` (único, subdominio), `vertical`, `timezone` (default `America/Bogota`), `currency` (default `COP`), `language` (default `es`), `status` (`active`, `suspended`), `plan` (FK), `theme` (JSON de tokens), `created_at`.
2. `Domain`: `tenant`, `host` (único), `kind` (`subdomain`, `custom`), `verified` (bool), `verification_token`.
3. Middleware `TenantMiddleware`: lee `Host`, busca `Domain` verificado, guarda el tenant en un `ContextVar`. Host `admin.<BASE_DOMAIN>` = contexto Super Admin (sin tenant). Host desconocido = 404.
4. `TenantOwnedModel` (abstracto): campo `tenant` FK, manager por defecto que filtra con el `ContextVar`, y `save()` que asigna el tenant. Un manager `all_tenants` explícito para el Super Admin y tareas Celery.
5. RLS: por cada tabla de negocio, política `USING (tenant_id = current_setting('app.current_tenant')::uuid)`. El middleware ejecuta `SET LOCAL app.current_tenant` por petición/transacción. Los workers Celery lo fijan al inicio de cada tarea.
6. Subdominios reservados (rechazar como slug): `admin, api, www, app, mail, static, media, support, status`.
7. Módulos: `TenantModule(tenant, module_key, enabled)`. Claves MVP: `booking`, `commissions`, `reports`, `notifications_whatsapp`. Decorador `@requires_module("x")` en vistas y endpoint `/api/me/` que devuelve módulos habilitados para que el frontend oculte la UI.
8. Tema: `theme = {primary, secondary, background, surface, text}` (hex). Lo edita solo el Super Admin. El frontend lo aplica como variables CSS. Validar contraste de texto sobre fondo (WCAG AA) al guardar.
9. Prueba obligatoria: test que crea dos tenants y verifica que ningún endpoint devuelve datos del otro, incluso con RLS activo y manager sin filtrar.

## 5. Roles y permisos

Roles: `superadmin` (sin tenant), `owner`, `admin`, `receptionist`, `professional`.

| Recurso / acción | owner | admin | receptionist | professional |
| --- | --- | --- | --- | --- |
| Datos de empresa, tema (no), términos | editar | ver | — | — |
| Empleados y servicios | CRUD | CRUD | ver | ver propio |
| Horarios y bloqueos | todos | todos | todos | solo propios |
| Citas | todas, CRUD | todas, CRUD | todas, CRUD | solo propias (ver, completar, no_show) |
| Comisiones y reportes | ver | ver | — | solo sus comisiones |
| Plan y módulos | ver | — | — | — |

Implementar con `permissions.py` por app y tests parametrizados por rol. El profesional nunca recibe citas de otro profesional ni en listados ni por id (404, no 403).

## 6. Modelo de datos (Fase 1)

Convenciones: `id` UUID, `created_at`, `updated_at`, `deleted_at` (borrado lógico) salvo en logs.

**User**: `email` (único por tenant; único global para superadmin), `password`, `full_name`, `phone`, `role`, `tenant` (null solo superadmin), `is_active`, `totp_secret` (solo superadmin/owner).

**Company** (1:1 Tenant): `legal_name`, `trade_name`, `tax_id` (NIT), `address`, `city`, `phone`, `email`, `logo` (media), `terms_html`, `privacy_html`, `cookies_html`, `social_links` (JSON).

**Location**: `name`, `address`, `is_default`. MVP usa una sede; el modelo ya la incluye.

**ServiceCategory**: `name`, `sort_order`.

**Service**: `category`, `name`, `description`, `duration_min`, `buffer_min` (default 0), `price`, `is_active`, `requires_resource` (bool), `image`.

**Professional**: `user` (nullable), `location`, `display_name`, `bio`, `photo`, `specialties` (M2M a `Specialty`), `default_commission_pct`, `is_active`, `accepts_online_booking` (bool), `rating_avg` (campo reservado, sin uso en MVP).

**ProfessionalService**: `professional`, `service`, `price_override` (null), `commission_pct_override` (null), `duration_override_min` (null).

**Resource** (puesto de trabajo): `location`, `name`, `kind`, `is_active`. `Service.requires_resource` exige un recurso libre además del profesional.

**WorkingHours**: `professional`, `weekday` (0-6), `start_time`, `end_time`. Varias filas por día permiten descanso.

**TimeBlock** (bloqueo de agenda): `professional` o `resource`, `start_at`, `end_at`, `reason`. Crear bloqueo que choque con citas existentes devuelve 409 con la lista de citas en conflicto.

**Customer**: `full_name`, `email`, `phone` (normalizado E.164), `birthday` (null), `notes`, `marketing_consent` (bool), `data_consent_at` (datetime, obligatorio). Unicidad `(tenant, phone)`.

**Appointment**: `customer`, `professional`, `resource` (null), `location`, `start_at`, `end_at`, `status`, `source` (`web`, `dashboard`), `price_total`, `cancel_token` (aleatorio, para enlace público), `cancelled_at`, `cancel_reason`, `created_by` (user, null si web).

- Restricción de exclusión (PostgreSQL) para evitar doble reserva por profesional:
  `ExclusionConstraint(expressions=[(TsTzRange("start_at","end_at"), "&&"), ("professional","=")], condition=Q(status__in=["pending","confirmed","in_progress"]))`.
- Misma restricción sobre `resource` cuando no es null.

**AppointmentItem**: `appointment`, `service`, `professional` (permite varios profesionales en el futuro; MVP = el mismo), `price_charged`, `duration_min`, `commission_pct_snapshot`.

**CommissionEntry**: `appointment`, `professional`, `base_amount`, `pct`, `commission_amount`, `business_amount`, `created_at`. Se crea al pasar la cita a `completed`; inmutable (correcciones = entrada de ajuste).

**NotificationLog**: `appointment`, `kind` (`confirmation`, `reminder`, `cancellation`, `reschedule`), `channel` (`email`, `whatsapp`), `to`, `status` (`queued`, `sent`, `failed`), `attempts`, `error`, `sent_at`.

**AuditLog** (plataforma y acciones sensibles): `actor`, `tenant`, `action`, `entity`, `entity_id`, `before`, `after`, `created_at`.

## 7. Estados de la cita

`pending → confirmed → in_progress → completed`
`pending|confirmed → cancelled`
`confirmed → no_show`
`pending|confirmed → rescheduled` (crea una cita nueva enlazada con `rescheduled_from`).

Reglas:
- Reserva pública nace `confirmed` (sin anticipo en MVP). Creada por el dashboard también `confirmed`.
- Solo `completed` genera `CommissionEntry` y cuenta en ventas.
- `cancelled` y `no_show` liberan el hueco (salen de la restricción de exclusión).
- Transiciones inválidas devuelven 409.

## 8. Motor de disponibilidad (`scheduling/services.py`)

Función pública: `get_available_slots(tenant, service_ids, date, professional_id|None) -> list[Slot]`.

Algoritmo:
1. Duración total = suma de `duration_min` (con override del profesional) + `buffer_min` del último servicio.
2. Candidatos de profesional: el indicado, o todos los activos con `accepts_online_booking` que ofrezcan todos los servicios.
3. Por cada candidato: intervalos de `WorkingHours` del día (en la zona del tenant) menos `TimeBlock` menos citas activas.
4. Generar inicios cada `slot_step_min` (config por tenant, default 15) donde quepa la duración total.
5. Si algún servicio `requires_resource`, exigir un `Resource` libre en el rango.
6. Aplicar `min_notice_min` (default 60) y `max_advance_days` (default 60) del tenant.
7. Con "cualquiera": unir slots; asignación por menor número de citas ese día, desempate por orden alfabético. Devolver el profesional asignado solo al confirmar.
8. Agrupar en `morning` (< 12:00), `afternoon` (12:00-17:59), `evening` (≥ 18:00) en hora local.
9. Caché en Redis por `(tenant, professional, date)`, invalidada por señales al crear/cambiar cita, horario o bloqueo.
10. `get_available_days(tenant, service_ids, professional_id|None, month)` para marcar días con disponibilidad.

La creación de cita re-valida el slot dentro de una transacción; si la restricción de exclusión falla responde 409 `slot_taken` con nuevos horarios sugeridos.

## 9. API (prefijo `/api/v1`, JSON, OpenAPI en `/api/schema/`)

Autenticación: sesión con cookie HttpOnly + CSRF para el dashboard (o JWT corto + refresh en cookie; elegir uno y documentarlo). Públicos sin auth pero con rate limit.

**Públicos (tenant por host)**
- `GET /public/company/` — nombre, logo, tema, idioma, términos, vertical, etiquetas.
- `GET /public/services/` — categorías y servicios activos.
- `GET /public/professionals/?service_ids=` — profesionales que ofrecen esos servicios.
- `GET /public/availability/days/?service_ids=&professional_id=&month=YYYY-MM`
- `GET /public/availability/slots/?service_ids=&professional_id=&date=YYYY-MM-DD`
- `POST /public/appointments/` — `{service_ids, professional_id|null, start_at, customer:{full_name,email,phone}, accept_data_policy:true}` → 201 con cita y `manage_url`.
- `GET /public/appointments/{cancel_token}/` y `POST /public/appointments/{cancel_token}/cancel/` — respeta ventana de cancelación del tenant (`cancel_min_hours`, default 2).
- Rate limit: 10 POST/hora por IP y 5 por teléfono; honeypot + captcha activable por config.

**Auth**
- `POST /auth/login/`, `POST /auth/logout/`, `POST /auth/password-reset/`, `POST /auth/password-reset/confirm/`, `GET /me/` (usuario, rol, módulos, tenant, tema).

**Dashboard (autenticado)**
- `company/` GET/PATCH; `locations/` CRUD.
- `categories/`, `services/`, `professionals/`, `resources/` CRUD; `professionals/{id}/services/` asignación con overrides.
- `professionals/{id}/working-hours/` GET/PUT; `time-blocks/` CRUD.
- `appointments/` listar (filtros: rango, profesional, estado, cliente) y crear; `appointments/{id}/` PATCH; acciones `/confirm|start|complete|cancel|no-show|reschedule/`.
- `customers/` CRUD y búsqueda por nombre o teléfono.
- `commissions/` listar con filtros; `reports/sales/` y `reports/bookings/` (ver sección 11).
- `events/` SSE: emite `appointment.created|updated|cancelled` al tenant.

**Super Admin (host `admin.`)**
- `tenants/` CRUD (crear tenant crea Company, Domain subdominio, owner con contraseña temporal y módulos del plan).
- `tenants/{id}/suspend|activate/`, `tenants/{id}/theme/`, `tenants/{id}/modules/`, `tenants/{id}/domains/` (alta de dominio propio + instrucciones CNAME/TXT + `verify/`).
- `plans/` CRUD (nombre, módulos, límites `max_professionals`, `max_locations`).
- `audit-log/` listar.

Errores con formato `{ "code": "slot_taken", "detail": "...", "fields": {} }`. Paginación por cursor en listados largos.

## 10. Notificaciones

- Canales: email (SMTP/SES vía Django `EmailBackend`) y WhatsApp Business Cloud API detrás de una interfaz `WhatsAppProvider` (implementación real + `FakeProvider` para dev/tests).
- Eventos: confirmación inmediata; recordatorio configurable (default 24 h y 2 h antes, Celery Beat); cancelación; reprogramación.
- Plantillas por idioma y por vertical, editables solo por código en MVP. Variables: `{customer_name}`, `{service}`, `{professional}`, `{date}`, `{time}`, `{business}`, `{manage_url}`.
- WhatsApp solo se envía si `customer.marketing_consent` o la cita fue creada por el cliente con consentimiento de contacto; botones: Confirmar, Cancelar, Reprogramar (apuntan a `manage_url`).
- Reintentos con backoff (3 intentos); fallo de WhatsApp cae a email.
- Todo envío escribe `NotificationLog`. Tareas idempotentes (clave `appointment+kind+channel`).

## 11. Comisiones y reportes

- Al `complete`: por cada `AppointmentItem` base = `price_charged`; `pct` = `commission_pct_override` > `Professional.default_commission_pct`; `commission_amount = round(base * pct / 100, 2)`; `business_amount = base - commission_amount`. Guardar snapshot del porcentaje.
- `GET reports/sales/`: filtros `from`, `to`, `professional`, `service`, `category`, `status`; agrupar por `day|week|month`, profesional o servicio; devuelve total ventas, total comisiones, total negocio, número de citas, ticket promedio.
- `GET reports/bookings/`: reservas por mes y por servicio, por profesional, tasa de cancelación y no-show.
- Exportar CSV en ambos.
- El profesional solo ve sus filas.

## 12. Fuera de alcance (no implementar)

Inventario, reseñas, fidelización y cumpleaños automáticos, CRM extendido, Wompi, facturación electrónica, wallet, asesoría de imagen, multi-sede en UI, lista de espera, paquetes, PWA, API pública para terceros, sincronización con Google Calendar, galería de trabajos. El modelo puede dejar hooks, pero sin lógica.

## 13. Frontend (rutas)

- Público (host del tenant): `/` landing mínima con CTA; `/reservar` asistente de 5 pasos (servicios → profesional → fecha → hora → datos y confirmación); `/cita/:token` ver, cancelar; `/terminos`, `/privacidad`, `/cookies`. Banner de cookies. Selector de idioma. Mobile-first; probar 360 px de ancho.
- Dashboard: `/login`, `/recuperar`, `/agenda` (vista día y semana por profesional, con SSE), `/citas`, `/clientes`, `/servicios`, `/equipo`, `/puestos`, `/horarios`, `/reportes`, `/empresa`.
- Super Admin: `/login`, `/empresas`, `/empresas/:id` (datos, tema, módulos, dominios), `/planes`, `/auditoria`.
- Tema por variables CSS leídas de `/public/company/`. Estados vacíos, de carga y de error en cada pantalla. Accesibilidad: foco visible, labels, contraste AA.

## 14. Orden de construcción y criterios de aceptación

| Hito | Entregable | Aceptación |
| --- | --- | --- |
| M0 | Repo, Docker Compose, CI, settings, healthcheck, i18n base | `docker compose up` levanta todo; CI corre lint y tests |
| M1 | Tenancy: Tenant, Domain, middleware, RLS, módulos | Test de aislamiento entre dos tenants pasa; host desconocido da 404 |
| M2 | Accounts: login, reset, roles, `/me/` | Matriz de permisos de la sección 5 cubierta por tests |
| M3 | Super Admin API y UI: empresas, tema, módulos, dominios | Crear tenant produce subdominio funcional y owner que puede entrar |
| M4 | Company + catálogo + equipo + puestos + horarios + bloqueos (API y UI) | CRUD completo con permisos; imágenes se guardan como WebP |
| M5 | Motor de disponibilidad + citas + estados + restricción de exclusión | Prueba de concurrencia: 20 POST simultáneos al mismo hueco crean 1 cita y 19 reciben 409 |
| M6 | Reserva pública (asistente) + gestión por token | Reserva completa en móvil en menos de 60 s; cancelación respeta ventana |
| M7 | Agenda del dashboard con SSE | Una cita creada en la web aparece en la agenda abierta sin recargar |
| M8 | Notificaciones email y WhatsApp (con FakeProvider) | Confirmación y recordatorio registrados en `NotificationLog`; reintentos probados |
| M9 | Comisiones y reportes + CSV | Valores cuadran con casos de prueba calculados a mano |
| M10 | Endurecimiento: rate limits, auditoría, backups, observabilidad, e2e | Playwright cubre el flujo reservar → completar → comisión |

Cada hito se entrega con: migraciones, tests, documentación OpenAPI actualizada y notas en `CHANGELOG.md`.

## 15. No funcionales

- Respuesta de `/public/availability/slots/` bajo 300 ms con caché caliente (objetivo, medir y ajustar).
- Backups diarios de PostgreSQL fuera del servidor, cifrados; restauración probada antes de producción.
- Secretos solo por variables de entorno; credenciales de integraciones por tenant cifradas en reposo.
- Logs estructurados JSON; Sentry para errores.
- Cumplimiento Ley 1581: casilla de autorización sin marcar en la reserva, registro `data_consent_at`, política de tratamiento por empresa, endpoints internos para consultar, corregir y eliminar datos de un cliente. Validar con abogado antes del lanzamiento.

## 16. Datos semilla

Comando `manage.py seed_demo --vertical barbershop|salon|nails` que crea un tenant demo con 3 profesionales, 6 servicios de ejemplo, horarios L-S 9:00-19:00 y citas de muestra. Usar en desarrollo y en e2e.
