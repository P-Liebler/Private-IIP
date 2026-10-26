"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { bookingRequestKey, clearBookingRequestKey } from "@/lib/booking-request";
import { api } from "@/lib/api";
import { searchInstruments } from "@/lib/api/market-foundation";
import { PortfolioOverviewDetails } from "@/components/portfolio-overview-details";
import { TransactionCsvImport } from "@/components/transaction-csv-import";
import { getAllocation, getPerformance, getValuation, listAccounts, listPortfolios,
  listTransactions, getSummary, listBenchmarks, type Account, type Transaction } from "@/lib/api/portfolios";
import { money, ratio } from "@/lib/portfolio-format";
import { AllocationChart, ValueChart } from "@/components/portfolio-charts";
import { PortfolioRiskPanel } from "@/components/portfolio-risk-panel";
import { CorporateActionReview } from "@/components/corporate-action-review";
import { ConfirmationDialog } from "@/components/ui/primitives";
import { HoldingsTable } from "@/components/holdings-table";
import { PortfolioDataActions } from "@/components/portfolio-data-actions";
import { PortfolioOnboarding } from "@/components/portfolio-onboarding";
import { PortfolioReconciliation } from "@/components/portfolio-reconciliation";

const input = "w-full rounded border border-zinc-700 bg-zinc-950 p-2";
const kinds = ["DEPOSIT", "WITHDRAWAL", "BUY", "SELL", "DIVIDEND", "INTEREST", "FEE", "TAX", "TRANSFER_IN", "TRANSFER_OUT", "SPLIT", "CASH_ADJUSTMENT", "OPENING_POSITION"];

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const cache = useQueryClient();
  const requestedTab = useSearchParams().get("tab");
  const allowedTabs = ["Übersicht", "Positionen", "Performance", "Allokation", "Risiko", "Korrelationen", "Szenarien", "What-if", "Dividenden", "Transaktionen", "Depotabgleich", "Datenqualität"];
  const tab = requestedTab && allowedTabs.includes(requestedTab) ? requestedTab : "Übersicht";
  const setTab = (next: string) => { const url = new URL(window.location.href); url.searchParams.set("tab", next); router.replace(url.pathname + url.search, { scroll: false }); };
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
  const [notes, setNotes] = useState("");
  const [bookingReview, setBookingReview] = useState(false);
  const bookingTrigger = useRef<HTMLButtonElement>(null);
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
  const allocation = useQuery({ queryKey: ["allocation", id], queryFn: () => getAllocation(id), enabled: tab === "Allokation" || tab === "Übersicht" });
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
    method: "POST", headers: { "Idempotency-Key": bookingRequestKey("account") }, body: JSON.stringify({ name: accountName, account_type: accountType, default_currency: currency }) }),
    onSuccess: row => { clearBookingRequestKey("account"); setAccountName(""); setAccountId(row.id); cache.invalidateQueries({ queryKey: ["accounts", id] }); } });
  const saveTransaction = useMutation({ mutationFn: () => {
    const security = ["BUY", "SELL", "SPLIT", "DIVIDEND", "OPENING_POSITION"].includes(kind);
    const shares = ["BUY", "SELL", "SPLIT", "OPENING_POSITION"].includes(kind);
    const trading = ["BUY", "SELL"].includes(kind);
    const chargeable = ["BUY", "SELL", "DIVIDEND", "INTEREST"].includes(kind);
    const body = { account_id: accountId, type: kind, trade_date: day, currency,
      instrument_id: security ? instrumentId || null : null,
      quantity: shares ? quantity || null : null,
      price: trading ? price || null : null,
      amount: trading || kind === "SPLIT" ? null : amount || null,
      fee: chargeable ? fee || "0" : "0", tax: chargeable ? tax || "0" : "0", notes: notes || null };
    return api<Transaction>(editing ? `/transactions/${editing}` : `/portfolios/${id}/transactions`,
      { method: editing ? "PATCH" : "POST", headers: editing ? undefined : { "Idempotency-Key": bookingRequestKey("booking") }, body: JSON.stringify(body) });
  }, onSuccess: () => { if (!editing) clearBookingRequestKey("booking"); setEditing(null); setAmount(""); setQuantity(""); setPrice(""); setFee("0"); setTax("0"); setNotes(""); refresh(); } });
  const voidTransaction = useMutation({ mutationFn: (txId: string) => api<Transaction>(`/transactions/${txId}`, { method: "DELETE" }), onSuccess: refresh });
  function selectTransaction(row: Transaction) {
    setNotes(row.notes ?? ""); setEditing(row.id); setAccountId(row.account_id); setKind(row.type); setDay(row.trade_date);
    setCurrency(row.currency); setInstrumentId(row.instrument_id ?? ""); setQuantity(row.quantity ?? "");
    setPrice(row.price ?? ""); setAmount(row.amount ?? ""); setFee(row.fee); setTax(row.tax); setTab("Transaktionen");
  }
  const valuationData = valuation.data;
  function navigate(next: string, anchor?: string) {
    setTab(next);
    if (anchor) requestAnimationFrame(() => document.getElementById(anchor)?.scrollIntoView({ behavior: "smooth" }));
  }
  return <main className="space-y-6 py-10">
    <header><h1 className="text-3xl font-semibold">{portfolio?.name ?? "Portfolio"}</h1><p className="mt-2 text-zinc-400">Basiswährung: {portfolio?.base_currency ?? "…"}</p></header>
    <ConfirmationDialog title={editing ? "Buchungskorrektur prüfen" : "Buchung prüfen"} open={bookingReview} onOpenChange={setBookingReview} returnFocus={bookingTrigger} busy={saveTransaction.isPending} onConfirm={() => saveTransaction.mutateAsync()} description={<><p>{kind} am {day} auf {accounts.data?.find(a => a.id === accountId)?.name ?? "Konto prüfen"}.</p><dl className="mt-3 grid grid-cols-2 gap-2"><dt>Währung</dt><dd>{currency}</dd><dt>Betrag</dt><dd>{amount || "Wird aus Stückzahl und Preis bestimmt, falls fachlich vorgesehen"}</dd><dt>Stückzahl / Preis</dt><dd>{quantity || "Nicht angegeben"} / {price || "Nicht angegeben"}</dd><dt>Gebühr / Steuer</dt><dd>{fee} / {tax}</dd></dl><p className="mt-3">Bitte Instrument, Datum, Konto und alle Werte prüfen. Korrekturen bleiben im Audit sichtbar. Es wird kein Brokerauftrag ausgelöst.</p></>} />
    <PortfolioOnboarding accounts={accounts.data ?? []} transactions={transactions.data ?? []} valuation={valuationData} navigate={navigate} />
    {tab === "Depotabgleich" && <PortfolioReconciliation portfolioId={id} accounts={accounts.data ?? []} holdings={valuationData?.holdings ?? []} baseCurrency={portfolio?.base_currency ?? "CHF"} />}
    <details className="rounded border border-zinc-800 p-4"><summary>Portfolio verwalten</summary>
      <form onSubmit={event => { event.preventDefault(); updatePortfolio.mutate({ name: newName }); }} className="mt-3 flex gap-3"><input aria-label="Neuer Portfolio-Name" required value={newName} onChange={event => setNewName(event.target.value)} className={input} /><button className="text-emerald-400">Umbenennen</button></form>
      <button onClick={() => archivePortfolio.mutate()} className="mt-3 text-rose-400">Portfolio archivieren</button>
      <label className="mt-4 block">Benchmark<select value={portfolio?.benchmark_id ?? ""} onChange={event => updatePortfolio.mutate({ benchmark_id: event.target.value || null })} className={input}><option value="">NONE</option>{benchmarks.data?.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <p className="mt-2 text-sm text-zinc-400">Ein im Transaktionsformular gewähltes Instrument kann als Benchmark registriert werden.</p><button disabled={!instrumentId} onClick={() => createBenchmark.mutate()} className="text-emerald-400">Gewähltes Instrument als Benchmark registrieren</button>
      {[updatePortfolio, archivePortfolio, createBenchmark].map((mutation, index) => mutation.isError && <p key={index} role="alert">{mutation.error.message}</p>)}
    </details>
    <nav className="flex flex-wrap gap-2" aria-label="Portfolio-Bereiche">{["Übersicht", "Positionen", "Performance", "Allokation", "Risiko", "Korrelationen", "Szenarien", "What-if", "Dividenden", "Transaktionen", "Depotabgleich", "Datenqualität"].map(item => <button key={item} onClick={() => setTab(item)} className={`rounded px-3 py-2 ${tab === item ? "bg-emerald-500 text-zinc-950" : "border border-zinc-700"}`}>{item}</button>)}</nav>
    {["Risiko", "Korrelationen", "Szenarien", "What-if"].includes(tab) && <PortfolioRiskPanel portfolioId={id} tab={tab} />}
    {valuation.isPending && <p>Bewertung wird geladen…</p>}
    {valuation.isError && <p role="alert" className="text-rose-400">{valuation.error.message}</p>}
    {valuationData && <>
      {tab === "Übersicht" && <section className="space-y-3"><p className="text-sm text-zinc-400">Renditen: PROVISIONAL · Corporate-Action-Abdeckung ungeprüft. Bewertungsdatum: {valuationData.on_date} · Analyse: {valuationData.analytics_status}</p><div className="grid gap-4 sm:grid-cols-3"><Tile label="Tagesertrag (ohne externe Flows)" value={money(summary.data?.daily_change_base, valuationData.base_currency)} /><Tile label="Gesamtertrag" value={money(summary.data?.total_return_base, valuationData.base_currency)} /><Tile label="YTD-Ertrag" value={money(summary.data?.ytd_return_base, valuationData.base_currency)} /><Tile label="Investierter Marktwert" value={money(valuationData.securities_value_base, valuationData.base_currency)} /><Tile label="Gebühren" value={money(valuationData.fees_base_at_event_fx, valuationData.base_currency)} /><Tile label="Steuern" value={money(valuationData.taxes_base_at_event_fx, valuationData.base_currency)} /></div>{summary.isError && <p role="alert">{summary.error.message}</p>}<p className="text-sm text-zinc-400">Kursalter: {valuationData.holdings.map(item => `${item.name}: ${item.price_age_days ?? "DATA_UNAVAILABLE"} Tage`).join(" · ") || "Keine offenen Positionen"}</p></section>}
      {summary.data?.historical_return_limit && <p role="status" className="text-amber-400">Startbestand vorhanden: Historische Rendite ab einem unbewerteten Eröffnungsbestand ist nicht verfügbar. Ein unbekannter Einstand bleibt unbekannt.</p>}
      {valuationData.status !== "COMPLETE" && <p role="status" className="rounded border border-amber-700 bg-amber-950 p-4">Portfolio PARTIAL: Der Gesamtwert ist wegen fehlender oder alter Daten nicht verfügbar. Bekannte Teilwerte bleiben sichtbar.</p>}
      {tab === "Übersicht" && <div className="grid gap-4 sm:grid-cols-3"><Tile label="Gesamtwert" value={money(valuationData.total_value_base, valuationData.base_currency)} /><Tile label="Bekannter Teilwert" value={money(valuationData.known_value_base, valuationData.base_currency)} /><Tile label="Cash" value={money(valuationData.cash_value_base, valuationData.base_currency)} /><Tile label="Realisiert (FX am Buchungstag)" value={money(valuationData.realized_pnl_base_at_trade_fx, valuationData.base_currency)} /><Tile label="Unrealisiert (heutiger FX)" value={money(valuationData.unrealized_pnl_base_at_valuation_fx, valuationData.base_currency)} /><Tile label="Brutto-Erträge (FX am Buchungstag)" value={money(valuationData.income_base_at_event_fx, valuationData.base_currency)} />
        <section className="sm:col-span-3 rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">Cash nach Währung</h2>{valuationData.cash.length ? <ul className="mt-3 space-y-1">{valuationData.cash.map((cash, index) => <li key={index}>{money(cash.amount, cash.currency)} → {money(cash.base_amount, valuationData.base_currency)} · FX {cash.fx.rate_date ?? "DATA_UNAVAILABLE"}, Alter {cash.fx.age_days ?? "DATA_UNAVAILABLE"} Tage, {cash.fx.derived ?? "DATA_UNAVAILABLE"}</li>)}</ul> : <p className="mt-2 text-zinc-400">Noch keine Cash-Buchungen.</p>}</section></div>}
      {tab === "Übersicht" && <PortfolioOverviewDetails valuation={valuationData} transactions={transactions.data ?? []} allocation={allocation.data} />}
      {(tab === "Datenqualität" || (tab === "Übersicht" && valuationData.issues.length > 0)) && <PortfolioDataActions valuation={valuationData} transactions={() => navigate("Transaktionen", "transaction-entry")} />}
      {tab === "Positionen" && <section className="ui-panel"><HoldingsTable valuation={valuationData} /></section>}
      {tab === "Datenqualität" && <section className="rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">Bewertungsstatus: {valuationData.status}</h2>{valuationData.issues.length ? <ul className="mt-3 list-disc pl-5">{valuationData.issues.map((issue, index) => <li key={index}>{issue.code}{issue.instrument_id && ` · Instrument ${issue.instrument_id}`}{issue.currency && ` · ${issue.currency}`}{issue.account_id && issue.action_version_ids?.map(actionId => <CorporateActionReview key={actionId} portfolioId={id} accountId={issue.account_id!} versionId={actionId} onApplied={refresh} />)}</li>)}</ul> : <p className="mt-2">Keine offenen Bewertungsprobleme.</p>}</section>}
      {tab === "Dividenden" && <section className="space-y-3"><h2 className="font-semibold">Dividenden und Zinsen</h2>{transactions.data?.filter(row => row.status === "ACTIVE" && ["DIVIDEND", "INTEREST"].includes(row.type)).map(row => <article key={row.id} className="rounded border border-zinc-800 p-4"><p>{row.trade_date} · {row.type} · Instrument {row.instrument_name ?? (row.instrument_id ? "Instrument zuordnen" : "kein Instrument")}</p><p>Brutto: {money(row.amount, row.currency)} · Gebühr: {money(row.fee, row.currency)} · Steuer: {money(row.tax, row.currency)}</p><p className="text-sm text-zinc-400">Quelle: {row.source} · Basis brutto: {money(row.amount_base, valuationData.base_currency)} · Basis netto: {money(row.net_amount_base, valuationData.base_currency)}</p></article>)}</section>}
      {tab === "Allokation" && <section className="space-y-4">{allocation.isPending && <p>Lade Allokation…</p>}{allocation.isError && <p role="alert">{allocation.error.message}</p>}{allocation.data?.status !== "AVAILABLE" && <p>Allokation DATA_UNAVAILABLE, solange der Portfoliowert unvollständig oder null ist.</p>}{allocation.data?.status === "AVAILABLE" && <>
        <AllocationChart title="Instrumente" currency={valuationData.base_currency} items={(allocation.data.by_instrument ?? []).map(item => ({ label: valuationData.holdings.find(holding => holding.instrument_id === item.instrument_id)?.name ?? item.instrument_id, weight: item.weight, value: item.value }))} />
        <AllocationChart title="Währung" currency={valuationData.base_currency} items={(allocation.data.by_currency ?? []).map(item => ({ label: item.currency, weight: item.weight, value: item.value }))} />
        <AllocationChart title="Anlageklasse" currency={valuationData.base_currency} items={(allocation.data.by_asset_type ?? []).map(item => ({ label: item.asset_type, weight: item.weight, value: item.value }))} />
      </>}</section>}
      {tab === "Performance" && <section className="space-y-4 rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">Historische Performance</h2><form onSubmit={event => { event.preventDefault(); setHistoryRequested(true); performance.refetch(); }} className="flex flex-wrap gap-3"><input aria-label="Von" type="date" value={historyStart} onChange={event => { setHistoryStart(event.target.value); setHistoryRequested(false); }} className={input} /><input aria-label="Bis" type="date" value={historyEnd} onChange={event => { setHistoryEnd(event.target.value); setHistoryRequested(false); }} className={input} /><button className="rounded bg-emerald-500 px-4 text-zinc-950">Berechnen</button></form>{performance.isError && <p role="alert">{performance.error.message}</p>}{performance.data && <><p>Status: {performance.data.status} {performance.data.reason}</p><div className="grid gap-3 sm:grid-cols-4"><Tile label="Absoluter Ertrag" value={money(performance.data.absolute_return_base, valuationData.base_currency)} /><Tile label="TWR" value={ratio(performance.data.twr)} /><Tile label="XIRR" value={ratio(performance.data.xirr)} /><Tile label="CAGR" value={ratio(performance.data.cagr)} /></div><p className="text-sm text-zinc-400">FX-Beitrag: {money(performance.data.fx_contribution_base, valuationData.base_currency)}</p><p className="text-sm text-amber-400">Renditen: {performance.data.return_status ?? "DATA_UNAVAILABLE"}</p><ValueChart series={performance.data.series} currency={valuationData.base_currency} /><p>Benchmark (brutto, ohne Wiederanlage) {performance.data.benchmark?.name ?? "NONE"}: {ratio(performance.data.benchmark?.return_base)} · {performance.data.benchmark?.status ?? "DATA_UNAVAILABLE"} {performance.data.benchmark?.reason}</p><ul className="max-h-72 overflow-auto text-sm">{performance.data.series.map(point => <li key={point.date}>{point.date}: {money(point.value_base, valuationData.base_currency)} · {point.status}</li>)}</ul></>}</section>}
    </>}
    {tab === "Transaktionen" && <div className="space-y-6">
      <section id="account-setup" className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Account anlegen</h2><form onSubmit={(event: FormEvent) => { event.preventDefault(); createAccount.mutate(); }} className="mt-3 flex flex-wrap gap-3"><input aria-label="Account-Name" required value={accountName} onChange={event => setAccountName(event.target.value)} className={input} /><select aria-label="Account-Typ" value={accountType} onChange={event => setAccountType(event.target.value)} className={input}><option value="BROKER">Broker</option><option value="CASH">Cash</option><option value="MANUAL">Manuell</option></select><button disabled={createAccount.isPending} className="rounded bg-emerald-500 px-4 text-zinc-950">Account anlegen</button></form>{createAccount.isError && <p role="alert" className="text-rose-400">{createAccount.error.message}</p>}</section>
      <section id="transaction-entry" className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">{editing ? "Transaktion korrigieren" : "Transaktion erfassen"}</h2><form onSubmit={event => { event.preventDefault(); setBookingReview(true); }} className="mt-4 grid gap-3 sm:grid-cols-2">
        <label>Account<select required value={accountId} onChange={event => setAccountId(event.target.value)} className={input}><option value="">Auswählen</option>{accounts.data?.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Typ<select value={kind} onChange={event => setKind(event.target.value)} className={input}>{kinds.map(item => <option key={item}>{item}</option>)}</select></label>
        <label>{kind === "OPENING_POSITION" ? "Bestandsstichtag" : "Handelsdatum"}<input type="date" required value={day} onChange={event => setDay(event.target.value)} className={input} /></label>
        <label>Währung<select value={currency} onChange={event => setCurrency(event.target.value)} className={input}><option>CHF</option><option>EUR</option><option>USD</option></select></label>
        {["BUY", "SELL", "SPLIT", "DIVIDEND", "OPENING_POSITION"].includes(kind) && <div className="sm:col-span-2"><label>Instrument suchen<input value={instrumentQuery} onChange={event => setInstrumentQuery(event.target.value)} className={input} /></label><button type="button" onClick={() => setInstrumentSearch(instrumentQuery)} className="mt-2 rounded border border-zinc-700 px-3 py-1">Suchen</button><ul>{instruments.data?.map(hit => <li key={hit.instrument.id}><button type="button" className="text-emerald-400" onClick={() => { setInstrumentId(hit.instrument.id); setCurrency(hit.instrument.currency); }}>{hit.instrument.name} · {hit.instrument.ticker}</button></li>)}</ul><p className="text-xs text-zinc-400">Gewählt: {instruments.data?.find(hit => hit.instrument.id === instrumentId)?.instrument.name ?? valuationData?.holdings.find(h => h.instrument_id === instrumentId)?.name ?? (instrumentId ? "Gespeichertes Instrument" : "keines")}</p></div>}
        {["BUY", "SELL", "SPLIT", "OPENING_POSITION"].includes(kind) && <label>{kind === "SPLIT" ? "Split-Verhältnis" : "Stückzahl"}<input required value={quantity} onChange={event => setQuantity(event.target.value)} className={input} /></label>}
        {["BUY", "SELL"].includes(kind) && <label>Preis je Stück<input required value={price} onChange={event => setPrice(event.target.value)} className={input} /></label>}
        {!["BUY", "SELL", "SPLIT"].includes(kind) && <label>{kind === "OPENING_POSITION" ? "Gesamter Einstandswert (optional)" : "Betrag"}<input required={kind !== "OPENING_POSITION"} value={amount} onChange={event => setAmount(event.target.value)} className={input} /></label>}
        {kind === "OPENING_POSITION" && <><p className="sm:col-span-2 text-sm text-amber-400">Eröffnungsposition laut Beleg; kein historischer Kauf und kein Cashflow. Unbekannten Einstand leer lassen. Historische Renditen über diesen Startpunkt sind nicht verfügbar.</p><label className="sm:col-span-2">Herkunft des Startbestands<input required minLength={10} maxLength={1000} value={notes} onChange={event => setNotes(event.target.value)} placeholder="Depot-Auszug, Stichtag und Herkunft" className={input} /></label></>}
        {["BUY", "SELL", "DIVIDEND", "INTEREST"].includes(kind) && <><label>Gebühr<input value={fee} onChange={event => setFee(event.target.value)} className={input} /></label><label>Steuer / Quellensteuer<input value={tax} onChange={event => setTax(event.target.value)} className={input} /></label></>}
        <button ref={bookingTrigger} disabled={!accountId || saveTransaction.isPending} className="rounded bg-emerald-500 px-4 py-2 font-semibold text-zinc-950">{editing ? "Korrektur speichern" : "Buchen"}</button>{editing && <button type="button" onClick={() => setEditing(null)} className="rounded border border-zinc-700">Abbrechen</button>}
      </form>{saveTransaction.isError && <p role="alert" className="mt-3 text-rose-400">{saveTransaction.error.message}</p>}</section>
      <TransactionCsvImport portfolioId={id} accounts={accounts.data ?? []} onImported={refresh} />
      <section className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Buchungen</h2>{transactions.isError && <p role="alert">{transactions.error.message}</p>}<ul className="mt-3 space-y-2">{transactions.data?.map(row => <li key={row.id} className="rounded border border-zinc-700 p-3"><span className={row.status === "VOIDED" ? "text-zinc-500 line-through" : ""}>{row.trade_date} · {row.type} · Account {accounts.data?.find(item => item.id === row.account_id)?.name ?? row.account_id} · Instrument {row.instrument_name ?? (row.instrument_id ? "Instrument zuordnen" : "kein Instrument")} · Menge {row.quantity ?? "—"} · Preis {money(row.price, row.currency)} · Betrag {money(row.amount, row.currency)} · Gebühr {money(row.fee, row.currency)} · Steuer {money(row.tax, row.currency)} · {row.status}</span>{row.status === "ACTIVE" && !row.action_locked && !row.system_generated && <span className="ml-3 inline-flex gap-3"><button onClick={() => selectTransaction(row)} className="text-emerald-400">Korrigieren</button><ConfirmationDialog title="Buchung stornieren?" description="Das Original bleibt im Audit erhalten und wird aus aktiven Beständen herausgerechnet. Bitte die betroffene Buchung ausdrücklich prüfen." trigger={<button disabled={voidTransaction.isPending} className="text-rose-400">Stornieren</button>} onConfirm={() => voidTransaction.mutateAsync(row.id)} /></span>}</li>)}</ul>{voidTransaction.isError && <p role="alert" className="text-rose-400">{voidTransaction.error.message}</p>}</section>
    </div>}
  </main>;
}

function Tile({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5"><p className="text-sm text-zinc-400">{label}</p><p className="mt-2 text-xl font-semibold">{value}</p></div>;
}
