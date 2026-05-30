import React, { useState, useEffect } from "react";
import { 
  MessageSquare, 
  RefreshCw, 
  Activity, 
  ShieldAlert, 
  Heart, 
  User, 
  Clock, 
  AlertTriangle,
  Zap, 
  Navigation, 
  Droplet, 
  Wifi, 
  Sliders,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import SkeletonLoader from "../common/SkeletonLoader";
import { 
  getSocialComplaints, 
  getSocialAnalytics, 
  triggerSocialIngest, 
  SocialComplaint, 
  SocialAnalyticsResponse 
} from "../../api/social";

export const SocialMonitoring: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [complaints, setComplaints] = useState<SocialComplaint[]>([]);
  const [analytics, setAnalytics] = useState<SocialAnalyticsResponse | null>(null);
  
  // Filter states
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("ALL");
  
  // Card Expansion states
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);

  const loadData = async (showSyncSpinner = false) => {
    if (showSyncSpinner) setSyncing(true);
    try {
      const activeCat = selectedCategory === "ALL" ? undefined : selectedCategory;
      const activeSev = selectedSeverity === "ALL" ? undefined : selectedSeverity;

      const complaintsData = await getSocialComplaints(activeCat, activeSev);
      const analyticsData = await getSocialAnalytics();

      setComplaints(complaintsData);
      setAnalytics(analyticsData);
    } catch (err) {
      console.error("Failed to load social signals telemetry:", err);
    } finally {
      setLoading(false);
      setSyncing(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-poll complaints every 10 seconds
    const interval = setInterval(() => {
      loadData();
    }, 10000);
    return () => clearInterval(interval);
  }, [selectedCategory, selectedSeverity]);

  const handleIngestClick = async () => {
    setSyncing(true);
    try {
      await triggerSocialIngest();
      // Reload lists instantly
      await loadData();
    } catch (err) {
      console.error("Failed to trigger social signals manual ingestion:", err);
    } finally {
      setSyncing(false);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toUpperCase()) {
      case "POWER":                 return <Zap size={14} color="hsl(35, 100%, 50%)" />;
      case "TRAFFIC":               return <Navigation size={14} color="hsl(200, 95%, 55%)" />;
      case "WATER":                 return <Droplet size={14} color="hsl(180, 100%, 45%)" />;
      case "INTERNET":              return <Wifi size={14} color="hsl(265, 89%, 60%)" />;
      case "PUBLIC_INFRASTRUCTURE": return <Sliders size={14} color="hsl(145, 80%, 45%)" />;
      default:                      return <MessageSquare size={14} color="var(--text-secondary)" />;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category.toUpperCase()) {
      case "POWER":                 return "Power Outage";
      case "TRAFFIC":               return "Traffic Flow";
      case "WATER":                 return "Water Supply";
      case "INTERNET":              return "Internet/Wifi";
      case "PUBLIC_INFRASTRUCTURE": return "Public Utility";
      default:                      return category;
    }
  };

  const getSeverityBadgeColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL": return "var(--status-critical)";
      case "WARNING":  return "var(--status-warning)";
      case "INFO":     return "var(--status-safe)";
      default:         return "var(--text-secondary)";
    }
  };

  const getSentimentEmoji = (score: number) => {
    if (score < 0.25) return "🛑 Highly Critical";
    if (score < 0.50) return "⚠️ Negatively Alert";
    if (score < 0.75) return "💬 Neutral Signal";
    return "✅ Positive/Restored";
  };

  return (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      
      {/* 1. Header Section */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "2rem" }}>
            <MessageSquare color="var(--accent-cyan)" /> NLP Complaint Classification
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: "0.25rem" }}>
            Real-time NLP-based complaint analysis, dynamic incident clustering, and urgency telemetry
          </p>
        </div>

        <button 
          className="btn-primary" 
          onClick={handleIngestClick} 
          disabled={syncing}
          style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: "0.5rem",
            padding: "0.75rem 1.25rem",
            background: "var(--accent-blue)",
            color: "var(--text-primary)",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontWeight: 600,
            opacity: syncing ? 0.7 : 1,
            transition: "var(--transition-smooth)"
          }}
        >
          <RefreshCw className={syncing ? "animate-spin" : ""} size={16} />
          <span>{syncing ? "Analyzing Feeds..." : "Trigger Ingestion"}</span>
        </button>
      </div>

      {/* 2. Analytics Summary Grid */}
      <div style={{ 
        display: "grid", 
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", 
        gap: "1.25rem" 
      }}>
        {loading ? (
          <>
            <SkeletonLoader height="100px" />
            <SkeletonLoader height="100px" />
            <SkeletonLoader height="100px" />
          </>
        ) : (
          <>
            {/* Card 1: Total complaints */}
            <div className="card" style={{ display: "flex", alignItems: "center", gap: "1.25rem", padding: "1.25rem" }}>
              <div style={{ 
                background: "hsla(199, 89%, 48%, 0.1)", 
                border: "1px solid rgba(199, 89, 48, 0.2)",
                padding: "0.75rem", 
                borderRadius: "8px" 
              }}>
                <Activity color="var(--accent-blue)" size={24} />
              </div>
              <div>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)", display: "block" }}>Total Extracted Complaints</span>
                <span style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  {analytics?.total_complaints ?? 0}
                </span>
              </div>
            </div>

            {/* Card 2: Average Sentiment */}
            <div className="card" style={{ display: "flex", alignItems: "center", gap: "1.25rem", padding: "1.25rem" }}>
              <div style={{ 
                background: "hsla(180, 100%, 45%, 0.1)", 
                border: "1px solid rgba(180, 100, 45, 0.2)",
                padding: "0.75rem", 
                borderRadius: "8px" 
              }}>
                <Heart color="var(--accent-cyan)" size={24} />
              </div>
              <div>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)", display: "block" }}>Mean Signal Sentiment</span>
                <span style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  {Math.round((analytics?.average_sentiment ?? 0) * 100)}%
                </span>
              </div>
            </div>

            {/* Card 3: Active Severity Alert */}
            <div className="card" style={{ display: "flex", alignItems: "center", gap: "1.25rem", padding: "1.25rem" }}>
              <div style={{ 
                background: "hsla(346, 100%, 50%, 0.1)", 
                border: "1px solid rgba(346, 100, 50, 0.2)",
                padding: "0.75rem", 
                borderRadius: "8px" 
              }}>
                <ShieldAlert color="var(--status-critical)" size={24} />
              </div>
              <div>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)", display: "block" }}>Critical Disruptions</span>
                <span style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--status-critical)" }}>
                  {analytics?.severity_breakdown.find(s => s.severity === "CRITICAL")?.count ?? 0}
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* 3. Filter Controls Row */}
      <div className="card" style={{ 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "center", 
        padding: "1rem 1.25rem", 
        flexWrap: "wrap",
        gap: "1rem"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Sliders size={16} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Filter Complaints Feed</span>
        </div>

        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          {/* Category Filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Category:</span>
            <select 
              value={selectedCategory} 
              onChange={(e) => setSelectedCategory(e.target.value)}
              style={{
                background: "var(--bg-deep)",
                border: "1px solid var(--border-card)",
                color: "var(--text-primary)",
                padding: "0.4rem 0.75rem",
                borderRadius: "4px",
                fontSize: "0.85rem"
              }}
            >
              <option value="ALL">All Categories</option>
              <option value="POWER">Power Outage</option>
              <option value="TRAFFIC">Traffic Jam</option>
              <option value="WATER">Water Leakage</option>
              <option value="INTERNET">Internet Outage</option>
              <option value="PUBLIC_INFRASTRUCTURE">Public Infrastructure</option>
              <option value="GENERAL">General</option>
            </select>
          </div>

          {/* Severity Filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Severity:</span>
            <select 
              value={selectedSeverity} 
              onChange={(e) => setSelectedSeverity(e.target.value)}
              style={{
                background: "var(--bg-deep)",
                border: "1px solid var(--border-card)",
                color: "var(--text-primary)",
                padding: "0.4rem 0.75rem",
                borderRadius: "4px",
                fontSize: "0.85rem"
              }}
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
            </select>
          </div>
        </div>
      </div>

      {/* 4. Split Layout - Complaint List & Category Charts */}
      <div style={{ 
        display: "grid", 
        gridTemplateColumns: "1fr",
        gap: "1.5rem",
        alignItems: "start"
      }} className="lg:grid-cols-3">
        
        {/* Left Column: Live Complaints list (span 2 if grid-cols-3) */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }} className="lg:col-span-2">
          <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1.1rem" }}>
            <span>Live Social Complaint Stream</span>
            {syncing && <span style={{ fontSize: "0.8rem", color: "var(--accent-cyan)", fontWeight: 400 }}>(Ingesting...)</span>}
          </h3>

          {loading ? (
            <SkeletonLoader height="300px" />
          ) : complaints.length === 0 ? (
            <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-secondary)" }}>
              <MessageSquare size={48} style={{ margin: "0 auto 1rem", opacity: 0.3 }} />
              <p>No complaints matching the selected filters found.</p>
            </div>
          ) : (
            complaints.map((c) => {
              const isExpanded = expandedCardId === c.id;
              
              return (
                <div 
                  key={c.id} 
                  className="card" 
                  style={{ 
                    padding: "1.25rem", 
                    display: "flex", 
                    flexDirection: "column", 
                    gap: "0.75rem",
                    transition: "var(--transition-smooth)",
                    borderLeft: `4px solid ${getSeverityBadgeColor(c.severity)}`
                  }}
                >
                  {/* Post Top Details */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <div style={{ background: "var(--border-card)", padding: "0.25rem", borderRadius: "50%" }}>
                        <User size={14} color="var(--text-secondary)" />
                      </div>
                      <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>@{c.author}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                        <Clock size={10} /> {new Date(c.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <span 
                      style={{ 
                        fontSize: "0.7rem", 
                        fontWeight: 700, 
                        padding: "0.2rem 0.5rem", 
                        borderRadius: "4px",
                        background: `rgba(${c.severity === "CRITICAL" ? "239, 68, 68" : c.severity === "WARNING" ? "245, 158, 11" : "34, 197, 94"}, 0.1)`,
                        color: getSeverityBadgeColor(c.severity),
                        border: `1px solid ${getSeverityBadgeColor(c.severity)}`
                      }}
                    >
                      {c.severity}
                    </span>
                  </div>

                  {/* Text body */}
                  <p style={{ fontSize: "0.95rem", color: "var(--text-primary)", lineHeight: 1.5 }}>
                    {c.text}
                  </p>

                  {/* Urgency Progress bar */}
                  <div style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    gap: "0.75rem", 
                    background: "rgba(255, 255, 255, 0.02)", 
                    padding: "0.4rem 0.75rem", 
                    borderRadius: "6px", 
                    border: "1px solid var(--border-card)" 
                  }}>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", minWidth: "100px" }}>NLP Urgency:</span>
                    <div style={{ background: "var(--bg-deep)", height: "6px", flex: 1, borderRadius: "3px", overflow: "hidden" }}>
                      <div style={{ 
                        width: `${c.urgency_score ?? 0}%`, 
                        background: (c.urgency_score ?? 0) > 75 ? "var(--status-critical)" : (c.urgency_score ?? 0) > 40 ? "var(--status-warning)" : "var(--status-safe)", 
                        height: "100%",
                        transition: "width 0.6s ease-out"
                      }} />
                    </div>
                    <span style={{ 
                      fontSize: "0.85rem", 
                      fontWeight: 700, 
                      color: (c.urgency_score ?? 0) > 75 ? "var(--status-critical)" : (c.urgency_score ?? 0) > 40 ? "var(--status-warning)" : "var(--status-safe)" 
                    }}>
                      {Math.round(c.urgency_score ?? 0)}/100
                    </span>
                  </div>

                  {/* Badges footer */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem", paddingTop: "0.5rem", borderTop: "1px solid hsla(223, 47%, 16%, 0.4)" }}>
                    <div style={{ display: "flex", gap: "0.75rem" }}>
                      {/* Category */}
                      <span style={{ display: "flex", alignItems: "center", gap: "0.25rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {getCategoryIcon(c.category)}
                        <span>{getCategoryLabel(c.category)}</span>
                      </span>

                      {/* Matched Keyword */}
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        Trigger: <code>{c.matched_keyword}</code>
                      </span>
                    </div>

                    <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      Sentiment: <span style={{ fontWeight: 600, color: c.sentiment_score < 0.25 ? "var(--status-critical)" : c.sentiment_score < 0.5 ? "var(--status-warning)" : "var(--status-safe)" }}>{Math.round(c.sentiment_score * 100)}%</span> ({getSentimentEmoji(c.sentiment_score)})
                    </span>
                  </div>

                  {/* Explainable AI dropdown */}
                  <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.25rem" }}>
                    <button 
                      onClick={() => setExpandedCardId(isExpanded ? null : c.id)}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--accent-cyan)",
                        fontSize: "0.8rem",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.25rem",
                        padding: "0.25rem 0",
                        outline: "none"
                      }}
                    >
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      <span>{isExpanded ? "Hide AI Diagnostics" : "Explain AI Classification"}</span>
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="fade-in" style={{
                      background: "var(--bg-deep)",
                      border: "1px solid var(--border-card)",
                      borderRadius: "6px",
                      padding: "0.75rem 1rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.6rem",
                      marginTop: "0.25rem"
                    }}>
                      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                        <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Keywords Extracted:</span>
                        <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
                          {(c.keywords || c.matched_keyword).split(", ").map((kw, i) => (
                            <span key={i} style={{ 
                              fontSize: "0.7rem", 
                              background: "rgba(0, 242, 254, 0.08)", 
                              border: "1px solid rgba(0, 242, 254, 0.2)", 
                              padding: "0.1rem 0.4rem", 
                              borderRadius: "4px", 
                              color: "var(--accent-cyan)" 
                            }}>
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                      
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>NLP Explainable Rationale:</span>
                        <p style={{ fontSize: "0.8rem", color: "var(--text-primary)", lineHeight: 1.4, margin: 0 }}>
                          {c.explanation || "System determined classification using standard lexical mapping patterns."}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Category Distribution */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          
          {/* Section A: Category Breakdowns */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <h3 style={{ fontSize: "1.1rem" }}>NLP Disruption Analytics</h3>
            
            <div className="card" style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>Complaint Category Breakdown</span>
              
              {loading ? (
                <SkeletonLoader height="150px" />
              ) : !analytics || analytics.category_breakdown.length === 0 ? (
                <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>No analytics metrics compiled.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                  {analytics.category_breakdown.map((item) => {
                    const maxCount = Math.max(...analytics.category_breakdown.map(i => i.count)) || 1;
                    const percentWidth = (item.count / maxCount) * 100;
                    
                    return (
                      <div key={item.category} style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                          <span style={{ display: "flex", alignItems: "center", gap: "0.25rem", fontWeight: 600 }}>
                            {getCategoryIcon(item.category)}
                            {getCategoryLabel(item.category)}
                          </span>
                          <span style={{ color: "var(--text-secondary)" }}>{item.count} complaints</span>
                        </div>
                        
                        {/* Premium Bar Slider */}
                        <div style={{ 
                          background: "var(--bg-deep)", 
                          height: "8px", 
                          borderRadius: "4px", 
                          width: "100%",
                          overflow: "hidden",
                          border: "1px solid var(--border-card)"
                        }}>
                          <div style={{ 
                            width: `${percentWidth}%`,
                            background: item.category === "POWER" ? "hsl(35, 100%, 50%)" : 
                                        item.category === "TRAFFIC" ? "hsl(200, 95%, 55%)" :
                                        item.category === "WATER" ? "hsl(180, 100%, 45%)" :
                                        item.category === "INTERNET" ? "hsl(265, 89%, 60%)" :
                                        item.category === "PUBLIC_INFRASTRUCTURE" ? "hsl(145, 80%, 45%)" :
                                        "var(--text-muted)",
                            height: "100%",
                            borderRadius: "4px",
                            transition: "width 0.8s ease-out"
                          }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              
              <div style={{ height: "1px", background: "var(--border-card)", margin: "0.5rem 0" }} />
              
              {/* Sentiment Gauge Explanation */}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>NLP Diagnostics Note</span>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                  Sentiment calculations are powered by localized vocabulary parsing. Complaining text patterns are matched against 
                  negation matrices to trigger downstream pre-emptive failure alerts.
                </p>
              </div>
            </div>
          </div>

          {/* Section B: dynamic incident clusters */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <h3 style={{ fontSize: "1.1rem" }}>Active Incident Clusters</h3>
            
            <div className="card" style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
              <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>Dynamic Clusters (KMeans)</span>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.4, margin: "0 0 0.5rem 0" }}>
                Complaints are clustered dynamically based on word-frequency. This maps localized events into cohesive operational hubs.
              </p>

              {loading ? (
                <SkeletonLoader height="150px" />
              ) : !analytics || !analytics.clusters || analytics.clusters.length === 0 ? (
                <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>No active clusters found.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {analytics.clusters.map((cluster) => (
                    <div 
                      key={cluster.id} 
                      style={{
                        background: "var(--bg-deep)",
                        border: "1px solid var(--border-card)",
                        padding: "0.75rem 1rem",
                        borderRadius: "6px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.4rem"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>
                          {cluster.name}
                        </span>
                        <span style={{ 
                          fontSize: "0.7rem", 
                          background: "rgba(0, 242, 254, 0.08)", 
                          border: "1px solid rgba(0, 242, 254, 0.15)",
                          padding: "0.1rem 0.4rem", 
                          borderRadius: "10px", 
                          color: "var(--accent-cyan)",
                          fontWeight: 600
                        }}>
                          {cluster.count} posts
                        </span>
                      </div>
                      
                      <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap", marginTop: "0.25rem" }}>
                        {cluster.keywords.map((kw, i) => (
                          <span key={i} style={{ 
                            fontSize: "0.65rem", 
                            background: "rgba(255, 255, 255, 0.02)", 
                            border: "1px solid rgba(255, 255, 255, 0.06)", 
                            padding: "0.05rem 0.35rem", 
                            borderRadius: "3px", 
                            color: "var(--text-muted)" 
                          }}>
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default SocialMonitoring;
