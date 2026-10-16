"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { DataSource } from "@/lib/api/market-foundation";

export function SourceControls({ source }: { source: DataSource }) {
  const client = useQueryClient();
  const rights = useQuery({ queryKey: ["data-operations"], queryFn: () => api<{ is_operator: boolean }>("/data-operations") });
  const [status, setStatus] = useState("UNKNOWN"); const [terms, setTerms] = useState(source.terms_url ?? "");
  const [scope, setScope] = useState(source.scope ?? ""); const [uses, setUses] = useState(source.allowed_uses.join(","));
  const [note, setNote] = useState(""); const [next, setNext] = useState(""); const [rate, setRate] = useState(10);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function change(action: string) {
    setBusy(true); setError("");
    try {
      await api(`/data-operations/sources/${source.slug}/${action}`, { method: "POST", ...(action === "review" ? { body: JSON.stringify({ status, terms_url: terms || null, scope, allowed_uses: uses.split(",").map(s => s.trim()).filter(Boolean), decision_note: note, next_review_at: next ? `${next}T23:59:00Z` : null, rate_limit_per_minute: rate }) } : {}) });
      await client.invalidateQueries({ queryKey: ["data-sources"] });
      await client.invalidateQueries({ queryKey: ["source-reviews", source.slug] });
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Änderung fehlgeschlagen"); }
    finally { setBusy(false); }
  }
  const history = useQuery({ queryKey: ["source-reviews", source.slug], queryFn: () => api<{ id: string; created_at: string; decision: { status: string; decision_by: string; decision_note: string } }[]>(`/data-operations/sources/${source.slug}/reviews`), enabled: rights.data?.is_operator === true });
  const box = "block w-full rounded border border-zinc-700 bg-zinc-950 p-2";
  return <div className="mt-4 space-y-3 text-sm"><p>Letzter erfolgreicher Import: {source.last_success ?? "Keiner"} · Letzter Fehler: {source.last_failure ?? "Keiner"} · Limit: {source.rate_limit_per_minute ?? "Nicht konfiguriert"}/Minute</p>
    {source.scope && <p>Freigabeumfang: {source.scope}</p>}
    {rights.data?.is_operator && <details><summary className="cursor-pointer text-emerald-400">Operator: Rechteentscheidung und Aktivierung</summary>
      <p className="my-3 text-amber-300">Die Entscheidung erfordert belegte Rechte für automatischen Abruf, lokale Originalablage, historische Aufbewahrung und Analysen. Speichern deaktiviert die Quelle; Aktivieren ist ein eigener Schritt.</p>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={e => { e.preventDefault(); void change("review"); }}>
        <label>Rechtestatus<select className={box} value={status} onChange={e => setStatus(e.target.value)}><option>UNKNOWN</option><option>BLOCKED</option><option>APPROVED</option></select></label>
        <label>Nutzungsbedingungen<input className={box} type="url" value={terms} onChange={e => setTerms(e.target.value)} /></label>
        <label>Genauer Freigabeumfang<textarea className={box} required minLength={10} value={scope} onChange={e => setScope(e.target.value)} /></label>
        <label>Erlaubte Datennutzungen (Komma getrennt)<input className={box} value={uses} onChange={e => setUses(e.target.value)} /></label>
        <label>Begründung und Beleg<textarea className={box} required minLength={20} value={note} onChange={e => setNote(e.target.value)} /></label>
        <label>Nächste Rechteprüfung<input className={box} type="date" value={next} onChange={e => setNext(e.target.value)} /></label>
        <label>Anfragen pro Minute<input className={box} type="number" min={1} max={300} value={rate} onChange={e => setRate(Number(e.target.value))} /></label>
        <button className={box} disabled={busy} type="submit">Rechteentscheidung speichern</button>
      </form>
      <div className="my-3 flex gap-3"><button className="rounded border p-2" disabled={busy || source.gate_status !== "APPROVED" || source.enabled} onClick={() => void change("enable")}>Separat aktivieren</button><button className="rounded border p-2" disabled={busy || !source.enabled} onClick={() => void change("disable")}>Deaktivieren</button></div>
      <h3>Archivierte Rechteentscheidungen</h3>{history.data?.map(row => <p key={row.id}>{row.created_at} · {row.decision.status} · {row.decision.decision_by} · {row.decision.decision_note}</p>)}
    </details>}
    {error && <p role="alert" className="text-rose-300">{error}</p>}
  </div>;
}
