"use client";

import { ChartContainer } from "@/components/ui/chart-container";
import { money, ratio } from "@/lib/portfolio-format";

export function ValueChart({ series, currency }: { series: { date: string; value_base: string | null }[]; currency: string }) {
  return <ChartContainer title="Portfoliowert" currency={currency} points={series.map(p => ({ date: p.date, value: p.value_base }))} description="Aus dem aktuellen Ledger rückgerechnete Bewertungszeitpunkte, kein Nachweis damals lokal archivierter Depotwerte. Fehlende Bewertungen unterbrechen die Kurve; keine interpolierten Werte." />;
}

export function AllocationChart({ title, items, currency }: { title: string;
  items: { label: string; weight: string; value: string }[]; currency: string }) {
  return <section className="rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">{title}</h2><ul className="mt-3 space-y-3">{items.map((item, index) => <li key={index}>
    <div className="flex justify-between gap-3 text-sm"><span>{item.label}</span><span>{ratio(item.weight)} · {money(item.value, currency)}</span></div>
    <div className="mt-1 h-2 rounded bg-zinc-800"><div className={`h-2 rounded ${Number(item.weight) < 0 ? "bg-rose-400" : "bg-emerald-400"}`} style={{ width: `${Math.min(100, Math.abs(Number(item.weight)) * 100)}%` }} /></div>
  </li>)}</ul><p className="mt-3 text-xs text-zinc-400">Negative Cash-Bestände erscheinen als negative Gewichte.</p></section>;
}
