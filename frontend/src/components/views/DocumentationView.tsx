import React, { useState } from "react";
import {
  BookOpen,
  Code2,
  Terminal,
  Rocket,
  Layers,
  ChevronRight,
  ChevronDown,
  ExternalLink,
  Copy,
  CheckCheck,
  Search,
  Cpu,
  Shield,
  Activity,
  Brain,
  Database,
  GitBranch,
} from "lucide-react";

type DocSection = "overview" | "quickstart" | "api" | "architecture" | "deployment" | "ml";

interface DocItem {
  id: DocSection;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

interface CodeBlockProps {
  code: string;
  language?: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ code, language = "bash" }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        background: "var(--bg-panel)",
        border: "1px solid var(--border-card)",
        borderRadius: "10px",
        marginBottom: "1rem",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0.4rem 0.85rem",
          background: "rgba(0,0,0,0.25)",
          borderBottom: "1px solid var(--border-card)",
        }}
      >
        <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>
          {language}
        </span>
        <button
          onClick={handleCopy}
          style={{ background: "none", border: "none", color: copied ? "var(--accent-cyan)" : "var(--text-muted)", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.75rem" }}
        >
          {copied ? <><CheckCheck size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          padding: "1rem 1rem",
          fontFamily: "var(--font-mono)",
          fontSize: "0.8rem",
          color: "var(--text-primary)",
          lineHeight: 1.7,
          overflowX: "auto",
          whiteSpace: "pre",
        }}
      >
        {code}
      </pre>
    </div>
  );
};

interface CardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  tag?: string;
  tagColor?: string;
}

const DocCard: React.FC<CardProps> = ({ icon, title, description, tag, tagColor = "var(--accent-cyan)" }) => (
  <div
    style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border-card)",
      borderRadius: "12px",
      padding: "1.1rem",
      transition: "border-color 0.2s, transform 0.15s",
      cursor: "default",
    }}
    onMouseEnter={e => {
      (e.currentTarget as HTMLDivElement).style.borderColor = "var(--accent-cyan)";
      (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
    }}
    onMouseLeave={e => {
      (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-card)";
      (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
    }}
  >
    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
      <div style={{ color: tagColor, flexShrink: 0, marginTop: "0.1rem" }}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
          <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.9rem" }}>{title}</span>
          {tag && (
            <span style={{ fontSize: "0.65rem", padding: "0.1rem 0.45rem", borderRadius: "20px", background: `${tagColor}20`, color: tagColor, fontWeight: 700, textTransform: "uppercase" }}>
              {tag}
            </span>
          )}
        </div>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: 0, lineHeight: 1.55 }}>{description}</p>
      </div>
    </div>
  </div>
);

interface AccordionProps {
  title: string;
  children: React.ReactNode;
}

const Accordion: React.FC<AccordionProps> = ({ title, children }) => {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ border: "1px solid var(--border-card)", borderRadius: "10px", marginBottom: "0.6rem", overflow: "hidden" }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0.85rem 1rem", background: "var(--bg-card)", border: "none",
          color: "var(--text-primary)", cursor: "pointer", fontWeight: 600, fontSize: "0.88rem",
          textAlign: "left",
        }}
      >
        {title}
        {open ? <ChevronDown size={15} color="var(--accent-cyan)" /> : <ChevronRight size={15} color="var(--text-muted)" />}
      </button>
      {open && (
        <div style={{ padding: "1rem", background: "var(--bg-panel)", borderTop: "1px solid var(--border-card)" }}>
          {children}
        </div>
      )}
    </div>
  );
};

const DOC_SECTIONS: DocItem[] = [
  { id: "overview",      label: "Overview",       icon: <BookOpen size={15} />,  badge: "Start Here" },
  { id: "quickstart",    label: "Quick Start",    icon: <Rocket size={15} />,    badge: "5 min" },
  { id: "api",           label: "API Reference",  icon: <Code2 size={15} /> },
  { id: "architecture",  label: "Architecture",   icon: <Layers size={15} /> },
  { id: "deployment",    label: "Deployment",     icon: <Terminal size={15} /> },
  { id: "ml",            label: "AI / ML Guide",  icon: <Brain size={15} /> },
];

