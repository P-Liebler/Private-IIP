"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useCapabilities } from "@/components/capabilities";

type Source = { source_slug: string; approved: boolean; enabled: boolean; gate_reason: string | null; terms_url: string | null; operator_checklist: Record<string, string>; operator_notes: Record<string, string> };
type Evidence = { id: string; kind: string; parent_id: string | null; result: Record<string, unknown>; created_at: string };
type Overview = { is_data_operator: boolean; is_ml_operator: boolean; sources: Source[]; records: Evidence[]; forward_scheduling_enabled: boolean };
type Dataset = { id: string; configuration: Record<string, unknown>; content_hash: string };
const box = "rounded border border-zinc-700 bg-zinc-900 p-2";

function CandidateAction({ row, refresh }: { row: Evidence; refresh: () => void }) {
  const [index, setIndex] = useState(0);
  return <div><label>Kandidat auswählen <select aria-label={`Kandidat ${row.id}`} className={box} value={index} onChange={e => setIndex(Number(e.target.value))}>{Array.from({ length: Number(row.result.candidate_count ?? 0) }, (_, i) => <option key={i} value={i}>{i + 1}</option>)}</select></label><JsonAction title={`Kandidat ${index + 1}`} endpoint={`/validation/experiments/${row.id}/candidates/${index}`} refresh={refresh} /></div>;
}

export function ValidationLinks() {
  const { permissions } = useCapabilities();
  return <nav className="flex flex-wrap gap-4 text-emerald-400" aria-label="Analysewerkzeuge"><Link href="/data-operations/readiness">Historische Datenqualität</Link>{permissions.ml_operator && <Link href="/models/validation">Modelle prüfen</Link>}<Link href="/models/forward-validation">Prognosen im Testbetrieb</Link>{permissions.ml_operator && <Link href="/recommendations/validation">Strategien prüfen</Link>}</nav>;
}

