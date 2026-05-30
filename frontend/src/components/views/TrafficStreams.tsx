import React, { useState, useEffect, useRef } from "react";
import { 
  Gauge, 
  Clock, 
  AlertTriangle, 
  Activity, 
  MapPin, 
  Server,
  RefreshCw,
  Navigation
} from "lucide-react";
import Plot from "react-plotly.js";
import { getCurrentTraffic, getTrafficTrends, TrafficRecord } from "../../api/traffic";
import SkeletonLoader from "../common/SkeletonLoader";

export const TrafficStreams: React.FC = React.memo(() => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [currentRecords, setCurrentRecords] = useState<TrafficRecord[]>([]);
  const [selectedCorridor, setSelectedCorridor] = useState<string>("NYC-I95");
  const [visibleSeries, setVisibleSeries] = useState({
    flowSpeed: true,
    freeFlowSpeed: true,
    jamFactor: true,
    incidents: false
  });
  const [trends, setTrends] = useState<TrafficRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [apiSource, setApiSource] = useState<string>("HERE Traffic (Simulation Fallback)");

  const trendContainerRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState<number>(600);

  // Poll intervals
  useEffect(() => {
    fetchInitialData();

    // Auto-refresh traffic stats every 30 seconds
    const interval = setInterval(() => {
      refreshDataSilently();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Fetch trends when selected corridor changes
  useEffect(() => {
    fetchCorridorTrends(selectedCorridor);
  }, [selectedCorridor]);

  // Handle responsive plotly resizing
  useEffect(() => {
    const handleResize = () => {
      if (trendContainerRef.current) {
        setChartWidth(trendContainerRef.current.clientWidth);
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();

    return () => window.removeEventListener("resize", handleResize);
  }, [trends, loading]);

  const fetchInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      const trafficRes = await getCurrentTraffic();
      setCurrentRecords(trafficRes.records);
      
      const source = (trafficRes as any).success ? "HERE Traffic API" : "HERE Traffic (Simulation Fallback)";
      setApiSource(source);

      if (trafficRes.records.length > 0) {
        const matchingCorridor = trafficRes.records.find(r => r.corridor_id.toLowerCase() === selectedCorridor.toLowerCase());
        if (!matchingCorridor) {
          setSelectedCorridor(trafficRes.records[0].corridor_id);
        }
      }
      
      await fetchCorridorTrends(selectedCorridor);
    } catch (err: any) {
      setError(err.message || "Failed to establish road congestion telemetry link.");
    } finally {
      setLoading(false);
    }
  };

  const refreshDataSilently = async () => {
    setRefreshing(true);
    try {
      const trafficRes = await getCurrentTraffic();
      setCurrentRecords(trafficRes.records);
      await fetchCorridorTrends(selectedCorridor);
    } catch (err) {
      console.error("Traffic telemetry silent refresh error", err);
    } finally {
      setRefreshing(false);
    }
  };

  const fetchCorridorTrends = async (corridor: string) => {
    try {
      const trendRes = await getTrafficTrends(corridor);
      setTrends(trendRes.records);
    } catch (err) {
      console.error(`Failed to retrieve historical trends for ${corridor}`, err);
    }
  };

  // Extract selected corridor's current stats
  const activeRecord = currentRecords.find(
    (r) => r.corridor_id.toLowerCase() === selectedCorridor.toLowerCase()
  ) || trends[trends.length - 1];

  // Prepare continuous timeline xData array using JS Date objects
  const xData = trends.map((t) => new Date(t.timestamp));

  // Build high-fidelity multi-series overlay traces
  const traces: any[] = [];
  if (visibleSeries.flowSpeed) {
    traces.push({
      x: xData,
      y: trends.map((t) => t.flow_speed_kmh ?? 0),
      type: "scatter",
      mode: "lines+markers",
      name: "Flow Speed",
      yaxis: "y",
      line: { color: "#a78bfa", width: 3, shape: "spline" },
      marker: { color: "#a78bfa", size: 5, line: { color: "rgba(15, 23, 42, 0.8)", width: 1 } },
      hovertemplate: "%{y:.1f} km/h<extra></extra>"
    });
  }
  if (visibleSeries.freeFlowSpeed) {
    traces.push({
      x: xData,
      y: trends.map((t) => t.free_flow_speed_kmh ?? 0),
      type: "scatter",
      mode: "lines",
      name: "Reference Free-Flow",
      yaxis: "y",
      line: { color: "#64748b", width: 2, dash: "dash", shape: "spline" },
      hovertemplate: "%{y:.1f} km/h<extra></extra>"
    });
  }
  if (visibleSeries.jamFactor) {
    traces.push({
      x: xData,
      y: trends.map((t) => t.jam_factor ?? 0),
      type: "scatter",
      mode: "lines",
      fill: "tozeroy",
      fillcolor: "rgba(245, 158, 11, 0.15)",
      name: "Jam Factor",
      yaxis: "y2",
      line: { color: "#f59e0b", width: 1.5, shape: "spline" },
      hovertemplate: "%{y:.1f} / 10<extra></extra>"
    });
  }
  if (visibleSeries.incidents) {
    traces.push({
      x: xData,
      y: trends.map((t) => t.incident_count ?? 0),
      type: "bar",
      name: "Incidents",
      yaxis: "y2",
      marker: { 
        color: "rgba(239, 68, 68, 0.4)",
        line: { color: "#ef4444", width: 1.5 }
      },
      hovertemplate: "%{y} incidents<extra></extra>"
    });
  }

  const getCongestionBadgeClass = (level: string) => {
    switch (level) {
      case "GRIDLOCK": return "badge-critical";
      case "CONGESTED": return "badge-warning";
      case "SLOW": return "badge-warning";
      default: return "badge-safe";
    }
  };

  const getCorridorName = (id: string) => {
    if (id === "NYC-I95") return "New York I-95";
    if (id === "LA-I405") return "Los Angeles I-405";
    if (id === "LON-M25") return "London M25";
    return id;
  };

  if (loading) {
    return <SkeletonLoader variant="chart" />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", marginTop: "1rem" }}>
      
      {/* SECTION HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <Navigation size={24} color="var(--accent-purple)" style={{ transform: "rotate(45deg)" }} />
          <div>
            <h3 style={{ margin: 0 }}>Corridor Traffic Ingestion Telemetry</h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0 }}>
              Live transit flow patterns and jam indicators mapped to municipal sequence correlation matrices.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {/* Active API source pill */}
          <div 
            style={{ 
              background: "rgba(30, 41, 59, 0.4)", 
              border: "1px solid var(--border-card)",
              padding: "0.35rem 0.75rem",
              borderRadius: "20px",
              fontSize: "0.75rem",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem"
            }}
          >
            <Server size={12} color="var(--text-muted)" />
            <span style={{ color: "var(--text-secondary)" }}>Source:</span>
            <span style={{ color: "var(--accent-purple)", fontWeight: 600 }}>{apiSource}</span>
          </div>

          <button 
            className="btn-secondary" 
            onClick={fetchInitialData} 
            disabled={refreshing}
            style={{ padding: "0.4rem 0.85rem" }}
          >
            <RefreshCw size={14} className={refreshing ? "spin-animation" : ""} />
            <span>{refreshing ? "SYNCING..." : "SYNC NOW"}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderColor: "var(--status-critical)", background: "rgba(239, 68, 68, 0.05)" }}>
          <p style={{ color: "var(--status-critical)", margin: 0, fontSize: "0.9rem" }}>
            ⚠️ <strong>Traffic Ingress Link Error:</strong> {error}
          </p>
        </div>
      )}

      {/* DETAILED TRAFFIC METRIC CARDS */}
      {activeRecord && (
        <div className="dashboard-grid">
          
          {/* Flow Speed Card */}
          <div className="card col-3" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 500 }}>FLOW SPEED</span>
              <Gauge size={20} color="#a78bfa" />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {activeRecord.flow_speed_kmh !== null ? `${activeRecord.flow_speed_kmh} km/h` : "N/A"}
              </span>
            </div>
            <div style={{ width: "100%", background: "rgba(30, 41, 59, 0.3)", height: "4px", borderRadius: "2px" }}>
              <div 
                style={{ 
                  width: `${Math.min(100, ((activeRecord.flow_speed_kmh ?? 0) / (activeRecord.free_flow_speed_kmh ?? 100)) * 100)}%`, 
                  background: "linear-gradient(90deg, #a78bfa, #06b6d4)", 
                  height: "100%", 
                  borderRadius: "2px" 
                }} 
              />
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Reference Free Flow: {activeRecord.free_flow_speed_kmh} km/h
            </span>
          </div>

          {/* Jam Factor Card */}
          <div className="card col-3" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 500 }}>JAM FACTOR</span>
              <AlertTriangle size={20} color="#f59e0b" />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {activeRecord.jam_factor !== null ? activeRecord.jam_factor.toFixed(1) : "N/A"}
              </span>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>/ 10</span>
            </div>
            <div style={{ width: "100%", background: "rgba(30, 41, 59, 0.3)", height: "4px", borderRadius: "2px" }}>
              <div 
                style={{ 
                  width: `${(activeRecord.jam_factor ?? 0) * 10}%`, 
                  background: (activeRecord.jam_factor ?? 0) >= 5.0 ? "var(--status-critical)" : "#f59e0b", 
                  height: "100%", 
                  borderRadius: "2px" 
                }} 
              />
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Congestion: <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>{activeRecord.congestion_level}</span>
            </span>
          </div>

          {/* Travel Time Card */}
          <div className="card col-3" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 500 }}>TRAVEL TIME</span>
              <Clock size={20} color="#06b6d4" />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {activeRecord.travel_time_seconds !== null ? `${Math.round(activeRecord.travel_time_seconds / 60)} mins` : "N/A"}
              </span>
            </div>
            <div style={{ width: "100%", background: "rgba(30, 41, 59, 0.3)", height: "4px", borderRadius: "2px" }}>
              <div 
                style={{ 
                  width: `${Math.min(100, ((activeRecord.travel_time_seconds ?? 0) / 240) * 20)}%`, 
                  background: "#06b6d4", 
                  height: "100%", 
                  borderRadius: "2px" 
                }} 
              />
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Average transit delay calculated live
            </span>
          </div>

          {/* Incident Count Card */}
          <div className="card col-3" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 500 }}>ACTIVE INCIDENTS</span>
              <AlertTriangle size={20} color="#ef4444" />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 700, fontFamily: "var(--font-mono)", color: activeRecord.incident_count && activeRecord.incident_count > 0 ? "var(--status-critical)" : "var(--text-primary)" }}>
                {activeRecord.incident_count !== null ? activeRecord.incident_count : "N/A"}
              </span>
            </div>
            <div style={{ width: "100%", background: "rgba(30, 41, 59, 0.3)", height: "4px", borderRadius: "2px" }}>
              <div 
                style={{ 
                  width: `${(activeRecord.incident_count ?? 0) * 33.3}%`, 
                  background: "var(--status-critical)", 
                  height: "100%", 
                  borderRadius: "2px" 
                }} 
              />
            </div>
            <span style={{ fontSize: "0.75rem", color: activeRecord.incident_count && activeRecord.incident_count > 0 ? "var(--status-critical)" : "var(--text-muted)", fontWeight: activeRecord.incident_count && activeRecord.incident_count > 0 ? 600 : 400 }}>
              {activeRecord.incident_count && activeRecord.incident_count > 0 
                ? "Collisions/Construction Blocking Lanes" 
                : "Free of major obstructions"}
            </span>
          </div>

        </div>
      )}

      {/* TREND CHART AND ACTIVE SENSORS LIST */}
      <div className="dashboard-grid">
        
        {/* Trend Chart (Col 8) */}
        <div 
          className="card col-8" 
          ref={trendContainerRef} 
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
            <h4 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Activity size={16} color="var(--accent-purple)" />
              {getCorridorName(selectedCorridor)} Congestion Analytics
            </h4>

            {/* Parameter selection toggles */}
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {(["flowSpeed", "freeFlowSpeed", "jamFactor", "incidents"] as const).map((param) => {
                const label = param === "flowSpeed" ? "Flow Speed" : param === "freeFlowSpeed" ? "Free-Flow Ref" : param === "jamFactor" ? "Jam Factor" : "Incidents";
                const isActive = visibleSeries[param];
                const activeColor = param === "flowSpeed" ? "var(--accent-purple)" : param === "freeFlowSpeed" ? "#64748b" : param === "jamFactor" ? "#f59e0b" : "#ef4444";
                return (
                  <button
                    key={param}
                    onClick={() => setVisibleSeries(prev => ({ ...prev, [param]: !prev[param] }))}
                    style={{
                      background: isActive ? `rgba(${param === "flowSpeed" ? "167, 139, 250" : param === "freeFlowSpeed" ? "100, 116, 139" : param === "jamFactor" ? "245, 158, 11" : "239, 68, 68"}, 0.12)` : "rgba(30, 41, 59, 0.25)",
                      border: `1px solid ${isActive ? activeColor : "var(--border-card)"}`,
                      color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                      padding: "0.35rem 0.75rem",
                      borderRadius: "6px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.35rem",
                      transition: "var(--transition-smooth)"
                    }}
                  >
                    <span 
                      style={{ 
                        display: "inline-block", 
                        width: "6px", 
                        height: "6px", 
                        borderRadius: "50%", 
                        background: isActive ? activeColor : "transparent",
                        border: `1px solid ${activeColor}`
                      }}
                    />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Plotly line chart */}
          {trends.length === 0 || traces.length === 0 ? (
            <div style={{ height: "380px", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "0.9rem" }}>
              {trends.length === 0 
                ? `No historical trends indexed for ${selectedCorridor} yet.` 
                : "Select at least one active traffic parameter above to overlay."}
            </div>
          ) : (
            <div style={{ width: "100%", overflow: "hidden" }}>
              <Plot
                data={traces}
                layout={{
                  width: chartWidth - 32,
                  height: 380,
                  paper_bgcolor: "transparent",
                  plot_bgcolor: "rgba(30, 41, 59, 0.12)",
                  margin: { l: 50, r: 50, t: 20, b: 60 },
                  showlegend: true,
                  legend: {
                    orientation: "h",
                    y: 1.12,
                    x: 0.5,
                    xanchor: "center",
                    font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 }
                  },
                  xaxis: {
                    type: "date",
                    tickformat: "%I:%M %p",
                    gridcolor: "rgba(71, 85, 105, 0.12)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                    zeroline: false,
                    rangeslider: {
                      visible: true,
                      bgcolor: "rgba(30, 41, 59, 0.25)",
                      bordercolor: "rgba(71, 85, 105, 0.2)",
                      thickness: 0.12
                    }
                  },
                  yaxis: {
                    title: {
                      text: "Flow Velocity (km/h)",
                      font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 }
                    },
                    gridcolor: "rgba(71, 85, 105, 0.12)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                    zeroline: false
                  },
                  yaxis2: {
                    title: {
                      text: "Jam Index (0-10) / Incidents",
                      font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 }
                    },
                    gridcolor: "rgba(71, 85, 105, 0.04)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                    zeroline: false,
                    overlaying: "y",
                    side: "right"
                  },
                  hovermode: "x unified",
                  dragmode: "pan"
                }}
                config={{
                  responsive: true,
                  displayModeBar: true,
                  displaylogo: false,
                  modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d"]
                }}
              />
            </div>
          )}
        </div>

        {/* Monitored Highway Corridors Panel (Col 4) */}
        <div className="card col-4" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <h4>Active Road Corridors</h4>
          <p style={{ color: "var(--text-muted)", fontSize: "0.825rem", margin: 0 }}>
            Highway flow metrics indexed across high-capacity municipal routes.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", overflowY: "auto", flex: 1 }}>
            {currentRecords.map((record) => {
              const isActive = selectedCorridor.toLowerCase() === record.corridor_id.toLowerCase();
              return (
                <div
                  key={record.corridor_id}
                  onClick={() => setSelectedCorridor(record.corridor_id)}
                  style={{
                    background: isActive ? "hsla(265, 89%, 60%, 0.08)" : "rgba(30, 41, 59, 0.15)",
                    border: `1px solid ${isActive ? "var(--accent-purple)" : "var(--border-card)"}`,
                    borderRadius: "10px",
                    padding: "0.85rem",
                    cursor: "pointer",
                    transition: "var(--transition-smooth)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                  }}
                >
                  <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
                    <div 
                      style={{ 
                        background: isActive ? "var(--accent-purple)" : "rgba(30, 41, 59, 0.4)", 
                        borderRadius: "50%", 
                        width: "32px", 
                        height: "32px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center"
                      }}
                    >
                      <MapPin size={16} color={isActive ? "var(--text-primary)" : "var(--text-secondary)"} />
                    </div>

                    <div>
                      <div style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>
                        {getCorridorName(record.corridor_id)}
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {record.corridor_id}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.25rem" }}>
                    <span className={`badge ${getCongestionBadgeClass(record.congestion_level ?? "SAFE")}`}>
                      {record.congestion_level}
                    </span>
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                      {record.flow_speed_kmh !== null ? `${record.flow_speed_kmh} km/h` : "N/A"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>

    </div>
  );
});

export default TrafficStreams;
