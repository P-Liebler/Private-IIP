import { money, ratio } from "@/lib/portfolio-format";

export function ValueChart({ series, currency }: { series: { date: string; value_base: string | null }[]; currency: string }) {
  const values = series.filter(point => point.value_base !== null).map(point => Number(point.value_base));
  if (values.length < 2) return <p>Chart DATA_UNAVAILABLE: mindestens zwei bewertbare Zeitpunkte erforderlich.</p>;
  const low = Math.min(...values), high = Math.max(...values), spread = high - low || 1;
  const points = series.map((point, index) => point.value_base === null ? null :
    `${20 + index * 560 / Math.max(1, series.length - 1)},${180 - (Number(point.value_base) - low) / spread * 150}`);
  // Break the line at missing data instead of connecting across unavailable intervals.
  const segments: string[][] = [[]];
  for (const point of points) { if (point === null) segments.push([]); else segments[segments.length - 1].push(point); }
  return <figure><svg role="img" aria-label={`Portfoliowert in ${currency}`} viewBox="0 0 600 210" className="w-full rounded bg-zinc-950">
    {segments.map((segment, index) => <polyline key={index} points={segment.join(" ")} fill="none" stroke="#34d399" strokeWidth="2" />)}
    <text x="20" y="15" fill="#a1a1aa" fontSize="12">{money(String(high), currency)}</text>
    <text x="20" y="205" fill="#a1a1aa" fontSize="12">{series[0].date}</text>
    <text x="480" y="205" fill="#a1a1aa" fontSize="12">{series[series.length - 1].date}</text>
  </svg><figcaption className="text-sm text-zinc-400">Lücken entsprechen fehlenden Bewertungen.</figcaption></figure>;
}

export function AllocationChart({ title, items, currency }: { title: string;
  items: { label: string; weight: string; value: string }[]; currency: string }) {
  return <section className="rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">{title}</h2><ul className="mt-3 space-y-3">{items.map((item, index) => <li key={index}>
    <div className="flex justify-between gap-3 text-sm"><span>{item.label}</span><span>{ratio(item.weight)} · {money(item.value, currency)}</span></div>
    <div className="mt-1 h-2 rounded bg-zinc-800"><div className={`h-2 rounded ${Number(item.weight) < 0 ? "bg-rose-400" : "bg-emerald-400"}`} style={{ width: `${Math.min(100, Math.abs(Number(item.weight)) * 100)}%` }} /></div>
  </li>)}</ul><p className="mt-3 text-xs text-zinc-400">Negative Cash-Bestände erscheinen als negative Gewichte.</p></section>;
}
