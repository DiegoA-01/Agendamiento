# Changelog

## Agenda más legible

- **Bloques de cita nuevos** (`AgendaBlock`): hora de inicio y fin, cliente (y para quién, si es otra persona), servicios y estado. Cada uno tiene fondo suave y borde izquierdo del color de su estado: confirmada en rojo, completada en verde, pendiente en ámbar, en curso en azul y canceladas en gris. Sin barras de desplazamiento dentro del bloque: muestra lo que cabe según su alto, y el resto va en el título emergente y al abrir el detalle.
- **Grilla más alta y más clara**: 96 px por hora (antes 60), la hora centrada sobre su línea, una línea tenue en cada media hora y aire entre citas seguidas. Cada cita queda exactamente en su horario.
- Las canceladas, las inasistencias y las reprogramadas se ocultan por defecto, porque angostaban las demás. La casilla **Mostrar canceladas e inasistencias** las trae de vuelta.

## Panel del negocio sin selector de idioma

- La barra superior del panel del dueño ya no muestra el selector Español / English. El panel del Super Admin ya no lo tenía (S1). El sitio público de cada negocio lo conserva, porque ahí el visitante elige su idioma (S4).

## Panel del negocio con vidrio, en blanco y rojo metalizado, y nueva página Inicio

- **Marco nuevo del panel del dueño**, como la referencia de diseño y con el mismo sistema de vidrio del Super Admin (clases `.platform` y `.platform-main`) en su propia paleta (`.owner`): blanco y rojo metalizado sobre un fondo rosado tenue.
  - Barra lateral de vidrio oscuro cálido con la inicial y el nombre del negocio, una tarjeta con la persona y su rol, y el menú en tres grupos (Día a día, Negocio, Gestión) con íconos. La opción activa va en rojo metalizado.
  - Barra superior de vidrio con buscador de clientes (lleva a Clientes con la búsqueda escrita), idioma, iniciales, nombre y rol, y Cerrar sesión. En el celular, el menú se abre desde un botón.
- **Inicio** (`/inicio`), la nueva primera página para el dueño y el administrador. Recepción y profesionales siguen entrando a la agenda.
  - Saludo según la hora, mes y negocio, y botón **Nueva cita** que abre el formulario en la agenda (`/agenda?nueva=1`).
  - Cuatro cifras: ventas del mes con el cambio frente al mes anterior, citas de hoy, ticket promedio y reservas web del mes.
  - Barras de ventas de los últimos 6 meses (el mes actual en rojo metalizado; los meses sin ventas en cero) y ventas por servicio del mes.
  - Todo sale de los reportes (M9), sin datos inventados. Plata en formato "$ 160.000".
- Dentro del panel, los cinco colores del tema quedan fijos en la paleta del panel. El tema de cada negocio sigue mandando en su sitio público. Esto arregla textos que casi no se veían con un tema oscuro (el título "Agenda" y el detalle de la cita).
- 4 pruebas nuevas en el frontend (136 en total). Revisado con `design-taste-frontend`: 0 fallas.

## Sitio público: botones con los colores del negocio y efecto vidrio

- **Cancelar la cita** ("Sí, cancelar"): deja el rojo fijo y usa un rojo apagado mezclado con la superficie del negocio, con el texto del tema encima (`.risk-button`). Se nota como peligro y combina con un tema claro u oscuro.
- **Reservar otra cita** (página de la cita) pasa de enlace subrayado a botón con ícono de calendario.
- **Efecto vidrio** al pasar el cursor, enfocar con el teclado o tocar cualquier botón del sitio público (reserva, página de la cita, portada y aviso de cookies): brillo diagonal y filo de luz por encima del color del botón y por debajo del texto. Se respeta "reducir movimiento".
- La portada ("Reservar cita") y el aviso de cookies usan los colores del negocio en vez del gris fijo.
- Todo el sitio público toma los tokens de la reserva (`.booking`): por ejemplo, la etiqueta "Motivo" al cancelar ya se lee sobre un tema oscuro (antes salía casi invisible).

## Super Admin: acciones de riesgo con confirmación, login y condiciones de uso con vidrio

- **Acciones de riesgo** (eliminar plan, quitar dominio, suspender y eliminar empresa): dejan el rojo, que no combinaba con el panel, y pasan a un **grafito oxidado con texto rosado claro** (contraste 10,8:1), de la familia oscura de la barra lateral. Se reconocen como peligro sin chocar.
- **Siempre piden confirmación** en una ventana propia (`ConfirmAction`): ícono de advertencia, qué va a pasar y dos botones; el foco empieza en **Cancelar** y Escape también cancela. Reemplaza la alerta del navegador al eliminar un plan y se agrega donde no había ninguna (quitar dominio, suspender). Eliminar una empresa sigue pidiendo además escribir su subdominio.
- **Login del Super Admin** (y recuperar o cambiar la contraseña en `admin.`): mismo vidrio que el panel. A la izquierda la tarjeta oscura con la marca y lo que se administra; a la derecha el formulario en vidrio claro con el botón metálico. El login de los negocios no cambia.
- **Condiciones de uso**: se arman como el panel, con el índice de secciones en la tarjeta oscura (enlaces a cada sección), el texto en vidrio claro y el aviso de borrador.
- La marca ("A" metalizada) y el vidrio oscuro quedan como piezas compartidas (`shared/ui/brand.tsx`, `brandStyles.ts`).
- Probado en el navegador con un Super Admin de prueba (ya borrado): la confirmación al eliminar un plan y al suspender, cancelando ambas, y el login y las condiciones a 1440 px.

## Panel del Super Admin con vidrio, en blanco, negro y verde metalizado

