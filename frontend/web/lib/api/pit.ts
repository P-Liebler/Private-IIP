import { api } from "@/lib/api";

export type Universe = { id: string; name: string };
export type Quality = { total_observations: number; valid_observations: number; excluded_observations: number; missing_features: number; unavailable_targets: number; survivorship_risk: boolean; exclusion_reasons: Record<string, number> };
export type Dataset = { id: string; content_hash: string; configuration: { universe_id: string; availability_mode: string }; quality: Quality };
export type Fill = { instrument_id: string; side: string; quantity: string; execution_price: string; execution_price_timestamp: string; signal_generated_at: string; price_version_id: string; raw_ingestion_id: string; commission: string; spread_slippage_cost: string };
export type Run = { id: string; content_hash: string; result: { status: string; data_context: string; warnings: string[]; metrics: Record<string, string | number | null>; equity: { date: string; value: string | null; cash: string }[]; fills: Fill[]; orders: { instrument_id: string; status: string }[]; benchmark_equity: string[] | null } };
export const listUniverses = () => api<Universe[]>("/universes");
export const listDatasets = () => api<Dataset[]>("/datasets");
