import React, { useState, useEffect, useCallback } from "react";
import {
  Brain, Zap, Car, Droplets, Wifi, Building2,
  AlertCircle, CheckCircle, ChevronDown, ChevronRight,
  Lightbulb, Link2, GitBranch, Target, Cpu,
  RefreshCw, ArrowRight, BarChart2, Shield, Info,
  TrendingUp, Clock, MapPin, Activity,
} from "lucide-react";
import {
  explainBatch,
  AnomalyExplanation,
  ContributingFactor,
  ReasoningStep,
  DEMO_ANOMALIES,
} from "../../api/explain";

// ==============================================================================
// Design constants
// ==============================================================================
const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#ff0044",
  WARNING:  "#ff8c00",
  INFO:     "#00b8ff",
};

const CATEGORY_COLORS: Record<string, string> = {
  POWER:                 "#ff8c00",
  TRAFFIC:               "#a855f7",
  WATER:                 "#0ea5e9",
  INTERNET:              "#00e5ff",
  PUBLIC_INFRASTRUCTURE: "#22c55e",
  WEATHER:               "#6ee7b7",
  TEMPORAL:              "#818cf8",
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  POWER:                 <Zap size={12} />,
  TRAFFIC:               <Car size={12} />,
  WATER:                 <Droplets size={12} />,
  INTERNET:              <Wifi size={12} />,
  PUBLIC_INFRASTRUCTURE: <Building2 size={12} />,
  WEATHER:               <Activity size={12} />,
  TEMPORAL:              <Clock size={12} />,
};

const FACTOR_TYPE_COLORS: Record<string, string> = {
  PRIMARY:     "#ef4444",
  AMPLIFIER:   "#f97316",
  CORRELATE:   "#a855f7",
  ENVIRONMENTAL:"#22c55e",
  TEMPORAL:    "#818cf8",
};

const STEP_TYPE_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  OBSERVE:    { color: "#00b8ff", icon: <Activity size={13} />,    label: "Observe"    },
  HYPOTHESIZE:{ color: "#eab308", icon: <Lightbulb size={13} />,   label: "Hypothesize"},
  CORRELATE:  { color: "#a855f7", icon: <Link2 size={13} />,       label: "Correlate"  },
  CONCLUDE:   { color: "#f97316", icon: <Target size={13} />,      label: "Conclude"   },
  RECOMMEND:  { color: "#22c55e", icon: <CheckCircle size={13} />, label: "Recommend"  },
};

const CASCADE_RISK_COLORS: Record<string, string> = {
  LOW:      "#22c55e",
  MODERATE: "#eab308",
  HIGH:     "#f97316",
  CRITICAL: "#ef4444",
};

const QUALITY_COLORS: Record<string, string> = {
  STRONG:     "#22c55e",
  MODERATE:   "#eab308",
  SPECULATIVE:"#9ca3af",
};

// ==============================================================================
// Sub-components
// ==============================================================================

/** Animated confidence ring */
const ConfidenceRing: React.FC<{ value: number; size?: number; label?: string }> = ({ value, size = 56, label }) => {
  const r = (size - 6) / 2;
  const circ = 2 * Math.PI * r;
  const dash = value * circ;
  const color = value >= 0.75 ? "#22c55e" : value >= 0.55 ? "#eab308" : "#9ca3af";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.2rem" }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="hsla(217,32%,18%,0.5)" strokeWidth={5} />
        <circle
          cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={5}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: "stroke-dasharray 0.8s ease" }}
        />
        <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="middle"
          style={{ transform: "rotate(90deg)", transformOrigin: `${size/2}px ${size/2}px` }}
          fill={color} fontSize={size * 0.22} fontWeight={800} fontFamily="monospace">
          {Math.round(value * 100)}%
        </text>
      </svg>
      {label && <span style={{ fontSize: "0.6rem", color: "var(--text-muted)", textAlign: "center" }}>{label}</span>}
    </div>
  );
};

