import { api } from "@/lib/api";

export type ImportKind = "prices" | "actions" | "fx";
export type MarketPreview = {
  raw_ingestion_id: string;
  mapping: Record<string, string>;
  row_count: number;
  invalid_count: number;
  warnings_count: number;
  validation_errors: string[];
  sample_rows: {
    line: number;
    values: Record<string, string | null>;
    normalized: Record<string, string | null>;
    instrument_id: string | null;
    errors: string[];
    warnings: string[];
  }[];
};
export type ImportResult = {
  raw_ingestion_id: string;
  inserted: number;
  corrected: number;
  observed_only: number;
  unchanged: number;
  quarantined: number;
  accepted_rows: number;
  warning_rows: number;
  rejected_rows: number;
  new_versions: number;
};
export type PriceRecord = {
  id: string; date: string; open: string | null; high: string | null;
  low: string | null; close: string; adjusted_close: string | null;
  volume: string | null; currency: string; source_id: string;
  source_count: number; raw_ingestion_id: string; known_at: string;
  validation_status: string; quality_score: number; quality_label: string;
  warnings: string[];
};
export type PriceHistory = {
  status: string; reason: string | null; as_of: string; prices: PriceRecord[];
  chart_series?: { date: string; value: string | null }[]; calendar_status?: string; calendar_version?: string | null;
};
export type QualitySummary = {
  status: string; price_quality: Record<string, number>;
  quarantined_rows: number; failed_raw_ingestions: number;
  source_failures: { slug: string; last_failure: string; failure_count: number }[];
  source_disagreements: number; instruments_with_missing_prices: number;
  stale_prices: number; last_successful_price_import: string | null;
  last_successful_fx_import: string | null;
  price_freshness: string; fx_freshness: string;
};

export const getPrices = (id: string) => api<PriceHistory>(`/instruments/${id}/prices`);
export const getQualitySummary = () => api<QualitySummary>("/data-quality/summary");

export function previewMarketCsv(kind: ImportKind, file: File) {
  return api<MarketPreview>(`/market-data/imports/${kind}/preview`, {
    method: "POST", body: file,
    headers: { "Content-Type": "text/csv", "X-Filename": file.name },
  });
}

export function commitMarketCsv(
  kind: ImportKind, preview: MarketPreview, options: {
    accept_partial: boolean;
    conflict_policy: "REJECT" | "ACCEPT_NEW" | "KEEP_EXISTING";
    decision_note: string;
  },
) {
  return api<ImportResult>(`/market-data/imports/${kind}/commit`, {
    method: "POST",
    body: JSON.stringify({
      raw_ingestion_id: preview.raw_ingestion_id,
      mapping: preview.mapping,
      ...options,
      decision_note: options.decision_note || null,
    }),
  });
}
