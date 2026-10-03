#!/bin/bash
echo "Starting backend..."
echo "Seeding database..."
python scripts/seed_users.py
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
