import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Check,
  ShieldCheck,
  Filter,
  RefreshCw,
  ServerCrash,
  Database,
  Sliders,
  TrendingDown,
  Activity,
  PlusCircle,
  Clock
} from "lucide-react";
import SkeletonLoader from "../common/SkeletonLoader";
import { useAnomalies } from "../../hooks/useAnomalies";
import { Anomaly, PrioritizedAlert } from "../../types/domain";
import { 
  getAlertsQueue, 
  acknowledgePrioritizedAlert, 
  resolvePrioritizedAlert, 
  injectPrioritizedIncident
} from "../../api/alerts";

export const AnomalyAlerts: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<"prioritized" | "historical">("prioritized");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [queueData, setQueueData] = useState<PrioritizedAlert[]>([]);

  // Injector state
  const [showInjector, setShowInjector] = useState(false);
  const [injectMetric, setInjectMetric] = useState("CPU_Usage");
  const [injectSeverity, setInjectSeverity] = useState<"CRITICAL" | "WARNING" | "INFO">("CRITICAL");
  const [injectScore, setInjectScore] = useState(0.85);
  const [injectDesc, setInjectDesc] = useState("Manual load testing anomaly trigger.");

  // Fetch standard historical anomalies using hook
  const { 
    data: historicalData, 
    loading: historicalLoading, 
    error: historicalError, 
    isPlaceholder: historicalPlaceholder, 
    refetch: refetchHistorical, 
    acknowledge: acknowledgeHistorical 
  } = useAnomalies({ page_size: 50 });

  // Fetch prioritized queue
  const fetchQueue = useCallback(async () => {
    setLoadingQueue(true);
    try {
      const data = await getAlertsQueue(statusFilter, severityFilter);
      const items = data && Array.isArray(data)
        ? data
        : (data && Array.isArray((data as any).items) ? (data as any).items : []);
      setQueueData(items);
    } catch (err) {
      console.error("Failed to fetch prioritized alerts queue:", err);
    } finally {
      setLoadingQueue(false);
    }
  }, [statusFilter, severityFilter]);

  useEffect(() => {
    fetchQueue();
    // Poll the prioritizer queue every 3 seconds to dynamically demonstrate SLA escalations!
    const interval = setInterval(fetchQueue, 3000);
    return () => clearInterval(interval);
  }, [statusFilter, severityFilter]);

  const handleAcknowledge = async (id: string) => {
    try {
      await acknowledgePrioritizedAlert(id);
      await fetchQueue();
    } catch (err) {
      console.error("Failed to acknowledge prioritized alert:", err);
    }
  };

  const handleResolve = async (id: string) => {
    try {
      await resolvePrioritizedAlert(id);
      await fetchQueue();
    } catch (err) {
      console.error("Failed to resolve prioritized alert:", err);
    }
  };

  const handleInject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        id: `anom-inj-${Math.floor(Math.random() * 900) + 100}`,
        timestamp: new Date().toISOString(),
        metric_name: injectMetric,
        severity: injectSeverity,
        score: injectScore,
        description: injectDesc
      };
      await injectPrioritizedIncident(payload);
      setShowInjector(false);
      await fetchQueue();
    } catch (err) {
      console.error("Failed to inject incident:", err);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL":
        return <AlertCircle size={16} color="var(--status-critical, #ef4444)" />;
      case "WARNING":
      case "HIGH":
        return <AlertTriangle size={16} color="var(--status-warning, #f59e0b)" />;
      case "MEDIUM":
        return <AlertTriangle size={16} color="#eab308" />;
      case "LOW":
      case "INFO":
      default:
        return <Info size={16} color="var(--status-info, #3b82f6)" />;
    }
  };

  const getSeverityBadge = (severity: string) => (
    <span className={`badge badge-${severity.toLowerCase()}`}>{severity}</span>
  );

  const getPriorityColor = (score: number) => {
    if (score >= 75) return "var(--status-critical, #ef4444)";
    if (score >= 50) return "#f97316";
    if (score >= 25) return "var(--accent-yellow, #eab308)";
    return "var(--accent-cyan, #00e5ff)";
  };

  // Filter historical table records locally — memoised to avoid re-filtering on every render
  const filteredHistorical = useMemo(
    () =>
      (historicalData || []).filter((alert) => {
        if (!alert) return false;
        const sevMatch = severityFilter === "ALL" || alert.severity === severityFilter;
        const statMatch =
          statusFilter === "ALL" ||
          (statusFilter === "ACTIVE" && !alert.acknowledged) ||
          (statusFilter === "ACKNOWLEDGED" && alert.acknowledged);
        return sevMatch && statMatch;
      }),
    [historicalData, severityFilter, statusFilter]
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h2>Operational Incident Control</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Real-time alert prioritizations, duplicate suppression buffers, and automatic SLA response escalations.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          {/* Injector trigger */}
          <button 
            className="btn-primary" 
            onClick={() => setShowInjector(!showInjector)}
            style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}
          >
            <PlusCircle size={14} />
            <span>Simulate Anomaly</span>
          </button>

          {/* Filters */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
            <Filter size={16} color="var(--accent-cyan)" />
            <span>Filters:</span>
          </div>

          <select
            className="select-dropdown"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="WARNING">Warning / High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low / Info</option>
          </select>

          <select
            className="select-dropdown"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="SUPPRESSED">Suppressed</option>
            <option value="ESCALATED">Escalated</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          <button
            className="btn-secondary"
            onClick={activeSubTab === "prioritized" ? fetchQueue : refetchHistorical}
            disabled={activeSubTab === "prioritized" ? loadingQueue : historicalLoading}
          >
            <RefreshCw
              size={14}
              className={(activeSubTab === "prioritized" ? loadingQueue : historicalLoading) ? "spin-animation" : ""}
            />
            <span>Refresh</span>
          </button>

        
        </div>
      </div>

      {/* Manual Anomaly Simulator Drawer Panel */}
      {showInjector && (
        <form onSubmit={handleInject} className="card" style={{
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
          background: "rgba(6, 182, 212, 0.03)",
          border: "1px solid rgba(6, 182, 212, 0.2)",
          padding: "1.25rem",
          borderRadius: "10px"
        }}>
          <h4 style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Activity size={16} color="var(--accent-cyan)" />
            Real-time Anomaly Injector Simulator
          </h4>
          <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", margin: 0 }}>
            Simulate incoming raw ML telemetry triggers. Injecting duplicates within 5 minutes will merge them; injecting on acknowledged/resolved metrics enters cooldown.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginTop: "0.25rem" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Metric Channel</span>
              <select 
                className="select-dropdown" 
                value={injectMetric} 
                onChange={(e) => setInjectMetric(e.target.value)}
              >
                <option value="CPU_Usage">CPU_Usage (Power / Gateway)</option>
                <option value="Database_Latency">Database_Latency (Postgres)</option>
                <option value="weather_precip">weather_precip (Water Floods)</option>
                <option value="traffic_jam">traffic_jam (Traffic gridlock)</option>
                <option value="anomaly_score">anomaly_score (Internet lines)</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Severity Level</span>
              <select 
                className="select-dropdown" 
                value={injectSeverity} 
                onChange={(e) => setInjectSeverity(e.target.value as "CRITICAL" | "WARNING" | "INFO")}
              >
                <option value="CRITICAL">CRITICAL</option>
                <option value="WARNING">WARNING</option>
                <option value="INFO">INFO</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Anomaly Score ({injectScore})</span>
              <input 
                type="range" 
                min="0.1" 
                max="1.0" 
                step="0.05"
                value={injectScore} 
                onChange={(e) => setInjectScore(parseFloat(e.target.value))}
                style={{ marginTop: "0.4rem", accentColor: "var(--accent-cyan)" }}
              />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Custom Description</span>
            <input 
              type="text" 
              className="search-input" 
              style={{ padding: "0.4rem 0.8rem", width: "100%" }}
              value={injectDesc} 
              onChange={(e) => setInjectDesc(e.target.value)}
            />
          </div>

          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <button type="button" className="btn-secondary" onClick={() => setShowInjector(false)}>Cancel</button>
            <button type="submit" className="btn-primary">Inject Incident</button>
          </div>
        </form>
      )}

      {/* Sub-Tab Navigation Toggle */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))", gap: "1.5rem", paddingBottom: "0.5rem" }}>
        <button
          onClick={() => setActiveSubTab("prioritized")}
          style={{
            background: "none",
            border: "none",
            color: activeSubTab === "prioritized" ? "var(--accent-cyan, #00e5ff)" : "var(--text-muted)",
            borderBottom: activeSubTab === "prioritized" ? "2px solid var(--accent-cyan, #00e5ff)" : "none",
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
          Intelligent Prioritized Alert Queue
        </button>
        <button
          onClick={() => setActiveSubTab("historical")}
          style={{
            background: "none",
            border: "none",
            color: activeSubTab === "historical" ? "var(--accent-cyan, #00e5ff)" : "var(--text-muted)",
            borderBottom: activeSubTab === "historical" ? "2px solid var(--accent-cyan, #00e5ff)" : "none",
            paddingBottom: "0.5rem",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            outline: "none"
          }}
        >
          <Database size={16} />
          Historical Anomaly Triggers
        </button>
      </div>

      {activeSubTab === "prioritized" ? (
        /* ================= TAB 1: INTELLIGENT PRIORITIZED QUEUE ================= */
        loadingQueue ? (
          <SkeletonLoader variant="table-row" count={5} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            
            {/* Quick Prioritizer stats summary */}
            <div style={{
              display: "flex",
              gap: "2rem",
              background: "rgba(30, 41, 59, 0.15)",
              border: "1px solid var(--border-card)",
              padding: "1.25rem",
              borderRadius: "8px",
              flexWrap: "wrap"
            }}>
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Critical Prioritized Alerts</span>
                <h3 style={{ fontSize: "1.5rem", color: "var(--status-critical)", marginTop: "0.25rem" }}>
                  {(queueData || []).filter(a => a && a.priority_score >= 75 && a.status !== "RESOLVED").length} Incidents
                </h3>
              </div>
              <div style={{ borderLeft: "1px solid var(--border-card)", paddingLeft: "2rem" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Active De-duplicated Outages</span>
                <h3 style={{ fontSize: "1.5rem", color: "var(--accent-cyan)", marginTop: "0.25rem" }}>
                  {(queueData || []).reduce((acc, a) => acc + (a && a.status !== "RESOLVED" ? a.occurrence_count : 0), 0)} Triggers suppressed
                </h3>
              </div>
              <div style={{ borderLeft: "1px solid var(--border-card)", paddingLeft: "2rem" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Active Metric Cooldowns</span>
                <h3 style={{ fontSize: "1.5rem", color: "var(--status-safe)", marginTop: "0.25rem" }}>
                  {(queueData || []).filter(a => a && a.cooldown_until && new Date(a.cooldown_until) > new Date()).length} Cooldown Locks
                </h3>
              </div>
            </div>

            {/* Prioritized alert list queue */}
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {(queueData || []).length === 0 ? (
                <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                  No prioritized operational alerts are currently active in this filter.
                </div>
              ) : (
                (queueData || []).map((alert) => {
                  if (!alert) return null;
                  const pColor = getPriorityColor(alert.priority_score);
                  const isCooldown = alert.cooldown_until && new Date(alert.cooldown_until) > new Date();

                  return (
                    <div 
                      key={alert.id}
                      className="card"
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: "1.5rem",
                        flexWrap: "wrap",
                        borderLeft: `5px solid ${pColor}`,
                        opacity: alert.status === "RESOLVED" ? 0.6 : 1,
                        background: alert.status === "ESCALATED" ? "rgba(239, 68, 68, 0.02)" : "rgba(30, 41, 59, 0.15)",
                        transition: "all 0.3s ease"
                      }}
                    >
                      {/* Priority Score ring dial */}
                      <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
                        <div style={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          justifyContent: "center",
                          width: "60px",
                          height: "60px",
                          borderRadius: "50%",
                          border: `3px solid ${pColor}`,
                          boxShadow: `0 0 10px ${pColor}20`,
                          fontWeight: "bold"
                        }}>
                          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>PRI</span>
                          <span style={{ fontSize: "1rem", color: pColor, marginTop: "-0.2rem" }}>{Math.round(alert.priority_score)}</span>
                        </div>

                        {/* Middle metadata details */}
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                            <strong style={{ fontSize: "1rem", color: "var(--text-primary)" }}>{alert.metric_name.replace(/_/g, " ")}</strong>
                            {getSeverityBadge(alert.current_severity)}
                            
                            {/* Duplicate count tag */}
                            {alert.occurrence_count > 1 && (
                              <span style={{ 
                                fontSize: "0.7rem", 
                                background: "rgba(168, 85, 247, 0.15)", 
                                color: "var(--accent-purple, #a855f7)", 
                                padding: "0.1rem 0.4rem", 
                                borderRadius: "4px",
                                border: "1px solid rgba(168, 85, 247, 0.3)",
                                fontWeight: "bold"
                              }}>
                                x{alert.occurrence_count} duplicate events suppressed
                              </span>
                            )}

                            {/* Escalated SLA badge */}
                            {alert.status === "ESCALATED" && (
                              <span className="badge badge-critical" style={{ fontSize: "0.65rem", padding: "0.1rem 0.3rem" }}>
                                SLA Violation
                              </span>
                            )}

                            {/* Cooldown Lock badge */}
                            {isCooldown && (
                              <span style={{ 
                                fontSize: "0.7rem", 
                                background: "rgba(16, 185, 129, 0.15)", 
                                color: "var(--status-safe, #10b981)", 
                                padding: "0.1rem 0.4rem", 
                                borderRadius: "4px",
                                border: "1px solid rgba(16, 185, 129, 0.3)",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "0.25rem",
                                fontWeight: "bold"
                              }}>
                                <Clock size={10} /> Cooldown Lock
                              </span>
                            )}
                          </div>

                          <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)", maxWidth: "550px" }}>
                            {alert.description}
                          </p>

                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                            ID: {alert.id} • Triggered: {new Date(alert.timestamp).toLocaleTimeString()} • Status: <code style={{ color: pColor }}>{alert.status}</code>
                          </span>
                        </div>
                      </div>

                      {/* Right action triggers */}
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        {alert.status !== "RESOLVED" && alert.status !== "SUPPRESSED" ? (
                          <>
                            {alert.status !== "ACKNOWLEDGED" && (
                              <button 
                                className="btn-secondary" 
                                style={{ padding: "0.4rem 0.8rem", fontSize: "0.8rem" }}
                                onClick={() => handleAcknowledge(alert.id)}
                              >
                                Acknowledge
                              </button>
                            )}
                            <button 
                              className="btn-primary" 
                              style={{ padding: "0.4rem 0.8rem", fontSize: "0.8rem" }}
                              onClick={() => handleResolve(alert.id)}
                            >
                              Resolve Alert
                            </button>
                          </>
                        ) : (
                          <span style={{ 
                            color: "var(--status-safe)", 
                            display: "inline-flex", 
                            alignItems: "center", 
                            gap: "0.25rem", 
                            fontSize: "0.85rem", 
                            fontWeight: "bold" 
                          }}>
                            <ShieldCheck size={16} /> Closed / Logged
                          </span>
                        )}
                      </div>

                    </div>
                  );
                })
              )}
            </div>

          </div>
        )
      ) : (
        /* ================= TAB 2: HISTORICAL ANOMALY REGISTRY ================= */
        historicalLoading && !historicalError ? (
          <SkeletonLoader variant="table-row" count={5} />
        ) : historicalError ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem", padding: "3rem", textAlign: "center" }} className="card">
            <ServerCrash size={40} color="var(--status-critical)" />
            <h3>Failed to Fetch Anomaly Records</h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>{historicalError.message}</p>
            <button className="btn-primary" onClick={refetchHistorical}><RefreshCw size={14} /> Retry</button>
          </div>
        ) : (
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Quick counts */}
            <div style={{ display: "flex", gap: "2rem", borderBottom: "1px solid var(--border-card)", paddingBottom: "1.25rem", flexWrap: "wrap" }}>
              <div>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Active Anomalies</span>
                <h3 style={{ fontSize: "1.5rem", color: "var(--status-critical)", marginTop: "0.25rem" }}>
                  {(historicalData || []).filter((x) => x && !x.acknowledged).length} Incidents
                </h3>
              </div>
              <div style={{ borderLeft: "1px solid var(--border-card)", paddingLeft: "2rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Mitigated / Acknowledged</span>
                <h3 style={{ fontSize: "1.5rem", color: "var(--status-safe)", marginTop: "0.25rem" }}>
                  {(historicalData || []).filter((x) => x && x.acknowledged).length} Resolved
                </h3>
              </div>
            </div>

            {/* Table */}
            <div className="table-container">
              {filteredHistorical.length === 0 ? (
                <div style={{ padding: "3rem 1rem", textAlign: "center", color: "var(--text-muted)" }}>
                  No anomaly triggers matched active filters.
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>Signal ID</th>
                      <th>Metric Trigger</th>
                      <th>Model Score</th>
                      <th>Timestamp</th>
                      <th>Details</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHistorical.map((alert) => (
                      <tr key={alert.id} style={{ opacity: alert.acknowledged ? 0.65 : 1, transition: "opacity 0.25s ease" }}>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                            {getSeverityIcon(alert.severity)}
                            {getSeverityBadge(alert.severity)}
                          </div>
                        </td>
                        <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{alert.id}</td>
                        <td style={{ fontWeight: 500 }}>{alert.metric_name.replace(/_/g, " ")}</td>
                        <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: alert.severity === "CRITICAL" ? "var(--status-critical)" : "var(--status-warning)" }}>
                          {alert.score.toFixed(2)}
                        </td>
                        <td style={{ fontSize: "0.85rem", whiteSpace: "nowrap", fontFamily: "var(--font-mono)" }}>
                          {new Date(alert.timestamp).toLocaleString()}
                        </td>
                        <td style={{ maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={alert.description}>
                          {alert.description}
                        </td>
                        <td>
                          {!alert.acknowledged ? (
                            <button
                              className="btn-secondary"
                              style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
                              onClick={() => acknowledgeHistorical(alert.id)}
                            >
                              <Check size={12} /> Acknowledge
                            </button>
                          ) : (
                            <span style={{ color: "var(--status-safe)", display: "inline-flex", alignItems: "center", gap: "0.25rem", fontSize: "0.8rem", fontWeight: 600 }}>
                              <ShieldCheck size={14} /> Logged
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )
      )}
    </div>
  );
};

export default AnomalyAlerts;
