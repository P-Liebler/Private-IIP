"use client";

import Link from "next/link";
import { StatusIndicator } from "@/components/ui/primitives";
import { sourceExplanations } from "@/lib/source-explanations";
import { SourceControls } from "@/components/source-controls";
import { SourceReadiness } from "@/components/source-readiness";
import { useQuery } from "@tanstack/react-query";
import { getSources } from "@/lib/api/market-foundation";

export default function DataSourcesPage() {
  const sources = useQuery({ queryKey: ["data-sources"], queryFn: getSources });
  return <main className="py-10"><Link href="/settings" className="text-emerald-400 hover:underline">← Einstellungen</Link>
    <h1 className="mt-6 text-3xl font-semibold">Datenquellen</h1><p className="mt-2 text-zinc-400">Quellenfreigaben, Aktualität und archivierte Operator-Entscheidungen.</p>
    <button className="ui-button mt-4" disabled={sources.isFetching} onClick={() => void sources.refetch()}>Quellenstatus aktualisieren</button>
    {sources.isFetching && !sources.isPending && <p role="status" className="mt-3">Aktueller Quellenstatus wird geprüft…</p>}
    <section className="mt-5 space-y-3 rounded border border-zinc-700 p-5"><h2 className="text-xl font-semibold">Eine Quelle bewusst freigeben</h2><ol className="list-decimal space-y-2 pl-5"><li>Konkreten Dienst und benötigte Daten prüfen: Markt/Instrument, erlaubter automatisierter Abruf, Originalspeicherung, Aufbewahrung, abgeleitete Analyse und Attribution.</li><li>Primärbedingungen mit Datum und Fundstelle archivieren. Einen begrenzten Scope und ein Ablauf-/Prüfdatum festlegen; offene Rechte bedeuten UNKNOWN oder BLOCKED.</li><li>Als berechtigter Operator die Entscheidung dokumentieren. Eine Review schaltet die Quelle zunächst aus; erst anschließend ausdrücklich aktivieren.</li><li>Unter Datenbetrieb einen einzelnen begrenzten Auftrag für gehaltene Instrumente oder eine kleine Watchlist auslösen und Originale, Qualität sowie Erfolgs-/Fehlerzeit prüfen.</li></ol><p className="text-sm text-amber-400">Technische Unterstützung, Vertrauen oder ein kostenloser API-Zugang erteilen keine Nutzungsrechte. Globale Collection bleibt standardmäßig aus; ein erfolgreicher Einzelabruf ist noch keine abgenommene tägliche Versorgung.</p><Link className="text-emerald-400 underline" href="/data-operations">Zum Datenbetrieb</Link> · <Link className="text-emerald-400 underline" href="/imports">Zulässige Originaldatei manuell importieren</Link></section>
    {sources.isPending && <p className="mt-6">Lade Quellen…</p>}
    {sources.isError && <div className="mt-6 space-y-3"><p role="alert" className="text-rose-400">{sources.error.message}</p><button className="ui-button" disabled={sources.isFetching} onClick={() => void sources.refetch()}>Quellen erneut laden</button></div>}
    <ul className="mt-6 space-y-3">{!sources.isError && sources.data?.map((source) => <li key={source.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-5"><h2 className="text-lg font-semibold">{source.name} <span className="text-sm font-normal text-zinc-500">({source.slug})</span></h2><p className="mt-3 text-sm ui-muted">{sourceExplanations[source.slug] ?? "Quellenvertrag und konkreten Datenumfang vor Nutzung prüfen."}</p><dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><div><dt className="text-zinc-400">Gate</dt><dd><StatusIndicator status={source.gate_status} /><details className="mt-2 text-xs"><summary>Technischer Zustand</summary>{source.gate_status}</details></dd></div><div><dt className="text-zinc-400">Aktiv</dt><dd>{source.enabled ? "Ja" : "Nein"}</dd></div><div><dt className="text-zinc-400">Vertrauen</dt><dd>{source.trust_level}</dd></div><div><dt className="text-zinc-400">Letzte Prüfung</dt><dd>{source.checked_at ? new Date(source.checked_at).toLocaleDateString("de-CH") : "Keine"}</dd></div><div><dt className="text-zinc-400">Nächste Prüfung</dt><dd>{source.next_review_at ? new Date(source.next_review_at).toLocaleDateString("de-CH") : "Nicht festgelegt"}</dd></div><div><dt className="text-zinc-400">Erlaubte Nutzung</dt><dd>{source.allowed_uses.join(", ") || "Keine"}</dd></div></dl><SourceReadiness source={source} /><SourceControls source={source} /></li>)}</ul>
  </main>;
}
