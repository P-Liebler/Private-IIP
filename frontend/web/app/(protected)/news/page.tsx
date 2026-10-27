"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getNews } from "@/lib/api/research";
import { getSources } from "@/lib/api/market-foundation";
import { Button, EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/primitives";

export default function NewsPage() {
  const [offset, setOffset] = useState(0);
  const [source, setSource] = useState("");
  const [start, setStart] = useState("");
  const params = new URLSearchParams({ offset: String(offset), limit: "25" });
  if (source) params.set("source_id", source);
  if (start) params.set("start", `${start}T00:00:00Z`);
  const news = useQuery({ queryKey: ["news", params.toString()], queryFn: () => getNews(params.toString()) });
  const sources = useQuery({ queryKey: ["data-sources"], queryFn: getSources });
  const rows = news.isError ? undefined : news.data;
  return <main className="space-y-6 py-10">
    <h1 className="text-3xl font-semibold">News</h1>
    <p>Archivierte Metadaten und Quellenlinks. Duplikate sind gekennzeichnet; Sentiment ohne lokales Modell bleibt nicht verfügbar.</p>
    <div className="flex flex-wrap gap-4">
      <select aria-label="News Quelle" value={source} disabled={sources.isPending} onChange={event => { setSource(event.target.value); setOffset(0); }} className="rounded bg-zinc-900 p-3">
        <option value="">Alle Quellen</option>{sources.data?.map(item => <option key={item.id} value={item.id}>{item.slug}</option>)}
      </select>
      <input aria-label="News ab Datum" type="date" value={start} onChange={event => { setStart(event.target.value); setOffset(0); }} className="rounded bg-zinc-900 p-3" />
    </div>
    {sources.isError && <ErrorState error={sources.error} retry={() => { void sources.refetch(); }} />}
    <section aria-label="Archivierte Nachrichten" className="space-y-4">
      {news.isError && <ErrorState error={news.error} retry={() => { void news.refetch(); }} />}
      {news.isPending && <LoadingSkeleton label="Nachrichten werden geladen" />}
      {rows?.length === 0 && <EmptyState title="Keine Nachrichten verfügbar" description="Für diese Filter liegen keine archivierten Nachrichten vor. Externe Quellen benötigen eine dokumentierte Freigabe." />}
      {rows?.map(item => <article className="rounded border border-zinc-800 p-5" key={item.id}>
        <a className="text-emerald-400 underline" href={item.source_url} target="_blank" rel="noopener noreferrer">{item.title}</a>
        <p className="text-sm text-zinc-400">{sources.data?.find(value => value.id === item.source_id)?.slug ?? item.source_id} · Veröffentlicht {item.published_at ?? "unbekannt"} · Entdeckt {item.discovered_at}</p>
        {item.summary && <p>{item.summary}</p>}
        <p>Sentiment: {item.sentiment ? "vorhanden" : "nicht verfügbar"} {item.duplicate_of_id && `· Duplikat von ${item.duplicate_of_id}`}</p>
        <p>{item.associations.map(value => `${value.instrument_id}: ${value.mapping_status}`).join(" · ")}</p>
      </article>)}
    </section>
    <div className="flex gap-4">
      <Button disabled={offset === 0 || news.isFetching} onClick={() => setOffset(Math.max(0, offset - 25))}>← Zurück</Button>
      <Button disabled={news.isFetching || (rows?.length ?? 0) < 25} onClick={() => setOffset(offset + 25)}>Weiter →</Button>
    </div>
  </main>;
}
