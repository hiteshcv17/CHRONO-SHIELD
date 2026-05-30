import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import Plot from "react-plotly.js";
import { 
  Play, Pause, RotateCcw, AlertTriangle, Zap, Car, Wifi, 
  Terminal, Shield, CheckCircle, RefreshCw, Layers, ArrowRight, PlayCircle 
} from "lucide-react";
import SkeletonLoader from "../common/SkeletonLoader";
import { injectPrioritizedIncident } from "../../api/alerts";

// ==============================================================================
// Simulation Telemetry Interfaces
// ==============================================================================
interface SimTick {
  timeOffset: string;
  actual: number;
  expected: number;
  anomalyScore: number;
  status: "NOMINAL" | "WARNING" | "CRITICAL";
  message: string;
}

interface ScenarioPreset {
  id: string;
  title: string;
  category: "POWER" | "TRAFFIC" | "CYBER_HYDRO";
  severity: "CRITICAL" | "WARNING" | "INFO";
  district: string;
  description: string;
  technicalDetails: string;
  ticks: SimTick[];
}

// ==============================================================================
// Curated Demo Datasets (20 High-Fidelity Ticks each for flawless Demo Runs)
// ==============================================================================
const SCENARIO_PRESETS: ScenarioPreset[] = [
  {
    id: "substation-overload",
    title: "Substation Transformer Thermal Overload",
    category: "POWER",
    severity: "CRITICAL",
    district: "District 4 (Industrial Hub)",
    description: "Peak factory manufacturing shifts overload Substation SUB-09 core windings, triggering rapid thermal runaway and a cascading cooling network failure.",
    technicalDetails: "Model identifies high load divergence (actuals > 150kW vs. baseline of 85kW) coupled with absolute cooling pump lockup. AI prioritizes incident with a 96% priority score due to critical public power cascade risks.",
    ticks: [
      { timeOffset: "+0m", actual: 82, expected: 85, anomalyScore: 0.11, status: "NOMINAL", message: "SUB-09 transformer core temp: 64°C. Cooling pumps nominal." },
      { timeOffset: "+1m", actual: 85, expected: 85, anomalyScore: 0.12, status: "NOMINAL", message: "Grid demand stable. Local battery banks online at 100% capacity." },
      { timeOffset: "+2m", actual: 94, expected: 86, anomalyScore: 0.18, status: "NOMINAL", message: "Factory conveyor lines power up. Windings temperature: 69°C." },
      { timeOffset: "+3m", actual: 105, expected: 86, anomalyScore: 0.28, status: "NOMINAL", message: "Substation load increases. Power factor: 0.94. Core temp: 72°C." },
      { timeOffset: "+4m", actual: 118, expected: 86, anomalyScore: 0.38, status: "NOMINAL", message: "Power spikes detected. Model marks mild load baseline deviation." },
      { timeOffset: "+5m", actual: 122, expected: 87, anomalyScore: 0.44, status: "NOMINAL", message: "Substation windings temp reaches 80°C. High harmonics logged." },
      { timeOffset: "+6m", actual: 128, expected: 87, anomalyScore: 0.52, status: "NOMINAL", message: "SUB-09 oil pump valve pressure warning. Cooling efficiency drop." },
      { timeOffset: "+7m", actual: 134, expected: 87, anomalyScore: 0.59, status: "NOMINAL", message: "Transformer core windings reach 92°C. Backup fan fails to start." },
      { timeOffset: "+8m", actual: 139, expected: 88, anomalyScore: 0.68, status: "NOMINAL", message: "Warning: High thermal winding deviation detected. Harmonics surging." },
      { timeOffset: "+9m", actual: 145, expected: 88, anomalyScore: 0.72, status: "WARNING", message: "WARNING: SUB-09 core temp at 102°C. Auto-cooling loop saturated." },
      { timeOffset: "+10m", actual: 148, expected: 88, anomalyScore: 0.78, status: "WARNING", message: "AI Engine projects threshold breach. Local alerts in buffer lock." },
      { timeOffset: "+11m", actual: 152, expected: 89, anomalyScore: 0.82, status: "WARNING", message: "Divergence index high. High current lock tension on fastapi-01." },
      { timeOffset: "+12m", actual: 155, expected: 89, anomalyScore: 0.85, status: "WARNING", message: "Substation oil coolant boiling. Core temperature reaches 118°C." },
      { timeOffset: "+13m", actual: 158, expected: 89, anomalyScore: 0.88, status: "WARNING", message: "Warning: Transformer insulation degradation threshold crossed." },
      { timeOffset: "+14m", actual: 162, expected: 90, anomalyScore: 0.91, status: "CRITICAL", message: "CRITICAL: Core temperature: 132°C. Substation enters thermal emergency." },
      { timeOffset: "+15m", actual: 164, expected: 90, anomalyScore: 0.94, status: "CRITICAL", message: "Thermal runaway core breach warning. Fire suppression deck primed." },
      { timeOffset: "+16m", actual: 167, expected: 90, anomalyScore: 0.96, status: "CRITICAL", message: "CRITICAL: Automated gas-pressure circuit breakers locked open." },
      { timeOffset: "+17m", actual: 169, expected: 91, anomalyScore: 0.97, status: "CRITICAL", message: "SUB-09 windings short circuit. Core thermal explosion shield engaged." },
      { timeOffset: "+18m", actual: 172, expected: 91, anomalyScore: 0.98, status: "CRITICAL", message: "BLACKOUT in Industrial Sector A. Cascaded power grid dropouts active." },
      { timeOffset: "+19m", actual: 10, expected: 91, anomalyScore: 0.99, status: "CRITICAL", message: "TOTAL LOAD CRASH. Station dead. SLA power outage escalated." }
    ]
  },
  {
    id: "traffic-gridlock",
    title: "Metropolitan Beltway Traffic Collapse",
    category: "TRAFFIC",
    severity: "WARNING",
    district: "District 2 (Metropolitan Belt)",
    description: "A major multi-vehicle collision blockades two lanes of the beltway route, causing a rapid speed crash that propagates gridlock delay warnings to adjacent arterials.",
    technicalDetails: "AI autoencoder detects a massive speed index compression (actuals drop to 4mph vs. typical 55mph) and a corresponding social media traffic complaint surge. The model tags this as a warning level anomaly.",
    ticks: [
      { timeOffset: "+0m", actual: 54, expected: 52, anomalyScore: 0.08, status: "NOMINAL", message: "Metropolitan beltway flow: 54mph. Commute delays: zero." },
      { timeOffset: "+1m", actual: 52, expected: 52, anomalyScore: 0.09, status: "NOMINAL", message: "Lane sensor loops nominal. Traffic density within standard limits." },
      { timeOffset: "+2m", actual: 51, expected: 51, anomalyScore: 0.11, status: "NOMINAL", message: "Speed cameras log standard morning commute volume." },
      { timeOffset: "+3m", actual: 48, expected: 51, anomalyScore: 0.15, status: "NOMINAL", message: "Minor lane slowdown. Typical headway brake wave in progress." },
      { timeOffset: "+4m", actual: 32, expected: 51, anomalyScore: 0.32, status: "NOMINAL", message: "ALERT: Speed drop detected near exit 14. Average speed: 32mph." },
      { timeOffset: "+5m", actual: 24, expected: 50, anomalyScore: 0.45, status: "NOMINAL", message: "Beltway Sector B loops confirm crash. Multi-vehicle impact in lanes 1 & 2." },
      { timeOffset: "+6m", actual: 18, expected: 50, anomalyScore: 0.54, status: "NOMINAL", message: "Sensors log vehicle blockages. Emergency responder channels dispatched." },
      { timeOffset: "+7m", actual: 14, expected: 50, anomalyScore: 0.62, status: "NOMINAL", message: "Average speed: 14mph. Tailbacks extend for 1.2 miles." },
      { timeOffset: "+8m", actual: 10, expected: 49, anomalyScore: 0.69, status: "NOMINAL", message: "Beltway deadlock warning. Lane flow capacity compromised by 70%." },
      { timeOffset: "+9m", actual: 8, expected: 49, anomalyScore: 0.74, status: "WARNING", message: "WARNING: Average speed crashes to 8mph. Gridlock spreading." },
      { timeOffset: "+10m", actual: 7, expected: 49, anomalyScore: 0.78, status: "WARNING", message: "Delays exceed 40 minutes. Auto-rerouting systems saturated." },
      { timeOffset: "+11m", actual: 5, expected: 48, anomalyScore: 0.81, status: "WARNING", message: "Twitter signals: 42 geo-tagged complaints of beltway exit locks." },
      { timeOffset: "+12m", actual: 4, expected: 48, anomalyScore: 0.83, status: "WARNING", message: "Cascading delays detected on District 2 municipal bus corridors." },
      { timeOffset: "+13m", actual: 4, expected: 48, anomalyScore: 0.85, status: "WARNING", message: "WARNING: High-density traffic queue backup spans 3.8 miles." },
      { timeOffset: "+14m", actual: 3, expected: 47, anomalyScore: 0.86, status: "WARNING", message: "Exit ramp gridlock forces arterial municipal detours." },
      { timeOffset: "+15m", actual: 3, expected: 47, anomalyScore: 0.87, status: "WARNING", message: "Average speed deadlocked at 3mph. Transit delays: 85 minutes." },
      { timeOffset: "+16m", actual: 3, expected: 47, anomalyScore: 0.88, status: "WARNING", message: "Warning: Critical cargo logistic corridor blocked. SLA penalty active." },
      { timeOffset: "+17m", actual: 3, expected: 46, anomalyScore: 0.89, status: "WARNING", message: "Tow trucks blocked in gridlock. Incident clearance delay anticipated." },
      { timeOffset: "+18m", actual: 2, expected: 46, anomalyScore: 0.90, status: "WARNING", message: "District 2 beltway total deadlock. Standstill commuter locks." },
      { timeOffset: "+19m", actual: 2, expected: 46, anomalyScore: 0.91, status: "WARNING", message: "BELTWAY BELT COMPRESSION. Spillover gridlock into center grid arterials." }
    ]
  },
  {
    id: "gateway-hydro",
    title: "Hydro-Pressure & Gateway Saturation Cascade",
    category: "CYBER_HYDRO",
    severity: "CRITICAL",
    district: "District 7 (SaaS Science Park)",
    description: "Concurrent physical high-pressure water grid saturation and cybernetic request locks. Highly complex cross-domain infrastructure incident preset.",
    technicalDetails: "Simulates a pipeline burst flooding the cooling node room of the primary server gateway. Extreme data packet volume spike (15,000 req/s) occurs while hydro-line pressure drops, forcing a critical dual-system AI alert.",
    ticks: [
      { timeOffset: "+0m", actual: 40, expected: 42, anomalyScore: 0.05, status: "NOMINAL", message: "Water pressure: 40psi. Gateway throughput: 3,200 req/s. Nominal." },
      { timeOffset: "+1m", actual: 42, expected: 42, anomalyScore: 0.06, status: "NOMINAL", message: "Tech Park water node sensors stable. Packet delivery latency: 12ms." },
      { timeOffset: "+2m", actual: 46, expected: 43, anomalyScore: 0.08, status: "NOMINAL", message: "Micro-leak sensor loops running diagnostics. Gateway core locks stable." },
      { timeOffset: "+3m", actual: 52, expected: 43, anomalyScore: 0.12, status: "NOMINAL", message: "Gateway throughput rises to 4,800 req/s. Hydro-pressure: 45psi." },
      { timeOffset: "+4m", actual: 64, expected: 43, anomalyScore: 0.25, status: "NOMINAL", message: "Warning: High flow rate logged on main hydro-valve 12. Pressure: 58psi." },
      { timeOffset: "+5m", actual: 75, expected: 44, anomalyScore: 0.42, status: "NOMINAL", message: "Cyber traffic surge detected. Core gateway hits 8,200 req/s." },
      { timeOffset: "+6m", actual: 88, expected: 44, anomalyScore: 0.58, status: "NOMINAL", message: "Main pump room logs water accumulation. High humidity alarms." },
      { timeOffset: "+7m", actual: 95, expected: 44, anomalyScore: 0.67, status: "NOMINAL", message: "Gateway throughput: 11,400 req/s. CPU Core temperature: 84°C." },
      { timeOffset: "+8m", actual: 72, expected: 45, anomalyScore: 0.71, status: "WARNING", message: "WARNING: Tech Park hydro-pressure drops to 22psi. Massive leak vector." },
      { timeOffset: "+9m", actual: 60, expected: 45, anomalyScore: 0.76, status: "WARNING", message: "Cooling system leak confirmed. Server node room 04 flooded." },
      { timeOffset: "+10m", actual: 52, expected: 45, anomalyScore: 0.81, status: "WARNING", message: "WARNING: Gateway server temperatures crossing emergency limits." },
      { timeOffset: "+11m", actual: 45, expected: 46, anomalyScore: 0.84, status: "WARNING", message: "Gateway drops 12% of connections. High packet drop rates." },
      { timeOffset: "+12m", actual: 38, expected: 46, anomalyScore: 0.87, status: "WARNING", message: "Hydro pressure falls to 12psi. Water main flow cutoff triggered." },
      { timeOffset: "+13m", actual: 24, expected: 46, anomalyScore: 0.89, status: "WARNING", message: "Mainframe cooling loop failed. Thermal shutdowns initiated." },
      { timeOffset: "+14m", actual: 15, expected: 47, anomalyScore: 0.92, status: "CRITICAL", message: "CRITICAL: Hydro main pipe ruptured. Pressure: 4psi. Core room flooding." },
      { timeOffset: "+15m", actual: 8, expected: 47, anomalyScore: 0.95, status: "CRITICAL", message: "Primary cyber gateway node restart loop. Total packet drops." },
      { timeOffset: "+16m", actual: 4, expected: 47, anomalyScore: 0.97, status: "CRITICAL", message: "CRITICAL: Core database cluster connection timed out." },
      { timeOffset: "+17m", actual: 2, expected: 48, anomalyScore: 0.98, status: "CRITICAL", message: "Hydro pump short circuit due to submersion. Emergency shutoff." },
      { timeOffset: "+18m", actual: 1, expected: 48, anomalyScore: 0.99, status: "CRITICAL", message: "GATEWAY COLD BLACKOUT. SaaS Science Park systems offline." },
      { timeOffset: "+19m", actual: 0, expected: 48, anomalyScore: 1.00, status: "CRITICAL", message: "TOTAL CASCADING COLLAPSE. Combined hardware & network lockout." }
    ]
  }
];

