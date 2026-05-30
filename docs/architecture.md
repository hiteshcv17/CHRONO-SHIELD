# ChronoShield AI: System Architecture Specification

This document provides a highly detailed architectural overview of the **ChronoShield AI** platform, explaining telemetry streams, message routing, neural network anomaly assessment, and downstream indexing strategies.

---

## 1. Core Architecture Overview

ChronoShield AI serves as an active telemetry operations center dashboard designed to identify system anomalies across time-series metrics:

```mermaid
graph TD
    %% Frontend Node
    FE[Vite React Dashboard]
    
    %% API Gateway Node
    subgraph FastAPI_Gateway [FastAPI API Gateway]
        REST[REST Router]
        WS[WebSocket Emitter]
        LFS[Lifespan Connection Manager]
    end
    
    %% Caching and Buffering
    subgraph Buffer_Store [Redis Telemetry Buffer]
        R_PUB[Redis Pub/Sub Channels]
        R_STR[Redis Sliding Window Streams]
        R_TOK[Redis Token Store]
    end
    
    %% Storage Database
    subgraph Transactional_DB [PostgreSQL Database]
        PG_TBL[PostgreSQL Tables]
        PG_IDX[PostgreSQL Indices]
        PG_ALM[Alembic Migrations]
    end
    
    %% AI Pipeline
    subgraph AI_Engine [AI Core Engine]
        ML_PRED[PyTorch Inference Predictor]
        ML_REG[Model Registry]
        ML_NORM[Z-Score Scale Normalizer]
    end

    %% Mesh Connections
    FE <-->|REST Requests / JWT Auth| REST
    FE <-->|WebSockets Alert Pipeline| WS
    REST -->|Lifespan Session Factory| PG_TBL
    REST -->|Auth Session Cache| R_TOK
    REST -->|Push Telemetry Stream| R_STR
    
    R_STR -->|Sequence Matrix Pull| ML_NORM
    ML_NORM -->|Normalized Vectors| ML_PRED
    ML_PRED -->|Model Checkpoint Weight| ML_REG
    
    ML_PRED -->|Write Anomaly Record| PG_TBL
    ML_PRED -->|Emit Anomaly Event| R_PUB
    
    R_PUB -->|Pub/Sub Alert Trigger| WS
    
    classDef default fill:#0f172a,stroke:#334155,stroke-width:1px,color:#f1f5f9;
    classDef highlight fill:#1e1b4b,stroke:#818cf8,stroke-width:1.5px,color:#f1f5f9;
    class FE highlight;
```

---

## 2. Telemetry Ingestion & Real-Time Alert Broadcast Sequence

The platform ingests metric streams, runs neural network reconstructions, saves findings, and broadcasts alerts within sub-second latencies:

```mermaid
sequenceDiagram
    autonumber
    actor Collector as Prometheus / Telemetry Agent
    participant API as FastAPI Gateway
    participant Redis as Redis Buffer & PubSub
    participant AI as PyTorch AI Engine
    participant DB as PostgreSQL DB
    actor Dashboard as React Dashboard Client

    Collector->>API: POST /api/v1/telemetry/ (Metric Data Points)
    activate API
    API->>Redis: Append metrics to sliding list (e.g. redis_client.lpush)
    API-->>Collector: 202 Accepted (Low-Latency Response)
    deactivate API

    activate AI
    AI->>Redis: Pull sequence range (e.g. last 60 ticks via LRANGE)
    Redis-->>AI: Raw Sequence Matrix
    AI->>AI: Z-Score Normalization Scale-fit
    AI->>AI: Evaluate Autoencoder Reconstruction Loss (MSE)
    
    alt Loss > Threshold (Anomaly Detected)
        AI->>DB: Write AnomalyRecord (id, metric, score, desc, severity)
        activate DB
        DB-->>AI: Record Saved
        deactivate DB
        
        AI->>Redis: Publish Anomaly Event to PubSub Channel
        activate Redis
        Redis-->>AI: Event Acknowledged
        deactivate AI
        
        Redis->>API: Trigger Pub/Sub Subscriber Callback
        activate API
        API->>Dashboard: Broadcast Anomaly Event (WebSocket JSON Envelope)
        activate Dashboard
        Dashboard->>Dashboard: Smoothly scale scatter points on Plotly & play Eye-shake mascot animation
        deactivate Dashboard
        deactivate API
        deactivate Redis
    end
```

---

## 3. Core Domain Entity Model UML

Below is the entity-relationship class mapping representing database tables orchestrated by SQL Alchemy in the backend and reflected in the frontend schemas:

```mermaid
classDiagram
    class User {
        +UUID id
        +String username
        +String hashed_password
        +String role
        +Boolean is_active
        +DateTime created_at
        +authenticate()
    }
    
    class Asset {
        +UUID id
        +String name
        +String ip_address
        +String status
        +String category
        +DateTime created_at
        +update_status()
    }
    
    class AnomalyRecord {
        +UUID id
        +String metric_name
        +Float score
        +String severity
        +String description
        +DateTime timestamp
        +Boolean acknowledged
        +acknowledge_record()
    }
    
    class Alert {
        +UUID id
        +UUID anomaly_record_id
        +String status
        +Boolean suppressed
        +DateTime created_at
        +suppress_alert()
    }
    
    class BenchmarkRun {
        +String run_id
        +DateTime timestamp
        +String[] models_evaluated
        +String overall_winner
        +Float total_benchmark_time_ms
        +String report_summary
        +String[] recommendations
    }

    User "1" --> "*" Asset : manages
    AnomalyRecord "1" <-- "1" Alert : triggers
    Asset "1" --> "*" AnomalyRecord : experiences
```

---

## 4. Core Modules

### 4.1 Frontend Operations (React + TypeScript)
- **State Layer**: Maintains low-overhead state triggers capturing WebSocket broadcasts.
- **Plotly Canvas**: Implements sub-second latency re-renders for sliding data windows, highlighting anomaly flags as discrete scatter markers overlaid on the telemetry curve.
- **Visual Design**: Cyber-dark Operations Room look-and-feel leveraging glassmorphism, responsive grid coordinates, and pulsing active state triggers.

### 4.2 API Layer (FastAPI)
- **Lifespan Manager**: Handles setup/teardown connections for database session factories and Redis connection pools.
- **WebSocket Gateway**: Broadsheet emitter pushing evaluated anomaly events to active UI clients.
- **Routing Modules**: Provides CRUD operations for logs, filters, user alerts, and model registries.

### 4.3 AI Pipeline (Python + PyTorch)
- **Temporal Ingestion**: Gathers metrics from Redis sliding window lists.
- **Data Normalizer**: Transforms sequence data using z-score scaler parameters calibrated during model fit.
- **Autoencoder Reconstruction**: Evaluates sequence vectors. If the mean squared error between input sequences and decodings surpasses standard sensitivity thresholds, it categorizes it as an anomaly.

### 4.4 Caching & Storage Layer (Redis & PostgreSQL)
- **Redis Cache**: Holds short-term telemetry sequence arrays. Executes pub/sub communication hooks to trigger AI assessment alerts.
- **PostgreSQL Database**: Acts as the transactional storage ledger, maintaining database indices of past incidents, user acknowledgements, settings, and ML weights checkpoints.
