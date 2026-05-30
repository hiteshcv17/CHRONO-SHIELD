import React, { useState, useEffect, useMemo } from "react";
import Plot from "react-plotly.js";
import { 
  LineChart, 
  HelpCircle, 
  ArrowRightLeft, 
  Network, 
  LayoutGrid, 
  Sliders, 
  Palette,
  ShieldAlert,
  Clock
} from "lucide-react";
import SkeletonLoader from "../common/SkeletonLoader";
import {
  getCorrelationMatrix,
  getCorrelationGraph,
  getCorrelationOverlays,
  getActivityIntensity,
  getAnomalyConcentration,
  getSynchronizedAnomalies,
  getLagAnalysis,
  GraphNode,
  GraphEdge
} from "../../api/correlation";

// Mapping of internal metric IDs to user-friendly labels including our new social signals
const METRIC_LABELS: Record<string, string> = {
  weather_temp: "Temperature (°C)",
  weather_humidity: "Humidity (%)",
  weather_wind: "Wind Speed (m/s)",
  weather_precip: "Precipitation (mm)",
  traffic_speed: "Traffic Flow Speed (km/h)",
  traffic_jam: "Traffic Jam Factor",
  traffic_incidents: "Traffic Incidents",
  energy_load: "Grid Energy Load (kW)",
  energy_solar: "Solar Output (kW)",
  energy_demand: "Energy Demand (kW)",
  energy_stability: "Grid Stability (%)",
  anomaly_score: "AI Anomaly Score",
  complaints_count: "Complaints Count",
  complaints_urgency: "Mean Complaint Urgency",
  complaints_sentiment: "Mean Complaint Sentiment",
};

