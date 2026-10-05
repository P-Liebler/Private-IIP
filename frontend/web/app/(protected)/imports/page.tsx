"use client";

import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  commitMarketCsv, previewMarketCsv,
  type ImportKind, type ImportResult, type MarketPreview,
} from "@/lib/api/market-data";

const labels: Record<ImportKind, string> = {
  prices: "Tageskurse", actions: "Corporate Actions", fx: "Wechselkurse",
};

export default function ImportsPage() {
  const [kind, setKind] = useState<ImportKind>("prices");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<MarketPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [acceptPartial, setAcceptPartial] = useState(false);
  const [policy, setPolicy] = useState<"REJECT" | "ACCEPT_NEW" | "KEEP_EXISTING">("REJECT");
  const [note, setNote] = useState("");
  const upload = useMutation({
    mutationFn: () => previewMarketCsv(kind, file!),
    onSuccess: (value) => { setPreview(value); setResult(null); setConfirmed(false); },
  });
  const commit = useMutation({
    mutationFn: () => commitMarketCsv(kind, preview!, {
      accept_partial: acceptPartial, conflict_policy: policy, decision_note: note,
    }),
    onSuccess: setResult,
  });
  function reset() { setFile(null); setPreview(null); setResult(null); setConfirmed(false); }
  function submitPreview(event: FormEvent) { event.preventDefault(); if (file) upload.mutate(); }
  return <main className="space-y-8 py-10">
    <header><h1 className="text-3xl font-semibold">CSV-Import</h1><p className="mt-2 text-zinc-400">Originaldatei prüfen, Zuordnung bestätigen und erst dann in geprüfte Daten übernehmen.</p></header>
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <form onSubmit={submitPreview} className="grid gap-4 sm:grid-cols-2">
        <label>Datentyp<select className="mt-2 w-full rounded border border-zinc-700 bg-zinc-950 p-3" value={kind} onChange={(event) => { setKind(event.target.value as ImportKind); reset(); }}>{Object.entries(labels).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>
        <label>UTF-8-CSV (max. 5 MB)<input className="mt-2 block w-full" type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setPreview(null); setResult(null); }} required /></label>
        <button disabled={!file || upload.isPending} className="rounded bg-emerald-500 px-5 py-3 font-semibold text-zinc-950 disabled:opacity-50">Vorschau erstellen</button>
      </form>
      {upload.isError && <p role="alert" className="mt-4 text-rose-400">{upload.error.message}</p>}
    </section>
    {preview && <section className="space-y-5 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-semibold">Vorschau und Bestätigung</h2>
      <p className="break-all text-sm text-zinc-400">Raw-Ingestion-ID: {preview.raw_ingestion_id}</p>
      <p>{preview.row_count} Zeilen · {preview.invalid_count} ungültig · {preview.warnings_count} mit Warnung</p>
      <div><h3 className="font-semibold">Spaltenzuordnung</h3><ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">{Object.entries(preview.mapping).map(([from, to]) => <li key={from}>{from} → {to}</li>)}</ul></div>
      {preview.validation_errors.map((error, index) => <p key={index} className="text-rose-400">{error}</p>)}
      <div className="max-h-80 space-y-2 overflow-auto">{preview.sample_rows.map((row) => <div key={row.line} className="rounded border border-zinc-700 p-3 text-sm"><strong>Zeile {row.line}</strong> · {row.instrument_id ?? (kind === "fx" ? "FX" : "Instrument ungeklärt")}<p className="break-all text-zinc-400">{Object.entries(row.values).map(([key, value]) => `${key}: ${value ?? ""}`).join(" · ")}</p>{row.errors.map((error, index) => <p key={index} className="text-rose-400">{error}</p>)}{row.warnings.map((warning, index) => <p key={index} className="text-amber-400">{warning}</p>)}</div>)}</div>
      <label className="flex items-center gap-2"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />Datei, Zuordnung und Ergebnis geprüft</label>
      {preview.invalid_count > 0 && <label className="flex items-center gap-2"><input type="checkbox" checked={acceptPartial} onChange={(event) => setAcceptPartial(event.target.checked)} />Gültige Zeilen übernehmen, ungültige in Quarantäne ablegen</label>}
      <label>Bei Kurskonflikten<select className="ml-3 rounded border border-zinc-700 bg-zinc-950 p-2" value={policy} onChange={(event) => setPolicy(event.target.value as typeof policy)}><option value="REJECT">Prüfung verlangen</option><option value="KEEP_EXISTING">Bisherigen Wert behalten</option><option value="ACCEPT_NEW">Neuen Wert übernehmen</option></select></label>
      {policy !== "REJECT" && <label className="block">Begründung<input className="mt-2 w-full rounded border border-zinc-700 bg-zinc-950 p-3" maxLength={180} value={note} onChange={(event) => setNote(event.target.value)} required /></label>}
      <button disabled={!confirmed || preview.validation_errors.length > 0 || (preview.invalid_count > 0 && !acceptPartial) || (policy !== "REJECT" && !note.trim()) || commit.isPending} onClick={() => commit.mutate()} className="rounded bg-emerald-500 px-5 py-3 font-semibold text-zinc-950 disabled:opacity-50">Explizit übernehmen</button>
      {commit.isError && <p role="alert" className="text-rose-400">{commit.error.message}</p>}
      {result && <div role="status" className="rounded border border-emerald-700 p-4"><p>Übernommen: {result.inserted} neu, {result.corrected} korrigiert, {result.unchanged} unverändert, {result.observed_only} nur beobachtet, {result.quarantined} in Quarantäne.</p><p className="mt-2 break-all text-sm">Raw-Ingestion-ID: {result.raw_ingestion_id}</p></div>}
    </section>}
  </main>;
}
