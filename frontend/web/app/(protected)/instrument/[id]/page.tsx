"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getInstrument, getSources } from "@/lib/api/market-foundation";
import { getPrices, type PriceRecord } from "@/lib/api/market-data";

function PriceChart({ prices }: { prices: PriceRecord[] }) {
  if (prices.length < 2) return <p className="text-sm text-zinc-400">Für eine Kurslinie sind mindestens zwei geprüfte Tageskurse nötig.</p>;
  const closes = prices.map((price) => price.close);
  const minimum = Math.min(...closes);
  const maximum = Math.max(...closes);
  const spread = maximum - minimum || 1;
  const points = closes.map((close, index) => `${(index / (closes.length - 1)) * 100},${90 - ((close - minimum) / spread) * 80}`).join(" ");
  return <div><svg role="img" aria-label="Verlauf der ungepassten geprüften Schlusskurse" viewBox="0 0 100 100" preserveAspectRatio="none" className="h-48 w-full rounded bg-zinc-950"><polyline points={points} fill="none" stroke="#34d399" strokeWidth="1.5" vectorEffect="non-scaling-stroke" /></svg><div className="mt-2 flex justify-between text-xs text-zinc-400"><span>{prices[0].date}</span><span>Unangepasster Schlusskurs · {prices[0].currency}</span><span>{prices[prices.length - 1].date}</span></div></div>;
}

export default function InstrumentPage() {
  const params = useParams<{ id: string }>();
  const detail = useQuery({ queryKey: ["instrument", params.id], queryFn: () => getInstrument(params.id) });
  const history = useQuery({ queryKey: ["prices", params.id], queryFn: () => getPrices(params.id) });
  const sources = useQuery({ queryKey: ["data-sources"], queryFn: getSources });
  const prices = history.data?.prices ?? [];
  const latest = prices.at(-1);
  const source = sources.data?.find((item) => item.id === latest?.source_id);
  const ageDays = latest ? Math.max(0, Math.floor((Date.now() - new Date(`${latest.date}T00:00:00Z`).getTime()) / 86_400_000)) : null;

  return <main className="space-y-8 py-10">
    <Link href="/instruments" className="text-emerald-400 hover:underline">← Instrumente</Link>
    {detail.isPending && <p>Lade Instrument…</p>}
    {detail.isError && <p role="alert" className="text-rose-400">{detail.error.message}</p>}
    {detail.data && <>
      <header><h1 className="text-3xl font-semibold">{detail.data.name}</h1><p className="mt-2 text-zinc-400">{detail.data.active ? "Aktiv" : "Inaktiv"} · {detail.data.asset_type} · ID {detail.data.id}</p></header>
      <dl className="grid gap-4 rounded-xl border border-zinc-800 bg-zinc-900 p-6 sm:grid-cols-2">{([
        ["Ticker", detail.data.ticker], ["ISIN", detail.data.isin], ["FIGI", detail.data.figi],
        ["Börse", detail.data.exchange], ["MIC", detail.data.mic], ["Währung", detail.data.currency],
        ["Land", detail.data.country], ["Listung", detail.data.listed_at], ["Delisting", detail.data.delisted_at],
      ] as const).map(([label, value]) => <div key={label}><dt className="text-sm text-zinc-400">{label}</dt><dd>{value ?? "Nicht vorhanden"}</dd></div>)}</dl>
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6"><h2 className="text-xl font-semibold">Geprüfte Marktdaten</h2>
        {history.isPending && <p className="mt-4">Lade Kursdaten…</p>}
        {history.isError && <p role="alert" className="mt-4 text-rose-400">{history.error.message}</p>}
        {history.data?.status === "UNAVAILABLE" && <p className="mt-4 text-amber-400">Price data unavailable · {history.data.reason ?? "Keine geprüften Daten"}. <Link href="/imports" className="underline">CSV importieren</Link></p>}
        {latest && <><p className="mt-4 text-3xl font-semibold">{latest.close.toLocaleString("de-CH")} {latest.currency}</p><p className="mt-1 text-sm text-zinc-400">Schlusskurs vom {latest.date} · Quelle {source?.slug ?? latest.source_id} · Bekannt seit {new Date(latest.known_at).toLocaleString("de-CH")}</p><div className="mt-3 grid gap-2 text-sm sm:grid-cols-3"><p>Qualität: {latest.quality_label} ({Math.round(latest.quality_score * 100)} %)</p><p>Validierung: {latest.validation_status}</p><p>Alter: {ageDays} Kalendertage{ageDays !== null && ageDays > 7 ? " · ALT" : ""}</p></div><p className="mt-2 text-xs text-zinc-500">{latest.source_count} beobachtete Quelle(n) · Raw-ID {latest.raw_ingestion_id}</p><div className="mt-6"><PriceChart prices={prices} /></div><h3 className="mt-6 font-semibold">Letzte Schlusskurse</h3><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="text-zinc-400"><th className="pb-2">Datum</th><th className="pb-2">Close</th><th className="pb-2">Qualität</th><th className="pb-2">Quelle</th></tr></thead><tbody>{prices.slice(-20).reverse().map((item) => <tr key={item.id} className="border-t border-zinc-800"><td className="py-2">{item.date}</td><td>{item.close} {item.currency}</td><td>{item.quality_label}</td><td>{sources.data?.find((entry) => entry.id === item.source_id)?.slug ?? item.source_id}</td></tr>)}</tbody></table></div></>}
      </section>
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-6"><h2 className="text-xl font-semibold">Kennungshistorie</h2>{detail.data.identifiers.length === 0 ? <p className="mt-3 text-zinc-400">Keine Kennungen hinterlegt.</p> : <ul className="mt-4 space-y-3">{detail.data.identifiers.map((item) => <li key={item.id} className="rounded border border-zinc-700 p-3"><strong>{item.type}: {item.value}</strong><p className="text-sm text-zinc-400">Gültig ab {item.valid_from} bis {item.valid_to ?? "heute/offen"} · Beobachtet {new Date(item.observed_at).toLocaleString("de-CH")}</p><p className="break-all text-xs text-zinc-500">Quelle: {item.source_id ?? "manuell"} · Rohdaten: {item.raw_ingestion_id ?? "keine"}</p></li>)}</ul>}</section>
    </>}
  </main>;
}
