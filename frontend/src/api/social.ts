import apiClient, { getWithRetry } from "./client";

export interface SocialComplaint {
  id: string;
  timestamp: string;
  platform: string;
  text: string;
  author: string;
  matched_keyword: string;
  category: string;
  severity: string;
  sentiment_score: number;
  urgency_score: number;
  explanation?: string;
  keywords?: string;
  cluster_tag?: string;
}

export interface CategoryDistribution {
  category: string;
  count: number;
}

export interface SeverityDistribution {
  severity: string;
  count: number;
}

export interface ClusterGroup {
  id: number;
  name: string;
  keywords: string[];
  count: number;
}

export interface SocialAnalyticsResponse {
  total_complaints: number;
  average_sentiment: number;
  category_breakdown: CategoryDistribution[];
  severity_breakdown: SeverityDistribution[];
  clusters: ClusterGroup[];
}

export async function getSocialComplaints(category?: string, severity?: string): Promise<SocialComplaint[]> {
  let query = "";
  if (category || severity) {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (severity) params.append("severity", severity);
    query = `?${params.toString()}`;
  }
  return getWithRetry<SocialComplaint[]>(`/api/v1/social/complaints${query}`);
}

export async function getSocialAnalytics(): Promise<SocialAnalyticsResponse> {
  return getWithRetry<SocialAnalyticsResponse>("/api/v1/social/analytics");
}

export async function triggerSocialIngest(): Promise<any> {
  const res = await apiClient.post("/api/v1/social/ingest");
  return res.data;
}
