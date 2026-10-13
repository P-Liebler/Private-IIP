"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getNews } from "@/lib/api/research";
import { getSources } from "@/lib/api/market-foundation";

export default function NewsPage() {
  const [offset,setOffset]=useState(0);const [source,setSource]=useState("");const [start,setStart]=useState("");
  const params=new URLSearchParams({offset:String(offset),limit:"25"});if(source)params.set("source_id",source);if(start)params.set("start",`${start}T00:00:00Z`);
  const news=useQuery({queryKey:["news",params.toString()],queryFn:()=>getNews(params.toString())});const sources=useQuery({queryKey:["data-sources"],queryFn:getSources});
  return <main className="space-y-6 py-10"><h1 className="text-3xl font-semibold">News</h1><p>Archivierte Metadaten und Quellenlinks. Duplikate sind gekennzeichnet; Sentiment ohne lokales Modell bleibt unavailable.</p><div className="flex gap-4"><select aria-label="News Quelle" value={source} onChange={e=>setSource(e.target.value)} className="rounded bg-zinc-900 p-3"><option value="">Alle Quellen</option>{sources.data?.map(s=><option key={s.id} value={s.id}>{s.slug}</option>)}</select><input aria-label="News ab Datum" type="date" value={start} onChange={e=>setStart(e.target.value)} className="rounded bg-zinc-900 p-3"/></div>{news.isError&&<p role="alert">{news.error.message}</p>}{news.isPending&&<p>Lade Nachrichten…</p>}{news.data?.length===0&&<p>Keine Nachrichten verfügbar. Externe Quellen benötigen eine dokumentierte Freigabe.</p>}{news.data?.map(n=><article className="rounded border border-zinc-800 p-5" key={n.id}><a className="text-emerald-400 underline" href={n.source_url} target="_blank" rel="noopener noreferrer">{n.title}</a><p className="text-sm text-zinc-400">{sources.data?.find(s=>s.id===n.source_id)?.slug??n.source_id} · Veröffentlicht {n.published_at??"unbekannt"} · Entdeckt {n.discovered_at}</p>{n.summary&&<p>{n.summary}</p>}<p>Sentiment: {n.sentiment?"vorhanden":"unavailable"} {n.duplicate_of_id&&`· Duplikat von ${n.duplicate_of_id}`}</p><p>{n.associations.map(a=>`${a.instrument_id}: ${a.mapping_status}`).join(" · ")}</p></article>)}<button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-25))} className="mr-4">← Zurück</button><button disabled={(news.data?.length??0)<25} onClick={()=>setOffset(offset+25)}>Weiter →</button></main>;
}
