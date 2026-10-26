"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Wallet, CircleDollarSign, ChartNoAxesCombined } from "lucide-react";
import { api } from "@/lib/api";
import { listPortfolios, listTransactions, getValuation, getPerformance, getAllocation } from "@/lib/api/portfolios";
import { PortfolioCard } from "@/components/portfolio-card";
import { AllocationChart, ValueChart } from "@/components/portfolio-charts";
import { PortfolioDataActions } from "@/components/portfolio-data-actions";
import { PositionHighlights } from "@/components/position-highlights";
import { HoldingsTable } from "@/components/holdings-table";
import { DataFreshness, EmptyState, ErrorState, FinancialMetric, LoadingSkeleton, PageHeader, StatusIndicator, SummaryCard } from "@/components/ui/primitives";

type Group = { base_currency: string; status: string; total_value_base: string | null; known_value_base: string; cash_value_base: string | null; daily_change_base: string | null; total_return_base: string | null; ytd_return_base: string | null };
type Dashboard = { groups: Group[]; chf_summary?: Group | null; as_of?: string };
type Notice = { id: string; read_at: string | null; payload: { title: string; url: string } };

export default function DashboardPage() {
  const router = useRouter();
  const [selection, setSelection] = useState("");
  const [end] = useState(() => new Date().toISOString().slice(0, 10));
  const [start] = useState(() => new Date(Date.now() - 90 * 86400000).toISOString().slice(0, 10));
  const portfolios = useQuery({ queryKey: ["portfolios"], queryFn: listPortfolios });
  const dashboard = useQuery({ queryKey: ["portfolio-dashboard"], queryFn: () => api<Dashboard>("/portfolio-dashboard") });
  const selected = portfolios.data?.find(p => p.id === selection) ?? portfolios.data?.[0];
  const id = selected?.id ?? "";
  const valuation = useQuery({ queryKey: ["valuation", id], queryFn: () => getValuation(id), enabled: !!id });
  const transactions = useQuery({ queryKey: ["transactions", id], queryFn: () => listTransactions(id), enabled: !!id });
  const allocation = useQuery({ queryKey: ["allocation", id], queryFn: () => getAllocation(id), enabled: !!id });
  const firstBooking = transactions.data?.filter(t => t.status === "ACTIVE").map(t => t.trade_date).sort()[0];
  const historyStart = firstBooking && firstBooking > start ? firstBooking : start;
  const performance = useQuery({ queryKey: ["performance", id, historyStart, end], queryFn: () => getPerformance(id, historyStart, end), enabled: !!id && !!firstBooking });
  const notices = useQuery({ queryKey: ["notifications"], queryFn: () => api<{ items: Notice[]; unread_count: number }>("/notifications") });
  const chf = dashboard.data?.chf_summary;
  const recent = [...(transactions.data ?? [])].sort((a, b) => b.trade_date.localeCompare(a.trade_date)).slice(0, 6);
  return <main className="space-y-8">
    <PageHeader title="Ihr Vermögen im Blick" description="Nachvollziehbare Bewertungen, Ihre letzten Buchungen und die nächsten Schritte." action={<Link className="ui-button ui-button-primary" href="/portfolios/new">Portfolio einrichten<ArrowUpRight size={16} /></Link>} />
    {dashboard.isPending && <LoadingSkeleton label="Gesamtbewertung wird geladen" />}
    {dashboard.isError && <ErrorState error={dashboard.error} retry={() => { void dashboard.refetch(); }} />}
    {chf && <><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <SummaryCard title="Gesamtvermögen in CHF" value={<FinancialMetric value={chf.total_value_base} />} detail={<StatusIndicator status={chf.status} />} icon={<Wallet size={18} className="ui-muted" />} />
      <SummaryCard title="Veränderung heute" value={<FinancialMetric value={chf.daily_change_base} semantic />} detail="In CHF, externe Geldeingänge und Auszahlungen herausgerechnet. Rendite vorläufig." icon={<ChartNoAxesCombined size={18} className="ui-muted" />} />
      <SummaryCard title="Gesamtertrag" value={<FinancialMetric value={chf.total_return_base} semantic />} detail="Ereignisbezogene FX-Umrechnung. Fehlender Einstand oder historische FX sperren den Ertrag." />
      <SummaryCard title="Verfügbarer Cashbestand" value={<FinancialMetric value={chf.cash_value_base} />} detail="Gebuchte Salden in CHF; keine Aussage zur sofortigen Verfügbarkeit beim Broker." icon={<CircleDollarSign size={18} className="ui-muted" />} />
    </div><DataFreshness date={dashboard.data?.as_of} source="Eigene Buchungen und geprüfte Kurse/FX" />{chf.status === "PARTIAL" && <EmptyState title="Die Gesamtbewertung ist unvollständig" description={<>Bekannter Teilwert: <FinancialMetric value={chf.known_value_base} />. Fehlende oder veraltete Kurse und Wechselkurse zuerst prüfen.</>} action={<Link className="ui-button" href="/data-quality">Datenprobleme ansehen</Link>} />}</>}
    {portfolios.isPending && <LoadingSkeleton />}{portfolios.isError && <ErrorState error={portfolios.error} />}
    {portfolios.data?.length === 0 && <EmptyState title="Willkommen in Ihrem Arbeitsbereich" description="Richten Sie Ihr erstes Portfolio ein. Eigene Buchungen und zulässige Dateien reichen für den Einstieg; externe Quellen können später freigegeben werden." action={<Link className="ui-button ui-button-primary" href="/portfolios/new">Erstes Portfolio einrichten</Link>} />}
    {!!portfolios.data?.length && <>
      <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-xl font-semibold">Ihr Depot im Detail</h2><p className="text-sm ui-muted">Verlauf und Positionen beziehen sich auf das ausgewählte Portfolio und dessen Basiswährung.</p></div><label className="grid gap-2 text-sm">Portfolio auswählen<select value={id} onChange={e => setSelection(e.target.value)}>{portfolios.data.map(p => <option key={p.id} value={p.id}>{p.name} · {p.base_currency}</option>)}</select></label></div>
      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]"><div>{(transactions.isPending || performance.isFetching) && <LoadingSkeleton label="Wertentwicklung wird geladen" />}{transactions.data && !firstBooking && <EmptyState title="Noch keine Wertentwicklung" description="Erfassen Sie zuerst belegte Buchungen oder einen Startbestand. Vor dem ersten bekannten Bestand wird keine Historie erfunden." />}{performance.isError && <ErrorState error={performance.error} />}{performance.data && <ValueChart series={performance.data.series} currency={selected!.base_currency} />}</div><div className="space-y-4">{allocation.data?.status === "AVAILABLE" ? <AllocationChart title="Vermögensaufteilung" currency={selected!.base_currency} items={(allocation.data.by_asset_type ?? []).map(i => ({ label: i.asset_type, value: i.value, weight: i.weight }))} /> : <EmptyState title="Aufteilung noch nicht verfügbar" description="Eine vollständige Bewertung und ein positiver Gesamtwert sind erforderlich." />}{allocation.isError && <ErrorState error={allocation.error} />}</div></div>
      {valuation.isError && <ErrorState error={valuation.error} />}{valuation.isPending && <LoadingSkeleton />}
      {valuation.data && <><section className="ui-panel space-y-5"><div className="flex items-center justify-between gap-4"><h2 className="text-xl font-semibold">Ihre Positionen</h2><Link href={`/portfolios/${id}?tab=Positionen`} className="ui-button">Depot öffnen</Link></div><HoldingsTable valuation={valuation.data} /></section><PositionHighlights valuation={valuation.data} /><PortfolioDataActions valuation={valuation.data} transactions={() => { router.push(`/portfolios/${id}?tab=Transaktionen`); }} /></>}
      <div className="grid gap-6 lg:grid-cols-2"><section className="ui-panel"><h2 className="text-xl font-semibold">Letzte Transaktionen</h2>{transactions.isError && <ErrorState error={transactions.error} />}{recent.length ? <ul className="mt-4 divide-y divide-zinc-800">{recent.map(t => <li key={t.id} className="py-3"><div className="flex justify-between gap-3"><span>{t.instrument_name ?? "Cash-Ereignis"}</span><FinancialMetric value={t.amount} currency={t.currency} /></div><p className="text-xs ui-muted">{t.trade_date} · {t.type} · {t.status}{t.quantity ? ` · ${t.quantity} Stück` : ""}</p></li>)}</ul> : <p className="mt-3 ui-muted">Noch keine Transaktionen.</p>}</section><section className="ui-panel"><h2 className="text-xl font-semibold">Ereignisse und Hinweise</h2>{notices.isError && <ErrorState error={notices.error} />}{notices.isPending && <LoadingSkeleton />}{notices.data?.items.length === 0 && <p className="mt-3 ui-muted">Keine archivierten Benachrichtigungen. Das bedeutet keine nachgewiesene Vollständigkeit aller Markttermine.</p>}<ul className="mt-4 space-y-3">{notices.data?.items.slice(0, 5).map(n => <li key={n.id}><Link className="underline" href={n.payload.url}>{n.payload.title}</Link><p className="text-xs ui-muted">{n.read_at ? "Gelesen" : "Ungelesen"}</p></li>)}</ul><Link href="/alerts" className="ui-button mt-4">Alle Benachrichtigungen</Link></section></div>
      <details className="ui-details"><summary>Alle Portfolios und Summen je Basiswährung</summary><p className="my-4 text-sm ui-muted">Renditen bleiben vorläufig, solange die Dividenden-/Split-Abdeckung ungeprüft ist. Gruppen verschiedener Währungen werden nicht unkonvertiert addiert.</p><ul className="grid gap-4 sm:grid-cols-2">{portfolios.data.map(p => <li key={p.id}><PortfolioCard portfolio={p} /></li>)}</ul></details>
    </>}
  </main>;
}
