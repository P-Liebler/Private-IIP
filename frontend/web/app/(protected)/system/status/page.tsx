"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Run = { status: string; completed_at: string | null; age_seconds?: number };
type Status = {
  application_version: string; code_commit: string; environment: string; status: string;
  services: Record<string, string>; backup: Run; last_successful_backup: Run; restore_test: Run;
  data_collection_enabled: boolean; forward_shadow_enabled: boolean;
  decisions: Record<string, string>; operator_evidence: Record<string, string>;
};

export default function SystemStatusPage() {
  const query = useQuery({ queryKey: ["system-status"], queryFn: () => api<Status>("/system/status"), retry: false, refetchInterval: 60000 });
  const data = query.data;
  return <main className="space-y-6 py-10">
    <h1 className="text-3xl font-semibold">Systemstatus</h1>
    <p>Geschützte Betriebsansicht für ausdrücklich autorisierte Operatoren.</p>
    {query.isPending && <p>Status wird geprüft…</p>}
    {query.isError && <p role="alert">{query.error.message}</p>}
    {data && <>
      <p>Version {data.application_version} · {data.environment} · {data.status}</p>
      <p className="break-all">Code: {data.code_commit}</p>
      <section><h2 className="text-xl">Dienste</h2><dl>{Object.entries(data.services).map(([name, status]) => <div key={name} className="flex gap-4"><dt>{name}</dt><dd>{status}</dd></div>)}</dl></section>
      <section><h2 className="text-xl">Backup und Restore</h2>{([ ["Letzter Backupversuch", data.backup], ["Letztes erfolgreiches Backup", data.last_successful_backup], ["Letzter Restore-Test", data.restore_test] ] as [string, Run][]).map(([name, run]) => <p key={name}>{name}: {run.status} · {run.completed_at ? new Date(run.completed_at).toLocaleString("de-CH") : "Kein Nachweis"}{run.age_seconds !== undefined && ` · Alter ${Math.floor(run.age_seconds / 3600)} Stunden`}</p>)}</section>
      <p>Datensammlung: {data.data_collection_enabled ? "Aktiviert" : "Deaktiviert"} · Forward Shadow: {data.forward_shadow_enabled ? "Aktiviert" : "Deaktiviert"}</p>
      <section><h2 className="text-xl">Getrennte Freigaben</h2><ul>{Object.values(data.decisions).map(value => <li key={value}>{value}</li>)}</ul></section>
      <section><h2 className="text-xl">Offene Operatornachweise</h2><ul className="text-amber-300">{Object.entries(data.operator_evidence).map(([key, value]) => <li key={key}>{key}: {value}</li>)}</ul><p>Ein lokaler Backup-Ordner belegt kein unabhängiges Backupziel. Zielhost-, Client- und Zustellnachweise werden im Abnahmeprotokoll geführt.</p></section>
      <Link href="/data-quality" className="text-emerald-400 underline">Datenqualität und Herkunft prüfen</Link>
    </>}
  </main>;
}
