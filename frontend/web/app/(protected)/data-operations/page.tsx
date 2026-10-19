"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ValidationLinks } from "@/components/validation-workbench";
import { getSources, searchInstruments } from "@/lib/api/market-foundation";
import { DataCoverage } from "@/components/data-coverage";

type Job = { id: string; status: string; progress: number; configuration: { kind: string; source_slug: string; start: string; end: string }; last_error_code: string | null; results: Record<string, unknown>[] };
type Operations = { is_operator: boolean; scheduling_enabled: boolean; daily_request_limit: number; jobs: Job[] };
type Preview = { status: string; chunks: number; maximum_requests: number; instruments: number; limitations: string[] };
const contracts = { ECB_FX: "ECB", SNB_MACRO: "SNB", SEC: "SEC_EDGAR", OPENFIGI: "OPENFIGI", MANUAL_PRICES: "MANUAL_CSV", COVERAGE: "MANUAL_CSV", ALPHA_PRICES: "ALPHAVANTAGE" };
type Kind = keyof typeof contracts;
const box = "rounded border border-zinc-700 bg-zinc-900 p-2";

export default function DataOperationsPage() {
  const operations = useQuery({ queryKey: ["data-operations"], queryFn: () => api<Operations>("/data-operations"), refetchInterval: 10000 });
  const sources = useQuery({ queryKey: ["data-sources"], queryFn: getSources });
  const [kind, setKind] = useState<Kind>("ECB_FX");
  const [start, setStart] = useState(""); const [end, setEnd] = useState("");
  const [search, setSearch] = useState(""); const [instrumentId, setInstrumentId] = useState("");
  const [cik, setCik] = useState(""); const [series, setSeries] = useState("SNB_rate");
  const [rawId, setRawId] = useState(""); const [mapping, setMapping] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<Preview | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const instruments = useQuery({ queryKey: ["operation-instruments", search], queryFn: () => searchInstruments(search), enabled: search.length > 1 });
  const source = sources.data?.find(row => row.slug === contracts[kind]);
  const isOperator = operations.data?.is_operator === true;
  const gate = kind === "COVERAGE" || (source?.enabled && source.gate_status === "APPROVED" && !source.gate_reason);
  const body = () => ({ source_slug: contracts[kind], kind, start, end, instrument_ids: instrumentId ? [instrumentId] : [], series,
    ...(kind === "SEC" ? { cik } : {}), ...(kind === "MANUAL_PRICES" ? { raw_ingestion_id: rawId, mapping } : {}) });
  async function run(action: "preview" | "jobs") {
    setBusy(true); setError("");
    try {
      const result = await api<Preview>(`/data-operations/${action}`, { method: "POST", body: JSON.stringify(body()) });
      setPreview(action === "preview" ? result : null); await operations.refetch();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Anfrage fehlgeschlagen"); }
    finally { setBusy(false); }
  }
  async function upload(file?: File) {
    if (!file) return;
    setBusy(true); setError("");
    try {
      const result = await api<{ raw_ingestion_id: string; mapping: Record<string, string> }>("/market-data/imports/prices/preview", { method: "POST", body: file, headers: { "Content-Type": "text/csv", "X-Filename": file.name } });
      setRawId(result.raw_ingestion_id); setMapping(result.mapping); setPreview(null);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Datei nicht lesbar"); }
    finally { setBusy(false); }
  }
  async function control(id: string, action: string) {
    setError("");
    try { await api(`/data-operations/jobs/${id}/${action}`, { method: "POST" }); await operations.refetch(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Aktion fehlgeschlagen"); }
  }
  return <main className="space-y-6 py-10"><ValidationLinks />
    <header><h1 className="text-3xl font-semibold">Datenversorgung</h1><p className="mt-2 text-zinc-400">Begrenzte historische Importe, dauerhafte Aufträge und belegte Datenqualität.</p></header>
    <p>Automatischer Zeitplan: {operations.data?.scheduling_enabled ? "Aktiv, nur freigegebene Verträge" : "Deaktiviert"}. Globales Tagesbudget: {operations.data?.daily_request_limit ?? "Unbekannt"} Provider-Anfragen.</p>
    <p className="text-amber-300">Forecasts NOT_VALIDATED · Recommendations GATED · Production NOT_RELEASED</p>
    {operations.isError && <p role="alert">{operations.error.message}</p>}
    <Link className="text-emerald-400 underline" href="/settings/data-sources">Quellenrechte und Aktivierung prüfen</Link>
    {!isOperator && <p>Aufträge und Rechteänderungen erfordern eine konfigurierte Daten-Operator-Berechtigung. Die Abdeckungsprüfung bleibt verfügbar.</p>}
    <section className="space-y-4 rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Backfill-Vorschau</h2>
      <form className="grid gap-4 sm:grid-cols-2" onChange={() => setPreview(null)} onSubmit={e => { e.preventDefault(); void run("preview"); }}>
        <label>Datentyp<select className={`${box} block w-full`} value={kind} onChange={e => { setKind(e.target.value as Kind); setRawId(""); }}>
          <option value="ECB_FX">ECB · tägliche EUR/CHF und EUR/USD</option><option value="SNB_MACRO">SNB · monatliche Referenzreihe</option><option value="SEC">SEC · geprüfte US-Fundamentals</option><option value="OPENFIGI">OpenFIGI · Mapping-Kandidaten</option><option value="MANUAL_PRICES">Manueller CSV-Kursimport</option><option value="COVERAGE">Historische Abdeckung prüfen</option><option value="ALPHA_PRICES">Alpha Vantage · optional, höchstens 100 Tageskurse</option>
        </select></label>
        <p className="self-center">Quelle {contracts[kind]} · {source?.gate_status ?? "UNKNOWN"} · {source?.enabled ? "Aktiv" : "Deaktiviert"}</p>
        <label>Von<input required className={`${box} block w-full`} type="date" value={start} onChange={e => setStart(e.target.value)} /></label><label>Bis<input required className={`${box} block w-full`} type="date" value={end} onChange={e => setEnd(e.target.value)} /></label>
        <label>Instrument suchen<input className={`${box} block w-full`} value={search} onChange={e => setSearch(e.target.value)} placeholder="Name, Ticker oder ISIN" /></label>
        <label>Geprüftes Instrument<select className={`${box} block w-full`} value={instrumentId} onChange={e => setInstrumentId(e.target.value)}><option value="">Keines ausgewählt</option>{instruments.data?.map(row => <option key={row.instrument.id} value={row.instrument.id}>{row.instrument.name} · {row.instrument.currency}</option>)}</select></label>
        {kind === "SEC" && <label>Bestätigter CIK<input required className={`${box} block w-full`} value={cik} onChange={e => setCik(e.target.value)} /></label>}
        {kind === "SNB_MACRO" && <label>Monatliche Reihe<select className={`${box} block w-full`} value={series} onChange={e => setSeries(e.target.value)}><option value="SNB_rate">SNB-Leitzins · Prozent</option><option value="EUR_CHF">EUR/CHF · Monatsende</option><option value="USD_CHF">USD/CHF · Monatsende</option></select><p className="text-sm text-amber-300">Monatliche FX-Werte werden nicht für tägliche Bewertungen verwendet.</p></label>}
        {kind === "MANUAL_PRICES" && <label>Kursdatei (CSV, eigene Nutzungsrechte)<input disabled={!isOperator || busy} className="block" type="file" accept=".csv,text/csv" onChange={e => void upload(e.target.files?.[0])} />{rawId && <span className="text-sm">Original archiviert. Spaltenmapping wird in der Vorschau geprüft.</span>}</label>}
        <button className={box} disabled={!isOperator || !gate || busy} type="submit">Umfang prüfen</button>
      </form>
      {!gate && <p className="text-amber-300">SOURCE_NOT_APPROVED · Die Quelle kann nicht gestartet werden. <Link href="/imports" className="underline">Manueller Import</Link></p>}
      {preview && <div className="space-y-2"><p>{preview.status} · {preview.chunks} Abschnitte · höchstens {preview.maximum_requests} Anfragen einschließlich begrenzter Wiederholungen</p><ul>{preview.limitations.map(text => <li key={text}>{text}</li>)}</ul><button disabled={busy || !gate} className={box} onClick={() => void run("jobs")}>Geprüften Auftrag starten</button></div>}
      {error && <p role="alert" className="text-rose-300">{error}</p>}
    </section>
    <section className="space-y-3"><h2 className="text-xl font-semibold">Meine Collector-Aufträge</h2>{operations.data?.jobs.length === 0 && <p>Keine Aufträge.</p>}{operations.data?.jobs.map(job => <article key={job.id} className="space-y-2 rounded border border-zinc-800 p-4"><h3>{job.configuration.source_slug} · {job.configuration.kind} · {job.status}</h3><p>{job.configuration.start} – {job.configuration.end} · {job.progress} Abschnitte abgeschlossen</p>{job.last_error_code && <p className="text-amber-300">{job.last_error_code}</p>}<div className="flex gap-3">{["QUEUED", "RUNNING"].includes(job.status) && <button className={box} onClick={() => void control(job.id, "cancel")}>Abbrechen</button>}{["PARTIAL", "FAILED", "SKIPPED", "CANCELLED"].includes(job.status) && <button className={box} onClick={() => void control(job.id, "resume")}>Nach Prüfung fortsetzen</button>}</div><details><summary>Ergebnisse und Provenienz</summary><pre className="overflow-auto text-xs">{JSON.stringify(job.results, null, 2)}</pre></details></article>)}</section>
    {instrumentId && <DataCoverage instrumentId={instrumentId} />}
  </main>;
}
