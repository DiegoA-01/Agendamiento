# Changelog

## M5 — Motor de disponibilidad, citas y estados (frente A)

- **Motor de disponibilidad** (`scheduling/availability.py`, spec §8): tiempo libre = horario del día (zona del negocio) menos bloqueos menos citas activas; inicios cada `slot_step_min` alineados desde la medianoche donde cabe la duración total (overrides del profesional + buffer del último servicio); si un servicio exige puesto, debe quedar uno libre en la sede del profesional. Franjas `morning` (< 12:00), `afternoon` y `evening` (≥ 18:00).
  - Reserva pública: anticipación mínima (`min_notice_min`), días hacia adelante (`max_advance_days`) y solo profesionales con reserva en línea. El panel solo impide el pasado.
  - "Cualquiera": une los horarios de todos los que ofrecen los servicios.
  - Caché en Redis del tiempo libre por (negocio, profesional, fecha), con una versión por negocio que sube con cada cambio de citas, horarios o bloqueos.
- `GET /api/v1/availability/slots/?service_ids=&professional_id=&date=` y `GET /api/v1/availability/days/?service_ids=&professional_id=&month=YYYY-MM` para el panel (quien puede crear citas).
- **Citas** (`appointments/`): listar con filtros (rango, profesional, estado, cliente) y paginación por cursor; crear con un cliente existente (`customer_id`) o nuevo (`customer`, se busca por celular normalizado a E.164); ver; `PATCH` del puesto.
  - Nacen `confirmed`, con precio, duración y comisión congelados en `AppointmentItem`.
  - La creación revalida el horario y la restricción de exclusión es la garantía final: si el hueco se ocupa, `409 slot_taken` con hasta 5 horarios sugeridos.
  - "Cualquiera" asigna al profesional libre con menos citas ese día (empate: orden alfabético); si otro ganó el hueco, prueba con el siguiente.
- **Estados** (spec §7): `confirm`, `start`, `complete`, `cancel` (con motivo), `no-show` y `reschedule` (crea la cita nueva enlazada con `rescheduled_from`; si el horario nuevo no está libre, nada cambia). Transiciones inválidas: `409 invalid_transition`. Cancelar y no-show liberan el hueco.
- Permisos (matriz §5): owner, admin y recepción hacen todo; el profesional solo ve sus citas y puede completarlas o marcar no-show (lo ajeno da 404). Todo exige el módulo `booking` del plan (`403 module_disabled`).
- **Aceptación**: 20 POST simultáneos al mismo hueco crean 1 cita y 19 reciben 409 (`tests/booking/test_concurrency.py`, con hilos y transacciones reales). La prueba destapó una carrera al crear el mismo cliente dos veces a la vez, ya corregida.

## Fase 0 (pendiente) — Rutas públicas del negocio

- El host del negocio ya tiene las rutas públicas de la spec §13: `/reservar`, `/cita/:token`, `/terminos`, `/privacidad` y `/cookies`. Por ahora muestran su título traducido, el selector de idioma y "Esta página llega en el hito M6". Con esto `App.tsx` queda cerrado: M6 solo reemplaza el contenido de cada página.
- Textos en `locales/{es,en}/booking.json` (área nueva `booking`).

## Fase 0 (pendiente) — Sede por defecto de cada negocio

- `company.services.create_company` crea también la sede por defecto (`is_default=True`), con el nombre en el idioma del negocio: "Sede principal" o "Main location". Como el alta de empresas del Super Admin la usa, todo negocio nuevo nace con su sede y ya puede crear profesionales y puestos.
- Migración de datos `company/0003`: da la sede por defecto a los negocios creados antes. Corre con el rol de la app (sujeto a RLS), activa el modo plataforma solo mientras dura y no duplica si se repite.
- Nuevo `company.services.get_default_location(tenant)` para las demás apps.

## Fase 0 (pendiente) — `/me/` con los permisos del rol

- `GET /api/v1/me/` agrega `permissions`: `{recurso: {"scope": "all" | "own", "actions": [...]}}`, calculado con `permissions_for_role` desde la misma matriz que valida la API (spec §5). Ejemplo para un profesional: `"appointments": {"scope": "own", "actions": ["complete", "no_show", "view"]}`. Solo guía a la interfaz; la API sigue validando cada petición.
- El menú del panel deja de copiar los roles: cada sección declara el recurso que necesita ver (y si exige verlo todo, como `/clientes` y `/puestos`) y se muestra según esos permisos. Si cambia la matriz del backend, el menú cambia solo. Los menús por rol quedan igual que antes.