- Nuevo marco del panel siguiendo la referencia de diseño:
  - **Barra lateral de vidrio oscuro** con la marca, una tarjeta de la plataforma (negocios y planes) y el menú en dos grupos: **Plataforma** (Resumen, Empresas, Planes) y **Control** (Auditoría, Seguridad). La opción activa va en verde metalizado.
  - Contadores reales en el menú: empresas suspendidas, y códigos de recuperación cuando quedan 3 o menos.
  - **Barra superior de vidrio** con buscador de empresas (lleva a Empresas con la búsqueda escrita), iniciales y nombre del usuario, y Cerrar sesión.
  - En el celular, la barra lateral se abre como menú desde un botón.
- **Resumen** nuevo:
  - Saludo según la hora ("Buenas tardes, Laura"), mes y botón **Nueva empresa** en verde metalizado.
  - Cuatro cifras en tarjetas de vidrio con su explicación: negocios, activos, suspendidos y nuevos en 30 días.
  - Barras de negocios por plan (el plan con más negocios, en metal), reparto por tipo de negocio y últimos negocios creados. Todo sale de la API del resumen (S6), sin datos inventados.
- Empresas, detalle, planes, auditoría, seguridad y alta de empresa toman el mismo estilo: tarjetas y tablas de vidrio, botón principal metálico y títulos más grandes. Se hace con tokens bajo `.platform` en `index.css`, así el panel de los negocios y la reserva no cambian.
- Revisado con `design-taste-frontend`: 0 fallas. El vidrio, los degradados metálicos y las sombras van marcados como pedidos expresamente. Probado en el navegador a 1440 px y a 375 px.

## Cancelar la cita desde la confirmación, hasta 1 hora antes

- Al confirmar una reserva, la misma ventana trae **Cancelar mi cita** con la hora límite ("Puedes cancelarla en línea hasta el sábado 14 de noviembre, 8:15"). Pide confirmación y un motivo opcional; al cancelar, el título cambia a "Tu cita quedó cancelada" y el horario queda libre. La página de la cita (`/cita/<token>`) usa el mismo componente (`CancelAppointment`).
- **Ventana de 1 hora por defecto** (antes 2 h): el cliente puede cancelar hasta 1 hora antes; faltando exactamente 1 hora o menos, ya no (`409 cancel_window_closed`, con la hora límite en el mensaje). La migración `tenancy/0003` pasa a 1 h los negocios que seguían en 2 h por defecto; cada negocio puede cambiarla en la configuración de agenda. La spec se actualizó.
- 1 prueba nueva en el backend (817 en total) y 1 en el frontend (132). Probado en el navegador: reservar y cancelar desde la confirmación.

## Reserva: un servicio por categoría por defecto y citas para otra persona

- **"Solo uno por cita" activo por defecto** en todas las categorías (cortes, barba, cejas, líneas, depilación…): no se pueden elegir dos cortes en la misma cita, pero sí corte + barba + cejas. La migración `catalog/0003` lo activa también en las categorías que ya existían; el dueño puede apagarlo en una categoría desde el catálogo. Al crear una categoría nueva, la casilla viene marcada.
- **Reservar para otra persona** (el hijo, el papá, el hermano): al terminar una reserva aparece **Reservar otra cita para alguien más**. Abre la reserva de nuevo con los datos de contacto ya llenos y pide el nombre de quien va. La cita guarda ese nombre en `Appointment.attendee_name` (migración `booking/0002`).
- La regla de R3 ahora es por persona: el mismo cliente puede tener a la misma hora una cita para él y otra para su hijo (con otro profesional), pero no dos citas cruzadas para la misma persona (`409 customer_overlap`). El nombre se compara sin mayúsculas ni espacios de más.
- `attendee_name` (opcional) en `POST /public/appointments/` y `POST /appointments/`; se devuelve en la cita del panel y en la del enlace público, y se conserva al reprogramar. El panel muestra "Para Juan" en el detalle de la cita y el enlace de la cita muestra la fila **Para**.
- 3 pruebas nuevas en el backend (816 en total) y 1 en el frontend (131). Probado en el navegador: tres cortes seguidos dejan solo el último; un papá reservó para él y para su hijo a la misma hora con dos barberos.

## Rediseño de la reserva pública (sobre R9)

- La ventana de reserva toma el estilo de la referencia de diseño: tarjeta **Tu reserva** fija arriba (servicios, barbero, día, hora, duración y precio, que se actualizan con cada elección), servicios en tarjetas de 2 columnas, barberos en lista compacta con foto o inicial y especialidades, calendario de colores y horas en pestañas **Mañana / Tarde / Noche**. El botón dice lo que hace: "Seguir con las 15:45" y "Confirmar a las 15:45".
- Siguen los 3 pasos y todo lo anterior: "Cualquiera", detalle del servicio (R2), "Elige uno" (R3), fotos (R1 y R4), especialidades (R5), calendario por estado (R7) y los datos con la autorización de datos. El paso de datos ya no repite el resumen: está en la tarjeta de arriba.
- **Colores del tema de cada negocio**: todo sale de sus cinco colores y de mezclas de ellos (`.booking` en `index.css`), así funciona igual con un tema claro o uno oscuro. Lo elegido se marca invirtiendo texto y fondo; el color principal va en la hora y el día elegidos, el precio y el botón. Separación por tono, sin sombras ni bordes oscuros.
- Títulos en serif del sistema (`font-display`), sin descargar fuentes.
- El negocio de muestra de barbería (`seed_demo --vertical barbershop`) trae ahora el tema verde oscuro y dorado de la referencia. Cumple el contraste AA: texto 13,5:1 sobre el fondo y 10,6:1 sobre las superficies.
- Revisado con la skill de diseño (`design-taste-frontend`, estilo de app "true-black-flat"): 0 fallas; iconos dibujados en SVG en vez de caracteres que algunos teléfonos pintan como emoji. Probado a 375 px y en escritorio, con el tema oscuro y con el claro por defecto.
- La prueba de Playwright busca los botones nuevos ("Seguir con las…", "Confirmar a las…"); pasa en local.

## pormejorar §2: códigos de recuperación del 2FA (frente A)

