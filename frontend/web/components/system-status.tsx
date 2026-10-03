"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api/health";

const services = [
  { key: "api", label: "API" },
  { key: "database", label: "PostgreSQL" },
  { key: "valkey", label: "Valkey" },
  { key: "minio", label: "MinIO" },
] as const;

export function SystemStatus() {
  const query = useQuery({
    queryKey: ["system-health"],
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: 10_000,
  });

  return (
    <section aria-labelledby="system-status-heading" className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-6 shadow-xl shadow-black/10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="system-status-heading" className="text-lg font-semibold text-zinc-50">System status</h2>
          <p className="mt-1 text-sm text-zinc-400">Live checks from the local API. Updated every 10 seconds.</p>
        </div>
        <button className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-200 transition hover:border-zinc-500 disabled:opacity-50" onClick={() => void query.refetch()} disabled={query.isFetching} type="button">
          {query.isFetching ? "Checking…" : "Refresh"}
        </button>
      </div>
      {query.isError && <p role="alert" className="mt-5 rounded-lg border border-rose-900/70 bg-rose-950/40 p-3 text-sm text-rose-200">API unavailable or returned an invalid response. No status has been assumed.</p>}
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {services.map((service) => {
          const state = service.key === "api"
            ? query.isSuccess ? "ok" : query.isPending ? "checking" : "unavailable"
            : query.isSuccess
              ? query.data.services[service.key] ?? "unavailable"
              : query.isPending ? "checking" : "unavailable";
          const healthy = state === "ok";
          return (
            <div key={service.key} className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-950/60 px-4 py-3">
              <span className="text-sm font-medium text-zinc-200">{service.label}</span>
              <span className={`inline-flex items-center gap-2 text-xs font-medium ${healthy ? "text-emerald-300" : state === "checking" ? "text-amber-300" : "text-rose-300"}`}>
                <span aria-hidden="true" className={`size-2 rounded-full ${healthy ? "bg-emerald-400" : state === "checking" ? "bg-amber-400" : "bg-rose-400"}`} />
                {state === "ok" ? "Healthy" : state === "checking" ? "Checking" : "Unavailable"}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
