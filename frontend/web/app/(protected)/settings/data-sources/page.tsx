"use client";

import Link from "next/link";
import { SourceControls } from "@/components/source-controls";
import { useQuery } from "@tanstack/react-query";
import { getSources } from "@/lib/api/market-foundation";

export default function DataSourcesPage() {
  const sources = useQuery({ queryKey: ["data-sources"], queryFn: getSources });
  return <main className="py-10"><Link href="/settings" className="text-emerald-400 hover:underline">← Einstellungen</Link>
    <h1 className="mt-6 text-3xl font-semibold">Datenquellen</h1><p className="mt-2 text-zinc-400">Quellenfreigaben, Aktualität und archivierte Operator-Entscheidungen.</p>
    {sources.isPending && <p className="mt-6">Lade Quellen…</p>}
    {sources.isError && <p role="alert" className="mt-6 text-rose-400">{sources.error.message}</p>}
    <ul className="mt-6 space-y-3">{sources.data?.map((source) => <li key={source.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-5"><h2 className="text-lg font-semibold">{source.name} <span className="text-sm font-normal text-zinc-500">({source.slug})</span></h2><dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><div><dt className="text-zinc-400">Gate</dt><dd>{source.gate_status}</dd></div><div><dt className="text-zinc-400">Aktiv</dt><dd>{source.enabled ? "Ja" : "Nein"}</dd></div><div><dt className="text-zinc-400">Vertrauen</dt><dd>{source.trust_level}</dd></div><div><dt className="text-zinc-400">Letzte Prüfung</dt><dd>{source.checked_at ? new Date(source.checked_at).toLocaleDateString("de-CH") : "Keine"}</dd></div><div><dt className="text-zinc-400">Nächste Prüfung</dt><dd>{source.next_review_at ? new Date(source.next_review_at).toLocaleDateString("de-CH") : "Nicht festgelegt"}</dd></div><div><dt className="text-zinc-400">Erlaubte Nutzung</dt><dd>{source.allowed_uses.join(", ") || "Keine"}</dd></div></dl><SourceControls source={source} /></li>)}</ul>
  </main>;
}
