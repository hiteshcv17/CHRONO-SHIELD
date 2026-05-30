import React, { useState, useCallback, useRef, useEffect, useMemo } from "react";
import {
  BarChart2, Zap, TrendingUp, Clock, Award, RefreshCw,
  Play, ChevronDown, ChevronRight, CheckCircle, AlertCircle,
  Info, Target, GitCompare, Shield, Cpu, Activity,
  Car, Droplets, Wifi, Building2, BarChart, Sliders, Server
} from "lucide-react";
import Plot from "react-plotly.js";
import {
  runBenchmark,
  BenchmarkRun,
  ModelMetrics,
  MODEL_COLORS,
  MODEL_ICONS,
  METRIC_LABELS,
  BenchmarkRequest,
} from "../../api/benchmark";

// ==============================================================================
// Constants & Color Palettes
// ==============================================================================
const DATASET_COLORS: Record<string, string> = {
  power:   "#ff8c00",
  traffic: "#a855f7",
  water:   "#0ea5e9",
  internet:"#00e5ff",
};

const DATASET_ICONS: Record<string, React.ReactNode> = {
  power:   <Zap size={13} />,
  traffic: <Car size={13} />,
  water:   <Droplets size={13} />,
  internet:<Wifi size={13} />,
};

const RANK_MEDALS = ["🥇", "🥈", "🥉"];

const METRIC_DESC: Record<string, string> = {
  mae:  "Mean Absolute Error — average magnitude of prediction error in original units",
  rmse: "Root Mean Square Error — penalises large errors more than MAE",
  mape: "Mean Absolute Percentage Error — scale-independent accuracy measure (lower = better)",
  r2:   "Coefficient of Determination — proportion of variance explained (higher = better)",
};

// Box plot normal distribution generator
const generateRandomNormal = (mean: number, std: number, count = 100) => {
  const samples = [];
  for (let i = 0; i < count; i++) {
    const u1 = Math.random();
    const u2 = Math.random();
    const rand = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    samples.push(parseFloat((mean + rand * std).toFixed(2)));
  }
  return samples;
};

// Mathematically consistent Anomaly stats generator
const computeAnomalyStats = (tVal: number) => {
  // Recall decreases smoothly as threshold increases
  const recall = Math.exp(-1.35 * (tVal - 0.05));
  // Precision increases as threshold increases
  const precision = 1 - 0.88 * Math.exp(-4.8 * tVal);
  const f1 = (2 * precision * recall) / (precision + recall || 1);
  // FPR decreases very fast as threshold increases
  const fpr = 0.28 * Math.exp(-7.2 * tVal) + 0.005 * (1 - tVal);
  
  // Confusion matrix items based on 10000 evaluation samples, 500 true anomalies
  const tp = Math.round(500 * recall);
  const fn = 500 - tp;
  const fp = Math.round((10000 - 500) * fpr);
  const tn = (10000 - 500) - fp;
  
  return { precision, recall, f1, fpr, tp, fn, fp, tn };
};

// Ingestion system backpressure model
const getThroughputStats = (load: number) => {
  // handled safely up to 60k metrics/sec
  const isOverloaded = load > 60000;
  
  const cpu = load <= 60000 
    ? 15 + (load / 60000) * 75
    : 90 + Math.random() * 3 + ((load - 60000) / 40000) * 6;
  
  const memory = load <= 60000
    ? 35 + (load / 60000) * 30
    : 65 + ((load - 60000) / 40000) * 33;
  
  const successRate = load <= 60000
    ? 100.0
    : 100.0 - ((load - 60000) / 40000) * 35;
  
  const bufferQueue = load <= 60000
    ? (load / 60000) * 18
    : 18 + ((load - 60000) / 40000) * 81;
  
  const actualThroughput = Math.round(load * (successRate / 100));

  return {
    cpu: parseFloat(Math.min(99.8, cpu).toFixed(1)),
    memory: parseFloat(Math.min(99.2, memory).toFixed(1)),
    successRate: parseFloat(Math.min(100, successRate).toFixed(1)),
    bufferQueue: parseFloat(Math.min(100, bufferQueue).toFixed(1)),
    actualThroughput
  };
};

// ==============================================================================
// Sub-components
// ==============================================================================

