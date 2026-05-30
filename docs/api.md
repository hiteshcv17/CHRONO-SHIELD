# ChronoShield AI: REST & WebSocket API Specification

This document details the REST API endpoints and WebSocket telemetry broadcast contracts for the **ChronoShield AI** backend service under `/api/v1/`.

---

## 1. Authentication & Security
The API enforces JWT Bearer authentication. Include the access token in the headers of all secure requests:
```http
Authorization: Bearer <your_jwt_access_token>
```

### 1.1 POST /api/v1/auth/register
Register a new operator.
- **Request Payload**:
  ```json
  {
    "username": "operator_chief",
    "password": "SecurePassword123!",
    "role": "ANALYST"
  }
  ```
  *(Note: roles must be either `"ANALYST"` or `"ADMIN"`)*
- **Response (201 Created)**:
  ```json
  {
    "id": "usr-8a9d9c22",
    "username": "operator_chief",
    "role": "ANALYST",
    "is_active": true
  }
  ```

### 1.2 POST /api/v1/auth/login
Authenticate credentials and retrieve a session JWT.
- **Request Payload**:
  ```json
  {
    "username": "operator_chief",
    "password": "SecurePassword123!"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "role": "ANALYST"
  }
  ```

---

## 2. Infrastructure Asset Management (RBAC: ADMIN only)

### 2.1 GET /api/v1/asset/
Retrieve all registered assets. Supports filtering by operational status.
- **Query Parameters**:
  - `status` (optional, string): Filter assets by `"active"`, `"degraded"`, `"offline"`.
- **Response (200 OK)**:
  ```json
  [
    {
      "id": "ast-9a2c118b",
      "name": "District 4 Windings Substation",
      "ip_address": "10.0.4.12",
      "status": "active",
      "category": "power",
      "created_at": "2026-05-28T12:00:00Z"
    }
  ]
  ```

### 2.2 POST /api/v1/asset/
Register a new operational asset.
- **Request Payload**:
  ```json
  {
    "name": "District 9 Server Grid Node",
    "ip_address": "10.0.9.45",
    "category": "internet"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "id": "ast-ef55c110",
    "name": "District 9 Server Grid Node",
    "ip_address": "10.0.9.45",
    "status": "active",
    "category": "internet",
    "created_at": "2026-05-28T19:40:00Z"
  }
  ```

### 2.3 DELETE /api/v1/asset/{id}
De-register an asset by ID.
- **Response (204 No Content)**

---

## 3. Anomaly Tracking & Real-Time Analytics (RBAC: ANALYST, ADMIN)

### 3.1 GET /api/v1/anomaly/
Query historical anomaly records. Supports pagination and timestamps filtering.
- **Query Parameters**:
  - `skip` (optional, integer, default: 0): Page offsets.
  - `limit` (optional, integer, default: 100): Page limits.
  - `severity` (optional, string): Filter by `"WARNING"`, `"CRITICAL"`.
- **Response (200 OK)**:
  ```json
  {
    "items": [
      {
        "id": "anm-f2c8a110",
        "metric_name": "traffic_flow_beltway",
        "score": 0.84,
        "severity": "CRITICAL",
        "description": "Bimodal speed drop near Exit 14. Average speed below 3mph.",
        "timestamp": "2026-05-28T19:42:12Z",
        "acknowledged": false
      }
    ],
    "total": 1
  }
  ```

### 3.2 GET /api/v1/anomaly/stats
Get composite statistical analysis summary for the dashboard cards.
- **Response (200 OK)**:
  ```json
  {
    "total_anomalies_24h": 42,
    "critical_count": 12,
    "warning_count": 30,
    "mean_severity_score": 0.642,
    "ingestion_events_per_sec": 14200
  }
  ```

---

## 4. Alerts Control & Operations Desk (RBAC: ANALYST, ADMIN)

### 4.1 GET /api/v1/alert/
Retrieve the prioritized queue of active alerts requiring operator attention.
- **Response (200 OK)**:
  ```json
  [
    {
      "id": "alr-3e9d88ab",
      "anomaly_record_id": "anm-f2c8a110",
      "severity": "CRITICAL",
      "description": "Bimodal speed drop near Exit 14. Average speed below 3mph.",
      "created_at": "2026-05-28T19:42:15Z",
      "suppressed": false,
      "priority_score": 95.0
    }
  ]
  ```