- Al activar el 2FA, la respuesta de `POST /auth/2fa/confirm/` trae **10 códigos de un solo uso** (`xxxxx-xxxxx`, sin letras que se confundan). Es la única vez que se ven: el servidor guarda solo su SHA-256 en `User.totp_recovery_codes` (migración `accounts/0004`). Son aleatorios y largos (≈ 50 bits), así que no hace falta un hash lento.
- **Al entrar**, el campo del código acepta un código de recuperación en lugar de los 6 dígitos, con o sin guion y en mayúsculas o minúsculas. Cada uno sirve una vez. Uno inválido cuenta como intento fallido (`invalid_recovery_code`) para el límite de intentos.
- `POST /auth/2fa/recovery-codes/` (con sesión) genera códigos nuevos y anula los anteriores. Pide la contraseña y un código de la app, por si alguien dejó la sesión abierta.
- `/me/` trae `recovery_codes_left`. `reset_2fa` también borra los códigos.
- Auditoría: `auth.recovery_code_used` y `auth.recovery_codes_regenerated`, con su nombre en el filtro de la pantalla de auditoría.
- **Pantallas:**
  - Después de activar el 2FA aparece **Guarda tus códigos de recuperación**, con Copiar todos y Descargar .txt. No se sigue hasta marcar "Ya los guardé".
  - En el panel del Super Admin hay una página nueva, **Seguridad** (`/seguridad`). Muestra cuántos códigos quedan, avisa cuando quedan 3 o menos y permite generar otros.
- 9 pruebas nuevas en el backend (812 en total) y 1 en el frontend. Probado en el navegador con un Super Admin de prueba (ya borrado): activar, guardar, entrar con un código y generar otros.

## Mejora R9: la reserva en una ventana de 3 pasos (frente B, hecha por el frente A)

- El botón **Reservar cita** de la portada abre la reserva en una ventana encima de la portada. En el celular ocupa toda la pantalla; en pantallas grandes es una ventana centrada. `/reservar` sigue funcionando: abre la portada con la ventana encima.
- **De 5 pasos a 3:** servicios; profesional, día y hora en la misma vista (el calendario aparece al elegir profesional y las horas al elegir día, y la vista baja sola hasta ellas); y tus datos con el resumen.
- Se cierra con la ✕, con Escape o desde el navegador; al cerrarla se vuelve a la portada. Usa `<dialog>` nativo, como el detalle del servicio (R2), que ahora se abre encima de la reserva.
- Al cambiar de paso, la ventana vuelve arriba y el foco pasa al título, que también es el nombre de la ventana para los lectores de pantalla. La barra de **Volver / Continuar** queda siempre abajo.
- La prueba de Playwright ahora abre la reserva desde la portada y recorre los 3 pasos; pasa en local.
- Textos nuevos en español e inglés.

## Mejora S8: condiciones de uso de la plataforma (frente B, hecha por el frente A)

- Nueva página pública `/condiciones-de-uso`, igual en el host del Super Admin y en el de cada negocio. Es para el Super Admin y el equipo de cada negocio; los clientes que reservan siguen viendo los términos propios del negocio en `/terminos`.
- El texto es fijo y vive en las traducciones (`locales/<idioma>/terms.json`), en español e inglés. Cubre cuentas y acceso, uso permitido, datos de clientes según la Ley 1581 de 2012 (el negocio es responsable y la plataforma encargada), avisos por correo y WhatsApp, planes, disponibilidad y copias, suspensión y cierre, responsabilidad, cambios y ley aplicable.
- La página dice que es un **borrador de referencia** que debe revisar un abogado antes de abrir la plataforma a negocios reales.
- Enlaces: debajo del inicio de sesión (y de recuperar o cambiar la contraseña), al pie del panel del Super Admin y al final del menú del panel del negocio.
- 2 pruebas nuevas en el frontend: las secciones existen en los dos idiomas con el mismo número de párrafos, y la página no se rompe si falta la traducción.
- Nota para desarrollo: Vitest 5 guarda en `node_modules/.vitest-cache` el resultado de `import.meta.glob`. Al agregar un archivo de traducciones nuevo, borra esa carpeta si las pruebas no lo ven. El CI empieza sin caché y no se ve afectado.

## Mejora S6: resumen de la plataforma (frente B, hecha por el frente A)

- `GET /platform/summary/` (solo Super Admin) devuelve el total de negocios, cuántos están activos y suspendidos, los nuevos de los últimos 30 días, el reparto por plan y por tipo de negocio, y los 5 últimos negocios creados. Los negocios borrados no cuentan.
- El conteo vive en `tenancy.platform_summary`; `platform_admin` solo le suma la ventana de días.
- Panel del Super Admin: nueva página **Resumen** (`/resumen`), primera del menú y adonde llega el Super Admin al iniciar sesión. Tarjetas con los cuatro números, barras por plan y por tipo, y la lista de los últimos negocios con enlace a su detalle. Funciona a 375 px sin desplazamiento horizontal.
- Textos en español e inglés. 4 pruebas nuevas en el backend y 1 en el frontend.

## Mejora R3: reglas para combinar servicios y un cliente a la vez

- **Solo uno por cita por categoría.** Las categorías tienen el campo `single_choice` (migración `catalog/0002`). Si está activo, una cita no puede llevar dos servicios de esa categoría.
  - Ejemplo: con "Cortes" marcada, dos cortes juntos dan error. Un corte con barba, cejas o diseño sí se puede.
  - La API responde `400 one_per_category` al crear la cita y también al pedir horarios o días, en el panel y en la reserva pública.
- **Un cliente no puede estar en dos citas a la vez.** Si el mismo cliente (mismo celular) ya tiene una cita activa que se cruza con el horario, la API responde `409 customer_overlap` y dice cuál es.
  - Se bloquea la fila del cliente durante la reserva, así dos reservas simultáneas no pueden pasar las dos.
  - Sí se permite una cita justo después de otra, otra cita después de cancelar, y que otro cliente reserve la misma hora con otro profesional. Con el mismo profesional sigue saliendo `slot_taken`.
