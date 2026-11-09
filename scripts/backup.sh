#!/usr/bin/env bash
# Copia de seguridad cifrada de PostgreSQL (M10, spec §15).
#
#   BACKUP_PASSPHRASE='...' scripts/backup.sh [carpeta]
#
# - Usa pg_dump en formato custom dentro del contenedor `postgres` con el usuario dueño
#   (superusuario), así la copia incluye las filas de todos los negocios: RLS no aplica a él.
# - Cifra con AES-256 (openssl, clave derivada con PBKDF2). Sin la frase no se puede leer.
# - Deja al lado un .sha256 para verificar que el archivo no se dañó.
# - Borra las copias locales con más de BACKUP_KEEP_DAYS días (14 por defecto).
# - Si BACKUP_UPLOAD_CMD está definido, lo ejecuta con la ruta del archivo para subirlo fuera
#   del servidor (por ejemplo: BACKUP_UPLOAD_CMD='rclone copy {} remoto:agenda-backups').
#   Una copia que solo vive en el mismo servidor no protege contra la pérdida del disco.
set -euo pipefail

: "${BACKUP_PASSPHRASE:?Define BACKUP_PASSPHRASE (guárdala fuera del servidor).}"
OUT_DIR="${1:-backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
FILE="$OUT_DIR/agenda-$STAMP.dump.enc"

docker compose exec -T -e BACKUP_PASSPHRASE postgres sh -c '
  set -e
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner \
    | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:BACKUP_PASSPHRASE
' > "$FILE.part"
mv "$FILE.part" "$FILE"

( cd "$OUT_DIR" && sha256sum "$(basename "$FILE")" > "$(basename "$FILE").sha256" )
echo "Copia creada: $FILE ($(du -h "$FILE" | cut -f1))"

if [ -n "${BACKUP_UPLOAD_CMD:-}" ]; then
  eval "${BACKUP_UPLOAD_CMD//\{\}/\"$FILE\"}"
  eval "${BACKUP_UPLOAD_CMD//\{\}/\"$FILE.sha256\"}"
  echo "Copia subida fuera del servidor."
fi

find "$OUT_DIR" -name 'agenda-*.dump.enc*' -mtime "+$KEEP_DAYS" -print -delete
