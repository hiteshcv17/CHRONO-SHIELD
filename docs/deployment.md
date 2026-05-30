# ChronoShield AI: Operations & Production Deployment Guide

This document details the step-by-step procedures for deploying **ChronoShield AI** in production-grade containerized environments using Docker Compose, Alembic migrations, Nginx reverse proxies, and Prometheus monitoring.

---

## 1. Environment Setup Configuration (`.env`)
Create a production `.env` file in the root of the workspace. This file encapsulates secret credentials and host configuration variables:

```env
# ── PLATFORM VARIABLES ────────────────────────────────────────────────────────
PROJECT_NAME="ChronoShield AI Operations Gateway"
ENVIRONMENT="production"
VERSION="1.0.0"
API_V1_STR="/api/v1"

# ── POSTGRESQL TRANSACTION DATABASE ───────────────────────────────────────────
POSTGRES_USER=chronoshield_admin
POSTGRES_PASSWORD=VaultSecureDbPassword99!
POSTGRES_DB=chronoshield_prod
POSTGRES_HOST=postgres_db
POSTGRES_PORT=5432

# Production SQLAlchemy Connection String (AsyncPG driver)
DATABASE_URL=postgresql+asyncpg://chronoshield_admin:VaultSecureDbPassword99!@postgres_db:5432/chronoshield_prod

# Database Connection Pool Sizing
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=15
DB_POOL_TIMEOUT=30

# ── REDIS CACHE & pub/sub CHANNEL ─────────────────────────────────────────────
REDIS_HOST=redis_cache
REDIS_PORT=6379
REDIS_URL=redis://redis_cache:6379/0

# ── SECURITY AUTHENTICATION ───────────────────────────────────────────────────
# Generate high-entropy hash locally: openssl rand -hex 32
JWT_SECRET_KEY=e83a73c178229c1b48e36214f494a821e25e1c41b8a920c3298a09f8c1223e7f
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── TELEMETRY SYSTEM RATINGS ──────────────────────────────────────────────────
ANOMALY_ALARM_THRESHOLD=0.70
INGEST_BUFFER_CAPACITY=80000
```

---

## 2. Multi-Service Container Setup (`docker-compose.yml`)

The platform deploys four coordinated service engines isolated inside a unified Docker network bridge:

```yaml
version: '3.8'

services:
  # 1. Transaction Database
  postgres_db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pg_data_volume:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - chronoshield_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  # 2. Redis Telemetry Cache Buffer
  redis_cache:
    image: redis:7-alpine
    container_name: redis_cache
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis_data_volume:/data
    ports:
      - "6379:6379"
    networks:
      - chronoshield_net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # 3. Uvicorn FastAPI Backend Gateway
  backend_gateway:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend_gateway
    restart: always
    depends_on:
      postgres_db:
        condition: service_healthy
      redis_cache:
        condition: service_healthy
    env_file:
      - .env
    ports:
      - "8000:8000"
    networks:
      - chronoshield_net

  # 4. Nginx Reverse Proxy React Web App
  frontend_app:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: frontend_app
    restart: always
    depends_on:
      - backend_gateway
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    networks:
      - chronoshield_net

volumes:
  pg_data_volume:
  redis_data_volume:

networks:
  chronoshield_net:
    driver: bridge
```

---

## 3. Database Schema Upgrades via Alembic Migrations
Alembic manages asynchronous database schemas sequentially. 

The production backend container runs Alembic updates automatically on container startup inside `entrypoint.sh` before spawning the Uvicorn worker process.

### 3.1 Manual Database Upgrades
To run manual upgrades directly on the deployment host:
```bash
# Execute Alembic schema upgrades to the latest head
docker exec -it backend_gateway alembic upgrade head
```

### 3.2 Rollback Schema Updates
To roll back the schema in the event of an emergency:
```bash
# Roll back database schema by 1 step
docker exec -it backend_gateway alembic downgrade -1
```

---

## 4. Production Reverse Proxy Configuration (`nginx.conf`)
The Nginx server handles frontend asset routing, reverse proxy mappings to the FastAPI gateway, WebSocket endpoint tunnels, and SSL termination:

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    # Gzip Compression Optimization
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    server {
        listen 80;
        server_name chronoshield.ai www.chronoshield.ai;
        
        # Enforce HTTPS redirect
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name chronoshield.ai www.chronoshield.ai;

        # SSL Certificates Offloading (Let's Encrypt CA path standard)
        ssl_certificate /etc/letsencrypt/live/chronoshield.ai/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/chronoshield.ai/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # ── HTML/CSS Frontend Assets Static Mapping ──
        location / {
            root   /usr/share/nginx/html;
            index  index.html index.htm;
            try_files $uri $uri/ /index.html;
        }

        # ── REST API Proxy Pass ──
        location /api/v1/ {
            proxy_pass http://backend_gateway:8000/api/v1/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # ── WebSocket Alert Stream proxy tunnel ──
        location /api/v1/ws/ {
            proxy_pass http://backend_gateway:8000/api/v1/ws/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

---

## 5. Telemetry & Performance Monitoring (Prometheus Integration)
The FastAPI backend acts as an active Prometheus exporter, exposing key gateway metrics under the unsecured endpoint `/metrics` for scraper collection:

- **Prometheus Collector Scrape Target**:
  - `http://backend_gateway:8000/metrics`

### Exposed Operational Metrics
1. **`http_requests_total{method, handler, status}`**: Counter tracking request counts across REST paths.
2. **`http_request_duration_seconds{handler}`**: Histogram tracking API gateway response RTT profiles.
3. **`anomaly_evaluation_duration_seconds`**: Histogram tracking PyTorch Autoencoder reconstruction execution durations.
4. **`cache_operations_total{prefix, operation, status}`**: Counter tracking Redis cache read/write hits and invalidation success rates.
5. **`active_websocket_connections`**: Gauge tracking current dashboard clients connected over WebSockets.
