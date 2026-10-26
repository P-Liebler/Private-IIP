"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { searchInstruments } from "@/lib/api/market-foundation";
import { getWatchlists, getWatchItems } from "@/lib/api/research";
import { Button, ConfirmationDialog, EmptyState, ErrorState, LoadingSkeleton, PageHeader, SearchCombobox } from "@/components/ui/primitives";

export default function WatchlistsPage() {
  const cache = useQueryClient();
  const [name, setName] = useState("");
  const [id, setId] = useState("");
  const [instrument, setInstrument] = useState("");
  const [selectedName, setSelectedName] = useState("");
  const [search, setSearch] = useState("");
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState("");
  const lists = useQuery({ queryKey: ["watchlists"], queryFn: getWatchlists });
  const items = useQuery({ queryKey: ["watchlist-items", id], queryFn: () => getWatchItems(id), enabled: !!id });
  const hits = useQuery({ queryKey: ["instrument-search", search], queryFn: () => searchInstruments(search), enabled: search.trim().length >= 2 });
  const action = useMutation({ mutationFn: ({ path, method, body }: { path: string; method: string; body?: unknown }) => api(path, { method, body: body === undefined ? undefined : JSON.stringify(body) }), onSuccess: async () => { await cache.invalidateQueries({ queryKey: ["watchlists"] }); await cache.invalidateQueries({ queryKey: ["watchlist-items"] }); } });
  return <main className="space-y-8"><PageHeader title="Watchlists" description="Eigene Beobachtungslisten und private Notizen. Research-Scores sind keine Anlageempfehlungen." />
    <form className="ui-panel flex flex-wrap gap-3" onSubmit={e => { e.preventDefault(); if (!action.isPending) action.mutate({ path: "/watchlists", method: "POST", body: { name } }); }}><label className="grid gap-2 flex-1">Watchlist Name<input required maxLength={120} value={name} onChange={e => setName(e.target.value)} placeholder="Zum Beispiel: Langfristig beobachten" /></label><Button className="self-end" variant="primary" disabled={!name.trim() || action.isPending}>Watchlist erstellen</Button></form>
    {lists.isPending && <LoadingSkeleton />}{lists.isError && <ErrorState error={lists.error} />}{action.isError && <ErrorState error={action.error} />}
    {lists.data?.length === 0 && <EmptyState title="Noch keine Beobachtungsliste" description="Legen Sie eine Liste an und suchen Sie anschließend nach Instrumenten mit Name, Ticker oder ISIN." />}
    <label className="grid gap-2 max-w-xl">Watchlist öffnen<select value={id} onChange={e => { setId(e.target.value); setInstrument(""); setSelectedName(""); }}><option value="">Watchlist wählen</option>{lists.data?.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
    {id && <>
      <div className="flex flex-wrap gap-3"><Button disabled={!name.trim() || action.isPending} onClick={() => action.mutate({ path: `/watchlists/${id}`, method: "PATCH", body: { name } })}>Umbenennen</Button><ConfirmationDialog title="Watchlist archivieren?" description="Die Liste wird aus der aktiven Auswahl entfernt. Diese Aktion löst keine Buchung oder Order aus." trigger={<Button variant="danger">Archivieren</Button>} onConfirm={async () => { await action.mutateAsync({ path: `/watchlists/${id}`, method: "PATCH", body: { archived: true } }); setId(""); }} /></div>
      <section className="ui-panel space-y-5"><h2 className="text-xl font-semibold">Ein Instrument beobachten</h2><SearchCombobox label="Instrument für Watchlist suchen" onSearch={setSearch} busy={hits.isFetching} options={(hits.data ?? []).map(h => ({ id: h.instrument.id, label: h.instrument.name, detail: `${h.instrument.isin ?? h.instrument.ticker ?? "Keine Kennung"} · ${h.instrument.mic ?? h.instrument.exchange ?? "Börse ungeprüft"} · ${h.instrument.currency}` }))} onSelect={value => { setInstrument(value); setSelectedName(hits.data?.find(h => h.instrument.id === value)?.instrument.name ?? "Ausgewähltes Instrument"); }} />
        {hits.isError && <ErrorState error={hits.error} />}{instrument && <p role="status">Ausgewählt: {selectedName}. Kennung, Börse und Handelswährung vor dem Speichern prüfen.</p>}
        <label className="grid gap-2">Notizen<textarea value={notes} onChange={e => setNotes(e.target.value)} /></label><label className="grid gap-2">Tags<input value={tags} onChange={e => setTags(e.target.value)} placeholder="Durch Kommas getrennt" /></label>
        <Button variant="primary" disabled={!instrument || action.isPending} onClick={() => action.mutate({ path: `/watchlists/${id}/items`, method: "PUT", body: { instrument_id: instrument, notes, tags: tags.split(",").map(t => t.trim()).filter(Boolean) } })}>Instrument / Notizen speichern</Button>
      </section>
      {items.isPending && <LoadingSkeleton />}{items.isError && <ErrorState error={items.error} />}{items.data?.length === 0 && <EmptyState title="Diese Watchlist ist noch leer" description="Wählen Sie oben ein Instrument aus oder fügen Sie es von seiner Detailseite hinzu." />}
      <div className="grid gap-4 lg:grid-cols-2">{items.data?.map(item => <article className="ui-panel space-y-3" key={item.id}><Link className="text-lg font-semibold underline" href={`/instrument/${item.instrument_id}`}>{item.instrument.name}</Link><p className="text-sm">{item.price ? `Schlusskurs ${item.price.close} ${item.price.currency} vom ${item.price.date} · ${item.price.quality_label} · ${item.price.age_days} Tage alt` : "Kurs nicht verfügbar"}</p><p className="text-xs ui-muted">Quality: {item.research?.scores.Quality.score ?? "Nicht auswertbar"} · Growth: {item.research?.scores.Growth.score ?? "Nicht auswertbar"}</p><p>{item.notes}</p><p className="text-xs ui-muted">{item.tags.join(", ")}</p><div className="flex flex-wrap gap-3"><Button onClick={() => { setInstrument(item.instrument_id); setSelectedName(item.instrument.name); setNotes(item.notes ?? ""); setTags(item.tags.join(", ")); document.querySelector('textarea')?.focus(); }}>Notizen bearbeiten</Button><ConfirmationDialog title="Instrument aus Watchlist entfernen?" description="Die Beobachtung wird entfernt. Ihr Portfolio und seine Buchungen bleiben erhalten." trigger={<Button variant="danger">Entfernen</Button>} onConfirm={() => action.mutateAsync({ path: `/watchlists/${id}/items/${item.instrument_id}`, method: "DELETE" })} /></div></article>)}</div>
    </>}
  </main>;
}
