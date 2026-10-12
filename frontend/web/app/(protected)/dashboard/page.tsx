"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { listPortfolios } from "@/lib/api/portfolios";
import { money } from "@/lib/portfolio-format";
import { PortfolioCard } from "@/components/portfolio-card";

type Group = { base_currency: string; status: string; total_value_base: string | null;
  known_value_base: string; cash_value_base: string | null; daily_change_base: string | null;
  total_return_base: string | null; ytd_return_base: string | null };

export default function DashboardPage() {
  const portfolios = useQuery({ queryKey: ["portfolios"], queryFn: listPortfolios });
  const dashboard = useQuery({ queryKey: ["portfolio-dashboard"], queryFn: () => api<{ groups: Group[] }>("/portfolio-dashboard") });
  return <main className="space-y-8 py-10">
    <header><h1 className="text-3xl font-semibold">Übersicht</h1><p className="mt-2 text-zinc-400">Ihre Portfolios und die Verfügbarkeit ihrer aktuellen Bewertung.</p></header>
    <Link href="/portfolios" className="inline-block rounded border border-emerald-500 px-4 py-2 text-emerald-400">Portfolios verwalten</Link>
    <p className="text-sm text-zinc-400">Summen je Basiswährung; Erträge sind vorläufig, solange die Corporate-Action-Abdeckung ungeprüft ist.</p>
    {dashboard.isError && <p role="alert">{dashboard.error.message}</p>}
    {dashboard.data?.groups.map(group => <section key={group.base_currency} className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Gesamt · {group.base_currency} · {group.status}</h2>
      <dl className="mt-4 grid gap-4 sm:grid-cols-3">{[["Portfoliowert", group.total_value_base], ["Tagesertrag", group.daily_change_base], ["Gesamtertrag", group.total_return_base], ["YTD-Ertrag", group.ytd_return_base], ["Cash", group.cash_value_base]].map(([label, value]) => <div key={label}><dt className="text-sm text-zinc-400">{label}</dt><dd className="text-xl">{money(value, group.base_currency)}</dd></div>)}</dl>
      {group.status === "PARTIAL" && <p className="mt-3 text-amber-400">Bekannter Teilwert: {money(group.known_value_base, group.base_currency)}</p>}
    </section>)}
    {portfolios.isPending && <p>Lade Portfolios…</p>}
    {portfolios.isError && <p role="alert" className="text-rose-400">{portfolios.error.message}</p>}
    {portfolios.data?.length === 0 && <p>Noch kein Portfolio vorhanden. Legen Sie eines an und erfassen Sie zuerst ein Konto und Transaktionen.</p>}
    <ul className="grid gap-4 sm:grid-cols-2">{portfolios.data?.map(portfolio => <li key={portfolio.id}><PortfolioCard portfolio={portfolio} showAllocation /></li>)}</ul>
  </main>;
}