- **`/servicios`:** casilla "Solo un servicio de esta categoría por cita" al crear o editar una categoría, y la etiqueta "Uno por cita" en el título.
- **Asistente `/reservar`:** en esas categorías dice "Elige uno". Elegir otro servicio de la misma categoría reemplaza al anterior en vez de sumarlo.
- `GET /public/services/` incluye `single_choice` en cada categoría.
- Hubo que ajustar cuatro pruebas viejas que reservaban dos citas a la misma hora con el mismo cliente; ahora usan clientes distintos.
- **Pruebas:** 11 nuevas en el backend (761 en total) y 4 en el frontend (126 en total).

## Mejoras S1, S3, S4 y R2 (frente B)

- **S1:** el panel del Super Admin ya no tiene selector de idioma. El sitio de cada negocio y su panel lo conservan.
- **S3 y S4:** el alta de un negocio ya no pide zona horaria, moneda ni idioma. Se crea con Bogotá, COP y español, y el formulario lo dice. Se pueden cambiar después en los datos de la empresa, que siguen editables, y la API sigue aceptándolos.
- **R2:** en el paso de servicios de la reserva, cada servicio tiene un botón **Detalle** que abre una ventana con la foto grande, la descripción completa, la duración, el precio y el botón para agregarlo o quitarlo de la cita. Es un `<dialog>` nativo: maneja el foco, se cierra con Escape o tocando fuera y se anuncia como diálogo. En la lista, la descripción queda en 2 líneas.
- Textos en español e inglés. Probado en el navegador: el alta de un negocio queda con `America/Bogota`, `COP` y `es`, y la ventana de detalle funciona a 375 px.

## Mejora S11: integraciones por negocio (frente B)

- `GET /tenants/{id}/integrations/` (solo Super Admin) devuelve, por negocio:
  - **WhatsApp:** si el plan lo incluye, el proveedor de la plataforma (`fake`, `cloud_api` u `other`) y si está configurado.
  - **Correo:** el sistema de envío (`console`, `smtp`…).
  - **Por canal, en los últimos 30 días:** enviados, fallidos, en cola y último envío.
  - **Los 5 fallos más recientes** con fecha, tipo, canal, intentos y error (máximo 300 caracteres).
- **Privacidad:** el destinatario sale enmascarado (`+57•••••4567`, `c•••@example.com`).
- Cada app aporta su parte desde su `services.py` (`notifications.integration_summary` y `mask_recipient`), contando dentro del negocio (RLS).
- En el panel del Super Admin, el detalle de cada empresa tiene la pestaña **Integraciones**. Avisa cuando WhatsApp real no está configurado o cuando los correos no salen de verdad (consola). La tabla de fallos se desplaza dentro de su caja en el celular.
- Implementado con Codex y verificado: 19 pruebas nuevas (el backend pasa 789) y probado en el navegador con los envíos reales de la demo.

## M8 — Notificaciones por correo y WhatsApp (frente B)

- Nueva tabla `NotificationLog` (con RLS): tipo (`confirmation`, `reminder`, `cancellation`, `reschedule`), canal (`email`, `whatsapp`), destinatario, estado (`queued`, `sent`, `failed`), intentos, error, fecha de envío, asunto y texto. **Idempotente**: la misma cita, tipo y canal (y horas, en los recordatorios) se manda una sola vez, aunque Celery repita la tarea o el recordatorio corra de nuevo.
- **Cuándo se avisa:** al crear una cita (confirmación, o reprogramación si viene de otra), al cancelarla (desde el panel o por el enlace) y con los **recordatorios** 24 h y 2 h antes (`NOTIFICATION_REMINDER_HOURS`). Iniciar, completar o marcar inasistencia no avisan.
- **Enganche sin acoplar las apps:** `booking.events.notify` envía la señal `booking.signals.appointment_changed`; `notifications` la escucha (igual que la auditoría de M10). `booking` gana dos funciones de lectura para las notificaciones: `appointment_for_notification` y `confirmed_starting_between`.
- **Canal:** WhatsApp si el plan incluye `notifications_whatsapp` y hay consentimiento (el cliente aceptó mensajes o reservó él mismo en la web); si no, correo; sin ninguno de los dos no se manda nada.
- **Reintentos:** hasta 3 intentos con espera de 1, 2 y 4 minutos. Si WhatsApp los agota, el mismo mensaje sale por correo.
- **Proveedores:** correo con el `EmailBackend` de Django; WhatsApp detrás de `WhatsAppProvider` con `FakeProvider` (por defecto, no sale a internet) y `CloudApiProvider` (Meta, con `urllib`, sin dependencias nuevas). Ver `pormejorar.md` §36 y §37 antes de usar WhatsApp real.
- **Plantillas** por idioma (es, en) y vertical en `notifications/templates.py`, con las variables de la spec y el enlace absoluto de la cita (`PUBLIC_SITE_URL`). Fechas y horas en la zona del negocio.
- **Celery Beat** corre `notifications.send_reminders` cada 5 minutos por negocio activo, con la base `TenantTask` de M8.
- **Pruebas:** en `test.py` Celery corre en el mismo proceso y sin broker; antes, las pruebas con commits reales mandaban tareas al Redis de desarrollo. 26 pruebas nuevas; el backend pasa 770.
- Probado con el worker de Docker: una reserva web en `demo-barbershop` generó la confirmación por WhatsApp (FakeProvider) y la cancelación por enlace su aviso, ambos `sent`; Beat reparte los recordatorios por negocio.
- Variables nuevas en `.env.example`: `WHATSAPP_PROVIDER`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `NOTIFICATION_REMINDER_HOURS` y `PUBLIC_SITE_URL`.
- **Pendiente:** credenciales por negocio cifradas (necesita aprobar `cryptography`), plantillas aprobadas por Meta y la pantalla de integraciones (S11).

## M10 (parte 2) — Prueba de punta a punta con Playwright

