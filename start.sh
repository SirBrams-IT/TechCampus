#!/bin/bash
# start.sh

# ✅ Create media directory if it doesn't exist (just in case)
mkdir -p media

# ✅ Set proper permissions
chmod -R 755 media staticfiles

# Start Gunicorn (Django) in background
echo "Starting Gunicorn..."
gunicorn TechCampuss.wsgi:application \
    --bind localhost:8000 \
    --workers 3 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - &

# Start Nginx in foreground
echo "Starting Nginx..."
exec nginx -g "daemon off;"