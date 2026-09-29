#!/bin/bash
set -euo pipefail

SERVICE="${DB_TEST_SERVICE:-kealex-svc-auth}"
echo "Checking database connectivity through ${SERVICE}..."
docker compose exec -T "${SERVICE}" python -c "import os; from sqlalchemy import create_engine, text; engine=create_engine(os.environ['KEALEX_DATABASE_URL']); conn=engine.connect(); print('Database connected; server version:', conn.execute(text('SELECT VERSION()')).scalar()); conn.close()"