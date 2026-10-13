"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { getSources } from "@/lib/api/market-foundation";
import { getResearch, getWatchlists, getNews, type Metric, type Fact } from "@/lib/api/research";

export function MetricTable({ values }: { values: Record<string, Metric> }) {
  return <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Kennzahl</th><th>Wert</th><th>Verfügbarkeit / Eingaben</th></tr></thead><tbody>{Object.entries(values).map(([name, item]) => <tr key={name} className="border-t border-zinc-800"><td className="py-3">{name}</td><td>{item.value ?? "DATA_UNAVAILABLE"}</td><td><p>{item.reason ?? item.status}</p><details className="text-xs text-zinc-400"><summary>Herkunft</summary><p>Regel: {item.rule_version} · Periode: {item.period_end ?? "—"} · Kurs: {item.price_date ?? "—"}</p><p>Bekannt: {item.known_at ?? "—"} · Abgerufen: {item.retrieved_at ?? "—"}</p><p className="break-all">Faktversionen: {item.inputs.join(", ") || "Keine"} · Kursversion: {item.price_version ?? "—"}</p></details></td></tr>)}</tbody></table></div>;
}

function FinancialChart({ facts, metric }: { facts: Fact[]; metric: string }) {
  const points = facts.filter(f => f.metric === metric && f.period_type === "ANNUAL").sort((a, b) => a.period_end.localeCompare(b.period_end));
  if (!points.length) return <p>{metric}: DATA_UNAVAILABLE</p>;
  const max = Math.max(...points.map(f => Math.abs(Number(f.value))), 1);
  return <figure className="rounded border border-zinc-800 p-4"><figcaption>{metric} · gemeldete Jahresperioden</figcaption>{points.map(f => <div key={f.id} className="my-2 grid grid-cols-[7rem_1fr] gap-2 text-sm"><span>{f.period_end}</span><div><div style={{ width: `${Math.abs(Number(f.value))/max*100}%` }} className={`h-3 ${Number(f.value) < 0 ? "bg-rose-500" : "bg-emerald-500"}`} /><span>{f.value} {f.currency}</span></div></div>)}</figure>;
}

