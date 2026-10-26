"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ColorType, createChart, LineSeries, LineStyle, type LineData, type Time, type WhitespaceData } from "lightweight-charts";
import { useTheme } from "./theme-provider";
import { Button, EmptyState } from "./primitives";
import { money, ratio } from "@/lib/portfolio-format";

export type ValuePoint = { date: string; value: string | null };

function cssColor(element: HTMLElement, variable: string): string {
  const probe = document.createElement("span");
  probe.style.color = `var(${variable})`;
  element.append(probe);
  const value = getComputedStyle(probe).color;
  probe.remove();
  return value;
}

export function ChartContainer({ title, points: allPoints, currency, description, action, pointsOnly = false, percentage = false, comparison }: { title: string; points: ValuePoint[]; currency: string; description: string; action?: ReactNode; pointsOnly?: boolean; percentage?: boolean; comparison?: { label: string; points: ValuePoint[] } }) {
  const [period, setPeriod] = useState("MAX");
  const [today] = useState(() => new Date().toISOString().slice(0, 10));
  const cutoff = new Date(`${today}T00:00:00Z`);
  if (period === "YTD") cutoff.setUTCMonth(0, 1);
  else cutoff.setUTCDate(cutoff.getUTCDate() - ({ "1W": 7, "1M": 30, "3M": 90, "1J": 365 }[period] ?? 0));
  const points = period === "MAX" ? allPoints : allPoints.filter(p => p.date >= cutoff.toISOString().slice(0, 10));
  const host = useRef<HTMLDivElement>(null);
  const { resolved: resolvedTheme } = useTheme();
  const valid = points.filter(p => p.value !== null && Number.isFinite(Number(p.value)));
  useEffect(() => {
    if (!host.current || valid.length < 2) return;
    const element = host.current;
    const color = (name: string) => cssColor(element, name);
    const chart = createChart(element, {
      autoSize: true, height: 280,
      layout: { background: { type: ColorType.Solid, color: color("--surface") }, textColor: color("--muted"), attributionLogo: true },
      grid: { vertLines: { visible: false }, horzLines: { color: color("--border") } },
      rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false, timeVisible: false },
      localization: { locale: "de-CH", priceFormatter: (value: number) => percentage ? ratio(String(value)) : money(String(value), currency) },
      handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
    });
    // Keep actual calendar/session gaps on the time axis without drawing a
    // continuous line. This series contains only the supplied observations.
    const axis = chart.addSeries(LineSeries, { lineVisible: false, pointMarkersVisible: false, crosshairMarkerVisible: false, priceLineVisible: false, lastValueVisible: false });
    axis.setData(points.map(p => p.value === null || !Number.isFinite(Number(p.value)) ? { time: p.date as Time } : { time: p.date as Time, value: Number(p.value) }));
    // Separate line series at every explicit unavailable point. Whitespace alone can
    // still visually connect a line in chart libraries, so never rely on that.
    const segments: (LineData<Time> | WhitespaceData<Time>)[][] = [[]];
    for (const point of points) {
      if (point.value === null || !Number.isFinite(Number(point.value))) { segments.push([]); continue; }
      segments[segments.length - 1].push({ time: point.date as Time, value: Number(point.value) });
    }
    for (const data of segments.filter(s => s.length)) {
      const series = chart.addSeries(LineSeries, { color: color("--accent"), lineWidth: 2, lineVisible: !pointsOnly, pointMarkersVisible: true, priceLineVisible: false, lastValueVisible: false });
      series.setData(data);
    }
    if (comparison) {
      const compared = period === "MAX" ? comparison.points : comparison.points.filter(p => p.date >= cutoff.toISOString().slice(0, 10));
      const segments: LineData<Time>[][] = [[]];
      for (const p of compared) {
        if (p.value === null || !Number.isFinite(Number(p.value))) segments.push([]);
        else segments[segments.length - 1].push({ time: p.date as Time, value: Number(p.value) });
      }
      for (const data of segments.filter(s => s.length)) {
        const line = chart.addSeries(LineSeries, { color: color("--warning"), lineStyle: LineStyle.Dashed, lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
        line.setData(data);
      }
    }
    chart.timeScale().fitContent();
    return () => chart.remove();
    // valid is derived from points; including it would recreate the chart every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, currency, resolvedTheme, pointsOnly, percentage, comparison, period]);
  return <section className="ui-panel space-y-4"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">{title}</h2>{action}</div>
    <div className="ui-chart-periods flex flex-wrap gap-2" role="group" aria-label={`Zeitraum: ${title}`}>{["1W", "1M", "3M", "1J", "YTD", "MAX"].map(p => <Button key={p} aria-pressed={period === p} onClick={() => setPeriod(p)}>{p}</Button>)}</div>
    {valid.length < 2 ? <EmptyState title="Noch keine Verlaufskurve" description="Mindestens zwei bewertbare Zeitpunkte im gewählten Zeitraum sind erforderlich. Fehlende Bewertungen werden nicht ergänzt." /> : <div ref={host} className="w-full min-w-0" role="img" aria-label={`${title}, ${currency}. Dieselben Werte stehen in der aufklappbaren Datentabelle.`} />}
    <p className="text-xs ui-muted">{description} MAX zeigt die gesamte übermittelte Historie; Zeiträume werden ab dem heutigen UTC-Datum gefiltert. Fehlende Historie bleibt fehlend.</p>
    {comparison && <p className="text-xs ui-muted">Durchgezogene Linie: Portfolio · Gestrichelte Linie: {comparison.label}. Gemeinsame Prozentachse und derselbe Ausgangspunkt.</p>}
    <details className="ui-details"><summary>Werte als zugängliche Tabelle anzeigen</summary><div className="max-h-80 overflow-auto mt-3"><table className="ui-table w-full"><caption className="sr-only">{title} in {currency}</caption><thead><tr><th scope="col">Datum</th><th scope="col">Wert</th>{comparison && <th scope="col">{comparison.label}</th>}</tr></thead><tbody>{points.map(p => <tr key={p.date}><th scope="row">{p.date}</th><td>{p.value === null ? "Nicht verfügbar" : percentage ? ratio(p.value) : money(p.value, currency)}</td>{comparison && <td>{comparison.points.find(c => c.date === p.date)?.value == null ? "Nicht verfügbar" : percentage ? ratio(comparison.points.find(c => c.date === p.date)!.value!) : money(comparison.points.find(c => c.date === p.date)!.value!, currency)}</td>}</tr>)}</tbody></table></div></details>
    <p className="text-xs ui-muted">Darstellung mit <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer" className="underline">TradingView Lightweight Charts™</a> · <a href="/third-party/lightweight-charts-NOTICE.txt" className="underline">Lizenzhinweis</a></p>
  </section>;
}
