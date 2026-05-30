import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polygon,
  useMap,
  ZoomControl,
} from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  Map,
  Layers,
  AlertCircle,
  RefreshCw,
  X,
  Globe,
  Zap,
  Droplets,
  Wifi,
  Car,
  Building2,
  Activity,
  Clock,
  ChevronRight,
  Filter,
} from "lucide-react";
import {
  fetchGeoMap,
  GeoMapResponse,
  GeoAnomalyPoint,
  GeoRegionStatus,
} from "../../api/geo";

// ==============================================================================
// Fix leaflet default icon paths (broken in Vite/Webpack builds)
// ==============================================================================
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

// ==============================================================================
// Constants & Config
// ==============================================================================
const MAP_CENTER: [number, number] = [28.6304, 77.2177]; // Central Delhi NCR
const MAP_ZOOM = 11;

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

const RISK_POLYGON_COLORS: Record<string, string> = {
  NOMINAL:  "#22c55e",
  LOW:      "#84cc16",
  MEDIUM:   "#eab308",
  HIGH:     "#f97316",
  CRITICAL: "#ef4444",
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  POWER:                 <Zap size={11} />,
  TRAFFIC:               <Car size={11} />,
  WATER:                 <Droplets size={11} />,
  INTERNET:              <Wifi size={11} />,
  PUBLIC_INFRASTRUCTURE: <Building2 size={11} />,
};

// ==============================================================================
// Custom SVG DivIcon factory
// ==============================================================================
function createAnomalyIcon(severity: string, _category: string): L.DivIcon {
  const color = SEVERITY_COLORS[severity] ?? "#00e5ff";
  const size = severity === "CRITICAL" ? 22 : severity === "WARNING" ? 18 : 14;
  const pulseStyle =
    severity === "CRITICAL"
      ? `animation: geo-pulse-critical 1.6s infinite;`
      : severity === "WARNING"
      ? `animation: geo-pulse-warning 2s infinite;`
      : `animation: geo-pulse-info 2.4s infinite;`;

  const html = `
    <div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:${color}33;border:2.5px solid ${color};
      ${pulseStyle}
      position:relative;display:flex;align-items:center;justify-content:center;
      cursor:pointer;
    ">
      <div style="
        width:${size * 0.38}px;height:${size * 0.38}px;border-radius:50%;
        background:${color};opacity:0.9;
      "></div>
    </div>`;

  return L.divIcon({
    html,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2 - 4],
  });
}

const iconCache: Record<string, L.DivIcon> = {};

function getAnomalyIcon(severity: string, category: string): L.DivIcon {
  const cacheKey = `${severity}:${category}`;
  if (!iconCache[cacheKey]) {
    iconCache[cacheKey] = createAnomalyIcon(severity, category);
  }
  return iconCache[cacheKey];
}

// ==============================================================================
// HeatmapLayer — rendered via imperative Leaflet.heat
// ==============================================================================
interface HeatmapLayerProps {
  points: { lat: number; lng: number; intensity: number }[];
  visible: boolean;
}

const HeatmapLayer: React.FC<HeatmapLayerProps> = ({ points, visible }) => {
  const map = useMap();
  const heatLayerRef = useRef<any>(null);

  useEffect(() => {
    if (!visible || points.length === 0) {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current);
        heatLayerRef.current = null;
      }
      return;
    }

    // Dynamically import leaflet.heat and attach
    import("leaflet.heat" as any).then(() => {
      const data = points.map((p) => [p.lat, p.lng, p.intensity]);
      if (heatLayerRef.current) {
        heatLayerRef.current.setLatLngs(data);
      } else {
        heatLayerRef.current = (L as any).heatLayer(data, {
          radius: 35,
          blur: 28,
          maxZoom: 15,
          max: 1.0,
          gradient: {
            0.0: "#001a33",
            0.2: "#003366",
            0.4: "#0077b6",
            0.6: "#00b4d8",
            0.75: "#90e0ef",
            0.88: "#ffd166",
            1.0: "#ef233c",
          },
        });
        heatLayerRef.current.addTo(map);
      }
    });

    return () => {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current);
        heatLayerRef.current = null;
      }
    };
  }, [points, visible, map]);

  return null;
};

// ==============================================================================
// Region Polygon with hover popup
// ==============================================================================
interface RegionPolygonProps {
  region: GeoRegionStatus;
  visible: boolean;
}

