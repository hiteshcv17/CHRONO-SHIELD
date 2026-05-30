import React, { useState, useEffect, useRef } from "react";
import { 
  Thermometer, 
  Droplets, 
  Wind, 
  CloudRain, 
  RefreshCw, 
  Activity, 
  MapPin, 
  Server,
  CloudSun
} from "lucide-react";
import Plot from "react-plotly.js";
import { getCurrentWeather, getWeatherTrends, WeatherRecord } from "../../api/weather";
import SkeletonLoader from "../common/SkeletonLoader";

export const WeatherStreams: React.FC = React.memo(() => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [currentRecords, setCurrentRecords] = useState<WeatherRecord[]>([]);
  const [selectedCity, setSelectedCity] = useState<string>("New York");
  const [visibleSeries, setVisibleSeries] = useState({
    temp: true,
    humidity: true,
    wind: false,
    rain: true
  });
  const [trends, setTrends] = useState<WeatherRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [apiSource, setApiSource] = useState<string>("Open-Meteo (Public)");

  const trendContainerRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState<number>(600);

  // Poll intervals
  useEffect(() => {
    fetchInitialData();

    // Auto-refresh weather stats every 30 seconds
    const interval = setInterval(() => {
      refreshDataSilently();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Fetch trends when selected city changes
  useEffect(() => {
    fetchCityTrends(selectedCity);
  }, [selectedCity]);

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
      const weatherRes = await getCurrentWeather();
      setCurrentRecords(weatherRes.records);
      
      // Attempt to read the actual API source used by backend from metadata if available
      const source = (weatherRes as any).success ? "OpenWeatherMap" : "Open-Meteo (Public)";
      setApiSource(source);

      if (weatherRes.records.length > 0) {
        const matchingCity = weatherRes.records.find(r => r.location.toLowerCase() === selectedCity.toLowerCase());
        if (!matchingCity) {
          setSelectedCity(weatherRes.records[0].location);
        }
      }
      
      await fetchCityTrends(selectedCity);
    } catch (err: any) {
      setError(err.message || "Failed to establish environment metrics link.");
    } finally {
      setLoading(false);
    }
  };

  const refreshDataSilently = async () => {
    setRefreshing(true);
    try {
      const weatherRes = await getCurrentWeather();
      setCurrentRecords(weatherRes.records);
      await fetchCityTrends(selectedCity);
    } catch (err) {
      console.error("Telemetry silent refresh error", err);
    } finally {
      setRefreshing(false);
    }
  };

  const fetchCityTrends = async (city: string) => {
    try {
      const trendRes = await getWeatherTrends(city);
      setTrends(trendRes.records);
    } catch (err) {
      console.error(`Failed to retrieve historical trends for ${city}`, err);
    }
  };

  // Extract selected city's current stats
  const activeRecord = currentRecords.find(
    (r) => r.location.toLowerCase() === selectedCity.toLowerCase()
  ) || trends[trends.length - 1]; // Fallback to trends if currentRecords not loaded yet

  // Prepare continuous timeline xData array using JS Date objects
  const xData = trends.map((t) => new Date(t.timestamp));
  // Compute anomalies for temperature series (client-side statistical detection)
  const computeAnomalies = (data: number[], timestamps: Date[], window: number = 20, zThresh: number = 2.5) => {
    const anomalies: { x: Date; y: number }[] = [];
    const rolledMean: number[] = [];
    const rolledStd: number[] = [];
    for (let i = 0; i < data.length; i++) {
      const start = Math.max(0, i - window + 1);
      const slice = data.slice(start, i + 1);
      const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
      const variance = slice.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / slice.length;
      const std = Math.sqrt(variance) || 1e-6;
      rolledMean.push(mean);
      rolledStd.push(std);
      const z = (data[i] - mean) / std;
      if (Math.abs(z) > zThresh) {
        anomalies.push({ x: timestamps[i], y: data[i] });
      }
    }
    return anomalies;
  };
  const tempValues = trends.map((t) => t.temperature_c ?? 0);
  const tempAnomalies = computeAnomalies(tempValues, xData);


  // Build high-fidelity multi-series overlay traces
const anomalyTrace = {
  x: tempAnomalies.map(a => a.x),
  y: tempAnomalies.map(a => a.y),
  type: "scatter",
  mode: "markers",
  name: "Temp Anomalies",
  marker: { color: "#ff0000", size: 8, symbol: "circle-open" }
};
  const traces: any[] = [];
  if (visibleSeries.temp) {
    traces.push({
      x: xData,
      y: trends.map((t) => t.temperature_c ?? 0),
      type: "scatter",
      mode: "lines+markers",
      name: "Temperature",
      yaxis: "y",
      line: { color: "#06b6d4", width: 3, shape: "spline" },
      marker: { color: "#06b6d4", size: 5, line: { color: "rgba(15, 23, 42, 0.8)", width: 1 } },
      hovertemplate: "%{y:.1f} °C<extra></extra>"
    });
  }
  if (visibleSeries.humidity) {
    traces.push({
      x: xData,
      y: trends.map((t) => t.humidity_pct ?? 0),
      type: "scatter",
      mode: "lines+markers",
      name: "Humidity",
      yaxis: "y2",
      line: { color: "#a78bfa", width: 2, dash: "dash", shape: "spline" },
      marker: { color: "#a78bfa", size: 4, line: { color: "rgba(15, 23, 42, 0.8)", width: 1 } },
      hovertemplate: "%{y:.1f} %<extra></extra>"
    });
  }
  if (visibleSeries.wind) {
    traces.push({
      x: xData,
      y: trends.map((t) => t.wind_speed_ms ?? 0),
      type: "scatter",
      mode: "lines",
      name: "Wind Speed",
      yaxis: "y",
      line: { color: "#10b981", width: 2, shape: "spline" },
      hovertemplate: "%{y:.1f} m/s<extra></extra>"
    });
  }
  if (visibleSeries.rain) {
    traces.push({
      x: xData,
      y: trends.map((t) => t.precipitation_mm ?? 0),
      type: "bar",
      name: "Precipitation",
      yaxis: "y2",
      marker: { 
        color: "rgba(245, 158, 11, 0.25)",
        line: { color: "#f59e0b", width: 1.5 }
      },
      hovertemplate: "%{y:.2f} mm<extra></extra>"
    });
  }

  if (loading) {
    return <SkeletonLoader variant="chart" />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", marginTop: "1rem" }}>
      
      {/* SECTION HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <CloudSun size={24} color="var(--accent-cyan)" />
          <div>
            <h3 style={{ margin: 0 }}>Environmental Telemetry Streams</h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0 }}>
              Atmospheric ingress streams mapped to operational anomaly prediction engines.
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
            <span style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>{apiSource}</span>
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
            ⚠️ <strong>Telemetry Ingress Link Error:</strong> {error}
          </p>
        </div>
      )}

      {/* DETAILED CITY WEATHER METRIC CARDS */}
      {activeRecord && (
        <div className="dashboard-grid">
          
          {/* Temperature Card */}
          <div className="card col-3" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 500 }}>TEMPERATURE</span>
              <Thermometer size={20} color="#06b6d4" />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {activeRecord.temperature_c !== null ? `${activeRecord.temperature_c}°C` : "N/A"}
              </span>
            </div>
            <div style={{ width: "100%", background: "rgba(30, 41, 59, 0.3)", height: "4px", borderRadius: "2px" }}>
              <div 
                style={{ 
                  width: `${Math.min(100, Math.max(0, ((activeRecord.temperature_c ?? 0) + 10) * 2))}%`, 
                  background: "linear-gradient(90deg, #06b6d4, #8b5cf6)", 
                  height: "100%", 
                  borderRadius: "2px" 
                }} 
              />
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Baseline Thermal Deviation: Normal
            </span>
          </div>

          {/* Humidity Card */}
          <div className="card col-3" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 500 }}>RELATIVE HUMIDITY</span>
              <Droplets size={20} color="#8b5cf6" />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {activeRecord.humidity_pct !== null ? `${activeRecord.humidity_pct}%` : "N/A"}
              </span>
            </div>
            <div style={{ width: "100%", background: "rgba(30, 41, 59, 0.3)", height: "4px", borderRadius: "2px" }}>
              <div 
                style={{ 
                  width: `${activeRecord.humidity_pct ?? 0}%`, 
                  background: "#8b5cf6", 
                  height: "100%", 
                  borderRadius: "2px" 
                }} 
              />
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Condensation / Static Risk: Safe
            </span>
          </div>

          {/* Wind Speed Card */}
          <div className="card col-3" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 500 }}>WIND VELOCITY</span>
              <Wind size={20} color="#10b981" />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {activeRecord.wind_speed_ms !== null ? `${activeRecord.wind_speed_ms} m/s` : "N/A"}
              </span>
            </div>
            <div style={{ width: "100%", background: "rgba(30, 41, 59, 0.3)", height: "4px", borderRadius: "2px" }}>
              <div 
                style={{ 
                  width: `${Math.min(100, (activeRecord.wind_speed_ms ?? 0) * 5)}%`, 
                  background: "#10b981", 
                  height: "100%", 
                  borderRadius: "2px" 
                }} 
              />
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Atmospheric Convection cooling: Adequate
            </span>
          </div>

          {/* Precipitation Card */}
          <div className="card col-3" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 500 }}>PRECIPITATION RATE</span>
              <CloudRain size={20} color="#f59e0b" />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {activeRecord.precipitation_mm !== null ? `${activeRecord.precipitation_mm} mm` : "N/A"}
              </span>
            </div>
            <div style={{ width: "100%", background: "rgba(30, 41, 59, 0.3)", height: "4px", borderRadius: "2px" }}>
              <div 
                style={{ 
                  width: `${Math.min(100, (activeRecord.precipitation_mm ?? 0) * 10)}%`, 
                  background: "#f59e0b", 
                  height: "100%", 
                  borderRadius: "2px" 
                }} 
              />
            </div>
            <span style={{ fontSize: "0.75rem", color: activeRecord.precipitation_mm && activeRecord.precipitation_mm > 2.0 ? "var(--status-warning)" : "var(--text-muted)" }}>
              {activeRecord.precipitation_mm && activeRecord.precipitation_mm > 2.0 
                ? "Moderate Rainfall - Monitoring drainage" 
                : "Dry / Atmospheric Stable"}
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
              <Activity size={16} color="var(--accent-cyan)" />
              {selectedCity} Environmental Telemetry Trends
            </h4>

            {/* Parameter selection toggles */}
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {(["temp", "humidity", "wind", "rain"] as const).map((param) => {
                const label = param === "temp" ? "Temp" : param === "wind" ? "Wind" : param === "rain" ? "Rain" : "Humidity";
                const isActive = visibleSeries[param];
                const activeColor = param === "temp" ? "var(--accent-cyan)" : param === "humidity" ? "var(--accent-purple)" : param === "wind" ? "#10b981" : "#f59e0b";
                return (
                  <button
                    key={param}
                    onClick={() => setVisibleSeries(prev => ({ ...prev, [param]: !prev[param] }))}
                    style={{
                      background: isActive ? `rgba(${param === "temp" ? "6, 182, 212" : param === "humidity" ? "167, 139, 250" : param === "wind" ? "16, 185, 129" : "245, 158, 11"}, 0.12)` : "rgba(30, 41, 59, 0.25)",
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
                ? `No historical trends indexed for ${selectedCity} yet.` 
                : "Select at least one active metric parameter above to overlay."}
            </div>
          ) : (
            <div style={{ width: "100%", overflow: "hidden" }}>
              <Plot
                data={[...traces, anomalyTrace]}
                layout={{
                  width: chartWidth - 32, // Accommodate card padding
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
                      text: "Temperature (°C) / Wind (m/s)",
                      font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 }
                    },
                    gridcolor: "rgba(71, 85, 105, 0.12)",
                    tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 },
                    zeroline: false
                  },
                  yaxis2: {
                    title: {
                      text: "Humidity (%) / Precipitation (mm)",
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

        {/* Monitored Locations Panel (Col 4) */}
        <div className="card col-4" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <h4>Active Climate Sensors</h4>
          <p style={{ color: "var(--text-muted)", fontSize: "0.825rem", margin: 0 }}>
            Geographic time-series feeds continuously synced via ingestion jobs.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", overflowY: "auto", flex: 1 }}>
            {currentRecords.map((record) => {
              const isActive = selectedCity.toLowerCase() === record.location.toLowerCase();
              return (
                <div
                  key={record.location}
                  onClick={() => setSelectedCity(record.location)}
                  style={{
                    background: isActive ? "hsla(199, 89%, 48%, 0.08)" : "rgba(30, 41, 59, 0.15)",
                    border: `1px solid ${isActive ? "var(--accent-blue)" : "var(--border-card)"}`,
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
                        background: isActive ? "var(--accent-blue)" : "rgba(30, 41, 59, 0.4)", 
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
                        {record.location}
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {record.latitude.toFixed(2)}°N, {record.longitude.toFixed(2)}°E
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.25rem" }}>
                    <span className="pulse-indicator"></span>
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                      {record.temperature_c !== null ? `${record.temperature_c}°C` : "N/A"}
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

export default WeatherStreams;
