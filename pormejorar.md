# Por mejorar

Lista de todo lo que se puede mejorar o ajustar en lo construido hasta M3 (esqueleto, tenancy, cuentas y panel del Super Admin), explicado para entenderlo sin conocimientos previos. Se actualiza al cerrar cada hito.

## Cómo leer este documento

Cada punto responde cuatro preguntas:

- **Qué es:** qué falta o qué se puede mejorar.
- **Por qué importa:** qué pasaría si no se hace, con un ejemplo.
- **Cuándo:** el hito o el momento recomendado.
- **Cómo:** qué hay que hacer, y en qué archivo cuando aplica.

**Prioridad:**
- **Alta:** hacerlo antes de que entren usuarios reales.
- **Media:** hacerlo pronto, no bloquea el desarrollo.
- **Baja:** mejora deseable cuando haya tiempo.

Los puntos marcados **Requiere aprobación** necesitan una decisión tuya o del equipo, porque agregan una dependencia que no está en la lista de la spec (regla del `CLAUDE.md`) o cambian una decisión de producto.

## Índice rápido

| # | Tema | Prioridad | Hito sugerido |
|---|---|---|---|
| 33 | **REACTIVAR el 2FA antes de entregar** (hoy está apagado en desarrollo) | **Alta** | **Al final, obligatorio** |
| 1 | Límite de intentos de login | Alta | M10 (antes si se puede) |
| 2 | Códigos de recuperación del 2FA (el comando `reset_2fa` ya existe) | Alta | Pronto |
| 3 | Cifrar el secreto del 2FA | Alta | M10 |
| 4 | Servidor de producción | Alta | Antes de desplegar |
| 5 | 2FA obligatorio para el propietario | Media | Decisión del equipo |
| 6 | Activación del 2FA solo con contraseña | Media | Pronto |
| 7 | Ajustar Argon2id al servidor real | Media | Al elegir el VPS |
| 8 | Caché de la búsqueda de tenant | Media | M5 o M10 |
| 9 | Contexto del tenant en respuestas en streaming (SSE) | Alta | M7 |
| 10 | Tareas de Celery con tenant | Media | M8 |
| 11 | Modo solo lectura para tenants suspendidos (el bloqueo total ya existe) | Baja | Decisión de producto |
| 12 | Subdominios borrados siguen reservados | Baja | Cuando haga falta |
| 13 | Correo real y plantillas | Media | M8 |
| 14 | Alta del propietario por enlace, en lugar de contraseña temporal | Media | Mejora |
| 15 | Sesiones: duración y control | Media | M3 a M10 |
| 16 | Auditar inicios de sesión y suplantación (las acciones del Super Admin ya se registran) | Media | M10 |
| 17 | Alcance "solo lo propio" del profesional | Media | M4 y M5 |
| 18 | Logs con tenant e identificador de petición | Baja | M10 |
| 19 | CI: ramas, versiones y pruebas | Media | Ahora |
| 20 | Pruebas de pantallas del frontend | Media | M4 en adelante |
| 21 | Dependencias fuera de la lista | Media | Decisión del equipo |
| 22 | HTTPS automático para dominios propios (la verificación por DNS ya existe) | Media | Antes de desplegar |
| 23 | Copias de seguridad y observabilidad | Alta | M10 |
| 24 | Detalles técnicos que conviene conocer | Baja | Informativo |
| 25 | QR para activar el 2FA | Media | Decisión del equipo |
| 26 | Verificación de dominios depende de Google | Media | Antes de desplegar |
| 27 | Si se pierde la contraseña temporal | Media | Mejora |
| 28 | Mensajes del servidor solo en español | Baja | M4 en adelante |
| 29 | Tamaño del paquete principal del frontend | Baja | M6 |
| 30 | Cerrar un negocio: exportar y borrar sus datos | Media | Antes de tener clientes reales |
| 31 | Límites del plan sin aplicar | Media | M4 |
| 32 | Revisión de accesibilidad automática | Baja | M10 |

---

## 1. Límite de intentos de login

**Qué es:** hoy se puede probar contraseñas sin límite. La spec lo deja para M10.

**Por qué importa:** un atacante puede automatizar miles de intentos. Por ejemplo, tiene el correo del dueño de una barbería (suele ser público) y prueba las 10 000 contraseñas más comunes. Ya se rechazan las contraseñas comunes y Argon2id vuelve cada intento más lento, pero el límite es la defensa principal.

