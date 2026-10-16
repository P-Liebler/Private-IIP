import { api } from "@/lib/api";

export type Instrument = {
  id: string; name: string; asset_type: string; currency: string;
  ticker: string | null; isin: string | null; figi: string | null;
  exchange: string | null; mic: string | null; country: string | null;
  sector: string | null; industry: string | null;
  listed_at: string | null; delisted_at: string | null; active: boolean;
};
export type Identifier = {
  id: string; type: string; value: string; market_key: string;
  valid_from: string; valid_to: string | null;
  source_id: string | null; raw_ingestion_id: string | null; observed_at: string;
};
export type InstrumentDetail = Instrument & { identifiers: Identifier[] };
export type SearchResult = {
  instrument: Instrument; match_type: string; resolution_status: string;
  matched_value: string; current: boolean;
};
export type DataSource = {
  id: string; name: string; slug: string; type: string; trust_level: string;
  priority: number; enabled: boolean; gate_status: string; terms_url: string | null;
  checked_at: string | null; scope: string | null; allowed_uses: string[];
  next_review_at: string | null; rate_limit_per_minute: number | null;
  last_success: string | null; last_failure: string | null;
  gate_reason: string | null;
};
export type CsvPreview = {
  raw_ingestion_id: string; detected_columns: string[];
  possible_mapping: Record<string, string>; row_count: number;
  validation_errors: string[];
  sample_rows: {
    line: number; values: Record<string, string | null>;
    resolution_status: string; instrument_id: string | null; errors: string[];
  }[];
};

export const searchInstruments = (query: string) =>
  api<SearchResult[]>(`/instruments/search?q=${encodeURIComponent(query)}`);
export const getInstrument = (id: string) => api<InstrumentDetail>(`/instruments/${id}`);
export const getSources = () => api<DataSource[]>("/data-sources");
export async function previewCsv(file: File): Promise<CsvPreview> {
  return api<CsvPreview>("/imports/csv/preview", {
    method: "POST", body: file,
    headers: { "Content-Type": "text/csv", "X-Filename": file.name },
  });
}
