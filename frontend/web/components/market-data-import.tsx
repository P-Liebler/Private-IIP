"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  commitMarketCsv, previewMarketCsv,
  type ImportKind, type ImportResult, type MarketPreview,
} from "@/lib/api/market-data";

const labels: Record<ImportKind, string> = {
  prices: "Tageskurse", actions: "Corporate Actions", fx: "Wechselkurse",
};
const templates: Record<ImportKind, string> = {
  prices: "date,isin,ticker,close,currency,open,high,low,volume\n",
  fx: "date,base_currency,quote_currency,rate\n",
  actions: "date,isin,ticker,action_type,value,currency,payment_date,source_reference\n",
};

export function MarketDataImport({ embedded = false }: { embedded?: boolean }) {
  const queryClient = useQueryClient();
  const selection = useRef(0);
  const requested = useSearchParams().get("kind");
  const [kind, setKind] = useState<ImportKind>(requested === "fx" || requested === "actions" ? requested : "prices");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<MarketPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [acceptPartial, setAcceptPartial] = useState(false);
  const [policy, setPolicy] = useState<"REJECT" | "ACCEPT_NEW" | "KEEP_EXISTING">("REJECT");
  const [note, setNote] = useState("");
  const [fileError, setFileError] = useState("");
  const [detection, setDetection] = useState("");
  const [reading, setReading] = useState(false);
  const upload = useMutation({
    mutationFn: () => previewMarketCsv(kind, file!),
    onSuccess: (value) => { setPreview(value); setResult(null); setConfirmed(false); },
  });
  const commit = useMutation({
    mutationFn: () => commitMarketCsv(kind, preview!, {
      accept_partial: acceptPartial, conflict_policy: policy, decision_note: note,
    }),
    onSuccess: (value) => { setResult(value); void queryClient.invalidateQueries(); },
  });
  const pending = reading || upload.isPending || commit.isPending;
  function reset() {
    selection.current += 1;
    setFile(null); setPreview(null); setResult(null); setConfirmed(false);
    setAcceptPartial(false); setPolicy("REJECT"); setNote("");
    setFileError(""); setDetection(""); setReading(false);
    upload.reset(); commit.reset();
  }
  async function chooseFile(candidate: File | null) {
    if (pending) return;
    reset();
    if (!candidate) return;
    if (!/\.csv$/i.test(candidate.name) || candidate.size === 0 || candidate.size > 5 * 1024 * 1024) {
      setFileError("Eine nicht leere CSV-Datei bis 5 MB auswählen. Das Original bleibt unverändert.");
      return;
    }
    const revision = selection.current;
    setReading(true);
    try {
      const header = (await candidate.slice(0, 8192).text()).replace(/^\uFEFF/, "").split(/\r?\n/, 1)[0];
      const columns = new Set(header.split(",").map(value => value.trim().replace(/^"|"$/g, "").toLowerCase()));
      const detected: ImportKind | null = ["base_currency", "quote_currency", "rate"].every(key => columns.has(key)) ? "fx"
        : columns.has("action_type") ? "actions" : columns.has("close") ? "prices" : null;
      if (revision !== selection.current) return;
      setFile(candidate);
      if (detected) setKind(detected);
      setDetection(detected ? `Erkannter Datentyp: ${labels[detected]}. Bitte Datentyp und anschließende Spaltenzuordnung prüfen.`
        : "Datentyp nicht eindeutig erkannt. Bitte auswählen; die Vorschau prüft die tatsächlichen Spalten und Originalbytes.");
    } catch {
      if (revision === selection.current) setFileError("Datei konnte nicht gelesen werden. Datei erneut auswählen.");
    } finally { if (revision === selection.current) setReading(false); }
  }
  function submitPreview(event: FormEvent) {
    event.preventDefault();
    if (file && !pending) { setPreview(null); setResult(null); setConfirmed(false); upload.mutate(); }
  }
  return <section className="space-y-8">
    {!embedded && <header><h1 className="text-3xl font-semibold">CSV-Import</h1><p className="mt-2 text-zinc-400">Originaldatei prüfen, Zuordnung bestätigen und erst dann in geprüfte Daten übernehmen.</p></header>}
    <section className="space-y-3 rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Marktdaten für Ihr Portfolio</h2><p>Nur rechtmäßig bereitgestellte Originale verwenden. UTF-8, Komma, ISO-Datum und Dezimalpunkt; eine passende ISIN, FIGI oder eindeutige Tickerkennung pro Kurs-/Action-Zeile. Kein Kurs wird aus einem Kaufpreis oder einem LLM ergänzt.</p><p className="text-sm text-zinc-400">Tageskurse sind Schlusskurse, keine Livepreise. FX: 1 Einheit Basiswährung = rate Einheiten Zielwährung. Tägliche Referenzen verwenden; SNB-Monatswerte ersetzen keine täglichen Fixings. Corporate Actions: SPLIT mit Verhältnis, DIVIDEND mit Bruttobetrag je Aktie; Zahlungstag und Herkunft angeben, sofern belegt. Die Übernahme allein bucht keine zusätzliche Portfoliodividende.</p><a className="inline-block text-emerald-400 underline" download={`${kind}-template.csv`} href={`data:text/csv;charset=utf-8,${encodeURIComponent(templates[kind])}`}>Leere Vorlage für {labels[kind]} herunterladen</a><div className="flex flex-wrap gap-4"><Link className="text-emerald-400 underline" href="/portfolios">Zur Portfolioeinrichtung</Link><Link className="text-emerald-400 underline" href="/settings/data-sources">Quellenfreigaben prüfen</Link><Link className="text-emerald-400 underline" href="/data-operations">Begrenzte Aktualisierung für freigegebene Quellen</Link></div><p className="text-sm text-amber-400">Ohne Freigabe kein automatischer Abruf. Eine manuelle Datei beweist weder vollständige Corporate-Action-Abdeckung noch historische Point-in-Time-Verfügbarkeit.</p></section>
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <form onSubmit={submitPreview} className="grid gap-4 sm:grid-cols-2">
        <label>Datentyp<select disabled={pending} className="mt-2 w-full rounded border border-zinc-700 bg-zinc-950 p-3" value={kind} onChange={(event) => { setKind(event.target.value as ImportKind); setPreview(null); setResult(null); setConfirmed(false); setAcceptPartial(false); setPolicy("REJECT"); setNote(""); upload.reset(); commit.reset(); }}>{Object.entries(labels).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>
        <div aria-label="CSV-Dateiabgabe" className="rounded border border-dashed border-zinc-600 p-3" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); if (event.dataTransfer.files.length !== 1) { if (!pending) { reset(); setFileError("Genau eine CSV-Datei ablegen. Sie darf Zeilen für mehrere Instrumente enthalten."); } return; } void chooseFile(event.dataTransfer.files[0]); }}>
          <label>UTF-8-CSV (max. 5 MB)<input disabled={pending} className="mt-2 block w-full" type="file" accept=".csv,text/csv" onChange={(event) => { void chooseFile(event.target.files?.[0] ?? null); event.target.value = ""; }} /></label>
          <p className="mt-2 text-sm">Datei auswählen oder hier ablegen. Mehrere Instrumente dürfen in derselben Datei stehen; jede Zeile wird einzeln zugeordnet.</p>
          {file && <p className="mt-2 break-all text-sm">Ausgewählt: {file.name}</p>}
        </div>
        <button disabled={!file || pending} className="rounded bg-emerald-500 px-5 py-3 font-semibold text-zinc-950 disabled:opacity-50">{upload.isPending ? "Original wird geprüft…" : "Vorschau erstellen"}</button>
      </form>
      {reading && <p role="status" className="mt-4">Dateikopf wird geprüft…</p>}
      {detection && <p role="status" className="mt-4">{detection}</p>}
      {fileError && <p role="alert" className="mt-4 text-rose-400">{fileError}</p>}
      {upload.isError && <p role="alert" className="mt-4 text-rose-400">{upload.error.message}</p>}
    </section>
    {preview && <section className="space-y-5 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-semibold">Vorschau und Bestätigung</h2>
      <p className="break-all text-sm text-zinc-400">Raw-Ingestion-ID: {preview.raw_ingestion_id}</p>
      <p>{preview.row_count} Zeilen · {preview.invalid_count} ungültig · {preview.warnings_count} mit Warnung</p>
      <div><h3 className="font-semibold">Spaltenzuordnung</h3><ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">{Object.entries(preview.mapping).map(([from, to]) => <li key={from}>{from} → {to}</li>)}</ul></div>
      {preview.validation_errors.map((error, index) => <p key={index} className="text-rose-400">{error}</p>)}
      <div className="max-h-80 space-y-2 overflow-auto">{preview.sample_rows.map((row) => <div key={row.line} className="rounded border border-zinc-700 p-3 text-sm"><strong>Zeile {row.line}</strong> · {row.instrument_id ?? (kind === "fx" ? "FX" : "Instrument ungeklärt")}<p className="break-all text-zinc-400">{Object.entries(row.values).map(([key, value]) => `${key}: ${value ?? ""}`).join(" · ")}</p><p className="break-all text-emerald-300">Normalisiert: {Object.entries(row.normalized).map(([key, value]) => `${key}: ${value ?? ""}`).join(" | ")}</p>{row.errors.map((error, index) => <p key={index} className="text-rose-400">{error}</p>)}{row.warnings.map((warning, index) => <p key={index} className="text-amber-400">{warning}</p>)}</div>)}</div>
      <label className="flex items-center gap-2"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />Datei, Zuordnung und Ergebnis geprüft</label>
      {preview.invalid_count > 0 && <label className="flex items-center gap-2"><input type="checkbox" checked={acceptPartial} onChange={(event) => setAcceptPartial(event.target.checked)} />Gültige Zeilen übernehmen, ungültige in Quarantäne ablegen</label>}
      <label>Bei Kurskonflikten<select className="ml-3 rounded border border-zinc-700 bg-zinc-950 p-2" value={policy} onChange={(event) => setPolicy(event.target.value as typeof policy)}><option value="REJECT">Prüfung verlangen</option><option value="KEEP_EXISTING">Bisherigen Wert behalten</option><option value="ACCEPT_NEW">Neuen Wert übernehmen</option></select></label>
      {policy !== "REJECT" && <label className="block">Begründung<input className="mt-2 w-full rounded border border-zinc-700 bg-zinc-950 p-3" maxLength={180} value={note} onChange={(event) => setNote(event.target.value)} required /></label>}
      <button disabled={!confirmed || !!result || preview.validation_errors.length > 0 || (preview.invalid_count > 0 && !acceptPartial) || (policy !== "REJECT" && !note.trim()) || pending} onClick={() => commit.mutate()} className="rounded bg-emerald-500 px-5 py-3 font-semibold text-zinc-950 disabled:opacity-50">Explizit übernehmen</button>
      {commit.isError && <p role="alert" className="text-rose-400">{commit.error.message}</p>}
      {result && <div role="status" className="rounded border border-emerald-700 p-4"><p>Übernommen: {result.accepted_rows} akzeptiert, {result.warning_rows} mit Warnung, {result.rejected_rows} verworfen, {result.quarantined} in Quarantäne, {result.new_versions} neue Versionen, {result.unchanged} unverändert, {result.observed_only} nur beobachtet.</p><p className="mt-2 break-all text-sm">Raw-Ingestion-ID: {result.raw_ingestion_id}</p></div>}
    </section>}
  </section>;
}