export const DocumentationView: React.FC = () => {
  const [activeSection, setActiveSection] = useState<DocSection>("overview");
  const [search, setSearch] = useState("");

  const renderContent = () => {
    switch (activeSection) {
      case "overview":
        return (
          <div>
            <div style={{ marginBottom: "1.75rem" }}>
              <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", margin: "0 0 0.5rem" }}>
                ChronoShield AI Platform
              </h2>
              <p style={{ color: "var(--text-muted)", fontSize: "0.88rem", lineHeight: 1.7, maxWidth: 640 }}>
                ChronoShield AI is an enterprise-grade infrastructure monitoring platform combining real-time telemetry ingestion, transformer-based anomaly detection, and causal AI for predictive incident response.
              </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem", marginBottom: "2rem" }}>
              <DocCard icon={<Activity size={18} />} title="Live Monitoring" description="Stream sensor telemetry at up to 50K events/second with sub-200ms alerting latency." tag="Core" />
              <DocCard icon={<Brain size={18} />} title="Anomaly Detection" description="TimeFormer transformer model trained on 14M infrastructure events achieves 94.7% F1." tag="AI" tagColor="var(--accent-violet)" />
              <DocCard icon={<Shield size={18} />} title="Security & Auth" description="JWT-based RBAC with VIEWER, ANALYST and ADMIN role tiers. MFA support included." tag="Security" tagColor="var(--accent-rose)" />
              <DocCard icon={<Database size={18} />} title="Data Pipeline" description="Apache Kafka → TimescaleDB → feature pipeline with automated model retraining." tag="Infra" tagColor="var(--accent-amber)" />
              <DocCard icon={<GitBranch size={18} />} title="CI/CD Pipeline" description="Automated GitHub Actions workflows for lint, test, build and deployment verification." tag="DevOps" tagColor="var(--accent-emerald)" />
              <DocCard icon={<Cpu size={18} />} title="Model Registry" description="Versioned ML model storage with A/B canary evaluation and automatic rollback." tag="MLOps" tagColor="var(--accent-cyan)" />
            </div>

            <div style={{ background: "rgba(0,245,212,0.07)", border: "1px solid rgba(0,245,212,0.2)", borderRadius: "12px", padding: "1.25rem" }}>
              <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.6rem" }}>System Requirements</h4>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem", fontSize: "0.82rem", color: "var(--text-muted)" }}>
                {[
                  ["Python", "≥ 3.11"],
                  ["Node.js", "≥ 18 LTS"],
                  ["Docker", "≥ 24.0"],
                  ["RAM", "≥ 8 GB"],
                  ["GPU", "Optional (CUDA 12+)"],
                  ["Storage", "≥ 50 GB SSD"],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid var(--border-card)" }}>
                    <span>{k}</span><span style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case "quickstart":
        return (
          <div>
            <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)", margin: "0 0 0.5rem" }}>Quick Start Guide</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>Get ChronoShield running locally in under 5 minutes.</p>

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>1. Clone the repository</h4>
            <CodeBlock language="bash" code={`git clone https://github.com/your-org/chronoshield-ai.git
cd chronoshield-ai`} />

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>2. Configure environment variables</h4>
            <CodeBlock language="bash" code={`cp .env.example .env
# Edit .env and set DATABASE_URL, SECRET_KEY, AI_ENGINE_URL`} />

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>3. Start all services with Docker Compose</h4>
            <CodeBlock language="bash" code={`docker compose up -d --build

# Verify all services are healthy
docker compose ps`} />

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>4. Seed demo data and open the dashboard</h4>
            <CodeBlock language="bash" code={`# Seed database with sample telemetry
python scripts/seed_demo_data.py

# Open the dashboard
open http://localhost:5173

# Default credentials
# Username: admin@chronoshield.ai  Password: admin123`} />

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>5. Run tests</h4>
            <CodeBlock language="bash" code={`# Backend tests (253 tests)
cd backend && python -m pytest tests/ -v

# Frontend lint + type check
cd frontend && npm run lint && npm run build`} />
          </div>
        );

      case "api":
        return (
          <div>
            <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)", margin: "0 0 0.5rem" }}>REST API Reference</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
              Base URL: <code style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", fontSize: "0.85rem" }}>http://localhost:8000/api/v1</code>
            </p>

            {[
              {
                group: "Authentication",
                color: "var(--accent-emerald)",
                endpoints: [
                  { method: "POST", path: "/auth/login", desc: "Authenticate and receive JWT token pair" },
                  { method: "POST", path: "/auth/refresh", desc: "Refresh access token using refresh token" },
                  { method: "POST", path: "/auth/logout", desc: "Invalidate current session tokens" },
                ],
              },
              {
                group: "Anomaly Detection",
                color: "var(--accent-violet)",
                endpoints: [
                  { method: "GET",  path: "/anomaly/",          desc: "List all detected anomalies (paginated)" },
                  { method: "GET",  path: "/anomaly/{id}",      desc: "Get a single anomaly with explanation" },
                  { method: "POST", path: "/anomaly/predict",   desc: "Submit raw telemetry for live inference" },
                  { method: "GET",  path: "/anomaly/stats",     desc: "Aggregated anomaly statistics and trends" },
                ],
              },
              {
                group: "Alerts",
                color: "var(--accent-rose)",
                endpoints: [
                  { method: "GET",    path: "/alert/",        desc: "List all active and historical alerts" },
                  { method: "POST",   path: "/alert/",        desc: "Manually create an alert" },
                  { method: "PATCH",  path: "/alert/{id}",    desc: "Update alert status (acknowledge, resolve)" },
                  { method: "DELETE", path: "/alert/{id}",    desc: "Delete an alert record" },
                ],
              },
              {
                group: "Assets",
                color: "var(--accent-amber)",
                endpoints: [
                  { method: "GET",  path: "/asset/",      desc: "List all registered infrastructure assets" },
                  { method: "POST", path: "/asset/",      desc: "Register a new infrastructure asset" },
                  { method: "GET",  path: "/asset/{id}",  desc: "Get asset details and telemetry summary" },
                  { method: "PUT",  path: "/asset/{id}",  desc: "Update asset metadata and configuration" },
                ],
              },
            ].map(group => (
              <div key={group.group} style={{ marginBottom: "1.75rem" }}>
                <h4 style={{ color: group.color, fontWeight: 700, marginBottom: "0.65rem", fontSize: "0.95rem" }}>{group.group}</h4>
                {group.endpoints.map(ep => (
                  <div
                    key={ep.path}
                    style={{
                      display: "flex", alignItems: "flex-start", gap: "0.75rem",
                      padding: "0.7rem 0.9rem", marginBottom: "0.4rem",
                      background: "var(--bg-card)", borderRadius: "8px",
                      border: "1px solid var(--border-card)",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.68rem", fontWeight: 800, fontFamily: "var(--font-mono)",
                        padding: "0.2rem 0.55rem", borderRadius: "5px", flexShrink: 0,
                        background: ep.method === "GET" ? "rgba(0,245,212,0.15)" : ep.method === "POST" ? "rgba(139,92,246,0.15)" : ep.method === "PATCH" ? "rgba(245,158,11,0.15)" : "rgba(239,68,68,0.15)",
                        color: ep.method === "GET" ? "var(--accent-cyan)" : ep.method === "POST" ? "var(--accent-violet)" : ep.method === "PATCH" ? "var(--accent-amber)" : "var(--accent-rose)",
                      }}
                    >
                      {ep.method}
                    </span>
                    <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem", color: "var(--text-primary)", flexShrink: 0 }}>{ep.path}</code>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{ep.desc}</span>
                  </div>
                ))}
              </div>
            ))}

            <CodeBlock language="bash" code={`# Example: Authenticate and fetch anomalies
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email":"admin@chronoshield.ai","password":"admin123"}' \\
  | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" \\
  http://localhost:8000/api/v1/anomaly/?limit=10`} />
          </div>
        );

      case "architecture":
        return (
          <div>
            <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)", margin: "0 0 0.5rem" }}>System Architecture</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
              ChronoShield follows a microservices architecture with clear domain boundaries.
            </p>

            <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-card)", borderRadius: "12px", padding: "1.5rem", marginBottom: "1.5rem", fontFamily: "var(--font-mono)", fontSize: "0.8rem", lineHeight: 1.9, color: "var(--text-muted)" }}>
              <div style={{ color: "var(--accent-cyan)", fontWeight: 700, marginBottom: "0.5rem" }}>{"// Service Dependency Graph"}</div>
              <div><span style={{ color: "var(--accent-violet)" }}>{"[React Dashboard]"}</span> {"───► "}<span style={{ color: "var(--accent-cyan)" }}>{"[FastAPI Backend]"}</span> {"───► "}<span style={{ color: "var(--accent-amber)" }}>{"[PostgreSQL]"}</span></div>
              <div style={{ paddingLeft: "6rem" }}>{"└───────────► "}<span style={{ color: "var(--accent-violet)" }}>{"[AI Engine]"}</span> {"───► "}<span style={{ color: "var(--accent-amber)" }}>{"[Model Registry]"}</span></div>
              <div style={{ paddingLeft: "6rem" }}>{"└───────────► "}<span style={{ color: "var(--accent-emerald)" }}>{"[Prometheus]"}</span> {"◄─► "}<span style={{ color: "var(--accent-emerald)" }}>{"[Grafana]"}</span></div>
              <div style={{ paddingLeft: "6rem" }}>{"└───────────► "}<span style={{ color: "var(--accent-rose)" }}>{"[Redis Cache]"}</span></div>
            </div>

            {[
              { title: "Frontend (React + Vite)", desc: "TypeScript SPA with lazy-loaded views, React Context state management, Recharts visualisations, and role-based access control via JWT claims." },
              { title: "Backend (FastAPI)", desc: "Async Python REST API with SQLAlchemy ORM, Alembic migrations, Pydantic v2 schemas, JWT auth middleware, and Prometheus metrics endpoint." },
              { title: "AI Engine (FastAPI + PyTorch)", desc: "Standalone inference service hosting the TimeFormer transformer model. Handles real-time prediction, model versioning, and canary deployments." },
              { title: "Data Layer", desc: "TimescaleDB (PostgreSQL extension) for time-series telemetry. Redis for rate limiting and hot-path caching. MinIO for model artifact storage." },
              { title: "Observability", desc: "Prometheus scrapes /metrics from backend and AI engine. Grafana dashboards for operational visibility. Structured JSON logging via structlog." },
            ].map(s => (
              <Accordion key={s.title} title={s.title}>
                <p style={{ fontSize: "0.84rem", color: "var(--text-muted)", margin: 0, lineHeight: 1.65 }}>{s.desc}</p>
              </Accordion>
            ))}
          </div>
        );

      case "deployment":
        return (
          <div>
            <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)", margin: "0 0 0.5rem" }}>Deployment Guide</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>Production deployment on Kubernetes / Docker Swarm.</p>

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>Docker Compose (Local / Staging)</h4>
            <CodeBlock language="bash" code={`# Build and start all 6 services
docker compose -f docker-compose.yml up -d --build

# Scale AI engine workers
docker compose up -d --scale ai-engine=3`} />

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>Environment Variables (Required)</h4>
            <CodeBlock language="env" code={`DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/chronoshield
SECRET_KEY=your-256-bit-secret-key
AI_ENGINE_URL=http://ai-engine:8001
REDIS_URL=redis://redis:6379/0
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
LOG_LEVEL=INFO`} />

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>Database Migrations</h4>
            <CodeBlock language="bash" code={`# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Create a new migration
docker compose exec backend alembic revision --autogenerate -m "add_asset_tags"`} />

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>Health Checks</h4>
            <CodeBlock language="bash" code={`curl http://localhost:8000/health          # Backend
curl http://localhost:8001/health          # AI Engine
curl http://localhost:9090/-/healthy       # Prometheus`} />
          </div>
        );

      case "ml":
        return (
          <div>
            <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)", margin: "0 0 0.5rem" }}>AI / ML Developer Guide</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
              The anomaly detection core uses a TimeFormer encoder trained on 14M labelled infrastructure telemetry events.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem", marginBottom: "1.5rem" }}>
              {[
                { label: "Model Architecture", value: "TimeFormer Transformer" },
                { label: "Input Window", value: "128 timesteps" },
                { label: "Feature Dimensions", value: "64-D embeddings" },
                { label: "Training Dataset", value: "14.2M events" },
                { label: "F1 Score (test)", value: "94.7%" },
                { label: "Inference Latency", value: "< 18ms p95" },
              ].map(m => (
                <div key={m.label} style={{ background: "var(--bg-card)", border: "1px solid var(--border-card)", borderRadius: "10px", padding: "0.85rem 1rem" }}>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.04em" }}>{m.label}</div>
                  <div style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", fontWeight: 700, fontSize: "1rem", marginTop: "0.25rem" }}>{m.value}</div>
                </div>
              ))}
            </div>

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>Train a custom model</h4>
            <CodeBlock language="python" code={`from ai_engine.src.models.anomaly_detector import AnomalyDetector
from ai_engine.src.ml.registry import ModelRegistry

# Initialise model
model = AnomalyDetector(
    input_dim=64,
    seq_len=128,
    num_heads=8,
    num_layers=4,
)

# Train (replace with your DataLoader)
model.fit(train_loader, val_loader, epochs=50)

# Register in model registry
registry = ModelRegistry()
registry.save(model, version="v2.1.0", metadata={"f1": 0.954})`} />

            <h4 style={{ color: "var(--accent-cyan)", fontWeight: 700, margin: "0 0 0.65rem" }}>Run inference via API</h4>
            <CodeBlock language="python" code={`import httpx, numpy as np

payload = {
    "sensor_id": "transformer-042",
    "readings": np.random.randn(128, 64).tolist(),
    "timestamp": "2025-01-15T10:30:00Z",
}

resp = httpx.post("http://localhost:8001/api/v1/predict", json=payload)
print(resp.json())
# {"anomaly_score": 0.89, "is_anomaly": true, "confidence": 0.94}`} />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", maxWidth: 960, margin: "0 auto", padding: "0 0.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            Documentation
          </h2>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", margin: "0.25rem 0 0" }}>
            Developer guides, API reference, and deployment runbooks
          </p>
        </div>
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          style={{
            display: "flex", alignItems: "center", gap: "0.4rem",
            padding: "0.55rem 1rem", background: "var(--bg-card)",
            border: "1px solid var(--border-card)", borderRadius: "8px",
            color: "var(--text-muted)", textDecoration: "none", fontSize: "0.82rem",
            transition: "border-color 0.2s",
          }}
          onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--accent-cyan)")}
          onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border-card)")}
        >
          <ExternalLink size={13} /> View on GitHub
        </a>
      </div>

      {/* Search bar */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", background: "var(--bg-card)", border: "1px solid var(--border-card)", borderRadius: "10px", padding: "0.65rem 1rem" }}>
        <Search size={15} color="var(--text-muted)" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search documentation..."
          style={{ flex: 1, background: "none", border: "none", outline: "none", color: "var(--text-primary)", fontSize: "0.88rem" }}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: "1.25rem" }}>
        {/* Left nav */}
        <div style={{ background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border-card)", padding: "0.5rem", height: "fit-content" }}>
          {DOC_SECTIONS.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              style={{
                display: "flex", alignItems: "center", gap: "0.6rem", width: "100%",
                padding: "0.7rem 0.85rem", borderRadius: "8px", border: "none",
                background: activeSection === item.id ? "rgba(0,245,212,0.1)" : "transparent",
                color: activeSection === item.id ? "var(--accent-cyan)" : "var(--text-muted)",
                cursor: "pointer", fontWeight: activeSection === item.id ? 700 : 400,
                fontSize: "0.85rem", transition: "all 0.2s", marginBottom: "0.2rem",
                textAlign: "left",
              }}
            >
              {item.icon}
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.badge && (
                <span style={{ fontSize: "0.6rem", padding: "0.1rem 0.4rem", borderRadius: "20px", background: "rgba(0,245,212,0.15)", color: "var(--accent-cyan)", fontWeight: 700 }}>
                  {item.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Right content */}
        <div style={{ background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border-card)", padding: "1.75rem", minHeight: 400 }}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default DocumentationView;
