#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> [1/4] Upgrading pip..."
python -m pip install --upgrade pip

echo "==> [2/4] Installing dependencies from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

echo "==> [3/4] Collecting static files..."
python manage.py collectstatic --noinput

echo "==> [4/4] Running database migrations..."
python manage.py migrate

echo "==> Build complete! Ready to start server."

