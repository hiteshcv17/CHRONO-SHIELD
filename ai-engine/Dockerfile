# ==============================================================================
# Production-Ready Dockerfile for Python AI Engine
# ==============================================================================

# --- Stage 1: Build & Wheel Cache ---
FROM python:3.10-slim AS builder

WORKDIR /build

# Install compiler essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Compile and compile libraries into wheels (caching CPU torch)
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: Minimal Runtime Layer ---
FROM python:3.10-slim AS runner

WORKDIR /app

# Install runtime utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled packages from builder stage
COPY --from=builder /install /usr/local
COPY --from=builder /build/requirements.txt .

# Set execution PATH and disable bytecode outputs
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy AI module codebase
COPY ./src ./src

# Establish a non-root system user for runtime execution
RUN addgroup --system aigroup && adduser --system --group aiuser
RUN chown -R aiuser:aigroup /app
USER aiuser

# Expose port 8001
EXPOSE 8001

# Healthcheck definition
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Entrypoint launching the FastAPI microservice and background ingestion loops
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
