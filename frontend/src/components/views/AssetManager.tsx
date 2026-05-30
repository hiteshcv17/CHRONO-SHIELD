import React, { useState, useEffect } from "react";
import { 
  Database,
  Plus, 
  Search, 
  Filter, 
  Wrench, 
  Trash2, 
  Cpu, 
  Activity, 
  Droplet, 
  Bell, 
  MapPin, 
  Calendar, 
  X, 
  Edit3, 
  Save, 
  AlertTriangle,
  FileText
} from "lucide-react";
import { 
  getAssets, 
  registerAsset, 
  updateAsset, 
  decommissionAsset
} from "../../api/asset";
import { Asset, AssetCreateInput } from "../../types/domain";
import { useAuth } from "../../context/AuthContext";

export const AssetManager: React.FC = () => {
  const { user } = useAuth();
  const userRole = user?.role || "VIEWER";
  const canWrite = userRole === "ANALYST" || userRole === "ADMIN";
  const canDelete = userRole === "ADMIN";

  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterRegion, setFilterRegion] = useState("");

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);

  // Form states (Create / Edit)
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState<"TRANSFORMER" | "TRAFFIC_ZONE" | "WATER_PIPELINE" | "PUBLIC_SYSTEM">("TRANSFORMER");
  const [formStatus, setFormStatus] = useState<"NOMINAL" | "WARNING" | "CRITICAL" | "MAINTENANCE" | "DECOMMISSIONED">("NOMINAL");
  const [formRegion, setFormRegion] = useState("");
  const [formMetadata, setFormMetadata] = useState<{ key: string; value: string }[]>([
    { key: "", value: "" }
  ]);

  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchAssetsList = async () => {
    try {
      setLoading(true);
      const data = await getAssets({
        asset_type: filterType || undefined,
        status: filterStatus || undefined,
        region: filterRegion || undefined,
        name: searchTerm || undefined
      });
      setAssets(data);
    } catch (e) {
      console.error("Failed to load infrastructure assets", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssetsList();
  }, [filterType, filterStatus, filterRegion, searchTerm]);

  // Open Create Modal
  const handleOpenCreate = () => {
    setFormName("");
    setFormType("TRANSFORMER");
    setFormStatus("NOMINAL");
    setFormRegion("");
    setFormMetadata([{ key: "", value: "" }]);
    setErrorMsg("");
    setIsCreateOpen(true);
  };

  // Open Edit Modal
  const handleOpenEdit = (asset: Asset) => {
    setFormName(asset.name);
    setFormType(asset.asset_type);
    setFormStatus(asset.status);
    setFormRegion(asset.region);
    
    // Map record to array of keys/values
    const metaArray = Object.entries(asset.dynamic_metadata || {}).map(([k, v]) => ({
      key: k,
      value: typeof v === "object" ? JSON.stringify(v) : String(v)
    }));
    
    setFormMetadata(metaArray.length > 0 ? metaArray : [{ key: "", value: "" }]);
    setErrorMsg("");
    setEditingAsset(asset);
  };

  // Add Metadata key-value row
  const addMetadataRow = () => {
    setFormMetadata([...formMetadata, { key: "", value: "" }]);
  };

  // Remove Metadata row
  const removeMetadataRow = (index: number) => {
    const next = [...formMetadata];
    next.splice(index, 1);
    setFormMetadata(next.length > 0 ? next : [{ key: "", value: "" }]);
  };

  // Change metadata row field
  const handleMetadataChange = (index: number, field: "key" | "value", val: string) => {
    const next = [...formMetadata];
    next[index][field] = val;
    setFormMetadata(next);
  };

  // Construct metadata dictionary from form array
  const constructMetadataDict = () => {
    const dict: Record<string, any> = {};
    for (const item of formMetadata) {
      if (item.key.trim()) {
        const val = item.value.trim();
        // Try parsing JSON or numbers if possible, fallback to string
        if (val === "true") dict[item.key] = true;
        else if (val === "false") dict[item.key] = false;
        else if (!isNaN(Number(val)) && val !== "") dict[item.key] = Number(val);
        else {
          try {
            dict[item.key] = JSON.parse(val);
          } catch {
            dict[item.key] = val;
          }
        }
      }
    }
    return dict;
  };

  // Submit Asset Creation
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");
    if (!formName.trim() || !formRegion.trim()) {
      setErrorMsg("Asset Name and Region are required.");
      return;
    }
    setSubmitting(true);

    try {
      const meta = constructMetadataDict();
      const payload: AssetCreateInput = {
        name: formName,
        asset_type: formType,
        status: formStatus,
        region: formRegion,
        dynamic_metadata: Object.keys(meta).length > 0 ? meta : null
      };

      await registerAsset(payload);
      setSuccessMsg("Infrastructure asset registered successfully.");
      setTimeout(() => setSuccessMsg(""), 3000);
      setIsCreateOpen(false);
      fetchAssetsList();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to register new infrastructure asset.");
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Asset Update
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAsset) return;
    setErrorMsg("");
    setSuccessMsg("");
    if (!formName.trim() || !formRegion.trim()) {
      setErrorMsg("Asset Name and Region are required.");
      return;
    }
    setSubmitting(true);

    try {
      const meta = constructMetadataDict();
      await updateAsset(editingAsset.id, {
        name: formName,
        asset_type: formType,
        status: formStatus,
        region: formRegion,
        dynamic_metadata: Object.keys(meta).length > 0 ? meta : null
      });

      setSuccessMsg("Infrastructure asset updated successfully.");
      setTimeout(() => setSuccessMsg(""), 3000);
      setEditingAsset(null);
      fetchAssetsList();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update infrastructure asset.");
    } finally {
      setSubmitting(false);
    }
  };

  // Decommission Asset
  const handleDelete = async (assetId: string, name: string) => {
    if (!window.confirm(`Are you sure you want to decommission and delete asset '${name}'?`)) {
      return;
    }
    try {
      await decommissionAsset(assetId);
      setSuccessMsg("Asset decommissioned successfully.");
      setTimeout(() => setSuccessMsg(""), 3000);
      fetchAssetsList();
    } catch (err: any) {
      alert(err.message || "Failed to decommission asset.");
    }
  };

  // Get Type styling
  const getTypeDetails = (type: string) => {
    switch (type) {
      case "TRANSFORMER":
        return { icon: <Cpu size={18} />, color: "var(--accent-cyan)", label: "Transformer Node" };
      case "TRAFFIC_ZONE":
        return { icon: <Activity size={18} />, color: "var(--accent-blue)", label: "Traffic Monitor" };
      case "WATER_PIPELINE":
        return { icon: <Droplet size={18} />, color: "var(--accent-purple)", label: "Hydraulic Pipeline" };
      case "PUBLIC_SYSTEM":
        return { icon: <Bell size={18} />, color: "var(--accent-orange)", label: "Siren / Alert Array" };
      default:
        return { icon: <Database size={18} />, color: "var(--text-muted)", label: "Infrastructure Item" };
    }
  };

  // Get Status Badge styling
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "NOMINAL":
        return "badge-success";
      case "WARNING":
        return "badge-warning";
      case "CRITICAL":
        return "badge-danger";
      case "MAINTENANCE":
        return "badge-info";
      default:
        return "badge-secondary";
    }
  };

  // Calculate totals for KPI cards
  const totalCount = assets.length;
  const criticalCount = assets.filter(a => a.status === "CRITICAL").length;
  const warningCount = assets.filter(a => a.status === "WARNING").length;
  const nominalCount = assets.filter(a => a.status === "NOMINAL").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header section */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2>Infrastructure Asset Registry</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Monitor physical nodes, manage metadata payloads, and oversee sector region mappings.
          </p>
        </div>
        {canWrite && (
          <button onClick={handleOpenCreate} className="btn btn-primary" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Plus size={16} />
            Register Asset
          </button>
        )}
      </div>

      {/* KPI Cards Grid */}
      <div className="dashboard-grid">
        <div className="card col-3" style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "1.25rem" }}>
          <div style={{ background: "rgba(6, 182, 212, 0.1)", border: "1px solid rgba(6, 182, 212, 0.2)", width: "44px", height: "44px", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Database size={20} color="var(--accent-cyan)" />
          </div>
          <div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Total Assets</span>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: "0.2rem" }}>{totalCount}</h3>
          </div>
        </div>

        <div className="card col-3" style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "1.25rem" }}>
          <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.2)", width: "44px", height: "44px", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Activity size={20} color="var(--status-nominal)" />
          </div>
          <div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Nominal</span>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: "0.2rem", color: "var(--status-nominal)" }}>{nominalCount}</h3>
          </div>
        </div>

        <div className="card col-3" style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "1.25rem" }}>
          <div style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.2)", width: "44px", height: "44px", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <AlertTriangle size={20} color="var(--status-warning)" />
          </div>
          <div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Warnings</span>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: "0.2rem", color: "var(--status-warning)" }}>{warningCount}</h3>
          </div>
        </div>

        <div className="card col-3" style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "1.25rem" }}>
          <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", width: "44px", height: "44px", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <AlertTriangle size={20} color="var(--status-critical)" />
          </div>
          <div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Critical Incidents</span>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: "0.2rem", color: "var(--status-critical)" }}>{criticalCount}</h3>
          </div>
        </div>
      </div>

      {/* Filtering and search bar */}
      <div className="card" style={{ display: "flex", flexWrap: "wrap", gap: "1rem", padding: "1rem", alignItems: "center" }}>
        <div style={{ position: "relative", flex: "1 1 250px" }}>
          <Search size={16} color="var(--text-muted)" style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
          <input 
            type="text" 
            placeholder="Search assets by name..." 
            className="search-input"
            style={{ paddingLeft: "2.25rem", width: "100%" }}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Filter size={14} color="var(--text-muted)" />
            <select className="search-input" style={{ padding: "0.4rem 2rem 0.4rem 0.75rem", fontSize: "0.85rem" }} value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All Categories</option>
              <option value="TRANSFORMER">Transformers</option>
              <option value="TRAFFIC_ZONE">Traffic Zones</option>
              <option value="WATER_PIPELINE">Water Pipelines</option>
              <option value="PUBLIC_SYSTEM">Public Systems</option>
            </select>
          </div>

          <select className="search-input" style={{ padding: "0.4rem 2rem 0.4rem 0.75rem", fontSize: "0.85rem" }} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="NOMINAL">Nominal</option>
            <option value="WARNING">Warning</option>
            <option value="CRITICAL">Critical</option>
            <option value="MAINTENANCE">Maintenance</option>
            <option value="DECOMMISSIONED">Decommissioned</option>
          </select>

          <input 
            type="text" 
            placeholder="Filter by region..." 
            className="search-input"
            style={{ padding: "0.4rem 0.75rem", fontSize: "0.85rem", width: "150px" }}
            value={filterRegion}
            onChange={(e) => setFilterRegion(e.target.value)}
          />
        </div>
      </div>

      {successMsg && (
        <div style={{ background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", color: "var(--status-nominal)", padding: "0.75rem", borderRadius: "6px", fontSize: "0.85rem" }}>
          {successMsg}
        </div>
      )}

      {/* Assets Grid List */}
      {loading ? (
        <div className="card" style={{ display: "flex", justifyContent: "center", padding: "4rem" }}>
          <Activity size={32} className="spin" color="var(--accent-cyan)" />
        </div>
      ) : assets.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "4rem", color: "var(--text-muted)" }}>
          <Database size={48} style={{ opacity: 0.25, marginBottom: "1rem" }} />
          <h3>No Assets Found</h3>
          <p style={{ fontSize: "0.85rem" }}>Try adjusting your search criteria or register a new asset node.</p>
        </div>
      ) : (
        <div className="dashboard-grid">
          {assets.map(asset => {
            const typeInfo = getTypeDetails(asset.asset_type);
            return (
              <div key={asset.id} className="card col-4" style={{ display: "flex", flexDirection: "column", gap: "1rem", position: "relative", overflow: "hidden", transition: "transform 0.2s, box-shadow 0.2s" }} onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 30px rgba(6, 182, 212, 0.05)"; }} onMouseLeave={(e) => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}>
                {/* Visual Category Stripe Accent */}
                <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "3px", background: typeInfo.color }} />
                
                {/* Card Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", paddingLeft: "0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <div style={{ color: typeInfo.color }}>
                      {typeInfo.icon}
                    </div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
                      {typeInfo.label}
                    </span>
                  </div>
                  <span className={`badge ${getStatusBadgeClass(asset.status)}`}>
                    {asset.status}
                  </span>
                </div>

                {/* Asset Title */}
                <div style={{ paddingLeft: "0.5rem" }}>
                  <h4 style={{ fontSize: "1.1rem", fontWeight: 700, margin: 0 }}>{asset.name}</h4>
                  <span style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>{asset.id}</span>
                </div>

                {/* Region tag */}
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", fontSize: "0.85rem", color: "var(--text-secondary)", paddingLeft: "0.5rem" }}>
                  <MapPin size={14} color="var(--text-muted)" />
                  <span>{asset.region}</span>
                </div>

                {/* Installation and maintenance dates */}
                <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", borderTop: "1px solid var(--border-card)", paddingTop: "0.75rem", fontSize: "0.8rem", color: "var(--text-muted)", paddingLeft: "0.5rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <Calendar size={12} />
                    <span>Installed: {new Date(asset.installation_date).toLocaleDateString()}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <Wrench size={12} />
                    <span>Maintained: {new Date(asset.last_maintenance).toLocaleDateString()}</span>
                  </div>
                </div>

                {/* Dynamic Metadata Properties list */}
                {asset.dynamic_metadata && Object.keys(asset.dynamic_metadata).length > 0 && (
                  <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-card)", borderRadius: "6px", padding: "0.5rem 0.75rem", fontSize: "0.75rem", display: "flex", flexDirection: "column", gap: "0.3rem", paddingLeft: "0.75rem" }}>
                    <span style={{ fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", fontSize: "0.65rem", letterSpacing: "0.05em" }}>Operational Telemetry Metadata</span>
                    {Object.entries(asset.dynamic_metadata).map(([k, v]) => (
                      <div key={k} style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>{k}</span>
                        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                          {typeof v === "object" ? JSON.stringify(v) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action Buttons */}
                {canWrite && (
                  <div style={{ marginTop: "auto", display: "flex", gap: "0.5rem", borderTop: "1px solid var(--border-card)", paddingTop: "0.75rem", paddingLeft: "0.5rem" }}>
                    <button 
                      onClick={() => handleOpenEdit(asset)} 
                      className="btn btn-secondary" 
                      style={{ flex: 1, padding: "0.35rem", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.25rem", fontSize: "0.8rem" }}
                    >
                      <Edit3 size={12} />
                      Edit Schema
                    </button>
                    {canDelete && (
                      <button 
                        onClick={() => handleDelete(asset.id, asset.name)} 
                        className="btn btn-secondary" 
                        style={{ padding: "0.35rem 0.6rem", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--status-critical)", border: "1px solid rgba(239, 68, 68, 0.2)" }}
                        title="Decommission Asset"
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* CREATE / EDIT MODAL DRAWER */}
      {(isCreateOpen || editingAsset) && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(2, 6, 23, 0.7)", backdropFilter: "blur(6px)", zIndex: 1000, display: "flex", justifyContent: "center", alignItems: "center", padding: "1.5rem" }}>
          <div className="card" style={{ width: "100%", maxWidth: "600px", background: "rgba(9, 13, 24, 0.95)", border: "1px solid var(--border-card)", borderRadius: "12px", boxShadow: "0 20px 50px rgba(0,0,0,0.5)", overflow: "hidden", display: "flex", flexDirection: "column", maxHeight: "90vh" }}>
            
            {/* Modal Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-card)", padding: "1.25rem 1.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Database size={20} color="var(--accent-cyan)" />
                <h3 style={{ margin: 0 }}>
                  {isCreateOpen ? "Register Infrastructure Node" : "Edit Asset Schema"}
                </h3>
              </div>
              <button 
                onClick={() => { setIsCreateOpen(false); setEditingAsset(null); }}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={isCreateOpen ? handleCreateSubmit : handleEditSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem", padding: "1.5rem", overflowY: "auto", flex: 1 }}>
              
              {errorMsg && (
                <div style={{ background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.2)", color: "var(--status-critical)", padding: "0.75rem", borderRadius: "6px", fontSize: "0.85rem" }}>
                  {errorMsg}
                </div>
              )}

              {/* Asset Name */}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Asset Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Substation Transformer T-02"
                  className="search-input"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  required
                />
              </div>

              {/* Type and Status Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                  <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Category Type</label>
                  <select 
                    className="search-input"
                    value={formType}
                    onChange={(e) => setFormType(e.target.value as any)}
                  >
                    <option value="TRANSFORMER">Transformer</option>
                    <option value="TRAFFIC_ZONE">Traffic Zone</option>
                    <option value="WATER_PIPELINE">Water Pipeline</option>
                    <option value="PUBLIC_SYSTEM">Public System</option>
                  </select>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                  <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Status</label>
                  <select 
                    className="search-input"
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value as any)}
                  >
                    <option value="NOMINAL">Nominal</option>
                    <option value="WARNING">Warning</option>
                    <option value="CRITICAL">Critical</option>
                    <option value="MAINTENANCE">Maintenance</option>
                    <option value="DECOMMISSIONED">Decommissioned</option>
                  </select>
                </div>
              </div>

              {/* Region */}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Geographic Region Tag</label>
                <input 
                  type="text"
                  placeholder="e.g. North Sector, Downtown Grid"
                  className="search-input"
                  value={formRegion}
                  onChange={(e) => setFormRegion(e.target.value)}
                  required
                />
              </div>

              {/* Dynamic Metadata Editor */}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", borderTop: "1px solid var(--border-card)", paddingTop: "1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>Dynamic Schema Metadata</label>
                  <button 
                    type="button" 
                    onClick={addMetadataRow} 
                    className="btn btn-secondary" 
                    style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem", display: "flex", alignItems: "center", gap: "0.25rem" }}
                  >
                    <Plus size={12} />
                    Add Row
                  </button>
                </div>
                
                <p style={{ color: "var(--text-muted)", fontSize: "0.75rem", margin: 0 }}>
                  Enter key-value pairs (e.g. capacity_kva: 2500, flow_rate_lps: 480). Non-empty keys serialize to JSON.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.25rem" }}>
                  {formMetadata.map((row, idx) => (
                    <div key={idx} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                      <input 
                        type="text" 
                        placeholder="Key (e.g. capacity)" 
                        className="search-input" 
                        style={{ flex: 1, fontSize: "0.8rem", padding: "0.35rem 0.5rem" }}
                        value={row.key}
                        onChange={(e) => handleMetadataChange(idx, "key", e.target.value)}
                      />
                      <input 
                        type="text" 
                        placeholder="Value (e.g. 2500)" 
                        className="search-input" 
                        style={{ flex: 1, fontSize: "0.8rem", padding: "0.35rem 0.5rem" }}
                        value={row.value}
                        onChange={(e) => handleMetadataChange(idx, "value", e.target.value)}
                      />
                      <button 
                        type="button" 
                        onClick={() => removeMetadataRow(idx)}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "var(--status-critical)", padding: "0.25rem" }}
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Modal Footer Actions */}
              <div style={{ borderTop: "1px solid var(--border-card)", paddingTop: "1.25rem", marginTop: "1rem", display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
                <button 
                  type="button" 
                  onClick={() => { setIsCreateOpen(false); setEditingAsset(null); }} 
                  className="btn btn-secondary"
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}
                  disabled={submitting}
                >
                  {submitting ? <Activity size={14} className="spin" /> : <Save size={14} />}
                  {isCreateOpen ? "Register Asset" : "Save Changes"}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default AssetManager;