**Cuándo:** M10, pero es barato hacerlo antes, sobre todo para el login y la recuperación de contraseña.

**Cómo:**
- Con el sistema de límites de DRF (viene incluido, usa Redis): por ejemplo, 5 intentos por minuto por IP y 10 por hora por correo.
- Ojo: el contador debe ser por correo **y** por IP. Solo por IP, un atacante con muchas IP no se frena. Solo por correo, un atacante puede bloquear la cuenta de otra persona a propósito.
- Para el Super Admin, además, bloqueo temporal tras varios fallos seguidos.
- Los tests deben limpiar el contador entre pruebas, o se vuelven inestables.

## 2. Códigos de recuperación del 2FA

**Qué es:** si el Super Admin pierde el celular, hoy **no hay forma de entrar**. No existe recuperación.

**Por qué importa:** ejemplo: el único Super Admin cambia de teléfono sin migrar la app de códigos. No puede entrar al panel, y por tanto nadie puede administrar los negocios.

**Estado tras M3:** parcialmente resuelto. Ya existe el comando de emergencia `reset_2fa` (ver abajo). **Siguen pendientes los códigos de recuperación.**

**Cuándo:** pronto, antes de que haya más de un Super Admin real.

**Cómo (las dos partes):**
1. **Códigos de recuperación de un solo uso.** Al activar el 2FA se muestran 8 a 10 códigos para guardar en un lugar seguro. Cada uno sirve una vez en lugar del código de 6 dígitos. Se guardan con hash, como las contraseñas.
2. **Comando de emergencia por terminal**, por ejemplo `reset_2fa --email ...`. Solo lo puede ejecutar quien tenga acceso al servidor. Es la última salida si se pierden también los códigos.

## 3. Cifrar el secreto del 2FA

**Qué es:** el secreto con el que se generan los códigos de 6 dígitos (`totp_secret`) se guarda como texto normal en la base de datos.

**Por qué importa:** si alguien roba una copia de la base de datos, puede generar los códigos 2FA de todos. El 2FA dejaría de proteger. La spec también pide cifrar las credenciales de integraciones.

**Cuándo:** M10.

**Cómo:** cifrar el campo antes de guardarlo, con una clave que viva solo en una variable de entorno (nunca en la base). **Requiere aprobación:** necesita una librería de cifrado (por ejemplo `cryptography`) que no está en la lista de la spec. Este mismo mecanismo servirá luego para las claves de Wompi y WhatsApp.

## 4. Servidor de producción

**Qué es:** los contenedores usan `runserver`, el servidor de desarrollo de Django. Está en `backend/Dockerfile` y `docker-compose.yml`.

**Por qué importa:** `runserver` no está pensado para tráfico real: es lento y no aguanta muchas conexiones a la vez. Ejemplo: 30 personas reservando a la vez en una promoción se encolarían.

**Cuándo:** antes de desplegar. Es obligatorio.

**Cómo:** usar un servidor de aplicaciones real, por ejemplo `gunicorn` (más simple) o `uvicorn`/`daphne` (si se necesita asincronía). **Requiere aprobación:** ninguno está en la lista de la spec. Para el tiempo real (SSE, M7) conviene un servidor que maneje muchas conexiones abiertas. También hará falta un `docker-compose` de producción aparte, sin los volúmenes de código ni el servidor de Vite del frontend (se sirve el resultado compilado).

## 5. 2FA obligatorio para el propietario

**Qué es:** hoy el 2FA es obligatorio solo para el Super Admin. Para el propietario es opcional, pero si lo activa se le exige. La PDF de producto lo pedía obligatorio para ambos.

**Por qué importa:** el propietario controla todos los datos de su negocio (clientes, citas, ingresos). Si le roban la contraseña, pierde todo.

**Por qué se dejó opcional:** exigirlo en el primer inicio complica la entrada de personas poco técnicas, y el flujo de alta del propietario se define en M3.

**Cuándo:** decisión del equipo antes de M3.

**Cómo:** es un cambio de una línea en `backend/apps/accounts/services.py`: agregar `User.Role.OWNER` a `REQUIRED_2FA_ROLES`. El resto del flujo ya funciona. Hay que ajustar los tests y la pantalla de alta del propietario.

## 6. Activación del 2FA solo con contraseña

**Qué es:** el primer alta del 2FA se hace con correo y contraseña, sin otro paso. Si alguien consigue la contraseña de un Super Admin que **aún no activó** el 2FA, puede activar el suyo y quedarse con la cuenta.

