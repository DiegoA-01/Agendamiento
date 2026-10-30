# Changelog

## M2 — Accounts

- App `apps.accounts`: modelo `User` propio (`AUTH_USER_MODEL`), roles `superadmin`, `owner`, `admin`, `receptionist`, `professional`. Correo único por tenant (sin distinguir mayúsculas) y único global entre Super Admins; solo el superadmin carece de tenant (restricción en base de datos).
- Autenticación por sesión con cookie HttpOnly + CSRF (decisión en `docs/adr/0001-autenticacion-por-sesion.md`). Sin sesión: 401; sin permiso: 403.
- Endpoints bajo `/api/v1`: `auth/csrf/`, `auth/login/`, `auth/logout/`, `auth/2fa/setup/`, `auth/2fa/confirm/`, `auth/password-reset/`, `auth/password-reset/confirm/`, `me/` (usuario, rol, tenant, tema y módulos habilitados).
- El login siempre se resuelve dentro del tenant del host (`admin.` = Super Admin). Mismo error y tiempo para correo inexistente y contraseña mala. `TenantSessionGuardMiddleware` descarta una sesión usada en un host que no es de su usuario.
- 2FA TOTP (RFC 6238) con la librería estándar, sin dependencias nuevas. Obligatorio para el Super Admin; opcional para el propietario (si lo activa, se le exige). Un código no se puede reutilizar.
- Recuperación de contraseña: siempre responde 204 (no revela correos), enlace de un solo uso por tenant; cambiar la contraseña cierra las sesiones abiertas.
- Matriz de permisos de la spec §5 en `accounts/permissions.py` (`can`, `scope_for`, `permission_for`) y cubierta por tests parametrizados por rol contra una tabla escrita a mano desde la spec.
- Formato de error único `{code, detail, fields}` para toda la API (`config/api.py`). Toda vista exige sesión por defecto.
- Comando `create_superadmin` para crear el primer Super Admin.
- OpenAPI actualizado con los endpoints de autenticación.
- **Cambio de entorno:** `AUTH_USER_MODEL` cambia, hay que recrear la base de desarrollo: `docker compose down -v`.
- Contraseñas con **Argon2id** (dependencia nueva aprobada: `argon2-cffi`). Perfil mínimo de OWASP (19 MiB, 2 pasadas, 1 hilo): ~26 ms y ~20 MB por login, medido en Docker; los valores por defecto de Django usaban ~100 MB. PBKDF2 sigue en `PASSWORD_HASHERS` para verificar hashes viejos; Django los convierte solo al próximo login. Parámetros en `config/hashers.py`.
- Pendiente / decisiones abiertas: `totp_secret` en texto plano (cifrado en reposo requiere una librería de cifrado, M10); límite de intentos de login y 2FA obligatorio para el propietario (M10).
- Frontend: el cliente debe releer la cookie `csrftoken` tras el login (Django la rota).

## M1 — Tenancy

- App `apps.tenancy`: `Plan`, `Tenant`, `Domain`, `TenantModule` (UUID, fechas UTC, borrado lógico).
- `TenantMiddleware`: resuelve el tenant por `Host` (`ContextVar`), `admin.<BASE_DOMAIN>` = contexto Super Admin, host desconocido o dominio sin verificar = 404. `/healthz/` y `/api/schema/` no dependen de tenant.
- `TenantOwnedModel`: manager por defecto filtrado por tenant (sin tenant activo no devuelve nada), `all_tenants` explícito, `save()` asigna el tenant y rechaza escribir en otro.
- RLS de PostgreSQL: `apps.tenancy.rls.enable_rls(tabla)` para las migraciones de cada modelo de negocio. Política con `FORCE` y `WITH CHECK`; modo plataforma (`platform_context`) para Super Admin y tareas globales.
- La app se conecta con un rol **sin superusuario ni BYPASSRLS** (`APP_DB_USER`); PostgreSQL ignora RLS para superusuarios. Un test falla si el rol tuviera esos privilegios.
- `@requires_module("x")` y servicios públicos (`services.py`). Slugs reservados rechazados siempre en `save()`.
- Tests: aislamiento entre dos tenants (endpoint, manager sin filtrar, SQL crudo, insert/update/delete cruzados), middleware, modelos y módulos.
- Pendiente para M2: `/api/me/` (necesita usuario y rol). Los tenants se crean desde el Super Admin (M3).
- **Cambio de entorno:** hay que recrear el volumen de PostgreSQL para crear el rol de la app: `docker compose down -v && docker compose up --build`.

## M0 — Base del repo

- Estructura `backend/` (Django 5 + DRF + drf-spectacular + Celery) y `frontend/` (React + Vite + TS + Tailwind).
- Settings `base`, `dev`, `prod`; logs JSON estructurados; i18n es/en en backend (`LocaleMiddleware`).
- Healthcheck `GET /healthz/` (verifica PostgreSQL y Redis) y esquema OpenAPI en `/api/schema/`.
- Frontend con i18next (es/en), TanStack Query, react-router, Tailwind y página inicial que consulta el healthcheck.
- Docker Compose: `api`, `worker`, `beat`, `web`, `postgres` (con `btree_gist`), `redis`, `caddy`.
- CI en GitHub Actions: ruff, mypy, pytest (backend); eslint, prettier, vitest, build (frontend).
- Sin migraciones propias: aún no hay modelos de negocio (empiezan en M1).