export const CorrelationAnalytics: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"network" | "heatmaps">("network");
  const [city, setCity] = useState("New York");
  const [threshold, setThreshold] = useState(0.3);
  const [windowDays, setWindowDays] = useState<number | undefined>(undefined);
  const [colorscale, setColorscale] = useState<"coolwarm" | "viridis" | "hot" | "plasma">("coolwarm");
  const [metricA, setMetricA] = useState<string>("weather_precip");
  const [metricB, setMetricB] = useState<string>("complaints_urgency");

  const [matrixData, setMatrixData] = useState<{ variables: string[]; matrix: number[][] } | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [overlayData, setOverlayData] = useState<{ timestamps: string[]; series: Record<string, (number | null)[]> } | null>(null);
  const [intensityData, setIntensityData] = useState<{ days: string[]; hours: number[]; matrix: number[][] } | null>(null);
  const [concentrationData, setConcentrationData] = useState<{ days: string[]; hours: number[]; matrix: number[][] } | null>(null);
  const [synchronizedAnomalies, setSynchronizedAnomalies] = useState<any[]>([]);
  const [lagAnalysis, setLagAnalysis] = useState<any[]>([]);

  const [parentWidth, setParentWidth] = useState(600);

  // Responsive resizing handler
  useEffect(() => {
    const handleResize = () => {
      const parent = document.getElementById("correlation-chart-container") || document.getElementById("heatmap-analytics-container");
      if (parent) {
        setParentWidth(parent.clientWidth);
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, [loading, activeTab]);

  // Load telemetry data from backend including lag and synchronized failure overlays
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [matrixRes, graphRes, overlayRes, intensityRes, concentrationRes, synRes, lagRes] = await Promise.all([
          getCorrelationMatrix(city, windowDays),
          getCorrelationGraph(city, threshold, windowDays),
          getCorrelationOverlays(city, windowDays),
          getActivityIntensity(city),
          getAnomalyConcentration(city),
          getSynchronizedAnomalies(city),
          getLagAnalysis(city)
        ]);

        if (matrixRes.success) setMatrixData({ variables: matrixRes.variables, matrix: matrixRes.matrix });
        if (graphRes.success) setGraphData({ nodes: graphRes.nodes, edges: graphRes.edges });
        if (overlayRes.success) setOverlayData({ timestamps: overlayRes.timestamps, series: overlayRes.series });
        if (intensityRes.success) setIntensityData({ days: intensityRes.days, hours: intensityRes.hours, matrix: intensityRes.matrix });
        if (concentrationRes.success) setConcentrationData({ days: concentrationRes.days, hours: concentrationRes.hours, matrix: concentrationRes.matrix });
        if (synRes.success) setSynchronizedAnomalies(synRes.anomalies);
        if (lagRes.success) setLagAnalysis(lagRes.relationships);
      } catch (err) {
        console.error("Failed to load correlation data:", err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [city, threshold, windowDays]);

  // Circular layout coordinates generator for relationship graph
  const nodePositions = useMemo(() => {
    if (!graphData) return {};
    const positions: Record<string, { x: number; y: number }> = {};
    const nodes = graphData.nodes;
    const r = 120; // radius of circular layout
    const cx = 175; // center X
    const cy = 175; // center Y

    nodes.forEach((node, idx) => {
      const angle = (idx * 2 * Math.PI) / nodes.length;
      positions[node.id] = {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      };
    });
    return positions;
  }, [graphData]);

  // Group colors mapping for relationship graph - enriched with purple for social complaints
  const groupColors: Record<string, string> = {
    weather: "var(--accent-cyan, #00e5ff)",
    traffic: "var(--accent-blue, #3b82f6)",
    energy: "var(--accent-yellow, #eab308)",
    anomaly: "var(--status-critical, #ef4444)",
    social: "var(--accent-purple, #a855f7)",
  };

  // Pearson Covariance statistics summaries
  const rSquared = useMemo(() => {
    if (!overlayData || !overlayData.series[metricA] || !overlayData.series[metricB]) return 0.0;
    const seriesA = overlayData.series[metricA].map(v => v ?? 0.0);
    const seriesB = overlayData.series[metricB].map(v => v ?? 0.0);
    
    const n = seriesA.length;
    if (n === 0) return 0.0;

    const sumA = seriesA.reduce((a, b) => a + b, 0);
    const sumB = seriesB.reduce((a, b) => a + b, 0);
    const sumA2 = seriesA.reduce((a, b) => a + b * b, 0);
    const sumB2 = seriesB.reduce((a, b) => a + b * b, 0);
    const sumAB = seriesA.reduce((acc, val, i) => acc + val * seriesB[i], 0);

    const num = n * sumAB - sumA * sumB;
    const den = Math.sqrt((n * sumA2 - sumA * sumA) * (n * sumB2 - sumB * sumB));

    if (den === 0.0) return 0.0;
    const r = num / den;
    return r * r; // R-squared
  }, [overlayData, metricA, metricB]);

  // Dynamic colorscale selection for heatmaps
  const selectedColorscale = useMemo(() => {
    switch (colorscale) {
      case "viridis":
        return "Viridis";
      case "hot":
        return "Hot";
      case "plasma":
        return "Plasma";
      case "coolwarm":
      default:
        return [
          [0.0, "#ef4444"], // negative correlation red
          [0.5, "#1e293b"], // neutral slate
          [1.0, "var(--accent-cyan, #00e5ff)"], // positive correlation cyan
        ];
    }
  }, [colorscale]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* View Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h2>Correlation & Dependency Mapping</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Multi-variable correlation metrics inspecting dependency bounds across telemetry channels.
          </p>
        </div>

        {/* Global Controls - Enriched with Rolling Analysis Toggles */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Rolling Analysis Window</span>
            <div style={{ display: "flex", gap: "0.25rem", marginTop: "0.25rem" }}>
              {[
                { label: "All Time", value: undefined },
                { label: "24 Hours", value: 1 },
                { label: "7 Days", value: 7 },
                { label: "30 Days", value: 30 }
              ].map((w) => (
                <button
                  key={w.label}
                  onClick={() => setWindowDays(w.value)}
                  style={{
                    fontSize: "0.7rem",
                    padding: "0.4rem 0.75rem",
                    borderRadius: "4px",
                    border: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))",
                    background: windowDays === w.value ? "var(--accent-cyan, #00e5ff)" : "rgba(30, 41, 59, 0.4)",
                    color: windowDays === w.value ? "#1e293b" : "var(--text-secondary, #94a3b8)",
                    fontWeight: "bold",
                    cursor: "pointer",
                    transition: "var(--transition-smooth)"
                  }}
                >
                  {w.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Target Location</span>
            <select
              className="select-dropdown"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              style={{ marginTop: "0.25rem" }}
            >
              <option value="New York">New York Grid</option>
              <option value="London">London Grid</option>
              <option value="Singapore">Singapore Grid</option>
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Min Correlation Edge ({threshold})</span>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              style={{
                marginTop: "0.5rem",
                width: "120px",
                accentColor: "var(--accent-cyan, #00e5ff)",
                cursor: "pointer",
              }}
            />
          </div>
        </div>
      </div>

      {/* Sub-Tab Navigation */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))", gap: "1.5rem", paddingBottom: "0.5rem" }}>
        <button
          onClick={() => setActiveTab("network")}
          style={{
            background: "none",
            border: "none",
            color: activeTab === "network" ? "var(--accent-cyan, #00e5ff)" : "var(--text-muted)",
            borderBottom: activeTab === "network" ? "2px solid var(--accent-cyan, #00e5ff)" : "none",
            paddingBottom: "0.5rem",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            outline: "none"
          }}
        >
          <Network size={16} />
          Network & Bivariate Overlays
        </button>
        <button
          onClick={() => setActiveTab("heatmaps")}
          style={{
            background: "none",
            border: "none",
            color: activeTab === "heatmaps" ? "var(--accent-cyan, #00e5ff)" : "var(--text-muted)",
            borderBottom: activeTab === "heatmaps" ? "2px solid var(--accent-cyan, #00e5ff)" : "none",
            paddingBottom: "0.5rem",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            outline: "none"
          }}
        >
          <LayoutGrid size={16} />
          Heatmaps & Temporal Grids
        </button>
      </div>

      {loading ? (
        <SkeletonLoader variant="chart" />
      ) : activeTab === "network" ? (
        /* ================= NETWORK & OVERLAYS TAB ================= */
        <div className="dashboard-grid" id="correlation-chart-container">
          
          {/* Scatter Overlay Timeline Plot */}
          <div className="card col-8" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <LineChart size={18} color="var(--accent-cyan, #00e5ff)" />
                Bivariate Overlay Timeline
              </h3>
              
              {/* Double selectors */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <select
                  className="select-dropdown"
                  value={metricA}
                  onChange={(e) => setMetricA(e.target.value)}
                  style={{ fontSize: "0.8rem", padding: "0.25rem 0.5rem" }}
                >
                  {Object.entries(METRIC_LABELS).map(([k, label]) => (
                    <option key={k} value={k}>{label}</option>
                  ))}
                </select>
                <ArrowRightLeft size={14} color="var(--text-muted)" />
                <select
                  className="select-dropdown"
                  value={metricB}
                  onChange={(e) => setMetricB(e.target.value)}
                  style={{ fontSize: "0.8rem", padding: "0.25rem 0.5rem" }}
                >
                  {Object.entries(METRIC_LABELS).map(([k, label]) => (
                    <option key={k} value={k}>{label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ width: "100%", minHeight: "350px" }}>
              {overlayData && (
                <Plot
                  data={[
                    {
                      x: overlayData.timestamps,
                      y: overlayData.series[metricA] || [],
                      type: "scatter",
                      mode: "lines",
                      name: METRIC_LABELS[metricA],
                      line: { color: "var(--accent-cyan, #00e5ff)", width: 2 },
                    },
                    {
                      x: overlayData.timestamps,
                      y: overlayData.series[metricB] || [],
                      type: "scatter",
                      mode: "lines",
                      name: METRIC_LABELS[metricB],
                      yaxis: "y2",
                      line: { color: "var(--accent-purple, #a855f7)", width: 2, dash: "dot" },
                    },
                  ]}
                  layout={{
                    width: parentWidth * 0.63,
                    height: 350,
                    paper_bgcolor: "transparent",
                    plot_bgcolor: "rgba(30, 41, 59, 0.15)",
                    margin: { l: 50, r: 50, t: 30, b: 50 },
                    xaxis: {
                      gridcolor: "rgba(71, 85, 105, 0.15)",
                      tickfont: { color: "#94a3b8", family: "Outfit, sans-serif" },
                      type: "date",
                    },
                    yaxis: {
                      title: {
                        text: METRIC_LABELS[metricA],
                        font: { color: "var(--accent-cyan, #00e5ff)", family: "Outfit, sans-serif", size: 11 },
                      },
                      gridcolor: "rgba(71, 85, 105, 0.15)",
                      tickfont: { color: "var(--accent-cyan, #00e5ff)", family: "Outfit, sans-serif" },
                    },
                    yaxis2: {
                      title: {
                        text: METRIC_LABELS[metricB],
                        font: { color: "var(--accent-purple, #a855f7)", family: "Outfit, sans-serif", size: 11 },
                      },
                      tickfont: { color: "var(--accent-purple, #a855f7)", family: "Outfit, sans-serif" },
                      overlaying: "y",
                      side: "right",
                    },
                    legend: {
                      font: { color: "#94a3b8", family: "Outfit, sans-serif" },
                      orientation: "h",
                      x: 0.05,
                      y: -0.2,
                    },
                    hovermode: "x unified",
                  }}
                  config={{
                    responsive: true,
                    displayModeBar: false,
                  }}
                />
              )}
            </div>
          </div>

          {/* Coefficient of Determination diagnostics */}
          <div className="card col-4" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <h3>Bivariate Diagnostics</h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              Regression analytics matching paired variables.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "0.5rem" }}>
              <div 
                style={{
                  background: "rgba(30, 41, 59, 0.15)",
                  border: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))",
                  padding: "1rem",
                  borderRadius: "10px"
                }}
              >
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Coefficient of Determination (R²)
                </span>
                <h3 style={{ fontSize: "1.75rem", color: "var(--accent-cyan, #00e5ff)", marginTop: "0.25rem" }}>
                  {rSquared.toFixed(3)}
                </h3>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  {rSquared > 0.55 
                    ? "Significant dependency relationship. Outliers in A directly cascade onto B." 
                    : rSquared > 0.25
                    ? "Moderate correlation detected. Systems share soft temporal ties."
                    : "Low linear dependency. Metrics operate on separated micro-channels."}
                </p>
              </div>

              <div 
                style={{
                  background: "rgba(30, 41, 59, 0.15)",
                  border: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))",
                  padding: "1rem",
                  borderRadius: "10px"
                }}
              >
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Pearson Covariance Rating
                </span>
                <h3 style={{ fontSize: "1.75rem", color: "var(--status-safe, #10b981)", marginTop: "0.25rem" }}>
                  {Math.sqrt(rSquared) > 0 ? "+" + Math.sqrt(rSquared).toFixed(3) : "0.000"}
                </h3>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Positive covariance matches typical operational performance states under high stress.
                </p>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-muted)", fontSize: "0.8rem", marginTop: "auto" }}>
              <HelpCircle size={14} />
              <span>Aligned in 10-minute resolution buckets</span>
            </div>
          </div>

          {/* Heatmap Correlation Matrix Plot */}
          <div className="card col-6" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <LayoutGrid size={18} color="var(--accent-cyan, #00e5ff)" />
              Pearson Correlation Matrix
            </h3>
            <div style={{ width: "100%", height: "350px", overflow: "hidden" }}>
              {matrixData && (
                <Plot
                  data={[
                    {
                      x: matrixData.variables.map(v => v.split(" (")[0]),
                      y: matrixData.variables.map(v => v.split(" (")[0]),
                      z: matrixData.matrix,
                      type: "heatmap",
                      colorscale: selectedColorscale,
                      zmin: -1.0,
                      zmax: 1.0,
                      showscale: true,
                    },
                  ]}
                  layout={{
                    width: parentWidth * 0.48,
                    height: 340,
                    paper_bgcolor: "transparent",
                    plot_bgcolor: "transparent",
                    margin: { l: 80, r: 10, t: 20, b: 80 },
                    xaxis: {
                      tickangle: -45,
                      tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                    },
                    yaxis: {
                      tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                    },
                  }}
                  config={{
                    displayModeBar: false,
                  }}
                />
              )}
            </div>
          </div>

          {/* Graph Network Relationship Diagram */}
          <div className="card col-6" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Network size={18} color="var(--accent-cyan, #00e5ff)" />
              Cross-Source Relationship Network
            </h3>
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "350px", background: "rgba(30, 41, 59, 0.15)", borderRadius: "8px", position: "relative" }}>
              <svg width="350" height="350" style={{ border: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))", borderRadius: "8px" }}>
                {/* Edges */}
                {graphData &&
                  graphData.edges.map((edge, idx) => {
                    const fromPos = nodePositions[edge.source];
                    const toPos = nodePositions[edge.target];
                    if (!fromPos || !toPos) return null;
                    return (
                      <line
                        key={`edge-${idx}`}
                        x1={fromPos.x}
                        y1={fromPos.y}
                        x2={toPos.x}
                        y2={toPos.y}
                        stroke={edge.weight > 0 ? "rgba(0, 229, 255, 0.4)" : "rgba(239, 68, 68, 0.4)"}
                        strokeWidth={Math.max(1, Math.abs(edge.weight) * 5)}
                      />
                    );
                  })}

                {/* Nodes */}
                {graphData &&
                  graphData.nodes.map((node) => {
                    const pos = nodePositions[node.id];
                    if (!pos) return null;
                    return (
                      <g key={`node-${node.id}`}>
                        <circle
                          cx={pos.x}
                          cy={pos.y}
                          r="8"
                          fill={groupColors[node.group] || "var(--text-muted)"}
                          stroke="#1e293b"
                          strokeWidth="2"
                        />
                        <text
                          x={pos.x}
                          y={pos.y - 12}
                          textAnchor="middle"
                          fill="#94a3b8"
                          fontSize="8"
                          fontFamily="Outfit, sans-serif"
                        >
                          {node.label.split(" (")[0]}
                        </text>
                      </g>
                    );
                  })}
              </svg>

              {/* Group Legend overlay */}
              <div style={{ position: "absolute", bottom: "10px", left: "10px", display: "flex", gap: "0.5rem", flexWrap: "wrap", fontSize: "0.65rem" }}>
                {Object.entries(groupColors).map(([group, color]) => (
                  <div key={group} style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: color }}></span>
                    <span style={{ color: "#94a3b8", textTransform: "capitalize" }}>{group}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Section: Synchronized Anomalies failure cascades */}
          <div className="card col-7" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <ShieldAlert size={18} color="var(--status-critical, #ef4444)" />
              Anomaly Linkage & Failure Cascades
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
              Chronological listing of synchronized anomaly events across weather, traffic, and complaints.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", overflowY: "auto", maxHeight: "350px", paddingRight: "0.5rem" }}>
              {synchronizedAnomalies.length === 0 ? (
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "2rem" }}>
                  No concurrent cross-source anomaly spikes logged in this window.
                </p>
              ) : (
                synchronizedAnomalies.map((anom, idx) => (
                  <div key={anom.id || idx} style={{
                    background: "var(--bg-deep)",
                    border: "1px solid var(--border-card)",
                    padding: "1rem",
                    borderRadius: "8px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.5rem",
                    borderLeft: `4px solid ${anom.severity === "HIGH" ? "var(--status-critical)" : "var(--status-warning)"}`
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                        <Clock size={12} /> {new Date(anom.timestamp).toLocaleString()}
                      </span>
                      <span style={{
                        fontSize: "0.65rem",
                        fontWeight: "bold",
                        background: anom.severity === "HIGH" ? "rgba(239, 68, 68, 0.1)" : "rgba(245, 158, 11, 0.1)",
                        color: anom.severity === "HIGH" ? "var(--status-critical)" : "var(--status-warning)",
                        padding: "0.1rem 0.4rem",
                        borderRadius: "4px",
                        border: `1px solid ${anom.severity === "HIGH" ? "var(--status-critical)" : "var(--status-warning)"}`
                      }}>{anom.severity} SEVERITY</span>
                    </div>

                    <p style={{ fontSize: "0.85rem", color: "var(--text-primary)", fontWeight: 500, margin: 0 }}>
                      {anom.description}
                    </p>

                    <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", fontSize: "0.7rem", color: "var(--text-muted)", background: "rgba(255, 255, 255, 0.02)", padding: "0.4rem 0.6rem", borderRadius: "4px" }}>
                      {Object.entries(anom.metrics).map(([key, val]) => (
                        <span key={key}>
                          <strong>{METRIC_LABELS[key] || key}</strong>: <code style={{ color: "var(--accent-cyan)" }}>{val as React.ReactNode}</code>
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Section: Lag Cascade relationships */}
          <div className="card col-5" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <ArrowRightLeft size={18} color="var(--accent-cyan, #00e5ff)" />
              Temporal Lag & Cascade Analysis
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
              Peak cross-correlation shifts mapping leading and lagging propagation directions.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", overflowY: "auto", maxHeight: "350px" }}>
              {lagAnalysis.length === 0 ? (
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "2rem" }}>
                  Computing cascade lag coefficients...
                </p>
              ) : (
                lagAnalysis.map((lag, idx) => (
                  <div key={idx} style={{
                    background: "rgba(30, 41, 59, 0.15)",
                    border: "1px solid var(--border-card)",
                    padding: "0.85rem 1rem",
                    borderRadius: "8px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.35rem"
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "0.85rem", fontWeight: "bold", color: "var(--text-primary)" }}>
                        {lag.metric_a} → {lag.metric_b}
                      </span>
                      <span style={{
                        fontSize: "0.75rem",
                        color: "var(--accent-cyan)",
                        fontWeight: "bold"
                      }}>
                        {lag.lag_minutes > 0 ? `+${lag.lag_minutes} min lag` : `${lag.lag_minutes} min lag`}
                      </span>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      <span>Peak Correlation (Pearson r):</span>
                      <span style={{ fontWeight: "bold", color: "var(--status-safe)" }}>
                        r = {lag.correlation.toFixed(2)}
                      </span>
                    </div>

                    <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.4, margin: "0.25rem 0 0 0" }}>
                      {lag.description}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      ) : (
        /* ================= HEATMAPS & TEMPORAL GRIDS TAB ================= */
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }} id="heatmap-analytics-container">
          
          {/* Colorscale Theme Toggles Bar */}
          <div 
            style={{ 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "space-between", 
              padding: "1rem", 
              background: "rgba(30, 41, 59, 0.15)", 
              border: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))", 
              borderRadius: "8px",
              flexWrap: "wrap",
              gap: "1rem"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Palette size={16} color="var(--accent-cyan, #00e5ff)" />
              <span style={{ fontSize: "0.85rem", fontWeight: "bold" }}>Heatmap Color Theme</span>
            </div>
            
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {[
                { id: "coolwarm", label: "Cool-to-Warm" },
                { id: "viridis", label: "Viridis" },
                { id: "hot", label: "Hot" },
                { id: "plasma", label: "Plasma" }
              ].map((theme) => (
                <button
                  key={theme.id}
                  onClick={() => setColorscale(theme.id as any)}
                  style={{
                    fontSize: "0.75rem",
                    padding: "0.4rem 0.8rem",
                    borderRadius: "6px",
                    border: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))",
                    background: colorscale === theme.id ? "var(--accent-cyan, #00e5ff)" : "rgba(30, 41, 59, 0.4)",
                    color: colorscale === theme.id ? "#1e293b" : "var(--text-secondary, #94a3b8)",
                    fontWeight: "bold",
                    cursor: "pointer",
                    transition: "all 0.2s ease"
                  }}
                >
                  {theme.label}
                </button>
              ))}
            </div>
          </div>

          <div className="dashboard-grid">
            
            {/* 1. Pearson Correlation Heatmap */}
            <div className="card col-12" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <LayoutGrid size={18} color="var(--accent-cyan, #00e5ff)" />
                Bivariate Correlation Map (Hover for Analytics)
              </h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
                Hover cells to view exact statistical covariance bounds between key telemetry vectors.
              </p>
              
              <div style={{ width: "100%", height: "380px" }}>
                {matrixData && (
                  <Plot
                    data={[
                      {
                        x: matrixData.variables.map(v => v.split(" (")[0]),
                        y: matrixData.variables.map(v => v.split(" (")[0]),
                        z: matrixData.matrix,
                        type: "heatmap",
                        colorscale: selectedColorscale,
                        zmin: -1.0,
                        zmax: 1.0,
                        showscale: true,
                        hovertemplate: 
                          "<b>Variable A</b>: %{y}<br>" +
                          "<b>Variable B</b>: %{x}<br>" +
                          "<b>Pearson r</b>: %{z:.3f}<br>" +
                          "<b>Status</b>: %{text}<extra></extra>",
                        text: matrixData.matrix.map((row) =>
                          row.map((val) => {
                            if (Math.abs(val) >= 0.7) return "High Covariance (System Cascade Hazard)";
                            if (Math.abs(val) >= 0.3) return "Moderate Dependency (Correlated Channel)";
                            return "Low Dependency (Micro-Channel Variance)";
                          })
                        ),
                      },
                    ]}
                    layout={{
                      width: parentWidth - 32,
                      height: 380,
                      paper_bgcolor: "transparent",
                      plot_bgcolor: "transparent",
                      margin: { l: 150, r: 20, t: 20, b: 120 },
                      xaxis: {
                        tickangle: -45,
                        tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                        gridcolor: "rgba(71, 85, 105, 0.1)"
                      },
                      yaxis: {
                        tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                        gridcolor: "rgba(71, 85, 105, 0.1)"
                      },
                    }}
                    config={{
                      responsive: true,
                      displayModeBar: false,
                    }}
                  />
                )}
              </div>
            </div>

            {/* 2. Activity Intensity Heatmap */}
            <div className="card col-6" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Sliders size={18} color="var(--accent-yellow, #eab308)" />
                24x7 Infrastructure Activity Intensity
              </h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
                Identifies peak temporal congestion and load patterns (Day of Week vs Hour).
              </p>
              
              <div style={{ width: "100%", height: "350px" }}>
                {intensityData && (
                  <Plot
                    data={[
                      {
                        x: intensityData.hours.map(h => `${h.toString().padStart(2, "0")}:00`),
                        y: intensityData.days,
                        z: intensityData.matrix,
                        type: "heatmap",
                        colorscale: selectedColorscale,
                        zmin: 0.0,
                        zmax: 1.0,
                        showscale: true,
                        hovertemplate: 
                          "<b>Day</b>: %{y}<br>" +
                          "<b>Time</b>: %{x}<br>" +
                          "<b>Intensity</b>: %{z:.1%}<br>" +
                          "<b>Status</b>: %{text}<extra></extra>",
                        text: intensityData.matrix.map((row) =>
                          row.map((val) => {
                            if (val >= 0.75) return "Rush Hour Peak / Maximum Congestion";
                            if (val >= 0.5) return "Moderate Operational Loading";
                            return "Low Activity / Operational Slump";
                          })
                        ),
                      },
                    ]}
                    layout={{
                      width: parentWidth * 0.48,
                      height: 330,
                      paper_bgcolor: "transparent",
                      plot_bgcolor: "transparent",
                      margin: { l: 80, r: 10, t: 20, b: 60 },
                      xaxis: {
                        tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                        gridcolor: "rgba(71, 85, 105, 0.1)"
                      },
                      yaxis: {
                        tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                        gridcolor: "rgba(71, 85, 105, 0.1)"
                      },
                    }}
                    config={{
                      responsive: true,
                      displayModeBar: false,
                    }}
                  />
                )}
              </div>
            </div>

            {/* 3. Anomaly Concentration Hotspots */}
            <div className="card col-6" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Sliders size={18} color="var(--status-critical, #ef4444)" />
                24x7 Anomaly Threat Concentration
              </h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
                Displays frequency hotzones to target preventative maintenance scheduling windows.
              </p>
              
              <div style={{ width: "100%", height: "350px" }}>
                {concentrationData && (
                  <Plot
                    data={[
                      {
                        x: concentrationData.hours.map(h => `${h.toString().padStart(2, "0")}:00`),
                        y: concentrationData.days,
                        z: concentrationData.matrix,
                        type: "heatmap",
                        colorscale: colorscale === "coolwarm" ? "Hot" : selectedColorscale,
                        zmin: 0,
                        showscale: true,
                        hovertemplate: 
                          "<b>Day</b>: %{y}<br>" +
                          "<b>Time</b>: %{x}<br>" +
                          "<b>Total Threats</b>: %{z} events<br>" +
                          "<b>Threat Window</b>: %{text}<extra></extra>",
                        text: concentrationData.matrix.map((row) =>
                          row.map((val) => {
                            if (val >= 8) return "Critical Concentration (High Alert)";
                            if (val >= 4) return "Elevated Hotspot (Increased Threat)";
                            return "Nominal Threat Activity";
                          })
                        ),
                      },
                    ]}
                    layout={{
                      width: parentWidth * 0.48,
                      height: 330,
                      paper_bgcolor: "transparent",
                      plot_bgcolor: "transparent",
                      margin: { l: 80, r: 10, t: 20, b: 60 },
                      xaxis: {
                        tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                        gridcolor: "rgba(71, 85, 105, 0.1)"
                      },
                      yaxis: {
                        tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                        gridcolor: "rgba(71, 85, 105, 0.1)"
                      },
                    }}
                    config={{
                      responsive: true,
                      displayModeBar: false,
                    }}
                  />
                )}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};

export default CorrelationAnalytics;
