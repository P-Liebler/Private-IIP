"use client";

import { ratio } from "@/lib/portfolio-format";
import { EmptyState } from "@/components/ui/primitives";

export function ForecastInterval({ low, expected, high }: { low: number | null; expected: number | null; high: number | null }) {
  if (low === null || expected === null || high === null || ![low, expected, high].every(Number.isFinite) || low > high) return <EmptyState title="Kein belastbares Prognoseintervall" description="Vollständige, geordnete Modellgrenzen und ein erwarteter Wert werden benötigt." />;
  const minimum = Math.min(low, expected, 0), maximum = Math.max(high, expected, 0), spread = maximum - minimum || 1;
  const x = (value: number) => (value - minimum) / spread * 100;
  return <figure className="ui-panel"><figcaption className="font-semibold">Prognostizierte relative Rendite zum Benchmark</figcaption><div className="relative mx-3 my-6 h-6" role="img" aria-label={`Untere Grenze ${ratio(String(low))}, Erwartungswert ${ratio(String(expected))}, obere Grenze ${ratio(String(high))}. Dieselben Werte folgen als Text.`}><span className="absolute top-3 h-px w-full bg-zinc-700" /><span className="absolute top-0 h-6 border-l border-dashed border-zinc-700" style={{ left: `${x(0)}%` }} /><span className="absolute top-2 h-2 rounded" style={{ left: `${x(low)}%`, width: `${x(high) - x(low)}%`, background: "var(--accent)" }} /><span className="absolute top-0 size-6 rounded-full border-4" style={{ left: `${x(expected)}%`, transform: "translateX(-50%)", background: "var(--surface)", borderColor: "var(--accent)" }} /></div><dl className="grid gap-3 sm:grid-cols-3"><div><dt className="text-xs ui-muted">Untere Grenze</dt><dd>{ratio(String(low))}</dd></div><div><dt className="text-xs ui-muted">Erwartungswert</dt><dd>{ratio(String(expected))}</dd></div><div><dt className="text-xs ui-muted">Obere Grenze</dt><dd>{ratio(String(high))}</dd></div></dl><p className="mt-3 text-xs ui-muted">Modellausgabe, kein garantierter Ertrag oder zukünftiger Kurs. Die Darstellung erzeugt keine zusätzliche Prognose.</p></figure>;
}