## Fase 0 (pendiente) — Polling de Vite en Docker

- `frontend/vite.config.ts` vigila los archivos por sondeo cuando `VITE_USE_POLLING=1`, y `docker-compose.yml` lo activa en el servicio `web`. En Docker sobre Windows la carpeta compartida no avisa los cambios, y sin esto el navegador seguía mostrando código viejo hasta recrear el contenedor. Fuera de Docker no cambia nada.

## Fase 0 (pendiente) — Configuración de agenda del negocio (frente A)

- `Tenant` gana cuatro reglas de agenda (spec §8 y §9), con los valores por defecto de la spec: `slot_step_min` 15 (de 5 a 120), `min_notice_min` 60 (hasta 7 días), `max_advance_days` 60 (de 1 a 365) y `cancel_min_hours` 2 (hasta 7 días). Los rangos se validan en el modelo y también con restricciones en la base. Migración `tenancy/0002`.
- `GET/PATCH /api/v1/agenda-settings/` en el host del negocio: el propietario las edita y el administrador solo las ve (son datos de empresa, matriz §5). Recepción y profesionales reciben 403.
- Servicios públicos `tenancy.agenda_settings` y `tenancy.update_agenda_settings`, que leerán el motor de disponibilidad (M5) y la reserva pública (M6).

## M4 — Horarios y bloqueos (app `scheduling`, frente A)

- `GET/PUT /api/v1/professionals/{id}/working-hours/`: lee o reemplaza la semana completa de un profesional (lista de franjas `weekday` 0 = lunes … 6 = domingo, `start_time`, `end_time`, en hora local). Varias franjas el mismo día representan un descanso; franjas que se traslapan dan `400 overlapping_hours`. Máximo 50 franjas por semana.
- `time-blocks/` CRUD: bloqueos de un profesional **o** de un puesto (`professional_id` o `resource_id`, exactamente uno). Listado con paginación por cursor y filtros `professional_id`, `resource_id`, `start_at` y `end_at`.
- Un bloqueo que choca con citas activas responde **`409 time_block_conflict`** con las citas en `fields.appointments` (`id`, `start_at`, `end_at`, `status`). Las citas canceladas o `no_show` no cuentan, y tocar el borde (bloqueo que termina cuando empieza la cita) no es choque.
- Permisos de la matriz (§5): propietario, administrador y recepción gestionan todos los horarios y bloqueos; un profesional solo los suyos. Lo ajeno responde 404 (no 403); un profesional que intenta bloquear un puesto recibe 403.
- Fechas en la zona horaria del negocio: una fecha sin zona se interpreta en hora local y las respuestas llevan el desfase (`2030-01-10T09:00:00-05:00`). En la base siguen en UTC.
- Borrado lógico: reemplazar la semana y borrar un bloqueo marcan `deleted_at`.
- Servicios públicos nuevos: `scheduling/services.py`, `booking.services.overlapping_appointments` y un `catalog/services.py` mínimo de solo lectura (`get_professional`, `get_resource`, `professional_for_user`), que el frente B amplía en B4.1.

## M4 — Pantallas de empresa, servicios, puestos y equipo (frente B)

- `/empresa`:
  - Datos del negocio, logo (sube a `media/`), redes sociales y textos legales.
  - El HTML legal se muestra como quedó guardado, ya limpio por el servidor.
  - Nombre y dirección de la sede principal. La UI multisede sigue fuera de alcance (§12).
- `/servicios`: categorías (crear, renombrar, borrar) y servicios agrupados por categoría con precio en la moneda del negocio, duración, tiempo de preparación, activo, si necesita puesto e imagen.
- `/puestos`: crear, editar y borrar puestos.
- `/equipo`:
  - Fichas con foto, especialidades (se crean desde la misma ficha), comisión, activo y reserva en línea.
  - Editor de **servicios que ofrece cada profesional** con precio, duración y comisión propios. Lo que se deja en blanco usa el valor general.
