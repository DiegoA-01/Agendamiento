# Prueba manual completa (Fase 1)

Lista para recorrer todo el sistema antes de pedir la revisión del encargado. Marca cada casilla cuando el resultado sea el esperado. Si algo falla, anota la pantalla, qué hiciste, qué esperabas y qué pasó, con una captura.

**Duración aproximada:** 1 a 1,5 horas.

---

## 0. Preparación

- [ ] `develop` al día: `git checkout develop && git pull`.
- [ ] Sistema arriba y migraciones aplicadas:
  ```bash
  docker compose up -d
  docker compose exec api python manage.py migrate
  ```
- [ ] En `.env` está `REQUIRE_TWO_FACTOR=1`, y en `docker compose logs api` **no** aparece "Verificación en dos pasos DESACTIVADA".
- [ ] Negocio demo creado:
  ```bash
  docker compose exec api python manage.py seed_demo --vertical barbershop
  ```
  Guarda el correo y la contraseña del propietario que imprime el comando, solo en tu equipo. Nunca en el repositorio.
- [ ] Ten a mano una app de autenticación en el celular (Google Authenticator, Microsoft Authenticator o Authy).

| Qué | Dirección |
|---|---|
| Super Admin | http://admin.localhost:8080 |
| Sitio y panel del negocio demo | http://demo-barbershop.localhost:8080 |

Repite las secciones 3 y 4 en el celular, o en el navegador con el ancho de un celular (375 px).

---

## 1. Super Admin: entrada y seguridad

- [ ] El login muestra el enlace **Condiciones de uso** debajo. Abre una página con 11 secciones y el aviso de "borrador".
- [ ] Entrar con el Super Admin sin 2FA pide **activarlo**: muestra una clave manual y un campo de 6 dígitos.
- [ ] Al escribir el código de la app, aparece **Guarda tus códigos de recuperación** con 10 códigos.
  - [ ] **Copiar todos** los copia, y **Descargar .txt** baja el archivo con los 10.
  - [ ] **Continuar** está deshabilitado hasta marcar "Ya los guardé".
- [ ] Llegas a **Resumen**.
- [ ] Cerrar sesión y volver a entrar **pide el código** de 6 dígitos.
- [ ] Un código equivocado da error y no deja entrar.
- [ ] Entrar con **un código de recuperación** en lugar de los 6 dígitos funciona. Ese mismo código ya no sirve una segunda vez.
- [ ] **Seguridad** dice cuántos códigos quedan. **Generar códigos nuevos** con contraseña y código de la app entrega 10 nuevos; los viejos dejan de servir.
- [ ] Varios intentos de contraseña equivocada seguidos bloquean el ingreso por un rato.

## 2. Super Admin: negocios, planes y auditoría

- [ ] **Resumen**: los números de negocios activos, suspendidos y nuevos cuadran con **Empresas**. Las barras por plan y por tipo suman el total.
- [ ] **Planes**: crear un plan con algunos módulos y editarlo.
- [ ] **Empresas → Nueva empresa**:
  - [ ] No pide zona horaria, moneda ni idioma (S3 y S4).
  - [ ] Pide teléfono, tipo y número de documento del propietario y NIT (S5). Valida los formatos.
  - [ ] Al crearla muestra la **contraseña temporal** del propietario. Cópiala.
- [ ] En el detalle de la empresa revisa cada pestaña:
  - [ ] **Datos**: se pueden editar.
  - [ ] **Tema**: los colores con poco contraste dan aviso.
  - [ ] **Módulos**: se pueden activar y desactivar.
  - [ ] **Dominios**: se puede agregar uno; sin DNS no se verifica.
  - [ ] **Uso**: muestra citas, reservas web, usuarios y último ingreso.
  - [ ] **Integraciones**: dice que WhatsApp es de prueba (FakeProvider) y que el correo sale por consola.
- [ ] **Suspender** la empresa nueva: su sitio deja de funcionar. **Reactivarla**: vuelve a funcionar.
- [ ] **Auditoría** registra lo que hiciste: creaciones, suspensión, ingresos, códigos de recuperación. Los filtros funcionan.
- [ ] Nunca aparece un selector de idioma en el panel del Super Admin (S1).

## 3. Sitio público del negocio (cliente sin cuenta)

En http://demo-barbershop.localhost:8080:

- [ ] La portada muestra logo, nombre, dirección, teléfono y el botón **Reservar cita**. El aviso de cookies se cierra con "Entendido".
- [ ] El selector de idioma cambia todo el sitio entre español e inglés.
- [ ] **Reservar cita** abre una **ventana** encima de la portada (R9). En el celular ocupa toda la pantalla.
- [ ] La ✕ y la tecla Escape la cierran y vuelven a la portada. Abrir `/reservar` directamente también muestra la ventana.

**Paso 1 de 3: servicios**
- [ ] Cada servicio muestra foto, precio y duración (R1). **Detalle** abre la foto grande y la descripción completa (R2).
- [ ] En "Cortes" dice **Elige uno**: elegir un segundo corte reemplaza al primero (R3).
- [ ] Un corte + barba o cejas sí se puede.
- [ ] El total de tiempo y precio se actualiza.

