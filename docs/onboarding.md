# ChronoShield AI: Developer Onboarding & Local Setup Guide

Welcome to the **ChronoShield AI** development team! This guide provides everything you need to know to map the codebase, configure a local development sandbox, run quality checks, and begin extending the platform.

---

## 1. Codebase Directory Mapping

Understanding the layout of the repository will help you navigate the codebase:

```
chronoshield-ai/
├── .github/workflows/       # GitHub Actions CI/CD pipeline definitions
│   ├── ci.yml               # Parallel linters, code quality, and testing pipeline
│   └── cd.yml               # Container building and deployment simulator
├── ai-engine/               # PyTorch ML Anomaly Detection engine project
│   ├── src/                 # PyTorch model architecture, ingestion, pipelines
│   ├── requirements.txt     # AI Engine pip requirements
│   └── ruff.toml            # AI Engine ruff linter configurations
├── backend/                 # Uvicorn FastAPI API Gateway project
│   ├── app/                 # Core backend modules
│   │   ├── configs/         # System settings configurations
│   │   ├── db/              # SQLAlchemy sessions & Redis cache connectors
│   │   ├── models/          # SQLAlchemy database tables mapping
│   │   ├── routes/          # REST endpoints and WebSocket pipelines
│   │   ├── schemas/         # Pydantic schemas validating payloads
│   │   ├── services/        # Backend business logic Orchestrators
│   │   ├── tests/           # Full pytest integration & unit test suite (253 tests)
│   │   └── utils/           # Prometheus clients, caches, and log formatting
│   ├── requirements.txt     # Backend pip requirements
│   └── ruff.toml            # Backend ruff linter configurations
├── docs/                    # Architectural & API Technical Specification suite
│   ├── architecture.md      # Microservice UML and sequence diagrams
│   ├── api.md               # Complete REST & WS endpoint specs
│   ├── deployment.md        # Docker Compose & Production configurations
│   └── onboarding.md        # Local workspace setup and developer tutorials
├── frontend/                # Vite React + TypeScript Dashboard project
│   ├── src/                 # React frontend source files
│   │   ├── api/             # Secure request hooks & mock pipelines
│   │   ├── components/      # UI components and view pages
│   │   ├── context/         # Auth, Theme, and API state context modules
│   │   └── types/           # Type definitions and navigation interfaces
│   ├── .eslintrc.cjs        # ESLint linter specifications
│   └── package.json         # Frontend Node.js dependencies
└── docker-compose.yml       # Production-ready orchestration mapping
```

---

## 2. Local Backend Environment Configuration
The backend automatically falls back to a **zero-dependency SQLite database** and **InMemoryTokenStore** in development when `USE_SQLITE_DEV = True` (the default), eliminating the need for a local PostgreSQL or Redis host during initial onboarding!

### Step 2.1 Set up the Virtual Environment & Dependencies
Initialize a clean Python virtualenv and install the required modules:
```bash
# Navigate to the backend directory
cd backend

# Create a Python 3.9 virtual environment
python3.9 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install core backend dependencies
pip install -r requirements.txt

# Install linting and formatting packages
pip install black ruff
```

### Step 2.2 Launch the Local FastAPI Development Server
Start Uvicorn with reload mapping enabled:
```bash
# Start Uvicorn development server
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Local Swagger UI Documentation**: Verify the gateway is running by navigating to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser.

---

## 3. Local Frontend Environment Configuration
Setup Vite, React, and Plotly dependencies.

### Step 3.1 Install Node modules
```bash
# Navigate to the frontend directory
cd frontend

# Install Node dependencies cleanly
npm install
```

### Step 3.2 Start the Vite Development Server
```bash
# Start Vite local development server
npm run dev
```
- **Local Dashboard UI View**: Open your browser and navigate to [http://localhost:5173](http://localhost:5173) to view the ChronoShield AI Operations Room.

---

## 4. Local Quality Control & Testing Enforcements
Our CI/CD pipeline enforces strict code quality gates. Enforce these locally before pushing code changes:

### 4.1 Frontend Quality Checks
Run TypeScript type-checking and ESLint checks:
```bash
# Run TypeScript compiler dry-run (verifies zero typecheck breaks)
npm run build

# Run ESLint check
npm run lint
```

### 4.2 Backend Linter Checks
Run Ruff syntax and styling validations:
```bash
# Run ruff check inside backend/ (verifies zero style checks fail)
venv/bin/ruff check app
```

### 4.3 Run Backend Automated Tests
Execute all 253 unit and integration tests using Pytest:
```bash
# Execute Pytest suite
PYTHONPATH=. ./venv/bin/pytest app/tests/
```

---

## 5. How-to-Extend Tutorial

Let's walk through how to add a brand new feature tab to the ChronoShield AI platform!

### Scenario: Add a new "Quantum Streams" (`quantum`) view to track future qubit operational telemetries.

#### Step 1: Create the new view component
Create `/frontend/src/components/views/QuantumStreams.tsx`:
```tsx
import React from "react";
import { Activity } from "lucide-react";

export const QuantumStreams: React.FC = () => {
  return (
    <div className="animate-fade-in" style={{ padding: "1.5rem" }}>
      <h2 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <Activity color="var(--accent-cyan)" />
        Quantum Streams Telemetry Desk
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        Real-time telemetry diagnostics of qubit coherence decay indexes.
      </p>
    </div>
  );
};
export default QuantumStreams;
```

#### Step 2: Register the new view tab
Open `/frontend/src/types/navigation.ts` and add `"quantum"` to the `ViewTab` type:
```typescript
export type ViewTab =
  | "health"
  | "monitoring"
  | "quantum" // Register new tab ID
  // ... other existing tabs
```

#### Step 3: Configure Sidebar Navigation Label & Roles
Open `/frontend/src/constants/navigation.ts` and register the new navigation link:
```typescript
export const SIDEBAR_LINKS = [
  // ...
  {
    id: "quantum",
    label: "Quantum Coherence",
    roles: ["ADMIN", "ANALYST"], // Define access scopes
  }
];
```

#### Step 4: Route the Component inside `App.tsx`
Open `/frontend/src/App.tsx`, import your new view, and append the routing case inside the `renderActiveView()` method:
```tsx
import QuantumStreams from "./components/views/QuantumStreams";

const renderActiveView = () => {
  switch (activeTab) {
    case "quantum": return <QuantumStreams />;
    // ... other switch cases
  }
};
```
Now, simply launch the Vite dev server and log in. Your new tab will automatically render on the sidebar, support light/dark styling shifts, and load smoothly with bezier transitions!