const RegionPolygon: React.FC<RegionPolygonProps> = React.memo(({ region, visible }) => {
  if (!visible) return null;

  const color = RISK_POLYGON_COLORS[region.risk_level] ?? "#22c55e";
  const positions = region.polygon.map(([lat, lng]) => [lat, lng] as [number, number]);

  const healthBarWidth = `${region.health_score}%`;

  return (
    <Polygon
      positions={positions}
      pathOptions={{
        color,
        weight: 2,
        opacity: 0.85,
        fillColor: color,
        fillOpacity: 0.07,
        dashArray: region.risk_level === "CRITICAL" ? "6 4" : undefined,
      }}
    >
      <Popup>
        <div style={{ minWidth: 200, padding: "0.25rem 0" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <Globe size={14} color={color} />
            <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "#f0f4f8" }}>
              {region.name}
            </span>
          </div>

          {/* Health score bar */}
          <div style={{ marginBottom: "0.6rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
              <span style={{ fontSize: "0.7rem", color: "#8899aa", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Health Score
              </span>
              <span style={{ fontFamily: "monospace", fontSize: "0.82rem", fontWeight: 700, color }}>
                {region.health_score.toFixed(1)}
              </span>
            </div>
            <div style={{ height: "5px", background: "#1a2340", borderRadius: "4px", overflow: "hidden" }}>
              <div style={{ height: "100%", width: healthBarWidth, background: color, borderRadius: "4px", transition: "width 0.4s" }} />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.35rem" }}>
            <div style={{ fontSize: "0.75rem", color: "#8899aa" }}>Risk Level</div>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color }}>{region.risk_level}</div>

            <div style={{ fontSize: "0.75rem", color: "#8899aa" }}>Anomalies</div>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f0f4f8" }}>{region.anomaly_count}</div>

            <div style={{ fontSize: "0.75rem", color: "#8899aa" }}>Critical</div>
            <div style={{
              fontSize: "0.75rem", fontWeight: 700,
              color: region.critical_count > 0 ? "#ff0044" : "#22c55e"
            }}>
              {region.critical_count}
            </div>

            {region.dominant_category && (
              <>
                <div style={{ fontSize: "0.75rem", color: "#8899aa" }}>Dominant</div>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: CATEGORY_COLORS[region.dominant_category] ?? "#00e5ff" }}>
                  {region.dominant_category.replace("_", " ")}
                </div>
              </>
            )}
          </div>
        </div>
      </Popup>
    </Polygon>
  );
});

