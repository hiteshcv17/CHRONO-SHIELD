# ==============================================================================
# Multi-stage Production-Ready Dockerfile for FastAPI Backend
# ==============================================================================

# --- Stage 1: Build & Package Caching ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Install compilation essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .

# Compile and build Python packages into /install prefix
RUN pip install --default-timeout=1000 --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: Final Slim Runtime ---
FROM python:3.11-slim AS runner

WORKDIR /app

# Install system dependencies needed for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy built packages from builder
COPY --from=builder /install /usr/local
COPY --from=builder /build/requirements.txt .

# Ensure binary execution paths are updated
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Copy FastAPI codebase, migrations and startup files
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini
COPY ./entrypoint.sh ./entrypoint.sh

# Create a non-privileged dedicated system user to execute the server
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Expose target port
EXPOSE 8000

# Healthcheck definition
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch application with entrypoint script
ENTRYPOINT ["./entrypoint.sh"]

