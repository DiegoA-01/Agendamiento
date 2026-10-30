# Changelog

feat/m4-media
## M4 — Imágenes (app `media`)

- `POST /api/v1/media/` (multipart, campo `file`): sube una imagen JPG, PNG o WebP y responde `201` con `id`, tamaño original y las URLs de las tres variantes. Solo para quien puede editar la empresa o el catálogo (propietario y administrador) y solo en el host de un negocio.
- Toda imagen se convierte a **WebP** en tres tamaños: `thumb` 200 px, `medium` 800 px y `large` 1600 px (lado mayor). Nunca se agranda una imagen pequeña. Se respeta la transparencia.
- Se aplica la rotación de la cámara y se **descarta el EXIF**, que puede traer la ubicación GPS de la foto.
- Rechazos con el formato de error estándar: `invalid_image`, `unsupported_image` (GIF, BMP…), `file_too_large` (más de 10 MB, `MEDIA_MAX_UPLOAD_BYTES`) e `image_too_large` (más de 40 megapíxeles, protección contra bombas de descompresión).
- Servicios públicos para otras apps: `upload_image`, `get_media` (solo imágenes del tenant activo, para validar el id que manda el cliente) y `media_urls`.
- En desarrollo Django sirve `/media/...` y Caddy enruta esas rutas a la API. En producción falta servirlas desde Caddy (`pormejorar.md` §34).
- Sin dependencias nuevas (Pillow ya estaba en la lista).

feat/fase0-frontend
## Fase 0 — Contratos compartidos (frontend)

Base del panel del negocio para trabajar M4 a M10 en paralelo sin choques (ver `docs/REPARTO.md`).

- **Traducciones por área**: `locales/<idioma>/<area>.json` (`common`, `auth`, `platform`, `dashboard`). Un archivo nuevo se carga solo (`import.meta.glob`), sin registrarlo en ningún lado. Las claves no cambian (`t("tenants.x")` sigue igual). Un test falla si dos archivos usan la misma clave de primer nivel o si `es` y `en` no tienen los mismos archivos.
- **Panel del negocio**: layout con el tema del negocio, menú lateral (botón "Menú" en el celular) y las rutas de la spec §13: `/agenda`, `/citas`, `/clientes`, `/servicios`, `/equipo`, `/puestos`, `/horarios`, `/reportes`, `/empresa`. Cada sección es una página provisional en su propia carpeta (`features/dashboard/<seccion>/`) y en su propio paquete (lazy). Cada frente reemplaza las suyas sin tocar `App.tsx`.
- **El menú depende del rol y de los módulos** (matriz de la spec §5, en `features/dashboard/navigation.ts`, con tests por rol). Entrar por URL a una sección no permitida lleva al inicio del panel. `/panel` lleva a la primera sección visible.
- Se elimina el panel provisional de M3. Cerrar sesión pasa a `useSignOut`, compartido con el panel del Super Admin.
- Probado en el navegador como propietario y como profesional, en escritorio y a 375 px (sin desbordamiento horizontal).
develop

## Fase 0 — Contratos compartidos (backend)

Base para trabajar M4 a M10 en paralelo sin choques (ver `docs/REPARTO.md`).

- Apps nuevas registradas en `INSTALLED_APPS` y en `config/urls.py` (con `urls.py` vacíos): `media`, `catalog`, `scheduling`, `booking`, `commissions`, `notifications`, `reports`. También `django.contrib.postgres` (parte de Django, no es dependencia nueva). Desde aquí nadie necesita tocar esos dos archivos.
- Modelos y migraciones de la spec §6, todos con `TenantOwnedModel` y RLS:
  - `media`: `MediaFile` (registro de la imagen y sus tres variantes WebP; la conversión llega en M4).
  - `company`: `Location` (una sola sede por defecto por tenant) y `Company.logo`.
  - `catalog`: `ServiceCategory`, `Service`, `Specialty`, `Professional`, `ProfessionalSpecialty` (tabla intermedia propia para que también tenga tenant y RLS), `ProfessionalService` con overrides, `Resource`.
  - `scheduling`: `WorkingHours` y `TimeBlock` (exactamente uno de profesional o puesto).
  - `booking`: `Customer` (celular único por tenant), `Appointment` con las dos restricciones de exclusión anti doble reserva (profesional y puesto; solo estados activos; límites `[)`), y `AppointmentItem`. La migración crea `btree_gist` si falta.
  - Dinero en `DecimalField(12, 2)`, porcentajes en `DecimalField(5, 2)` con rango 0 a 100, y restricciones `CHECK` de duración y precio.
