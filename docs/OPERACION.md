# Operación

Guía para quien opera el servidor: copias de seguridad, monitoreo, logs y límites de seguridad. Corresponde a M10 y a la spec §15.

## 1. Copias de seguridad

### Crear una copia

```bash
BACKUP_PASSPHRASE='frase-larga-guardada-fuera-del-servidor' scripts/backup.sh
```

El script hace lo siguiente:

- Usa `pg_dump` con el usuario dueño de la base. La copia incluye las filas de todos los negocios, porque RLS no aplica a ese usuario.
- Cifra la copia con AES-256. Sin la frase, el archivo no se puede leer.
- Deja la copia en `backups/agenda-AAAAMMDD-HHMMSS.dump.enc`, con un `.sha256` al lado para comprobar que el archivo está completo.
- Borra las copias locales con más de `BACKUP_KEEP_DAYS` días (14 por defecto).
- **Sube la copia fuera del servidor** si `BACKUP_UPLOAD_CMD` está definido. `{}` se reemplaza por la ruta del archivo:

  ```bash
  BACKUP_UPLOAD_CMD='rclone copy {} remoto:agenda-backups' scripts/backup.sh
  ```

  Una copia que solo vive en el mismo servidor no sirve si se pierde el disco.

**Guarda la frase de cifrado en un gestor de contraseñas, fuera del servidor.** Si se pierde, las copias no se pueden recuperar.

### Programarla todos los días

Ejemplo de cron en el servidor, a las 3:15 a. m.:

```cron
15 3 * * * cd /srv/agenda && BACKUP_PASSPHRASE="$(cat /root/.agenda-backup-pass)" BACKUP_UPLOAD_CMD='rclone copy {} remoto:agenda-backups' scripts/backup.sh >> /var/log/agenda-backup.log 2>&1
```

### Probar que la copia sirve

Una copia que nunca se restauró no es una copia. Prueba una al menos una vez al mes:

```bash
BACKUP_PASSPHRASE='...' scripts/restore.sh backups/agenda-AAAAMMDD-HHMMSS.dump.enc
```

Restaura en una base **nueva**, `agenda_restore_check`, sin tocar la base en uso. Al final muestra cuántos negocios, citas, usuarios y migraciones tiene la copia. Después bórrala:

```bash
docker compose exec postgres dropdb -U agenda agenda_restore_check
```

### Restaurar sobre la base real (incidente)

Esto reemplaza los datos actuales. Hazlo solo si la base en uso se perdió o se dañó.

1. Detén la API y los workers:

   ```bash
   docker compose stop api worker beat
   ```

2. Restaura en una base nueva y revisa los conteos:

   ```bash
   scripts/restore.sh <archivo> agenda_nueva
   ```

3. Cambia los nombres de las bases. La actual queda guardada como `agenda_danada`:

   ```bash
   docker compose exec postgres psql -U agenda -d postgres -c 'ALTER DATABASE agenda RENAME TO agenda_danada' -c 'ALTER DATABASE agenda_nueva RENAME TO agenda'
   ```

4. Levanta los servicios. Si la API no puede leer las tablas, vuelve a aplicar `docker/postgres/create_app_role.sql` para dar permisos al rol de la aplicación:

   ```bash
   docker compose up -d
   ```

5. Comprueba `/healthz/` y entra al panel.

## 2. Monitoreo

- **`GET /healthz/`** responde 200 si la base de datos y Redis contestan, y 503 si alguno falla. Apunta ahí un monitor de disponibilidad externo, por ejemplo UptimeRobot o Better Stack, revisando cada minuto y con alerta por correo o WhatsApp.
- **Errores:** la spec pide Sentry (§15). No está instalado porque `sentry-sdk` no está en la lista de dependencias aprobadas; hay que pedir la aprobación antes de agregarlo.

## 3. Logs

Cada línea de log es un JSON con `ts`, `level`, `logger` y `message`, más:

- `request_id`: identifica la petición. También vuelve al navegador en el header `X-Request-ID`. Si el proxy manda su propio `X-Request-ID`, se reutiliza.
- `tenant`: el subdominio del negocio, cuando la petición o la tarea es de un negocio.

Si un cliente reporta un error, pídele la hora o el `X-Request-ID` y filtra por ese valor:

```bash
docker compose logs api | grep '"request_id": "abc123..."'
```

## 4. Límites de seguridad

| Qué                                              | Límite por defecto                               | Variable                         |
| ------------------------------------------------ | ------------------------------------------------ | -------------------------------- |
| Fallos de login por IP                           | 20 cada 15 min                                   | `AUTH_LIMIT_PER_IP`              |
| Fallos de login por correo                       | 10 cada 15 min (un acierto reinicia el contador) | `AUTH_LIMIT_PER_EMAIL`           |
| Ventana de los dos anteriores                    | 900 s                                            | `AUTH_LIMIT_WINDOW`              |
| Solicitudes de recuperación de contraseña por IP | 10 cada 15 min                                   | `PASSWORD_RESET_LIMIT_PER_IP`    |
| Solicitudes de recuperación por correo           | 3 cada 15 min                                    | `PASSWORD_RESET_LIMIT_PER_EMAIL` |
| Reservas públicas por IP                         | 10 por hora                                      | `PUBLIC_BOOKING_LIMIT_PER_IP`    |
| Reservas públicas por celular                    | 5 por hora                                       | `PUBLIC_BOOKING_LIMIT_PER_PHONE` |

Los contadores son por negocio y viven en Redis. Al pasar el límite, la API responde `429` con el código `rate_limited`.

Detrás de Caddy, `TRUSTED_PROXY_COUNT=1` hace que la IP sea la del cliente y no la del proxy. Si se agrega otro proxy delante, por ejemplo Cloudflare, súbelo a 2.

## 5. Auditoría

`AuditLog` guarda las acciones del Super Admin sobre negocios, planes, temas, módulos y dominios. Desde M10 también guarda estos eventos de seguridad de las cuentas:

| Acción                        | Cuándo                                                                                 |
| ----------------------------- | -------------------------------------------------------------------------------------- |
| `auth.login`                  | Inicio de sesión correcto                                                              |
| `auth.login_failed`           | Contraseña o código 2FA incorrecto, o correo inexistente (se guarda el correo escrito) |
| `auth.password_change`        | Cambio de contraseña desde la cuenta                                                   |
| `auth.password_reset_request` | Solicitud de recuperación de contraseña                                                |
| `auth.password_reset`         | Recuperación de contraseña completada                                                  |
| `auth.two_factor_enable`      | Activación del 2FA                                                                     |
| `auth.two_factor_reset`       | 2FA quitado con el comando `reset_2fa`                                                 |

Nunca se guardan contraseñas ni códigos. Se consulta en el panel del Super Admin, en **Auditoría**.
