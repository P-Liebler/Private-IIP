"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { searchInstruments, type Instrument } from "@/lib/api/market-foundation";
import type { Account, Holding } from "@/lib/api/portfolios";
import { money } from "@/lib/portfolio-format";

const input = "w-full rounded border border-zinc-700 bg-zinc-950 p-2";
type Row = { id: string; quantity: string; currency: string; value: string };
type Result = { status: string; coverage: string; source_reference: string; valuation_status: string;
  calculated_value_base: string | null; reported_value_base: string | null; value_difference_base: string | null;
  positions: { instrument_id: string; name: string; reported_quantity: string; ledger_quantity: string; quantity_difference: string; currency_matches: boolean; market_value_difference: string | null }[];
  cash: { currency: string; reported: string; ledger: string; difference: string }[];
  ledger_changed: boolean; unreviewed_positions: string[] };

export function PortfolioReconciliation({ portfolioId, accounts, holdings, baseCurrency }: { portfolioId: string; accounts: Account[]; holdings: Holding[]; baseCurrency: string }) {
  const [account, setAccount] = useState("");
  const [day, setDay] = useState(new Date().toISOString().slice(0, 10));
  const [reference, setReference] = useState("");
  const [complete, setComplete] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [cash, setCash] = useState<Record<string, string>>({ CHF: "", EUR: "", USD: "" });
  const [nav, setNav] = useState("");
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Record<string, Instrument>>({});
  const instruments = useQuery({ queryKey: ["statement-instruments", search], queryFn: () => searchInstruments(search), enabled: !!search });
  const compare = useMutation({ mutationFn: () => {
    if (rows.some(r => (r.quantity || r.value) && !r.id)) throw new Error("Jede eingegebene Auszugsposition zuerst einem Instrument zuordnen.");
    if (rows.some(r => r.id && !r.quantity)) throw new Error("Stückzahl vom Auszug für jede gewählte Position eingeben.");
    return api<Result>(`/portfolios/${portfolioId}/reconciliation`, { method: "POST", body: JSON.stringify({
      account_id: account, statement_date: day, source_reference: reference, complete_statement: complete,
      positions: rows.filter(r => r.id).map(r => ({ instrument_id: r.id, quantity: r.quantity, currency: r.currency, reported_market_value: r.value || null })),
      cash: Object.entries(cash).filter(([, v]) => v.trim()).map(([currency, amount]) => ({ currency, amount })), reported_value_base: nav || null,
    }) });
  } });
  const choices = [...new Map([...Object.values(selected), ...(instruments.data?.map(h => h.instrument) ?? [])].map(i => [i.id, i])).values()];
  function change(index: number, values: Partial<Row>) { setRows(rows.map((r, n) => n === index ? { ...r, ...values } : r)); compare.reset(); }
  return <section className="space-y-4 rounded-xl border border-zinc-800 p-5">
    <h2 className="text-xl font-semibold">Depotabgleich</h2>
    <p>Werte von Ihrem Auszug manuell übertragen. Der Abgleich ändert keine Buchung. Er ersetzt keinen geprüften Originalbeleg; vergleichen Sie denselben Stichtag und dieselbe FX-Referenz.</p>
    <form className="space-y-4" onSubmit={e => { e.preventDefault(); compare.mutate(); }}>
      <div className="grid gap-3 sm:grid-cols-2"><label>Auszugskonto<select required value={account} onChange={e => { setAccount(e.target.value); setRows([]); compare.reset(); }} className={input}><option value="">Auswählen</option>{accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
        <label>Auszugsdatum<input required type="date" value={day} onChange={e => { setDay(e.target.value); compare.reset(); }} className={input} /></label>
        <label className="sm:col-span-2">Belegreferenz<input required minLength={10} maxLength={200} value={reference} onChange={e => { setReference(e.target.value); compare.reset(); }} placeholder="Depot / Auszug / Stichtag (keine Zugangsdaten)" className={input} /></label></div>
      <button type="button" className="text-emerald-400 underline" onClick={() => { setRows(holdings.filter(h => h.account_id === account).map(h => ({ id: h.instrument_id, quantity: "", currency: h.currency, value: "" }))); compare.reset(); }}>Vorhandene Instrumente vorbereiten – Stückzahlen vom Auszug selbst eingeben</button>
      <label className="block">Auszugsinstrument suchen<input value={query} onChange={e => setQuery(e.target.value)} className={input} /></label><button type="button" onClick={() => setSearch(query.trim())} className="rounded border px-3 py-1">Instrument im Auszug suchen</button>
      {instruments.isError && <p role="alert">{instruments.error.message}</p>}
      {rows.map((row, index) => <fieldset key={index} className="grid gap-3 border border-zinc-700 p-3 sm:grid-cols-2"><legend>Auszugsposition {index + 1}</legend>
        <label>Instrument<select aria-label={`Auszugsinstrument ${index + 1}`} value={row.id} onChange={e => { const instrument = choices.find(i => i.id === e.target.value); if (instrument) setSelected({ ...selected, [instrument.id]: instrument }); change(index, { id: e.target.value, currency: instrument?.currency ?? row.currency }); }} className={input}><option value="">Auswählen</option>{holdings.filter(h => h.account_id === account && !choices.some(i => i.id === h.instrument_id)).map(h => <option key={h.instrument_id} value={h.instrument_id}>{h.name} · {h.currency}</option>)}{choices.map(i => <option key={i.id} value={i.id}>{i.name} · {i.isin ?? i.ticker} · {i.mic ?? i.exchange} · {i.currency}</option>)}</select></label>
        <label>Stückzahl laut Auszug<input aria-label={`Auszugsstückzahl ${index + 1}`} value={row.quantity} onChange={e => change(index, { quantity: e.target.value })} required={!!row.id} className={input} /></label>
        <label>Positionswährung<select value={row.currency} onChange={e => change(index, { currency: e.target.value })} className={input}>{["CHF", "EUR", "USD"].map(c => <option key={c}>{c}</option>)}</select></label>
        <label>Marktwert in Positionswährung (optional)<input value={row.value} onChange={e => change(index, { value: e.target.value })} className={input} /></label><button type="button" onClick={() => { setRows(rows.filter((_, n) => n !== index)); compare.reset(); }} className="text-rose-400">Auszugszeile entfernen</button>
      </fieldset>)}
      <button type="button" onClick={() => setRows([...rows, { id: "", quantity: "", currency: "CHF", value: "" }])} className="rounded border px-3 py-2">Auszugsposition hinzufügen</button>
      <div className="grid gap-3 sm:grid-cols-3">{["CHF", "EUR", "USD"].map(c => <label key={c}>{c}-Cash laut Auszug<input aria-label={`${c}-Cash laut Auszug`} value={cash[c]} onChange={e => { setCash({ ...cash, [c]: e.target.value }); compare.reset(); }} placeholder="Leer = nicht angegeben" className={input} /></label>)}</div>
      <label className="block">Gesamtwert laut Auszug in {baseCurrency} (optional)<input value={nav} onChange={e => { setNav(e.target.value); compare.reset(); }} className={input} /></label>
      <label className="block"><input type="checkbox" checked={complete} onChange={e => { setComplete(e.target.checked); compare.reset(); }} /> Vollständigen Kontoauszug eingegeben: nicht aufgeführte Positionen und Cash-Währungen sind ausdrücklich null.</label>
      <button disabled={!account || compare.isPending} className="rounded bg-emerald-500 px-4 py-2 text-zinc-950">Abgleich berechnen</button>
    </form>
    {compare.isError && <p role="alert">{compare.error.message}</p>}
    {compare.data && <div className="space-y-3" aria-label="Abgleichergebnis"><p role="status">{compare.data.status} · {compare.data.coverage}</p><p>{compare.data.source_reference} · Ledger unverändert: {compare.data.ledger_changed ? "FEHLER" : "ja"}</p>
      <ul>{compare.data.positions.map(p => <li key={p.instrument_id}>{p.name}: Auszug {p.reported_quantity}, Ledger {p.ledger_quantity}, Differenz {p.quantity_difference}. Währung {p.currency_matches ? "passend" : "abweichend"}. Marktwertdifferenz {p.market_value_difference ?? "nicht vergleichbar / nicht angegeben"}.</li>)}</ul>
      <ul>{compare.data.cash.map(c => <li key={c.currency}>{c.currency}: Auszug {c.reported}, Ledger {c.ledger}, Differenz {c.difference}</li>)}</ul>
      <p>App-Kontowert: {money(compare.data.calculated_value_base, baseCurrency)} · Differenz zum Auszug: {money(compare.data.value_difference_base, baseCurrency)} · Bewertung {compare.data.valuation_status}</p>
      {compare.data.unreviewed_positions.length > 0 && <p className="text-amber-400">Weitere App-Positionen sind in dieser Teilprüfung nicht erfasst.</p>}
      <p className="text-sm text-zinc-400">Bei Differenzen: fehlende Transaktionen, Gebühren, Dividenden, falsches Instrument/Börse, Bewertungszeit, FX-Referenz oder Corporate Actions prüfen. Korrekturen anschließend ausdrücklich unter Transaktionen vornehmen.</p>
    </div>}
  </section>;
}