- Dependencia nueva de desarrollo, aprobada: `@playwright/test`.
- `frontend/e2e/booking-to-commission.spec.ts` cubre el criterio de aceptación de M10 con un navegador real:
  1. Un cliente reserva en `/reservar`: servicio, barbero, primer día disponible, primera hora y sus datos.
  2. El dueño entra al panel, encuentra la cita en `/citas`, la inicia y la completa.
  3. La comisión aparece en `/reportes` y la cita cuenta en ventas.
- `e2e/global-setup.ts` crea un negocio nuevo en cada corrida con `seed_demo`, con un subdominio distinto, así no choca con datos viejos.
- **CI:** job `e2e` que levanta todo con `docker compose`, instala Chromium y corre la prueba. Si falla, sube el reporte de Playwright (capturas, video y traza) y muestra los logs de los contenedores.
- **Correr en local**, con el proyecto levantado:

  ```bash
  cd frontend && npx playwright install chromium && npx playwright test
  ```

- `.local/` queda en `.gitignore` para guardar credenciales de prueba sin subirlas.

## M10 (parte 1) — Endurecimiento: límites, auditoría, logs y copias

- **Límite de intentos** (`apps/accounts/throttle.py`):
  - El login cuenta los fallos por IP (20) y por correo (10) en 15 minutos. Pasado el límite responde `429 rate_limited` aunque la contraseña sea correcta.
  - Un acierto reinicia el contador del correo, así un atacante no puede dejar bloqueada la cuenta de otra persona por mucho tiempo.
  - La recuperación de contraseña se limita a 10 solicitudes por IP y 3 por correo cada 15 minutos.
  - Los contadores son por negocio y se pueden ajustar por variables de entorno.
- **Auditoría de seguridad:**
  - `accounts` emite eventos (`signals.security_event`) y `platform_admin` los guarda en `AuditLog`. Ninguna de las dos apps importa los modelos de la otra.
  - Se auditan los inicios de sesión correctos y fallidos (con el correo escrito, aunque no exista), los cambios y recuperaciones de contraseña, la activación del 2FA y el 2FA quitado por comando.
  - Nunca se guardan contraseñas ni códigos. La pantalla **Auditoría** del Super Admin ya los muestra y permite filtrarlos.
- **Logs:** cada línea JSON lleva `request_id` y el `tenant` cuando existen. La respuesta devuelve el `request_id` en `X-Request-ID`, y se reutiliza el que mande el proxy si es válido.
- **Copias de seguridad:**
  - `scripts/backup.sh` hace `pg_dump` de toda la base, la cifra con AES-256 y le agrega una suma SHA-256. Borra las copias viejas y, si se configura, sube la copia fuera del servidor.
  - `scripts/restore.sh` restaura en una base aparte para probar la copia.
  - Probado: se restauraron 1 negocio, 6 citas y 2 usuarios, y con la frase equivocada la restauración falla.
- **`docs/OPERACION.md`:** copias diarias con cron, prueba de restauración, restauración ante un incidente, monitoreo con `/healthz/`, cómo buscar en los logs, tabla de límites y acciones auditadas.
- `client_ip` pasa a `config/net.py` porque ahora la usan la reserva pública y el login.
- **Pruebas:** 9 nuevas. El backend pasa 750 y el frontend 122.
- **Pendiente de M10:**
  - Pruebas e2e con Playwright para reservar, completar y ver la comisión. Necesita aprobar la dependencia.
  - Sentry (también es una dependencia nueva).
  - Reactivar la 2FA.

## Mejora S10: uso del sistema por negocio

- `GET /tenants/{id}/usage/` (solo Super Admin) devuelve, por negocio:
  - Citas creadas en los últimos 30 días: cuántas fueron reservas web, cuántas se completaron y cuántas se cancelaron.
  - Citas totales y clientes.
  - Usuarios activos y el último ingreso de cualquiera de ellos.
- Las cifras de 30 días cuentan citas **creadas** en ese periodo: miden actividad, no agenda futura.
- Cada app aporta su parte desde su `services.py` (`booking.usage_counts`, `accounts.usage_for`). Las citas se cuentan dentro del negocio, así que RLS impide mezclar datos de otro.
- En el panel del Super Admin, el detalle de cada empresa tiene la pestaña **Uso** con esas cifras. Textos en español e inglés.
- **Pruebas:** 3 nuevas. El backend pasa 741 pruebas y el frontend 122.

## Mejora S5: datos del propietario al crear un negocio

- `POST /tenants/` acepta campos nuevos. En la API son opcionales, así que las integraciones actuales no se rompen.
  - `owner_phone`: celular del propietario.
  - `owner_document_type`: tipo de documento. Puede ser `CC`, `CE`, `PA` o `PPT`.
  - `owner_document_number`: número de documento.
  - `tax_id`: NIT o RUT del negocio, con o sin dígito de verificación.
- Validaciones: el tipo y el número de documento van juntos; la cédula solo lleva números; el celular tiene de 7 a 15 dígitos; el NIT tiene de 6 a 12 dígitos y un dígito de verificación opcional.
- El documento y el teléfono se guardan en el usuario propietario (`accounts`, migración `0003_user_document`). El NIT se guarda en `Company.tax_id`.
- El documento no se guarda en la auditoría.
- **La contraseña sigue siendo temporal**: el Super Admin no la escribe. Así la contraseña definitiva solo la conoce el propietario.
- El formulario `/empresas/nueva` del Super Admin pide celular, tipo y número de documento. El NIT es opcional. Textos en español e inglés.
- **Pruebas:** 10 nuevas en el backend (738 en total) y 6 en el frontend (122 en total).

## Pantallas de M9, R5 y R7 (frente B, hechas por el frente A)