// ==============================================================================
// SimulationEngine Component
// ==============================================================================
export const SimulationEngine: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<ScenarioPreset>(SCENARIO_PRESETS[0]);
  const [playhead, setPlayhead] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playSpeed, setPlaySpeed] = useState<number>(1);
  const [isInjecting, setIsInjecting] = useState<boolean>(false);
  const [injectSuccess, setInjectSuccess] = useState<boolean>(false);

  const playbackRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [chartWidth, setChartWidth] = useState<number>(600);

  // Responsive chart resizing handler
  useEffect(() => {
    const handleResize = () => {
      const parent = document.getElementById("sim-chart-container");
      if (parent) {
        setChartWidth(parent.clientWidth);
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Set scenario preset loader
  const handleSelectScenario = (scenario: ScenarioPreset) => {
    setIsPlaying(false);
    setSelectedScenario(scenario);
    setPlayhead(0);
    setInjectSuccess(false);
  };

  // Playback loop controller
  useEffect(() => {
    if (playbackRef.current) clearInterval(playbackRef.current);
    if (!isPlaying) return;

    const intervalMs = 1200 / playSpeed;
    playbackRef.current = setInterval(() => {
      setPlayhead((prev) => {
        const next = prev + 1;
        if (next >= selectedScenario.ticks.length) {
          setIsPlaying(false);
          return prev;
        }
        return next;
      });
    }, intervalMs);

    return () => {
      if (playbackRef.current) clearInterval(playbackRef.current);
    };
  }, [isPlaying, playSpeed, selectedScenario]);

  // Derived visible vectors based on active playhead
  const visibleTicks = useMemo(() => {
    return selectedScenario.ticks.slice(0, playhead + 1);
  }, [selectedScenario, playhead]);

  const currentTick = selectedScenario.ticks[playhead] || selectedScenario.ticks[0];

  const plotVectors = useMemo(() => {
    const times = visibleTicks.map((t) => t.timeOffset);
    const actuals = visibleTicks.map((t) => t.actual);
    const baselines = visibleTicks.map((t) => t.expected);
    const scores = visibleTicks.map((t) => t.anomalyScore);
    const thresholds = visibleTicks.map(() => 0.70); // Anomaly score alert line
    return { times, actuals, baselines, scores, thresholds };
  }, [visibleTicks]);

  // Dynamic status badges
  const getStatusBadgeClass = (status: string) => {
    switch (status.toUpperCase()) {
      case "CRITICAL": return "badge-critical";
      case "WARNING": return "badge-warning";
      case "NOMINAL":
      case "INFO":
      default:
        return "badge-safe";
    }
  };

  const getPresetCategoryColor = (category: string) => {
    switch (category) {
      case "POWER": return "var(--status-warning, #f59e0b)";
      case "TRAFFIC": return "var(--accent-purple, #a855f7)";
      case "CYBER_HYDRO":
      default:
        return "var(--accent-cyan, #00e5ff)";
    }
  };

  // Inject active preset to backend queue trigger
  const handleInjectToBackend = async () => {
    setIsInjecting(true);
    setInjectSuccess(false);
    try {
      const payload = {
        id: `sim-inj-${selectedScenario.id.substring(0, 3)}-${Math.floor(Math.random() * 900) + 100}`,
        timestamp: new Date().toISOString(),
        metric_name: selectedScenario.id === "gateway-hydro" ? "gateway_floods" : selectedScenario.id.replace("-", "_"),
        severity: selectedScenario.severity,
        score: selectedScenario.id === "traffic-gridlock" ? 0.88 : 0.98,
        description: `[SIMULATION REPLAY] ${selectedScenario.title}. Peak anomaly score: ${selectedScenario.id === "traffic-gridlock" ? "88%" : "98%"}. District target: ${selectedScenario.district}.`
      };
      await injectPrioritizedIncident(payload);
      setInjectSuccess(true);
      setTimeout(() => setInjectSuccess(false), 5000);
    } catch (err) {
      console.error("Failed to inject simulation to backend queue:", err);
    } finally {
      setIsInjecting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }} className="animate-scale-in">
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h2>AI Simulation Control Deck</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Stable operations simulation cockpit. Replay curated high-fidelity incident scenarios, inspect datasets, and stress-test the model.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button 
            className="btn-secondary" 
            onClick={() => handleSelectScenario(selectedScenario)}
            style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}
          >
            <RotateCcw size={14} />
            <span>Reset Demo</span>
          </button>
        </div>
      </div>

      {/* Demo Presets Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1.25rem" }}>
        {SCENARIO_PRESETS.map((preset) => {
          const isSelected = preset.id === selectedScenario.id;
          const catColor = getPresetCategoryColor(preset.category);

          return (
            <div 
              key={preset.id}
              className={`card ${isSelected ? "loading-scan-wrapper" : ""}`}
              onClick={() => handleSelectScenario(preset)}
              style={{
                cursor: "pointer",
                border: isSelected ? `1px solid ${catColor}` : "1px solid var(--border-card)",
                background: isSelected ? "rgba(30, 41, 59, 0.25)" : "var(--bg-card)",
                transition: "all 0.3s ease",
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span 
                  style={{ 
                    fontSize: "0.62rem", 
                    fontWeight: 800, 
                    color: catColor, 
                    border: `1px solid ${catColor}44`,
                    background: `${catColor}12`,
                    padding: "0.15rem 0.45rem",
                    borderRadius: "4px",
                    letterSpacing: "0.05em"
                  }}
                >
                  {preset.category.replace("_", " & ")}
                </span>
                <span className={`badge ${getStatusBadgeClass(preset.severity)}`} style={{ fontSize: "0.65rem", padding: "0.1rem 0.35rem" }}>
                  {preset.severity}
                </span>
              </div>

              <h4 style={{ fontSize: "0.95rem", fontWeight: 700, margin: "0.25rem 0 0 0", color: "var(--text-primary)" }}>
                {preset.title}
              </h4>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: 0, lineHeight: "1.4" }}>
                {preset.description}
              </p>
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", marginTop: "auto", display: "block" }}>
                📍 {preset.district}
              </span>
            </div>
          );
        })}
      </div>

      {/* Main Control Panel Structure */}
      <div className="dashboard-grid">
        {/* Left Side: Playback and Live Chart */}
        <div className="card col-8" id="sim-chart-container" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          
          {/* Playback Control HUD */}
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "rgba(15, 23, 42, 0.4)",
            border: "1px solid var(--border-card)",
            padding: "0.85rem 1.25rem",
            borderRadius: "10px",
            flexWrap: "wrap",
            gap: "1rem"
          }}>
            {/* Play/Pause/Reset Transport */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <button 
                className="btn-primary" 
                onClick={() => setIsPlaying(!isPlaying)}
                style={{ padding: "0.45rem 1rem", fontSize: "0.8rem", width: "100px", justifyContent: "center" }}
              >
                {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                <span>{isPlaying ? "Pause" : "Play"}</span>
              </button>
              
              <button 
                className="btn-secondary" 
                onClick={() => setPlayhead((p) => Math.max(0, p - 1))}
                disabled={playhead === 0}
                style={{ padding: "0.45rem", minWidth: "35px", display: "flex", justifyContent: "center" }}
                title="Step Back"
              >
                <span>-1</span>
              </button>
              
              <button 
                className="btn-secondary" 
                onClick={() => setPlayhead((p) => Math.min(selectedScenario.ticks.length - 1, p + 1))}
                disabled={playhead === selectedScenario.ticks.length - 1}
                style={{ padding: "0.45rem", minWidth: "35px", display: "flex", justifyContent: "center" }}
                title="Step Forward"
              >
                <span>+1</span>
              </button>

              <button 
                className="btn-secondary"
                onClick={() => { setPlayhead(0); setIsPlaying(false); }}
                style={{ padding: "0.45rem", minWidth: "35px", display: "flex", justifyContent: "center" }}
                title="Restart"
              >
                <RotateCcw size={14} />
              </button>
            </div>

            {/* Speed Options Toggler */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: "bold" }}>SPEED:</span>
              {[1, 2, 5].map((speed) => (
                <button
                  key={speed}
                  onClick={() => setPlaySpeed(speed)}
                  className="btn-secondary"
                  style={{
                    padding: "0.2rem 0.5rem",
                    fontSize: "0.7rem",
                    border: playSpeed === speed ? "1px solid var(--accent-cyan)" : "1px solid var(--border-card)",
                    background: playSpeed === speed ? "rgba(0, 229, 255, 0.12)" : "transparent",
                    color: playSpeed === speed ? "var(--accent-cyan)" : "var(--text-muted)"
                  }}
                >
                  {speed}x
                </button>
              ))}
            </div>

            {/* Scrubber Playhead Progress */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flex: 1, minWidth: "150px" }}>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                {Math.round((playhead / (selectedScenario.ticks.length - 1)) * 100)}%
              </span>
              <input 
                type="range"
                min="0"
                max={selectedScenario.ticks.length - 1}
                value={playhead}
                onChange={(e) => { setIsPlaying(false); setPlayhead(Number(e.target.value)); }}
                style={{
                  flex: 1,
                  accentColor: "var(--accent-cyan)",
                  height: "4px",
                  borderRadius: "2px",
                  background: "var(--border-card)",
                  cursor: "pointer"
                }}
              />
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Tick {playhead + 1}/{selectedScenario.ticks.length}
              </span>
            </div>

          </div>

          {/* Plotly Live Simulated Chart */}
          <div style={{ width: "100%", minHeight: "350px" }}>
            <Plot 
              data={[
                // 1. Expected Baseline Path
                {
                  x: plotVectors.times,
                  y: plotVectors.baselines,
                  type: "scatter",
                  mode: "lines",
                  name: "Baseline Expectation",
                  line: { color: "var(--text-muted, #94a3b8)", width: 1.5, dash: "dash" }
                },
                // 2. Simulated Telemetry Actual Feed
                {
                  x: plotVectors.times,
                  y: plotVectors.actuals,
                  type: "scatter",
                  mode: "lines",
                  name: "Simulated Telemetry Actual",
                  line: { color: getPresetCategoryColor(selectedScenario.category), width: 2, shape: "spline" }
                },
                // 3. AI Anomaly Score Path
                {
                  x: plotVectors.times,
                  y: plotVectors.scores,
                  type: "scatter",
                  mode: "lines+markers",
                  name: "AI Anomaly Score",
                  yaxis: "y2",
                  line: { color: "var(--accent-purple, #a855f7)", width: 2 },
                  marker: {
                    color: plotVectors.scores.map(s => s >= 0.70 ? "var(--status-critical)" : "var(--accent-purple)"),
                    size: 6
                  }
                },
                // 4. Alert Threshold Line
                {
                  x: plotVectors.times,
                  y: plotVectors.thresholds,
                  type: "scatter",
                  mode: "lines",
                  name: "Alert Trigger Threshold (0.70)",
                  yaxis: "y2",
                  line: { color: "rgba(239, 68, 68, 0.4)", width: 1.5, dash: "dot" }
                }
              ]}
              layout={{
                width: chartWidth - 32,
                height: 350,
                transition: {
                  duration: 350,
                  easing: "cubic-in-out"
                },
                frame: {
                  duration: 350
                },
                paper_bgcolor: "transparent",
                plot_bgcolor: "rgba(15, 23, 42, 0.2)",
                margin: { l: 45, r: 45, t: 25, b: 50 },
                xaxis: {
                  gridcolor: "rgba(71, 85, 105, 0.12)",
                  tickfont: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                  zeroline: false
                },
                yaxis: {
                  title: {
                    text: "Telemetry Metric Load / Value",
                    font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 10 }
                  },
                  gridcolor: "rgba(71, 85, 105, 0.12)",
                  tickfont: { color: "#94a3b8", family: "Outfit, sans-serif" },
                  zeroline: false
                },
                yaxis2: {
                  title: {
                    text: "AI Anomaly Score",
                    font: { color: "#a855f7", family: "Outfit, sans-serif", size: 10 }
                  },
                  tickfont: { color: "#a855f7", family: "Outfit, sans-serif" },
                  overlaying: "y",
                  side: "right",
                  range: [0, 1.1],
                  zeroline: false,
                  gridcolor: "none"
                },
                legend: {
                  font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 9 },
                  orientation: "h",
                  x: 0.05,
                  y: -0.22
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

        {/* Right Side: Demo Presets Status & Live Console */}
        <div className="card col-4" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1.1rem" }}>
            <Terminal size={18} color="var(--accent-cyan)" />
            Demo Operations HUD
          </h3>

          {/* Current Preset Info */}
          <div style={{ background: "rgba(15, 23, 42, 0.2)", border: "1px solid var(--border-card)", padding: "0.85rem", borderRadius: "10px", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontWeight: "bold", textTransform: "uppercase" }}>Active Preset Target</span>
            <strong style={{ fontSize: "0.9rem", color: "var(--text-primary)" }}>{selectedScenario.title}</strong>
            <span style={{ fontSize: "0.72rem", color: "var(--accent-cyan)" }}>📍 {selectedScenario.district}</span>
            <p style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "0.25rem", lineHeight: "1.4", borderTop: "1px solid var(--border-card)", paddingTop: "0.5rem" }}>
              <strong>AI Detection Logic:</strong> {selectedScenario.technicalDetails}
            </p>
          </div>

          {/* Live Telemetry Log Feed Console */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", flex: 1 }}>
            <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontWeight: "bold", textTransform: "uppercase" }}>Live Ingestion Log</span>
            
            <div style={{
              background: "#080c14",
              border: "1px solid var(--border-card)",
              borderRadius: "8px",
              padding: "0.85rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              flex: 1,
              maxHeight: "190px",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "0.4rem",
              color: "#38bdf8",
              boxShadow: "inset 0 0 10px rgba(0,0,0,0.8)"
            }}>
              <div style={{ color: "var(--text-muted)", fontSize: "0.62rem" }}>[INGESTION INITIALIZED AT {new Date().toLocaleTimeString()}]</div>
              {visibleTicks.map((t, idx) => (
                <div key={idx} style={{ 
                  borderLeft: `2.5px solid ${t.status === "CRITICAL" ? "var(--status-critical)" : t.status === "WARNING" ? "var(--status-warning)" : "var(--status-safe)"}`,
                  paddingLeft: "0.4rem",
                  marginBottom: "0.2rem"
                }}>
                  <span style={{ color: "#a855f7" }}>{t.timeOffset}</span> • <span style={{ color: t.status === "CRITICAL" ? "var(--status-critical)" : t.status === "WARNING" ? "var(--status-warning)" : "#94a3b8" }}>[{t.status}]</span> {t.message}
                </div>
              ))}
              {/* Auto-scroll playhead marker */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", color: "var(--accent-cyan)", animation: isPlaying ? "pulse 1s infinite" : "none" }}>
                <span>&gt;</span>
                <span className="blink">_</span>
              </div>
            </div>
          </div>

          {/* Actions & Hackathon Controls */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", borderTop: "1px solid var(--border-card)", paddingTop: "1rem" }}>
            <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontWeight: "bold", textTransform: "uppercase" }}>Demo Escalation Control</span>
            
            <button 
              className="btn-primary" 
              onClick={handleInjectToBackend}
              disabled={isInjecting || playhead < 10}
              style={{ width: "100%", justifyContent: "center", padding: "0.6rem" }}
            >
              {isInjecting ? (
                <>
                  <RefreshCw size={14} className="spin-animation" />
                  <span>Provisioning Incident...</span>
                </>
              ) : (
                <>
                  <PlayCircle size={14} />
                  <span>Inject Anomaly to Alerts Queue</span>
                </>
              )}
            </button>

            {injectSuccess && (
              <div style={{ 
                fontSize: "0.7rem", 
                background: "rgba(16, 185, 129, 0.1)", 
                border: "1px solid rgba(16, 185, 129, 0.3)", 
                color: "var(--status-safe)", 
                padding: "0.4rem 0.65rem",
                borderRadius: "6px",
                textAlign: "center",
                fontWeight: "bold",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.25rem"
              }}>
                <CheckCircle size={12} />
                <span>Simulated Incident Injected to Active Queue!</span>
              </div>
            )}
            
            {playhead < 10 && (
              <span style={{ fontSize: "0.62rem", color: "var(--text-muted)", textAlign: "center" }}>
                * Play simulation forward to at least 50% to enable backend alerts injection.
              </span>
            )}
          </div>

        </div>
      </div>

      {/* Curated Datasets Registry Inspector (Data Table) */}
      <div className="card">
        <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1.1rem", marginBottom: "0.85rem" }}>
          <Layers size={18} color="var(--accent-cyan)" />
          Curated Telemetry Datasets Registry
        </h3>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timeline Offset</th>
                <th>Metric Mode</th>
                <th>Baseline expected</th>
                <th>Simulated Actual</th>
                <th>AI Ingestion Score</th>
                <th>System Status</th>
                <th>Ingested Diagnostic Log Message</th>
              </tr>
            </thead>
            <tbody>
              {selectedScenario.ticks.map((tick, idx) => {
                const isElapsed = idx <= playhead;
                const isCurrent = idx === playhead;

                return (
                  <tr 
                    key={idx} 
                    style={{ 
                      opacity: isElapsed ? 1 : 0.35,
                      background: isCurrent ? "rgba(6, 182, 212, 0.04)" : "transparent",
                      borderLeft: isCurrent ? "4px solid var(--accent-cyan)" : "none",
                      transition: "all 0.25s ease"
                    }}
                  >
                    <td style={{ fontFamily: "var(--font-mono)", fontWeight: isCurrent ? 700 : 500 }}>
                      {tick.timeOffset} {isCurrent && "◀"}
                    </td>
                    <td style={{ fontWeight: 600 }}>{selectedScenario.id.replace("-", " ")}</td>
                    <td style={{ fontFamily: "var(--font-mono)" }}>{tick.expected}</td>
                    <td style={{ fontFamily: "var(--font-mono)", color: isElapsed ? "var(--text-primary)" : "var(--text-muted)" }}>
                      {tick.actual}
                    </td>
                    <td style={{ 
                      fontFamily: "var(--font-mono)", 
                      fontWeight: 700, 
                      color: isElapsed 
                        ? (tick.anomalyScore >= 0.70 ? "var(--status-critical)" : tick.anomalyScore >= 0.40 ? "var(--status-warning)" : "var(--accent-cyan)")
                        : "var(--text-muted)"
                    }}>
                      {tick.anomalyScore.toFixed(2)}
                    </td>
                    <td>
                      <span className={`badge ${isElapsed ? getStatusBadgeClass(tick.status) : ""}`} style={{ fontSize: "0.6rem", padding: "0.08rem 0.3rem" }}>
                        {isElapsed ? tick.status : "PENDING"}
                      </span>
                    </td>
                    <td style={{ fontSize: "0.75rem", color: isElapsed ? "var(--text-secondary)" : "var(--text-muted)", maxWidth: "300px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {tick.message}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};

export default SimulationEngine;
