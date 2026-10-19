"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ValidationLinks } from "@/components/validation-workbench";

type Profile = { id: string | null; status: string; preferences: Record<string, unknown>; units: Record<string, string>; classification: Record<string, string[]> };
type Portfolio = { id: string; name: string };
type Saved = { id: string; instrument_id: string; category: string; generated_at: string; eligibility: { permitted: boolean; missing_inputs: string[]; violations: string[] }; input_manifest?: Record<string, unknown>; result?: { explanation: Record<string, unknown>; scoring: { score: string | null } } };
type Risk = { id: string; result: { current_valuation: { holdings: { instrument_id: string; name: string }[] } } };
const field = "rounded border border-zinc-700 bg-zinc-950 p-2";

export default function RecommendationsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [draft, setDraft] = useState("");
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfolio, setPortfolio] = useState("");
  const [instrument, setInstrument] = useState("");
  const [risk, setRisk] = useState<Risk | null>(null);
  const [mode, setMode] = useState("FIXED");
  const [side, setSide] = useState("BUY");
  const [amount, setAmount] = useState("100");
  const [rows, setRows] = useState<Saved[]>([]);
  const [selected, setSelected] = useState<Saved | null>(null);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [strategy, setStrategy] = useState("UNREVIEWED");
  useEffect(() => {
    Promise.all([api<Profile>("/investment-profile"), api<Portfolio[]>("/portfolios"), api<{ status: string }>("/recommendations/strategies")])
      .then(([p, ps, s]) => { setProfile(p); setDraft(JSON.stringify(p.preferences, null, 2)); setPortfolios(ps); setPortfolio(ps[0]?.id ?? ""); setStrategy(s.status); })
      .catch(e => setError(String(e)));
  }, []);
  useEffect(() => {
    if (!portfolio) return;
    let active = true;
    api<Saved[]>(`/recommendations/history?portfolio_id=${portfolio}&offset=${offset}`).then(r => { if (active) setRows(r); }).catch(e => { if (active) setError(String(e)); });
    api<Risk>(`/portfolios/${portfolio}/risk`).then(r => { if (active) setRisk(r.id ? r : null); }).catch(e => { if (active) setError(String(e)); });
    return () => { active = false; };
  }, [portfolio, offset]);
  async function saveProfile() {
    setBusy(true); setError(""); setMessage("");
    try {
      const preferences = JSON.parse(draft) as Record<string, unknown>;
      const p = await api<Profile>("/investment-profile", { method: "PATCH", body: JSON.stringify({ expected_version_id: profile?.id ?? null, preferences }) });
      setProfile(p); setDraft(JSON.stringify(p.preferences, null, 2)); setMessage("Profilversion gespeichert");
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  async function evaluate() {
    setBusy(true); setError(""); setMessage("");
    try {
      const r = await api<Saved[]>("/recommendations/evaluate", { method: "POST", body: JSON.stringify({ portfolio_id: portfolio, risk_snapshot_id: risk?.id, instrument_ids: instrument ? [instrument] : [], amount_mode: mode, side, amount }) });
      setSelected(r[0] ?? null); setOffset(0);
      setRows(await api<Saved[]>(`/recommendations/history?portfolio_id=${portfolio}`));
      const p = await api<Profile>("/investment-profile"); setProfile(p); setDraft(JSON.stringify(p.preferences, null, 2));
      setMessage(`${r.length} Bewertungen gespeichert. Keine Transaktion ausgeführt.`);
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <main className="space-y-6 py-8"><ValidationLinks />
    <h1 className="text-2xl font-semibold">Recommendations</h1>
    {(strategy !== "PRODUCTION" || !selected?.eligibility.permitted) && <section className="rounded border border-amber-600 p-4"><h2 className="font-semibold">NO VALIDATED INVESTMENT RECOMMENDATIONS</h2><p>Erforderlich: validierte Produktionsprognosen und belegte historische Strategieabnahme.</p><p>Risikoanalysen sind unabhängig davon verfügbar. Abstentions sind keine Anlageeinschätzung.</p></section>}
    {error && <p role="alert" className="text-rose-400">{error}</p>}{message && <p role="status">{message}</p>}
    <section className="space-y-3 rounded border border-zinc-800 p-4"><h2 className="text-xl">Investmentprofil</h2><p>{profile?.status ?? "Lädt"} · Version {profile?.id ?? "Noch nicht gespeichert"}</p><p>Defaults sind unbestätigt. Bestätigen Sie Ihre Grenzen im Feld <code>confirmed</code>. Beträge gelten in der Basiswährung, Gewichte als NAV-Anteile (0–1), Liquidität als 20-Session-Durchschnitt in Stück.</p><details><summary>Einheiten und harte/weiche Grenzen</summary><pre className="overflow-auto text-xs">{JSON.stringify({ units: profile?.units, classification: profile?.classification }, null, 2)}</pre></details><label className="block">Profilparameter<textarea aria-label="Profilparameter" disabled={!profile || busy} className={`${field} mt-2 block h-80 w-full font-mono text-sm`} value={draft} onChange={e => setDraft(e.target.value)} /></label><button className={field} disabled={busy || !profile} onClick={saveProfile}>Profilversion speichern</button></section>
    <section className="space-y-3 rounded border border-zinc-800 p-4"><h2 className="text-xl">Bestände und Kandidaten bewerten</h2><label className="block">Portfolio <select aria-label="Portfolio" className={field} value={portfolio} onChange={e => { if (e.target.value !== portfolio) { setPortfolio(e.target.value); setOffset(0); setRisk(null); setSelected(null); setRows([]); } }}>{portfolios.map(p => <option value={p.id} key={p.id}>{p.name}</option>)}</select></label><p>Risiko-Snapshot: {risk?.id ?? "Nicht verfügbar — zuerst im Portfolio berechnen"}</p><ul>{risk?.result.current_valuation.holdings.map(h => <li key={h.instrument_id}>{h.name} · {h.instrument_id}</li>)}</ul><label className="block">Zusätzliche Instrument-ID <input aria-label="Instrument-ID" className={field} value={instrument} onChange={e => setInstrument(e.target.value)} /></label><label className="block">Hypothese <select aria-label="Hypothese" className={field} value={side} onChange={e => setSide(e.target.value)}><option value="BUY">Kaufbetrag prüfen</option><option value="SELL">Verkaufsbetrag prüfen</option></select></label><label className="block">Betragsmodus <select aria-label="Betragsmodus" className={field} value={mode} onChange={e => setMode(e.target.value)}><option value="FIXED">Fixbetrag Basiswährung</option><option value="NAV_FRACTION">NAV-Anteil 0–1</option><option value="TARGET_WEIGHT">Zielgewicht 0–1</option></select></label><label className="block">Kandidatenbetrag <input aria-label="Kandidatenbetrag" className={field} value={amount} onChange={e => setAmount(e.target.value)} /></label><button className={field} disabled={busy || !risk} onClick={evaluate}>Eligibility prüfen und speichern</button></section>
    {selected && <section className="space-y-3 rounded border border-zinc-800 p-4" aria-label="Bewertungsdetails"><h2 className="text-xl">{selected.category}</h2><p>Score: {selected.result?.scoring.score ?? "Nicht verfügbar"}</p><h3>Fehlende Eingaben</h3><ul>{selected.eligibility.missing_inputs.map(k => <li key={k}>{k}</li>)}</ul><h3>Harte Einschränkungen</h3><ul>{selected.eligibility.violations.map(k => <li key={k}>{k}</li>)}</ul><details><summary>Begründung, Portfolioauswirkung, Risiko, Kosten und Quellen</summary><pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(selected.result?.explanation, null, 2)}</pre></details><details><summary>Gepinnte Eingaben und Präferenzen</summary><pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(selected.input_manifest, null, 2)}</pre></details></section>}
    <section className="space-y-3"><h2 className="text-xl">Unveränderliche Bewertungshistorie</h2>{rows.map(r => <button key={r.id} className="block w-full rounded border border-zinc-800 p-3 text-left" onClick={() => api<Saved>(`/recommendations/${r.id}`).then(setSelected).catch(e => setError(String(e)))}>{r.generated_at} · {r.category} · {r.instrument_id}</button>)}{rows.length === 0 && <p>Keine gespeicherten Bewertungen.</p>}<button className={field} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))}>Neuere</button> <button className={field} disabled={rows.length < 100} onClick={() => setOffset(offset + 100)}>Ältere</button></section>
  </main>;
}
