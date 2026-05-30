# ChronoShield AI Test Suite Guidelines

This directory holds end-to-end integration tests, cluster scripts, and mock assertions verifying connectivity and data integrity across the frontend, backend, database, and AI engine containers.

---

## 🧪 Testing Pyramid

### 1. Backend Service Unit Tests
Uses `pytest` and `httpx` to verify REST endpoints, authentication middleware, log structures, and SQLAlchemy engines.
```bash
# Navigate to backend and launch pytest
cd backend
source venv/bin/activate
pytest app/tests/
```

### 2. AI Engine Pipeline Verification
Asserts dimensional shape integrity of the sliding window preprocessing layer and validates autoencoder reconstruction limits.
```bash
# Navigate to AI Engine and run unit tests
cd ai-engine
source venv/bin/activate
pytest src/tests/
```

### 3. Frontend React Component Tests
Uses Vitest or Jest along with React Testing Library to assert components mounts, Plotly resizes, and status badging logic.
```bash
# Navigate to frontend and run tests
cd frontend
npm run test
```

### 4. End-to-End Integration Suite
Leverages Docker Compose contexts to assert live pipeline workflows: feeding a simulated anomaly into the backend api, asserting the AI engine scoring process, and verifying Redis pub/sub routing down to the websocket gateway.
```bash
# Run integration check script from the monorepo root
python -m unittest tests/integration/test_anomaly_stream.py
```
