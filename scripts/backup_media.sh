#!/usr/bin/env bash
#
# Velegrad CMS — backup media/ direktorijuma (Story 6.4 AC3).
# Upload-ovane slike nekretnina su nezamenljive (klijent ih ručno unosi).
# tar + gzip -> retencija -> offsite kopija (rsync na Hetzner Storage Box).
# Pokreće se iz cron-a na VPS-u, npr. dnevno u 02:30:
#   30 2 * * * /srv/velegrad/scripts/backup_media.sh >> /var/log/velegrad-backup.log 2>&1
set -euo pipefail

MEDIA_DIR="${MEDIA_DIR:-/srv/velegrad/media}"
BACKUP_DIR="${BACKUP_DIR:-/srv/velegrad/backups/media}"
WEEKLY_DIR="${WEEKLY_DIR:-${BACKUP_DIR}/weekly}"
# Tiered retencija (AC3: "7 dnevnih + 4 nedeljna") — usklađeno sa backup_db.sh:
#   - dnevne arhive se čuvaju DAILY_RETENTION_DAYS dana (7),
#   - nedeljom (dan 7) se arhiva dodatno kopira u weekly/ i čuva
#     WEEKLY_RETENTION_DAYS dana (28 = 4 nedelje).
DAILY_RETENTION_DAYS="${DAILY_RETENTION_DAYS:-${RETENTION_DAYS:-7}}"
WEEKLY_RETENTION_DAYS="${WEEKLY_RETENTION_DAYS:-28}"

# Offsite (Hetzner Storage Box preko rsync/SSH). Postaviti u env-u.
OFFSITE_DEST="${OFFSITE_DEST:-u123456@u123456.your-storagebox.de:velegrad/media/}"

TS="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR" "$WEEKLY_DIR"
ARCHIVE="${BACKUP_DIR}/media-${TS}.tar.gz"

echo "[$(date -Is)] tar media ${MEDIA_DIR} -> ${ARCHIVE}"
tar -czf "$ARCHIVE" -C "$(dirname "$MEDIA_DIR")" "$(basename "$MEDIA_DIR")"

# Nedeljni snapshot: nedeljom (date +%u == 7) kopiraj današnju arhivu u weekly/.
# Oslanja se na POSIX `date +%u` (1=ponedeljak ... 7=nedelja) — standardni Linux VPS.
if [ "$(date +%u)" = "7" ]; then
    echo "[$(date -Is)] nedeljni snapshot -> ${WEEKLY_DIR}/"
    cp "$ARCHIVE" "${WEEKLY_DIR}/media-${TS}.tar.gz"
fi

# Tiered retencija: dnevne arhive starije od DAILY_RETENTION_DAYS dana,
# i nedeljne arhive starije od WEEKLY_RETENTION_DAYS dana.
echo "[$(date -Is)] retencija: dnevne > ${DAILY_RETENTION_DAYS} dana, nedeljne > ${WEEKLY_RETENTION_DAYS} dana"
find "$BACKUP_DIR" -maxdepth 1 -name "media-*.tar.gz" -type f -mtime "+${DAILY_RETENTION_DAYS}" -delete
find "$WEEKLY_DIR" -maxdepth 1 -name "media-*.tar.gz" -type f -mtime "+${WEEKLY_RETENTION_DAYS}" -delete

# Offsite kopija — rsync media/ + arhive na storage box.
echo "[$(date -Is)] offsite rsync media -> ${OFFSITE_DEST}"
rsync -az "$BACKUP_DIR/" "$OFFSITE_DEST"
rsync -az "$MEDIA_DIR/" "${OFFSITE_DEST}current/"

echo "[$(date -Is)] backup_media zavrsen OK"
