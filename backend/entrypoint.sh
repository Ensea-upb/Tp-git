#!/bin/sh
set -e

echo "⏳ Attente de PostgreSQL..."
python - << 'PYEOF'
import os, time, psycopg2

url = os.environ["DATABASE_URL"]
for attempt in range(30):
    try:
        conn = psycopg2.connect(url)
        conn.close()
        print("✅ PostgreSQL prêt.")
        break
    except Exception as e:
        print(f"  [{attempt+1}/30] PostgreSQL non joignable : {e}")
        time.sleep(2)
else:
    raise SystemExit("❌ PostgreSQL inaccessible après 30 tentatives.")
PYEOF

echo "🔄 Application des migrations Alembic..."
alembic upgrade head

echo "🌱 Seed initial (ignoré si données existantes)..."
python scripts/seed.py

echo "🚀 Démarrage uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
