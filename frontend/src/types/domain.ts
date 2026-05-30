export interface Anomaly {
  id: string;
  timestamp: string;
  metric_name: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  score: number;
  description: string;
  acknowledged: boolean;
}

export interface AnomalyCreatePayload {
  id: string;
  timestamp: string;
  metric_name: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  score: number;
  description: string;
}

export interface AnomalyUpdatePayload {
  acknowledged: boolean;
}

export interface PrioritizedAlert {
  id: string;
  anomaly_id: string;
  metric_name: string;
  original_severity: string;
  current_severity: string;
  priority_score: number;
  status: "ACTIVE" | "ACKNOWLEDGED" | "SUPPRESSED" | "ESCALATED" | "RESOLVED";
  occurrence_count: number;
  timestamp: string;
  last_occurrence: string;
  cooldown_until: string | null;
  escalation_level: number;
  description: string;
}

export interface Asset {
  id: string;
  name: string;
  asset_type: "TRANSFORMER" | "TRAFFIC_ZONE" | "WATER_PIPELINE" | "PUBLIC_SYSTEM";
  status: "NOMINAL" | "WARNING" | "CRITICAL" | "MAINTENANCE" | "DECOMMISSIONED";
  region: string;
  dynamic_metadata: Record<string, any> | null;
  installation_date: string;
  last_maintenance: string;
  created_at: string;
  updated_at: string;
}

export interface AssetCreateInput {
  name: string;
  asset_type: "TRANSFORMER" | "TRAFFIC_ZONE" | "WATER_PIPELINE" | "PUBLIC_SYSTEM";
  status?: "NOMINAL" | "WARNING" | "CRITICAL" | "MAINTENANCE" | "DECOMMISSIONED";
  region: string;
  dynamic_metadata?: Record<string, any> | null;
  installation_date?: string;
  last_maintenance?: string;
}

export interface AssetUpdateInput {
  name?: string;
  asset_type?: "TRANSFORMER" | "TRAFFIC_ZONE" | "WATER_PIPELINE" | "PUBLIC_SYSTEM";
  status?: "NOMINAL" | "WARNING" | "CRITICAL" | "MAINTENANCE" | "DECOMMISSIONED";
  region?: string;
  dynamic_metadata?: Record<string, any> | null;
  installation_date?: string;
  last_maintenance?: string;
}
