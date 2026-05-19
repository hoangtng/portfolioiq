#!/usr/bin/env bash
#
# Restore a Postgres backup from S3.
# DESTRUCTIVE — this wipes the current database.
#
# Usage:
#   bash /opt/portfolioiq/scripts/restore.sh                    # latest backup
#   bash /opt/portfolioiq/scripts/restore.sh 2025-05-19         # specific date

set -euo pipefail

S3_BUCKET="${S3_BACKUP_BUCKET:-portfolioiq-backups}"
TARGET_DATE="${1:-}"
COMPOSE_FILE="/opt/portfolioiq/docker-compose.prod.yml"
ENV_FILE="/opt/portfolioiq/.env.production"

if [ -f "${ENV_FILE}" ]; then
    export $(grep -E '^POSTGRES_(USER|DB)=' "${ENV_FILE}" | xargs)
fi

POSTGRES_USER="${POSTGRES_USER:-portfolioiq}"
POSTGRES_DB="${POSTGRES_DB:-portfolioiq}"

# ─── Find backup ─────────────────────────────────────────────
echo "─── Looking up backups ───"

if [ -n "${TARGET_DATE}" ]; then
    BACKUP_KEY=$(aws s3 ls "s3://${S3_BUCKET}/postgres/" \
        | grep "${TARGET_DATE}" \
        | sort -r \
        | head -n 1 \
        | awk '{print $4}')
else
    BACKUP_KEY=$(aws s3 ls "s3://${S3_BUCKET}/postgres/" \
        | sort -r \
        | head -n 1 \
        | awk '{print $4}')
fi

if [ -z "${BACKUP_KEY}" ]; then
    echo "✗ No backup found"
    exit 1
fi

echo "✓ Selected: ${BACKUP_KEY}"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  WARNING: this will REPLACE the current database."
echo "  Target: ${POSTGRES_DB}"
echo "  Backup: ${BACKUP_KEY}"
echo "════════════════════════════════════════════════════════════"
echo ""
read -p "Type 'restore' to continue: " confirm
if [ "${confirm}" != "restore" ]; then
    echo "Cancelled."
    exit 0
fi

# ─── Download ────────────────────────────────────────────────
LOCAL_FILE="/tmp/${BACKUP_KEY}"
echo ""
echo "[$(date)] Downloading from S3..."
aws s3 cp "s3://${S3_BUCKET}/postgres/${BACKUP_KEY}" "${LOCAL_FILE}"

# ─── Stop dependent services ─────────────────────────────────
echo "[$(date)] Stopping dependent services..."
cd /opt/portfolioiq
docker compose -f "${COMPOSE_FILE}" stop api worker beat

# ─── Drop + recreate database ────────────────────────────────
echo "[$(date)] Dropping + recreating database..."
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
    psql -U "${POSTGRES_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"

docker compose -f "${COMPOSE_FILE}" exec -T postgres \
    psql -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE ${POSTGRES_DB};"

# ─── Restore ─────────────────────────────────────────────────
echo "[$(date)] Restoring (this may take a few minutes)..."
gunzip -c "${LOCAL_FILE}" | docker compose -f "${COMPOSE_FILE}" exec -T postgres \
    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"

# ─── Restart services ────────────────────────────────────────
echo "[$(date)] Restarting services..."
docker compose -f "${COMPOSE_FILE}" start api worker beat

# ─── Cleanup ─────────────────────────────────────────────────
rm -f "${LOCAL_FILE}"

echo ""
echo "[$(date)] ✓ Restore complete"
echo ""
echo "Verify with:"
echo "  docker compose -f ${COMPOSE_FILE} exec api python manage.py shell"
echo "  >>> from django.contrib.auth import get_user_model; print(get_user_model().objects.count())"