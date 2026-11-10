#!/usr/bin/env bash
# Restaura una copia de scripts/backup.sh (M10).
#
#   BACKUP_PASSPHRASE='...' scripts/restore.sh backups/agenda-AAAAMMDD-HHMMSS.dump.enc [base]
#
# Por defecto restaura en una base NUEVA llamada `agenda_restore_check` para probar la copia sin
# tocar la base en uso. Restaurar sobre la base real es una decisión aparte: detener la API,
# renombrar bases y volver a levantar (ver docs/OPERACION.md).
set -euo pipefail

: "${BACKUP_PASSPHRASE:?Define BACKUP_PASSPHRASE.}"
FILE="${1:?Indica el archivo .dump.enc}"
TARGET="${2:-agenda_restore_check}"

if [ -f "$FILE.sha256" ]; then
  ( cd "$(dirname "$FILE")" && sha256sum --check --quiet "$(basename "$FILE").sha256" )
  echo "Suma de verificación correcta."
fi

docker compose exec -T postgres sh -c "
  set -e
  dropdb -U \"\$POSTGRES_USER\" --if-exists '$TARGET'
  createdb -U \"\$POSTGRES_USER\" '$TARGET'
"
docker compose exec -T -e BACKUP_PASSPHRASE postgres sh -c "
  set -e
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:BACKUP_PASSPHRASE \
    | pg_restore -U \"\$POSTGRES_USER\" -d '$TARGET' --no-owner --exit-on-error
" < "$FILE"

docker compose exec -T postgres psql -U agenda -d "$TARGET" -At -c "
  SELECT 'negocios: ' || count(*) FROM tenancy_tenant
  UNION ALL SELECT 'citas: ' || count(*) FROM booking_appointment
  UNION ALL SELECT 'usuarios: ' || count(*) FROM accounts_user
  UNION ALL SELECT 'migraciones: ' || count(*) FROM django_migrations"
echo "Restaurada en la base '$TARGET'."
