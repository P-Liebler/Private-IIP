"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, StatusIndicator } from "@/components/ui/primitives";

export const field = "rounded border border-zinc-700 bg-zinc-950 p-2 disabled:opacity-50";
export function Result({ value }: { value: unknown }) {
  if (value === null || value === undefined) return null;
  return <section aria-label="Strukturiertes Ergebnis" className="ui-panel space-y-4"><Evidence value={value} depth={0} /><details className="ui-details"><summary>Technische Originalantwort und Kennungen</summary><pre className="max-h-[40rem] overflow-auto whitespace-pre-wrap mt-4 text-xs">{JSON.stringify(value, null, 2)}</pre></details></section>;
}
const labels: Record<string, string> = { status: "Zustand", reason: "Begründung", reasons: "Begründungen", created_at: "Erstellt", as_of: "Wissensstand", observed_at: "Lokal beobachtet", result: "Ergebnis", results: "Ergebnisse", items: "Einträge", metrics: "Kennzahlen", assumptions: "Annahmen", warnings: "Hinweise", missing_inputs: "Fehlende Grundlagen", score: "Bewertung", confidence: "Vertrauensmaß", evidence: "Belege", source: "Quelle", sources: "Quellen", name: "Name", title: "Titel", description: "Beschreibung", value: "Wert", currency: "Währung", calculation_type: "Berechnungsverfahren", mode: "Verfahren", observations: "Beobachtungen", coverage: "Datenabdeckung", available: "Verfügbar" };
function Evidence({ value, depth }: { value: unknown; depth: number }) {
  if (value === null || value === undefined) return <span className="ui-muted">Nicht verfügbar</span>;
  if (typeof value === "boolean") return <span>{value ? "Ja" : "Nein"}</span>;
  if (typeof value !== "object") return <span className="break-words">{String(value)}</span>;
  if (depth >= 4) return <span className="text-xs ui-muted">Weitere verschachtelte Details stehen in der Originalantwort.</span>;
  if (Array.isArray(value)) return value.length ? <><ul className="space-y-3">{value.slice(0, 50).map((v, i) => <li key={i} className="border-l-2 border-zinc-700 pl-3"><Evidence value={v} depth={depth + 1} /></li>)}</ul>{value.length > 50 && <p className="text-xs ui-muted">50 von {value.length} Einträgen. Vollständige Daten in der Originalantwort.</p>}</> : <p className="text-sm ui-muted">Keine Einträge übermittelt. Eine leere Liste beweist keine vollständige Datenabdeckung.</p>;
  const entries = Object.entries(value as Record<string, unknown>);
  if (!entries.length) return <EmptyState title="Noch kein Ergebnisinhalt" description="Die Antwort enthält keine auswertbaren Felder." />;
  const technical = (key: string) => /(^id$|_id$|_ids$|hash|manifest|configuration|code_version)/.test(key);
  const readable = entries.filter(([key]) => !technical(key));
  return <dl className="ui-result-grid">{readable.slice(0, 50).map(([key, v]) => <div className="ui-result-entry" key={key}><dt>{labels[key] ?? key.replaceAll("_", " ")}</dt><dd>{(key === "status" || key.endsWith("_status")) && typeof v === "string" ? <StatusIndicator status={v} /> : <Evidence value={v} depth={depth + 1} />}</dd></div>)}{readable.length === 0 && <div className="ui-result-entry"><dt>Nachweis gespeichert</dt><dd>Kennungen und Herkunft stehen in der technischen Originalantwort. Dies ist keine finanzielle Freigabe.</dd></div>}</dl>;
}
export function PortfolioSelect({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  const [rows, setRows] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api<{ id: string; name: string }[]>("/portfolios").then(setRows).catch(e => setError(String(e))); }, []);
  return <label className="block">Portfolio <select aria-label="Portfolio" className={field} value={value} onChange={e => onChange(e.target.value)}><option value="">Bitte waehlen</option>{rows.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>{error && <span role="alert">{error}</span>}</label>;
}
