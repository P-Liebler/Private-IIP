"use client";

import { useQuery } from "@tanstack/react-query";
import { getModels, getTrainingRuns } from "@/lib/api/ml";
import { api } from "@/lib/api";
import { ValidationLinks } from "@/components/validation-workbench";
import { useState } from "react";

export default function ModelsPage() {
  const models = useQuery({ queryKey: ["ml-models"], queryFn: getModels });
  const runs = useQuery({ queryKey: ["ml-training-runs"], queryFn: getTrainingRuns, refetchInterval: 10000 });
  const [datasetId, setDatasetId] = useState("");
  const [readiness, setReadiness] = useState<unknown>(null);
  const [error, setError] = useState("");
  async function audit() {
    setError("");
    try { setReadiness(await api(`/ml/datasets/readiness?dataset_id=${encodeURIComponent(datasetId)}&required_features=momentum_20d&required_features=volatility_20`)); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Prüfung fehlgeschlagen"); }
  }
  return <main className="space-y-6 py-10"><ValidationLinks /><h1 className="text-3xl font-semibold">ML-Modelle</h1><p className="text-zinc-400">Experimentelle Modelle und technische Tests begründen keine produktive Prognosefreigabe.</p>
    <section className="rounded-xl border border-zinc-800 p-6"><h2 className="text-xl font-semibold">Data readiness</h2><label className="mt-3 block">Dataset-ID <input value={datasetId} onChange={event => setDatasetId(event.target.value)} className="ml-2 rounded bg-zinc-900 p-2" /></label><button onClick={audit} disabled={!datasetId} className="mt-3 rounded border border-zinc-600 px-3 py-2">Datenbereitschaft prüfen</button>{error && <p role="alert">{error}</p>}{readiness !== null && <pre className="mt-4 overflow-auto text-xs">{JSON.stringify(readiness, null, 2)}</pre>}</section>
    <section><h2 className="text-xl font-semibold">Training runs</h2>{runs.isError && <p role="alert">{runs.error.message}</p>}{runs.data?.length === 0 && <p>Keine Trainingsläufe.</p>}{runs.data?.map(run => <p key={run.id} className="mt-3 rounded border border-zinc-800 p-3">{run.status} · {run.current_stage} · {run.progress} % · {run.error_code ?? run.id}</p>)}</section>
    <section><h2 className="text-xl font-semibold">Registered models</h2>{models.isError && <p role="alert">{models.error.message}</p>}{models.data?.length === 0 && <p>Keine registrierten Modelle. NO RELIABLE FORECAST.</p>}{models.data?.map(model => <article key={model.id} className="mt-4 rounded border border-zinc-800 p-5"><h3>{model.model_type} · {model.target_type} · {model.horizon} Sitzungen · {model.status}</h3><p className="mt-2 break-all text-xs">SHA-256: {model.artifact_hash}</p><details className="mt-3"><summary>Validation, OOS, Calibration und Intervalle</summary><pre className="overflow-auto text-xs">{JSON.stringify(model.evaluation, null, 2)}</pre></details></article>)}</section>
  </main>;
}
