"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { News } from "@/lib/api/research";
import { EmptyState, ErrorState, FinancialMetric, LoadingSkeleton } from "@/components/ui/primitives";

type Action = { id: string; date: string; type: string; ratio: string | null; cash_amount: string | null; currency: string | null; payment_date: string | null; source_id: string; raw_ingestion_id: string; known_at: string };
const names: Record<string, string> = { SPLIT: "Aktiensplit", REVERSE_SPLIT: "Aktienzusammenlegung", DIVIDEND: "Dividende", SYMBOL_CHANGE: "Symboländerung", DELISTING: "Delisting" };

export function InstrumentEvents({ instrumentId }: { instrumentId: string }) {
  const actions = useQuery({ queryKey: ["corporate-actions", instrumentId], queryFn: () => api<{ actions: Action[] }>(`/instruments/${instrumentId}/corporate-actions`) });
  const news = useQuery({ queryKey: ["instrument-news", instrumentId], queryFn: () => api<News[]>(`/instruments/${instrumentId}/news`) });
  return <div className="grid gap-6 xl:grid-cols-2"><section className="ui-panel space-y-4"><h2 className="text-xl font-semibold">Dividenden und Aktiensplits</h2><p className="text-xs ui-muted">Archivierte kanonische Ereignisse der letzten zehn Jahre. Diese Anzeige ist kein Nachweis vollständiger Abdeckung und bucht keine Dividende in ein Portfolio.</p>
    {actions.isPending && <LoadingSkeleton />}{actions.isError && <ErrorState error={actions.error} />}{actions.data?.actions.length === 0 && <EmptyState title="Keine belegten Ereignisse im Archiv" description="Ohne geprüfte Abdeckung darf daraus nicht auf ausgebliebene Dividenden oder Splits geschlossen werden." />}
    <ul className="space-y-3">{actions.data?.actions.map(a => <li key={a.id} className="rounded-lg border border-zinc-800 p-4"><h3 className="font-semibold">{names[a.type] ?? a.type} · {a.date}</h3>{a.type === "DIVIDEND" ? <p>Brutto je Aktie: {a.currency ? <FinancialMetric value={a.cash_amount} currency={a.currency} /> : "Nicht verfügbar: Währung fehlt"}</p> : a.ratio && <p>Verhältnis: {a.ratio}</p>}<p className="text-xs ui-muted">Zahlungstag: {a.payment_date ?? "Nicht angegeben"} · Bekannt seit {a.known_at}</p><details className="ui-details"><summary>Herkunft und Version</summary><p className="break-all text-xs">Quelle {a.source_id} · Original {a.raw_ingestion_id} · Version {a.id}</p></details></li>)}</ul>
    <Link href="/data-quality" className="ui-button">Anwendung im eigenen Portfolio prüfen</Link>
  </section><section className="ui-panel space-y-4"><h2 className="text-xl font-semibold">Zugeordnete Nachrichten</h2><p className="text-xs ui-muted">Archivierte Metadaten und Originalverweise. Eine Nachricht begründet keine Anlageempfehlung.</p>
    {news.isPending && <LoadingSkeleton />}{news.isError && <ErrorState error={news.error} />}{news.data?.length === 0 && <EmptyState title="Keine zugeordneten Nachrichten" description="Eine zulässige Quelle und eine geprüfte Instrumentzuordnung sind erforderlich." />}
    <ul className="space-y-3">{news.data?.slice(0, 10).map(n => <li key={n.id} className="border-b border-zinc-800 pb-4"><a className="font-medium underline" href={n.source_url} target="_blank" rel="noreferrer">{n.title}</a><p className="text-xs ui-muted mt-1">Veröffentlicht: {n.published_at ?? "Nicht belegt"} · Lokal entdeckt: {n.discovered_at}</p>{n.summary && <p className="text-sm mt-2">{n.summary}</p>}</li>)}</ul><Link href="/news" className="ui-button">Nachrichtenarchiv öffnen</Link>
  </section><section className="ui-panel xl:col-span-2 space-y-3"><h2 className="text-xl font-semibold">Risiko im Zusammenhang Ihres Depots</h2><p className="text-sm ui-muted">Die Wirkung eines Instruments hängt von Gewichtung, anderen Positionen und Währungen ab. Die Portfolioanalyse verwendet Ihre tatsächlichen Buchungen und prüft Datenabdeckung, bevor sie Kennzahlen berechnet.</p><Link href="/analyses" className="ui-button">Portfolio und Risiko auswählen</Link></section></div>;
}
