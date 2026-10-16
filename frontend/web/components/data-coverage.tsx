"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";

type Coverage = {
  state: string; start: string; end: string; reasons: string[];
  price_coverage: { expected_sessions: number | null; available_valid_sessions: number; missing_sessions: string[]; quarantined_rows: number; not_yet_published: string[]; stale: boolean; last_verified_market_session: string | null; daily_status: { date: string; classification: string }[] };
  OHLC_coverage: { open_available: number; available: number; missing_fields: Record<string, number>; execution_fallback: string };
  volume_coverage: { available: number };
  corporate_action_coverage: { status: string; review_id: string | null; by_type: Record<string, string>; events: { id: string; date: string; type: string; cash_amount: string | null; ratio: string | null; currency: string | null; raw_ingestion_id: string }[] };
  FX_coverage: { base: string; quote: string; missing_sessions: number; checked_sessions: number; max_carry_days: number };
  fundamental_coverage: { metrics: string[]; missing_metrics: string[]; periods: string[]; restated_facts: number; rejected_facts: number; latest_filing_id: string | null };
  historical_membership_coverage: { status: string; survivorship_risk: string };
  verified_availability: { strict_price_sessions: number; dataset_ready: boolean };
  readiness: Record<string, string>; last_successful_update: string | null;
};

export function DataCoverage({ instrumentId }: { instrumentId: string }) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const query = useQuery({ queryKey: ["instrument-coverage", instrumentId, start, end],
    queryFn: () => api<Coverage>(`/data-operations/coverage/${instrumentId}?${params}`) });
  const data = query.data;
  return <section className="space-y-4 rounded-xl border border-zinc-800 p-5">
    <h2 className="text-xl font-semibold">Historische Datenabdeckung</h2>
    <div className="flex flex-wrap gap-4"><label>Ab <input aria-label="Abdeckung ab" className="block rounded bg-zinc-900 p-2" type="date" value={start} onChange={e => setStart(e.target.value)} /></label><label>Bis <input aria-label="Abdeckung bis" className="block rounded bg-zinc-900 p-2" type="date" value={end} onChange={e => setEnd(e.target.value)} /></label></div>
    {query.isPending && <p>Prüfe Kalender und Evidenz…</p>}
    {query.isError && <p role="alert">{query.error.message}</p>}
    {data && <><p className="font-semibold text-amber-300">{data.state} · {data.start} – {data.end}</p>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div><dt>Kurse / erwartete Sitzungen</dt><dd>{data.price_coverage.available_valid_sessions} / {data.price_coverage.expected_sessions ?? "Kalender unbekannt"}</dd></div>
        <div><dt>Open-Preise / beobachtete Kurse</dt><dd>{data.OHLC_coverage.open_available} / {data.OHLC_coverage.available} · fehlend: NO_FILL</dd></div>
        <div><dt>Volumen vorhanden</dt><dd>{data.volume_coverage.available}</dd></div>
        <div><dt>Corporate Actions</dt><dd>{data.corporate_action_coverage.status} · Prüfbeleg: {data.corporate_action_coverage.review_id ?? "Keiner"}</dd></div>
        <div><dt>FX {data.FX_coverage.base}/{data.FX_coverage.quote}</dt><dd>{data.FX_coverage.missing_sessions} fehlende von {data.FX_coverage.checked_sessions} Sitzungen · maximal {data.FX_coverage.max_carry_days} Carry-Tage</dd></div>
        <div><dt>Historische Universe-Zugehörigkeit</dt><dd>{data.historical_membership_coverage.status}</dd></div>
        <div><dt>Letzte geprüfte Sitzung</dt><dd>{data.price_coverage.last_verified_market_session ?? "Keine"} · {data.price_coverage.stale ? "ALT" : "Aktualität nur im gewählten Intervall"}</dd></div>
        <div><dt>Letzte lokale Beobachtung</dt><dd>{data.last_successful_update ?? "Keine"}</dd></div>
      </dl>
      <p>Quarantäne: {data.price_coverage.quarantined_rows}. Noch nicht publizierte Sitzungen: {data.price_coverage.not_yet_published.length}.</p>
      <p>Fehlende Sitzungen: {data.price_coverage.missing_sessions.join(", ") || "Keine ermittelt"}</p>
      <details><summary>Sitzungen und Lückengründe</summary><ul className="max-h-64 overflow-auto text-sm">{data.price_coverage.daily_status.map(row => <li key={row.date}>{row.date} · {row.classification}</li>)}</ul></details>
      <p>Action-Abdeckung nach Typ: {Object.entries(data.corporate_action_coverage.by_type).map(([type, status]) => `${type}: ${status}`).join(" · ")}</p>
      <p>Fehlende Pflichtkennzahlen: {data.fundamental_coverage.missing_metrics.join(", ") || "Keine"}. Perioden: {data.fundamental_coverage.periods.join(", ") || "Keine"}.</p>
      <p>Restatements: {data.fundamental_coverage.restated_facts} · abgelehnte Fakten: {data.fundamental_coverage.rejected_facts} · Filing: {data.fundamental_coverage.latest_filing_id ?? "Keines"}</p>
      <p>Historisch belegte Kurssitzungen: {data.verified_availability.strict_price_sessions}. Ein heutiger Backfill beweist keine damalige lokale Archivierung.</p>
      <ul className="text-sm text-amber-300">{data.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>
      <details><summary>Belegte Corporate Actions</summary>{data.corporate_action_coverage.events.map(event => <p key={event.id}>{event.date} · {event.type} · {event.cash_amount ?? event.ratio ?? "Kein Zahlenwert"} {event.currency} · Original {event.raw_ingestion_id}</p>)}</details>
      <dl className="grid grid-cols-2 gap-2 text-sm">{Object.entries(data.readiness).map(([name, status]) => <div key={name}><dt>{name}</dt><dd>{status}</dd></div>)}</dl>
    </>}
    <Link href="/data-operations" className="text-emerald-400 underline">Datenversorgung und Backfills</Link>
  </section>;
}