**Paso 2 de 3: con quién y cuándo**
- [ ] Los barberos muestran foto (R4) y especialidades (R5). Está la opción **Cualquiera**.
- [ ] Al elegir barbero aparece el calendario con colores: disponible, lleno y cerrado, con su leyenda (R7).
- [ ] Al elegir un día, la vista baja a las horas, agrupadas en mañana, tarde y noche.
- [ ] Solo salen horas libres, y nada dice quién más reservó (R8).

**Paso 3 de 3: tus datos**
- [ ] El resumen muestra servicios, fecha, hora, barbero y precio.
- [ ] Sin nombre, con un celular inválido o sin marcar la autorización de datos, no deja confirmar y explica por qué.
- [ ] **Confirmar reserva** muestra "¡Listo, tu cita está reservada!" con el enlace para gestionarla.
- [ ] El enlace `/cita/...` muestra la cita y permite **reprogramarla** y **cancelarla**.
- [ ] Al reservar, cancelar y reprogramar aparece un aviso en **Integraciones** del Super Admin, o en `docker compose logs worker` si sale por correo.

**Reglas que deben frenar**
- [ ] Reservar otra vez con el **mismo celular** a una hora que se cruza, con otro barbero, da error: ya tienes una cita (R3).
- [ ] Otra persona, con otro celular, **sí** puede tomar esa misma hora con otro barbero.
- [ ] Dos personas no pueden tomar la misma hora con el **mismo** barbero: la segunda ve "ya no está disponible" y sugerencias.
- [ ] Los enlaces del pie (Términos, Privacidad, Cookies) abren los textos del negocio.

## 4. Panel del negocio (propietario)

Entra en http://demo-barbershop.localhost:8080/login con el propietario del demo:

- [ ] Con una contraseña temporal (la de la empresa nueva del punto 2), obliga a **cambiarla** antes de seguir.
- [ ] El menú tiene Agenda, Citas, Clientes, Servicios, Equipo, Puestos, Horarios, Reportes y Empresa, más **Condiciones de uso** al final.
- [ ] **Agenda**:
  - [ ] Muestra la cita del punto 3, en vista de día y de semana.
  - [ ] Con la agenda abierta, reservar otra cita desde el sitio público (en otra pestaña) hace que **aparezca sola**, sin recargar.
- [ ] **Citas**: filtrar por fechas. En una cita: **Iniciar**, luego **Completar**. El estado cambia en la tarjeta.
- [ ] Probar también **No asistió** y **Cancelar** en otras citas.
- [ ] **Clientes**: aparece quien reservó, con su celular; se puede buscar y editar.
- [ ] **Servicios**:
  - [ ] Crear y editar un servicio con foto.
  - [ ] En una categoría, activar y desactivar **Uno por cita**; la reserva pública lo respeta.
- [ ] **Equipo**: un barbero con foto, especialidades y servicios.
- [ ] **Horarios**: cambiar el horario de un barbero o agregar un bloqueo, y comprobar que la reserva pública ya no ofrece esas horas.
- [ ] **Reportes**:
  - [ ] **Ventas** por día, semana, mes, profesional y servicio. La cita completada cuenta.
  - [ ] **Reservas**: los totales cuadran con lo que hiciste.
  - [ ] **Comisiones**: la cita completada tiene su comisión. Un ajuste crea una fila nueva y no edita la original.
  - [ ] **Exportar CSV** baja un archivo que abre bien en Excel, con tildes correctas.
- [ ] **Empresa**: cambiar datos y textos legales; el sitio público los muestra.

## 5. Permisos por rol

El panel todavía no tiene pantalla para crear cuentas del equipo (`pormejorar.md` §39), y el demo no las trae. Créalas por comando. El profesional queda enlazado al primer barbero del demo. Elige tú las contraseñas (mínimo 10 caracteres) y no las subas al repositorio:

```bash
docker compose exec api python manage.py shell
```
```python
from apps.accounts.services import create_tenant_user
from apps.catalog.models import Professional
from apps.tenancy.context import tenant_context
from apps.tenancy.models import Tenant

shop = Tenant.objects.get(slug="demo-barbershop")
with tenant_context(shop):
    create_tenant_user(tenant=shop, email="recepcion@demo.test", full_name="Recepción Demo",
                       role="receptionist", password="ESCRIBE-UNA-CLAVE")
    pro = create_tenant_user(tenant=shop, email="barbero@demo.test", full_name="Barbero Demo",
                             role="professional", password="ESCRIBE-OTRA-CLAVE")
    barber = Professional.objects.order_by("display_name").first()
    barber.user = pro
    barber.save()
    print("Profesional enlazado a", barber.display_name)
```


- [ ] El **recepcionista** ve la agenda y las citas, pero no reportes de comisiones ni datos de la empresa.
- [ ] El **profesional** solo ve **sus** citas y **sus** comisiones.
- [ ] Una cuenta de negocio **no puede** entrar a http://admin.localhost:8080.
- [ ] El propietario de un negocio no ve nada del otro negocio (la empresa creada en el punto 2).

## 6. Cierre

- [ ] Revisa el registro de errores de cada servicio: no debe haber errores 500.
  ```bash
  docker compose logs api worker beat | grep -i "error\|traceback"
  ```
- [ ] Anota lo que falló en un issue o en `pormejorar.md`, con la sección de esta lista.
- [ ] Si todo pasó, marca la prueba manual como hecha en `progress.md` (§6) y prepara el PR de `develop` a `main` para la revisión del encargado.
