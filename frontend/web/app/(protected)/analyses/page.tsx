"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listPortfolios } from "@/lib/api/portfolios";
import { ActionList, EmptyState, ErrorState, LoadingSkeleton, PageHeader } from "@/components/ui/primitives";

export default function AnalysesPage() {
  const portfolios = useQuery({ queryKey: ["portfolios"], queryFn: listPortfolios });
  const [selection, setSelection] = useState("");
  const id = portfolios.data?.find(p => p.id === selection)?.id ?? portfolios.data?.[0]?.id;
  return <main className="space-y-8"><PageHeader title="Ihr Portfolio verstehen" description="Mit dem tatsächlichen Depot beginnen: Risiken prüfen, Szenarien vergleichen und Annahmen nachvollziehen." />
    <section className="ui-panel space-y-5"><h2 className="text-xl font-semibold">Risiko und Szenarien</h2><p className="text-sm ui-muted">Diese Analysen verwenden Ihre Buchungen und belegte Kurse/FX. Fehlende Handelstage oder ungeprüfte Dividenden-/Split-Abdeckung können einzelne Kennzahlen sperren.</p>
      {portfolios.isPending && <LoadingSkeleton />}{portfolios.isError && <ErrorState error={portfolios.error} />}
      {id ? <><label className="grid gap-2 max-w-xl">Portfolio<select value={id} onChange={e => setSelection(e.target.value)}>{portfolios.data?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><ActionList actions={[
        { label: "Risiken einschätzen", description: "Schwankungen, Verluste und Konzentration mit ihren Datengrenzen.", href: `/portfolios/${id}?tab=Risiko` },
        { label: "Szenarien vergleichen", description: "Mögliche Veränderungen und historische Stressphasen nachvollziehen.", href: `/portfolios/${id}?tab=Szenarien` },
        { label: "Portfolioänderung simulieren", description: "Was wäre wenn — ohne eine Buchung oder einen Auftrag auszulösen.", href: `/portfolios/${id}?tab=What-if` },
      ]} /></> : portfolios.data && <EmptyState title="Zuerst ein Portfolio einrichten" description="Für Ihre persönliche Risikoanalyse wird ein eigenes Depot benötigt." action={<Link className="ui-button" href="/portfolios/new">Portfolio einrichten</Link>} />}
    </section>
    <section className="ui-panel"><h2 className="text-xl font-semibold">Experimente und historische Vergleiche</h2><p className="mt-3 text-sm ui-muted">Ein technischer Test ist keine validierte Prognose oder Anlageempfehlung. Freigaben und historische Verfügbarkeit werden je Ergebnis geprüft.</p><ActionList actions={[
      { label: "Historische Vergleiche", description: "Datensätze und einfache Strategien mit damals verfügbaren Informationen prüfen.", href: "/backtests" },
      { label: "Modelle und Prognosen", description: "Registrierte Modelle, archivierte Ergebnisse und ihre Grenzen.", href: "/models" },
      { label: "Portfolioentscheidungen", description: "Strukturierte Prüfungen; ohne zugelassene Prognose und Strategie bleibt eine Enthaltung.", href: "/recommendations" },
    ]} /></section>
  </main>;
}
