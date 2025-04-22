FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=main.py

# Expose port
EXPOSE 443

# Run the application with SSL
CMD ["gunicorn", "--bind", "0.0.0.0:443", "--certfile", "/app/ssl/cloudflare.pem", "--keyfile", "/app/ssl/cloudflare-key.pem", "main:app"]