- La interfaz se adapta a los permisos de `/me/`: quien solo puede ver recibe la pantalla en modo lectura, sin botones de edición. Los errores del servidor (`plan_limit_reached`, `category_in_use`, `location_in_use`, imagen inválida…) se muestran traducidos.
- Compartido (solo se agregó código): `uploadFile` en `shared/api/client.ts`, tipos del catálogo en `shared/api/types.ts`, `TextAreaField` en `primitives.tsx` y nuevos códigos de error en `common.json`. Textos del área en `locales/{es,en}/catalog.json`.
- 30 pruebas nuevas (validación de formularios, conversión a lo que espera la API, formato de montos y permisos).
- Probado en el navegador como propietario y como recepcionista, en español y en inglés, en escritorio y a 375 px (sin desbordamiento horizontal).

## M4 — Equipo y servicios de cada profesional (app `catalog`, frente B)

- `professionals/` CRUD:
  - Ficha con `display_name`, `bio`, foto (`photo_id` de `media/`), especialidades (`specialty_ids`), comisión por defecto (0 a 100, dos decimales), `is_active` y `accepts_online_booking`.
  - Cuenta enlazada (`user_id`): debe ser del mismo negocio y solo puede tener una ficha.
  - Sede: sin indicarla se usa la sede por defecto.
- **Límite del plan** (`max_professionals`): `409 plan_limit_reached`. Borrar una ficha (borrado lógico) libera el cupo y deja de ofrecer sus servicios.
- `GET/PUT professionals/{id}/services/`: servicios que ofrece el profesional con sus overrides (precio, comisión, duración). `PUT` reemplaza la lista completa: conserva el id de los que siguen, crea los nuevos y da de baja los que faltan. Es lo que lee `catalog.services.quote` para el motor de disponibilidad.
- `specialties/` (listar, crear, renombrar, borrar). Borrar una especialidad la quita de las fichas.
- Permisos de la matriz §5 (`staff_services`): propietario y administrador editan, recepción ve y el profesional ve **solo su ficha** (otra da 404). Asignar servicios cuenta como editar.
- `accounts.services.get_tenant_user(tenant, user_id)`: búsqueda de solo lectura en `accounts` para enlazar la cuenta (regla 12 del reparto).
- 21 pruebas nuevas.

## M4 — Categorías, servicios y puestos (app `catalog`, frente B)

- CRUD de `categories/`, `services/` y `resources/` (con `GET/PATCH/DELETE` por id). Borrado lógico.
- Permisos de la matriz §5 (recurso `staff_services`): propietario y administrador hacen CRUD y recepción solo ve. El profesional solo ve **lo propio**: los servicios que ofrece y sus categorías; un servicio ajeno da 404. Los puestos no tienen "lo propio": el profesional recibe 403.
- Servicios:
  - Precio como texto decimal (`"30000.00"`), mínimo 0 y con 2 decimales.
  - Duración de 5 a 1440 minutos y buffer de 0 a 240.
  - `image_id` de `media/`, del mismo negocio.
  - Filtros `category_id` e `is_active`.
  - Borrar un servicio lo quita también de cada profesional; las citas pasadas conservan su precio y duración en `AppointmentItem`.
- Una categoría con servicios no se borra (`409 category_in_use`).
- Un puesto sin `location_id` va a la sede por defecto. Una categoría, imagen o sede de otro negocio da 400 en el campo, y un registro de otro negocio da 404.
- `company.services.find_location(id)` para validar la sede sin lanzar error.
- 48 pruebas nuevas.

## M4 — Empresa y sedes (app `company`, frente B)

- `GET/PATCH /api/v1/company/`: datos de la empresa, logo (`logo_id` de una imagen subida en `media/`, del mismo negocio; `null` lo quita), redes sociales (`instagram`, `facebook`, `tiktok`, `whatsapp`, `website`) y textos legales.
- **Textos legales limpios**: `terms_html`, `privacy_html` y `cookies_html` se guardan con solo formato básico (párrafos, negritas, listas, títulos y enlaces `http`, `https`, `mailto` o `tel`). Se quitan scripts, estilos, iframes, imágenes y atributos como `onclick`, porque esos textos se muestran en las páginas públicas. Usa la librería estándar, sin dependencias nuevas (`company/sanitize.py`).
- `GET/POST /api/v1/locations/` y `GET/PATCH/DELETE /api/v1/locations/{id}/`:
  - Respeta el límite de sedes del plan (`409 plan_limit_reached`).
  - Siempre hay exactamente una sede por defecto: se puede elegir otra, pero no quitarla ni borrarla (`default_location_required`).
  - No se borra una sede que usa un profesional o un puesto (`409 location_in_use`). El borrado es lógico.
