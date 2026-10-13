import { api } from "@/lib/api";
import type { Instrument, DataSource } from "./market-foundation";

export type Metric = { value: string | null; status: string; reason?: string; inputs: string[]; rule_version: string; unit?: string; period_end?: string; known_at?: string; retrieved_at?: string; price_date?: string; price_version?: string };
export type Fact = { id: string; metric: string; value: string; unit: string; currency: string | null; period_start: string | null; period_end: string; period_type: string; known_at: string; observed_at: string; retrieved_at: string; source_id: string; raw_ingestion_id: string; validation_status: string; replaces_version_id: string | null; evidence: { filing_reference: string; release: string | null } };
export type Score = { score: string | null; status: string; coverage: string; missing_inputs: string[]; rule_version: string; method: string; drivers: { metric: string; input: string; weight: string; contribution: string; provenance: Metric }[] };
export type Research = { instrument_id: string; as_of: string; status: string; facts: Fact[]; metrics: Record<string, Metric>; valuation: Record<string, Metric>; scores: Record<string, Score>; ttm: Record<string, Metric>; momentum: Metric; price: { close: string; date: string; currency: string; quality_label: string; source_id: string } | null; history_contract: string };
export type Screen = { items: { instrument: Instrument; research: Research | null; as_of: string | null; status: string }[]; available_filters: string[]; offset: number; limit: number };
export type Watchlist = { id: string; name: string; description: string | null; archived: boolean };
export type WatchItem = { id: string; instrument_id: string; notes: string | null; tags: string[]; instrument: Instrument; research: Research | null; price: (NonNullable<Research["price"]> & { age_days: number; freshness: string }) | null };
export type News = { id: string; title: string; source_id: string; source_url: string; summary: string | null; published_at: string | null; discovered_at: string; retrieved_at: string; sentiment: Record<string, unknown> | null; duplicate_of_id: string | null; associations: { instrument_id: string; mapping_status: string }[] };
export type Preview = { raw_ingestion_id: string; columns: string[]; rows: Record<string, unknown>[]; errors: { line: number; reason: string }[]; valid_rows: number; can_commit: boolean };
export const getResearch = (id: string, asOf = "") => api<Research>(`/research/instruments/${id}${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`);
export const getWatchlists = () => api<Watchlist[]>("/watchlists");
export const getWatchItems = (id: string) => api<WatchItem[]>(`/watchlists/${id}/items`);
export const getNews = (query = "") => api<News[]>(`/news${query ? `?${query}` : ""}`);
export type ResearchQuality = { last_filing_ingestion: string | null; failed_ingestions: number; quarantined_facts: number; restatements: number; missing_fundamentals: number; last_fact_period: string | null; news_articles: number; news_duplicates: number; estimate_count: number; sources: DataSource[] };
