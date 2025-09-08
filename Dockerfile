# Dockerfile
FROM python:3.11-slim

# Install system dependencies including Nginx
RUN apt-get update && apt-get install -y \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# ✅ Create media and static directories
RUN mkdir -p media staticfiles

# ✅ Set proper permissions for Linux
RUN chmod -R 755 media staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Remove default Nginx config
RUN rm -f /etc/nginx/sites-enabled/default

# Expose port 80 (Nginx)
EXPOSE 80

# Create start script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]