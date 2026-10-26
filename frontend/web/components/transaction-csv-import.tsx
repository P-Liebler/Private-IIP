"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, API_BASE } from "@/lib/api";
import { searchInstruments, type SearchResult } from "@/lib/api/market-foundation";
import type { Account, CsvFormat, ImportPreview } from "@/lib/api/portfolios";
import { FileDropzone, Stepper } from "@/components/ui/primitives";

const input = "w-full rounded border border-zinc-700 bg-zinc-950 p-2";
const fields = ["type", "trade_date", "settlement_date", "instrument_id", "isin", "ticker", "figi", "quantity", "price", "currency", "amount", "fee", "tax", "external_id", "account", "fx_rate_to_base", "notes"];

export function TransactionCsvImport({ portfolioId, accounts, onImported }: { portfolioId: string; accounts: Account[]; onImported: () => void }) {
  const [account, setAccount] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [resolutions, setResolutions] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [dirty, setDirty] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [explicitFormat, setExplicitFormat] = useState(false);
  const [csvFormat, setCsvFormat] = useState<CsvFormat>({ delimiter: ",", date_format: "ISO", number_format: "POINT" });
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [selectedHits, setSelectedHits] = useState<SearchResult[]>([]);
  const instruments = useQuery({ queryKey: ["import-instruments", search], queryFn: () => searchInstruments(search), enabled: !!search });
  const choices = Array.from(new Map([...selectedHits, ...(instruments.data ?? [])].map(hit => [hit.instrument.id, hit])).values());
  const upload = useMutation({ mutationFn: async () => {
    if (!file) throw new Error("CSV-Datei auswählen");
    const params = new URLSearchParams({ account_id: account, instrument_resolutions: JSON.stringify(resolutions) });
    if (Object.keys(mapping).length) params.set("column_mapping", JSON.stringify(mapping));
    if (explicitFormat) params.set("csv_format", JSON.stringify(csvFormat));
    const response = await fetch(`${API_BASE}/portfolios/${portfolioId}/transactions/import/preview?${params}`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "text/csv", "X-Filename": file.name }, body: file,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error?.message ?? "Vorschau fehlgeschlagen");
    return result as ImportPreview;
  }, onSuccess: result => { setPreview(result); setMapping(result.mapping); setDirty(false); setConfirmed(false); } });
  const commit = useMutation({ mutationFn: () => api<{ created_count: number; duplicate_count?: number; status?: string }>(`/portfolios/${portfolioId}/transactions/import/commit`, {
    method: "POST", body: JSON.stringify({ account_id: account, raw_ingestion_id: preview?.raw_ingestion_id, mapping: preview?.mapping, instrument_resolutions: resolutions, csv_format: explicitFormat ? csvFormat : null }),
  }), onSuccess: () => { setPreview(null); setConfirmed(false); onImported(); } });
  const canImport = preview && !dirty && preview.row_count > 0 && preview.rows.every(row => ["READY", "DUPLICATE"].includes(row.status));
  return <section id="transaction-import" className="space-y-4 rounded-xl border border-zinc-800 p-5">
    <h2 className="text-xl font-semibold">CSV-Transaktionen importieren</h2>
    <Stepper steps={["Datei", "Format & Zuordnung", "Vorschau", "Bestätigen"]} current={!file ? 0 : !preview || dirty || preview.format_required ? 1 : !confirmed ? 2 : 3} />
    <p className="text-sm text-zinc-400">Eigener rechtmäßiger UTF-8-Export, auch mit BOM. Mehrdeutige Datums- und Zahlenformate müssen Sie auswählen. Käufe/Verkäufe benötigen Stückzahl und Preis, Cash-Ereignisse einen Betrag.</p>
    <a className="text-emerald-400 underline" download="transactions-template.csv" href={`data:text/csv;charset=utf-8,${encodeURIComponent(fields.join(",") + "\n")}`}>Leere CSV-Vorlage herunterladen</a>
    <label className="block">Importkonto<select aria-label="Importkonto" value={account} onChange={e => { setAccount(e.target.value); setPreview(null); setConfirmed(false); }} className={input}><option value="">Konto auswählen</option>{accounts.filter(a => !a.archived_at).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
    <FileDropzone label="Transaktionsdatei" file={file} onFile={value => { setFile(value); setPreview(null); setMapping({}); setResolutions({}); setConfirmed(false); }} />
    <label className="block"><input type="checkbox" checked={explicitFormat} onChange={e => { setExplicitFormat(e.target.checked); setDirty(true); setConfirmed(false); }} /> Dateiformat ausdrücklich festlegen</label>
    {(explicitFormat || preview?.format_required) && <fieldset className="grid gap-3 sm:grid-cols-3"><legend>Format prüfen — keine Buchung vor eindeutiger Auswahl</legend>
      <label>Trennzeichen<select aria-label="CSV-Trennzeichen" className={input} value={csvFormat.delimiter} onChange={e => { setCsvFormat(v => ({ ...v, delimiter: e.target.value as CsvFormat["delimiter"] })); setExplicitFormat(true); setDirty(true); setConfirmed(false); }}><option value=",">Komma</option><option value=";">Semikolon</option><option value={"\t"}>Tabulator</option></select></label>
      <label>Datumsformat<select aria-label="CSV-Datumsformat" className={input} value={csvFormat.date_format} onChange={e => { setCsvFormat(v => ({ ...v, date_format: e.target.value as CsvFormat["date_format"] })); setExplicitFormat(true); setDirty(true); setConfirmed(false); }}><option value="ISO">Jahr-Monat-Tag (2026-10-23)</option><option value="DMY">Tag.Monat.Jahr (23.10.2026 oder 23/10/2026)</option><option value="MDY">Monat/Tag/Jahr (10/23/2026)</option></select></label>
      <label>Zahlenformat<select aria-label="CSV-Zahlenformat" className={input} value={csvFormat.number_format} onChange={e => { setCsvFormat(v => ({ ...v, number_format: e.target.value as CsvFormat["number_format"] })); setExplicitFormat(true); setDirty(true); setConfirmed(false); }}><option value="POINT">Dezimalpunkt (1234.50)</option><option value="COMMA">Dezimalkomma (1234,50), keine Tausenderpunkte</option><option value="CH">Schweiz (1&apos;234.50)</option></select></label>
    </fieldset>}
    <button disabled={!account || !file || upload.isPending} onClick={() => upload.mutate()} className="rounded border border-emerald-500 px-4 py-2 disabled:opacity-50">Vorschau prüfen</button>
    {upload.isError && <p role="alert">{upload.error.message}</p>}
    {preview && <>
      {preview.format_required && <p role="alert">Format nicht eindeutig. Bitte Trennzeichen, Datumsreihenfolge und Zahlenformat ausdrücklich festlegen und die Vorschau erneut prüfen.</p>}
      {preview.detected_format && <p className="text-xs ui-muted">Geprüftes Format: {preview.detected_format.delimiter === ";" ? "Semikolon" : preview.detected_format.delimiter === "," ? "Komma" : "Tabulator"} · {preview.detected_format.date_format} · {preview.detected_format.number_format}. Formatänderungen erfordern eine neue Vorschau.</p>}
      <p role="status">{preview.row_count} Zeilen · {preview.ready_count} importierbar · {preview.duplicate_count ?? 0} Duplikate. Noch keine Buchung übernommen.</p>
      <fieldset className="grid gap-3 sm:grid-cols-2"><legend>Erkannte Spalten zuordnen</legend>{preview.columns.map(column => <label key={column}>{column}<select value={mapping[column] ?? ""} className={input} onChange={e => { const next = { ...mapping }; if (e.target.value) next[column] = e.target.value; else delete next[column]; setMapping(next); setDirty(true); setConfirmed(false); }}><option value="">Ignorieren</option>{fields.map(f => <option key={f}>{f}</option>)}</select></label>)}</fieldset>
      <div className="rounded border border-zinc-700 p-3"><p>Unklare Instrumente ausdrücklich auswählen. Ticker allein ist nicht eindeutig. ISIN, Börse/MIC, Währung und Instrumenttyp prüfen.</p><Link className="text-emerald-400 underline" href="/instruments">Instrumente prüfen oder anlegen</Link>
        <label className="mt-3 block">Instrument für CSV-Zuordnung suchen<input value={query} onChange={e => setQuery(e.target.value)} className={input} /></label><button onClick={() => setSearch(query.trim())} className="mt-2 rounded border px-3 py-1">Zuordnung suchen</button>
        {instruments.isError && <p role="alert">{instruments.error.message}</p>}
      </div>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="text-left">Importvorschau mit Buchungswerten und Instrumentenprüfung</caption><thead><tr>{["Zeile / Status", "Datum / Typ", "Instrument", "Menge / Preis", "Betrag / Währung", "Gebühr / Steuer", "Explizite Zuordnung"].map(h => <th key={h} className="p-2">{h}</th>)}</tr></thead><tbody>{preview.rows.map(row => <tr key={row.line} className="border-t border-zinc-800"><td className="p-2">{row.line} · {row.status}<p className="text-amber-400">{row.error}</p></td><td className="p-2">{row.trade_date ?? "—"} · {row.type ?? "—"}<p>{row.settlement_date ? `Valuta ${row.settlement_date}` : ""}</p></td><td className="p-2">{row.instrument_name ?? (row.instrument_id ? "Instrument aufgelöst" : "—")}</td><td className="p-2">{row.quantity ?? "—"} / {row.price ?? "—"}</td><td className="p-2">{row.amount ?? (row.type === "OPENING_POSITION" ? "Einstand unbekannt" : "Aus Menge/Preis")} {row.currency}</td><td className="p-2">{row.fee ?? "—"} / {row.tax ?? "—"}</td><td className="p-2"><select aria-label={`Instrument für CSV-Zeile ${row.line}`} value={resolutions[row.line] ?? ""} className={input} onChange={e => { const hit = choices.find(item => item.instrument.id === e.target.value); if (hit) setSelectedHits(previous => [...previous.filter(item => item.instrument.id !== hit.instrument.id), hit]); const next = { ...resolutions }; if (e.target.value) next[row.line] = e.target.value; else delete next[row.line]; setResolutions(next); setDirty(true); setConfirmed(false); }}><option value="">CSV-Kennungen verwenden</option>{choices.map(hit => <option key={hit.instrument.id} value={hit.instrument.id}>{hit.instrument.name} · {hit.instrument.isin ?? hit.instrument.ticker} · {hit.instrument.mic ?? hit.instrument.exchange ?? "Börse ungeprüft"} · {hit.instrument.currency} · {hit.instrument.asset_type}</option>)}</select></td></tr>)}</tbody></table></div>
      {dirty && <p role="status" className="text-amber-400">Zuordnung geändert: Vorschau erneut prüfen.</p>}
      <label className="block"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} disabled={!canImport} /> Ich habe Konto, Instrumente, Beträge und Duplikate geprüft und bestätige die Buchungen.</label>
      <button disabled={!canImport || !confirmed || commit.isPending} onClick={() => commit.mutate()} className="rounded bg-emerald-500 px-4 py-2 text-zinc-950 disabled:opacity-50">Import übernehmen</button>
    </>}
    {commit.isError && <p role="alert">{commit.error.message}</p>}
    {commit.isSuccess && <p role="status">{commit.data.status === "ALREADY_COMMITTED" ? "Bereits übernommener Import; keine erneute Buchung." : `${commit.data.created_count} Buchungen übernommen; ${commit.data.duplicate_count ?? 0} Duplikate übersprungen.`}</p>}
  </section>;
}
