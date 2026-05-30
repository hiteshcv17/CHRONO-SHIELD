import React, { useState, useEffect, useRef } from "react";
import { Activity, Play, Square, Settings, RefreshCw } from "lucide-react";
import PlotlyChart from "../common/PlotlyChart";
import SkeletonLoader from "../common/SkeletonLoader";
import WeatherStreams from "./WeatherStreams";
import TrafficStreams from "./TrafficStreams";

interface LogEntry {
  timestamp: string;
  metric: string;
  value: number;
  status: "safe" | "warning";
}

export const LiveMonitoring: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [isLive, setIsLive] = useState(true);
  const [metricType, setMetricType] = useState<"CPU_Usage" | "Memory_Usage" | "Network_Throughput">("CPU_Usage");
  
  // Real-time sliding sequences state
  const [xData, setXData] = useState<string[]>([]);
  const [yData, setYData] = useState<number[]>([]);
  const [anomalies, setAnomalies] = useState<number[]>([]);
  const [eventLogs, setEventLogs] = useState<LogEntry[]>([]);
  
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Initialize baseline logs
  useEffect(() => {
    setLoading(true);
    const times: string[] = [];
    const values: number[] = [];
    const logs: LogEntry[] = [];
    const baseTime = new Date();

    for (let i = 40; i >= 0; i--) {
      const t = new Date(baseTime.getTime() - i * 5000); // 5 sec increments
      const timeStr = t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      times.push(timeStr);
      
      const v = Number((30 + Math.random() * 20).toFixed(1));
      values.push(v);

      if (i % 15 === 0 && i !== 0) {
        logs.unshift({
          timestamp: timeStr,
          metric: metricType,
          value: v,
          status: "warning"
        });
      }
    }

    setXData(times);
    setYData(values);
    setEventLogs(logs);
    
    // Outliers are indexes matching warning logs
    setAnomalies([10, 25]);
    
    setLoading(false);
  }, [metricType]);

  // Live telemetry appending simulation
  useEffect(() => {
    if (isLive) {
      timerRef.current = setInterval(() => {
        const nextTime = new Date();
        const timeStr = nextTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        // Generate random baseline noise or occasional spike
        const isSpike = Math.random() > 0.88;
        const nextValue = isSpike 
          ? Number((80 + Math.random() * 15).toFixed(1)) 
          : Number((30 + Math.random() * 20).toFixed(1));

        setXData((prev) => [...prev.slice(1), timeStr]);
        setYData((prev) => [...prev.slice(1), nextValue]);

        // Add anomaly trigger if spike
        if (isSpike) {
          setAnomalies((prev) => [...prev.map(idx => idx - 1).filter(idx => idx >= 0), 40]);
          setEventLogs((prev) => [
            {
              timestamp: timeStr,
              metric: metricType,
              value: nextValue,
              status: "warning"
            },
            ...prev.slice(0, 8)
          ]);
        } else {
          setAnomalies((prev) => prev.map(idx => idx - 1).filter(idx => idx >= 0));
        }
      }, 3000); // Poll metrics every 3s
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isLive, metricType]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Top action layout */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2>Live Stream Telemetry</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Sliding metric feeds evaluated in real-time by model hyperplanes.
          </p>
        </div>
        
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {/* Metric selector */}
          <select 
            className="select-dropdown"
            value={metricType}
            onChange={(e) => setMetricType(e.target.value as any)}
          >
            <option value="CPU_Usage">CPU Core Utilization</option>
            <option value="Memory_Usage">Memory Heap Saturation</option>
            <option value="Network_Throughput">Network Interface Bandwidth</option>
          </select>

          {/* Live Switch */}
          <div className="switch-container" onClick={() => setIsLive(!isLive)}>
            <div className={`switch ${isLive ? "active" : ""}`} />
            <span>{isLive ? "LIVE POLLING ACTIVE" : "STREAM PAUSED"}</span>
          </div>
        </div>
      </div>

      {loading ? (
        <SkeletonLoader variant="chart" />
      ) : (
        <div className="dashboard-grid">
          {/* Master Telemetry Graph */}
          <div className="card col-8" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Activity size={18} color="var(--accent-cyan)" />
                Dynamic Time-Series Analytics
              </h3>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                <span className="pulse-indicator"></span>
                <span>Receiving sequences at 5s resolution</span>
              </div>
            </div>

            <PlotlyChart
              xData={xData}
              yData={yData}
              anomalyIndices={anomalies}
              title={`Real-Time Ingestion Loop: ${metricType.replace("_", " ")}`}
              yLabel="Operational Metrics Unit"
              metricColor="#10b981"
            />
          </div>

          {/* Side Logs Feed */}
          <div className="card col-4" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <h3>Telemetry Incident Log</h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              Real-time spikes matching out-of-bounds anomaly signals.
            </p>
            
            <div 
              style={{ 
                display: "flex", 
                flexDirection: "column", 
                gap: "0.75rem", 
                height: "320px", 
                overflowY: "auto",
                paddingRight: "0.5rem"
              }}
            >
              {eventLogs.length === 0 ? (
                <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  No high-reconstruction incidents detected.
                </div>
              ) : (
                eventLogs.map((log, i) => (
                  <div 
                    key={i}
                    style={{
                      background: "rgba(30, 41, 59, 0.15)",
                      border: "1px solid var(--border-card)",
                      padding: "0.75rem",
                      borderRadius: "8px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.25rem"
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                      <span style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
                        {log.timestamp}
                      </span>
                      <span className="badge badge-warning">Outlier Spike</span>
                    </div>
                    <span style={{ fontSize: "0.875rem", fontWeight: 600 }}>
                      {log.metric.replace("_", " ")}: <span style={{ color: "var(--status-warning)" }}>{log.value}%</span>
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Environmental Telemetry Panel */}
      <WeatherStreams />

      {/* Traffic Telemetry Panel */}
      <TrafficStreams />
    </div>
  );
};

export default LiveMonitoring;