- **`/reportes`** (spec §11 y §13), con tres pestañas según los módulos del plan:
  - **Ventas:** total de ventas, comisiones, parte del negocio, citas y ticket promedio. Tabla por día, semana, mes, profesional o servicio.
  - **Reservas:** total, completadas y tasas de cancelación y de inasistencia, por mes, por servicio y por profesional.
  - **Comisiones:** lista paginada. Los ajustes salen marcados y con su motivo.
  - El dueño puede **ajustar** una comisión: escribe los valores correctos y un motivo, y la original se conserva.
  - **Filtros:** este mes, mes anterior, últimos 7 días, o fechas a mano (en la zona horaria del negocio, máximo un año). El filtro por profesional solo aparece a quien ve a todo el equipo; un profesional ve solo lo suyo.
  - Botón **Descargar CSV** en cada pestaña.
  - Las tablas se desplazan de lado en el celular, sin que la página se salga del ancho.
- **Asistente de reserva:**
  - **R5:** las especialidades de cada barbero aparecen como etiquetas en el paso "¿Con quién?".
  - **R7:** el calendario pinta cada día como disponible, lleno o cerrado, con una leyenda. El estado también va en el nombre accesible del día (por ejemplo, "domingo, 15 de noviembre: Cerrado"). Si la API no manda `calendar`, usa `days` como antes.
- Textos en español e inglés (`reports.json`, más claves en `booking.json` y el error `invalid_adjustment`).
- 9 pruebas nuevas (rangos de fechas, parámetros y estado de cada día). El frontend pasa sus 116 pruebas, typecheck, lint y build.
- Probado en el navegador con el negocio demo, en escritorio y a 375 px: reportes, ajuste de una comisión, especialidades y colores del calendario.

## Mejoras R5 y R7 de la reserva: API (frente A)

- **R5. Especialidades en la reserva.** `GET /public/professionals/` incluye `specialties`: una lista `{id, name}` por cada barbero, en orden alfabético y sin las borradas. Se cargan en una sola consulta para todos.
- **R7. Estado de cada día.** `GET /public/availability/days/` y `GET /availability/days/` agregan `calendar`, con todos los días del mes y su estado:
  - `available`: hay al menos un horario libre.
  - `full`: alguien trabaja ese día, pero las citas o el aviso mínimo ya no dejan horarios.
  - `closed`: nadie atiende, porque no hay horario o el día está bloqueado (festivo, vacaciones).
  - `unavailable`: fuera de la ventana de reserva (días pasados o más allá de `max_advance_days`).
  - Con "cualquiera", el día está lleno solo si ningún profesional tiene cupo. Una cita cancelada vuelve a liberar el día.
  - `days` sigue igual (solo los disponibles), así que las pantallas actuales no cambian.
- El enum nuevo se llama `CalendarDayStatusEnum` y el estado de la cita conserva el nombre `StatusEnum` en el OpenAPI.
- 10 pruebas nuevas. La suite completa pasa: 728 pruebas.
- **Pendiente (frente B):** los colores del calendario y las especialidades en el paso "Profesional" del asistente.

## M9 — Comisiones y reportes: API (frente A)

- **Comisiones** (`apps/commissions`, spec §11):
  - Al pasar una cita a `completed` se crea un `CommissionEntry` por cada servicio, en la misma transacción. El porcentaje es el que se congeló al reservar (`commission_pct_snapshot`), así que cambiar el porcentaje del profesional después no altera citas ya reservadas.
  - Cálculo: `comisión = valor × % / 100`, redondeada al centavo con la mitad hacia arriba, y `negocio = valor − comisión`. Una restricción en la base garantiza que las dos partes sumen el valor.
  - **Inmutables.** No se pueden editar ni borrar, ni desde el ORM ni con SQL directo: un trigger de PostgreSQL lo impide. Completar dos veces no duplica (restricción única por servicio de la cita).
  - **Ajustes.** `POST /commissions/{id}/adjustments/` recibe los valores corregidos y guarda la diferencia como una fila `adjustment` enlazada a la original. Solo el dueño (nueva acción `adjust` en la matriz de permisos).
  - `GET /commissions/` (paginado por cursor) y `GET /commissions/export/` (CSV), con filtros `from`, `to`, `professional_id`, `service_id`, `category_id` y `kind`.
  - Cancelar o marcar no-show no genera comisión.
- **Reportes** (`apps/reports`):
  - `GET /reports/sales/`: ventas, comisiones, parte del negocio, número de citas y ticket promedio. Agrupa por `day`, `week`, `month`, `professional` o `service`. Solo cuentan las citas completadas, y los ajustes ya van sumados.
  - `GET /reports/bookings/`: reservas por mes, por profesional y por servicio, con tasas de cancelación y de no-show. No cuenta las citas `rescheduled`, porque la reserva sigue en la cita nueva.
  - `export/` en los dos devuelve CSV.
- **Comunes a todo:**
  - `from` y `to` son días locales del negocio e incluyen ambos extremos. Por defecto es el mes en curso, y el rango máximo es un año. Una cita a las 23:30 del 31 de marzo en Bogotá queda en marzo aunque en UTC ya sea abril.
  - Un profesional solo ve sus filas aunque pida las de otro, y si no tiene ficha enlazada no ve nada. La recepción recibe 403.
  - Cada endpoint exige su módulo del plan (`commissions` o `reports`).
  - CSV en UTF-8 con BOM (Excel muestra bien las tildes). Los textos que empiezan con `=`, `+`, `-` o `@` se escapan para evitar inyección de fórmulas.
- **Pruebas:** 45 nuevas. Los valores se comparan con un negocio de ejemplo calculado a mano (tabla en `tests/reports/shop.py`). Cubren redondeo, inmutabilidad, ajustes, zona horaria, permisos, módulos, aislamiento entre negocios y CSV. La suite completa pasa: 718 pruebas.
- **Pendiente (frente B):** la pantalla `/reportes`.

## M8 — Tareas de Celery con el negocio activo (frente A)

