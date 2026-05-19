#!/usr/bin/env bash
#
# Daily Postgres backup → S3.
# Add to crontab on the EC2 host:
#
#   0 3 * * * /opt/portfolioiq/scripts/backup.sh >> /var/log/portfolioiq-backup.log 2>&1
#
# Requires AWS CLI configured (aws configure) with S3 write access.

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────
S3_BUCKET="${S3_BACKUP_BUCKET:-portfolioiq-backups}"
RETAIN_DAYS=30
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/tmp/portfolioiq-backup"
BACKUP_FILE="${BACKUP_DIR}/portfolioiq_${DATE}.sql.gz"
COMPOSE_FILE="/opt/portfolioiq/docker-compose.prod.yml"
ENV_FILE="/opt/portfolioiq/.env.production"

# Read POSTGRES_USER + POSTGRES_DB from .env.production
if [ -f "${ENV_FILE}" ]; then
    export $(grep -E '^POSTGRES_(USER|DB)=' "${ENV_FILE}" | xargs)
fi

POSTGRES_USER="${POSTGRES_USER:-portfolioiq}"
POSTGRES_DB="${POSTGRES_DB:-portfolioiq}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] ─── Starting Postgres backup ───"

# ─── Dump ────────────────────────────────────────────────────
cd /opt/portfolioiq
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
    pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
    | gzip -9 > "${BACKUP_FILE}"

SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Dump complete: $(basename ${BACKUP_FILE}) (${SIZE})"

# ─── Upload ──────────────────────────────────────────────────
echo "[$(date)] Uploading to s3://${S3_BUCKET}/postgres/"
aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/postgres/$(basename ${BACKUP_FILE})" \
    --storage-class STANDARD_IA

# ─── Cleanup local ───────────────────────────────────────────
rm -f "${BACKUP_FILE}"

# ─── Prune old backups ───────────────────────────────────────
echo "[$(date)] Pruning S3 backups older than ${RETAIN_DAYS} days"
CUTOFF=$(date -d "${RETAIN_DAYS} days ago" +%Y-%m-%d)

aws s3 ls "s3://${S3_BUCKET}/postgres/" | while read -r line; do
    file_date=$(echo "${line}" | awk '{print $1}')
    file_name=$(echo "${line}" | awk '{print $4}')
    
    if [[ -n "${file_name}" && "${file_date}" < "${CUTOFF}" ]]; then
        echo "  removing: ${file_name}"
        aws s3 rm "s3://${S3_BUCKET}/postgres/${file_name}"
    fi
done

echo "[$(date)] ✓ Backup complete"
echo ""