// ==============================================================================
// Anomaly Detail Popup Content
// ==============================================================================
const AnomalyPopupContent: React.FC<{ point: GeoAnomalyPoint }> = React.memo(({ point }) => {
  const color = SEVERITY_COLORS[point.severity] ?? "#00e5ff";
  const catColor = CATEGORY_COLORS[point.category] ?? "#00e5ff";

  return (
    <div style={{ minWidth: 210, padding: "0.25rem 0" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.6rem" }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
        <span style={{ fontWeight: 700, fontSize: "0.82rem", color, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          {point.severity}
        </span>
        <span style={{
          marginLeft: "auto", padding: "0.1rem 0.45rem", borderRadius: "10px",
          fontSize: "0.65rem", fontWeight: 700, background: `${catColor}22`, color: catColor,
          border: `1px solid ${catColor}55`
        }}>
          {point.category.replace("_", " ")}
        </span>
      </div>

      {/* Metric */}
      <div style={{ fontSize: "0.78rem", color: "#b0c0d0", marginBottom: "0.35rem" }}>
        <code style={{ background: "#0d1626", padding: "0.15rem 0.35rem", borderRadius: "4px", color: "#00e5ff", fontSize: "0.72rem" }}>
          {point.metric_name}
        </code>
      </div>

      {/* Score bar */}
      <div style={{ marginBottom: "0.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.2rem" }}>
          <span style={{ fontSize: "0.67rem", color: "#8899aa", textTransform: "uppercase" }}>Anomaly Score</span>
          <span style={{ fontFamily: "monospace", fontSize: "0.78rem", fontWeight: 700, color }}>{(point.score * 100).toFixed(0)}%</span>
        </div>
        <div style={{ height: "4px", background: "#1a2340", borderRadius: "4px", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${point.score * 100}%`, background: `linear-gradient(90deg, ${color}aa, ${color})`, borderRadius: "4px" }} />
        </div>
      </div>

      <p style={{ fontSize: "0.75rem", color: "#b0c0d0", margin: "0 0 0.4rem 0", lineHeight: 1.5 }}>
        {point.description}
      </p>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.67rem", color: "#607080" }}>
        <span>📍 {point.district}</span>
        <span>{new Date(point.timestamp).toLocaleTimeString()}</span>
      </div>
    </div>
  );
});

// ==============================================================================
// Main GeospatialMap View
// ==============================================================================
export const GeospatialMap: React.FC = () => {
  const [mapData, setMapData] = useState<GeoMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Layer toggles
  const [showClusters, setShowClusters] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showRegions, setShowRegions] = useState(true);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");

  // Side panel
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState<GeoAnomalyPoint | null>(null);

  // Fetch map data
  const loadMapData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGeoMap();
      setMapData(data);
      setLastRefresh(new Date());
    } catch (err: any) {
      setError(err?.message ?? "Failed to load geospatial data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMapData();
    const interval = setInterval(loadMapData, 45_000); // Auto-refresh every 45s
    return () => clearInterval(interval);
  }, [loadMapData]);

  // Derive filtered anomaly points
  const filteredPoints = useMemo(() => {
    return (mapData?.anomaly_points ?? []).filter((p) => {
      if (severityFilter !== "ALL" && p.severity !== severityFilter) return false;
      if (categoryFilter !== "ALL" && p.category !== categoryFilter) return false;
      return true;
    });
  }, [mapData?.anomaly_points, severityFilter, categoryFilter]);

  const severityChipClass = (sv: string) => {
    if (sv === "ALL") return `map-chip ${severityFilter === "ALL" ? "active-all" : ""}`;
    if (sv === "CRITICAL") return `map-chip ${severityFilter === "CRITICAL" ? "active-critical" : ""}`;
    if (sv === "WARNING")  return `map-chip ${severityFilter === "WARNING"  ? "active-warning"  : ""}`;
    return `map-chip ${severityFilter === "INFO" ? "active-info" : ""}`;
  };

  const categoryPillClass = (cat: string) => {
    if (categoryFilter !== cat && cat !== "ALL") return "category-pill";
    const map: Record<string, string> = {
      ALL:                 "category-pill active-info",
      POWER:               "category-pill active-power",
      TRAFFIC:             "category-pill active-traffic",
      WATER:               "category-pill active-water",
      INTERNET:            "category-pill active-internet",
      PUBLIC_INFRASTRUCTURE: "category-pill active-infra",
    };
    return map[cat] ?? "category-pill";
  };

  // Open side panel for a selected anomaly point
  const handleMarkerClick = (point: GeoAnomalyPoint) => {
    setSelectedPoint(point);
    setSidePanelOpen(true);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* ── Page Header ── */}
      <div className="geo-header">
        <div>
          <h2 style={{ fontSize: "1.3rem", fontWeight: 800, marginBottom: "0.2rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Map size={20} color="var(--accent-cyan)" />
            Infrastructure Geo Map
          </h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: 0 }}>
            Real-time anomaly distribution across monitored city zones
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {/* Header Stats */}
          {mapData && (
            <div className="geo-header-stats">
              <div className="geo-stat-chip total">
                <Activity size={12} />
                {mapData.total_anomalies} Total
              </div>
              <div className="geo-stat-chip critical">
                <AlertCircle size={12} />
                {mapData.critical_count} Critical
              </div>
              {mapData.most_affected_region && (
                <div className="geo-stat-chip zone">
                  <Globe size={12} />
                  {mapData.most_affected_region}
                </div>
              )}
            </div>
          )}

          {/* Refresh button */}
          <button
            onClick={loadMapData}
            disabled={loading}
            style={{
              display: "flex", alignItems: "center", gap: "0.4rem",
              padding: "0.45rem 0.9rem", borderRadius: "8px", fontSize: "0.8rem",
              fontWeight: 600, border: "1px solid var(--border-card)", cursor: "pointer",
              background: "hsla(217, 32%, 18%, 0.5)", color: "var(--text-secondary)",
              transition: "all 0.2s", opacity: loading ? 0.6 : 1,
            }}
          >
            <RefreshCw size={13} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* ── Error State ── */}
      {error && (
        <div style={{
          padding: "0.85rem 1.25rem", borderRadius: "10px",
          background: "hsla(346, 100%, 50%, 0.12)", border: "1px solid hsla(346, 100%, 50%, 0.35)",
          color: "var(--status-critical)", fontSize: "0.85rem", marginBottom: "0.75rem",
          display: "flex", alignItems: "center", gap: "0.5rem",
        }}>
          <AlertCircle size={15} />
          {error} — showing synthetic data.
        </div>
      )}

      {/* ── Main Map Wrapper ── */}
      <div className="geo-map-wrapper">
        {/* Leaflet Map */}
        <MapContainer
          center={MAP_CENTER}
          zoom={MAP_ZOOM}
          zoomControl={false}
          style={{ flex: 1, width: "100%", height: "100%" }}
          className="geo-map-container"
        >
          {/* Dark CartoDB base tiles */}
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
            maxZoom={19}
          />

          {/* Custom positioned zoom control */}
          <ZoomControl position="bottomright" />

          {/* Heatmap layer */}
          {mapData && (
            <HeatmapLayer points={mapData.heatmap_points} visible={showHeatmap} />
          )}

          {/* Region boundary polygons */}
          {mapData?.regions.map((region) => (
            <RegionPolygon key={region.region_id} region={region} visible={showRegions} />
          ))}

          {/* Anomaly cluster markers */}
          {showClusters && (
            <MarkerClusterGroup
              chunkedLoading
              showCoverageOnHover={false}
              maxClusterRadius={50}
            >
              {filteredPoints.map((point) => (
                <Marker
                  key={point.id}
                  position={[point.lat, point.lng]}
                  icon={getAnomalyIcon(point.severity, point.category)}
                  eventHandlers={{
                    click: () => handleMarkerClick(point),
                  }}
                >
                  <Popup maxWidth={260}>
                    <AnomalyPopupContent point={point} />
                  </Popup>
                </Marker>
              ))}
            </MarkerClusterGroup>
          )}
        </MapContainer>

        {/* ── Floating Control HUD (top-left) ── */}
        <div className="map-control-hud">
          {/* Layers card */}
          <div className="map-hud-card">
            <div className="map-hud-title">
              <Layers size={10} style={{ display: "inline", marginRight: "0.3rem" }} />
              Map Layers
            </div>
            <div className="map-layer-toggle">
              <span>Anomaly Clusters</span>
              <label className="toggle-switch">
                <input type="checkbox" checked={showClusters} onChange={e => setShowClusters(e.target.checked)} />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="map-layer-toggle">
              <span>Heat Intensity</span>
              <label className="toggle-switch">
                <input type="checkbox" checked={showHeatmap} onChange={e => setShowHeatmap(e.target.checked)} />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="map-layer-toggle">
              <span>Zone Regions</span>
              <label className="toggle-switch">
                <input type="checkbox" checked={showRegions} onChange={e => setShowRegions(e.target.checked)} />
                <span className="toggle-slider" />
              </label>
            </div>
          </div>

          {/* Severity filter card */}
          <div className="map-hud-card">
            <div className="map-hud-title">
              <Filter size={10} style={{ display: "inline", marginRight: "0.3rem" }} />
              Severity Filter
            </div>
            <div className="map-filter-chips">
              {["ALL", "CRITICAL", "WARNING", "INFO"].map((sv) => (
                <button
                  key={sv}
                  className={severityChipClass(sv)}
                  onClick={() => setSeverityFilter(sv)}
                >
                  {sv}
                </button>
              ))}
            </div>
          </div>

          {/* Category filter card */}
          <div className="map-hud-card">
            <div className="map-hud-title">Category Filter</div>
            <div className="map-category-pills">
              {["ALL", "POWER", "TRAFFIC", "WATER", "INTERNET", "PUBLIC_INFRASTRUCTURE"].map((cat) => (
                <button
                  key={cat}
                  className={categoryPillClass(cat)}
                  onClick={() => setCategoryFilter(cat)}
                >
                  {cat === "ALL" ? "ALL" : cat === "PUBLIC_INFRASTRUCTURE" ? "INFRA" : cat}
                </button>
              ))}
            </div>
          </div>

          {/* Side panel trigger */}
          <button
            onClick={() => setSidePanelOpen(!sidePanelOpen)}
            style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "0.75rem 1rem", borderRadius: "12px",
              background: sidePanelOpen
                ? "hsla(180, 100%, 45%, 0.15)"
                : "hsla(222, 47%, 7%, 0.92)",
              border: `1px solid ${sidePanelOpen ? "var(--accent-cyan)" : "var(--border-card)"}`,
              color: sidePanelOpen ? "var(--accent-cyan)" : "var(--text-secondary)",
              cursor: "pointer", fontSize: "0.82rem", fontWeight: 600,
              backdropFilter: "blur(16px)", transition: "all 0.25s",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <AlertCircle size={14} />
              Anomaly Feed
              <span style={{
                padding: "0.1rem 0.45rem", borderRadius: "10px",
                background: "hsla(346, 100%, 50%, 0.25)",
                color: "var(--status-critical)", fontFamily: "monospace", fontSize: "0.72rem",
              }}>
                {filteredPoints.length}
              </span>
            </span>
            <ChevronRight size={14} style={{ transform: sidePanelOpen ? "rotate(180deg)" : "none", transition: "transform 0.25s" }} />
          </button>
        </div>

        {/* ── Slide-in Side Panel ── */}
        <div className={`map-side-panel ${sidePanelOpen ? "open" : ""}`}>
          <div className="side-panel-header">
            <div>
              <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>
                Live Anomaly Feed
              </div>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.1rem" }}>
                {filteredPoints.length} incidents
                {severityFilter !== "ALL" && ` · ${severityFilter}`}
                {categoryFilter !== "ALL" && ` · ${categoryFilter}`}
              </div>
            </div>
            <button
              onClick={() => setSidePanelOpen(false)}
              style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: "0.25rem" }}
            >
              <X size={16} />
            </button>
          </div>

          <div className="side-panel-body">
            {filteredPoints.length === 0 ? (
              <div style={{ textAlign: "center", padding: "2rem 1rem", color: "var(--text-muted)", fontSize: "0.82rem" }}>
                No anomalies match current filters.
              </div>
            ) : (
              filteredPoints
                .sort((a, b) => b.score - a.score)
                .map((point) => {
                  const color = SEVERITY_COLORS[point.severity] ?? "#00e5ff";
                  const catColor = CATEGORY_COLORS[point.category] ?? "#00e5ff";
                  const isSelected = selectedPoint?.id === point.id;
                  return (
                    <div
                      key={point.id}
                      className={`anomaly-geo-card ${isSelected ? "highlighted" : ""}`}
                      onClick={() => setSelectedPoint(isSelected ? null : point)}
                    >
                      {/* Top row */}
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
                        <div style={{ width: 7, height: 7, borderRadius: "50%", background: color, flexShrink: 0 }} />
                        <span style={{ fontSize: "0.72rem", fontWeight: 700, color, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                          {point.severity}
                        </span>
                        <span style={{
                          marginLeft: "auto", padding: "0.08rem 0.4rem", borderRadius: "8px",
                          fontSize: "0.6rem", fontWeight: 700,
                          background: `${catColor}22`, color: catColor, border: `1px solid ${catColor}44`
                        }}>
                          {CATEGORY_ICONS[point.category]}
                        </span>
                      </div>

                      {/* Metric */}
                      <div style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
                        {point.metric_name}
                      </div>

                      {/* Score mini bar */}
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
                        <div style={{ flex: 1, height: "3px", background: "hsla(217, 32%, 18%, 0.6)", borderRadius: "3px", overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${point.score * 100}%`, background: color, borderRadius: "3px" }} />
                        </div>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color, fontWeight: 700 }}>
                          {(point.score * 100).toFixed(0)}%
                        </span>
                      </div>

                      <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", margin: "0 0 0.35rem 0", lineHeight: 1.4 }}>
                        {point.description}
                      </p>

                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", color: "var(--text-muted)" }}>
                        <span>📍 {point.district}</span>
                        <span>{new Date(point.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  );
                })
            )}
          </div>
        </div>

        {/* ── Bottom Stats Bar ── */}
        <div className="map-stats-bar">
          <div className="stats-bar-item">
            <Activity size={12} />
            <span>Anomalies:</span>
            <span className="stats-bar-value">{filteredPoints.length}</span>
          </div>
          <div className="stats-bar-item">
            <AlertCircle size={12} />
            <span>Critical:</span>
            <span className={`stats-bar-value ${filteredPoints.filter(p => p.severity === "CRITICAL").length > 0 ? "critical" : "safe"}`}>
              {filteredPoints.filter(p => p.severity === "CRITICAL").length}
            </span>
          </div>
          {mapData?.most_affected_region && (
            <div className="stats-bar-item">
              <Globe size={12} />
              <span>Hotspot:</span>
              <span className="stats-bar-value">{mapData.most_affected_region}</span>
            </div>
          )}
          <div className="stats-bar-item" style={{ marginLeft: "auto" }}>
            <Clock size={12} />
            <span>Updated:</span>
            <span className="stats-bar-value">{lastRefresh.toLocaleTimeString()}</span>
          </div>
        </div>

        {/* Loading overlay */}
        {loading && (
          <div style={{
            position: "absolute", inset: 0, zIndex: 2000,
            background: "hsla(224, 71%, 4%, 0.65)", backdropFilter: "blur(4px)",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexDirection: "column", gap: "1rem",
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: "50%",
              border: "3px solid hsla(180, 100%, 45%, 0.15)",
              borderTop: "3px solid var(--accent-cyan)",
              animation: "spin 0.9s linear infinite",
            }} />
            <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              Fetching geospatial telemetry…
            </div>
          </div>
        )}
      </div>

      {/* ── spin keyframe (inline) ── */}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default GeospatialMap;
