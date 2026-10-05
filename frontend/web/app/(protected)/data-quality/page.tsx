"use client";

import { useQuery } from "@tanstack/react-query";
import { getQualitySummary } from "@/lib/api/market-data";

function dateTime(value: string | null) {
  return value ? new Date(value).toLocaleString("de-CH") : "Keine geprüften Daten";
}

export default function DataQualityPage() {
  const quality = useQuery({ queryKey: ["data-quality"], queryFn: getQualitySummary });
  const data = quality.data;
  return <main className="space-y-7 py-10">
    <header><h1 className="text-3xl font-semibold">Datenqualität</h1><p className="mt-2 text-zinc-400">Stand der validierten Markt- und FX-Daten. Fehlende Werte werden ausdrücklich angezeigt.</p></header>
    {quality.isPending && <p>Lade Datenqualität…</p>}
    {quality.isError && <p role="alert" className="text-rose-400">{quality.error.message}</p>}
    {data && <>
      {data.status === "UNAVAILABLE" && <p className="rounded border border-amber-800 bg-amber-950 p-4">No validated data available</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        <Metric title="Kursaktualität" value={data.price_freshness} detail={`Letzter geprüfter Import: ${dateTime(data.last_successful_price_import)}`} />
        <Metric title="FX-Aktualität" value={data.fx_freshness} detail={`Letzter geprüfter Import: ${dateTime(data.last_successful_fx_import)}`} />
        <Metric title="Quarantäne" value={String(data.quarantined_rows)} detail="Verworfene oder zu prüfende Datensätze" />
        <Metric title="Quellkonflikte" value={String(data.source_disagreements)} detail="Abweichende Kursbeobachtungen" />
        <Metric title="Fehlgeschlagene Rohdatenimporte" value={String(data.failed_raw_ingestions)} />
        <Metric title="Instrumente ohne Kurse" value={String(data.instruments_with_missing_prices)} />
        <Metric title="Instrumente mit alten Kursen" value={String(data.stale_prices)} />
      </div>
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6"><h2 className="text-xl font-semibold">Kursqualität</h2>{Object.keys(data.price_quality).length === 0 ? <p className="mt-3 text-zinc-400">Keine validierten Kurse verfügbar.</p> : <ul className="mt-3 grid gap-2 sm:grid-cols-2">{Object.entries(data.price_quality).map(([label, count]) => <li key={label}>{label}: {count}</li>)}</ul>}</section>
    </>}
  </main>;
}

function Metric({ title, value, detail }: { title: string; value: string; detail?: string }) {
  return <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5"><h2 className="text-sm text-zinc-400">{title}</h2><p className="mt-2 text-2xl font-semibold">{value}</p>{detail && <p className="mt-2 text-sm text-zinc-400">{detail}</p>}</section>;
}
