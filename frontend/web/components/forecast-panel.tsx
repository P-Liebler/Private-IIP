"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getForecast, getPredictionHistory } from "@/lib/api/ml";

const percent = (value: number | null) => value === null ? "Nicht verfügbar" : `${(value * 100).toFixed(1)} %`;

export function ForecastPanel({ instrumentId }: { instrumentId: string }) {
  const [horizon, setHorizon] = useState(30);
  const [historyOffset, setHistoryOffset] = useState(0);
  const forecast = useQuery({ queryKey: ["forecast", instrumentId, horizon], queryFn: () => getForecast(instrumentId, horizon) });
  const history = useQuery({ queryKey: ["prediction-history", instrumentId, forecast.data?.id, historyOffset], queryFn: () => getPredictionHistory(instrumentId, historyOffset) });
  const result = forecast.data?.result;
  return <section className="space-y-5 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
    <header className="flex items-center justify-between"><h2 className="text-xl font-semibold">Forecast</h2><label>Horizont <select aria-label="Forecast-Horizont" value={horizon} onChange={event => setHorizon(Number(event.target.value))} className="ml-2 rounded bg-zinc-950 p-2"><option value={30}>30 Handelssitzungen</option><option value={90}>90 Handelssitzungen</option></select></label></header>
    {forecast.isPending && <p>Lade Prognosestatus…</p>}
    {forecast.isError && <p role="alert">{forecast.error.message}</p>}
    {result && result.confidence_status !== "VALIDATED" && <div className="rounded border border-amber-700 p-4"><p className="font-semibold text-amber-300">NO RELIABLE FORECAST</p><p>{result.reason}</p><p className="mt-2 text-sm text-zinc-400">Für diesen Horizont liegt keine freigegebene, zuverlässig geprüfte Prognose vor.</p></div>}
    {result?.confidence_status === "VALIDATED" && <dl className="grid gap-4 sm:grid-cols-2"><div><dt>Outperformance-Wahrscheinlichkeit</dt><dd>{percent(result.probability_outperform)}</dd></div><div><dt>Erwartete Excess-Rendite</dt><dd>{percent(result.expected_excess_return)}</dd></div><div><dt>Prognoseintervall</dt><dd>{percent(result.lower_bound)} bis {percent(result.upper_bound)}</dd></div><div><dt>Methode / geprüfte Coverage</dt><dd>{result.uncertainty_method} / {percent(result.empirical_coverage ?? null)}</dd></div></dl>}
    {forecast.data && <p className="text-xs text-zinc-400">Erzeugt: {new Date(forecast.data.generated_at).toLocaleString("de-CH")} · Modell: {forecast.data.model_id ?? "Kein freigegebenes Modell"}</p>}
    <h3 className="font-semibold">Model Explanation</h3>
    {result?.explanations?.length ? <pre className="overflow-auto text-xs">{JSON.stringify(result.explanations, null, 2)}</pre> : <p className="text-sm text-zinc-400">Ohne freigegebene Prognose keine Modellfaktoren.</p>}
    <h3 className="font-semibold">Prediction History</h3>
    <div className="flex gap-4 text-sm"><button disabled={historyOffset === 0} onClick={() => setHistoryOffset(Math.max(0, historyOffset - 100))}>Neuere Prognosen</button><button disabled={(history.data?.length ?? 0) < 100} onClick={() => setHistoryOffset(historyOffset + 100)}>Ältere Prognosen</button></div>
    {history.isError && <p role="alert">{history.error.message}</p>}
    <div className="overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th>Erzeugt</th><th>Horizont</th><th>Status</th><th>Prognose</th><th>Realisierte Excess-Rendite</th></tr></thead><tbody>{history.data?.map(row => <tr key={row.id} className="border-t border-zinc-800"><td className="py-3">{new Date(row.generated_at).toLocaleString("de-CH")}</td><td>{row.horizon}</td><td>{row.result.confidence_status}</td><td>{percent(row.result.expected_excess_return)}</td><td>{row.outcomes?.length ? percent(Number(row.outcomes.at(-1)!.result.actual_excess_return)) : "Noch nicht verfügbar"}</td></tr>)}</tbody></table></div>
  </section>;
}
