"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ResearchQuality } from "@/lib/api/research";

export function ResearchQualityPanel() {
  const result=useQuery({queryKey:["research-quality"],queryFn:()=>api<ResearchQuality>("/data-quality/research")});
  return <section className="space-y-3 rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Research-Datenqualität</h2>{result.isPending&&<p>Lade Research-Status…</p>}{result.isError&&<p role="alert">{result.error.message}</p>}{result.data&&<><p>Letztes Filing: {result.data.last_filing_ingestion??"DATA_UNAVAILABLE"} · Letzte Faktenperiode: {result.data.last_fact_period??"DATA_UNAVAILABLE"}</p><p>Fehlgeschlagene Importe: {result.data.failed_ingestions} · Fehlende Fundamentals: {result.data.missing_fundamentals} · Quarantäne: {result.data.quarantined_facts} · Versionierte Korrekturen: {result.data.restatements}</p><p>News: {result.data.news_articles} · Duplikate: {result.data.news_duplicates} · Schätzungssnapshots: {result.data.estimate_count}</p>{result.data.sources.map(source=><p key={source.id}>{source.slug}: {source.gate_status} · {source.enabled?"aktiv":"deaktiviert"} · Letzter Erfolg {source.last_success??"Keiner"}</p>)}</>}</section>;
}