### 4.2 POST /api/v1/alert/{id}/acknowledge
Acknowledge an alert to resolve it on the operational console.
- **Response (200 OK)**:
  ```json
  {
    "id": "alr-3e9d88ab",
    "status": "resolved",
    "acknowledged_by": "operator_chief",
    "resolved_at": "2026-05-28T19:45:00Z"
  }
  ```

---

## 5. Forecasting Model Benchmarking (RBAC: ANALYST, ADMIN)

### 5.1 POST /api/v1/benchmark/run
Trigger a full forecasting models benchmarking run (Prophet vs ARIMA vs ETS).
- **Request Payload**:
  ```json
  {
    "metric_types": ["power", "traffic", "water", "internet"],
    "horizon_steps": 24,
    "n_samples": 200,
    "include_ets": true
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "run_id": "BM-A98B22C0",
    "timestamp": "2026-05-28T19:46:12Z",
    "models_evaluated": ["Prophet", "ARIMA", "ETS"],
    "results": [
      {
        "model_name": "Prophet",
        "dataset_name": "Power Infrastructure",
        "metric_type": "power",
        "mae": 12.4,
        "rmse": 18.2,
        "mape": 4.12,
        "r2_score": 0.941,
        "training_time_ms": 310.2,
        "inference_time_ms": 8.2,
        "converged": true
      }
    ],
    "aggregate": {
      "Prophet": {
        "mae": 12.4,
        "rmse": 18.2,
        "mape": 4.12,
        "r2": 0.941,
        "train_ms": 310.2,
        "infer_ms": 8.2,
        "total_ms": 318.4
      }
    },
    "overall_winner": "Prophet",
    "overall_winner_reason": "Lowest composite rank sum across MAE, RMSE, MAPE, and speed (2.0 pts)",
    "recommendations": [
      "Deploy Prophet for production forecasting — lowest composite error"
    ],
    "total_benchmark_time_ms": 420.5
  }
  ```

### 5.2 GET /api/v1/benchmark/preview/{metric_type}
Retrieve raw timeseries details for a specific metric category.
- **Response (200 OK)**:
  ```json
  {
    "metric_type": "power",
    "description": "Hourly electricity demand (MW) — diurnal + weekly seasonality",
    "n_samples": 200,
    "train_size": 160,
    "test_size": 40,
    "values": [2845.2, 2912.4, 2800.5, ...],
    "stats": {
      "mean": 2812.4,
      "std": 68.2,
      "min": 2420.1,
      "max": 3520.4
    }
  }
  ```

---

## 6. System Diagnostics & Health checks (No Auth Required)

### 6.1 GET /api/v1/diagnostics/health
Check basic gateway routing connectivity.
- **Response (200 OK)**:
  ```json
  {
    "status": "healthy",
    "service": "chronoshield-backend",
    "environment": "production"
  }
  ```

### 6.2 GET /api/v1/diagnostics/status
Obtain extensive backend micro-diagnostics, database latencies, and system metrics.
- **Response (200 OK)**:
  ```json
  {
    "status": "operational",
    "dependencies": [
      {
        "name": "Database Connection",
        "connected": true,
        "latency_ms": 2.45
      },
      {
        "name": "Redis Cache Stream",
        "connected": true,
        "latency_ms": 0.85
      }
    ],
    "system_metrics": {
      "load_average_1m": 0.42,
      "memory_allocated_pct": 54.2,
      "active_threads_count": 8
    }
  }
  ```

---

## 7. Real-Time WebSocket Alerts Emitter (`/ws/alerts`)
Establish standard WebSocket listening pipeline to receive live telemetry incidents from the backend Pub/Sub.

- **URL Endpoint**: `ws://<backend_host>/api/v1/ws/alerts`
- **Authentication**: JWT token must be passed as query parameter `token`:
  `ws://localhost:8000/api/v1/ws/alerts?token=<jwt_access_token>`

- **Broadcast Message payload (JSON)**:
  Every time the PyTorch AI Engine detects an anomaly, it publishes a JSON payload which is broadcasted to all active WebSocket clients:
  ```json
  {
    "event_type": "ANOMALY_TRIGGERED",
    "payload": {
      "id": "alr-3e9d88ab",
      "metric_name": "traffic_flow_beltway",
      "score": 0.84,
      "severity": "CRITICAL",
      "description": "Bimodal speed drop near Exit 14. Average speed below 3mph.",
      "timestamp": "2026-05-28T19:42:15Z",
      "system_recommendation": "Activate Beltway Route 14 traffic signal overrides."
    }
  }
  ```