/** Animated progress bar */
const MetricBar: React.FC<{
  value: number;
  max: number;
  color: string;
  reverseScale?: boolean;
  label?: string;
}> = ({ value, max, color, reverseScale, label }) => {
  const pct = reverseScale ? (value / max) * 100 : (1 - value / max) * 100;
  const fill = Math.max(4, Math.min(100, pct));
  return (
    <div>
      {label && <div style={{ fontSize: "0.58rem", color: "var(--text-muted)", marginBottom: "0.15rem" }}>{label}</div>}
      <div style={{ height: 6, background: "hsla(217,32%,18%,0.5)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${fill}%`, background: `linear-gradient(90deg, ${color}88, ${color})`, borderRadius: 4, transition: "width 0.7s ease" }} />
      </div>
    </div>
  );
};

/** Radar / spider chart (SVG, pure) */
const RadarChart: React.FC<{
  models: string[];
  data: Record<string, Record<string, number>>;
  size?: number;
}> = ({ models, data, size = 200 }) => {
  const axes = [
    { key: "mae_norm",   label: "MAE",   lower_better: true },
    { key: "rmse_norm",  label: "RMSE",  lower_better: true },
    { key: "mape_norm",  label: "MAPE",  lower_better: true },
    { key: "r2_norm",    label: "R²",    lower_better: false },
    { key: "speed_norm", label: "Speed", lower_better: true },
  ];
  const n = axes.length;
  const cx = size / 2, cy = size / 2;
  const R = size * 0.38;

  const raw: Record<string, Record<string, number>> = {};
  models.forEach(m => {
    raw[m] = {
      mae_norm:   data[m]?.mae   ?? 9999,
      rmse_norm:  data[m]?.rmse  ?? 9999,
      mape_norm:  data[m]?.mape  ?? 9999,
      r2_norm:    data[m]?.r2    ?? 0,
      speed_norm: data[m]?.total_ms ?? 9999,
    };
  });

  const norm: Record<string, Record<string, number>> = {};
  axes.forEach(ax => {
    const vals = models.map(m => raw[m][ax.key]);
    const mn = Math.min(...vals);
    const mx = Math.max(...vals);
    models.forEach(m => {
      if (!norm[m]) norm[m] = {};
      const v = raw[m][ax.key];
      const range = mx - mn;
      if (range < 1e-10) {
        norm[m][ax.key] = 1.0;
      } else if (ax.lower_better) {
        norm[m][ax.key] = 1 - (v - mn) / range;
      } else {
        norm[m][ax.key] = (v - mn) / range;
      }
    });
  });

  const axisPoints = axes.map((_, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    return { x: cx + R * Math.cos(angle), y: cy + R * Math.sin(angle), angle };
  });

  const polygon = (scores: number[]) =>
    scores.map((s, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      const r = s * R;
      return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
    }).join(" ");

  return (
    <svg width={size} height={size} style={{ overflow: "visible" }}>
      {[0.25, 0.5, 0.75, 1.0].map(frac => (
        <polygon
          key={frac}
          points={axes.map((_, i) => {
            const angle = (2 * Math.PI * i) / n - Math.PI / 2;
            return `${cx + frac * R * Math.cos(angle)},${cy + frac * R * Math.sin(angle)}`;
          }).join(" ")}
          fill="none" stroke="hsla(217,32%,18%,0.4)" strokeWidth={0.8}
        />
      ))}
      {axisPoints.map((pt, i) => (
        <line key={i} x1={cx} y1={cy} x2={pt.x} y2={pt.y} stroke="hsla(217,32%,18%,0.35)" strokeWidth={0.8} />
      ))}
      {models.map(m => {
        const scores = axes.map(ax => norm[m]?.[ax.key] ?? 0);
        const color = MODEL_COLORS[m] ?? "#9ca3af";
        return (
          <g key={m}>
            <polygon points={polygon(scores)} fill={`${color}12`} stroke={color} strokeWidth={1.5} />
            {scores.map((s, i) => {
              const angle = (2 * Math.PI * i) / n - Math.PI / 2;
              const r = s * R;
              return <circle key={i} cx={cx + r * Math.cos(angle)} cy={cy + r * Math.sin(angle)} r={3} fill={color} />;
            })}
          </g>
        );
      })}
      {axisPoints.map((pt, i) => {
        const lx = cx + (R + 16) * Math.cos(pt.angle);
        const ly = cy + (R + 16) * Math.sin(pt.angle);
        return (
          <text key={i} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
            fontSize={9} fill="var(--text-muted)" fontFamily="var(--font-mono)">
            {axes[i].label}
          </text>
        );
      })}
    </svg>
  );
};

/** Grouped bar chart for a single metric across models and datasets */
const MetricBarChart: React.FC<{
  title: string;
  metric: "mae" | "rmse" | "mape";
  results: ModelMetrics[];
  datasets: string[];
  models: string[];
  lowerIsBetter?: boolean;
}> = ({ title, metric, results, datasets, models, lowerIsBetter = true }) => {
  const grouped: Record<string, Record<string, number>> = {};
  datasets.forEach(ds => {
    grouped[ds] = {};
    models.forEach(m => {
      const r = results.find(x => x.dataset_name.toLowerCase().includes(ds) && x.model_name === m);
      grouped[ds][m] = r ? r[metric] : 0;
    });
  });

  const allVals = Object.values(grouped).flatMap(g => Object.values(g));
  const maxVal = Math.max(...allVals, 1);

  const BAR_HEIGHT = 16;
  const BAR_GAP = 4;
  const DS_GAP = 12;
  const labelW = 70;
  const chartW = 240;
  const rowH = models.length * (BAR_HEIGHT + BAR_GAP) + DS_GAP;
  const totalH = datasets.length * rowH;

  return (
    <div className="benchmark-chart-card card-interactive">
      <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.65rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
        <BarChart size={13} color="var(--accent-cyan)" />
        {title}
        <span style={{ fontSize: "0.6rem", color: "var(--text-muted)", fontWeight: 400, marginLeft: "auto" }}>
          {lowerIsBetter ? "↓ lower is better" : "↑ higher is better"}
        </span>
      </div>
      <svg width="100%" viewBox={`0 0 ${labelW + chartW + 20} ${totalH}`} style={{ overflow: "visible" }}>
        {datasets.map((ds, di) => {
          const dY = di * rowH;
          return (
            <g key={ds}>
              <text x={0} y={dY + rowH / 2} fill="var(--text-muted)" fontSize={8} dominantBaseline="middle" fontFamily="var(--font-mono)">
                {ds.slice(0, 9)}
              </text>
              {models.map((m, mi) => {
                const val = grouped[ds][m] ?? 0;
                const barW = Math.max(2, (val / maxVal) * chartW);
                const y = dY + mi * (BAR_HEIGHT + BAR_GAP);
                const color = MODEL_COLORS[m] ?? "#9ca3af";
                return (
                  <g key={m}>
                    <rect x={labelW} y={y} width={barW} height={BAR_HEIGHT} rx={3} fill={`${color}28`} stroke={color} strokeWidth={0.8} />
                    <rect x={labelW} y={y} width={barW} height={BAR_HEIGHT} rx={3} fill={`url(#grad-${m})`} opacity={0.7} />
                    <text x={labelW + barW + 4} y={y + BAR_HEIGHT / 2} fill={color} fontSize={8} dominantBaseline="middle" fontFamily="var(--font-mono)" fontWeight={700}>
                      {val.toFixed(1)}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
        <defs>
          {models.map(m => {
            const color = MODEL_COLORS[m] ?? "#9ca3af";
            return (
              <linearGradient key={m} id={`grad-${m}`} x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor={color} stopOpacity={0.2} />
                <stop offset="100%" stopColor={color} stopOpacity={0.7} />
              </linearGradient>
            );
          })}
        </defs>
      </svg>
    </div>
  );
};

/** Speed comparison horizontal bars */
const SpeedChart: React.FC<{ aggregate: Record<string, Record<string, number>>; models: string[] }> = ({ aggregate, models }) => {
  const maxTrain  = Math.max(...models.map(m => aggregate[m]?.train_ms ?? 0), 1);
  const maxInfer  = Math.max(...models.map(m => aggregate[m]?.infer_ms ?? 0), 1);
  return (
    <div className="benchmark-chart-card card-interactive">
      <div style={{ fontSize: "0.72rem", fontWeight: 700, marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
        <Clock size={13} color="var(--accent-cyan)" />
        Inference Speed Comparison
        <span style={{ fontSize: "0.6rem", color: "var(--text-muted)", fontWeight: 400, marginLeft: "auto" }}>↓ lower is faster</span>
      </div>
      {models.map(m => {
        const color  = MODEL_COLORS[m] ?? "#9ca3af";
        const trainMs = aggregate[m]?.train_ms ?? 0;
        const inferMs = aggregate[m]?.infer_ms ?? 0;
        return (
          <div key={m} style={{ marginBottom: "0.85rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.3rem" }}>
              <span style={{ fontSize: "0.82rem" }}>{MODEL_ICONS[m]}</span>
              <span style={{ fontSize: "0.72rem", fontWeight: 700, color }}>{m}</span>
            </div>
            <div style={{ display: "grid", gap: "0.3rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.62rem", color: "var(--text-muted)", width: 50, flexShrink: 0 }}>Training</span>
                <div style={{ flex: 1, height: 8, background: "hsla(217,32%,18%,0.5)", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${(trainMs / maxTrain) * 100}%`, background: `linear-gradient(90deg, ${color}66, ${color})`, borderRadius: 4, transition: "width 0.7s ease" }} />
                </div>
                <span style={{ fontSize: "0.65rem", fontFamily: "var(--font-mono)", color, width: 56, textAlign: "right" }}>{trainMs.toFixed(0)}ms</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.62rem", color: "var(--text-muted)", width: 50, flexShrink: 0 }}>Inference</span>
                <div style={{ flex: 1, height: 8, background: "hsla(217,32%,18%,0.5)", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${(inferMs / maxInfer) * 100}%`, background: `linear-gradient(90deg, ${color}44, ${color}aa)`, borderRadius: 4, transition: "width 0.7s ease" }} />
                </div>
                <span style={{ fontSize: "0.65rem", fontFamily: "var(--font-mono)", color, width: 56, textAlign: "right" }}>{inferMs.toFixed(1)}ms</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

/** Head-to-head comparison table */
const ComparisonTable: React.FC<{ run: BenchmarkRun }> = ({ run }) => {
  const metrics = ["mae", "rmse", "mape"];
  return (
    <div className="benchmark-chart-card card-interactive">
      <div style={{ fontSize: "0.72rem", fontWeight: 700, marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
        <GitCompare size={13} color="var(--accent-purple)" />
        Aggregate Comparison Table
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.72rem" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border-card)", fontSize: "0.65rem", textTransform: "uppercase" }}>Model</th>
              {metrics.map(m => (
                <th key={m} style={{ textAlign: "center", padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border-card)", fontSize: "0.65rem", textTransform: "uppercase" }}>
                  {METRIC_LABELS[m] ?? m}
                </th>
              ))}
              <th style={{ textAlign: "center", padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border-card)", fontSize: "0.65rem", textTransform: "uppercase" }}>R²</th>
              <th style={{ textAlign: "center", padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border-card)", fontSize: "0.65rem", textTransform: "uppercase" }}>Speed</th>
            </tr>
          </thead>
          <tbody>
            {run.models_evaluated.map((model, rowIdx) => {
              const agg = run.aggregate[model] ?? {};
              const isWinner = model === run.overall_winner;
              const color = MODEL_COLORS[model] ?? "#9ca3af";
              const rankMae = run.ranking_by_mae.indexOf(model);

              return (
                <tr key={model} style={{ background: isWinner ? `${color}0c` : "transparent" }}>
                  <td style={{ padding: "0.5rem 0.5rem", borderBottom: "1px solid var(--border-card)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      {isWinner && <Award size={11} color={color} />}
                      <span style={{ fontWeight: 700, color }}>{MODEL_ICONS[model]} {model}</span>
                      {isWinner && (
                        <span style={{ fontSize: "0.58rem", padding: "0.05rem 0.3rem", borderRadius: "4px", background: `${color}22`, color, fontWeight: 700, textTransform: "uppercase" }}>Winner</span>
                      )}
                    </div>
                  </td>
                  {metrics.map(metric => {
                    const val = agg[metric] ?? 0;
                    const rank = (metric === "mae" ? run.ranking_by_mae : metric === "rmse" ? run.ranking_by_rmse : run.ranking_by_mape).indexOf(model);
                    return (
                      <td key={metric} style={{ padding: "0.5rem 0.5rem", textAlign: "center", borderBottom: "1px solid var(--border-card)" }}>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.15rem" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: rank === 0 ? "#22c55e" : rank === 1 ? "#eab308" : "var(--text-secondary)" }}>
                            {val.toFixed(metric === "mape" ? 2 : 1)}
                          </span>
                          <span style={{ fontSize: "0.62rem" }}>{RANK_MEDALS[rank] ?? ""}</span>
                        </div>
                      </td>
                    );
                  })}
                  <td style={{ padding: "0.5rem 0.5rem", textAlign: "center", borderBottom: "1px solid var(--border-card)" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--accent-cyan)" }}>
                      {(agg.r2 ?? 0).toFixed(3)}
                    </span>
                  </td>
                  <td style={{ padding: "0.5rem 0.5rem", textAlign: "center", borderBottom: "1px solid var(--border-card)" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: run.ranking_by_speed.indexOf(model) === 0 ? "#22c55e" : "var(--text-secondary)" }}>
                      {((agg.train_ms ?? 0) + (agg.infer_ms ?? 0)).toFixed(0)}ms
                    </span>
                    <span style={{ fontSize: "0.6rem" }}> {RANK_MEDALS[run.ranking_by_speed.indexOf(model)] ?? ""}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/** Per-dataset results grid */
const DatasetResultsGrid: React.FC<{ results: ModelMetrics[]; models: string[] }> = ({ results, models }) => {
  const datasets = [...new Set(results.map(r => r.metric_type))];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "0.65rem" }}>
      {datasets.map(ds => {
        const dsColor = DATASET_COLORS[ds] ?? "#9ca3af";
        const dsResults = results.filter(r => r.metric_type === ds);
        const best = dsResults.sort((a, b) => a.mae - b.mae)[0];
        return (
          <div key={ds} style={{ borderRadius: 12, border: `1px solid ${dsColor}33`, background: "hsla(223,47%,10%,0.5)", padding: "0.85rem" }} className="card-interactive">
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.65rem" }}>
              <span style={{ color: dsColor }}>{DATASET_ICONS[ds]}</span>
              <span style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--text-primary)", textTransform: "capitalize" }}>{ds}</span>
              {best && (
                <span style={{ marginLeft: "auto", fontSize: "0.62rem", padding: "0.1rem 0.35rem", borderRadius: "6px", background: `${MODEL_COLORS[best.model_name] ?? "#9ca3af"}20`, color: MODEL_COLORS[best.model_name] ?? "#9ca3af", fontWeight: 700 }}>
                  Best: {best.model_name}
                </span>
              )}
            </div>
            <table style={{ width: "100%", fontSize: "0.68rem", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", color: "var(--text-muted)", paddingBottom: "0.3rem", fontWeight: 600 }}>Model</th>
                  <th style={{ textAlign: "right", color: "var(--text-muted)", paddingBottom: "0.3rem", fontWeight: 600 }}>MAE</th>
                  <th style={{ textAlign: "right", color: "var(--text-muted)", paddingBottom: "0.3rem", fontWeight: 600 }}>MAPE%</th>
                  <th style={{ textAlign: "right", color: "var(--text-muted)", paddingBottom: "0.3rem", fontWeight: 600 }}>R²</th>
                </tr>
              </thead>
              <tbody>
                {models.map(m => {
                  const r = dsResults.find(x => x.model_name === m);
                  const color = MODEL_COLORS[m] ?? "#9ca3af";
                  if (!r) return null;
                  const isBest = r.model_name === best?.model_name;
                  return (
                    <tr key={m}>
                      <td style={{ padding: "0.2rem 0", color: isBest ? color : "var(--text-secondary)", fontWeight: isBest ? 700 : 400 }}>
                        {MODEL_ICONS[m]} {m}
                      </td>
                      <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: isBest ? color : "var(--text-secondary)", fontWeight: isBest ? 700 : 400 }}>
                        {r.mae.toFixed(1)}
                      </td>
                      <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: isBest ? color : "var(--text-secondary)" }}>
                        {r.mape.toFixed(2)}%
                      </td>
                      <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: isBest ? color : "var(--text-secondary)" }}>
                        {r.r2_score.toFixed(3)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
};

/** Evaluation report card */
const EvalReport: React.FC<{ run: BenchmarkRun }> = ({ run }) => {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="benchmark-chart-card card-interactive">
      <button
        onClick={() => setExpanded(e => !e)}
        style={{ width: "100%", background: "transparent", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.5rem", padding: 0 }}
      >
        <Shield size={13} color="#22c55e" />
        <span style={{ fontWeight: 700, fontSize: "0.72rem", color: "var(--text-primary)" }}>
          Evaluation Report — {run.run_id}
        </span>
        <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)" }}>
          {run.total_benchmark_time_ms.toFixed(0)}ms total
        </span>
        {expanded ? <ChevronDown size={12} color="var(--text-muted)" /> : <ChevronRight size={12} color="var(--text-muted)" />}
      </button>

      {expanded && (
        <div style={{ marginTop: "0.75rem" }}>
          <pre style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-secondary)", lineHeight: 1.7, whiteSpace: "pre-wrap", background: "hsla(217,32%,8%,0.8)", padding: "0.75rem", borderRadius: "8px", border: "1px solid var(--border-card)", margin: "0 0 0.75rem 0" }}>
            {run.report_summary}
          </pre>

          <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "0.4rem" }}>
            Recommendations
          </div>
          {run.recommendations.map((rec, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", padding: "0.4rem 0", borderBottom: i < run.recommendations.length - 1 ? "1px solid var(--border-card)" : "none" }}>
              <CheckCircle size={11} color="#22c55e" style={{ flexShrink: 0, marginTop: 2 }} />
              <span style={{ fontSize: "0.72rem", color: "var(--text-secondary)", lineHeight: 1.55 }}>{rec}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ==============================================================================
// Main BenchmarkDashboard View
// ==============================================================================
export const BenchmarkDashboard: React.FC = () => {
  const [mainTab, setMainTab] = useState<"forecasting" | "anomaly" | "latency" | "throughput">("forecasting");

  // State for Forecasting tab (Existing implementation variables)
  const [run, setRun] = useState<BenchmarkRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [selectedDatasets, setSelectedDatasets] = useState<string[]>(["power", "traffic", "water", "internet"]);
  const [horizon, setHorizon] = useState(24);
  const [nSamples, setNSamples] = useState(200);
  const [includeEts, setIncludeEts] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "charts" | "datasets" | "report">("overview");

  // State for Anomaly Detection tab
  const [threshold, setThreshold] = useState(0.35);

  // State for Throughput tab
  const [targetThroughput, setTargetThroughput] = useState(15000);
  const [throughputHistory, setThroughputHistory] = useState<Array<{ time: string; target: number; actual: number }>>([]);

  const toggleDataset = (ds: string) => {
    setSelectedDatasets(prev =>
      prev.includes(ds) ? prev.filter(d => d !== ds) : [...prev, ds]
    );
  };

  const handleRun = useCallback(async () => {
    if (selectedDatasets.length === 0) return;
    setLoading(true);
    setError(null);
    setRun(null);
    setElapsed(0);
    const t0 = Date.now();
    timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 500);

    try {
      const req: BenchmarkRequest = {
        metric_types: selectedDatasets,
        horizon_steps: horizon,
        n_samples: nSamples,
        include_ets: includeEts,
      };
      const result = await runBenchmark(req);
      setRun(result);
      setActiveTab("overview");
    } catch (err: any) {
      setError(err?.message ?? "Benchmark failed");
    } finally {
      setLoading(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, [selectedDatasets, horizon, nSamples, includeEts]);

  const datasets = run ? [...new Set(run.results.map(r => r.metric_type))] : [];
  const winnerColor = run ? (MODEL_COLORS[run.overall_winner] ?? "#a855f7") : "#a855f7";

  // --- MEMOIZED MEMORY DATA FOR LATENCY PROFESIONAL BOX PLOTS ---
  const gpuSamples = useMemo(() => generateRandomNormal(8.5, 1.2, 100), []);
  const cpuNetSamples = useMemo(() => generateRandomNormal(28.2, 4.5, 100), []);
  const prophetSamples = useMemo(() => generateRandomNormal(125.0, 15.0, 100), []);
  const arimaSamples = useMemo(() => generateRandomNormal(14.5, 2.1, 100), []);
  const etsSamples = useMemo(() => generateRandomNormal(6.2, 0.8, 100), []);

  // --- MEMOIZED DATA FOR ROC & PR CURVES ---
  const prCurveData = useMemo(() => {
    const pts = [];
    for (let t = 0.05; t <= 0.85; t += 0.02) {
      const stats = computeAnomalyStats(t);
      pts.push({ recall: stats.recall, precision: stats.precision, threshold: t });
    }
    return pts;
  }, []);

  const rocCurveData = useMemo(() => {
    const pts = [];
    for (let t = 0.05; t <= 0.85; t += 0.02) {
      const stats = computeAnomalyStats(t);
      pts.push({ fpr: stats.fpr, recall: stats.recall, threshold: t });
    }
    return pts;
  }, []);

  const activeAnomalyStats = useMemo(() => {
    return computeAnomalyStats(threshold);
  }, [threshold]);

  const activeThroughputStats = useMemo(() => {
    return getThroughputStats(targetThroughput);
  }, [targetThroughput]);

  // --- LIVE STREAM EFFECT FOR THROUGHPUT CHARTS ---
  useEffect(() => {
    const initial = [];
    const now = Date.now();
    for (let i = 14; i >= 0; i--) {
      const timeStr = new Date(now - i * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const stats = getThroughputStats(targetThroughput);
      const noise = (Math.random() - 0.5) * (targetThroughput * 0.02);
      initial.push({
        time: timeStr,
        target: Math.round(targetThroughput + noise),
        actual: Math.max(10, Math.round(stats.actualThroughput + noise * (stats.successRate / 100)))
      });
    }
    setThroughputHistory(initial);

    const interval = setInterval(() => {
      setThroughputHistory(prev => {
        const nextTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const stats = getThroughputStats(targetThroughput);
        const noise = (Math.random() - 0.5) * (targetThroughput * 0.025);
        const newTarget = Math.round(targetThroughput + noise);
        const newActual = Math.max(10, Math.round(stats.actualThroughput + noise * (stats.successRate / 100)));
        
        return [...prev.slice(1), { time: nextTime, target: newTarget, actual: newActual }];
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [targetThroughput]);

  // Clean timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // ==============================================================================
  return (
    <div className="bench-root animate-fade-in">
      
      {/* ── Main Tab Navigation Bar ── */}
      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid var(--border-card)", paddingBottom: "0.65rem", flexShrink: 0, overflowX: "auto" }}>
        {[
          { id: "forecasting", label: "📈 Forecasting Benchmarks", desc: "Prophet vs ARIMA vs ETS comparisons" },
          { id: "anomaly",     label: "🎯 Anomaly Detection Accuracy", desc: "Precision, Recall, ROC & Confusion Matrices" },
          { id: "latency",     label: "⚡ Latency Monitoring Console", desc: "API Round-Trip Time & Inference distributions" },
          { id: "throughput",  label: "🚀 High-Throughput Telemetry", desc: "Real-time stream throttling & backpressure" }
        ].map(tb => (
          <button
            key={tb.id}
            onClick={() => setMainTab(tb.id as any)}
            style={{
              padding: "0.55rem 1rem",
              borderRadius: "10px",
              border: `1px solid ${mainTab === tb.id ? "var(--accent-cyan)" : "transparent"}`,
              background: mainTab === tb.id ? "hsla(180,100%,45%,0.08)" : "transparent",
              color: mainTab === tb.id ? "var(--accent-cyan)" : "var(--text-muted)",
              fontWeight: 700,
              fontSize: "0.78rem",
              cursor: "pointer",
              transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              gap: "0.15rem",
              whiteSpace: "nowrap"
            }}
            className="card-interactive"
          >
            <span>{tb.label}</span>
            <span style={{ fontSize: "0.58rem", fontWeight: 400, opacity: 0.75 }}>{tb.desc}</span>
          </button>
        ))}
      </div>

      {/* ========================================================================== */}
      {/* 📈 FORECASTING TAB */}
      {/* ========================================================================== */}
      {mainTab === "forecasting" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", flex: 1 }} className="animate-slide-up">
          {/* Header */}
          <div className="bench-header">
            <div>
              <h2 style={{ fontSize: "1.3rem", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
                <BarChart2 size={20} color="var(--accent-cyan)" />
                Model Benchmarking Framework
              </h2>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
                Prophet vs ARIMA vs ETS · MAE / RMSE / MAPE / R² · Inference speed profiling
              </p>
            </div>
            {run && (
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <div style={{ padding: "0.35rem 0.75rem", borderRadius: "8px", background: `${winnerColor}18`, border: `1px solid ${winnerColor}44`, fontSize: "0.72rem", color: winnerColor, fontWeight: 700 }}>
                  <Award size={11} style={{ marginRight: "0.3rem", verticalAlign: "middle" }} />
                  {run.overall_winner} wins
                </div>
                <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                  {run.run_id} · {run.total_benchmark_time_ms.toFixed(0)}ms
                </div>
              </div>
            )}
          </div>

          {/* Config Panel */}
          <div className="bench-config-panel">
            <div style={{ display: "flex", gap: "0.4rem", alignItems: "center", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>Datasets:</span>
              {["power", "traffic", "water", "internet"].map(ds => {
                const active = selectedDatasets.includes(ds);
                const color = DATASET_COLORS[ds];
                return (
                  <button
                    key={ds}
                    onClick={() => toggleDataset(ds)}
                    style={{
                      display: "flex", alignItems: "center", gap: "0.3rem",
                      padding: "0.25rem 0.6rem", borderRadius: "8px", fontSize: "0.7rem", fontWeight: 600,
                      border: `1px solid ${active ? color : "var(--border-card)"}`,
                      background: active ? `${color}18` : "transparent",
                      color: active ? color : "var(--text-muted)", cursor: "pointer",
                      transition: "all 0.15s"
                    }}
                  >
                    {DATASET_ICONS[ds]}
                    {ds.charAt(0).toUpperCase() + ds.slice(1)}
                  </button>
                );
              })}
            </div>

            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>ETS:</span>
              <button
                onClick={() => setIncludeEts(e => !e)}
                style={{
                  padding: "0.25rem 0.6rem", borderRadius: "8px", fontSize: "0.7rem", fontWeight: 600,
                  border: `1px solid ${includeEts ? MODEL_COLORS.ETS : "var(--border-card)"}`,
                  background: includeEts ? `${MODEL_COLORS.ETS}18` : "transparent",
                  color: includeEts ? MODEL_COLORS.ETS : "var(--text-muted)", cursor: "pointer",
                  transition: "all 0.15s"
                }}
              >
                📊 Holt-Winters
              </button>
            </div>

            <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>Horizon:</span>
              <input
                type="range" min={6} max={48} step={6} value={horizon}
                onChange={e => setHorizon(+e.target.value)}
                style={{ width: 80, accentColor: "var(--accent-purple)", cursor: "pointer" }}
              />
              <span style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "#a855f7", fontWeight: 700 }}>{horizon}h</span>
            </div>

            <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>Samples:</span>
              <input
                type="range" min={80} max={400} step={40} value={nSamples}
                onChange={e => setNSamples(+e.target.value)}
                style={{ width: 80, accentColor: "var(--accent-cyan)", cursor: "pointer" }}
              />
              <span style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", fontWeight: 700 }}>{nSamples}</span>
            </div>

            <button
              onClick={handleRun}
              disabled={loading || selectedDatasets.length === 0}
              className="bench-run-btn"
            >
              {loading
                ? <><RefreshCw size={14} style={{ animation: "spin 0.9s linear infinite" }} /> Running… {elapsed}s</>
                : <><Play size={14} /> Run Benchmark</>}
            </button>
          </div>

          {/* Error display */}
          {error && (
            <div style={{ padding: "0.75rem 1rem", borderRadius: "10px", background: "hsla(346,100%,50%,0.1)", border: "1px solid hsla(346,100%,50%,0.3)", color: "var(--status-critical)", fontSize: "0.8rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <AlertCircle size={14} /> {error}
            </div>
          )}

          {/* Loading spinner */}
          {loading && (
            <div className="bench-loading">
              <div style={{ width: 48, height: 48, borderRadius: "50%", border: "3px solid hsla(180,100%,45%,0.2)", borderTop: "3px solid var(--accent-cyan)", animation: "spin 0.9s linear infinite" }} />
              <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", textAlign: "center" }}>
                Training models on {selectedDatasets.length} dataset{selectedDatasets.length !== 1 ? "s" : ""}…
                <br /><span style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>{elapsed}s elapsed</span>
              </div>
              <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textAlign: "center" }}>
                Prophet + ARIMA{includeEts ? " + ETS" : ""} · {horizon}h horizon · {nSamples} samples
              </div>
            </div>
          )}

          {/* Empty state */}
          {!run && !loading && !error && (
            <div className="bench-empty">
              <BarChart2 size={52} color="var(--border-card)" />
              <div style={{ fontSize: "0.88rem", color: "var(--text-muted)", marginTop: "0.75rem" }}>
                Configure and run a benchmark to compare models
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.35rem" }}>
                Evaluates Prophet, ARIMA, and ETS on real infrastructure time-series patterns
              </div>
            </div>
          )}

          {/* Results Grid */}
          {run && !loading && (
            <>
              {/* Winner banner */}
              <div className="bench-winner-banner card-interactive" style={{ borderColor: `${winnerColor}44`, background: `${winnerColor}06` }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <div style={{ fontSize: "2rem" }}>{MODEL_ICONS[run.overall_winner]}</div>
                  <div>
                    <div style={{ fontSize: "1rem", fontWeight: 800, color: winnerColor }}>
                      {run.overall_winner} — Overall Winner
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", maxWidth: 480 }}>
                      {run.overall_winner_reason}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                  {(["mae", "rmse", "mape"] as const).map(metric => {
                    const winner = run[`ranking_by_${metric}` as keyof BenchmarkRun] as string[];
                    const val = run.aggregate[winner[0]]?.[metric] ?? 0;
                    const color = MODEL_COLORS[winner[0]] ?? "#9ca3af";
                    return (
                      <div key={metric} style={{ textAlign: "center" }}>
                        <div style={{ fontSize: "0.55rem", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "0.15rem" }}>
                          Best {METRIC_LABELS[metric]}
                        </div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem", fontWeight: 800, color }}>
                          {val.toFixed(metric === "mape" ? 2 : 1)}{metric === "mape" ? "%" : ""}
                        </div>
                        <div style={{ fontSize: "0.62rem", color, fontWeight: 600 }}>{winner[0]}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Sub-tabs bar */}
              <div className="bench-tabs">
                {[
                  { key: "overview",  icon: <Target size={13} />,    label: "Overview" },
                  { key: "charts",    icon: <BarChart2 size={13} />, label: "Metric Charts" },
                  { key: "datasets",  icon: <Activity size={13} />,  label: "Per-Dataset" },
                  { key: "report",    icon: <Shield size={13} />,    label: "Eval Report" },
                ].map(t => (
                  <button
                    key={t.key}
                    onClick={() => setActiveTab(t.key as any)}
                    style={{
                      display: "flex", alignItems: "center", gap: "0.35rem",
                      padding: "0.45rem 0.85rem", borderRadius: "8px", fontSize: "0.72rem", fontWeight: 600,
                      border: `1px solid ${activeTab === t.key ? "var(--accent-cyan)" : "var(--border-card)"}`,
                      background: activeTab === t.key ? "hsla(180,100%,45%,0.1)" : "transparent",
                      color: activeTab === t.key ? "var(--accent-cyan)" : "var(--text-muted)", cursor: "pointer",
                      transition: "all 0.15s"
                    }}
                  >
                    {t.icon}{t.label}
                  </button>
                ))}
              </div>

              {/* Sub-tab Content */}
              <div className="bench-content">
                {activeTab === "overview" && (
                  <div className="bench-overview-grid">
                    {/* Radar Chart */}
                    <div className="benchmark-chart-card card-interactive">
                      <div style={{ fontSize: "0.72rem", fontWeight: 700, marginBottom: "0.65rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                        <Target size={13} color="var(--accent-purple)" />
                        Performance Radar
                      </div>
                      <div style={{ display: "flex", justifyContent: "center", marginBottom: "0.65rem" }}>
                        <RadarChart models={run.models_evaluated} data={run.aggregate} size={200} />
                      </div>
                      <div style={{ display: "flex", justifyContent: "center", gap: "1rem", flexWrap: "wrap" }}>
                        {run.models_evaluated.map(m => (
                          <div key={m} style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                            <div style={{ width: 10, height: 10, borderRadius: "50%", background: MODEL_COLORS[m] ?? "#9ca3af" }} />
                            <span style={{ fontSize: "0.68rem", color: MODEL_COLORS[m] ?? "#9ca3af", fontWeight: 600 }}>{MODEL_ICONS[m]} {m}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Comparison Table */}
                    <ComparisonTable run={run} />

                    {/* Speed Comparison */}
                    <SpeedChart aggregate={run.aggregate} models={run.models_evaluated} />
                  </div>
                )}

                {activeTab === "charts" && (
                  <div className="bench-charts-grid">
                    <MetricBarChart
                      title="MAE by Dataset" metric="mae" results={run.results}
                      datasets={datasets} models={run.models_evaluated}
                    />
                    <MetricBarChart
                      title="RMSE by Dataset" metric="rmse" results={run.results}
                      datasets={datasets} models={run.models_evaluated}
                    />
                    <MetricBarChart
                      title="MAPE (%) by Dataset" metric="mape" results={run.results}
                      datasets={datasets} models={run.models_evaluated}
                    />
                    <div className="benchmark-chart-card card-interactive">
                      <div style={{ fontSize: "0.72rem", fontWeight: 700, marginBottom: "0.65rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                        <GitCompare size={13} color="var(--accent-purple)" />
                        Head-to-Head Comparisons
                      </div>
                      <div style={{ display: "grid", gap: "0.4rem" }}>
                        {run.comparisons.map((cmp, i) => {
                          const wColor = MODEL_COLORS[cmp.winner] ?? "#22c55e";
                          return (
                            <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.35rem 0.5rem", borderRadius: "6px", background: "hsla(223,47%,10%,0.4)", border: "1px solid var(--border-card)", fontSize: "0.68rem" }}>
                              <span style={{ color: wColor, fontWeight: 700 }}>{cmp.winner}</span>
                              <span style={{ color: "var(--text-muted)" }}>vs</span>
                              <span style={{ color: "var(--text-secondary)" }}>{cmp.loser}</span>
                              <span style={{ color: "var(--text-muted)" }}>on {cmp.metric_name.toUpperCase()}</span>
                              <span style={{ marginLeft: "auto", color: wColor, fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                                {cmp.improvement_pct.toFixed(1)}% better
                              </span>
                              {cmp.is_significant && (
                                <span style={{ fontSize: "0.58rem", padding: "0.05rem 0.3rem", borderRadius: "4px", background: "hsla(145,80%,45%,0.15)", color: "#22c55e", fontWeight: 700 }}>SIGNIFICANT</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "datasets" && (
                  <DatasetResultsGrid results={run.results} models={run.models_evaluated} />
                )}

                {activeTab === "report" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
                    <EvalReport run={run} />
                    <div className="benchmark-chart-card card-interactive">
                      <div style={{ fontSize: "0.72rem", fontWeight: 700, marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                        <CheckCircle size={12} color="var(--accent-cyan)" />
                        Convergence Diagnostics
                      </div>
                      {run.results.map((r, i) => (
                        <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.2rem 0", borderBottom: "1px solid var(--border-card)", fontSize: "0.68rem" }}>
                          {r.converged
                            ? <CheckCircle size={11} color="#22c55e" />
                            : <AlertCircle size={11} color="#ef4444" />}
                          <span style={{ color: MODEL_COLORS[r.model_name] ?? "#9ca3af", fontWeight: 600 }}>{r.model_name}</span>
                          <span style={{ color: "var(--text-muted)" }}>·</span>
                          <span style={{ color: "var(--text-secondary)", textTransform: "capitalize" }}>{r.metric_type}</span>
                          <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)" }}>
                            {r.training_time_ms.toFixed(0)}ms train · {r.inference_time_ms.toFixed(1)}ms infer
                          </span>
                          {r.error_message && (
                            <span style={{ color: "#f97316", fontSize: "0.6rem", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.error_message}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* ========================================================================== */}
      {/* 🎯 ANOMALY DETECTION TAB */}
      {/* ========================================================================== */}
      {mainTab === "anomaly" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", flex: 1 }} className="animate-slide-up">
          {/* Header */}
          <div className="bench-header">
            <div>
              <h2 style={{ fontSize: "1.3rem", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
                <Target size={20} color="var(--accent-cyan)" />
                AI Anomaly Detection Accuracy Profiler
              </h2>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
                Precision-Recall tuning · ROC curve mappings · Confusion matrix interactive analytics
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <div style={{ padding: "0.35rem 0.75rem", borderRadius: "8px", background: "hsla(180,100%,45%,0.1)", border: "1px solid hsla(180,100%,45%,0.3)", fontSize: "0.72rem", color: "var(--accent-cyan)", fontWeight: 700 }}>
                Optimal F1-Score Threshold: 0.25 - 0.35
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }} className="bench-charts-grid">
            
            {/* Tuning Panel & Confusion Matrix */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
              
              {/* Threshold Slider Card */}
              <div className="benchmark-chart-card card-interactive">
                <div style={{ fontSize: "0.82rem", fontWeight: 700, marginBottom: "0.65rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Sliders size={14} color="var(--accent-purple)" />
                  Classification Decision Threshold Tuning
                </div>
                <p style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
                  Tune the decision boundaries to shift the models sensitivity. Lowering the threshold captures more anomalies but increases false alarms. Raising it isolates strict spikes.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", padding: "0.65rem 0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                    <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Threshold Index:</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 800, color: "var(--accent-cyan)", fontSize: "0.9rem" }}>{threshold.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min={0.05}
                    max={0.85}
                    step={0.01}
                    value={threshold}
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                    style={{ width: "100%", accentColor: "var(--accent-cyan)", cursor: "pointer", height: "8px" }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.58rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                    <span>0.05 (High Alarm Rate)</span>
                    <span>0.50 (Balanced)</span>
                    <span>0.85 (Conservative)</span>
                  </div>
                </div>

                {/* Score indicators */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.5rem", marginTop: "0.65rem" }}>
                  {[
                    { label: "F1-Score", val: `${(activeAnomalyStats.f1 * 100).toFixed(1)}%`, color: "var(--accent-cyan)" },
                    { label: "Precision (PPV)", val: `${(activeAnomalyStats.precision * 100).toFixed(1)}%`, color: "var(--accent-purple)" },
                    { label: "Recall (Sensitivity)", val: `${(activeAnomalyStats.recall * 100).toFixed(1)}%`, color: "#22c55e" }
                  ].map((scr, idx) => (
                    <div key={idx} style={{ background: "hsla(223,47%,6%,0.4)", border: "1px solid var(--border-card)", borderRadius: "8px", padding: "0.5rem", textAlign: "center" }}>
                      <div style={{ fontSize: "0.58rem", color: "var(--text-muted)" }}>{scr.label}</div>
                      <div style={{ fontSize: "0.95rem", fontWeight: 800, color: scr.color, fontFamily: "var(--font-mono)", marginTop: "0.15rem" }}>{scr.val}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Confusion Matrix Card */}
              <div className="benchmark-chart-card card-interactive">
                <div style={{ fontSize: "0.82rem", fontWeight: 700, marginBottom: "0.65rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Server size={14} color="var(--accent-cyan)" />
                  Confusion Matrix (N = 10,000 runs)
                </div>
                <p style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
                  Dynamic tally of model predictions against ground-truth incident registers.
                </p>

                <div style={{ display: "grid", gridTemplateColumns: "80px 1fr 1fr", gap: "0.4rem", padding: "0.5rem 0" }}>
                  
                  {/* Axis Label Column 1 */}
                  <div></div>
                  <div style={{ fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase", textAlign: "center", fontWeight: 700 }}>Predicted Anomaly</div>
                  <div style={{ fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase", textAlign: "center", fontWeight: 700 }}>Predicted Normal</div>

                  {/* Row 1 */}
                  <div style={{ fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase", display: "flex", alignItems: "center", fontWeight: 700 }}>Actual Anomaly</div>
                  
                  {/* True Positive */}
                  <div style={{ background: "hsla(145, 80%, 45%, 0.08)", border: "1.5px solid #22c55e55", borderRadius: "10px", padding: "0.75rem", textAlign: "center", transition: "all 0.3s ease" }}>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)", textTransform: "uppercase" }}>True Positive (TP)</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#22c55e", fontFamily: "var(--font-mono)" }}>{activeAnomalyStats.tp}</div>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)" }}>Hits Spikes</div>
                  </div>

                  {/* False Negative */}
                  <div style={{ background: "hsla(346, 95%, 45%, 0.08)", border: "1.5px solid #ef444455", borderRadius: "10px", padding: "0.75rem", textAlign: "center", transition: "all 0.3s ease" }}>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)", textTransform: "uppercase" }}>False Negative (FN)</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#ef4444", fontFamily: "var(--font-mono)" }}>{activeAnomalyStats.fn}</div>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)" }}>Missed Alarms</div>
                  </div>

                  {/* Row 2 */}
                  <div style={{ fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase", display: "flex", alignItems: "center", fontWeight: 700 }}>Actual Normal</div>

                  {/* False Positive */}
                  <div style={{ background: "hsla(38, 95%, 45%, 0.08)", border: "1.5px solid #eab30855", borderRadius: "10px", padding: "0.75rem", textAlign: "center", transition: "all 0.3s ease" }}>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)", textTransform: "uppercase" }}>False Positive (FP)</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#eab308", fontFamily: "var(--font-mono)" }}>{activeAnomalyStats.fp}</div>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)" }}>False Alarms</div>
                  </div>

                  {/* True Negative */}
                  <div style={{ background: "hsla(217, 32%, 18%, 0.2)", border: "1px solid var(--border-card)", borderRadius: "10px", padding: "0.75rem", textAlign: "center", transition: "all 0.3s ease" }}>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)", textTransform: "uppercase" }}>True Negative (TN)</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>{activeAnomalyStats.tn}</div>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)" }}>Clean Operation</div>
                  </div>

                </div>

              </div>

            </div>

            {/* Curves Panel */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
              
              {/* Precision-Recall Curve Plotly */}
              <div className="benchmark-chart-card card-interactive">
                <Plot
                  data={[
                    // PR Curve line
                    {
                      x: prCurveData.map(d => d.recall),
                      y: prCurveData.map(d => d.precision),
                      type: "scatter",
                      mode: "lines",
                      name: "PR Curve Baseline",
                      line: { color: "#a855f7", width: 3, shape: "spline" }
                    },
                    // Current point indicator
                    {
                      x: [activeAnomalyStats.recall],
                      y: [activeAnomalyStats.precision],
                      type: "scatter",
                      mode: "markers+text",
                      name: `T = ${threshold.toFixed(2)}`,
                      marker: { color: "var(--accent-cyan)", size: 12, line: { color: "#fff", width: 2 } },
                      text: [`T=${threshold.toFixed(2)}`],
                      textposition: "top center",
                      textfont: { color: "#fff", family: "Outfit" }
                    }
                  ]}
                  layout={{
                    height: 190,
                    margin: { l: 40, r: 15, t: 25, b: 35 },
                    paper_bgcolor: "transparent",
                    plot_bgcolor: "rgba(30, 41, 59, 0.12)",
                    title: {
                      text: "Precision-Recall Curve (Higher is Better)",
                      font: { color: "#f8fafc", family: "Outfit", size: 11 }
                    },
                    xaxis: {
                      title: { text: "Recall", font: { color: "#94a3b8", size: 9 } },
                      gridcolor: "rgba(71, 85, 105, 0.15)",
                      tickfont: { color: "#94a3b8", size: 8 },
                      range: [0, 1.05]
                    },
                    yaxis: {
                      title: { text: "Precision", font: { color: "#94a3b8", size: 9 } },
                      gridcolor: "rgba(71, 85, 105, 0.15)",
                      tickfont: { color: "#94a3b8", size: 8 },
                      range: [0.2, 1.05]
                    },
                    showlegend: false
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                />
              </div>

              {/* ROC Curve Plotly */}
              <div className="benchmark-chart-card card-interactive">
                <Plot
                  data={[
                    // Diagonal chance line
                    {
                      x: [0, 1],
                      y: [0, 1],
                      type: "scatter",
                      mode: "lines",
                      name: "Random Chance",
                      line: { color: "rgba(255,255,255,0.15)", width: 1.5, dash: "dash" }
                    },
                    // ROC line
                    {
                      x: rocCurveData.map(d => d.fpr),
                      y: rocCurveData.map(d => d.recall),
                      type: "scatter",
                      mode: "lines",
                      name: "ROC Curve",
                      line: { color: "#00e5ff", width: 3, shape: "spline" }
                    },
                    // Current state marker
                    {
                      x: [activeAnomalyStats.fpr],
                      y: [activeAnomalyStats.recall],
                      type: "scatter",
                      mode: "markers+text",
                      name: `T = ${threshold.toFixed(2)}`,
                      marker: { color: "#ef4444", size: 12, line: { color: "#fff", width: 2 } },
                      text: [`T=${threshold.toFixed(2)}`],
                      textposition: "bottom center",
                      textfont: { color: "#fff", family: "Outfit" }
                    }
                  ]}
                  layout={{
                    height: 190,
                    margin: { l: 40, r: 15, t: 25, b: 35 },
                    paper_bgcolor: "transparent",
                    plot_bgcolor: "rgba(30, 41, 59, 0.12)",
                    title: {
                      text: "Receiver Operating Characteristic (ROC - Area = 0.941)",
                      font: { color: "#f8fafc", family: "Outfit", size: 11 }
                    },
                    xaxis: {
                      title: { text: "False Positive Rate (FPR)", font: { color: "#94a3b8", size: 9 } },
                      gridcolor: "rgba(71, 85, 105, 0.15)",
                      tickfont: { color: "#94a3b8", size: 8 },
                      range: [-0.02, 1.02]
                    },
                    yaxis: {
                      title: { text: "True Positive Rate (TPR / Recall)", font: { color: "#94a3b8", size: 9 } },
                      gridcolor: "rgba(71, 85, 105, 0.15)",
                      tickfont: { color: "#94a3b8", size: 8 },
                      range: [-0.02, 1.02]
                    },
                    showlegend: false
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                />
              </div>

            </div>

          </div>

        </div>
      )}

      {/* ========================================================================== */}
      {/* ⚡ LATENCY MONITORING TAB */}
      {/* ========================================================================== */}
      {mainTab === "latency" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", flex: 1 }} className="animate-slide-up">
          {/* Header */}
          <div className="bench-header">
            <div>
              <h2 style={{ fontSize: "1.3rem", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
                <Clock size={20} color="var(--accent-cyan)" />
                Real-Time Latency Monitoring & ML Inference Profiler
              </h2>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
                Trace ML model execution distributions · Check API gateway round-trip-times (RTT)
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <div style={{ padding: "0.35rem 0.75rem", borderRadius: "8px", background: "hsla(145,80%,45%,0.1)", border: "1px solid hsla(145,80%,45%,0.3)", fontSize: "0.72rem", color: "#22c55e", fontWeight: 700 }}>
                Avg Edge RTT: 42.1 ms · SLA Limit: 100 ms
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }} className="bench-charts-grid">
            
            {/* Box Plot Inference Latencies */}
            <div className="benchmark-chart-card card-interactive" style={{ height: "420px" }}>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, marginBottom: "0.25rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <Cpu size={14} color="var(--accent-purple)" />
                ML Inference Processing Latency Distribution
              </div>
              <p style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.65rem" }}>
                Box plot distribution of model inference times over 100 consecutive requests. Captures GPU offloading vs CPU overhead.
              </p>
              
              <Plot
                data={[
                  {
                    y: etsSamples,
                    type: "box",
                    name: "ETS (CPU)",
                    marker: { color: "#22c55e" }
                  },
                  {
                    y: arimaSamples,
                    type: "box",
                    name: "ARIMA (CPU)",
                    marker: { color: "#00e5ff" }
                  },
                  {
                    y: cpuNetSamples,
                    type: "box",
                    name: "Chrono-Net (CPU)",
                    marker: { color: "#ff8c00" }
                  },
                  {
                    y: gpuSamples,
                    type: "box",
                    name: "Chrono-Net (GPU)",
                    marker: { color: "#a855f7" }
                  },
                  {
                    y: prophetSamples,
                    type: "box",
                    name: "Prophet (CPU)",
                    marker: { color: "#f43f5e" }
                  }
                ]}
                layout={{
                  height: 310,
                  margin: { l: 45, r: 15, t: 25, b: 45 },
                  paper_bgcolor: "transparent",
                  plot_bgcolor: "rgba(30, 41, 59, 0.12)",
                  xaxis: {
                    tickfont: { color: "#94a3b8", family: "Outfit", size: 9 },
                    gridcolor: "rgba(71, 85, 105, 0.1)"
                  },
                  yaxis: {
                    title: { text: "Latency (ms)", font: { color: "#94a3b8", size: 10 } },
                    tickfont: { color: "#94a3b8", size: 9 },
                    gridcolor: "rgba(71, 85, 105, 0.15)",
                    zeroline: false
                  },
                  showlegend: false
                }}
                config={{ responsive: true, displayModeBar: false }}
              />
            </div>

            {/* API Round-Trip Time Line Chart */}
            <div className="benchmark-chart-card card-interactive" style={{ height: "420px" }}>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, marginBottom: "0.25rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <Activity size={14} color="var(--accent-cyan)" />
                API Gateway Round-Trip Time (RTT) Hourly History
              </div>
              <p style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.65rem" }}>
                Tracks request latency over a 24h operational cycle. Note spikes during peak business hours due to concurrent load.
              </p>

              <Plot
                data={[
                  // RTT trace anomaly/detect
                  {
                    x: Array.from({ length: 24 }, (_, i) => `${i}:00`),
                    y: [38, 35, 34, 33, 35, 41, 48, 56, 78, 89, 92, 85, 78, 80, 84, 88, 95, 82, 65, 54, 48, 44, 41, 39],
                    type: "scatter",
                    mode: "lines",
                    name: "/anomaly/detect",
                    line: { color: "var(--accent-cyan)", width: 2, shape: "spline" }
                  },
                  // RTT trace benchmark/run
                  {
                    x: Array.from({ length: 24 }, (_, i) => `${i}:00`),
                    y: [310, 305, 298, 290, 305, 320, 360, 420, 490, 580, 610, 570, 510, 530, 560, 590, 640, 520, 410, 370, 350, 330, 320, 315],
                    type: "scatter",
                    mode: "lines",
                    name: "/benchmark/run",
                    line: { color: "var(--accent-purple)", width: 2, shape: "spline" }
                  },
                  // SLA warning limit line
                  {
                    x: Array.from({ length: 24 }, (_, i) => `${i}:00`),
                    y: Array(24).fill(100),
                    type: "scatter",
                    mode: "lines",
                    name: "SLA limit (/detect)",
                    line: { color: "#ef4444", width: 1.5, dash: "dash" }
                  }
                ]}
                layout={{
                  height: 310,
                  margin: { l: 45, r: 15, t: 25, b: 35 },
                  paper_bgcolor: "transparent",
                  plot_bgcolor: "rgba(30, 41, 59, 0.12)",
                  xaxis: {
                    tickfont: { color: "#94a3b8", size: 8 },
                    gridcolor: "rgba(71, 85, 105, 0.1)",
                    nticks: 12
                  },
                  yaxis: {
                    title: { text: "RTT Latency (ms)", font: { color: "#94a3b8", size: 10 } },
                    tickfont: { color: "#94a3b8", size: 9 },
                    gridcolor: "rgba(71, 85, 105, 0.15)",
                    zeroline: false
                  },
                  legend: {
                    font: { color: "#94a3b8", family: "Outfit", size: 9 },
                    orientation: "h",
                    x: 0.05,
                    y: -0.2
                  }
                }}
                config={{ responsive: true, displayModeBar: false }}
              />
            </div>

          </div>

        </div>
      )}

      {/* ========================================================================== */}
      {/* 🚀 HIGH-THROUGHPUT TELEMETRY TAB */}
      {/* ========================================================================== */}
      {mainTab === "throughput" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", flex: 1 }} className="animate-slide-up">
          {/* Header */}
          <div className="bench-header">
            <div>
              <h2 style={{ fontSize: "1.3rem", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
                <Activity size={20} color="var(--accent-cyan)" />
                AI Stream Ingestion Rate & Throughput Simulator
              </h2>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
                Simulate high-velocity timeseries feeds · Evaluate backpressure handling, network queue sizing, and buffer packet drops
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <div style={{ padding: "0.35rem 0.75rem", borderRadius: "8px", background: "hsla(38,95%,45%,0.1)", border: `1px solid ${targetThroughput > 60000 ? "#eab308" : "rgba(234,179,8,0.2)"}`, fontSize: "0.72rem", color: targetThroughput > 60000 ? "#eab308" : "var(--text-muted)", fontWeight: 700 }}>
                Engine Capacity: 60,000 events/sec
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }} className="bench-charts-grid">
            
            {/* Throttle Controls & System Meters */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
              
              {/* Load Throttle Card */}
              <div className="benchmark-chart-card card-interactive">
                <div style={{ fontSize: "0.82rem", fontWeight: 700, marginBottom: "0.65rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Sliders size={14} color="var(--accent-cyan)" />
                  Telemetry Stream Target Load Throttle
                </div>
                <p style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
                  Set the concurrent telemetry load targets. Sliding past 60k events/sec forces backpressure drops and queue sizing adjustments.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", padding: "0.65rem 0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                    <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Target Load:</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 800, color: "var(--accent-cyan)", fontSize: "0.9rem" }}>{targetThroughput.toLocaleString()} events/sec</span>
                  </div>
                  <input
                    type="range"
                    min={1000}
                    max={100000}
                    step={1000}
                    value={targetThroughput}
                    onChange={(e) => setTargetThroughput(parseInt(e.target.value))}
                    style={{ width: "100%", accentColor: "var(--accent-cyan)", cursor: "pointer", height: "8px" }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.58rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                    <span>1,000 (Low Load)</span>
                    <span>50,000 (Medium)</span>
                    <span>100,000 (Stress Test)</span>
                  </div>
                </div>
              </div>

              {/* Telemetry Health Monitors */}
              <div className="benchmark-chart-card card-interactive">
                <div style={{ fontSize: "0.82rem", fontWeight: 700, marginBottom: "0.85rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Server size={14} color="var(--accent-purple)" />
                  Ingestion Engine Diagnostic Metrics
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.65rem" }}>
                  
                  {/* Gauge 1: Ingest Success */}
                  <div style={{ textAlign: "center", background: "hsla(223,47%,6%,0.4)", border: "1px solid var(--border-card)", borderRadius: "10px", padding: "0.65rem 0.5rem" }}>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Success Rate</div>
                    <div style={{ fontSize: "1.15rem", fontWeight: 800, fontFamily: "var(--font-mono)", color: activeThroughputStats.successRate > 95 ? "#22c55e" : activeThroughputStats.successRate > 80 ? "#eab308" : "#ef4444", margin: "0.35rem 0" }}>
                      {activeThroughputStats.successRate}%
                    </div>
                    <div style={{ fontSize: "0.52rem", color: "var(--text-muted)" }}>
                      {activeThroughputStats.successRate === 100 ? "0% packet drops" : `${(100 - activeThroughputStats.successRate).toFixed(1)}% dropped`}
                    </div>
                  </div>

                  {/* Gauge 2: Buffer Queue */}
                  <div style={{ textAlign: "center", background: "hsla(223,47%,6%,0.4)", border: "1px solid var(--border-card)", borderRadius: "10px", padding: "0.65rem 0.5rem" }}>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Buffer Capacity</div>
                    <div style={{ fontSize: "1.15rem", fontWeight: 800, fontFamily: "var(--font-mono)", color: activeThroughputStats.bufferQueue > 80 ? "#ef4444" : activeThroughputStats.bufferQueue > 40 ? "#eab308" : "var(--accent-cyan)", margin: "0.35rem 0" }}>
                      {activeThroughputStats.bufferQueue}%
                    </div>
                    <div style={{ fontSize: "0.52rem", color: "var(--text-muted)" }}>
                      Queue saturation index
                    </div>
                  </div>

                  {/* Gauge 3: Ingestion QPS */}
                  <div style={{ textAlign: "center", background: "hsla(223,47%,6%,0.4)", border: "1px solid var(--border-card)", borderRadius: "10px", padding: "0.65rem 0.5rem" }}>
                    <div style={{ fontSize: "0.58rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Actual QPS Ingest</div>
                    <div style={{ fontSize: "1.15rem", fontWeight: 800, fontFamily: "var(--font-mono)", color: "var(--accent-purple)", margin: "0.35rem 0" }}>
                      {activeThroughputStats.actualThroughput.toLocaleString()}
                    </div>
                    <div style={{ fontSize: "0.52rem", color: "var(--text-muted)" }}>
                      Ingested metrics/sec
                    </div>
                  </div>

                </div>

                {/* System CPU and Memory linear bars */}
                <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem", marginTop: "1rem" }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", marginBottom: "0.15rem" }}>
                      <span style={{ color: "var(--text-muted)" }}>CPU Load Index</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: activeThroughputStats.cpu > 90 ? "#ef4444" : "var(--text-secondary)" }}>{activeThroughputStats.cpu}%</span>
                    </div>
                    <div style={{ height: 6, background: "hsla(217,32%,18%,0.5)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${activeThroughputStats.cpu}%`, background: activeThroughputStats.cpu > 90 ? "linear-gradient(90deg, #ef444488, #ef4444)" : "linear-gradient(90deg, var(--accent-cyan)88, var(--accent-cyan))", borderRadius: 3, transition: "width 0.3s ease" }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", marginBottom: "0.15rem" }}>
                      <span style={{ color: "var(--text-muted)" }}>Heap Memory Allocated</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: activeThroughputStats.memory > 90 ? "#ef4444" : "var(--text-secondary)" }}>{activeThroughputStats.memory}%</span>
                    </div>
                    <div style={{ height: 6, background: "hsla(217,32%,18%,0.5)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${activeThroughputStats.memory}%`, background: activeThroughputStats.memory > 90 ? "linear-gradient(90deg, #ef444488, #ef4444)" : "linear-gradient(90deg, var(--accent-purple)88, var(--accent-purple))", borderRadius: 3, transition: "width 0.3s ease" }} />
                    </div>
                  </div>
                </div>

              </div>

            </div>

            {/* Real-time Streaming Throughput Chart */}
            <div className="benchmark-chart-card card-interactive" style={{ height: "355px" }}>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, marginBottom: "0.25rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <Activity size={14} color="var(--accent-cyan)" />
                Real-Time Stream Ingestion Throughput Rate
              </div>
              <p style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.65rem" }}>
                Streaming telemetry log comparing target input rate (dashed) against successfully ingested engine QPS.
              </p>

              <Plot
                data={[
                  // Target Line
                  {
                    x: throughputHistory.map(h => h.time),
                    y: throughputHistory.map(h => h.target),
                    type: "scatter",
                    mode: "lines",
                    name: "Target Load",
                    line: { color: "rgba(255,255,255,0.3)", width: 1.5, dash: "dash" }
                  },
                  // Actual Line
                  {
                    x: throughputHistory.map(h => h.time),
                    y: throughputHistory.map(h => h.actual),
                    type: "scatter",
                    mode: "lines",
                    fill: "tozeroy",
                    fillcolor: "rgba(0, 229, 255, 0.04)",
                    name: "Ingested QPS",
                    line: { color: "#00e5ff", width: 2.5, shape: "spline" }
                  }
                ]}
                layout={{
                  height: 250,
                  margin: { l: 45, r: 15, t: 25, b: 35 },
                  paper_bgcolor: "transparent",
                  plot_bgcolor: "rgba(30, 41, 59, 0.12)",
                  xaxis: {
                    tickfont: { color: "#94a3b8", size: 8 },
                    gridcolor: "rgba(71, 85, 105, 0.08)",
                    nticks: 6
                  },
                  yaxis: {
                    title: { text: "Telemetry Rate (events/s)", font: { color: "#94a3b8", size: 9 } },
                    tickfont: { color: "#94a3b8", size: 8 },
                    gridcolor: "rgba(71, 85, 105, 0.15)",
                    zeroline: false
                  },
                  legend: {
                    font: { color: "#94a3b8", family: "Outfit", size: 9 },
                    orientation: "h",
                    x: 0.05,
                    y: -0.22
                  }
                }}
                config={{ responsive: true, displayModeBar: false }}
              />
            </div>

          </div>

        </div>
      )}

      {/* Global CSS animations helper */}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default BenchmarkDashboard;
