import React, { useState, lazy, Suspense } from "react";
import { ApiStatusProvider } from "./context/ApiStatusContext";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Sidebar from "./components/layout/Sidebar";
import { ViewTab } from "./types/navigation";
import { ROLE_TABS, VIEW_LABELS } from "./constants/navigation";
import RouteGuard from "./components/common/RouteGuard";
import TopBar from "./components/layout/TopBar";
import ErrorBoundary from "./components/common/ErrorBoundary";
import LoadingSpinner from "./components/common/LoadingSpinner";
import Login from "./components/views/Login";
import { ThemeProvider, useTheme } from "./context/ThemeContext";

// Lazy-loaded modular dashboard tab views for optimal bundle code splitting
const InfrastructureHealth = lazy(() => import("./components/views/InfrastructureHealth"));
const LiveMonitoring = lazy(() => import("./components/views/LiveMonitoring"));
const AnomalyAlerts = lazy(() => import("./components/views/AnomalyAlerts"));
const Forecasting = lazy(() => import("./components/views/Forecasting"));
const CorrelationAnalytics = lazy(() => import("./components/views/CorrelationAnalytics"));
const SocialMonitoring = lazy(() => import("./components/views/SocialMonitoring"));
const GeospatialMap = lazy(() => import("./components/views/GeospatialMap"));
const HistoricalReplay = lazy(() => import("./components/views/HistoricalReplay"));
const ExplainableAI = lazy(() => import("./components/views/ExplainableAI"));
const BenchmarkDashboard = lazy(() => import("./components/views/BenchmarkDashboard"));
const NotificationsControl = lazy(() => import("./components/views/NotificationsControl"));
const ReportCenter = lazy(() => import("./components/views/ReportCenter"));
const AssetManager = lazy(() => import("./components/views/AssetManager"));
const SimulationEngine = lazy(() => import("./components/views/SimulationEngine"));
const SystemSettings = lazy(() => import("./components/views/SystemSettings"));
const DocumentationView = lazy(() => import("./components/views/DocumentationView"));

const AppContent: React.FC = () => {
  const { theme } = useTheme();
  const { isAuthenticated, loading, user } = useAuth();
  const [activeTab, setActiveTab] = useState<ViewTab>("health");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  if (loading) {
    return (
      <div className="full-center">
        <LoadingSpinner size={48} label="Decrypting secure session..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  const handleTabChange = (tab: ViewTab) => {
    setActiveTab(tab);
    setSidebarOpen(false);
  };

  const renderActiveView = () => {
    switch (activeTab) {
      case "health":      return <InfrastructureHealth />;
      case "monitoring":  return <LiveMonitoring />;
      case "alerts":      return <AnomalyAlerts />;
      case "forecasting": return <Forecasting />;
      case "correlation": return <CorrelationAnalytics />;
      case "social":      return <SocialMonitoring />;
      case "geomap":      return <GeospatialMap />;
      case "replay":      return <HistoricalReplay />;
      case "xai":         return <ExplainableAI />;
      case "benchmark":   return <BenchmarkDashboard />;
      case "notifications": return <NotificationsControl />;
      case "reports":       return <ReportCenter />;
      case "assets":        return <AssetManager />;
      case "simulation":    return <SimulationEngine />;
      case "settings":      return <SystemSettings />;
      case "docs":          return <DocumentationView />;
      default:            return <InfrastructureHealth />;
    }
  };

  return (
    <div className={`layout-wrapper theme-${theme}`}>
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        isOpen={sidebarOpen}
      />

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="mobile-sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="main-content">
        <TopBar
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
        />

        <div className="container flex-1">
          <ErrorBoundary viewLabel={VIEW_LABELS[activeTab]}>
            <Suspense fallback={<LoadingSpinner label={`Initializing ${VIEW_LABELS[activeTab]}...`} />}>
              <RouteGuard role={user?.role || "VIEWER"} tab={activeTab}>
                <div key={activeTab} className="animate-slide-up animate-fade-in" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
                  {renderActiveView()}
                </div>
              </RouteGuard>
            </Suspense>
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
};

export const App: React.FC = () => (
  <ThemeProvider>
    <ApiStatusProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ApiStatusProvider>
  </ThemeProvider>
);

export default App;

