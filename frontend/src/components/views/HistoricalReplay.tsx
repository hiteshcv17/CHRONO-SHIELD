import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Play, Pause, SkipBack, SkipForward, Rewind, FastForward,
  AlertCircle, GitCompare, Clock, Filter, RefreshCw,
  Zap, Car, Droplets, Wifi, Building2, Activity,
  ChevronDown, ChevronRight, GitMerge, Shield, XCircle, CheckCircle,
  Info, BarChart2, ArrowLeft, ArrowRight, History,
} from "lucide-react";
import {
  fetchReplayTimeline,
  fetchIncidentComparison,
  ReplayTimelineResponse,
  IncidentRecord,
  TimelineBucket,
  IncidentComparisonResponse,
} from "../../api/replay";

// ==============================================================================
// Constants
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
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  POWER:                 <Zap size={11} />,
  TRAFFIC:               <Car size={11} />,
  WATER:                 <Droplets size={11} />,
  INTERNET:              <Wifi size={11} />,
  PUBLIC_INFRASTRUCTURE: <Building2 size={11} />,
};

const ALERT_LEVEL_COLORS: Record<string, string> = {
  NOMINAL:  "#22c55e",
  ELEVATED: "#eab308",
  HIGH:     "#f97316",
  CRISIS:   "#ef4444",
};

const SPEED_OPTIONS = [0.5, 1, 2, 4];

// ==============================================================================
// Helpers
// ==============================================================================
function computeSystemHealth(incidents: IncidentRecord[], upToBucket: number): number {
  const WEIGHT: Record<string, number> = { CRITICAL: 1.0, WARNING: 0.6, INFO: 0.25 };
  const cumulative = incidents.filter(i => i.bucket_index <= upToBucket);
  const penalty = cumulative.reduce((acc, i) => acc + WEIGHT[i.severity] * i.score * 2.5, 0);
  return Math.max(5, Math.min(100, 92 - penalty));
}

function alertLevel(health: number): "NOMINAL" | "ELEVATED" | "HIGH" | "CRISIS" {
  if (health >= 75) return "NOMINAL";
  if (health >= 55) return "ELEVATED";
  if (health >= 35) return "HIGH";
  return "CRISIS";
}

// ==============================================================================
// Sub-components
// ==============================================================================

/** Severity pill badge */
const SeverityBadge: React.FC<{ severity: string; small?: boolean }> = ({ severity, small }) => {
  const color = SEVERITY_COLORS[severity] ?? "#00b8ff";
  return (
    <span style={{
      padding: small ? "0.1rem 0.35rem" : "0.15rem 0.5rem",
      borderRadius: "10px",
      fontSize: small ? "0.6rem" : "0.68rem",
      fontWeight: 700,
      letterSpacing: "0.06em",
      background: `${color}22`,
      color,
      border: `1px solid ${color}44`,
      textTransform: "uppercase",
      flexShrink: 0,
    }}>
      {severity}
    </span>
  );
};

/** Category pill */
const CategoryBadge: React.FC<{ category: string }> = ({ category }) => {
  const color = CATEGORY_COLORS[category] ?? "#00e5ff";
  const short = category === "PUBLIC_INFRASTRUCTURE" ? "INFRA" : category;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: "0.25rem",
      padding: "0.1rem 0.4rem", borderRadius: "8px",
      fontSize: "0.62rem", fontWeight: 700,
      background: `${color}18`, color, border: `1px solid ${color}33`,
    }}>
      {CATEGORY_ICONS[category]}
      {short}
    </span>
  );
};

/** Mini health gauge arc (SVG) */
const HealthGauge: React.FC<{ value: number; size?: number }> = ({ value, size = 64 }) => {
  const r = (size - 8) / 2;
  const circ = Math.PI * r;
  const pct = value / 100;
  const dash = pct * circ;
  const color = value >= 75 ? "#22c55e" : value >= 55 ? "#eab308" : value >= 35 ? "#f97316" : "#ef4444";
  return (
    <svg width={size} height={size / 2 + 4} viewBox={`0 0 ${size} ${size / 2 + 4}`}>
      <path
        d={`M 4 ${size / 2 + 4} A ${r} ${r} 0 0 1 ${size - 4} ${size / 2 + 4}`}
        fill="none" stroke="hsla(217,32%,18%,0.6)" strokeWidth={6} strokeLinecap="round"
      />
      <path
        d={`M 4 ${size / 2 + 4} A ${r} ${r} 0 0 1 ${size - 4} ${size / 2 + 4}`}
        fill="none" stroke={color} strokeWidth={6} strokeLinecap="round"
        strokeDasharray={`${dash} ${circ}`}
        style={{ transition: "stroke-dasharray 0.5s ease" }}
      />
      <text x={size / 2} y={size / 2 + 2} textAnchor="middle" fill={color}
        fontSize={size * 0.22} fontWeight={700} fontFamily="monospace">
        {value.toFixed(0)}
      </text>
    </svg>
  );
};