**Por qué importa:** ejemplo: creas el Super Admin con una contraseña temporal y pasan dos días antes de que active el 2FA. En ese tiempo la cuenta está más expuesta.

**Cuándo:** pronto.

**Cómo:**
- Mitigación inmediata, sin código: activar el 2FA justo después de crear la cuenta.
- Mejora: que el comando `create_superadmin` entregue un enlace o código de alta de un solo uso y con vencimiento corto, que se pida además de la contraseña.

## 7. Ajustar Argon2id al servidor real

**Qué es:** las contraseñas usan Argon2id con el perfil mínimo recomendado por OWASP: 19 MiB de memoria, 2 pasadas, 1 hilo. Está en `backend/config/hashers.py`.

**Mediciones (en Docker, en la máquina de desarrollo):**

| | Tiempo por login | Memoria por login |
|---|---|---|
| PBKDF2 (antes) | 152 ms | 0 |
| Argon2id, valores por defecto de Django | 48 ms | ~100 MB |
| Argon2id, perfil actual | 26 ms | ~20 MB |

**Por qué importa:** esas cifras salen de tu computador, no de tu servidor. Dos riesgos opuestos:
- **Memoria demasiado alta:** ejemplo: con 100 MB por login y 10 personas entrando a la vez, el servidor gasta 1 GB y se puede quedar sin memoria.
- **Demasiado bajo:** 26 ms es poco. Cuanto más cueste calcular el hash, más caro es para un atacante probar contraseñas robadas.

**Cuándo:** cuando se elija el VPS.

**Cómo:**
1. Medir el tiempo y la memoria en el servidor real.
2. Subir `memory_cost` y `time_cost` mientras un login siga tardando entre 50 y 100 ms y la memoria alcance con los logins simultáneos esperados.
3. No hace falta migrar nada: Django vuelve a guardar cada contraseña con los parámetros nuevos la próxima vez que esa persona entra.

## 8. Caché de la búsqueda de tenant

**Qué es:** en cada petición, `TenantMiddleware` consulta la base de datos para saber a qué negocio pertenece el dominio.

**Por qué importa:** son consultas pequeñas, pero en cada petición. Ejemplo: la pantalla de reserva hace unas 6 llamadas a la API, así que son 6 consultas extra solo para saber de qué barbería se trata. La spec pide que `/public/availability/slots/` responda en menos de 300 ms.

**Cuándo:** M5 (motor de disponibilidad) o M10, cuando se mida.

**Cómo:** guardar el resultado en Redis por unos 60 segundos, por dominio. Hay que **borrar esa caché** cuando se suspende un tenant, se cambia su dominio o se verifica uno nuevo, o los cambios tardarían en aplicarse.

## 9. Contexto del tenant en respuestas en streaming (SSE)

**Qué es:** el tenant activo se apaga al terminar la vista. Las respuestas en streaming (la agenda en tiempo real de M7) siguen enviando datos después de eso.

**Por qué importa:** ejemplo: la agenda abierta consulta citas cada vez que llega un evento. Si en ese momento ya no hay tenant activo, la consulta no devuelve nada, o en el peor caso se rompe el aislamiento si se resuelve mal.

**Cuándo:** M7. Es **prioridad alta** cuando se implemente, porque toca el aislamiento entre negocios.

**Cómo:** el endpoint SSE debe volver a activar el tenant dentro de su propio generador, con `tenant_context(...)` en cada consulta a la base de datos. Añadir un test que haga streaming con dos tenants a la vez. Hay una advertencia escrita en `backend/apps/tenancy/middleware.py`.

## 10. Tareas de Celery con tenant

**Qué es:** las tareas en segundo plano no tienen petición web, así que no hay host del que sacar el tenant. Hoy hay un helper (`tenant_context`) pero no una forma estándar de usarlo.

**Por qué importa:** ejemplo: la tarea "enviar recordatorios de mañana" recorre citas de todos los negocios. Si olvida activar el tenant, no ve nada (falla cerrado), y si usa el modo global sin cuidado, mezcla datos.

**Cuándo:** M8 (notificaciones), cuando exista la primera tarea real.

**Cómo:**
- Una clase base para tareas que reciba `tenant_id`, active el contexto al empezar y lo apague al terminar.
- Para tareas que recorren todos los negocios: listar los tenants con `platform_context()` y procesar cada uno **dentro de su propio `tenant_context`**, no con el modo global.

