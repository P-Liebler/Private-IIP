"use client";

import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { listUniverses, listDatasets, type Run } from "@/lib/api/pit";

export default function BacktestsPage() {
  const client = useQueryClient();
  const universes = useQuery({ queryKey: ["universes"], queryFn: listUniverses });
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: listDatasets });
  const runs = useQuery({ queryKey: ["backtests"], queryFn: () => api<{ id: string; status: string }[]>("/backtests") });
  const [universe, setUniverse] = useState(""); const [name, setName] = useState("");
  const [start, setStart] = useState(""); const [end, setEnd] = useState(""); const [benchmark, setBenchmark] = useState("");
  const [mode, setMode] = useState("STRICT_PIT"); const [dataset, setDataset] = useState(""); const [strategy, setStrategy] = useState("EQUAL_WEIGHT");
  const [execution, setExecution] = useState("NEXT_OPEN"); const [commission, setCommission] = useState("1");
  const [spread, setSpread] = useState("5"); const [slippage, setSlippage] = useState("5"); const [capital, setCapital] = useState("10000");
  const [currency, setCurrency] = useState("CHF"); const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const [raw, setRaw] = useState(""); const [preview, setPreview] = useState<{ rows: unknown[]; errors: string[] } | null>(null);
  async function action(work: () => Promise<void>) { setError(""); setBusy(true); try { await work(); } catch (e) { setError(e instanceof Error ? e.message : "Anfrage fehlgeschlagen"); } finally { setBusy(false); } }
  async function build(event: FormEvent) { event.preventDefault(); await action(async () => {
    const value = await api<{ id: string; quality: { valid_observations: number; excluded_observations: number } }>("/datasets/build", { method: "POST", body: JSON.stringify({ universe_id: universe, benchmark_id: benchmark, start, end, availability_mode: mode, base_currency: currency }) });
    setDataset(value.id); setMessage(`Dataset: ${value.quality.valid_observations} gültig, ${value.quality.excluded_observations} ausgeschlossen.`); await client.invalidateQueries({ queryKey: ["datasets"] });
  }); }
  async function execute(event: FormEvent) { event.preventDefault(); await action(async () => {
    setRun(await api<Run>("/backtests", { method: "POST", body: JSON.stringify({ dataset_id: dataset, strategy, execution_policy: execution, initial_capital: capital, commission, spread_bps: spread, slippage_bps: slippage, zero_cost_comparison: commission === "0" && spread === "0" && slippage === "0" }) }));
    await client.invalidateQueries({ queryKey: ["backtests"] });
  }); }
  const input = "block w-full rounded border border-zinc-700 bg-zinc-900 p-2";
  return <main className="space-y-6 py-8">
    <h1 className="text-3xl font-semibold">Backtests</h1>
    <p>Historische Baselines mit geprüften Informationszeitpunkten. Keine Prognose und kein realer Handel.</p>
    {error && <p role="alert" className="text-rose-400">{error}</p>}{message && <p role="status">{message}</p>}
    <section className="space-y-3 rounded border border-zinc-800 p-4"><h2 className="text-xl">Universes & Membership</h2>
      <form onSubmit={e => { e.preventDefault(); void action(async () => { const value = await api<{ id: string }>("/universes", { method: "POST", body: JSON.stringify({ name }) }); setUniverse(value.id); await client.invalidateQueries({ queryKey: ["universes"] }); }); }}>
        <label>Universe Name<input className={input} value={name} onChange={e => setName(e.target.value)} required /></label><button disabled={busy} className="my-2 rounded border p-2">Universe erstellen</button>
      </form>
      <label>Universe<select className={input} value={universe} onChange={e => { setUniverse(e.target.value); setPreview(null); setRaw(""); }}><option value="">Auswählen</option>{universes.data?.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select></label>
      <p className="text-sm text-zinc-400">CSV: instrument_id, valid_from, valid_to, known_at, membership_status. Interne IDs ausdrücklich zuordnen. Historische Behauptungen benötigen einen dokumentierten Operator-Review.</p>
      <label>Membership CSV<input type="file" accept=".csv" disabled={!universe || busy} onChange={e => { const file = e.target.files?.[0]; if (file) void action(async () => { const value = await api<{ raw_id: string }>(`/universes/${universe}/imports/upload`, { method: "POST", body: await file.text(), headers: { "Content-Type": "text/csv" } }); setRaw(value.raw_id); setPreview(await api(`/universes/${universe}/imports/preview`, { method: "POST", body: JSON.stringify({ raw_id: value.raw_id }) })); }); }} /></label>
      {preview && <><p>{preview.rows.length} zugeordnete Zeilen · {preview.errors.length} Fehler</p><pre className="overflow-auto text-xs">{JSON.stringify(preview, null, 2)}</pre><button className="rounded border p-2" disabled={busy || preview.errors.length > 0} onClick={() => void action(async () => { await api(`/universes/${universe}/imports/commit`, { method: "POST", body: JSON.stringify({ raw_id: raw }) }); setMessage("Membership-Versionen gespeichert."); setPreview(null); })}>Membership bestätigen</button></>}
    </section>
    <form onSubmit={build} className="grid gap-3 rounded border border-zinc-800 p-4 sm:grid-cols-2"><h2 className="text-xl sm:col-span-2">Dataset bauen</h2>
      <label>Start<input className={input} type="date" required value={start} onChange={e => setStart(e.target.value)} /></label><label>Ende<input className={input} type="date" required value={end} onChange={e => setEnd(e.target.value)} /></label>
      <label>Benchmark Instrument ID<input className={input} required value={benchmark} onChange={e => setBenchmark(e.target.value)} /></label>
      <label>Basiswährung<select className={input} value={currency} onChange={e => setCurrency(e.target.value)}>{["CHF", "USD", "EUR"].map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Historischer Modus<select className={input} value={mode} onChange={e => setMode(e.target.value)}><option>STRICT_PIT</option><option>RECONSTRUCTED_HISTORICAL</option></select></label>
      <p className="text-amber-400">{mode === "STRICT_PIT" ? "Ungeprüfte Verfügbarkeit und unvollständige historische Mitgliedschaften werden ausgeschlossen." : "RECONSTRUCTED / HISTORICAL_AVAILABILITY_UNVERIFIED · Explorativ; kein strenger historischer Nachweis."}</p>
      <button disabled={busy || !universe} className="rounded border p-2">Dataset bauen</button>
    </form>
    <form onSubmit={execute} className="grid gap-3 rounded border border-zinc-800 p-4 sm:grid-cols-2"><h2 className="text-xl sm:col-span-2">Baseline ausführen</h2>
      <label>Dataset<select className={input} required value={dataset} onChange={e => setDataset(e.target.value)}><option value="">Auswählen</option>{datasets.data?.map(d => <option key={d.id} value={d.id}>{d.id.slice(0, 8)} · {d.configuration.availability_mode} · {d.quality.valid_observations} gültig</option>)}</select></label>
      <label>Strategie<select className={input} value={strategy} onChange={e => setStrategy(e.target.value)}>{["EQUAL_WEIGHT", "BENCHMARK_ONLY", "MOMENTUM", "QUALITY_VALUE"].map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Ausführung<select className={input} value={execution} onChange={e => setExecution(e.target.value)}><option>NEXT_OPEN</option><option>NEXT_CLOSE</option></select></label>
      <label>Startkapital<input className={input} type="number" min="1" value={capital} onChange={e => setCapital(e.target.value)} required /></label>
      <label>Kommission<input className={input} type="number" min="0" step="0.01" value={commission} onChange={e => setCommission(e.target.value)} /></label>
      <label>Spread bps<input className={input} type="number" min="0" value={spread} onChange={e => setSpread(e.target.value)} /></label>
      <label>Slippage bps<input className={input} type="number" min="0" value={slippage} onChange={e => setSlippage(e.target.value)} /></label>
      <button disabled={busy || !dataset} className="rounded border p-2">Backtest starten</button>
    </form>
    {run && <section className="space-y-4 rounded border border-zinc-800 p-4"><h2 className="text-xl">Ergebnis: {run.result.status}</h2>
      <p className="text-amber-400">{run.result.data_context}</p><p className="break-all text-xs">Run {run.id} · Manifest {run.content_hash}</p>
      {run.result.warnings.map(w => <p key={w} role="alert" className="text-amber-400">{w}</p>)}
      <EquityCurve points={run.result.equity} benchmark={run.result.benchmark_equity} />
      <table className="w-full"><thead><tr><th>Kennzahl</th><th>Wert</th></tr></thead><tbody>{Object.entries(run.result.metrics).map(([k, v]) => <tr key={k}><td>{k}</td><td>{v ?? "INSUFFICIENT_DATA"}</td></tr>)}</tbody></table>
      <h3 className="text-lg">Trades / Fills und Provenienz</h3><div className="overflow-auto"><table><thead><tr><th>Instrument</th><th>Seite</th><th>Menge</th><th>Kurs</th><th>Ausführung</th><th>Signal</th><th>Kursversion / Raw</th></tr></thead><tbody>{run.result.fills.map((f, i) => <tr key={i}><td>{f.instrument_id}</td><td>{f.side}</td><td>{f.quantity}</td><td>{f.execution_price}</td><td>{f.execution_price_timestamp}</td><td>{f.signal_generated_at}</td><td>{f.price_version_id} / {f.raw_ingestion_id}</td></tr>)}</tbody></table></div>
      <p>{run.result.orders.filter(o => o.status === "NO_FILL").length} nicht ausgeführte Orders</p>
    </section>}
    <section><h2>Gespeicherte Runs</h2>{runs.data?.map(r => <button className="m-1 rounded border p-2" key={r.id} onClick={() => void action(async () => setRun(await api<Run>(`/backtests/${r.id}`)))}>{r.id.slice(0, 8)} · {r.status}</button>)}</section>
  </main>;
}

function EquityCurve({ points, benchmark }: { points: Run["result"]["equity"]; benchmark: string[] | null }) {
  if (!points.length || points.some(p => p.value === null)) return <p>Equity curve: INSUFFICIENT_DATA</p>;
  const values = points.map(p => Number(p.value)); const other = benchmark?.map(Number) ?? [];
  const min = Math.min(...values, ...other); const max = Math.max(...values, ...other); const scale = max - min || 1;
  const path = (data: number[]) => data.map((v, i) => `${10 + i / Math.max(1, data.length - 1) * 580},${180 - (v - min) / scale * 160}`).join(" ");
  return <figure><figcaption>Equity curve · Portfolio (grün), Benchmark (grau)</figcaption><svg role="img" aria-label="Equity curve" viewBox="0 0 600 200" className="w-full"><polyline points={path(values)} fill="none" stroke="#34d399" strokeWidth="2" />{other.length > 0 && <polyline points={path(other)} fill="none" stroke="#a1a1aa" strokeWidth="2" />}</svg><p>{points[0].date} – {points.at(-1)?.date}</p></figure>;
}
