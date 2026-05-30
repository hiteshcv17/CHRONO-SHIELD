import React, { useState, useEffect, useRef, useMemo } from "react";
import { 
  Server, 
  Database, 
  ShieldAlert, 
  CheckCircle, 
  RefreshCw, 
  Activity, 
  Heart, 
  AlertTriangle, 
  TrendingDown, 
  ArrowDown, 
  HelpCircle, 
  Info,
  Sliders,
  Sparkles
} from "lucide-react";
import Plot from "react-plotly.js";
import SkeletonLoader from "../common/SkeletonLoader";
import { 
  getInfrastructureHealth, 
  getCityInfrastructureHealth,
  NodeHealthReport, 
  ComponentHealthReport 
} from "../../api/health";

export const InfrastructureHealth: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<"sectors" | "cluster">("sectors");

  // State for Cluster Node Diagnostics (Tab 2)
  const [overallHealth, setOverallHealth] = useState<number>(100);
  const [activeRisksCount, setActiveRisksCount] = useState<number>(0);
  const [reports, setReports] = useState<NodeHealthReport[]>([]);

  // State for City Infrastructure Sectors (Tab 1)
  const [cityReports, setCityReports] = useState<ComponentHealthReport[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>("POWER");

  interface MetricPoint {
    time: Date;
    cpu: number;
    memory: number;
    network: number;
  }

  const generateInitialMetrics = (): MetricPoint[] => {
    const points: MetricPoint[] = [];
    const now = new Date();
    for (let i = 24; i >= 0; i--) {
      points.push({
        time: new Date(now.getTime() - i * 1000),
        cpu: Math.floor(45 + Math.random() * 15),
        memory: Math.floor(62 + Math.random() * 6),
        network: Math.floor(180 + Math.random() * 40)
      });
    }
    return points;
  };

  const [metrics, setMetrics] = useState<MetricPoint[]>(generateInitialMetrics);
  const trendContainerRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState<number>(600);

  // Load health diagnostics from backend
  const loadDiagnostics = async (showSyncSpinner = false) => {
    if (showSyncSpinner) setSyncing(true);
    try {
      const [clusterRes, cityRes] = await Promise.all([
        getInfrastructureHealth(),
        getCityInfrastructureHealth()
      ]);

      setOverallHealth(clusterRes.overall_health_score);
      setActiveRisksCount(clusterRes.active_risks_count);
      setReports(clusterRes.reports);

      if (cityRes.success) {
        setCityReports(cityRes.reports);
      }
    } catch (err) {
      console.error("Failed to load infrastructure health diagnostics:", err);
    } finally {
      setLoading(false);
      setSyncing(false);
    }
  };

  useEffect(() => {
    loadDiagnostics();
    // Auto-poll health status every 8 seconds
    const pollInterval = setInterval(() => {
      loadDiagnostics();
    }, 8000);
    return () => clearInterval(pollInterval);
  }, []);

  // Smooth rolling 1s intervals for charts (Tab 2)
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((prev) => {
        const nextPoints = [...prev];
        if (nextPoints.length >= 25) {
          nextPoints.shift();
        }
        
        const lastPoint = nextPoints[nextPoints.length - 1];
        const nextTime = new Date(lastPoint.time.getTime() + 1000);
        
        // Match live server loads derived from backend reports
        const activeAI = reports.find(r => r.name.includes("ai-engine"));
        const targetCpu = activeAI ? activeAI.cpu_load : 45;
        const targetMem = activeAI ? activeAI.memory_saturation : 60;

        const nextCpu = Math.min(98, Math.max(5, lastPoint.cpu + (Math.random() * 8 - 4) + (targetCpu - lastPoint.cpu) * 0.15));
        const nextMemory = Math.min(98, Math.max(10, lastPoint.memory + (Math.random() * 2 - 1) + (targetMem - lastPoint.memory) * 0.1));
        const nextNetwork = Math.min(480, Math.max(10, lastPoint.network + (Math.random() * 20 - 10)));
        
        nextPoints.push({
          time: nextTime,
          cpu: Math.round(nextCpu),
          memory: Math.round(nextMemory),
          network: Math.round(nextNetwork)
        });
        return nextPoints;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [reports]);

  // Resize listener
  useEffect(() => {
    const handleResize = () => {
      if (trendContainerRef.current) {
        setChartWidth(trendContainerRef.current.clientWidth);
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    
    const timeout = setTimeout(handleResize, 100);
    return () => {
      window.removeEventListener("resize", handleResize);
      clearTimeout(timeout);
    };
  }, [activeSubTab]);

  const handleSyncClick = () => {
    loadDiagnostics(true);
  };

  const getRiskBadge = (tier: string) => {
    switch (tier.toUpperCase()) {
      case "CRITICAL":
        return <span className="badge badge-critical">Critical</span>;
      case "HIGH":
        return <span className="badge badge-warning" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", border: "1px solid rgba(239, 68, 68, 0.3)" }}>High Risk</span>;
      case "MEDIUM":
        return <span className="badge badge-warning">Medium</span>;
      case "LOW":
        return <span className="badge badge-warning" style={{ background: "rgba(59, 130, 246, 0.15)", color: "#3b82f6", border: "1px solid rgba(59, 130, 246, 0.3)" }}>Low Risk</span>;
      case "NOMINAL":
      default:
        return <span className="badge badge-safe">Nominal</span>;
    }
  };

  const getHealthColor = (score: number) => {
    if (score >= 85) return "var(--status-safe, #10b981)";
    if (score >= 70) return "var(--accent-blue, #3b82f6)";
    if (score >= 55) return "var(--accent-yellow, #eab308)";
    if (score >= 35) return "#f97316";
    return "var(--status-critical, #ef4444)";
  };

  // Find the highest failure threat node for Tab 2
  const peakThreatNode = useMemo(() => {
    if (reports.length === 0) return null;
    return [...reports].sort((a, b) => b.failure_probability - a.failure_probability)[0];
  }, [reports]);

  // Sort city components from lowest health to highest (interactive leaderboard)
  const sortedSectors = useMemo(() => {
    return [...cityReports].sort((a, b) => a.health_score - b.health_score);
  }, [cityReports]);

  // Summary figures for City sectors
  const citySummary = useMemo(() => {
    if (cityReports.length === 0) return { meanHealth: 100, activeRisks: 0, avgConfidence: 100 };
    const meanHealth = Math.round(cityReports.reduce((acc, c) => acc + c.health_score, 0) / cityReports.length);
    const activeRisks = cityReports.filter(c => c.risk_level === "HIGH" || c.risk_level === "CRITICAL").length;
    const avgConfidence = Math.round(cityReports.reduce((acc, c) => acc + c.confidence_score, 0) / cityReports.length);
    return { meanHealth, activeRisks, avgConfidence };
  }, [cityReports]);

  // Find currently selected sector report
  const selectedSectorReport = useMemo(() => {
    return cityReports.find(c => c.category === selectedSector) || null;
  }, [cityReports, selectedSector]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* View Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h2>Infrastructure Health Diagnostics</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Real-time cybernetic diagnostic engines tracking systemic anomalies, sensor data feeds, and hardware performance.
          </p>
        </div>
        <button className="btn-secondary" onClick={handleSyncClick} disabled={syncing || loading}>
          <RefreshCw size={16} className={syncing ? "spin-animation" : ""} />
          <span>Sync Diagnostics</span>
        </button>
      </div>

      {/* Sub-Tab Navigation Toggle */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))", gap: "1.5rem", paddingBottom: "0.5rem" }}>
        <button
          onClick={() => setActiveSubTab("sectors")}
          style={{
            background: "none",
            border: "none",
            color: activeSubTab === "sectors" ? "var(--accent-cyan, #00e5ff)" : "var(--text-muted)",
            borderBottom: activeSubTab === "sectors" ? "2px solid var(--accent-cyan, #00e5ff)" : "none",
            paddingBottom: "0.5rem",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            outline: "none"
          }}
        >
          <Sliders size={16} />
          City Sectors Health (AI Aggregated)
        </button>
        <button
          onClick={() => setActiveSubTab("cluster")}
          style={{
            background: "none",
            border: "none",
            color: activeSubTab === "cluster" ? "var(--accent-cyan, #00e5ff)" : "var(--text-muted)",
            borderBottom: activeSubTab === "cluster" ? "2px solid var(--accent-cyan, #00e5ff)" : "none",
            paddingBottom: "0.5rem",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            outline: "none"
          }}
        >
          <Server size={16} />
          Operations Cluster Diagnostics
        </button>
      </div>

      {loading ? (
        <SkeletonLoader variant="chart" />
      ) : activeSubTab === "sectors" ? (
        /* ================= CITY SECTOR HEALTH VIEW (NEW) ================= */
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          
          {/* Quick Metrics Summary Bar */}
          <div className="dashboard-grid">
            <div className="card col-4">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>Overall City Score</span>
                <Heart size={18} color="var(--accent-cyan, #00e5ff)" />
              </div>
              <h3 style={{ fontSize: "1.75rem", margin: "0.25rem 0", color: getHealthColor(citySummary.meanHealth) }}>
                Health Score: {citySummary.meanHealth}/100
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                {citySummary.meanHealth >= 80 ? "● Nominal City Infrastructure" : "● Operational Interventions Required"}
              </p>
            </div>

            <div className="card col-4" style={{ 
              background: citySummary.activeRisks > 0 ? "rgba(239, 68, 68, 0.04)" : "rgba(30, 41, 59, 0.1)",
              border: citySummary.activeRisks > 0 ? "1px solid rgba(239, 68, 68, 0.2)" : "1px solid var(--border-card)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>Vulnerable Sectors</span>
                <ShieldAlert size={18} color={citySummary.activeRisks > 0 ? "var(--status-critical)" : "var(--status-safe)"} />
              </div>
              <h3 style={{ fontSize: "1.75rem", margin: "0.25rem 0", color: citySummary.activeRisks > 0 ? "var(--status-critical)" : "var(--status-safe)" }}>
                {citySummary.activeRisks} HIGH-RISK SECTOR{citySummary.activeRisks !== 1 ? "S" : ""}
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                {citySummary.activeRisks > 0 ? "Inspect anomaly logs immediately" : "All domains structurally secure"}
              </p>
            </div>

            <div className="card col-4">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>Average Telemetry Confidence</span>
                <Sparkles size={18} color="var(--accent-yellow, #eab308)" />
              </div>
              <h3 style={{ fontSize: "1.75rem", margin: "0.25rem 0", color: "var(--accent-yellow)" }}>
                {citySummary.avgConfidence}% CONFIDENCE
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                Derived from {cityReports.length * 5} active sensor nodes
              </p>
            </div>
          </div>

          {/* Radial Gauges Grid */}
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <h3 style={{ fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Activity size={18} color="var(--accent-cyan, #00e5ff)" />
              City Infrastructure Dynamic Health Gauges
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
              Dynamic HSL radial gauges. Click on any dial to open its diagnostic aggregation panel below.
            </p>

            <div style={{ display: "flex", justifyContent: "space-around", flexWrap: "wrap", gap: "1.5rem", padding: "1rem 0" }}>
              {cityReports.map((c) => {
                const isSelected = selectedSector === c.category;
                const hColor = getHealthColor(c.health_score);
                const r = 40;
                const circ = 2 * Math.PI * r;
                const offset = circ - (c.health_score / 100) * circ;

                return (
                  <div 
                    key={c.category}
                    onClick={() => setSelectedSector(c.category)}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "0.5rem",
                      cursor: "pointer",
                      padding: "1rem",
                      borderRadius: "10px",
                      background: isSelected ? "rgba(6, 182, 212, 0.08)" : "rgba(255,255,255,0.01)",
                      border: isSelected ? "1px solid rgba(6, 182, 212, 0.3)" : "1px solid rgba(255,255,255,0.03)",
                      width: "140px",
                      transition: "var(--transition-smooth)",
                      boxShadow: isSelected ? "0 0 15px rgba(6, 182, 212, 0.1)" : "none"
                    }}
                  >
                    {/* SVG Circular Progress */}
                    <svg width="100" height="100" style={{ transform: "rotate(-90deg)" }}>
                      <circle
                        cx="50"
                        cy="50"
                        r={r}
                        fill="transparent"
                        stroke="rgba(255,255,255,0.04)"
                        strokeWidth="8"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r={r}
                        fill="transparent"
                        stroke={hColor}
                        strokeWidth="8"
                        strokeDasharray={circ}
                        strokeDashoffset={offset}
                        strokeLinecap="round"
                        style={{ transition: "stroke-dashoffset 0.8s ease-in-out" }}
                      />
                    </svg>

                    {/* Centered Absolute Percent text overlay on graphic bounds */}
                    <div style={{ marginTop: "-70px", marginBottom: "30px", display: "flex", flexDirection: "column", alignItems: "center" }}>
                      <span style={{ fontSize: "1.1rem", fontWeight: "bold", color: hColor }}>{c.health_score}%</span>
                    </div>

                    <span style={{ fontWeight: "bold", fontSize: "0.8rem", color: isSelected ? "var(--text-primary)" : "var(--text-secondary)", textTransform: "capitalize", textAlign: "center" }}>
                      {c.category.replace("_", " ").toLowerCase()}
                    </span>
                    {getRiskBadge(c.risk_level)}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="dashboard-grid">
            
            {/* Interactive Rankings Board Leaderboard */}
            <div className="card col-7" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <h3 style={{ fontSize: "1.1rem" }}>Infrastructure Leaderboard Ranking</h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
                Automatic threat priority ranking. Worst-health infrastructure channels are dynamically sorted to the top.
              </p>

              <div className="table-container" style={{ maxHeight: "350px", overflowY: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Sector Name</th>
                      <th>Health Rating</th>
                      <th>Risk Level</th>
                      <th>Data Confidence</th>
                      <th>Inspect</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedSectors.map((sector) => {
                      const isSelected = selectedSector === sector.category;
                      const hColor = getHealthColor(sector.health_score);
                      return (
                        <tr 
                          key={sector.category}
                          onClick={() => setSelectedSector(sector.category)}
                          style={{
                            cursor: "pointer",
                            background: isSelected ? "rgba(255,255,255,0.03)" : "transparent"
                          }}
                        >
                          <td style={{ fontWeight: "bold", textTransform: "capitalize", color: isSelected ? "var(--accent-cyan)" : "var(--text-primary)" }}>
                            {sector.category.replace("_", " ").toLowerCase()}
                          </td>
                          <td>
                            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                              <span style={{ fontWeight: "bold", color: hColor, minWidth: "2rem" }}>
                                {sector.health_score}%
                              </span>
                              <div style={{ width: "50px", height: "5px", background: "rgba(255,255,255,0.04)", borderRadius: "2px", overflow: "hidden" }}>
                                <div style={{ width: `${sector.health_score}%`, height: "100%", background: hColor }}></div>
                              </div>
                            </div>
                          </td>
                          <td>{getRiskBadge(sector.risk_level)}</td>
                          <td style={{ fontWeight: "bold", color: "var(--text-secondary)" }}>
                            {sector.confidence_score}%
                          </td>
                          <td>
                            <button 
                              className="btn-secondary" 
                              style={{ padding: "0.2rem 0.5rem", fontSize: "0.7rem" }}
                            >
                              Details
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Selected Sector Details & Penalty Breakdown */}
            <div className="card col-5" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {selectedSectorReport ? (
                <>
                  <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem", textTransform: "capitalize" }}>
                    <Heart size={18} color={getHealthColor(selectedSectorReport.health_score)} />
                    {selectedSectorReport.category.replace("_", " ").toLowerCase()} Diagnostics
                  </h3>
                  
                  <div style={{
                    background: "var(--bg-deep, rgba(15, 23, 42, 0.3))",
                    border: "1px solid var(--border-card)",
                    padding: "0.85rem 1rem",
                    borderRadius: "8px",
                    borderLeft: `4px solid ${getHealthColor(selectedSectorReport.health_score)}`
                  }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "bold" }}>Explainable AI Summary</span>
                    <p style={{ fontSize: "0.85rem", color: "var(--text-primary)", lineHeight: 1.4, margin: "0.25rem 0 0 0" }}>
                      {selectedSectorReport.explanation}
                    </p>
                  </div>

                  {/* Multi-source Penalty Breakdown visual */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.50rem", marginTop: "0.25rem" }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "bold" }}>Multi-Source Risk Penalty Allocation</span>
                    
                    {[
                      { label: "AI Anomaly Penalty", value: selectedSectorReport.penalties_breakdown.anomaly_penalty, max: 60, color: "var(--status-critical, #ef4444)" },
                      { label: "Social Media Complaint Risk", value: selectedSectorReport.penalties_breakdown.social_penalty, max: 40, color: "var(--accent-purple, #a855f7)" },
                      { label: "Physical Telemetry Stress", value: selectedSectorReport.penalties_breakdown.physical_penalty, max: 30, color: "var(--accent-yellow, #eab308)" }
                    ].map((p, idx) => (
                      <div key={idx} style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                          <span style={{ color: "var(--text-secondary)" }}>{p.label}</span>
                          <span style={{ fontWeight: "bold", color: p.color }}>-{p.value.toFixed(1)}</span>
                        </div>
                        <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.04)", borderRadius: "3px", overflow: "hidden" }}>
                          <div style={{ width: `${(p.value / p.max) * 100}%`, height: "100%", background: p.color }}></div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Live Physical Telemetry Mapped values */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", marginTop: "0.5rem" }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "bold" }}>Active Sensor Feed Channels</span>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.5rem" }}>
                      {Object.entries(selectedSectorReport.metrics).map(([key, val]) => (
                        <div key={key} style={{ background: "rgba(255,255,255,0.02)", padding: "0.4rem 0.6rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.03)" }}>
                          <span style={{ display: "block", fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>{key.replace(/_/g, " ")}</span>
                          <strong style={{ fontSize: "0.85rem", color: "var(--accent-cyan)" }}>{val}</strong>
                        </div>
                      ))}
                    </div>
                  </div>

                </>
              ) : (
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "2rem" }}>
                  Select a sector to load its dynamic diagnostic panel.
                </p>
              )}
            </div>

          </div>

        </div>
      ) : (
        /* ================= PREDICTIVE CLUSTER DIAGNOSTICS VIEW (ORIGINAL) ================= */
        <>
          {/* Hardware Quick Indicators */}
          <div className="dashboard-grid">
            
            {/* 1. Overall Health Score */}
            <div className="card col-4">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>System Health Pool</span>
                <Heart size={18} color="var(--accent-cyan, #00e5ff)" />
              </div>
              <h3 style={{ fontSize: "1.75rem", margin: "0.25rem 0", color: getHealthColor(overallHealth) }}>
                Health Score: {overallHealth}/100
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                {overallHealth >= 80 ? "● Perfect Cluster Integrity" : "● Impending Baseline Degradation"}
              </p>
            </div>

            {/* 2. Peak Threat Highlight Card */}
            <div className="card col-4" style={{ 
              background: activeRisksCount > 0 ? "rgba(239, 68, 68, 0.04)" : "rgba(30, 41, 59, 0.1)",
              border: activeRisksCount > 0 ? "1px solid rgba(239, 68, 68, 0.2)" : "1px solid var(--border-card)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>Maximum Failure Vector</span>
                <AlertTriangle size={18} color={activeRisksCount > 0 ? "var(--status-critical)" : "var(--accent-yellow)"} />
              </div>
              {peakThreatNode ? (
                <>
                  <h3 style={{ fontSize: "1.65rem", margin: "0.25rem 0", color: peakThreatNode.failure_probability >= 50.0 ? "var(--status-critical, #ef4444)" : "var(--text-primary)" }}>
                    {peakThreatNode.failure_probability}% in {peakThreatNode.remaining_useful_life_days} days
                  </h3>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                    Node: <span style={{ fontFamily: "var(--font-mono)", fontWeight: "bold" }}>{peakThreatNode.name}</span>
                  </p>
                </>
              ) : (
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Nominal</p>
              )}
            </div>

            {/* 3. Active Incident Risks */}
            <div className="card col-4">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>Critical / High Risk Nodes</span>
                <ShieldAlert size={18} color={activeRisksCount > 0 ? "var(--status-critical)" : "var(--status-safe)"} />
              </div>
              <h3 style={{ fontSize: "1.75rem", margin: "0.25rem 0", color: activeRisksCount > 0 ? "var(--status-critical)" : "var(--status-safe)" }}>
                {activeRisksCount} DEGRADED NODE{activeRisksCount !== 1 ? "S" : ""}
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                {activeRisksCount > 0 ? "Autoscaling provision recommended" : "No threat overrides active"}
              </p>
            </div>
          </div>

          {/* Real-time System Telemetry Panel */}
          <div 
            className="card" 
            ref={trendContainerRef} 
            style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1.1rem", margin: 0 }}>
                <Activity size={18} color="var(--accent-cyan, #00e5ff)" />
                Active System Telemetry Core (1s Rolling Refresh)
              </h3>
              <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#06b6d4" }} />
                  <span>CPU ({metrics[metrics.length - 1]?.cpu}%)</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#3b82f6" }} />
                  <span>Memory ({metrics[metrics.length - 1]?.memory}%)</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#10b981" }} />
                  <span>Network ({metrics[metrics.length - 1]?.network} Mbps)</span>
                </div>
              </div>
            </div>

            <div style={{ width: "100%", overflow: "hidden" }}>
              <Plot
                data={[
                  {
                    x: metrics.map(m => m.time),
                    y: metrics.map(m => m.cpu),
                    type: "scatter",
                    mode: "lines",
                    name: "CPU Utilization",
                    yaxis: "y",
                    line: { color: "#06b6d4", width: 2.5, shape: "spline" },
                    hovertemplate: "%{y}%<extra></extra>"
                  },
                  {
                    x: metrics.map(m => m.time),
                    y: metrics.map(m => m.memory),
                    type: "scatter",
                    mode: "lines",
                    name: "Memory Saturation",
                    yaxis: "y",
                    line: { color: "#3b82f6", width: 2.5, shape: "spline" },
                    hovertemplate: "%{y}%<extra></extra>"
                  },
                  {
                    x: metrics.map(m => m.time),
                    y: metrics.map(m => m.network),
                    type: "scatter",
                    mode: "lines",
                    name: "Network Throughput",
                    yaxis: "y2",
                    line: { color: "#10b981", width: 2, shape: "spline" },
                    hovertemplate: "%{y} Mbps<extra></extra>"
                  }
                ]}
                layout={{
                  width: chartWidth - 32,
                  height: 250,
                  paper_bgcolor: "transparent",
                  plot_bgcolor: "rgba(30, 41, 59, 0.12)",
                  margin: { l: 45, r: 45, t: 15, b: 35 },
                  showlegend: false,
                  xaxis: {
                    type: "date",
                    tickformat: "%H:%M:%S",
                    gridcolor: "rgba(71, 85, 105, 0.12)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                    zeroline: false
                  },
                  yaxis: {
                    title: {
                      text: "Utilization (%)",
                      font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 }
                    },
                    gridcolor: "rgba(71, 85, 105, 0.12)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                    zeroline: false,
                    range: [0, 100]
                  },
                  yaxis2: {
                    title: {
                      text: "Throughput (Mbps)",
                      font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 }
                    },
                    gridcolor: "rgba(71, 85, 105, 0.04)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                    zeroline: false,
                    overlaying: "y",
                    side: "right",
                    range: [0, 500]
                  },
                  hovermode: "x unified",
                  dragmode: false
                }}
                config={{
                  responsive: true,
                  displayModeBar: false
                }}
              />
            </div>
          </div>

          {/* Node Operations Grid */}
          <div className="card">
            <h3 style={{ marginBottom: "1rem", fontSize: "1.1rem" }}>Predictive Diagnostic Cluster Node Registry</h3>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Host Node</th>
                    <th>Type / Role</th>
                    <th>Health Rating</th>
                    <th>Failure Probability</th>
                    <th>RUL Estimate</th>
                    <th>Risk Grade</th>
                    <th>Explainable AI diagnostics</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((node) => {
                    const healthColor = getHealthColor(node.health_score);
                    return (
                      <tr key={node.name}>
                        <td style={{ fontWeight: 600, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                          {node.name}
                        </td>
                        <td style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{node.node_type}</td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                            <span style={{ fontWeight: "bold", color: healthColor, minWidth: "2.5rem" }}>
                              {node.health_score}/100
                            </span>
                            <div style={{ width: "60px", height: "6px", background: "rgba(255,255,255,0.06)", borderRadius: "3px", overflow: "hidden" }}>
                              <div style={{ width: `${node.health_score}%`, height: "100%", background: healthColor }}></div>
                            </div>
                          </div>
                        </td>
                        <td style={{ 
                          fontFamily: "var(--font-mono)", 
                          fontWeight: "bold",
                          color: node.failure_probability >= 50.0 ? "var(--status-critical, #ef4444)" : "var(--text-primary)"
                        }}>
                          {node.failure_probability}%
                        </td>
                        <td style={{ fontWeight: 600 }}>
                          {node.remaining_useful_life_days === 365 
                            ? "365+ Days" 
                            : `${node.remaining_useful_life_days} Days`
                          }
                        </td>
                        <td>{getRiskBadge(node.risk_tier)}</td>
                        <td style={{ fontSize: "0.75rem", color: "var(--text-secondary)", maxWidth: "250px", lineHeight: "1.4" }}>
                          {node.explanation}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Embedded Spin Keyframes for reload */}
      <style>{`
        .spin-animation {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default InfrastructureHealth;
