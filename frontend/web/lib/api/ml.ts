import { api } from "@/lib/api";

export type Forecast = {
  id: string; generated_at: string; horizon: number; model_id: string | null;
  result: {
    confidence_status: string; reason: string | null;
    probability_outperform: number | null; expected_excess_return: number | null;
    lower_bound: number | null; upper_bound: number | null;
    uncertainty_method?: string; interval_level?: number; empirical_coverage?: number;
    explanations?: unknown[];
  };
  outcomes?: { id: string; result: { actual_excess_return: string; correct: boolean; evaluated_at: string } }[];
};
export type MLModel = {
  id: string; model_type: string; target_type: string; horizon: number; status: string;
  artifact_hash: string; mlflow_run_id: string | null;
  evaluation: Record<string, unknown>;
};
export type TrainingRun = { id: string; status: string; progress: number; current_stage: string; error_code: string | null };
export const getForecast = (id: string, horizon: number) => api<Forecast>(`/instruments/${id}/forecast?horizon=${horizon}`);
export const getPredictionHistory = (id: string, offset = 0) => api<Forecast[]>(`/instruments/${id}/prediction-history?offset=${offset}`);
export const getModels = () => api<MLModel[]>("/ml/models");
export const getTrainingRuns = () => api<TrainingRun[]>("/ml/training-runs");
