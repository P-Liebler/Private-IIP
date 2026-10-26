"use client";
import { useQuery } from "@tanstack/react-query";
import { listDatasets } from "@/lib/api/pit";
export function DatasetQualityPanel() {
  const query = useQuery({ queryKey: ["datasets"], queryFn: listDatasets });
  return <section className="space-y-3 rounded border border-zinc-800 p-5"><h2 className="text-xl">PIT Dataset-Qualität</h2>
    {query.isError && <p role="alert">{query.error.message}</p>}
    {query.data?.length === 0 && <p>Keine historischen Datasets vorhanden.</p>}
    {query.data?.map(d => <article key={d.id}><h3>{d.id.slice(0, 8)} · {d.configuration.availability_mode ?? "Verfügbarkeitsmodus nicht archiviert"}</h3><p>{d.quality.valid_observations ?? "Nicht archiviert"} gültig / {d.quality.total_observations ?? "Nicht archiviert"} · {d.quality.excluded_observations ?? "Nicht archiviert"} ausgeschlossen · {d.quality.missing_features ?? "Nicht archiviert"} fehlende Features · {d.quality.unavailable_targets ?? "Nicht archiviert"} fehlende Labels</p>{d.quality.survivorship_risk && <p className="text-amber-400">SURVIVORSHIP_BIAS_RISK / HISTORICAL_AVAILABILITY_UNVERIFIED</p>}{d.quality.exclusion_reasons ? <ul>{Object.entries(d.quality.exclusion_reasons).map(([reason, count]) => <li key={reason}>{reason}: {count}</li>)}</ul> : <p className="text-amber-400">Detaillierte Ausschlussgründe wurden für diese Datasetversion nicht archiviert. Fehlende Angaben sind kein Nachweis vollständiger Daten.</p>}</article>)}
  </section>;
}
