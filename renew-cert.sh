#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "[$(date)] Renewing certificate..."
docker compose run --rm certbot renew

echo "[$(date)] Reloading nginx..."
docker compose exec nginx nginx -s reload

echo "[$(date)] Done."