- Permisos de la matriz §5 (recurso `company`): el propietario edita, el administrador solo ve y los demás roles reciben 403. Una sede de otro negocio da 404.
- `catalog.services.location_in_use(location_id)` para la regla anterior.
- 42 pruebas nuevas (permisos por rol, limpieza del HTML, logo de otro negocio, límite del plan, sede por defecto y aislamiento).

## M4 — Catálogo para el motor de disponibilidad (app `catalog`, frente B, tarea B4.1)

Funciones públicas en `catalog/services.py` para el motor de disponibilidad y la creación de citas (M5, frente A). Todas buscan dentro del negocio activo.

- `get_bookable_services(ids)`: servicios activos en el orden pedido y sin repetidos. Devuelve `None` si la lista está vacía o si un solo id no existe, está inactivo, borrado o es de otro negocio.
- `professionals_for_services(services, online_only=False)`: profesionales activos que ofrecen **todos** los servicios, en orden alfabético (§8.2). Con `online_only=True` deja solo a quienes aceptan reservas en línea.
- `quote(professional, services)`: precio, duración y comisión de cada servicio con los overrides del profesional (override > valor del servicio o comisión por defecto; un override en 0 se respeta). Devuelve el total, la duración total (suma de duraciones + el buffer del **último** servicio, §8.1) y si hace falta puesto. `None` si el profesional no ofrece alguno de los servicios. Sus valores son los que se congelan en `AppointmentItem`.
- `requires_resource(services)` y `active_resources(location_id=None)` para exigir un puesto libre (§8.5).
- 16 pruebas nuevas, incluido el aislamiento entre negocios.

## M4 — Imágenes (app `media`)

- `POST /api/v1/media/` (multipart, campo `file`): sube una imagen JPG, PNG o WebP y responde `201` con `id`, tamaño original y las URLs de las tres variantes. Solo para quien puede editar la empresa o el catálogo (propietario y administrador) y solo en el host de un negocio.
- Toda imagen se convierte a **WebP** en tres tamaños: `thumb` 200 px, `medium` 800 px y `large` 1600 px (lado mayor). Nunca se agranda una imagen pequeña. Se respeta la transparencia.
- Se aplica la rotación de la cámara y se **descarta el EXIF**, que puede traer la ubicación GPS de la foto.
- Rechazos con el formato de error estándar: `invalid_image`, `unsupported_image` (GIF, BMP…), `file_too_large` (más de 10 MB, `MEDIA_MAX_UPLOAD_BYTES`) e `image_too_large` (más de 40 megapíxeles, protección contra bombas de descompresión).
- Servicios públicos para otras apps: `upload_image`, `get_media` (solo imágenes del tenant activo, para validar el id que manda el cliente) y `media_urls`.
- En desarrollo Django sirve `/media/...` y Caddy enruta esas rutas a la API. En producción falta servirlas desde Caddy (`pormejorar.md` §34).
- Sin dependencias nuevas (Pillow ya estaba en la lista).

## Fase 0 — Contratos compartidos (frontend)

Base del panel del negocio para trabajar M4 a M10 en paralelo sin choques (ver `docs/REPARTO.md`).

- **Traducciones por área**: `locales/<idioma>/<area>.json` (`common`, `auth`, `platform`, `dashboard`). Un archivo nuevo se carga solo (`import.meta.glob`), sin registrarlo en ningún lado. Las claves no cambian (`t("tenants.x")` sigue igual). Un test falla si dos archivos usan la misma clave de primer nivel o si `es` y `en` no tienen los mismos archivos.
- **Panel del negocio**: layout con el tema del negocio, menú lateral (botón "Menú" en el celular) y las rutas de la spec §13: `/agenda`, `/citas`, `/clientes`, `/servicios`, `/equipo`, `/puestos`, `/horarios`, `/reportes`, `/empresa`. Cada sección es una página provisional en su propia carpeta (`features/dashboard/<seccion>/`) y en su propio paquete (lazy). Cada frente reemplaza las suyas sin tocar `App.tsx`.
- **El menú depende del rol y de los módulos** (matriz de la spec §5, en `features/dashboard/navigation.ts`, con tests por rol). Entrar por URL a una sección no permitida lleva al inicio del panel. `/panel` lleva a la primera sección visible.
- Se elimina el panel provisional de M3. Cerrar sesión pasa a `useSignOut`, compartido con el panel del Super Admin.
- Probado en el navegador como propietario y como profesional, en escritorio y a 375 px (sin desbordamiento horizontal).

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
