"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { searchInstruments } from "@/lib/api/market-foundation";
import { API_BASE } from "@/lib/api";
import { getAllocation, getPerformance, getValuation, listAccounts, listPortfolios,
  listTransactions, getSummary, listBenchmarks, type Account, type ImportPreview, type Transaction } from "@/lib/api/portfolios";
import { money, ratio } from "@/lib/portfolio-format";
import { AllocationChart, ValueChart } from "@/components/portfolio-charts";
import { CorporateActionReview } from "@/components/corporate-action-review";

const input = "w-full rounded border border-zinc-700 bg-zinc-950 p-2";
const kinds = ["DEPOSIT", "WITHDRAWAL", "BUY", "SELL", "DIVIDEND", "INTEREST", "FEE", "TAX", "TRANSFER_IN", "TRANSFER_OUT", "SPLIT", "CASH_ADJUSTMENT"];

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const cache = useQueryClient();
  const [tab, setTab] = useState("Übersicht");
  const [accountName, setAccountName] = useState("");
  const [accountType, setAccountType] = useState("BROKER");
  const [accountId, setAccountId] = useState("");
  const [kind, setKind] = useState("DEPOSIT");
  const [day, setDay] = useState(new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [fee, setFee] = useState("0");
  const [tax, setTax] = useState("0");
  const [currency, setCurrency] = useState("CHF");
  const [instrumentQuery, setInstrumentQuery] = useState("");
  const [instrumentSearch, setInstrumentSearch] = useState("");
  const [instrumentId, setInstrumentId] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [newName, setNewName] = useState("");
  const [historyStart, setHistoryStart] = useState(() => new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10));
  const [historyEnd, setHistoryEnd] = useState(new Date().toISOString().slice(0, 10));
  const [historyRequested, setHistoryRequested] = useState(false);
  const portfolios = useQuery({ queryKey: ["portfolios"], queryFn: listPortfolios });
  const portfolio = portfolios.data?.find(item => item.id === id);
  const accounts = useQuery({ queryKey: ["accounts", id], queryFn: () => listAccounts(id) });
  const transactions = useQuery({ queryKey: ["transactions", id], queryFn: () => listTransactions(id) });
  const valuation = useQuery({ queryKey: ["valuation", id], queryFn: () => getValuation(id) });
  const summary = useQuery({ queryKey: ["summary", id], queryFn: () => getSummary(id) });
  const benchmarks = useQuery({ queryKey: ["benchmarks"], queryFn: listBenchmarks });
  const updatePortfolio = useMutation({ mutationFn: (changes: { name?: string; benchmark_id?: string | null }) => api(`/portfolios/${id}`, { method: "PATCH", body: JSON.stringify(changes) }), onSuccess: () => { cache.invalidateQueries({ queryKey: ["portfolios"] }); cache.invalidateQueries({ queryKey: ["performance", id] }); } });
  const archivePortfolio = useMutation({ mutationFn: () => api(`/portfolios/${id}`, { method: "DELETE" }), onSuccess: () => { cache.invalidateQueries({ queryKey: ["portfolios"] }); router.push("/portfolios"); } });
  const createBenchmark = useMutation({ mutationFn: () => api("/benchmarks", { method: "POST", body: JSON.stringify({ instrument_id: instrumentId }) }), onSuccess: () => cache.invalidateQueries({ queryKey: ["benchmarks"] }) });
  const allocation = useQuery({ queryKey: ["allocation", id], queryFn: () => getAllocation(id), enabled: tab === "Allokation" });
  const performance = useQuery({ queryKey: ["performance", id, historyStart, historyEnd],
    queryFn: () => getPerformance(id, historyStart, historyEnd), enabled: tab === "Performance" && historyRequested });
  const instruments = useQuery({ queryKey: ["instrument-search", instrumentSearch],
    queryFn: () => searchInstruments(instrumentSearch), enabled: !!instrumentSearch });
  const refresh = () => { cache.invalidateQueries({ queryKey: ["valuation", id] });
    cache.invalidateQueries({ queryKey: ["summary", id] }); cache.invalidateQueries({ queryKey: ["portfolio-dashboard"] });
    cache.invalidateQueries({ queryKey: ["transactions", id] });
    cache.invalidateQueries({ queryKey: ["allocation", id] });
    cache.invalidateQueries({ queryKey: ["performance", id] }); };
  const createAccount = useMutation({ mutationFn: () => api<Account>(`/portfolios/${id}/accounts`, {
    method: "POST", body: JSON.stringify({ name: accountName, account_type: accountType, default_currency: currency }) }),
    onSuccess: row => { setAccountName(""); setAccountId(row.id); cache.invalidateQueries({ queryKey: ["accounts", id] }); } });
  const saveTransaction = useMutation({ mutationFn: () => {
    const security = ["BUY", "SELL", "SPLIT", "DIVIDEND"].includes(kind);
    const shares = ["BUY", "SELL", "SPLIT"].includes(kind);
    const trading = ["BUY", "SELL"].includes(kind);
    const chargeable = ["BUY", "SELL", "DIVIDEND", "INTEREST"].includes(kind);
    const body = { account_id: accountId, type: kind, trade_date: day, currency,
      instrument_id: security ? instrumentId || null : null,
      quantity: shares ? quantity || null : null,
      price: trading ? price || null : null,
      amount: trading || kind === "SPLIT" ? null : amount || null,
      fee: chargeable ? fee || "0" : "0", tax: chargeable ? tax || "0" : "0" };
    return api<Transaction>(editing ? `/transactions/${editing}` : `/portfolios/${id}/transactions`,
      { method: editing ? "PATCH" : "POST", body: JSON.stringify(body) });
  }, onSuccess: () => { setEditing(null); setAmount(""); setQuantity(""); setPrice(""); setFee("0"); setTax("0"); refresh(); } });
  const voidTransaction = useMutation({ mutationFn: (txId: string) => api<Transaction>(`/transactions/${txId}`, { method: "DELETE" }), onSuccess: refresh });
  const upload = useMutation({ mutationFn: async ({ selected, columns }: { selected: File; columns?: Record<string, string> }) => {
    const query = new URLSearchParams({ account_id: accountId });
    if (columns) query.set("column_mapping", JSON.stringify(columns));
    const response = await fetch(`${API_BASE}/portfolios/${id}/transactions/import/preview?${query}`,
      { method: "POST", credentials: "include", headers: { "Content-Type": "text/csv", "X-Filename": selected.name }, body: selected });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error?.message ?? "CSV-Vorschau fehlgeschlagen");
    return body as ImportPreview;
  }, onSuccess: result => { setPreview(result); setMapping(result.mapping); } });
  const commitImport = useMutation({ mutationFn: () => api<{ created_count: number }>(`/portfolios/${id}/transactions/import/commit`, {
    method: "POST", body: JSON.stringify({ account_id: accountId, raw_ingestion_id: preview?.raw_ingestion_id, mapping: preview?.mapping }) }),
    onSuccess: () => { setPreview(null); refresh(); } });
  function selectTransaction(row: Transaction) {
    setEditing(row.id); setAccountId(row.account_id); setKind(row.type); setDay(row.trade_date);
    setCurrency(row.currency); setInstrumentId(row.instrument_id ?? ""); setQuantity(row.quantity ?? "");
    setPrice(row.price ?? ""); setAmount(row.amount ?? ""); setFee(row.fee); setTax(row.tax); setTab("Transaktionen");
  }
  const valuationData = valuation.data;
  return <main className="space-y-6 py-10">
    <header><h1 className="text-3xl font-semibold">{portfolio?.name ?? "Portfolio"}</h1><p className="mt-2 text-zinc-400">Basiswährung: {portfolio?.base_currency ?? "…"}</p></header>
    <details className="rounded border border-zinc-800 p-4"><summary>Portfolio verwalten</summary>
      <form onSubmit={event => { event.preventDefault(); updatePortfolio.mutate({ name: newName }); }} className="mt-3 flex gap-3"><input aria-label="Neuer Portfolio-Name" required value={newName} onChange={event => setNewName(event.target.value)} className={input} /><button className="text-emerald-400">Umbenennen</button></form>
      <button onClick={() => archivePortfolio.mutate()} className="mt-3 text-rose-400">Portfolio archivieren</button>
      <label className="mt-4 block">Benchmark<select value={portfolio?.benchmark_id ?? ""} onChange={event => updatePortfolio.mutate({ benchmark_id: event.target.value || null })} className={input}><option value="">NONE</option>{benchmarks.data?.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <p className="mt-2 text-sm text-zinc-400">Ein im Transaktionsformular gewähltes Instrument kann als Benchmark registriert werden.</p><button disabled={!instrumentId} onClick={() => createBenchmark.mutate()} className="text-emerald-400">Gewähltes Instrument als Benchmark registrieren</button>
      {[updatePortfolio, archivePortfolio, createBenchmark].map((mutation, index) => mutation.isError && <p key={index} role="alert">{mutation.error.message}</p>)}
    </details>
    <nav className="flex flex-wrap gap-2" aria-label="Portfolio-Bereiche">{["Übersicht", "Positionen", "Performance", "Allokation", "Dividenden", "Transaktionen", "Datenqualität"].map(item => <button key={item} onClick={() => setTab(item)} className={`rounded px-3 py-2 ${tab === item ? "bg-emerald-500 text-zinc-950" : "border border-zinc-700"}`}>{item}</button>)}</nav>
    {valuation.isPending && <p>Bewertung wird geladen…</p>}
    {valuation.isError && <p role="alert" className="text-rose-400">{valuation.error.message}</p>}
    {valuationData && <>
      {tab === "Übersicht" && <section className="space-y-3"><p className="text-sm text-zinc-400">Renditen: PROVISIONAL · Corporate-Action-Abdeckung ungeprüft. Bewertungsdatum: {valuationData.on_date} · Analyse: {valuationData.analytics_status}</p><div className="grid gap-4 sm:grid-cols-3"><Tile label="Tagesertrag (ohne externe Flows)" value={money(summary.data?.daily_change_base, valuationData.base_currency)} /><Tile label="Gesamtertrag" value={money(summary.data?.total_return_base, valuationData.base_currency)} /><Tile label="YTD-Ertrag" value={money(summary.data?.ytd_return_base, valuationData.base_currency)} /><Tile label="Investierter Marktwert" value={money(valuationData.securities_value_base, valuationData.base_currency)} /><Tile label="Gebühren" value={money(valuationData.fees_base_at_event_fx, valuationData.base_currency)} /><Tile label="Steuern" value={money(valuationData.taxes_base_at_event_fx, valuationData.base_currency)} /></div>{summary.isError && <p role="alert">{summary.error.message}</p>}<p className="text-sm text-zinc-400">Kursalter: {valuationData.holdings.map(item => `${item.name}: ${item.price_age_days ?? "DATA_UNAVAILABLE"} Tage`).join(" · ") || "Keine offenen Positionen"}</p></section>}
      {valuationData.status !== "COMPLETE" && <p role="status" className="rounded border border-amber-700 bg-amber-950 p-4">Portfolio PARTIAL: Der Gesamtwert ist wegen fehlender oder alter Daten nicht verfügbar. Bekannte Teilwerte bleiben sichtbar.</p>}
      {tab === "Übersicht" && <div className="grid gap-4 sm:grid-cols-3"><Tile label="Gesamtwert" value={money(valuationData.total_value_base, valuationData.base_currency)} /><Tile label="Bekannter Teilwert" value={money(valuationData.known_value_base, valuationData.base_currency)} /><Tile label="Cash" value={money(valuationData.cash_value_base, valuationData.base_currency)} /><Tile label="Realisiert (FX am Buchungstag)" value={money(valuationData.realized_pnl_base_at_trade_fx, valuationData.base_currency)} /><Tile label="Unrealisiert (heutiger FX)" value={money(valuationData.unrealized_pnl_base_at_valuation_fx, valuationData.base_currency)} /><Tile label="Brutto-Erträge (FX am Buchungstag)" value={money(valuationData.income_base_at_event_fx, valuationData.base_currency)} />
        <section className="sm:col-span-3 rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">Cash nach Währung</h2>{valuationData.cash.length ? <ul className="mt-3 space-y-1">{valuationData.cash.map((cash, index) => <li key={index}>{money(cash.amount, cash.currency)} → {money(cash.base_amount, valuationData.base_currency)} · FX {cash.fx.rate_date ?? "DATA_UNAVAILABLE"}, Alter {cash.fx.age_days ?? "DATA_UNAVAILABLE"} Tage, {cash.fx.derived ?? "DATA_UNAVAILABLE"}</li>)}</ul> : <p className="mt-2 text-zinc-400">Noch keine Cash-Buchungen.</p>}</section></div>}
      {tab === "Positionen" && <section className="space-y-3">{valuationData.holdings.length === 0 && <p>Keine offenen Positionen.</p>}{valuationData.holdings.map((item, index) => <article key={`${item.account_id}-${item.instrument_id}-${index}`} className="rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">{item.name}</h2><p className="text-sm text-zinc-400">{item.quantity} Stück · Ø Kosten {money(item.average_cost_native, item.currency)} · Einstand {money(item.cost_basis_native, item.currency)}</p><p className="mt-2">Marktwert: {money(item.market_value_native, item.currency)} · Basis: {money(item.market_value_base, valuationData.base_currency)}</p><p>Unrealisiert: {money(item.unrealized_pnl_native, item.currency)} · Gewicht {ratio(item.weight)}</p><p className="text-sm text-zinc-400">Kurs {item.price ?? "DATA_UNAVAILABLE"} vom {item.price_date ?? "–"} · {item.valuation_status} · FX {item.fx.rate_date ?? "DATA_UNAVAILABLE"}, Alter {item.fx.age_days ?? "DATA_UNAVAILABLE"} Tage</p></article>)}</section>}
      {tab === "Datenqualität" && <section className="rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">Bewertungsstatus: {valuationData.status}</h2>{valuationData.issues.length ? <ul className="mt-3 list-disc pl-5">{valuationData.issues.map((issue, index) => <li key={index}>{issue.code}{issue.instrument_id && ` · Instrument ${issue.instrument_id}`}{issue.currency && ` · ${issue.currency}`}{issue.account_id && issue.action_version_ids?.map(actionId => <CorporateActionReview key={actionId} portfolioId={id} accountId={issue.account_id!} versionId={actionId} onApplied={refresh} />)}</li>)}</ul> : <p className="mt-2">Keine offenen Bewertungsprobleme.</p>}</section>}
      {tab === "Dividenden" && <section className="space-y-3"><h2 className="font-semibold">Dividenden und Zinsen</h2>{transactions.data?.filter(row => row.status === "ACTIVE" && ["DIVIDEND", "INTEREST"].includes(row.type)).map(row => <article key={row.id} className="rounded border border-zinc-800 p-4"><p>{row.trade_date} · {row.type} · Instrument {row.instrument_id ?? "—"}</p><p>Brutto: {money(row.amount, row.currency)} · Gebühr: {money(row.fee, row.currency)} · Steuer: {money(row.tax, row.currency)}</p><p className="text-sm text-zinc-400">Quelle: {row.source} · Basis brutto: {money(row.amount_base, valuationData.base_currency)} · Basis netto: {money(row.net_amount_base, valuationData.base_currency)}</p></article>)}</section>}
      {tab === "Allokation" && <section className="space-y-4">{allocation.isPending && <p>Lade Allokation…</p>}{allocation.isError && <p role="alert">{allocation.error.message}</p>}{allocation.data?.status !== "AVAILABLE" && <p>Allokation DATA_UNAVAILABLE, solange der Portfoliowert unvollständig oder null ist.</p>}{allocation.data?.status === "AVAILABLE" && <>
        <AllocationChart title="Instrumente" currency={valuationData.base_currency} items={(allocation.data.by_instrument ?? []).map(item => ({ label: valuationData.holdings.find(holding => holding.instrument_id === item.instrument_id)?.name ?? item.instrument_id, weight: item.weight, value: item.value }))} />
        <AllocationChart title="Währung" currency={valuationData.base_currency} items={(allocation.data.by_currency ?? []).map(item => ({ label: item.currency, weight: item.weight, value: item.value }))} />
        <AllocationChart title="Anlageklasse" currency={valuationData.base_currency} items={(allocation.data.by_asset_type ?? []).map(item => ({ label: item.asset_type, weight: item.weight, value: item.value }))} />
      </>}</section>}
      {tab === "Performance" && <section className="space-y-4 rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">Historische Performance</h2><form onSubmit={event => { event.preventDefault(); setHistoryRequested(true); performance.refetch(); }} className="flex flex-wrap gap-3"><input aria-label="Von" type="date" value={historyStart} onChange={event => { setHistoryStart(event.target.value); setHistoryRequested(false); }} className={input} /><input aria-label="Bis" type="date" value={historyEnd} onChange={event => { setHistoryEnd(event.target.value); setHistoryRequested(false); }} className={input} /><button className="rounded bg-emerald-500 px-4 text-zinc-950">Berechnen</button></form>{performance.isError && <p role="alert">{performance.error.message}</p>}{performance.data && <><p>Status: {performance.data.status} {performance.data.reason}</p><div className="grid gap-3 sm:grid-cols-4"><Tile label="Absoluter Ertrag" value={money(performance.data.absolute_return_base, valuationData.base_currency)} /><Tile label="TWR" value={ratio(performance.data.twr)} /><Tile label="XIRR" value={ratio(performance.data.xirr)} /><Tile label="CAGR" value={ratio(performance.data.cagr)} /></div><p className="text-sm text-zinc-400">FX-Beitrag: {money(performance.data.fx_contribution_base, valuationData.base_currency)}</p><p className="text-sm text-amber-400">Renditen: {performance.data.return_status ?? "DATA_UNAVAILABLE"}</p><ValueChart series={performance.data.series} currency={valuationData.base_currency} /><p>Benchmark (brutto, ohne Wiederanlage) {performance.data.benchmark?.name ?? "NONE"}: {ratio(performance.data.benchmark?.return_base)} · {performance.data.benchmark?.status ?? "DATA_UNAVAILABLE"} {performance.data.benchmark?.reason}</p><ul className="max-h-72 overflow-auto text-sm">{performance.data.series.map(point => <li key={point.date}>{point.date}: {money(point.value_base, valuationData.base_currency)} · {point.status}</li>)}</ul></>}</section>}
    </>}
    {tab === "Transaktionen" && <div className="space-y-6">
      <section className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Account anlegen</h2><form onSubmit={(event: FormEvent) => { event.preventDefault(); createAccount.mutate(); }} className="mt-3 flex flex-wrap gap-3"><input aria-label="Account-Name" required value={accountName} onChange={event => setAccountName(event.target.value)} className={input} /><select aria-label="Account-Typ" value={accountType} onChange={event => setAccountType(event.target.value)} className={input}><option value="BROKER">Broker</option><option value="CASH">Cash</option><option value="MANUAL">Manuell</option></select><button className="rounded bg-emerald-500 px-4 text-zinc-950">Account anlegen</button></form>{createAccount.isError && <p role="alert" className="text-rose-400">{createAccount.error.message}</p>}</section>
      <section className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">{editing ? "Transaktion korrigieren" : "Transaktion erfassen"}</h2><form onSubmit={event => { event.preventDefault(); saveTransaction.mutate(); }} className="mt-4 grid gap-3 sm:grid-cols-2">
        <label>Account<select required value={accountId} onChange={event => setAccountId(event.target.value)} className={input}><option value="">Auswählen</option>{accounts.data?.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Typ<select value={kind} onChange={event => setKind(event.target.value)} className={input}>{kinds.map(item => <option key={item}>{item}</option>)}</select></label>
        <label>Handelsdatum<input type="date" required value={day} onChange={event => setDay(event.target.value)} className={input} /></label>
        <label>Währung<select value={currency} onChange={event => setCurrency(event.target.value)} className={input}><option>CHF</option><option>EUR</option><option>USD</option></select></label>
        {["BUY", "SELL", "SPLIT", "DIVIDEND"].includes(kind) && <div className="sm:col-span-2"><label>Instrument suchen<input value={instrumentQuery} onChange={event => setInstrumentQuery(event.target.value)} className={input} /></label><button type="button" onClick={() => setInstrumentSearch(instrumentQuery)} className="mt-2 rounded border border-zinc-700 px-3 py-1">Suchen</button><ul>{instruments.data?.map(hit => <li key={hit.instrument.id}><button type="button" className="text-emerald-400" onClick={() => { setInstrumentId(hit.instrument.id); setCurrency(hit.instrument.currency); }}>{hit.instrument.name} · {hit.instrument.ticker}</button></li>)}</ul><p className="text-xs text-zinc-400">Gewählt: {instrumentId || "keines"}</p></div>}
        {["BUY", "SELL", "SPLIT"].includes(kind) && <label>{kind === "SPLIT" ? "Split-Verhältnis" : "Stückzahl"}<input required value={quantity} onChange={event => setQuantity(event.target.value)} className={input} /></label>}
        {["BUY", "SELL"].includes(kind) && <label>Preis je Stück<input required value={price} onChange={event => setPrice(event.target.value)} className={input} /></label>}
        {!["BUY", "SELL", "SPLIT"].includes(kind) && <label>Betrag<input required value={amount} onChange={event => setAmount(event.target.value)} className={input} /></label>}
        {["BUY", "SELL", "DIVIDEND", "INTEREST"].includes(kind) && <><label>Gebühr<input value={fee} onChange={event => setFee(event.target.value)} className={input} /></label><label>Steuer / Quellensteuer<input value={tax} onChange={event => setTax(event.target.value)} className={input} /></label></>}
        <button disabled={!accountId || saveTransaction.isPending} className="rounded bg-emerald-500 px-4 py-2 font-semibold text-zinc-950">{editing ? "Korrektur speichern" : "Buchen"}</button>{editing && <button type="button" onClick={() => setEditing(null)} className="rounded border border-zinc-700">Abbrechen</button>}
      </form>{saveTransaction.isError && <p role="alert" className="mt-3 text-rose-400">{saveTransaction.error.message}</p>}</section>
      <section className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">CSV-Transaktionen importieren</h2><p className="mt-2 text-sm text-zinc-400">UTF-8; Spalten: type, trade_date, instrument_id, quantity, price, amount, currency, fee, tax. Erst Vorschau, dann vollständiger Commit.</p><form onSubmit={event => { event.preventDefault(); if (file) upload.mutate({ selected: file }); }} className="mt-3 flex flex-wrap gap-3"><input type="file" accept=".csv,text/csv" onChange={event => setFile(event.target.files?.[0] ?? null)} /><button disabled={!accountId || !file} className="rounded border border-emerald-500 px-3 py-2">Vorschau</button></form>{upload.isError && <p role="alert" className="text-rose-400">{upload.error.message}</p>}{preview && <div className="mt-4"><div className="grid gap-2 sm:grid-cols-2">{preview.columns.map(column => <label key={column}>{column}<select value={mapping[column] ?? ""} onChange={event => { const next = { ...mapping }; if (event.target.value) next[column] = event.target.value; else delete next[column]; setMapping(next); }} className={input}><option value="">Ignorieren</option>{["account", "type", "trade_date", "settlement_date", "instrument_id", "ticker", "isin", "figi", "quantity", "price", "amount", "currency", "fee", "tax", "external_id", "notes", "fx_rate_to_base"].map(field => <option key={field}>{field}</option>)}</select></label>)}</div><button disabled={!file} onClick={() => { if (file) upload.mutate({ selected: file, columns: mapping }); }} className="mt-3 text-emerald-400">Zuordnung prüfen</button><p>{preview.row_count} Zeilen, {preview.ready_count} bereit</p><ul className="max-h-40 overflow-auto text-sm">{preview.rows.map(row => <li key={row.line}>Zeile {row.line}: {row.status} {row.error}</li>)}</ul><button disabled={preview.row_count === 0 || preview.ready_count !== preview.row_count || commitImport.isPending || JSON.stringify(mapping) !== JSON.stringify(preview.mapping)} onClick={() => commitImport.mutate()} className="mt-3 rounded bg-emerald-500 px-4 py-2 text-zinc-950">Import übernehmen</button></div>}{commitImport.isError && <p role="alert" className="text-rose-400">{commitImport.error.message}</p>}</section>
      <section className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Buchungen</h2>{transactions.isError && <p role="alert">{transactions.error.message}</p>}<ul className="mt-3 space-y-2">{transactions.data?.map(row => <li key={row.id} className="rounded border border-zinc-700 p-3"><span className={row.status === "VOIDED" ? "text-zinc-500 line-through" : ""}>{row.trade_date} · {row.type} · Account {accounts.data?.find(item => item.id === row.account_id)?.name ?? row.account_id} · Instrument {row.instrument_id ?? "—"} · Menge {row.quantity ?? "—"} · Preis {money(row.price, row.currency)} · Betrag {money(row.amount, row.currency)} · Gebühr {money(row.fee, row.currency)} · Steuer {money(row.tax, row.currency)} · {row.status}</span>{row.status === "ACTIVE" && !row.action_locked && !row.system_generated && <span className="ml-3 inline-flex gap-3"><button onClick={() => selectTransaction(row)} className="text-emerald-400">Korrigieren</button><button onClick={() => voidTransaction.mutate(row.id)} className="text-rose-400">Stornieren</button></span>}</li>)}</ul>{voidTransaction.isError && <p role="alert" className="text-rose-400">{voidTransaction.error.message}</p>}</section>
    </div>}
  </main>;
}

function Tile({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5"><p className="text-sm text-zinc-400">{label}</p><p className="mt-2 text-xl font-semibold">{value}</p></div>;
}