## 11. Tenants suspendidos

**Qué es:** la spec define el estado `suspended` en `Tenant`, pero el middleware lo ignora: un negocio suspendido sigue funcionando.

**Por qué importa:** ejemplo: un negocio deja de pagar y se suspende. Si el middleware no lo bloquea, el negocio y sus clientes siguen usando el sistema sin límite. La PDF habla de periodo de gracia, luego modo solo lectura y después suspensión.

**Estado tras M3:** hoy suspender **bloquea todo** el acceso del negocio (responde 403 `tenant_suspended`) y no borra datos. El modo solo lectura de la PDF (periodo de gracia, solo lectura, suspensión) no existe.

**Cuándo:** cuando el equipo defina la política de cobro y gracia.

**Cómo:** decidir qué significa cada estado:
- Reserva pública: ¿se bloquea o muestra un aviso?
- Dashboard: ¿modo solo lectura o bloqueo total?
- Nunca borrar datos al suspender.

Se implementa en el middleware o con un permiso global.

## 12. Subdominios borrados siguen reservados

**Qué es:** el borrado es lógico (se marca `deleted_at`, el registro no desaparece). Como `slug` y `host` son únicos, un negocio borrado sigue ocupando su nombre.

**Por qué importa:** ejemplo: borras "El Filo" y mañana otro negocio quiere llamarse "elfilo". El sistema responde que ya existe. También ocurre con los correos de usuarios borrados.

**Cuándo:** solo si el problema aparece en la práctica.

**Cómo:** convertir las restricciones de unicidad en **condicionales** (única solo si `deleted_at` es nulo), como ya se hizo con el correo de los usuarios. Requiere una migración en `tenancy` y `accounts`.

## 13. Correo real y plantillas

**Qué es:** en desarrollo los correos de recuperación de contraseña salen por consola (`docker compose logs api`). Los textos están escritos dentro del código, en `backend/apps/accounts/messages.py`, no en el sistema de traducciones.

**Por qué importa:** en producción nadie recibiría el correo. Además, un correo sin SPF, DKIM y DMARC configurados suele caer en la carpeta de spam.

**Cuándo:** M8.

**Cómo:**
- Configurar un proveedor (Amazon SES, Brevo o Resend) con las variables `EMAIL_BACKEND` y `DEFAULT_FROM_EMAIL`, y los registros DNS del dominio de envío.
- Mover los textos a plantillas por idioma y por vertical, como pide la spec.
- El enlace del correo apunta a `/recuperar/confirmar`, que **ya existe** desde M3 (junto con `/recuperar`).

## 14. Contraseña temporal del propietario

**Qué es:** la spec (M3) dice que al crear un negocio se crea el propietario con una contraseña temporal. Hoy no hay forma de obligarlo a cambiarla.

**Por qué importa:** ejemplo: tú le mandas "Temporal123" por WhatsApp. Si nunca la cambia, esa clave circula en un chat.

**Estado tras M3:** resuelto con contraseña temporal. El Super Admin la crea, se muestra una sola vez y el propietario debe cambiarla en su primer ingreso (`must_change_password`). Lo que sigue pendiente es la mejora de abajo.

**Cuándo:** mejora futura.

**Cómo (versión original, ya hecha):** agregar un campo `must_change_password` al usuario y devolverlo en `/api/v1/me/`. El frontend lo manda a cambiar la contraseña antes de dejarlo usar el sistema. Mejor aún: en lugar de contraseña temporal, enviar un enlace de alta de un solo uso por correo.

## 15. Sesiones: duración y control

**Qué es:** la duración de la sesión es la que trae Django (2 semanas). No hay cierre por inactividad, ni lista de dispositivos, ni "cerrar todas las sesiones". Las sesiones se guardan en PostgreSQL.

**Por qué importa:** ejemplo: la recepcionista inicia sesión en el computador de un cibercafé y se olvida de salir. La sesión sigue abierta dos semanas. Para un Super Admin, eso es mucho.

**Cuándo:** M3 a M10.

**Cómo:**
- Duración más corta para roles sensibles (Super Admin: pocas horas, o cierre por inactividad).
- Botón "cerrar sesión en todos los dispositivos".
- Si la carga crece, mover las sesiones a Redis (`cached_db`), como indica el ADR.

Ya funcionan: cambiar la contraseña cierra todas las sesiones, y borrar o desactivar un usuario cierra las suyas.