/** Incident detail card */
const IncidentCard: React.FC<{
  incident: IncidentRecord;
  isSelected?: boolean;
  isCompareA?: boolean;
  isCompareB?: boolean;
  onClick?: () => void;
  onSelectA?: () => void;
  onSelectB?: () => void;
  dimmed?: boolean;
}> = ({ incident, isSelected, isCompareA, isCompareB, onClick, onSelectA, onSelectB, dimmed }) => {
  const color = SEVERITY_COLORS[incident.severity] ?? "#00b8ff";
  const [expanded, setExpanded] = useState(false);

  const borderColor = isCompareA ? "#a855f7"
    : isCompareB ? "#f97316"
    : isSelected ? "var(--accent-cyan)"
    : "var(--border-card)";

  return (
    <div
      style={{
        borderRadius: 10,
        border: `1px solid ${borderColor}`,
        background: isSelected
          ? "hsla(223,47%,13%,0.85)"
          : "hsla(223,47%,10%,0.55)",
        marginBottom: "0.5rem",
        transition: "all 0.2s",
        opacity: dimmed ? 0.45 : 1,
        cursor: "pointer",
      }}
    >
      {/* Header row */}
      <div
        style={{ padding: "0.7rem 0.85rem", display: "flex", alignItems: "center", gap: "0.5rem" }}
        onClick={() => { onClick?.(); setExpanded(e => !e); }}
      >
        <div style={{ width: 7, height: 7, borderRadius: "50%", background: color, flexShrink: 0 }} />
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: "var(--text-muted)", flexShrink: 0 }}>
          {incident.id}
        </span>
        <SeverityBadge severity={incident.severity} small />
        <CategoryBadge category={incident.category} />
        <span style={{ flex: 1, fontSize: "0.72rem", color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {incident.metric_name.replace(/_/g, " ")}
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color, fontWeight: 700, flexShrink: 0 }}>
          {(incident.score * 100).toFixed(0)}%
        </span>
        <ChevronDown size={12} color="var(--text-muted)" style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.2s", flexShrink: 0 }} />
      </div>

      {/* Expanded body */}
      {expanded && (
        <div style={{ padding: "0 0.85rem 0.75rem", borderTop: "1px solid hsla(217,32%,18%,0.5)" }}>
          <p style={{ fontSize: "0.73rem", color: "var(--text-secondary)", margin: "0.5rem 0 0.4rem 0", lineHeight: 1.5 }}>
            {incident.description}
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.25rem 0.75rem", fontSize: "0.68rem", marginBottom: "0.5rem" }}>
            <span style={{ color: "var(--text-muted)" }}>📍 {incident.district}</span>
            <span style={{ color: "var(--text-muted)" }}>⏱ {new Date(incident.timestamp).toLocaleTimeString()}</span>
            {incident.duration_minutes > 0 && <span style={{ color: "var(--text-muted)" }}>⌛ {incident.duration_minutes}min duration</span>}
            {incident.cascaded && <span style={{ color: "#f97316" }}>⚡ Cascade trigger</span>}
          </div>
          {incident.root_cause_hint && (
            <div style={{ fontSize: "0.68rem", color: "#eab308", marginBottom: "0.25rem" }}>
              <strong>Root cause:</strong> {incident.root_cause_hint}
            </div>
          )}
          {incident.resolution_hint && (
            <div style={{ fontSize: "0.68rem", color: "#22c55e" }}>
              <strong>Resolution:</strong> {incident.resolution_hint}
            </div>
          )}
          {incident.related_ids.length > 0 && (
            <div style={{ marginTop: "0.4rem", display: "flex", gap: "0.3rem", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>Related:</span>
              {incident.related_ids.map(id => (
                <span key={id} style={{ fontSize: "0.65rem", fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", background: "hsla(180,100%,45%,0.1)", padding: "0.05rem 0.3rem", borderRadius: "4px" }}>
                  {id}
                </span>
              ))}
            </div>
          )}
          {/* Compare actions */}
          <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.5rem" }}>
            <button
              onClick={e => { e.stopPropagation(); onSelectA?.(); }}
              style={{
                padding: "0.2rem 0.55rem", borderRadius: "6px", fontSize: "0.62rem", fontWeight: 700,
                border: `1px solid ${isCompareA ? "#a855f7" : "hsla(265,89%,60%,0.3)"}`,
                background: isCompareA ? "hsla(265,89%,60%,0.2)" : "transparent",
                color: "#a855f7", cursor: "pointer",
              }}
            >
              {isCompareA ? "✓ Slot A" : "Set Slot A"}
            </button>
            <button
              onClick={e => { e.stopPropagation(); onSelectB?.(); }}
              style={{
                padding: "0.2rem 0.55rem", borderRadius: "6px", fontSize: "0.62rem", fontWeight: 700,
                border: `1px solid ${isCompareB ? "#f97316" : "hsla(30,100%,50%,0.3)"}`,
                background: isCompareB ? "hsla(30,100%,50%,0.15)" : "transparent",
                color: "#f97316", cursor: "pointer",
              }}
            >
              {isCompareB ? "✓ Slot B" : "Set Slot B"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ==============================================================================
// Timeline Scrubber Component
// ==============================================================================
const TimelineScrubber: React.FC<{
  buckets: TimelineBucket[];
  currentIndex: number;
  onSeek: (index: number) => void;
  incidents: IncidentRecord[];
}> = ({ buckets, currentIndex, onSeek, incidents }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const maxCount = Math.max(...buckets.map(b => b.anomaly_count), 1);

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, x / rect.width));
    const idx = Math.floor(pct * buckets.length);
    onSeek(Math.min(idx, buckets.length - 1));
  };

  // Build health trajectory for sparkline
  const healthLine = buckets.map((_, i) => computeSystemHealth(incidents, i));
  const minH = Math.min(...healthLine);
  const maxH = Math.max(...healthLine);

  return (
    <div className="replay-scrubber-wrapper">
      {/* Health sparkline behind the bars */}
      <svg
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 1 }}
        preserveAspectRatio="none"
        viewBox={`0 0 ${buckets.length} 100`}
      >
        <polyline
          points={healthLine.map((h, i) => `${i + 0.5},${100 - ((h - minH) / (maxH - minH + 1)) * 80}`).join(" ")}
          fill="none"
          stroke="hsla(180,100%,45%,0.35)"
          strokeWidth={0.8}
          strokeLinejoin="round"
        />
      </svg>

      {/* Bucket bars */}
      <div
        ref={containerRef}
        className="replay-scrubber-bars"
        onClick={handleClick}
      >
        {buckets.map((bucket, i) => {
          const heightPct = bucket.anomaly_count / maxCount;
          const isCurrent = i === currentIndex;
          const critColor = bucket.critical_count > 0 ? "var(--status-critical)" : bucket.anomaly_count > 0 ? "var(--status-warning)" : "var(--border-card)";

          return (
            <div
              key={i}
              className={`scrubber-bar ${isCurrent ? "active" : ""}`}
              style={{ "--bar-height": `${Math.max(4, heightPct * 100)}%`, "--bar-color": critColor } as React.CSSProperties}
              title={`${bucket.label}\n${bucket.anomaly_count} events`}
            />
          );
        })}

        {/* Playhead cursor */}
        <div
          className="scrubber-playhead"
          style={{ left: `${(currentIndex / Math.max(buckets.length - 1, 1)) * 100}%` }}
        />
      </div>

      {/* Time labels */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.3rem", fontSize: "0.62rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
        {[0, 6, 12, 18, 24].map(h => (
          <span key={h}>{String(h).padStart(2, "0")}:00</span>
        ))}
      </div>
    </div>
  );
};

// ==============================================================================
// Comparison Panel
// ==============================================================================
const ComparisonPanel: React.FC<{
  comparison: IncidentComparisonResponse | null;
  loading: boolean;
  incA: IncidentRecord | null;
  incB: IncidentRecord | null;
  onClear: () => void;
}> = ({ comparison, loading, incA, incB, onClear }) => {
  if (!incA && !incB) return null;

  const riskColor: Record<string, string> = { EXTREME: "#ef4444", HIGH: "#f97316", MODERATE: "#eab308" };

  const CompColumn: React.FC<{ inc: IncidentRecord | null; slot: "A" | "B" }> = ({ inc, slot }) => {
    const slotColor = slot === "A" ? "#a855f7" : "#f97316";
    if (!inc) return (
      <div style={{ flex: 1, textAlign: "center", color: "var(--text-muted)", fontSize: "0.8rem", paddingTop: "2rem" }}>
        Select an incident for Slot {slot}
      </div>
    );
    const color = SEVERITY_COLORS[inc.severity];
    return (
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem", paddingBottom: "0.5rem", borderBottom: `1px solid ${slotColor}44` }}>
          <span style={{ padding: "0.15rem 0.55rem", borderRadius: "8px", fontSize: "0.68rem", fontWeight: 800, background: `${slotColor}22`, color: slotColor, border: `1px solid ${slotColor}55` }}>
            SLOT {slot}
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-primary)", fontWeight: 700 }}>{inc.id}</span>
        </div>

        {/* Score arc */}
        <div style={{ textAlign: "center", marginBottom: "0.75rem" }}>
          <div style={{ fontSize: "1.8rem", fontWeight: 900, color, fontFamily: "var(--font-mono)" }}>
            {(inc.score * 100).toFixed(0)}%
          </div>
          <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Anomaly Score</div>
          <div style={{ height: "4px", background: "hsla(217,32%,18%,0.6)", borderRadius: "4px", overflow: "hidden", marginTop: "0.4rem" }}>
            <div style={{ height: "100%", width: `${inc.score * 100}%`, background: `linear-gradient(90deg, ${color}88, ${color})`, borderRadius: "4px", transition: "width 0.5s" }} />
          </div>
        </div>

        <div style={{ display: "grid", gap: "0.4rem", fontSize: "0.72rem" }}>
          {[
            ["Severity", <SeverityBadge severity={inc.severity} small />],
            ["Category", <CategoryBadge category={inc.category} />],
            ["District", inc.district],
            ["Time", new Date(inc.timestamp).toLocaleTimeString()],
            ["Duration", inc.duration_minutes > 0 ? `${inc.duration_minutes} min` : "Instantaneous"],
            ["Cascaded", inc.cascaded ? <span style={{ color: "#f97316" }}>⚡ Yes</span> : <span style={{ color: "#22c55e" }}>No</span>],
          ].map(([label, value], idx) => (
            <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.25rem 0", borderBottom: "1px solid hsla(217,32%,18%,0.3)" }}>
              <span style={{ color: "var(--text-muted)" }}>{label}</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{value as React.ReactNode}</span>
            </div>
          ))}
        </div>

        {inc.root_cause_hint && (
          <div style={{ marginTop: "0.75rem", padding: "0.5rem 0.65rem", borderRadius: "8px", background: "hsla(35,100%,50%,0.08)", border: "1px solid hsla(35,100%,50%,0.2)", fontSize: "0.68rem", color: "#eab308" }}>
            <div style={{ fontWeight: 700, marginBottom: "0.2rem" }}>Root Cause</div>
            {inc.root_cause_hint}
          </div>
        )}
        {inc.resolution_hint && (
          <div style={{ marginTop: "0.4rem", padding: "0.5rem 0.65rem", borderRadius: "8px", background: "hsla(145,80%,45%,0.08)", border: "1px solid hsla(145,80%,45%,0.2)", fontSize: "0.68rem", color: "#22c55e" }}>
            <div style={{ fontWeight: 700, marginBottom: "0.2rem" }}>Resolution</div>
            {inc.resolution_hint}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="replay-compare-panel">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <GitCompare size={16} color="var(--accent-cyan)" />
          <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>Incident Comparison</span>
        </div>
        <button onClick={onClear} style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--text-muted)" }}>
          <XCircle size={15} />
        </button>
      </div>

      <div style={{ display: "flex", gap: "1rem" }}>
        <CompColumn inc={incA} slot="A" />
        {/* Center divider with stats */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem", minWidth: 80, paddingTop: "2.5rem" }}>
          <div style={{ width: "1px", flex: 1, background: "var(--border-card)" }} />
          {comparison && !loading && (
            <div style={{ textAlign: "center", fontSize: "0.65rem", color: "var(--text-muted)" }}>
              <div style={{
                padding: "0.3rem 0.45rem", borderRadius: "8px", marginBottom: "0.4rem",
                background: `${riskColor[comparison.combined_risk] ?? "#eab308"}18`,
                border: `1px solid ${riskColor[comparison.combined_risk] ?? "#eab308"}44`,
                color: riskColor[comparison.combined_risk] ?? "#eab308",
                fontSize: "0.6rem", fontWeight: 700,
              }}>
                {comparison.combined_risk} RISK
              </div>
              <div style={{ marginBottom: "0.3rem" }}>
                <span style={{ display: "block", fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                  {(comparison.similarity_score * 100).toFixed(0)}%
                </span>
                similarity
              </div>
              <div style={{ marginBottom: "0.3rem" }}>
                <span style={{ display: "block", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                  {comparison.time_delta_minutes}m
                </span>
                apart
              </div>
              {comparison.likely_correlated && (
                <div style={{ color: "#f97316", fontWeight: 700, fontSize: "0.58rem" }}>
                  ⚡ CORRELATED
                </div>
              )}
            </div>
          )}
          {loading && (
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", animation: "pulse 1.2s infinite" }}>
              Analyzing...
            </div>
          )}
          <div style={{ width: "1px", flex: 1, background: "var(--border-card)" }} />
        </div>
        <CompColumn inc={incB} slot="B" />
      </div>

      {comparison && !loading && (
        <div style={{ marginTop: "0.75rem", padding: "0.5rem 0.7rem", borderRadius: "8px", background: "hsla(223,47%,11%,0.65)", border: "1px solid var(--border-card)", fontSize: "0.7rem" }}>
          <div style={{ color: "var(--text-muted)", marginBottom: "0.3rem" }}>Forensic Assessment</div>
          <div style={{ color: "var(--text-secondary)" }}>{comparison.severity_diff}</div>
          {comparison.shared_categories.length > 0 && (
            <div style={{ color: "var(--text-secondary)", marginTop: "0.2rem" }}>
              Shared infrastructure domain: <strong style={{ color: CATEGORY_COLORS[comparison.shared_categories[0]] }}>{comparison.shared_categories[0].replace("_", " ")}</strong>
            </div>
          )}
          {comparison.shared_districts.length > 0 && (
            <div style={{ color: "var(--text-secondary)", marginTop: "0.2rem" }}>
              Same zone: <strong style={{ color: "var(--accent-cyan)" }}>{comparison.shared_districts[0]}</strong>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ==============================================================================
// Main HistoricalReplay View
// ==============================================================================
export const HistoricalReplay: React.FC = () => {
  const [timeline, setTimeline] = useState<ReplayTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState(24);

  // Playback state
  const [currentBucket, setCurrentBucket] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(1);
  const playRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");

  // Comparison
  const [compareIdA, setCompareIdA] = useState<string | null>(null);
  const [compareIdB, setCompareIdB] = useState<string | null>(null);
  const [comparison, setComparison] = useState<IncidentComparisonResponse | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  // Selected incident
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // View mode
  const [view, setView] = useState<"replay" | "compare">("replay");

  // ── Data loading ────────────────────────────────────────────────────────────
  const loadTimeline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReplayTimeline(timeRange);
      setTimeline(data);
      setCurrentBucket(0);
    } catch (err: any) {
      setError(err?.message ?? "Failed to load timeline");
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => { loadTimeline(); }, [loadTimeline]);

  // ── Playback engine ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (playRef.current) clearInterval(playRef.current);
    if (!isPlaying || !timeline) return;

    const intervalMs = 800 / playSpeed;
    playRef.current = setInterval(() => {
      setCurrentBucket(prev => {
        const next = prev + 1;
        if (next >= timeline.buckets.length) {
          setIsPlaying(false);
          return prev;
        }
        return next;
      });
    }, intervalMs);

    return () => { if (playRef.current) clearInterval(playRef.current); };
  }, [isPlaying, playSpeed, timeline]);

  // ── Incident comparison ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!compareIdA || !compareIdB) { setComparison(null); return; }
    setCompareLoading(true);
    fetchIncidentComparison(compareIdA, compareIdB, timeRange)
      .then(setComparison)
      .catch(() => setComparison(null))
      .finally(() => setCompareLoading(false));
  }, [compareIdA, compareIdB, timeRange]);

  // ── Derived state ────────────────────────────────────────────────────────────
  const currentBucketData = timeline?.buckets[currentBucket];
  const systemHealth = timeline
    ? computeSystemHealth(timeline.incidents, currentBucket)
    : 92;
  const level = alertLevel(systemHealth);
  const levelColor = ALERT_LEVEL_COLORS[level];

  const activeIncidents = timeline?.incidents.filter(i => i.bucket_index === currentBucket) ?? [];
  const filteredActive = activeIncidents.filter(i => {
    if (severityFilter !== "ALL" && i.severity !== severityFilter) return false;
    if (categoryFilter !== "ALL" && i.category !== categoryFilter) return false;
    return true;
  });

  const compareIncA = compareIdA ? timeline?.incidents.find(i => i.id === compareIdA) ?? null : null;
  const compareIncB = compareIdB ? timeline?.incidents.find(i => i.id === compareIdB) ?? null : null;

  const totalEventsToNow = timeline?.incidents.filter(i => i.bucket_index <= currentBucket).length ?? 0;
  const critToNow = timeline?.incidents.filter(i => i.bucket_index <= currentBucket && i.severity === "CRITICAL").length ?? 0;

  // ==============================================================================
  // Render
  // ==============================================================================
  return (
    <div className="replay-root">
      {/* ── Page Header ────────────────────────────────────────────────────── */}
      <div className="replay-header">
        <div>
          <h2 style={{ fontSize: "1.3rem", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
            <History size={20} color="var(--accent-purple)" />
            Historical Replay
          </h2>
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
            Forensic incident timeline analysis &amp; event replay engine
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {/* Time range selector */}
          <div style={{ display: "flex", gap: "0.3rem" }}>
            {[12, 24, 48].map(h => (
              <button
                key={h}
                onClick={() => setTimeRange(h)}
                style={{
                  padding: "0.3rem 0.65rem", borderRadius: "8px", fontSize: "0.73rem", fontWeight: 600,
                  border: `1px solid ${timeRange === h ? "var(--accent-purple)" : "var(--border-card)"}`,
                  background: timeRange === h ? "hsla(265,89%,60%,0.15)" : "transparent",
                  color: timeRange === h ? "#a855f7" : "var(--text-muted)", cursor: "pointer",
                }}
              >
                {h}h
              </button>
            ))}
          </div>

          {/* View toggle */}
          <div style={{ display: "flex", background: "hsla(217,32%,12%,0.8)", borderRadius: "10px", padding: "0.2rem", border: "1px solid var(--border-card)" }}>
            {[
              { key: "replay", icon: <Play size={12} />, label: "Replay" },
              { key: "compare", icon: <GitCompare size={12} />, label: "Compare" },
            ].map(({ key, icon, label }) => (
              <button
                key={key}
                onClick={() => setView(key as "replay" | "compare")}
                style={{
                  display: "flex", alignItems: "center", gap: "0.3rem",
                  padding: "0.3rem 0.7rem", borderRadius: "8px", fontSize: "0.72rem", fontWeight: 600,
                  border: "none",
                  background: view === key ? "hsla(265,89%,60%,0.25)" : "transparent",
                  color: view === key ? "#a855f7" : "var(--text-muted)", cursor: "pointer",
                }}
              >
                {icon} {label}
              </button>
            ))}
          </div>

          <button
            onClick={loadTimeline}
            disabled={loading}
            style={{ display: "flex", alignItems: "center", gap: "0.4rem", padding: "0.4rem 0.85rem", borderRadius: "8px", fontSize: "0.78rem", fontWeight: 600, border: "1px solid var(--border-card)", background: "hsla(217,32%,18%,0.5)", color: "var(--text-secondary)", cursor: "pointer", opacity: loading ? 0.6 : 1 }}
          >
            <RefreshCw size={13} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            {loading ? "Loading..." : "Reload"}
          </button>
        </div>
      </div>

      {/* ── Error Banner ─────────────────────────────────────────────────────── */}
      {error && (
        <div style={{ padding: "0.75rem 1rem", borderRadius: "10px", background: "hsla(346,100%,50%,0.1)", border: "1px solid hsla(346,100%,50%,0.3)", color: "var(--status-critical)", fontSize: "0.82rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* ── Top Status Bar ────────────────────────────────────────────────────── */}
      {timeline && (
        <div className="replay-status-bar">
          <div className="replay-status-item">
            <HealthGauge value={Math.round(systemHealth)} size={56} />
            <div>
              <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.15rem" }}>System Health</div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: levelColor }}>{level}</div>
            </div>
          </div>

          <div style={{ width: "1px", background: "var(--border-card)", alignSelf: "stretch" }} />

          <div className="replay-stat-block">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)" }}>{totalEventsToNow}</div>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Events Elapsed</div>
          </div>

          <div className="replay-stat-block">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 800, color: critToNow > 0 ? "var(--status-critical)" : "var(--status-safe)" }}>{critToNow}</div>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Critical</div>
          </div>

          <div className="replay-stat-block">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
              {currentBucketData ? new Date(currentBucketData.timestamp_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "--:--"}
            </div>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Current Time</div>
          </div>

          <div className="replay-stat-block">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1rem", fontWeight: 700, color: "var(--accent-purple)" }}>
              {currentBucket + 1} / {timeline.buckets.length}
            </div>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Bucket</div>
          </div>

          <div className="replay-stat-block">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1rem", fontWeight: 700, color: "var(--accent-cyan)" }}>
              {activeIncidents.length}
            </div>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>In Window</div>
          </div>
        </div>
      )}

      {/* ── Timeline Scrubber + Playback Controls ────────────────────────────── */}
      {timeline && (
        <div className="replay-controls-wrapper">
          {/* Scrubber */}
          <TimelineScrubber
            buckets={timeline.buckets}
            currentIndex={currentBucket}
            onSeek={i => { setCurrentBucket(i); setIsPlaying(false); }}
            incidents={timeline.incidents}
          />

          {/* Controls row */}
          <div className="replay-controls-row">
            {/* Transport */}
            <div className="replay-transport">
              <button className="transport-btn" onClick={() => { setCurrentBucket(0); setIsPlaying(false); }} title="Rewind to start">
                <Rewind size={15} />
              </button>
              <button className="transport-btn" onClick={() => setCurrentBucket(i => Math.max(0, i - 1))} title="Step back">
                <SkipBack size={15} />
              </button>
              <button
                className="transport-btn play-btn"
                onClick={() => setIsPlaying(p => !p)}
                title={isPlaying ? "Pause" : "Play"}
              >
                {isPlaying ? <Pause size={18} /> : <Play size={18} />}
              </button>
              <button className="transport-btn" onClick={() => setCurrentBucket(i => Math.min((timeline?.buckets.length ?? 1) - 1, i + 1))} title="Step forward">
                <SkipForward size={15} />
              </button>
              <button className="transport-btn" onClick={() => { setCurrentBucket((timeline?.buckets.length ?? 1) - 1); setIsPlaying(false); }} title="Jump to end">
                <FastForward size={15} />
              </button>
            </div>

            {/* Speed control */}
            <div className="replay-speed-controls">
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>Speed:</span>
              {SPEED_OPTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => setPlaySpeed(s)}
                  style={{
                    padding: "0.2rem 0.5rem", borderRadius: "6px", fontSize: "0.68rem", fontWeight: 700,
                    border: `1px solid ${playSpeed === s ? "var(--accent-purple)" : "var(--border-card)"}`,
                    background: playSpeed === s ? "hsla(265,89%,60%,0.18)" : "transparent",
                    color: playSpeed === s ? "#a855f7" : "var(--text-muted)", cursor: "pointer",
                  }}
                >
                  {s}×
                </button>
              ))}
            </div>

            {/* Current bucket label */}
            <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
              {currentBucketData?.label ?? ""}
            </div>
          </div>
        </div>
      )}

      {/* ── Main Body ─────────────────────────────────────────────────────────── */}
      {timeline && view === "replay" && (
        <div className="replay-body">
          {/* Left — Incident List */}
          <div className="replay-incident-list">
            {/* Filter bar */}
            <div style={{ display: "flex", gap: "0.4rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", alignSelf: "center" }}>
                <Filter size={10} style={{ marginRight: "0.25rem" }} />
                Filter:
              </span>
              {["ALL", "CRITICAL", "WARNING", "INFO"].map(s => (
                <button
                  key={s}
                  onClick={() => setSeverityFilter(s)}
                  style={{
                    padding: "0.15rem 0.5rem", borderRadius: "12px", fontSize: "0.62rem", fontWeight: 700,
                    border: `1px solid ${severityFilter === s ? SEVERITY_COLORS[s] ?? "var(--accent-cyan)" : "var(--border-card)"}`,
                    background: severityFilter === s ? `${SEVERITY_COLORS[s] ?? "var(--accent-cyan)"}22` : "transparent",
                    color: severityFilter === s ? SEVERITY_COLORS[s] ?? "var(--accent-cyan)" : "var(--text-muted)",
                    cursor: "pointer",
                  }}
                >
                  {s}
                </button>
              ))}
            </div>

            {/* Active count */}
            <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
              {filteredActive.length === 0
                ? "No events in this time window"
                : `${filteredActive.length} event${filteredActive.length !== 1 ? "s" : ""} in current window`}
              {filteredActive.length !== activeIncidents.length && ` (${activeIncidents.length} total before filter)`}
            </div>

            {/* Incident cards */}
            <div style={{ overflowY: "auto", flex: 1 }}>
              {filteredActive.length === 0 ? (
                <div style={{ textAlign: "center", padding: "2rem 1rem", color: "var(--text-muted)", fontSize: "0.82rem" }}>
                  <Shield size={32} color="var(--border-card)" style={{ marginBottom: "0.5rem" }} />
                  <div>No incidents in this 30-minute window.</div>
                </div>
              ) : (
                filteredActive.map(inc => (
                  <IncidentCard
                    key={inc.id}
                    incident={inc}
                    isSelected={selectedId === inc.id}
                    isCompareA={compareIdA === inc.id}
                    isCompareB={compareIdB === inc.id}
                    onClick={() => setSelectedId(id => id === inc.id ? null : inc.id)}
                    onSelectA={() => setCompareIdA(id => id === inc.id ? null : inc.id)}
                    onSelectB={() => setCompareIdB(id => id === inc.id ? null : inc.id)}
                  />
                ))
              )}
            </div>
          </div>

          {/* Right — Full timeline event log */}
          <div className="replay-timeline-log">
            <div style={{ fontWeight: 700, fontSize: "0.85rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <BarChart2 size={15} color="var(--accent-purple)" />
              Full Timeline Log
              <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontWeight: 400, marginLeft: "auto" }}>
                {timeline.total_incidents} total events · {timeline.total_critical} critical
              </span>
            </div>

            <div style={{ overflowY: "auto", flex: 1 }}>
              {timeline.incidents.map((inc, idx) => {
                const isCurrent = inc.bucket_index === currentBucket;
                const isPast = inc.bucket_index < currentBucket;
                const isFuture = inc.bucket_index > currentBucket;
                const color = SEVERITY_COLORS[inc.severity];
                return (
                  <div
                    key={inc.id}
                    onClick={() => {
                      setCurrentBucket(inc.bucket_index);
                      setIsPlaying(false);
                      setSelectedId(inc.id);
                    }}
                    style={{
                      display: "flex", alignItems: "center", gap: "0.5rem",
                      padding: "0.35rem 0.6rem", borderRadius: "6px", cursor: "pointer",
                      marginBottom: "0.15rem",
                      background: isCurrent ? "hsla(265,89%,60%,0.12)" : "transparent",
                      border: isCurrent ? "1px solid hsla(265,89%,60%,0.3)" : "1px solid transparent",
                      opacity: isFuture ? 0.4 : 1,
                      transition: "all 0.15s",
                    }}
                  >
                    {/* Timeline dot */}
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: isPast ? "var(--text-muted)" : color, flexShrink: 0 }} />
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", color: "var(--text-muted)", width: 50, flexShrink: 0 }}>
                      {new Date(inc.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: isCurrent ? "#a855f7" : "var(--text-muted)", width: 50, flexShrink: 0 }}>
                      {inc.id}
                    </span>
                    <SeverityBadge severity={inc.severity} small />
                    <span style={{ fontSize: "0.68rem", color: isCurrent ? "var(--text-primary)" : "var(--text-secondary)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {inc.metric_name.replace(/_/g, " ")}
                    </span>
                    {inc.cascaded && <span title="Cascade trigger" style={{ color: "#f97316", fontSize: "0.6rem" }}>⚡</span>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Compare View ─────────────────────────────────────────────────────── */}
      {timeline && view === "compare" && (
        <div className="replay-body">
          {/* Left — pick incidents */}
          <div className="replay-incident-list">
            <div style={{ fontWeight: 700, fontSize: "0.85rem", marginBottom: "0.6rem" }}>
              Select incidents to compare:
            </div>
            <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
              Expand an incident card and click Set Slot A / B to compare.
            </div>
            <div style={{ overflowY: "auto", flex: 1 }}>
              {timeline.incidents.map(inc => (
                <IncidentCard
                  key={inc.id}
                  incident={inc}
                  isCompareA={compareIdA === inc.id}
                  isCompareB={compareIdB === inc.id}
                  onSelectA={() => setCompareIdA(id => id === inc.id ? null : inc.id)}
                  onSelectB={() => setCompareIdB(id => id === inc.id ? null : inc.id)}
                />
              ))}
            </div>
          </div>

          {/* Right — comparison result */}
          <div className="replay-timeline-log">
            <ComparisonPanel
              comparison={comparison}
              loading={compareLoading}
              incA={compareIncA}
              incB={compareIncB}
              onClear={() => { setCompareIdA(null); setCompareIdB(null); setComparison(null); }}
            />
            {!compareIdA && !compareIdB && (
              <div style={{ textAlign: "center", padding: "4rem 2rem", color: "var(--text-muted)" }}>
                <GitCompare size={40} color="var(--border-card)" style={{ marginBottom: "1rem" }} />
                <div style={{ fontSize: "0.85rem", marginBottom: "0.5rem" }}>No incidents selected</div>
                <div style={{ fontSize: "0.72rem" }}>Set Slot A and Slot B from the incident list on the left to begin forensic comparison.</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading overlay */}
      {loading && (
        <div style={{ position: "fixed", inset: 0, zIndex: 2000, background: "hsla(224,71%,4%,0.7)", backdropFilter: "blur(6px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "1rem" }}>
          <div style={{ width: 44, height: 44, borderRadius: "50%", border: "3px solid hsla(265,89%,60%,0.2)", borderTop: "3px solid #a855f7", animation: "spin 0.9s linear infinite" }} />
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Reconstructing incident timeline…</div>
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.5;} }
      `}</style>
    </div>
  );
};

export default HistoricalReplay;
