FROM python:3.11-slim

# Version info (passed from docker-compose build args or CI)
ARG FILAOPS_VERSION=3.0.1
ARG FILAOPS_BUILD_DATE
ENV FILAOPS_VERSION=${FILAOPS_VERSION}
ENV FILAOPS_BUILD_DATE=${FILAOPS_BUILD_DATE:-unknown}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories and non-root user
RUN mkdir -p /app/uploads /app/logs \
    && addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app/uploads /app/logs \
    && chmod -R a+rX /app \
    && chmod +x /app/scripts/docker-migrate.sh

EXPOSE 8000

USER appuser

# Start server only - migrations run via separate 'migrate' service in docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
