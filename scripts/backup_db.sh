#!/usr/bin/env bash
#
# Velegrad CMS — backup PostgreSQL baze (Story 6.4 AC3).
# pg_dump -> gzip -> retencija -> offsite kopija (rsync na Hetzner Storage Box).
# Pokreće se iz cron-a na VPS-u, npr. dnevno u 02:00:
#   0 2 * * * /srv/velegrad/scripts/backup_db.sh >> /var/log/velegrad-backup.log 2>&1
#
# Tajne (DATABASE_URL / lozinka) NISU u skripti — čitaju se iz okruženja / .pgpass.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/srv/velegrad/backups/db}"
WEEKLY_DIR="${WEEKLY_DIR:-${BACKUP_DIR}/weekly}"
DB_NAME="${DB_NAME:-velegrad}"
DB_USER="${DB_USER:-velegrad}"
DB_HOST="${DB_HOST:-127.0.0.1}"
# Tiered retencija (AC3: "7 dnevnih + 4 nedeljna"):
#   - dnevni dump-ovi se čuvaju DAILY_RETENTION_DAYS dana (7),
#   - nedeljom (dan 7) se dump dodatno kopira u weekly/ i čuva
#     WEEKLY_RETENTION_DAYS dana (28 = 4 nedelje), pa ~28-dnevni rep preživljava.
DAILY_RETENTION_DAYS="${DAILY_RETENTION_DAYS:-${RETENTION_DAYS:-7}}"
WEEKLY_RETENTION_DAYS="${WEEKLY_RETENTION_DAYS:-28}"

# Offsite (Hetzner Storage Box preko rsync/SSH). Opciono — postaviti u env-u.
# Prazno (default) => offsite se PRESKAČE (oslanjamo se na Hetzner snapshot celog servera).
OFFSITE_DEST="${OFFSITE_DEST:-}"

TS="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR" "$WEEKLY_DIR"
DUMP_FILE="${BACKUP_DIR}/${DB_NAME}-${TS}.sql.gz"

echo "[$(date -Is)] pg_dump ${DB_NAME} -> ${DUMP_FILE}"
pg_dump --host="$DB_HOST" --username="$DB_USER" --no-owner --no-privileges "$DB_NAME" \
    | gzip -9 > "$DUMP_FILE"

# Nedeljni snapshot: nedeljom (date +%u == 7) kopiraj današnji dump u weekly/.
# Oslanja se na POSIX `date +%u` (1=ponedeljak ... 7=nedelja) — standardni Linux VPS.
if [ "$(date +%u)" = "7" ]; then
    echo "[$(date -Is)] nedeljni snapshot -> ${WEEKLY_DIR}/"
    cp "$DUMP_FILE" "${WEEKLY_DIR}/${DB_NAME}-${TS}.sql.gz"
fi

# Tiered retencija: dnevni dump-ovi stariji od DAILY_RETENTION_DAYS dana,
# i nedeljni dump-ovi stariji od WEEKLY_RETENTION_DAYS dana.
echo "[$(date -Is)] retencija: dnevni > ${DAILY_RETENTION_DAYS} dana, nedeljni > ${WEEKLY_RETENTION_DAYS} dana"
find "$BACKUP_DIR" -maxdepth 1 -name "${DB_NAME}-*.sql.gz" -type f -mtime "+${DAILY_RETENTION_DAYS}" -delete
find "$WEEKLY_DIR" -maxdepth 1 -name "${DB_NAME}-*.sql.gz" -type f -mtime "+${WEEKLY_RETENTION_DAYS}" -delete

# Offsite kopija (rsync na storage box) — preživljava gubitak VPS-a.
# BEZ --delete: rotacija/brisanje lokalnih dump-ova NE sme da obriše offsite kopije
# (offsite mora preživeti i gubitak VPS-a i lokalnu retenciju).
# Preskače se ako OFFSITE_DEST nije postavljen (npr. kad se oslanjamo na Hetzner snapshot).
if [ -n "$OFFSITE_DEST" ]; then
    echo "[$(date -Is)] offsite rsync -> ${OFFSITE_DEST}"
    rsync -az "$BACKUP_DIR/" "$OFFSITE_DEST"
else
    echo "[$(date -Is)] offsite preskočen (OFFSITE_DEST nije postavljen)"
fi

echo "[$(date -Is)] backup_db zavrsen OK"