- `tests/factories.py` se reparte en `tests/<app>/factories.py`. Nueva base `TenantOwnedFactory`, que crea cada registro dentro del contexto del tenant para que RLS acepte el INSERT, y una factory por modelo nuevo.
- Test que falla si una tabla de negocio no activa RLS, más tests de aislamiento entre tenants para todas las tablas nuevas, de la restricción de exclusión y de los `CHECK`.
- `docker/postgres/init.sh` ahora es ejecutable en git: en macOS y Linux no se creaba el rol de la app y los tests fallaban por contraseña.
- Archivos subidos en `MEDIA_ROOT` (`backend/mediafiles/`, ignorado en git).
- **Cambio de entorno:** hay que aplicar las migraciones nuevas (`docker compose up -d api` las aplica al arrancar).
- Pendiente para M5 (frente A): la configuración de agenda por tenant (`slot_step_min`, `min_notice_min`, `max_advance_days`, `cancel_min_hours`).
develop

## M3 — Super Admin

- API del Super Admin bajo `/api/v1` (solo rol `superadmin` y solo en el host `admin.`; CSRF en escrituras): `tenants/` (CRUD, listado por cursor con búsqueda y filtro de estado), `tenants/{id}/suspend|activate/`, `theme/`, `modules/`, `domains/` (alta, `verify/`, baja), `plans/` (CRUD) y `audit-log/` (por cursor, con filtros).
- **Alta de un negocio en una sola operación atómica**: tenant, subdominio verificado, tema por defecto, módulos del plan, `Company` y propietario con contraseña temporal. Si falla un paso no queda nada a medias. La contraseña temporal se muestra una sola vez y no se guarda ni se audita; el propietario debe cambiarla en su primer ingreso (`must_change_password`).
- Nueva app `company` con la tabla `Company` (1:1 con el tenant): la primera tabla de negocio con RLS real (`enable_rls` en su migración, probada).
- Nueva app `platform_admin` con `AuditLog`: cada acción del Super Admin deja constancia (antes/después, sin secretos). Una acción fallida no deja entrada.
- Tema con validación de contraste WCAG AA: el texto debe tener al menos 4.5:1 sobre el fondo y sobre la superficie. El frontend avisa en vivo; el servidor decide.
- Dominios propios: se piden registros `TXT` (prueba de propiedad, obligatorio) y `CNAME` (informativo). Verificación por DNS sobre HTTPS con la librería estándar (sin dependencias nuevas); en tests el DNS es falso y nunca sale a internet. Ver `pormejorar.md` §26.
- Suspender un negocio bloquea su host con `403 tenant_suspended` sin borrar datos. Eliminar es lógico. Editar un plan no cambia los módulos de los negocios existentes salvo `apply_to_tenants`; cambiar el plan de un negocio sí reinicia sus módulos.
- Cuentas: `POST /auth/password-change/` (cierra las demás sesiones y mantiene la actual), `must_change_password` en `/me/` y comando `reset_2fa` para el Super Admin que pierde el celular.
- **Corrección de M1**: `tenant_context` ya no tapa el error real si la transacción quedó rota (test de regresión).
- OpenAPI sin avisos y validado en el CI (`spectacular --validate --fail-on-warn`); describe la autenticación por cookie y CSRF.
- Frontend (React): login con los pasos de 2FA (clave manual, sin QR), cambio forzado de contraseña, recuperación de contraseña, y panel del Super Admin (empresas, nueva empresa, detalle con datos, tema con vista previa y contraste, módulos y dominios, planes y auditoría). Textos en español e inglés, estados de carga, vacío y error, y teclado y etiquetas accesibles. El panel va en un paquete aparte (lazy). Sin desbordamiento horizontal a 375 px. Probado de punta a punta en el navegador.
- Panel provisional del negocio en `/panel` (aplica el tema del negocio); el panel real llega en M4.
- Pruebas: 362 en el backend (incluye la matriz de seguridad de las 21 rutas) y 42 en el frontend.
- **Interruptor `REQUIRE_TWO_FACTOR`** (por defecto encendido). Apagado solo en desarrollo (`.env` y `.env.example` lo traen en 0) para probar sin autenticador: el login entra solo con contraseña, incluso a quien ya tenga 2FA activo. Al arrancar deja un aviso en el log (`DESACTIVADA`). `config/settings/prod.py` **se niega a arrancar** si está apagado, y los tests siempre corren con él encendido. **Reactivar antes de entregar** (`pormejorar.md` §33).
- Sin dependencias nuevas.
- Pendiente y por decidir: ver `pormejorar.md` (QR del 2FA, códigos de recuperación, dependencia de Google para el DNS, HTTPS de dominios propios, exportación de datos).

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