/** Factor type badge */
const FactorTypeBadge: React.FC<{ type: string }> = ({ type }) => {
  const color = FACTOR_TYPE_COLORS[type] ?? "#9ca3af";
  const labels: Record<string, string> = { PRIMARY: "Root Cause", AMPLIFIER: "Amplifier", CORRELATE: "Correlate", ENVIRONMENTAL: "Environment", TEMPORAL: "Temporal" };
  return (
    <span style={{ padding: "0.1rem 0.4rem", borderRadius: "6px", fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.05em", background: `${color}18`, color, border: `1px solid ${color}33` }}>
      {labels[type] ?? type}
    </span>
  );
};

/** Weight bar */
const WeightBar: React.FC<{ value: number; color?: string; label?: string }> = ({ value, color = "var(--accent-cyan)", label }) => (
  <div style={{ width: "100%" }}>
    {label && <div style={{ fontSize: "0.6rem", color: "var(--text-muted)", marginBottom: "0.2rem" }}>{label}</div>}
    <div style={{ height: 4, background: "hsla(217,32%,18%,0.6)", borderRadius: "4px", overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${value * 100}%`, background: `linear-gradient(90deg, ${color}88, ${color})`, borderRadius: "4px", transition: "width 0.6s ease" }} />
    </div>
  </div>
);

/** Expandable contributing factor card */
const FactorCard: React.FC<{ factor: ContributingFactor; index: number }> = ({ factor, index }) => {
  const [open, setOpen] = useState(index < 2);
  const color = FACTOR_TYPE_COLORS[factor.factor_type] ?? "#9ca3af";
  const catColor = CATEGORY_COLORS[factor.category] ?? "#9ca3af";

  return (
    <div style={{
      borderRadius: 10, marginBottom: "0.5rem", overflow: "hidden",
      border: `1px solid ${open ? color + "44" : "var(--border-card)"}`,
      background: open ? `${color}08` : "hsla(223,47%,10%,0.4)",
      transition: "all 0.2s",
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{ width: "100%", background: "transparent", border: "none", cursor: "pointer", padding: "0.65rem 0.85rem", display: "flex", alignItems: "center", gap: "0.5rem", textAlign: "left" }}
      >
        <div style={{ width: 20, height: 20, borderRadius: "50%", background: `${color}22`, border: `1.5px solid ${color}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: "0.62rem", color, fontWeight: 800 }}>
          {index + 1}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.15rem" }}>
            <FactorTypeBadge type={factor.factor_type} />
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {factor.name}
            </span>
          </div>
          <WeightBar value={factor.weight} color={color} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
          <span style={{ fontSize: "0.68rem", fontFamily: "var(--font-mono)", color: `${color}`, fontWeight: 700 }}>
            {(factor.confidence * 100).toFixed(0)}%
          </span>
          <span style={{ color: "var(--text-muted)" }}>
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
        </div>
      </button>

      {open && (
        <div style={{ padding: "0 0.85rem 0.75rem" }}>
          <p style={{ fontSize: "0.73rem", color: "var(--text-secondary)", margin: "0 0 0.6rem 0", lineHeight: 1.6 }}>
            {factor.description}
          </p>

          {/* Category + metric refs */}
          <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem", padding: "0.1rem 0.4rem", borderRadius: "6px", fontSize: "0.62rem", fontWeight: 700, background: `${catColor}15`, color: catColor, border: `1px solid ${catColor}30` }}>
              {CATEGORY_ICONS[factor.category]}
              {factor.category.replace("_", " ")}
            </span>
          </div>

          {/* Evidence list */}
          {factor.evidence.length > 0 && (
            <div style={{ fontSize: "0.68rem" }}>
              <div style={{ color: "var(--text-muted)", marginBottom: "0.25rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", fontSize: "0.6rem" }}>
                Supporting Evidence
              </div>
              {factor.evidence.map((e, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "0.4rem", padding: "0.2rem 0", color: "var(--text-secondary)" }}>
                  <span style={{ color, marginTop: 1, flexShrink: 0 }}>›</span>
                  {e}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/** Reasoning chain step */
const ReasoningStepCard: React.FC<{ step: ReasoningStep; isLast: boolean }> = ({ step, isLast }) => {
  const [open, setOpen] = useState(step.step_index <= 1);
  const cfg = STEP_TYPE_CONFIG[step.step_type] ?? { color: "#9ca3af", icon: <Info size={13} />, label: step.step_type };

  return (
    <div style={{ display: "flex", gap: "0.75rem", marginBottom: isLast ? 0 : "0.5rem" }}>
      {/* Timeline track */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, width: 32 }}>
        <div style={{
          width: 32, height: 32, borderRadius: "50%", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
          background: `${cfg.color}20`, border: `2px solid ${cfg.color}`, color: cfg.color,
        }}>
          {cfg.icon}
        </div>
        {!isLast && <div style={{ width: 2, flex: 1, background: "var(--border-card)", margin: "0.25rem 0", minHeight: 16 }} />}
      </div>

      {/* Content */}
      <div style={{ flex: 1, paddingTop: "0.35rem" }}>
        <button
          onClick={() => setOpen(o => !o)}
          style={{ width: "100%", background: "transparent", border: "none", cursor: "pointer", padding: 0, display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: open ? "0.4rem" : 0 }}
        >
          <span style={{ fontSize: "0.62rem", fontWeight: 700, color: cfg.color, textTransform: "uppercase", letterSpacing: "0.07em" }}>{cfg.label}</span>
          <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--text-primary)", textAlign: "left" }}>{step.title}</span>
          <span style={{ marginLeft: "auto", color: "var(--text-muted)" }}>
            {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </span>
          <span style={{ fontSize: "0.62rem", fontFamily: "var(--font-mono)", color: cfg.color, flexShrink: 0 }}>
            {(step.confidence * 100).toFixed(0)}%
          </span>
        </button>
        {open && (
          <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", lineHeight: 1.65, paddingBottom: "0.5rem" }}>
            {step.detail}
          </div>
        )}
      </div>
    </div>
  );
};

/** Correlation chain SVG visualization */
const CorrelationChainViz: React.FC<{ explanation: AnomalyExplanation }> = ({ explanation }) => {
  const { contributing_factors, correlation_chain } = explanation;
  if (contributing_factors.length === 0) return null;

  const maxDisplay = Math.min(contributing_factors.length, 6);
  const factors = contributing_factors.slice(0, maxDisplay);

  const REL_COLORS: Record<string, string> = {
    CAUSED: "#ef4444", AMPLIFIED: "#f97316", TRIGGERED: "#f97316",
    CORRELATED: "#a855f7", PRECEDED: "#818cf8",
  };

  return (
    <div style={{ padding: "0.75rem 0" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
        {factors.map((f, i) => {
          const color = FACTOR_TYPE_COLORS[f.factor_type] ?? "#9ca3af";
          const outLinks = correlation_chain.filter(l => l.from_factor === f.factor_id);
          const inLinks  = correlation_chain.filter(l => l.to_factor   === f.factor_id);
          const hasArrow = outLinks.length > 0;
          const rel = hasArrow ? outLinks[0].relationship : inLinks[0]?.relationship;
          const relColor = REL_COLORS[rel ?? ""] ?? "#9ca3af";

          return (
            <React.Fragment key={f.factor_id}>
              <div style={{
                padding: "0.35rem 0.6rem", borderRadius: "8px",
                background: `${color}18`, border: `1px solid ${color}44`,
                display: "flex", flexDirection: "column", gap: "0.15rem", minWidth: 90,
              }}>
                <span style={{ fontSize: "0.62rem", fontWeight: 700, color, letterSpacing: "0.04em" }}>{f.factor_id}</span>
                <span style={{ fontSize: "0.65rem", color: "var(--text-secondary)", lineHeight: 1.3, maxWidth: 100 }}>
                  {f.name.length > 18 ? f.name.slice(0, 17) + "…" : f.name}
                </span>
                <WeightBar value={f.weight} color={color} />
              </div>
              {hasArrow && i < maxDisplay - 1 && (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.1rem" }}>
                  <span style={{ fontSize: "0.55rem", color: relColor, textTransform: "uppercase", fontWeight: 700 }}>{rel}</span>
                  <ArrowRight size={14} color={relColor} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

/** Anomaly selector list item */
const AnomalyListItem: React.FC<{
  anomaly: typeof DEMO_ANOMALIES[0];
  isSelected: boolean;
  isLoading: boolean;
  explanation: AnomalyExplanation | null;
  onClick: () => void;
}> = ({ anomaly, isSelected, isLoading, explanation, onClick }) => {
  const sColor = SEVERITY_COLORS[anomaly.severity] ?? "#00b8ff";
  const catColor = CATEGORY_COLORS[anomaly.category] ?? "#9ca3af";

  return (
    <button
      onClick={onClick}
      style={{
        width: "100%", textAlign: "left", background: "transparent", border: "none", cursor: "pointer", padding: 0,
        marginBottom: "0.4rem",
      }}
    >
      <div style={{
        padding: "0.65rem 0.85rem", borderRadius: 10,
        border: `1px solid ${isSelected ? "var(--accent-cyan)" : "var(--border-card)"}`,
        background: isSelected ? "hsla(180,100%,45%,0.06)" : "hsla(223,47%,10%,0.45)",
        transition: "all 0.2s",
        display: "flex", alignItems: "center", gap: "0.5rem",
      }}>
        <div style={{ width: 7, height: 7, borderRadius: "50%", background: sColor, flexShrink: 0, boxShadow: isSelected ? `0 0 6px ${sColor}` : "none" }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", marginBottom: "0.15rem" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: isSelected ? "var(--accent-cyan)" : "var(--text-muted)" }}>{anomaly.anomaly_id}</span>
            <span style={{ padding: "0.05rem 0.3rem", borderRadius: "4px", fontSize: "0.58rem", fontWeight: 700, background: `${sColor}20`, color: sColor }}>{anomaly.severity}</span>
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {anomaly.metric_name.replace(/_/g, " ")}
          </div>
        </div>
        {isLoading && <div style={{ width: 12, height: 12, borderRadius: "50%", border: "2px solid var(--accent-cyan)", borderTopColor: "transparent", animation: "spin 0.8s linear infinite", flexShrink: 0 }} />}
        {!isLoading && explanation && (
          <span style={{ fontSize: "0.62rem", fontFamily: "var(--font-mono)", color: QUALITY_COLORS[explanation.explanation_quality], flexShrink: 0 }}>
            {(explanation.overall_confidence * 100).toFixed(0)}%
          </span>
        )}
        {!isLoading && !explanation && (
          <span style={{ color: catColor, flexShrink: 0 }}>{CATEGORY_ICONS[anomaly.category]}</span>
        )}
      </div>
    </button>
  );
};

// ==============================================================================
// Main ExplainableAI View
// ==============================================================================
export const ExplainableAI: React.FC = () => {
  const [explanations, setExplanations] = useState<Record<string, AnomalyExplanation>>({});
  const [selectedId, setSelectedId] = useState<string>("INC-005");
  const [loading, setLoading] = useState(false);
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<"factors" | "reasoning" | "chain" | "actions">("factors");
  const [batchLoaded, setBatchLoaded] = useState(false);
  const [systemNarrative, setSystemNarrative] = useState<string>("");
  const [crossPatterns, setCrossPatterns] = useState<string[]>([]);

  // ── Load all explanations in batch on mount ──────────────────────────────
  const loadBatch = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await explainBatch(DEMO_ANOMALIES);
      const map: Record<string, AnomalyExplanation> = {};
      resp.explanations.forEach(e => { map[e.anomaly_id] = e; });
      setExplanations(map);
      setSystemNarrative(resp.system_narrative);
      setCrossPatterns(resp.cross_incident_patterns);
      setBatchLoaded(true);
    } catch (err) {
      console.error("Batch explain failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadBatch(); }, [loadBatch]);

  const selected = explanations[selectedId] ?? null;
  const selectedAnomaly = DEMO_ANOMALIES.find(a => a.anomaly_id === selectedId);

  const sColor = selected ? SEVERITY_COLORS[selected.severity] ?? "#00b8ff" : "var(--accent-cyan)";
  const cascadeColor = selected ? CASCADE_RISK_COLORS[selected.cascade_risk] ?? "#eab308" : "#eab308";
  const qualColor = selected ? QUALITY_COLORS[selected.explanation_quality] ?? "#9ca3af" : "#9ca3af";

  // ==============================================================================
  return (
    <div className="xai-root">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="xai-header">
        <div>
          <h2 style={{ fontSize: "1.3rem", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
            <Brain size={20} color="#a855f7" />
            Explainable AI Reasoning
          </h2>
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
            Transparent causal analysis · Natural language explanations · Decision traceability
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
          <div style={{ padding: "0.3rem 0.75rem", borderRadius: "8px", background: "hsla(265,89%,60%,0.12)", border: "1px solid hsla(265,89%,60%,0.3)", fontSize: "0.7rem", color: "#a855f7", fontWeight: 600 }}>
            <Cpu size={11} style={{ marginRight: "0.3rem", verticalAlign: "middle" }} />
            ChronoShield-XAI-v2.4
          </div>
          <button
            onClick={loadBatch}
            disabled={loading}
            style={{ display: "flex", alignItems: "center", gap: "0.4rem", padding: "0.4rem 0.85rem", borderRadius: "8px", fontSize: "0.78rem", fontWeight: 600, border: "1px solid var(--border-card)", background: "hsla(217,32%,18%,0.5)", color: "var(--text-secondary)", cursor: "pointer", opacity: loading ? 0.6 : 1 }}
          >
            <RefreshCw size={13} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            Reload
          </button>
        </div>
      </div>

      {/* ── System-level narrative banner ──────────────────────────────────── */}
      {systemNarrative && (
        <div className="xai-narrative-banner">
          <div style={{ display: "flex", gap: "0.6rem", alignItems: "flex-start" }}>
            <Brain size={16} color="#a855f7" style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "#a855f7", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.3rem" }}>
                System-Level AI Assessment
              </div>
              <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {systemNarrative}
              </p>
            </div>
          </div>
          {crossPatterns.length > 0 && (
            <div style={{ marginTop: "0.6rem", display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
              {crossPatterns.map((p, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "0.4rem", background: "hsla(265,89%,60%,0.08)", border: "1px solid hsla(265,89%,60%,0.2)", borderRadius: "8px", padding: "0.35rem 0.55rem", fontSize: "0.68rem", color: "var(--text-secondary)", maxWidth: "100%" }}>
                  <GitBranch size={11} color="#a855f7" style={{ flexShrink: 0, marginTop: 1 }} />
                  {p}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Main Body ─────────────────────────────────────────────────────── */}
      <div className="xai-body">
        {/* Left: Anomaly selector list */}
        <div className="xai-selector">
          <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.65rem" }}>
            Incident Library ({DEMO_ANOMALIES.length})
          </div>
          <div style={{ overflowY: "auto", flex: 1 }}>
            {DEMO_ANOMALIES.map(a => (
              <AnomalyListItem
                key={a.anomaly_id}
                anomaly={a}
                isSelected={selectedId === a.anomaly_id}
                isLoading={loadingIds.has(a.anomaly_id)}
                explanation={explanations[a.anomaly_id] ?? null}
                onClick={() => setSelectedId(a.anomaly_id)}
              />
            ))}
          </div>
        </div>

        {/* Right: Explanation panel */}
        <div className="xai-panel">
          {loading && !batchLoaded && (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "1rem", color: "var(--text-muted)" }}>
              <div style={{ width: 48, height: 48, borderRadius: "50%", border: "3px solid hsla(265,89%,60%,0.2)", borderTop: "3px solid #a855f7", animation: "spin 0.9s linear infinite" }} />
              <div style={{ fontSize: "0.85rem" }}>Running causal analysis…</div>
            </div>
          )}

          {batchLoaded && !selected && (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
              <Brain size={48} color="var(--border-card)" style={{ marginBottom: "1rem" }} />
              <div style={{ fontSize: "0.85rem" }}>Select an incident to view AI reasoning</div>
            </div>
          )}

          {selected && (
            <>
              {/* Explanation headline card */}
              <div className="xai-headline-card" style={{ borderColor: `${sColor}44` }}>
                {/* Top meta row */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.85rem", flexWrap: "wrap" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: sColor, fontWeight: 700 }}>
                    {selected.anomaly_id}
                  </span>
                  <span style={{ padding: "0.12rem 0.45rem", borderRadius: "8px", fontSize: "0.65rem", fontWeight: 700, background: `${sColor}20`, color: sColor, border: `1px solid ${sColor}44` }}>
                    {selected.severity}
                  </span>
                  <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                    <MapPin size={10} style={{ marginRight: "0.2rem", verticalAlign: "middle" }} />
                    {selected.district}
                  </span>
                  <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                    <Clock size={10} style={{ marginRight: "0.2rem", verticalAlign: "middle" }} />
                    {selected.timestamp.slice(11, 16)} UTC
                  </span>
                  <span style={{ marginLeft: "auto", fontSize: "0.65rem", color: qualColor, fontWeight: 600 }}>
                    {selected.explanation_quality} quality · {selected.explanation_latency_ms}ms
                  </span>
                </div>

                {/* Headline */}
                <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start", marginBottom: "0.85rem" }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.5rem 0", lineHeight: 1.5 }}>
                      {selected.headline}
                    </p>
                    <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.65 }}>
                      {selected.summary}
                    </p>
                  </div>
                  <ConfidenceRing value={selected.overall_confidence} size={64} label="Confidence" />
                </div>

                {/* Metric row */}
                <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                  {[
                    { label: "Anomaly Score", value: `${(selected.score * 100).toFixed(0)}%`, color: sColor },
                    { label: "Cascade Risk", value: selected.cascade_risk, color: cascadeColor },
                    { label: "Factors", value: String(selected.contributing_factors.length), color: "#a855f7" },
                    { label: "Systems at Risk", value: String(selected.impacted_systems.length), color: "#f97316" },
                  ].map(m => (
                    <div key={m.label} style={{ padding: "0.45rem 0.75rem", borderRadius: "8px", background: `${m.color}12`, border: `1px solid ${m.color}30`, textAlign: "center" }}>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "1rem", fontWeight: 800, color: m.color }}>{m.value}</div>
                      <div style={{ fontSize: "0.6rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{m.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Causal narrative */}
              <div className="xai-narrative">
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.6rem" }}>
                  <Brain size={14} color="#a855f7" />
                  <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#a855f7", textTransform: "uppercase", letterSpacing: "0.07em" }}>Causal Narrative</span>
                </div>
                <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.75, fontStyle: "italic" }}>
                  "{selected.causal_narrative}"
                </p>
              </div>

              {/* Tab bar */}
              <div className="xai-tabs">
                {[
                  { key: "factors",   icon: <BarChart2 size={13} />,  label: `Factors (${selected.contributing_factors.length})` },
                  { key: "reasoning", icon: <GitBranch size={13} />,  label: "Reasoning Chain" },
                  { key: "chain",     icon: <Link2 size={13} />,      label: "Correlation Map" },
                  { key: "actions",   icon: <CheckCircle size={13} />,label: `Actions (${selected.recommended_actions.length})` },
                ].map(t => (
                  <button
                    key={t.key}
                    onClick={() => setActiveTab(t.key as any)}
                    style={{
                      display: "flex", alignItems: "center", gap: "0.35rem",
                      padding: "0.45rem 0.85rem", borderRadius: "8px", fontSize: "0.72rem", fontWeight: 600,
                      border: `1px solid ${activeTab === t.key ? "#a855f7" : "var(--border-card)"}`,
                      background: activeTab === t.key ? "hsla(265,89%,60%,0.18)" : "transparent",
                      color: activeTab === t.key ? "#a855f7" : "var(--text-muted)", cursor: "pointer",
                    }}
                  >
                    {t.icon}{t.label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="xai-tab-content">
                {/* Contributing Factors */}
                {activeTab === "factors" && (
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.75rem", lineHeight: 1.5 }}>
                      {selected.contributing_factors.length} causal and amplifying factors identified. Weight indicates relative contribution to anomaly severity.
                    </div>
                    {selected.contributing_factors.map((f, i) => (
                      <FactorCard key={f.factor_id} factor={f} index={i} />
                    ))}
                  </div>
                )}

                {/* Reasoning Steps */}
                {activeTab === "reasoning" && (
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.85rem", lineHeight: 1.5 }}>
                      Chain-of-thought reasoning trace from raw signal to remediation recommendation.
                    </div>
                    {selected.reasoning_steps.map((step, i) => (
                      <ReasoningStepCard key={step.step_index} step={step} isLast={i === selected.reasoning_steps.length - 1} />
                    ))}
                  </div>
                )}

                {/* Correlation chain */}
                {activeTab === "chain" && (
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.6rem" }}>
                      Directed causal factor graph showing amplification and cascade propagation paths.
                    </div>
                    <CorrelationChainViz explanation={selected} />

                    {/* Impacted systems */}
                    <div style={{ marginTop: "1rem" }}>
                      <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "0.5rem" }}>
                        Cascade Exposure — {selected.cascade_risk} Risk
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                        {selected.impacted_systems.map((sys, i) => (
                          <span key={i} style={{ padding: "0.25rem 0.6rem", borderRadius: "8px", fontSize: "0.68rem", background: `${cascadeColor}15`, border: `1px solid ${cascadeColor}33`, color: cascadeColor, fontWeight: 600 }}>
                            {sys}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Cross-domain correlations */}
                    {selected.correlation_chain.length > 0 && (
                      <div style={{ marginTop: "1rem" }}>
                        <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "0.5rem" }}>
                          Factor Relationships
                        </div>
                        {selected.correlation_chain.map((link, i) => {
                          const REL_COLORS: Record<string, string> = { CAUSED: "#ef4444", AMPLIFIED: "#f97316", TRIGGERED: "#f97316", CORRELATED: "#a855f7", PRECEDED: "#818cf8" };
                          const rc = REL_COLORS[link.relationship] ?? "#9ca3af";
                          return (
                            <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.35rem 0.5rem", marginBottom: "0.3rem", borderRadius: "6px", background: "hsla(223,47%,10%,0.4)", border: "1px solid var(--border-card)", fontSize: "0.68rem" }}>
                              <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)", fontWeight: 700 }}>{link.from_factor}</span>
                              <span style={{ color: rc, fontWeight: 700, textTransform: "uppercase", fontSize: "0.58rem", padding: "0.08rem 0.35rem", borderRadius: "4px", background: `${rc}18` }}>{link.relationship}</span>
                              <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)", fontWeight: 700 }}>{link.to_factor}</span>
                              <span style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: "0.62rem" }}>
                                {link.lag_minutes !== 0 && `${link.lag_minutes > 0 ? "+" : ""}{link.lag_minutes}min lag · `}
                                strength: {(link.strength * 100).toFixed(0)}%
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* Actions */}
                {activeTab === "actions" && (
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
                      AI-recommended remediation actions, prioritized by impact and execution speed.
                    </div>
                    {selected.recommended_actions.map((action, i) => (
                      <div key={i} style={{
                        display: "flex", alignItems: "flex-start", gap: "0.75rem", padding: "0.75rem 0.85rem", borderRadius: 10,
                        background: i === 0 ? "hsla(145,80%,45%,0.08)" : "hsla(223,47%,10%,0.4)",
                        border: `1px solid ${i === 0 ? "hsla(145,80%,45%,0.3)" : "var(--border-card)"}`,
                        marginBottom: "0.5rem",
                      }}>
                        <div style={{ width: 24, height: 24, borderRadius: "50%", background: i === 0 ? "hsla(145,80%,45%,0.2)" : "hsla(217,32%,18%,0.5)", border: `1.5px solid ${i === 0 ? "#22c55e" : "var(--border-card)"}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: "0.65rem", fontWeight: 800, color: i === 0 ? "#22c55e" : "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                          {i + 1}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: "0.75rem", color: i === 0 ? "var(--text-primary)" : "var(--text-secondary)", fontWeight: i === 0 ? 700 : 400, lineHeight: 1.5 }}>
                            {action}
                          </div>
                          {i === 0 && (
                            <div style={{ fontSize: "0.62rem", color: "#22c55e", marginTop: "0.25rem", fontWeight: 600 }}>
                              ↑ Highest priority — execute immediately
                            </div>
                          )}
                        </div>
                      </div>
                    ))}

                    {/* Primary cause box */}
                    <div style={{ marginTop: "0.75rem", padding: "0.65rem 0.85rem", borderRadius: 10, background: "hsla(35,100%,50%,0.08)", border: "1px solid hsla(35,100%,50%,0.25)" }}>
                      <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "#eab308", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "0.3rem" }}>
                        Root Cause Attribution
                      </div>
                      <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                        {selected.primary_cause}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default ExplainableAI;