## 16. Registro de auditoría

**Qué es:** la spec define un `AuditLog` (quién hizo qué, cuándo, con valores antes y después). Todavía no existe.

**Por qué importa:** ejemplo: "alguien cambió el tema de colores de un negocio, ¿quién fue?". O ante un incidente: ¿quién entró a la cuenta del Super Admin y desde dónde?

**Estado tras M3:** hecho para las acciones del Super Admin (crear, editar, suspender, tema, módulos, dominios, planes). Falta auditar **inicios de sesión** (exitosos y fallidos), cambios de 2FA y de contraseña, y la suplantación de soporte.

**Cuándo:** M10 (endurecimiento).

**Cómo:** guardar al menos inicios de sesión (exitosos y fallidos), activaciones o cambios de 2FA, cambios de contraseña, y todas las acciones del Super Admin sobre negocios. La spec también pide suplantación auditada para soporte (el Super Admin hoy no puede ver datos de clientes).

## 17. Alcance "solo lo propio" del profesional

**Qué es:** la matriz de permisos ya dice que el profesional solo ve **sus** citas, comisiones y horarios (`scope_for(...)` devuelve `own`). Pero hoy no hay citas ni profesionales, así que nada filtra todavía.

**Por qué importa:** la regla "el profesional nunca recibe citas de otro" (ni en listados ni por id) se cumple solo si cada consulta futura aplica el alcance. Si una vista lo olvida, un profesional vería la agenda de otro.

**Cuándo:** M4 (profesionales) y M5 (citas).

**Cómo:**
- Enlazar `User` con `Professional` (campo `user` del profesional).
- Una función común que, dado el usuario y el recurso, filtre las filas con `scope_for`.
- Para citas ajenas, responder **404**, no 403 (la spec lo pide: no revelar que la cita existe).
- Un test por recurso: un profesional pidiendo la cita de otro recibe 404.

## 18. Logs con tenant e identificador de petición

**Qué es:** los logs salen en JSON, pero sin saber de qué negocio ni de qué petición vienen.

**Por qué importa:** ejemplo: un cliente dice "me dio error a las 4:10". Sin el negocio y un identificador en cada línea, encontrar esa petición entre miles es muy lento.

**Cuándo:** M10.

**Cómo:** agregar `tenant` y `request_id` a cada línea (en `backend/config/logging.py`, con un filtro que lea el contexto) y devolver el `request_id` en un header. Más adelante, Sentry (spec §15).

## 19. CI: ramas, versiones y pruebas

**Qué es:** el CI de GitHub (`.github/workflows/ci.yml`) tiene tres temas:
1. **Solo corre en `main` y en pull requests.** Un push a `develop` no lo dispara. Como el equipo decidió no hacer pull requests hasta que el encargado revise, **el CI no corre sobre el trabajo diario**.
2. **Avisos de GitHub:** las acciones `actions/checkout@v4` y `actions/setup-python@v5` usan Node 20, que está en retirada, y `ubuntu-latest` migra a Ubuntu 26 desde el 19 de octubre de 2026. Hoy funciona, pero con avisos.
3. **El paso que crea el rol sin superusuario** (necesario para probar RLS) **nunca se ha ejecutado en GitHub**: se agregó en M1, y desde entonces el CI no ha corrido porque el trabajo está en `develop`. Funciona en Docker local, pero es el punto con más riesgo de fallar la primera vez en GitHub.

**Por qué importa:** ejemplo: alguien sube un cambio que rompe el aislamiento entre negocios. Sin CI en `develop`, nadie se entera hasta abrir el pull request.

**Cuándo:** ahora (el cambio es mínimo).

**Cómo:**
- Agregar `develop` a la lista `branches` del `push`. **No toca `main` ni abre pull requests**, solo prueba el código en `develop`. Si lo quieres, lo hago.
- Subir las versiones de las acciones cuando GitHub publique las compatibles con Node 24.
- Si algo falla en GitHub y no en tu computador, revisa primero las variables de entorno: el CI las tiene vacías, y en M0 el primer fallo vino de ahí.

## 20. Pruebas del frontend

**Qué es:** el frontend tiene 4 pruebas (idiomas y selector). No hay pruebas de pantallas ni de la interacción con la API.

**Por qué importa:** el asistente de reserva (M6) y la agenda (M7) son lo que más ven los clientes. La spec exige reservar en menos de 60 segundos en móvil.