- `apps/tenancy/tasks.py`, base para las tareas de notificaciones del frente B (spec §4.5):
  - **`TenantTask`**: la tarea recibe el id del negocio como primer argumento y corre dentro de `tenant_context`, así el ORM y RLS ven solo ese negocio, igual que en una petición. Al terminar (bien, con error o con reintento) el worker queda sin negocio: la siguiente tarea del mismo proceso no hereda el anterior. Si el negocio no existe o está suspendido, la tarea no corre.
  - **`delay_on_commit(task, tenant, ...)`**: encola cuando la transacción se confirma; el worker nunca procesa una cita que no se guardó.
  - **`tenancy.for_each_active_tenant`**: tarea para Celery Beat que encola otra tarea una vez por negocio activo (cada uno con su contexto; un error en uno no frena a los demás). Solo acepta tareas con `TenantTask`.
- Uso, en el docstring del módulo. Verificado con el worker real de Docker: registra y ejecuta la tarea.
- 8 pruebas: aislamiento por ORM y por SQL directo (RLS), tareas seguidas sin herencia, contexto anidado, error que libera el negocio, negocios suspendidos, encolado tras commit y recorrido por negocios.

## M7 — Corrección: el flujo de eventos fallaba en el navegador

- `GET /api/v1/events/` respondía **406** a los navegadores. `EventSource` siempre manda `Accept: text/event-stream` y la vista solo aceptaba JSON, así que la agenda nunca recibía eventos.
- Se arregla con un `EventStreamRenderer` en `EventsView`: acepta ese `Accept` y los errores previos al flujo (401, 403) siguen saliendo como JSON.
- Las pruebas de `test_events.py` ahora piden el flujo como el navegador, y hay dos pruebas de regresión: 200 con sesión y 401 en JSON sin sesión. Sin el arreglo, 5 pruebas fallan con 406.

## M6 — Reserva pública: pantallas (frente B)

- `/` (host del negocio): portada mínima con logo, nombre, dirección, teléfono, redes y el botón **Reservar cita**. Si el negocio no recibe reservas, lo dice.
- `/reservar`: asistente de 5 pasos, mobile-first:
  1. **Servicios.** Varios a la vez (máximo 10), con total de tiempo y precio.
  2. **Profesional.** "Cualquiera" o alguien que ofrezca todos los servicios.
  3. **Día.** Calendario del mes, de lunes a domingo, con solo los días disponibles.
  4. **Hora.** Agrupada en mañana, tarde y noche.
  5. **Datos.** Nombre, celular y correo opcional. La autorización de datos (Ley 1581) viene **sin marcar** y es obligatoria, con enlace a la política. El consentimiento de WhatsApp es opcional. Incluye el honeypot `website`.
  - Al confirmar se muestra el resumen y el enlace para gestionar la cita.
  - `409 slot_taken` ofrece los horarios sugeridos para elegir otro sin volver atrás; `429 rate_limited` y los errores de campo se muestran traducidos.
  - Fechas y horas en la zona del negocio; "hoy" también se calcula en esa zona.
  - El foco pasa al título de cada paso y el botón principal queda fijo abajo en el celular.
- `/cita/:token`: estado, fecha, profesional, sede, servicios y total. Permite cancelar con motivo opcional hasta el plazo del negocio, que se muestra; pasado el plazo explica que hay que comunicarse con el negocio. Un enlace inválido da un aviso claro.
- `/terminos`, `/privacidad` y `/cookies`: el texto del negocio (HTML ya limpio en el servidor), o un aviso si aún no lo publicó.
- Marco público con el tema del negocio, logo, enlaces legales y el idioma del negocio si el visitante no eligió otro.
- Aviso de cookies informativo: solo hay cookies necesarias y el idioma, nada que aceptar o rechazar.
- Cada página pública va en su propio paquete (lazy).
- `formatMoney` pasa a `shared/money.ts` porque lo usan el panel y la reserva.
- 12 pruebas nuevas: calendario (meses, bisiesto, "hoy" en la zona del negocio), suma de precios en centavos, agrupación de horarios, celular y cuerpo de la reserva.
- Probado en el navegador a 375 px:
  - Reserva completa con el negocio `demo` en menos de un minuto.
  - Validaciones antes de enviar.
  - Página de la cita dentro y fuera del plazo de cancelación, y cancelación.
  - Página legal y aviso de cookies, en español y en inglés.
- El total antes de confirmar se muestra como **precio de referencia**: la API pública no expone el precio propio de cada profesional, y el valor real sale en la confirmación.

## M7 — Agenda, citas y clientes: pantallas (frente B)

- `/agenda`:
  - Vista **día** (columna por profesional) y **semana** (columna por día, de lunes a domingo), con anterior, hoy y siguiente, y filtro por profesional.
  - Las citas simultáneas van en carriles. La grilla abre a las 7:00, con cabeceras fijas.
  - En el celular la vista día es una lista y la semana se desplaza dentro de su caja.
- **Tiempo real**: `useAppointmentEvents` abre `EventSource("/api/v1/events/")`; con cada `appointment.created|updated|cancelled` refresca las citas y los horarios libres. Muestra "En vivo" o "Reconectando…".
- `/citas`:
  - Lista por cursor con filtros de fechas (hoy + 7 días por defecto), profesional y estados. Desde `/clientes` se llega filtrado por cliente, con un filtro quitable.
  - Formulario de **nueva cita** compartido con la agenda: servicios, profesional o "cualquiera", día y horario libre, y un cliente existente (búsqueda) o nuevo. `409 slot_taken` ofrece las sugerencias.
  - Panel de detalle con las **acciones** que permiten el estado (spec §7) y el rol: confirmar, iniciar, completar, marcar inasistencia, cancelar con motivo y reprogramar.
- `/clientes`:
  - Búsqueda con debounce por nombre o celular, lista por cursor, crear, editar y borrar.
  - La autorización de datos (Ley 1581) viene sin marcar y es obligatoria.
  - `409 customer_exists` se marca en el campo celular, y hay un enlace "Ver citas".
