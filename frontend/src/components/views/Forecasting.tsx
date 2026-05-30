import React, { useState, useEffect } from "react";
import Plot from "react-plotly.js";
import { TrendingUp, Clock, AlertTriangle, ArrowRight, Brain, Calendar, ShieldCheck, MapPin, Sliders } from "lucide-react";
import SkeletonLoader from "../common/SkeletonLoader";
import { getTelemetryForecast, ForecastRecord, PredictedAnomaly, ExplainableForecasting } from "../../api/forecasting";

// User-friendly metric mapping
const FORECAST_METRICS = [
  { id: "energy_demand", label: "Energy Grid Demand (kW)" },
  { id: "traffic_jam", label: "Traffic Jam Factor" },
  { id: "anomaly_score", label: "AI Anomaly Score" },
  { id: "weather_temp", label: "Temperature (°C)" }
];

export const Forecasting: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [horizon, setHorizon] = useState<number>(24); // Hours
  const [metricId, setMetricId] = useState<string>("energy_demand");
  const [city, setCity] = useState<string>("New York");

  const [records, setRecords] = useState<ForecastRecord[]>([]);
  const [predictedAnomalies, setPredictedAnomalies] = useState<PredictedAnomaly[]>([]);
  const [explanation, setExplanation] = useState<ExplainableForecasting | null>(null);
  const [metricName, setMetricName] = useState<string>("Energy Grid Demand (kW)");

  const [parentWidth, setParentWidth] = useState(600);

  // Responsive resizing handler
  useEffect(() => {
    const handleResize = () => {
      const parent = document.getElementById("forecast-chart-container");
      if (parent) {
        setParentWidth(parent.clientWidth);
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, [loading]);

  // Load telemetry forecast from backend
  useEffect(() => {
    const loadForecast = async () => {
      setLoading(true);
      try {
        const res = await getTelemetryForecast(metricId, horizon, city);
        if (res.success) {
          setRecords(res.records);
          setPredictedAnomalies(res.predicted_anomalies);
          setExplanation(res.explanation);
          setMetricName(res.metric_name);
        }
      } catch (err) {
        console.error("Failed to load telemetry forecast:", err);
      } finally {
        setLoading(false);
      }
    };
    loadForecast();
  }, [metricId, horizon, city]);

  // Extract aligned plotting vectors
  const plotVectors = React.useMemo(() => {
    const times: string[] = [];
    const historicalValues: (number | null)[] = [];
    const forecastMean: (number | null)[] = [];
    const forecastUpper: (number | null)[] = [];
    const forecastLower: (number | null)[] = [];

    records.forEach((r) => {
      const dt = new Date(r.timestamp);
      // Format dynamically based on horizon: show date + time if multi-day
      const label = horizon <= 24
        ? dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : dt.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

      times.push(label);
      historicalValues.push(r.actual);
      forecastMean.push(r.is_forecast || r.actual === null ? r.forecast : null);
      forecastUpper.push(r.is_forecast || r.actual === null ? r.upper_bound : null);
      forecastLower.push(r.is_forecast || r.actual === null ? r.lower_bound : null);
    });

    // Provide a bridging connection point between actuals and forecasts
    const lastHistIdx = historicalValues.map((v, i) => v !== null ? i : -1).reduce((a, b) => Math.max(a, b), -1);
    if (lastHistIdx !== -1 && lastHistIdx < forecastMean.length) {
      forecastMean[lastHistIdx] = historicalValues[lastHistIdx];
      forecastUpper[lastHistIdx] = historicalValues[lastHistIdx];
      forecastLower[lastHistIdx] = historicalValues[lastHistIdx];
    }

    return { times, historicalValues, forecastMean, forecastUpper, forecastLower };
  }, [records, horizon]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* View Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h2>Predictive Telemetry Forecasting</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Neural sequence forecasting mapping infrastructure pathways and warning metrics via Prophet models.
          </p>
        </div>

        {/* Global Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>Target City</span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <MapPin size={14} color="var(--accent-cyan)" />
              <select
                className="select-dropdown"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                style={{ fontSize: "0.85rem", padding: "0.25rem 0.5rem" }}
              >
                <option value="New York">New York</option>
                <option value="London">London</option>
                <option value="Singapore">Singapore</option>
              </select>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>Telemetry Metric</span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <Sliders size={14} color="var(--accent-cyan)" />
              <select
                className="select-dropdown"
                value={metricId}
                onChange={(e) => setMetricId(e.target.value)}
                style={{ fontSize: "0.85rem", padding: "0.25rem 0.5rem" }}
              >
                {FORECAST_METRICS.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>Prediction Horizon</span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <Clock size={14} color="var(--accent-cyan)" />
              <select
                className="select-dropdown"
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
                style={{ fontSize: "0.85rem", padding: "0.25rem 0.5rem" }}
              >
                <option value={24}>Next 24 Hours</option>
                <option value={168}>Next 7 Days</option>
                <option value={720}>Next 30 Days</option>
              </select>
            </div>
          </div>

        </div>
      </div>

      {loading ? (
        <SkeletonLoader variant="chart" />
      ) : (
        <div className="dashboard-grid">
          {/* Main Confidence Plot */}
          <div className="card col-8" id="forecast-chart-container" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <TrendingUp size={18} color="var(--accent-cyan, #00e5ff)" />
                {metricName} Forecast Pathway
              </h3>
              <span className="badge badge-safe" style={{ fontSize: "0.75rem" }}>
                Confidence Interval: 95%
              </span>
            </div>

            <div style={{ width: "100%", minHeight: "350px" }}>
              <Plot
                data={[
                  // 1. Historical Path
                  {
                    x: plotVectors.times,
                    y: plotVectors.historicalValues,
                    type: "scatter",
                    mode: "lines",
                    name: "Historical Actuals",
                    line: { color: "var(--status-safe, #10b981)", width: 2 }
                  },
                  // 2. Shaded Confidence Envelope - Lower Bound
                  {
                    x: plotVectors.times,
                    y: plotVectors.forecastLower,
                    type: "scatter",
                    mode: "lines",
                    name: "Lower Bound (95%)",
                    line: { width: 0 },
                    showlegend: false
                  },
                  // 3. Shaded Confidence Envelope - Upper Bound
                  {
                    x: plotVectors.times,
                    y: plotVectors.forecastUpper,
                    type: "scatter",
                    mode: "lines",
                    name: "AI Confidence Envelope (95%)",
                    fill: "tonexty",
                    fillcolor: "rgba(168, 85, 247, 0.08)", // lavender envelope
                    line: { width: 0 }
                  },
                  // 4. Forecasted Mean Line
                  {
                    x: plotVectors.times,
                    y: plotVectors.forecastMean,
                    type: "scatter",
                    mode: "lines",
                    name: "Prophet Expected Path",
                    line: { color: "var(--accent-purple, #a855f7)", width: 2, dash: "dot" }
                  }
                ]}
                layout={{
                  width: parentWidth - 32,
                  height: 350,
                  transition: {
                    duration: 400,
                    easing: "cubic-in-out"
                  },
                  frame: {
                    duration: 400
                  },
                  paper_bgcolor: "transparent",
                  plot_bgcolor: "rgba(30, 41, 59, 0.15)",
                  margin: { l: 50, r: 20, t: 30, b: 50 },
                  xaxis: {
                    gridcolor: "rgba(71, 85, 105, 0.12)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                    zeroline: false
                  },
                  yaxis: {
                    gridcolor: "rgba(71, 85, 105, 0.12)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif" },
                    zeroline: false
                  },
                  legend: {
                    font: { color: "#94a3b8", family: "Outfit, sans-serif" },
                    orientation: "h",
                    x: 0.05,
                    y: -0.25
                  },
                  hovermode: "x unified",
                  dragmode: "pan"
                }}
                config={{
                  responsive: true,
                  displayModeBar: false
                }}
              />
            </div>
          </div>

          {/* Explainable Forecasting Insights & Future Anomalies */}
          <div className="card col-4" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            
            {/* 1. Explainable AI Insights Block */}
            <div>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1.1rem" }}>
                <Brain size={18} color="var(--accent-cyan, #00e5ff)" />
                Explainable AI Insights
              </h3>
              {explanation ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "0.75rem" }}>
                  <div style={{ background: "rgba(30, 41, 59, 0.2)", border: "1px solid var(--border-card, rgba(255,255,255,0.08))", padding: "0.75rem", borderRadius: "8px" }}>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "bold" }}>
                      Trend Vector Model
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "var(--accent-cyan, #00e5ff)", marginTop: "0.25rem", fontWeight: "bold" }}>
                      {explanation.trend_direction.replace("_", " ")}
                    </div>
                    <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem", lineHeight: "1.3" }}>
                      {explanation.trend_summary}
                    </p>
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <div style={{ flex: 1, background: "rgba(30, 41, 59, 0.2)", border: "1px solid var(--border-card, rgba(255,255,255,0.08))", padding: "0.5rem", borderRadius: "8px" }}>
                      <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", display: "block" }}>Peak Weekday</span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-primary)", fontWeight: "bold", display: "flex", alignItems: "center", gap: "0.25rem", marginTop: "0.15rem" }}>
                        <Calendar size={12} color="var(--accent-yellow, #eab308)" />
                        {explanation.peak_day_of_week}
                      </span>
                    </div>

                    <div style={{ flex: 1, background: "rgba(30, 41, 59, 0.2)", border: "1px solid var(--border-card, rgba(255,255,255,0.08))", padding: "0.5rem", borderRadius: "8px" }}>
                      <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", display: "block" }}>Peak Hour</span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-primary)", fontWeight: "bold", display: "flex", alignItems: "center", gap: "0.25rem", marginTop: "0.15rem" }}>
                        <Clock size={12} color="var(--accent-yellow, #eab308)" />
                        {explanation.peak_hour_of_day.toString().padStart(2, "0")}:00
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Loading explanation...</p>
              )}
            </div>

            {/* 2. Predicted Future Anomalies Block */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", borderTop: "1px solid var(--border-card, rgba(255,255,255,0.08))", paddingTop: "1rem" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1.1rem" }}>
                <AlertTriangle size={18} color="var(--status-critical, #ef4444)" />
                Forecasted Future Anomalies
              </h3>
              
              <div 
                style={{ 
                  maxHeight: "180px", 
                  overflowY: "auto", 
                  display: "flex", 
                  flexDirection: "column", 
                  gap: "0.5rem",
                  paddingRight: "0.25rem"
                }}
              >
                {predictedAnomalies.length > 0 ? (
                  predictedAnomalies.map((anom, idx) => (
                    <div 
                      key={`future-anom-${idx}`}
                      style={{
                        background: "rgba(239, 68, 68, 0.05)",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                        padding: "0.75rem",
                        borderRadius: "8px",
                        display: "flex",
                        gap: "0.5rem",
                        alignItems: "flex-start"
                      }}
                    >
                      <AlertTriangle size={14} color="var(--status-critical, #ef4444)" style={{ flexShrink: 0, marginTop: "0.1rem" }} />
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--status-critical, #ef4444)", fontWeight: "bold" }}>
                            {anom.severity} Alert
                          </span>
                          <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>
                            {new Date(anom.timestamp).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </div>
                        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.25rem", lineHeight: "1.3" }}>
                          {anom.description} Peak: <span style={{ fontWeight: "bold", color: "var(--text-primary)" }}>{anom.predicted_value}</span>
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div 
                    style={{
                      background: "rgba(16, 185, 129, 0.05)",
                      border: "1px solid rgba(16, 185, 129, 0.2)",
                      padding: "0.75rem",
                      borderRadius: "8px",
                      display: "flex",
                      gap: "0.5rem",
                      alignItems: "center"
                    }}
                  >
                    <ShieldCheck size={16} color="var(--status-safe, #10b981)" style={{ flexShrink: 0 }} />
                    <span style={{ fontSize: "0.8rem", color: "var(--status-safe, #10b981)" }}>
                      Nominal loading projected. No anomaly threats anticipated.
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Action provision */}
            <button 
              className="btn-primary" 
              style={{ width: "100%", justifyContent: "center", marginTop: "auto" }}
              disabled={predictedAnomalies.length === 0}
              onClick={() => alert(`Pre-emptive provisioning task successfully scheduled for grid load peaks!`)}
            >
              <span>Schedule Autoscaling Provision</span>
              <ArrowRight size={16} />
            </button>
          </div>

        </div>
      )}
    </div>
  );
};

export default Forecasting;