**Estado tras M3:** hay 42 pruebas de la lógica (cliente de API, CSRF, validaciones, mensajes, idiomas, plurales, contraste). Las **pantallas** solo se probaron a mano en el navegador.

**Cuándo:** M4 en adelante.

**Cómo:** sumar `@testing-library/react` y `jsdom` para probar componentes (**requiere aprobación**, no están en la lista), y Playwright para el flujo completo reservar → completar → comisión en M10. Hasta entonces, los tests de pantalla se limitan a lo que permite `react-dom/server`.

## 21. Dependencias fuera de la lista

Son paquetes que no estaban en la sección 2 de la spec. Por la regla del `CLAUDE.md`, el equipo debe aprobarlos.

| Paquete | Para qué | Estado |
|---|---|---|
| `argon2-cffi` | Hash de contraseñas Argon2id | **Aprobado** (M2) |
| `@types/node` | Tipos para `vite.config.ts` | Pendiente de aprobación (solo desarrollo) |
| `@hookform/resolvers` | Conecta Zod con React Hook Form | Pendiente de aprobación |
| Servidor de producción (`gunicorn` o similar) | Ver punto 4 | Pendiente |
| Librería de cifrado | Ver punto 3 | Pendiente |
| `@testing-library/react`, `jsdom` | Ver punto 20 | Pendiente |

## 22. Dominios propios y HTTPS

**Qué es:** el `Caddyfile` sirve HTTP en el puerto 80 para desarrollo. La spec pide HTTPS automático para cada subdominio y para dominios propios de clientes, verificados por DNS.

**Por qué importa:** en producción sin HTTPS, las contraseñas y las cookies de sesión viajan sin cifrar. Además, Django en producción exige HTTPS (`SECURE_SSL_REDIRECT`).

**Estado tras M3:** el alta y la verificación de dominios propios por DNS ya funcionan. Falta el HTTPS: el `Caddyfile` sirve HTTP en desarrollo.

**Cuándo:** antes de desplegar.

**Cómo:**
- Un certificado comodín (`*.tudominio.com`) para los subdominios, que requiere validar por DNS con el proveedor.
- Para dominios propios, el modo "bajo demanda" de Caddy: emite el certificado solo si el dominio está verificado en la base de datos (hay que exponer un endpoint de consulta para Caddy).
- `ALLOWED_HOSTS` de Django: con dominios propios hay que aceptar cualquier host y dejar que `TenantMiddleware` decida (devuelve 404 si no está registrado). Está explicado en el middleware.

## 23. Copias de seguridad y observabilidad

**Qué es:** no hay copias de seguridad, ni monitoreo de errores, ni alertas. La spec lo pide para M10.

**Por qué importa:** ejemplo: el disco del servidor falla y se pierden todas las citas de todos los negocios. Es el riesgo "un solo VPS" que menciona la PDF.

**Cuándo:** M10, pero **antes de tener un negocio piloto real**.

**Cómo:**
- Copia diaria de PostgreSQL **fuera del servidor**, cifrada, y **probar la restauración** periódicamente (una copia que nunca se probó no es una copia).
- Sentry para errores, monitoreo de disponibilidad (por ejemplo contra `/healthz/`) y alertas.
- Redis: decidir si algo imprescindible vive solo ahí (hoy solo hay caché y cola).

## 24. Detalles técnicos que conviene conocer

Información para quien mantenga el proyecto, no son errores:

