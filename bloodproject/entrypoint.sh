#!/bin/bash

# Exit on any error
set -e

# Wait for database to be ready
echo "Waiting for database..."
python manage.py wait_for_db

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "Starting application..."
exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 bloodproject.wsgi:application
