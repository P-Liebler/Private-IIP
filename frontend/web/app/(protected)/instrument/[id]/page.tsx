"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getInstrument } from "@/lib/api/market-foundation";

export default function InstrumentPage() {
  const params = useParams<{ id: string }>();
  const detail = useQuery({ queryKey: ["instrument", params.id], queryFn: () => getInstrument(params.id) });
  return <main className="py-10"><Link href="/instruments" className="text-emerald-400 hover:underline">← Instrumente</Link>
    {detail.isPending && <p className="mt-6">Lade Instrument…</p>}
    {detail.isError && <p role="alert" className="mt-6 text-rose-400">{detail.error.message}</p>}
    {detail.data && <><h1 className="mt-6 text-3xl font-semibold">{detail.data.name}</h1>
      <p className="mt-2 text-zinc-400">{detail.data.active ? "Aktiv" : "Inaktiv"} · {detail.data.asset_type} · ID {detail.data.id}</p>
      <dl className="mt-6 grid gap-4 rounded-xl border border-zinc-800 bg-zinc-900 p-6 sm:grid-cols-2">{([
        ["Ticker", detail.data.ticker], ["ISIN", detail.data.isin], ["FIGI", detail.data.figi],
        ["Börse", detail.data.exchange], ["MIC", detail.data.mic], ["Währung", detail.data.currency],
        ["Land", detail.data.country], ["Listung", detail.data.listed_at], ["Delisting", detail.data.delisted_at],
      ] as const).map(([label, value]) => <div key={label}><dt className="text-sm text-zinc-400">{label}</dt><dd>{value ?? "Nicht vorhanden"}</dd></div>)}</dl>
      <section className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900 p-6"><h2 className="text-xl font-semibold">Kennungshistorie</h2>
        {detail.data.identifiers.length === 0 ? <p className="mt-3 text-zinc-400">Keine Kennungen hinterlegt.</p> : <ul className="mt-4 space-y-3">{detail.data.identifiers.map((item) => <li key={item.id} className="rounded border border-zinc-700 p-3"><strong>{item.type}: {item.value}</strong><p className="text-sm text-zinc-400">Gültig ab {item.valid_from} bis {item.valid_to ?? "heute/offen"} · Beobachtet {new Date(item.observed_at).toLocaleString("de-CH")}</p><p className="break-all text-xs text-zinc-500">Quelle: {item.source_id ?? "manuell"} · Rohdaten: {item.raw_ingestion_id ?? "keine"}</p></li>)}</ul>}
      </section></>}
  </main>;
}
