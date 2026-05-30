#!/usr/bin/env bash
set -e

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Start FastAPI application
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
