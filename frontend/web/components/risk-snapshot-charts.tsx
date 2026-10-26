"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ChartContainer, type ValuePoint } from "@/components/ui/chart-container";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/primitives";

type ChartData = { status: string; reason: string | null; snapshot_content_hash: string; as_of: string; calculation_version: string; derived_content_hash?: string; returns: ValuePoint[]; drawdown: ValuePoint[]; benchmark: ValuePoint[]; benchmark_status: string };

export function RiskSnapshotCharts({ portfolioId, snapshotId, benchmarkName }: { portfolioId: string; snapshotId: string; benchmarkName?: string }) {
  const query = useQuery({ queryKey: ["risk-charts", portfolioId, snapshotId], queryFn: () => api<ChartData>(`/portfolios/${portfolioId}/risk/${snapshotId}/charts`) });
  if (query.isPending) return <LoadingSkeleton label="Archivierte Renditebeobachtungen werden aufbereitet" />;
  if (query.isError) return <ErrorState error={query.error} retry={() => { void query.refetch(); }} />;
  const data = query.data;
  if (data.status !== "AVAILABLE") return <EmptyState title="Für diese Verlaufskurven fehlen geprüfte Daten" description={<>Eine vollständige Renditereihe mit bestätigter Kurs-, FX- und Dividenden-/Split-Abdeckung ist erforderlich. Keine Lücke wird als Nullrendite ergänzt. <span className="block text-xs mt-2">Prüfgrund: {data.reason}</span></>} />;
  return <div className="space-y-5"><ChartContainer title="Renditeverlauf und Benchmark" currency="%" percentage points={data.returns} comparison={data.benchmark_status === "AVAILABLE" ? { label: benchmarkName ?? "Gespeicherter Benchmark", points: data.benchmark } : undefined} description={`Kumulierte, um externe Geldflüsse bereinigte Rendite ab dem ersten gespeicherten Bewertungszeitpunkt. Fester Wissensstand: ${data.as_of}.`} />
    {data.benchmark_status !== "AVAILABLE" && <p className="text-sm ui-muted">Kein vollständig gedeckter, zeitlich passender Benchmarkvergleich verfügbar. Es wird keine Nullrendite als Vergleich eingesetzt.</p>}
    <ChartContainer title="Rückgang vom bisherigen Höchststand" currency="%" percentage points={data.drawdown} description="Drawdown der geldflussbereinigten Reihe relativ zum jeweils zuvor erreichten Hoch. Keine Verlustgarantie; bei negativem Eigenkapital sind Verluste über 100 % möglich." />
    <details className="ui-details"><summary>Berechnung und unveränderlicher Datenstand</summary><dl className="text-xs break-all space-y-2 mt-3"><div><dt>Regel</dt><dd>{data.calculation_version}</dd></div><div><dt>Risiko-Snapshot</dt><dd>{data.snapshot_content_hash}</dd></div><div><dt>Abgeleitete Darstellung</dt><dd>{data.derived_content_hash}</dd></div></dl></details>
  </div>;
}