- **`set_config` en vez de `SET LOCAL`.** La spec decía `SET LOCAL`. Django corre en modo autocommit y `SET LOCAL` fuera de una transacción no hace nada, así que se usa el equivalente de sesión y siempre se restaura al salir (`backend/apps/tenancy/context.py`).
- **Tablas sin RLS a propósito.** `Tenant`, `Domain`, `Plan`, `TenantModule` y `User` son datos de plataforma o identidad: se necesitan antes de saber el tenant. Las tablas de **negocio** (citas, clientes, servicios...) sí llevan RLS con `enable_rls("tabla")` en su migración. Olvidar ese paso en un modelo nuevo deja la tabla sin segunda protección: conviene un test que lo detecte.
- **`User` no hereda de `TenantOwnedModel`.** El Super Admin no tiene negocio. Toda consulta de usuarios debe pasar por `User.objects.for_tenant(...)`.
- **El token CSRF se renueva al iniciar sesión.** El frontend debe volver a leer la cookie `csrftoken` después del login, o el siguiente POST falla con 403. Hay un test.
- **mypy no revisa los tests.** `factory-boy` no trae tipos y confundía las fábricas con los modelos. Sigue revisando todo el código de la aplicación.
- **El rol de la base de datos importa.** PostgreSQL ignora RLS para superusuarios. La app usa `agenda_app` (sin superusuario). Un test falla si ese rol tuviera esos privilegios. Si el aislamiento se rompe "sin motivo", empieza por revisar esto.
- **Recrear volúmenes.** Los cambios de M1 (rol de la app) y M2 (modelo de usuario) exigieron `docker compose down -v`. Cualquier compañero con una base anterior debe hacerlo.
- **Teléfonos.** Todavía no se normalizan a formato internacional (E.164). La spec lo exige para `Customer` en M5.
- **Documentación OpenAPI.** Los endpoints de autenticación están documentados, pero los errores (`{code, detail, fields}`) todavía no.
- **`/healthz/` es público** y muestra si la base de datos y Redis responden. No expone secretos, pero se puede restringir a la red interna en producción.
- **Docker Desktop en Windows** se apaga con frecuencia en este equipo. Si aparece el error del archivo `dockerInference`, ver la nota de recuperación (`wsl --shutdown` o borrar ese archivo temporal).

## 25. QR para activar el 2FA

**Qué es:** al activar el 2FA, la pantalla muestra una **clave manual** para escribirla en Google Authenticator. No hay código QR.

**Por qué importa:** escribir 32 caracteres a mano es incómodo y fácil de equivocar. Con un QR basta escanear con el celular.

**Cuándo:** cuando el equipo lo decida.

**Cómo:** **Requiere aprobación.** El backend ya entrega la URI `otpauth://...` que necesita el QR. Falta una librería que lo dibuje en el frontend (por ejemplo `qrcode`), que no está en la lista de la spec. La clave manual debe seguir disponible como alternativa.

## 26. Verificación de dominios depende de Google

**Qué es:** para comprobar los registros DNS de un dominio propio, el servidor consulta `dns.google` (DNS sobre HTTPS) con la librería estándar, sin dependencias nuevas. Está en `backend/apps/tenancy/dns.py`.

**Por qué importa:**
- Si Google no responde o el servidor no tiene salida a internet, la verificación falla con un 503 reintentable (nunca verifica por error).
- Cada verificación le revela a Google qué dominios de clientes se están dando de alta.
- Google puede tener en caché un valor viejo durante unos minutos.

**Cuándo:** antes de desplegar.

**Cómo:** cambiar de proveedor sin tocar el resto es una línea: el setting `DNS_RESOLVER` apunta a una clase con `txt()` y `cname()`. La alternativa más estándar es una librería de DNS (`dnspython`), que **requiere aprobación** por no estar en la lista. Con ella el servidor consulta directamente a su propio resolvedor.

## 27. Si se pierde la contraseña temporal

**Qué es:** la contraseña temporal del propietario se muestra **una sola vez** al crear el negocio y no se guarda. Si el Super Admin la pierde antes de entregarla, hoy no hay un botón para generar otra.

**Por qué importa:** ejemplo: cierras la pestaña sin copiarla. El propietario no puede entrar.

**Qué se puede hacer hoy:** el propietario usa "¿Olvidaste tu contraseña?" y recibe un enlace por correo. Eso exige que el correo funcione (ver punto 13); en desarrollo el enlace sale por la consola (`docker compose logs api`).

**Cuándo:** mejora futura.

**Cómo:** una acción "Restablecer acceso del propietario" en el detalle de la empresa que genere otra contraseña temporal (o un enlace de alta), deje constancia en la auditoría y vuelva a marcar `must_change_password`.

## 28. Mensajes del servidor solo en español

**Qué es:** los errores por campo que escribe el servidor (por ejemplo "Poco contraste con el fondo (1.61:1)…") están solo en español. Los mensajes por **código** (`invalid_credentials`, `low_contrast`…) sí se traducen a español e inglés en el frontend.

**Por qué importa:** un administrador con la interfaz en inglés ve algunos detalles de campo en español.

**Cuándo:** cuando haya administradores de habla inglesa.

**Cómo:** que el servidor devuelva códigos y parámetros (`{"code": "low_contrast", "ratio": 1.61}`) y que el frontend arme la frase, o usar el sistema de traducciones de Django (`LocaleMiddleware` ya está activo).