export function JsonAction({ title, endpoint, disabled = false, initial = "{}", refresh }: { title: string; endpoint: string; disabled?: boolean; initial?: string; refresh?: () => void }) {
  const [draft, setDraft] = useState(initial); const [result, setResult] = useState<unknown>(); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit() {
    setError(""); setBusy(true);
    try { const body = JSON.parse(draft); setResult(await api(endpoint, { method: "POST", body: JSON.stringify(body) })); refresh?.(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Prüfung fehlgeschlagen"); }
    finally { setBusy(false); }
  }
  return <section className="space-y-3 rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">{title}</h2><label className="block">Prüfauftrag: {title}<textarea aria-label={`Prüfauftrag: ${title}`} className={`${box} mt-2 block min-h-40 w-full font-mono text-xs`} value={draft} onChange={e => setDraft(e.target.value)} /></label><button className={box} disabled={disabled || busy} onClick={() => void submit()}>{busy ? "Prüfung läuft…" : `${title} ausführen`}</button>{error && <p role="alert">{error}</p>}{result !== undefined && <pre className="max-h-[36rem] overflow-auto text-xs">{JSON.stringify(result, null, 2)}</pre>}</section>;
}

function SourceChecklist({ source, disabled, refresh }: { source: Source; disabled: boolean; refresh: () => void }) {
  const [items, setItems] = useState<Record<string, string>>(source.operator_notes); const [message, setMessage] = useState("");
  async function save() {
    try { await api("/validation/source-checklists", { method: "POST", body: JSON.stringify({ source_slug: source.source_slug, items }) }); setMessage("Arbeitsnotizen gespeichert. Quellenrechte und Aktivierung bleiben separat."); refresh(); }
    catch (caught) { setMessage(caught instanceof Error ? caught.message : "Speichern fehlgeschlagen"); }
  }
  return <article className="space-y-2 rounded border border-zinc-800 p-4"><h3>{source.source_slug} · {source.approved ? "APPROVED" : "Prüfung offen"} · {source.enabled ? "Aktiv" : "Deaktiviert"}</h3><p>{source.gate_reason ?? "Registry-Gate bestanden; Dateneignung separat prüfen"}</p>{source.terms_url && <a className="text-emerald-400 underline" href={source.terms_url} target="_blank" rel="noreferrer">Offizielle Bedingungen</a>}<details><summary>Operator-Checkliste · keine Freigabe durch Abhaken</summary><p className="my-2 text-sm">Beleg und konkreten Geltungsbereich eintragen. Zugangsdaten ausschließlich lokal konfigurieren.</p>{Object.keys(source.operator_checklist).map(key => <label key={key} className="my-2 block text-sm">{key} · {items[key]?.trim() ? "Notiz vorhanden" : "OFFEN"}<input disabled={disabled} className={`${box} ml-2`} value={items[key] ?? ""} onChange={e => setItems({ ...items, [key]: e.target.value })} maxLength={2000} /></label>)}<button className={box} disabled={disabled} onClick={() => void save()}>Arbeitsnotizen speichern</button><p>{message}</p></details></article>;
}

export function ValidationWorkbench({ mode }: { mode: "readiness" | "experiments" | "strategies" }) {
  const overview = useQuery({ queryKey: ["validation-overview"], queryFn: () => api<Overview>("/validation/overview") });
  const datasets = useQuery({ queryKey: ["validation-datasets"], queryFn: () => api<Dataset[]>("/datasets") });
  const [selected, setSelected] = useState(""); const [recordId, setRecordId] = useState(""); const [record, setRecord] = useState<unknown>(); const [error, setError] = useState("");
  const dataset = datasets.data?.find(d => d.id === selected);
  const refresh = () => { void overview.refetch(); };
  const audit = dataset ? { universe_id: dataset.configuration.universe_id, benchmark_id: dataset.configuration.benchmark_id, start: dataset.configuration.start, end: dataset.configuration.end, availability_mode: dataset.configuration.availability_mode, base_currency: dataset.configuration.base_currency, horizon: dataset.configuration.target_horizon, dataset_id: dataset.id, source_policy: [{ source_slug: "MANUAL_CSV", use: "manual_upload" }], required_features: ["momentum_20d", "volatility_20"], folds: [] } : null;
  async function inspect(id: string) { setRecordId(id); try { setRecord(await api(`/validation/records/${id}`)); setError(""); } catch (caught) { setError(caught instanceof Error ? caught.message : "Archiv nicht verfügbar"); } }
  const titles = { readiness: "Real Data Readiness", experiments: "Model comparison", strategies: "Strategy evaluation" };
  return <main className="space-y-6 py-10"><h1 className="text-3xl font-semibold">{titles[mode]}</h1><ValidationLinks /><p>Reale Evidenz, technische Funktion und fachliche Freigabe werden getrennt geprüft. Keine automatische Modell- oder Strategiefreigabe.</p>{overview.isError && <p role="alert">{overview.error.message}</p>}
    {mode === "readiness" && <><h2 className="text-xl font-semibold">Quellen und offene Operator-Schritte</h2><p>LIVE_SMOKE_BLOCKED_SOURCE_NOT_APPROVED gilt für ungeprüfte oder deaktivierte Quellen. Rechtmäßig bereitgestellte manuelle Originale bleiben ein eigener Pilotweg.</p><div className="grid gap-3 md:grid-cols-2">{overview.data?.sources.map(source => <SourceChecklist key={source.source_slug} source={source} disabled={!overview.data?.is_data_operator} refresh={refresh} />)}</div><label className="block">Gepinntes Dataset<select aria-label="Gepinntes Dataset" className={`${box} ml-2`} value={selected} onChange={e => setSelected(e.target.value)}><option value="">Dataset auswählen</option>{datasets.data?.map(d => <option key={d.id} value={d.id}>{d.id} · {String(d.configuration.data_context ?? "UNKNOWN")} · {String(d.configuration.target_horizon)} Sitzungen</option>)}</select></label>{audit && <JsonAction key={selected} title="Readiness-Audit" endpoint="/validation/readiness" initial={JSON.stringify(audit, null, 2)} refresh={refresh} />}<details><summary>Kontrollierter Pilot und Originalbelege</summary><p className="my-3">3–5 bestehende Instrumente und separaten Benchmark wählen. Quellen, Zeitraum und bestehende Collector-Verträge explizit angeben. Vorschau erzeugt noch keinen Netzwerkabruf.</p><JsonAction title="Pilotvorschau" endpoint="/validation/pilots" disabled={!overview.data?.is_data_operator} initial={JSON.stringify({ readiness: audit ?? {}, collections: [] }, null, 2)} refresh={refresh} /><JsonAction title="Originalnachweis" endpoint="/validation/raw-evidence" disabled={!overview.data?.is_data_operator} initial={JSON.stringify({ raw_ids: [], classification: "UNVERIFIED", provenance_reference: "", rights_reference: "" }, null, 2)} refresh={refresh} /></details></>}
    {mode === "experiments" && <><p>RETROSPECTIVE_PIT_EXPERIMENT · Train, Validation, Calibration und finales OOS vor der ersten Auswertung registrieren. Bereits verwendete finale Fenster bleiben gesperrt. Ohne reale Dateneignung: BLOCKED_BY_REAL_DATA.</p><JsonAction title="Experiment registrieren" endpoint="/validation/experiments" disabled={!overview.data?.is_ml_operator} initial={JSON.stringify({ name: "", candidates: [], rationale: "", source_policy: [], regime_definitions: {} }, null, 2)} refresh={refresh} /><p>Registrierte Kandidaten verwenden die vorhandene P7-Queue, Baselines, Kalibrierung, Intervalle, Kosten-Backtests und unveränderte Promotion-Gates.</p></>}
    {mode === "strategies" && <><p className="text-amber-300">V3 RECOMMENDATIONS GATED</p><p>RESEARCH_BACKTEST und ARCHIVED_FORWARD_EVALUATION bleiben getrennt. Vergleiche: No change, Benchmark, Equal weight, Momentum, Quality/value und Recommendation strategy. Ohne historische Profile, Prognosen, Risiko und Ausführungsdaten sind Ergebnisse nicht verfügbar.</p><JsonAction title="Strategie prüfen" endpoint="/validation/strategies" disabled={!overview.data?.is_ml_operator} initial={JSON.stringify({ dataset_id: selected, portfolio_id: "", recommendation_ids: [] }, null, 2)} refresh={refresh} /></>}
    <section className="space-y-3"><h2 className="text-xl font-semibold">Unveränderliche Prüfprotokolle</h2>{overview.data?.records.length === 0 && <p>Keine Prüfprotokolle vorhanden. Reale Validierung ist nicht nachgewiesen.</p>}{overview.data?.records.map(row => <article key={row.id} className="rounded border border-zinc-800 p-3"><button className="text-left text-emerald-400" onClick={() => void inspect(row.id)}>{row.kind} · {row.created_at} · {String(row.result.status ?? row.result.readiness_status ?? "Gespeichert")}</button>{row.kind === "PILOT_PREVIEW" && overview.data?.is_data_operator && <div className="mt-2 flex gap-3"><button className={box} onClick={() => void api(`/validation/pilots/${row.id}/start`, { method: "POST" }).then(refresh).catch(e => setError(e.message))}>Pilot starten / fortsetzen</button><button className={box} onClick={() => void api(`/validation/pilots/${row.id}/assess`, { method: "POST" }).then(refresh).catch(e => setError(e.message))}>Pilotabnahme prüfen</button></div>}{row.kind === "EXPERIMENT_PROTOCOL" && overview.data?.is_ml_operator && <div className="mt-2"><button className={box} onClick={() => void api(`/validation/experiments/${row.id}/evaluate`, { method: "POST" }).then(refresh).catch(e => setError(e.message))}>Registrierte Ergebnisse vergleichen</button><p>Kandidaten nach Index über den registrierten Auftrag ausführen.</p><CandidateAction row={row} refresh={refresh} /></div>}</article>)}{error && <p role="alert">{error}</p>}{record !== undefined && <details key={recordId} open><summary>Archiv {recordId}</summary><pre className="max-h-[36rem] overflow-auto text-xs">{JSON.stringify(record, null, 2)}</pre></details>}</section>
  </main>;
}
