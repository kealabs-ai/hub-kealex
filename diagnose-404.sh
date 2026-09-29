#!/bin/bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
if [[ -f "$ENV_FILE" ]]; then
  KEALEX_PUBLIC_API_URL="${KEALEX_PUBLIC_API_URL:-$(sed -n 's/^KEALEX_PUBLIC_API_URL=//p' "$ENV_FILE" | tail -n 1)}"
fi
: "${KEALEX_PUBLIC_API_URL:?Set KEALEX_PUBLIC_API_URL in the backend .env}"

printf 'Checking containers...\n'
docker compose ps
printf '\nChecking public API health...\n'
curl -fsS "${KEALEX_PUBLIC_API_URL%/}/k1/lex/health"
printf '\nChecking database through svc-auth...\n'
docker compose exec -T kealex-svc-auth python -c "import os; from sqlalchemy import create_engine, text; c=create_engine(os.environ['KEALEX_DATABASE_URL']).connect(); print(c.execute(text('SELECT VERSION()')).scalar()); c.close()"
printf '\nRecent auth logs:\n'
docker compose logs --tail=30 kealex-svc-auth