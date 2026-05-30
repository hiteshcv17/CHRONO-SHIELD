import apiClient, { getWithRetry } from "./client";
import { Asset, AssetCreateInput, AssetUpdateInput } from "../types/domain";

export async function getAssets(params?: {
  asset_type?: string;
  status?: string;
  region?: string;
  name?: string;
  limit?: number;
}): Promise<Asset[]> {
  const query = new URLSearchParams();
  if (params?.asset_type) query.append("asset_type", params.asset_type);
  if (params?.status) query.append("status", params.status);
  if (params?.region) query.append("region", params.region);
  if (params?.name) query.append("name", params.name);
  if (params?.limit) query.append("limit", params.limit.toString());

  const queryString = query.toString();
  return getWithRetry<Asset[]>(`/api/v1/assets${queryString ? `?${queryString}` : ""}`);
}

export async function getAssetById(assetId: string): Promise<Asset> {
  return getWithRetry<Asset>(`/api/v1/assets/${assetId}`);
}

export async function registerAsset(payload: AssetCreateInput): Promise<Asset> {
  const res = await apiClient.post<Asset>("/api/v1/assets", payload);
  return res.data;
}

export async function updateAsset(assetId: string, payload: AssetUpdateInput): Promise<Asset> {
  const res = await apiClient.put<Asset>(`/api/v1/assets/${assetId}`, payload);
  return res.data;
}

export async function decommissionAsset(assetId: string): Promise<void> {
  await apiClient.delete(`/api/v1/assets/${assetId}`);
}

