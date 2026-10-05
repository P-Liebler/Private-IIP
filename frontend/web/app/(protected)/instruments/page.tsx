"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { previewCsv, searchInstruments, type CsvPreview, type Instrument } from "@/lib/api/market-foundation";

const inputClass = "w-full rounded-md border border-zinc-700 bg-zinc-950 p-3";

export default function InstrumentsPage() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState("STOCK");
  const [currency, setCurrency] = useState("USD");
  const [ticker, setTicker] = useState("");
  const [isin, setIsin] = useState("");
  const [figi, setFigi] = useState("");
  const [exchange, setExchange] = useState("");
  const [mic, setMic] = useState("");
  const [country, setCountry] = useState("");
  const [created, setCreated] = useState<Instrument | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const results = useQuery({ queryKey: ["instruments", search], queryFn: () => searchInstruments(search), enabled: !!search });
  const create = useMutation({ mutationFn: () => api<Instrument>("/instruments", {
    method: "POST", body: JSON.stringify({
      name, asset_type: assetType, currency: currency.toUpperCase(),
      ticker: ticker || null, isin: isin || null, figi: figi || null,
      exchange: exchange || null, mic: mic || null, country: country || null,
    }),
  }), onSuccess: (item) => { setCreated(item); setSearch(item.ticker ?? item.name); } });
  const upload = useMutation({ mutationFn: (selected: File) => previewCsv(selected), onSuccess: setPreview });
  function submitSearch(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setSearch(query.trim()); }

  return <main className="space-y-9 py-10">
    <header><h1 className="text-3xl font-semibold">Instrumente</h1><p className="mt-2 text-zinc-400">Lokaler Instrument Master. Treffer nach Name sind Kandidaten; Kennungen können mehrdeutig sein.</p></header>
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-semibold">Suchen</h2>
      <form onSubmit={submitSearch} className="mt-4 flex gap-3"><input aria-label="Name oder Kennung" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, Ticker, ISIN oder FIGI" className={inputClass} required /><button className="rounded-md bg-emerald-500 px-5 font-semibold text-zinc-950">Suchen</button></form>
      {results.isPending && search && <p className="mt-4 text-zinc-400">Suche läuft…</p>}
      {results.isError && <p role="alert" className="mt-4 text-rose-400">{results.error.message}</p>}
      {results.data?.length === 0 && <p className="mt-4 text-zinc-400">Keine lokalen Treffer.</p>}
      <ul className="mt-4 space-y-3">{results.data?.map((hit) => <li key={hit.instrument.id} className="rounded-md border border-zinc-700 p-4">
        <Link href={`/instrument/${hit.instrument.id}`} className="font-semibold text-emerald-400 hover:underline">{hit.instrument.name}</Link>
        <p className="text-sm text-zinc-300">{hit.instrument.ticker ?? "Kein Ticker"} · {hit.instrument.asset_type} · {hit.instrument.currency}</p>
        <p className="text-xs text-zinc-400">{hit.match_type} · {hit.resolution_status} · {hit.current ? "aktuelle Kennung" : "historische Kennung"}</p>
      </li>)}</ul>
    </section>
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-semibold">Manuell anlegen</h2>
      <p className="mt-2 text-sm text-zinc-400">Nur bestätigte Stammdaten eingeben. Fehlende Kennungen können leer bleiben.</p>
      <form onSubmit={(event) => { event.preventDefault(); create.mutate(); }} className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="sm:col-span-2">Name<input required value={name} onChange={(event) => setName(event.target.value)} className={inputClass} /></label>
        <label>Typ<select value={assetType} onChange={(event) => setAssetType(event.target.value)} className={inputClass}><option value="STOCK">Aktie</option><option value="ETF">ETF</option></select></label>
        <label>Währung<input required maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value)} className={inputClass} /></label>
        <label>Ticker<input value={ticker} onChange={(event) => setTicker(event.target.value)} className={inputClass} /></label>
        <label>ISIN<input value={isin} onChange={(event) => setIsin(event.target.value)} className={inputClass} /></label>
        <label>FIGI<input value={figi} onChange={(event) => setFigi(event.target.value)} className={inputClass} /></label>
        <label>Börse<input value={exchange} onChange={(event) => setExchange(event.target.value)} className={inputClass} /></label>
        <label>MIC<input value={mic} onChange={(event) => setMic(event.target.value)} className={inputClass} /></label>
        <label>Land<input value={country} onChange={(event) => setCountry(event.target.value)} className={inputClass} /></label>
        <button disabled={create.isPending} className="rounded-md bg-emerald-500 px-5 py-3 font-semibold text-zinc-950 disabled:opacity-50">Anlegen</button>
      </form>
      {create.isError && <p role="alert" className="mt-4 text-rose-400">{create.error.message}</p>}
      {created && <p role="status" className="mt-4 text-emerald-400">Angelegt: <Link href={`/instrument/${created.id}`} className="underline">{created.name}</Link></p>}
    </section>
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-xl font-semibold">CSV prüfen</h2>
      <p className="mt-2 text-sm text-zinc-400">Die Originaldatei wird gespeichert und geprüft. Die Vorschau legt keine Marktpreise an. UTF-8, maximal 5 MB; Spalten für Datum, Schlusskurs und Kennung.</p>
      <form onSubmit={(event) => { event.preventDefault(); if (file) upload.mutate(file); }} className="mt-4 flex flex-wrap gap-3"><input aria-label="CSV-Datei" type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setPreview(null); }} required /><button disabled={!file || upload.isPending} className="rounded-md border border-emerald-500 px-4 py-2 text-emerald-400 disabled:opacity-50">Vorschau</button></form>
      {upload.isError && <p role="alert" className="mt-4 text-rose-400">{upload.error.message}</p>}
      {preview && <div className="mt-5 space-y-2 text-sm"><p>Rohdaten-ID: <code>{preview.raw_ingestion_id}</code> · {preview.row_count} Zeilen</p><p>Spalten: {preview.detected_columns.join(", ")}</p><p>Zuordnung: {Object.entries(preview.possible_mapping).map(([from, to]) => `${from} → ${to}`).join(", ")}</p>{preview.validation_errors.map((error, i) => <p key={i} className="text-rose-400">{error}</p>)}<ul className="space-y-2">{preview.sample_rows.map((row) => <li key={row.line} className="rounded border border-zinc-700 p-3">Zeile {row.line}: {row.resolution_status}{row.instrument_id && <> · <Link href={`/instrument/${row.instrument_id}`} className="text-emerald-400 underline">Instrument</Link></>}{row.errors.length > 0 && <span className="text-rose-400"> · {row.errors.join(", ")}</span>}</li>)}</ul></div>}
    </section>
  </main>;
}
