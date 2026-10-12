"use client";

import { useQuery } from "@tanstack/react-query";
import { getQualitySummary } from "@/lib/api/market-data";
import { api } from "@/lib/api";
import Link from "next/link";
import { listPortfolios, getValuation } from "@/lib/api/portfolios";
import { useQueries } from "@tanstack/react-query";

type OperationalStatus = { backup: { status: string; completed_at: string | null };
  restore_test: { status: string; completed_at: string | null } };

function dateTime(value: string | null) {
  return value ? new Date(value).toLocaleString("de-CH") : "Keine geprüften Daten";
}

export default function DataQualityPage() {
  const quality = useQuery({ queryKey: ["data-quality"], queryFn: getQualitySummary });
  const operations = useQuery({ queryKey: ["backup-status"],
    queryFn: () => api<OperationalStatus>("/system/backup-status") });
  const data = quality.data;
  const portfolios = useQuery({ queryKey: ["portfolios"], queryFn: listPortfolios });
  const valuations = useQueries({ queries: (portfolios.data ?? []).map(portfolio => ({
    queryKey: ["valuation", portfolio.id], queryFn: () => getValuation(portfolio.id),
  })) });
  return <main className="space-y-7 py-10">
    <header><h1 className="text-3xl font-semibold">Datenqualität</h1><p className="mt-2 text-zinc-400">Stand der validierten Markt- und FX-Daten. Fehlende Werte werden ausdrücklich angezeigt.</p></header>
    {quality.isPending && <p>Lade Datenqualität…</p>}
    {quality.isError && <p role="alert" className="text-rose-400">{quality.error.message}</p>}
    <section className="space-y-3 rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Portfolio-Bewertungen</h2>
      {portfolios.isError && <p role="alert">{portfolios.error.message}</p>}
      {portfolios.data?.map((portfolio, index) => <article key={portfolio.id}><Link className="text-emerald-400 underline" href={`/portfolios/${portfolio.id}`}>{portfolio.name}</Link><p>{valuations[index].isPending ? "Wird geprüft…" : valuations[index].data?.status ?? "DATA_UNAVAILABLE"}</p>{valuations[index].isError && <p role="alert">{valuations[index].error.message}</p>}<ul className="text-sm text-amber-400">{valuations[index].data?.issues.map((issue, item) => <li key={item}>{issue.code} · {issue.currency}{issue.instrument_id && <Link href={`/instrument/${issue.instrument_id}`} className="ml-2 underline">Instrument / Quelle prüfen</Link>}</li>)}</ul></article>)}
    </section>
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
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6"><h2 className="text-xl font-semibold">Datensicherung</h2><p className="mt-2">Letztes Backup: {operations.data?.backup.status ?? "UNAVAILABLE"} · {dateTime(operations.data?.backup.completed_at ?? null)}</p><p className="mt-2">Isolierter Restore-Test: {operations.data?.restore_test.status ?? "UNAVAILABLE"} · {dateTime(operations.data?.restore_test.completed_at ?? null)}</p>{operations.isError && <p role="alert" className="text-rose-400">Status nicht verfügbar: {operations.error.message}</p>}</section>
      {data.source_failures.length > 0 && <section className="rounded-xl border border-amber-800 bg-amber-950 p-6"><h2 className="font-semibold">Quellenausfälle</h2><ul className="mt-2 space-y-1">{data.source_failures.map((source) => <li key={source.slug}>{source.slug}: {source.failure_count} Fehler, zuletzt {dateTime(source.last_failure)}</li>)}</ul></section>}
    </>}
  </main>;
}

function Metric({ title, value, detail }: { title: string; value: string; detail?: string }) {
  return <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5"><h2 className="text-sm text-zinc-400">{title}</h2><p className="mt-2 text-2xl font-semibold">{value}</p>{detail && <p className="mt-2 text-sm text-zinc-400">{detail}</p>}</section>;
}
