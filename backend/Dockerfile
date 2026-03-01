FROM python:3.11-slim

# Version info (passed from docker-compose build args or CI)
ARG FILAOPS_VERSION=3.2.0
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

# Optional: install plugin wheels if present (e.g. filaops-pro)
# Drop .whl files into backend/ before building — they're installed
# here and ignored if none exist. Core works identically without them.
RUN if ls /app/*.whl 1>/dev/null 2>&1; then \
        pip install --no-cache-dir /app/*.whl && rm -f /app/*.whl; \
    fi

# Create directories and non-root user
# sed strips Windows CRLF line endings that break shebangs on Linux
RUN mkdir -p /app/uploads /app/logs /app/static/uploads/products \
    && addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app/uploads /app/logs /app/static \
    && chmod -R a+rX /app \
    && sed -i 's/\r$//' /app/scripts/docker-migrate.sh \
    && chmod +x /app/scripts/docker-migrate.sh

EXPOSE 8000

USER appuser

# Start server only - migrations run via separate 'migrate' service in docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