export function ResearchDetail({ instrumentId }: { instrumentId: string }) {
  const client = useQueryClient();
  const [tab, setTab] = useState("Financials");
  const [period, setPeriod] = useState("ANNUAL");
  const [asOf, setAsOf] = useState("");
  const [watchId, setWatchId] = useState("");
  const [message, setMessage] = useState("");
  const research = useQuery({ queryKey: ["research", instrumentId, asOf], queryFn: () => getResearch(instrumentId, asOf ? new Date(asOf).toISOString() : "") });
  const sources = useQuery({ queryKey: ["data-sources"], queryFn: getSources });
  const lists = useQuery({ queryKey: ["watchlists"], queryFn: getWatchlists });
  const news = useQuery({ queryKey: ["instrument-news", instrumentId], queryFn: () => getNews(`instrument_id=${instrumentId}`) });
  async function addToList() {
    try { await api(`/watchlists/${watchId}/items`, { method: "PUT", body: JSON.stringify({ instrument_id: instrumentId, tags: [] }) }); setMessage("Zur Watchlist hinzugefügt."); await client.invalidateQueries({ queryKey: ["watchlist-items"] }); } catch (error) { setMessage(error instanceof Error ? error.message : "Fehler"); }
  }
  const data = research.data;
  return <section className="space-y-5 rounded-xl border border-zinc-800 p-6"><h2 className="text-xl font-semibold">Research</h2><div className="flex flex-wrap gap-4"><label>Wissenszeitpunkt (lokal)<input aria-label="Research Wissenszeitpunkt" type="datetime-local" className="ml-2 rounded bg-zinc-900 p-2" value={asOf} onChange={e => setAsOf(e.target.value)} /></label><select aria-label="Watchlist wählen" value={watchId} onChange={e => setWatchId(e.target.value)} className="rounded bg-zinc-900 p-2"><option value="">Watchlist wählen</option>{lists.data?.map(list => <option key={list.id} value={list.id}>{list.name}</option>)}</select><button className="rounded border border-zinc-600 px-3" disabled={!watchId} onClick={addToList}>Zur Watchlist hinzufügen</button></div>{message && <p role="status">{message}</p>}
    <nav aria-label="Research Tabs" className="flex flex-wrap gap-2">{["Financials", "Valuation", "Growth", "Profitability", "Momentum", "News", "Scores"].map(name => <button key={name} onClick={() => setTab(name)} className={`rounded px-3 py-2 ${tab === name ? "bg-emerald-900" : "bg-zinc-900"}`}>{name}</button>)}</nav>
    {research.isError && <p role="alert">{research.error.message}</p>}{research.isPending && <p>Lade Research…</p>}{data && <><p className="text-amber-300">{data.status} · {data.as_of}</p>{!data.facts.length && <p>Keine validierten Fundamentals. Neue Quellen bleiben bis zur Freigabe deaktiviert.</p>}
    {tab === "Financials" && <><select aria-label="Finanzperiode" className="rounded bg-zinc-900 p-2" value={period} onChange={e => setPeriod(e.target.value)}><option value="ANNUAL">Annual</option><option value="QUARTER">Quarterly</option><option value="TTM">TTM</option></select>{period === "TTM" ? <MetricTable values={data.ttm} /> : <><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Kennzahl</th><th>Periode</th><th>Wert</th><th>Herkunft</th></tr></thead><tbody>{data.facts.filter(f => f.period_type === period || f.period_type === "INSTANT").sort((a,b) => b.period_end.localeCompare(a.period_end)).map(f => <tr key={f.id} className="border-t border-zinc-800"><td className="py-3">{f.metric}</td><td>{f.period_start ?? "Instant"} – {f.period_end}</td><td>{f.value} {f.currency ?? f.unit}</td><td><details><summary>{f.replaces_version_id ? "restated" : "reported"} · {f.validation_status}</summary><p>Quelle {sources.data?.find(s => s.id === f.source_id)?.slug ?? f.source_id}</p><p>Bekannt: {f.known_at} · Erfasst: {f.observed_at}</p><p>{f.evidence.release ?? "Nur eigener Empfang belegt"}</p><p className="break-all">Version {f.id} · Raw {f.raw_ingestion_id}</p></details></td></tr>)}</tbody></table></div><div className="grid gap-4 sm:grid-cols-2">{["revenue", "net_income", "eps_diluted", "free_cash_flow"].map(metric => <FinancialChart key={metric} facts={data.facts} metric={metric} />)}</div></>}</>}
    {tab === "Valuation" && <MetricTable values={data.valuation} />}
    {tab === "Growth" && <MetricTable values={Object.fromEntries(Object.entries(data.metrics).filter(([name]) => name.includes("growth")))} />}
    {tab === "Profitability" && <MetricTable values={Object.fromEntries(Object.entries(data.metrics).filter(([name]) => !name.includes("growth")))} />}
    {tab === "Momentum" && <MetricTable values={{ momentum: data.momentum }} />}
    {tab === "Scores" && <div className="space-y-4">{Object.entries(data.scores).map(([name, score]) => <article key={name} className="rounded border border-zinc-800 p-4"><h3>{name}: {score.score ?? "INSUFFICIENT_DATA"}</h3><p>Coverage {score.coverage} · {score.rule_version}</p><p className="text-sm text-zinc-400">{score.method}</p><p>Fehlende Pflichtdaten: {score.missing_inputs.join(", ") || "Keine"}</p><ul>{score.drivers.map(driver => <li key={driver.metric}>{driver.metric}: {driver.input} · Gewicht {driver.weight} · Beitrag {driver.contribution}</li>)}</ul></article>)}</div>}
    {tab === "News" && <div>{news.isError && <p role="alert">{news.error.message}</p>}{!news.data?.length && <p>Keine zugeordneten Nachrichten vorhanden.</p>}{news.data?.map(n => <article key={n.id}><a href={n.source_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 underline">{n.title}</a><p>Veröffentlicht {n.published_at ?? "unbekannt"} · Entdeckt {n.discovered_at} · Sentiment {n.sentiment ? "vorhanden" : "unavailable"}</p></article>)}</div>}
    </>}
  </section>;
}
