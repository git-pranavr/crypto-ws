#!/bin/sh
set -e

PORT="${PORT:-8000}"
MAX_MIGRATION_ATTEMPTS="${MAX_MIGRATION_ATTEMPTS:-10}"
MIGRATION_RETRY_DELAY="${MIGRATION_RETRY_DELAY:-3}"

attempt=1
until alembic upgrade head; do
    if [ "$attempt" -ge "$MAX_MIGRATION_ATTEMPTS" ]; then
        echo "Migrations failed after ${MAX_MIGRATION_ATTEMPTS} attempts."
        exit 1
    fi

    echo "Migration attempt ${attempt} failed. Retrying in ${MIGRATION_RETRY_DELAY}s..."
    attempt=$((attempt + 1))
    sleep "$MIGRATION_RETRY_DELAY"
done

echo "Starting server..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
