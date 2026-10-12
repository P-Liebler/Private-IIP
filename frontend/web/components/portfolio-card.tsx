"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getSummary, getAllocation, type Portfolio } from "@/lib/api/portfolios";
import { money } from "@/lib/portfolio-format";
import { AllocationChart } from "@/components/portfolio-charts";

export function PortfolioCard({ portfolio, showAllocation = false }: { portfolio: Portfolio; showAllocation?: boolean }) {
  const query = useQuery({ queryKey: ["summary", portfolio.id], queryFn: () => getSummary(portfolio.id) });
  const data = query.data, value = data?.valuation;
  const allocation = useQuery({ queryKey: ["allocation", portfolio.id], queryFn: () => getAllocation(portfolio.id), enabled: showAllocation });
  return <article className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
    <Link href={`/portfolios/${portfolio.id}`} className="text-xl font-semibold text-emerald-400 underline">{portfolio.name}</Link>
    <p className="mt-2 text-sm text-zinc-400">Basiswährung: {portfolio.base_currency}</p>
    {query.isPending && <p>Bewertung wird geladen…</p>}
    {query.isError && <p role="alert" className="text-rose-400">{query.error.message}</p>}
    {data && value && <><p className="mt-3 text-2xl">{money(value.total_value_base, portfolio.base_currency)}</p>
      <p>Status: {value.status} · Renditen: {data.return_status}</p>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">{[["Tagesertrag", data.daily_change_base], ["Gesamtertrag", data.total_return_base], ["YTD-Ertrag", data.ytd_return_base], ["Cash", value.cash_value_base]].map(([label, amount]) => <div key={label}><dt className="text-zinc-400">{label}</dt><dd>{money(amount, portfolio.base_currency)}</dd></div>)}</dl>
      <p className="mt-3 text-sm text-zinc-400">Kursaltersangaben: {value.holdings.map(item => `${item.name}: ${item.price_age_days ?? "DATA_UNAVAILABLE"} Tage`).join(" · ") || "Keine offenen Positionen"}</p>
      {value.issues.length > 0 && <p className="mt-2 text-sm text-amber-400">Bekannter Teilwert: {money(value.known_value_base, portfolio.base_currency)} · {value.issues.map(issue => issue.code).join(", ")}</p>}
    </>}
    {showAllocation && allocation.data?.status === "AVAILABLE" && <div className="mt-4"><AllocationChart title="Allokation nach Anlageklasse" currency={portfolio.base_currency} items={(allocation.data.by_asset_type ?? []).map(item => ({ label: item.asset_type, value: item.value, weight: item.weight }))} /></div>}
    {showAllocation && allocation.isError && <p role="alert">{allocation.error.message}</p>}
  </article>;
}