- Fechas y horas en la zona del negocio. Textos en `locales/{es,en}/agenda.json`.
- Lógica en módulos con pruebas (`agenda/calendar.ts`, `appointments/transitions.ts`, `appointments/schemas.ts`): 14 pruebas nuevas.
- Implementado con Codex y revisado y probado en el navegador (ver el PR).

## M7 — Eventos en tiempo real y clientes (API, frente A)

- **`GET /api/v1/events/`** (Server-Sent Events, spec §9): la agenda abierta recibe `appointment.created`, `appointment.updated` y `appointment.cancelled` con `{id, status, start_at, end_at, professional_id, resource_id}`. El navegador lo abre con `new EventSource("/api/v1/events/")` y la misma sesión; reconecta solo (`retry: 3000`) y recibe un comentario cada 15 s para que ningún proxy corte la conexión.
  - Redis pub/sub, un canal por negocio. Cada cambio de cita (panel, web, cancelación por enlace, reprogramación, puesto) publica **después del commit**: la agenda nunca ve una cita que se deshizo. Si Redis falla, la cita igual se guarda.
  - El profesional solo recibe los eventos de sus citas. Exige sesión y el módulo `booking`.
  - El flujo no consulta la base: negocio y alcance se deciden antes de empezar (el tenant ya no está activo durante el streaming).
- **Clientes** `customers/` (CRUD): búsqueda por nombre o celular (`?q=`), número de citas, cumpleaños y notas. Alta con `data_consent: true` (Ley 1581). Un celular pertenece a un solo cliente (`409 customer_exists`). Borrado lógico: sus citas se conservan. Solo quien ve todas las citas (propietario, administrador y recepción); el profesional recibe 403.
- **Aceptación**: una reserva hecha en la web llega como evento al flujo SSE de la agenda abierta (`tests/booking/test_events.py`). Falta la pantalla `/agenda` del frente B para verlo en el navegador.

## M6 — Reserva pública (API, frente A)

- Endpoints sin sesión en el host del negocio (spec §9), con fechas en su zona horaria:
  - `GET /api/v1/public/company/`: nombre, logo, tema, idioma, contacto, redes, textos legales, `cancel_min_hours` y si recibe reservas. Responde aunque el módulo `booking` esté apagado; nunca expone NIT ni razón social.
  - `GET /api/v1/public/services/`: servicios activos agrupados por categoría.
  - `GET /api/v1/public/professionals/?service_ids=`: solo quienes ofrecen todos los servicios y aceptan reserva en línea.
  - `GET /api/v1/public/availability/days/` y `slots/`: el motor de M5 con las reglas del negocio (anticipación mínima y días hacia adelante). Con "cualquiera" no se revela quién atiende.
  - `POST /api/v1/public/appointments/`: crea la cita `confirmed` con origen `web`; exige `accept_data_policy: true` (Ley 1581) y devuelve `manage_url` (`/cita/<token>`). Hueco ocupado: `409 slot_taken` con sugerencias.
  - `GET /api/v1/public/appointments/{token}/` y `POST …/{token}/cancel/`: ver y cancelar por enlace, solo hasta `cancel_min_hours` antes (`409 cancel_window_closed`).
- Protecciones: honeypot (`website` debe ir vacío), captcha opcional (`PUBLIC_BOOKING_CAPTCHA`, compatible con Turnstile/hCaptcha/reCAPTCHA, sin dependencias nuevas) y límites por hora por negocio: 10 POST por IP y 5 por celular (`429 rate_limited`). La IP sale de `X-Forwarded-For` según `TRUSTED_PROXY_COUNT` (Caddy = 1), así que detrás del proxy cada cliente tiene su propio contador y una IP falsa antepuesta no salta el límite.
- `catalog.services.active_services()` (lectura, para el listado público).
- Variables nuevas documentadas en `.env.example`.

## M5 — Negocio de demostración (`seed_demo`, frente B)

- `manage.py seed_demo --vertical barbershop|salon|nails [--slug] [--password]` (spec §16):
  - Crea el negocio (`demo-<vertical>` por defecto) con su subdominio, la empresa, la sede y el propietario (`propietario@<slug>.test`).
  - Crea 3 profesionales y 6 servicios del vertical en 2 categorías. El tercer profesional solo ofrece 4 servicios, así "cualquiera" no siempre devuelve a los 3.
  - Horario de lunes a sábado de 9:00 a 19:00 y 6 citas de muestra en los próximos 3 días hábiles.
  - Usa el plan `Demo` con todos los módulos.
- Todo pasa por los `services.py` de cada app (las mismas reglas que la API) y en una sola transacción: si algo falla no queda nada a medias.
- No sobrescribe un subdominio que ya existe. Si no se da `--password`, la genera y la muestra una sola vez.
- Vive en `platform_admin` porque crea negocios. Documentado en el `README`. 7 pruebas, incluido que el propietario entra y la reserva pública lista los 6 servicios.

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

## M4 — Pantalla de horarios y bloqueos (frente B)

- `/horarios`: elige el profesional (el profesional ve solo el suyo) y edita su **semana**: franjas por día con descansos, "copiar el lunes de martes a viernes" y total de horas semanales. Avisa antes de guardar si una franja está vacía, termina antes de empezar o se cruza con otra del mismo día; el servidor valida lo mismo.
- **Bloqueos de agenda** del profesional: lista de los próximos, crear (desde, hasta, motivo) y borrar. Las fechas se envían sin zona y el servidor las interpreta en la hora del negocio; se muestran en la zona del negocio. Si el bloqueo choca con citas, se muestra el `409 time_block_conflict` traducido con la lista de citas en conflicto.
- Quien solo puede ver recibe la pantalla en modo lectura. Un profesional cuya cuenta no está enlazada a una ficha recibe un aviso para pedir que la enlacen.
- Lógica de la semana en `hours/week.ts`, con 5 pruebas.
- Probado en el navegador: semana con descanso, aviso de franjas cruzadas, bloqueo rechazado por una cita (409) y bloqueo creado y borrado; escritorio y 375 px.

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
