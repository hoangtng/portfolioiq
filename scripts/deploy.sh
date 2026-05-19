#!/usr/bin/env bash
#
# Pull latest code and redeploy. Run on the EC2 host.
#
# Usage:  bash /opt/portfolioiq/scripts/deploy.sh

set -euo pipefail

cd /opt/portfolioiq

echo "─── Pulling latest code ───"
git fetch --all
git reset --hard origin/main

echo "─── Rebuilding images ───"
docker compose -f docker-compose.prod.yml build --pull

echo "─── Applying migrations & restarting ───"
docker compose -f docker-compose.prod.yml up -d

echo "─── Cleaning up dangling images ───"
docker image prune -f

echo ""
echo "─── Status ───"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "✓ Deployment complete"
echo ""
echo "Tail logs with:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