## 29. Tamaño del paquete principal del frontend

**Qué es:** el paquete principal pesa unos 506 kB (158 kB comprimido) y el compilador avisa que supera 500 kB. El panel del Super Admin ya se carga aparte (33 kB), pero el resto (React, rutas, formularios, validación con Zod, textos en dos idiomas) va junto.

**Por qué importa:** la spec exige reservar en menos de 60 segundos desde un celular con 360 px. Un paquete grande tarda más en redes lentas.

**Cuándo:** M6, al construir el asistente de reserva.

**Cómo:** cargar por separado lo que no se usa en la reserva pública (login, recuperación), dividir los idiomas por archivo y medir con una conexión lenta simulada. Revisar el peso de Zod frente a alternativas más livianas.

## 30. Cerrar un negocio: exportar y borrar sus datos

**Qué es:** eliminar una empresa es **lógico**: deja de estar disponible pero sus datos siguen en la base. No hay exportación ni borrado definitivo.

**Por qué importa:** la PDF dice que cada empresa es dueña de sus datos, puede exportarlos al cancelar y se retienen un plazo por definir. La Ley 1581 exige poder eliminar los datos de una persona.

**Cuándo:** antes de tener clientes reales.

**Cómo:** definir el plazo de retención, una exportación (por ejemplo CSV de clientes y citas) y un borrado definitivo con confirmación y registro en la auditoría. Revisarlo con un abogado.

## 31. Límites del plan sin aplicar

**Qué es:** los planes guardan `max_professionals` y `max_locations`, pero nada los hace cumplir todavía.

**Por qué importa:** ejemplo: el plan Inicial dice "2 profesionales" y el negocio podría crear 20.

**Cuándo:** M4, cuando se puedan crear profesionales y sedes.

**Cómo:** validar el límite al crear cada uno (en el `services.py` del catálogo), con un error claro (`plan_limit_reached`) que el frontend traduzca.

## 32. Revisión de accesibilidad automática

**Qué es:** las pantallas usan etiquetas, foco visible, mensajes con `role="alert"`, tablas con `scope` y pestañas con teclado, y se revisaron a mano. No hay una prueba automática (por ejemplo axe) ni se probó con un lector de pantalla.

**Por qué importa:** la spec pide accesibilidad con contraste AA.

**Cuándo:** M10.

**Cómo:** sumar una revisión automática a las pruebas de extremo a extremo (Playwright) y probar el flujo de reserva con un lector de pantalla.

## 33. REACTIVAR el 2FA antes de entregar

**Qué es:** para facilitar las pruebas, la verificación en dos pasos está **apagada en desarrollo**: `REQUIRE_TWO_FACTOR=0` en el `.env` (y en `.env.example`). Con eso el Super Admin entra solo con correo y contraseña, incluso si ya tenía el 2FA activo.

**Por qué importa:** el Super Admin controla todos los negocios. Sin 2FA, una contraseña robada basta para entrar. Es lo que más protege el panel y lo que más se olvida reactivar.

**Qué ya protege contra el olvido:**
- Producción **no arranca** con él apagado (`config/settings/prod.py` lanza un error).
- Los tests siempre corren con el 2FA exigido, aunque tu `.env` lo tenga apagado.
- Al arrancar, el servidor escribe un aviso `Verificación en dos pasos DESACTIVADA` en el log (`docker compose logs api`).

**Cuándo:** al final de las pruebas, **antes de entregar o de poner el sistema en un servidor**. Mejor, junto con el punto 2 (códigos de recuperación) y el punto 25 (QR), para que activarlo sea cómodo.

**Cómo reactivarlo:**
1. En `.env` pon `REQUIRE_TWO_FACTOR=1` o borra esa línea. Haz lo mismo en `.env.example`.
2. Reinicia: `docker compose up -d api`.
3. Comprueba que el aviso `DESACTIVADA` ya no sale en `docker compose logs api`.
4. Entra a http://admin.localhost:8080: el Super Admin debe ver la pantalla de activación del 2FA (clave manual y código de 6 dígitos).
5. Si pierdes el celular: `docker compose exec api python manage.py reset_2fa --email tu@correo.com`.

**Ojo con cuentas que ya existen:** al reactivarlo, un Super Admin que **nunca** activó el 2FA tendrá que activarlo en su siguiente login. Un usuario que ya lo tenía activado vuelve a necesitar su código.
