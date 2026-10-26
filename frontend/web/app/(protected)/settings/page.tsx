"use client";

import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Settings } from "@/lib/api";
import { sessionQueryKey, useSession } from "@/lib/auth";
import { ThemeSwitcher } from "@/components/ui/theme-provider";

type TotpSetup = { secret: string; provisioning_uri: string };

function SettingsForm({ initial, onNotice, onError }: {
  initial: Settings; onNotice: (message: string) => void; onError: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const [timezone, setTimezone] = useState(initial.timezone);
  const [currency, setCurrency] = useState(initial.base_currency);
  const save = useMutation({
    mutationFn: () => api<Settings>("/settings", {
      method: "PATCH", body: JSON.stringify({ timezone, base_currency: currency.toUpperCase() }),
    }),
    onSuccess: async () => { onNotice("Einstellungen gespeichert."); onError(""); await queryClient.invalidateQueries({ queryKey: ["settings"] }); },
    onError: (caught) => onError(caught instanceof Error ? caught.message : "Speichern fehlgeschlagen"),
  });
  return <form onSubmit={(event) => { event.preventDefault(); save.mutate(); }} className="mt-8 space-y-5 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
    <h2 className="text-xl font-semibold">Anzeige</h2>
    <label className="block text-sm">Zeitzone (IANA)
      <input required value={timezone} onChange={(event) => setTimezone(event.target.value)} className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3" />
    </label>
    <label className="block text-sm">Basiswährung (ISO 4217, drei Buchstaben)
      <input required maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value)} className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3" />
    </label>
    <button disabled={save.isPending} className="rounded-md bg-emerald-500 px-5 py-3 font-semibold text-zinc-950 disabled:opacity-50">Speichern</button>
  </form>;
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<Settings>("/settings") });
  const session = useSession();
  const [setup, setSetup] = useState<TotpSetup | null>(null);
  const [code, setCode] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function startTotp() {
    setError(""); setNotice("");
    try { setSetup(await api<TotpSetup>("/auth/totp/setup", { method: "POST" })); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Einrichtung fehlgeschlagen"); }
  }

  async function confirmTotp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    try {
      await api<{ totp_enabled: boolean }>("/auth/totp/confirm", { method: "POST", body: JSON.stringify({ code }) });
      setSetup(null); setCode(""); setNotice("Zwei-Faktor-Authentifizierung aktiviert. Bei erneuter Anmeldung den nächsten Code abwarten.");
      await queryClient.invalidateQueries({ queryKey: sessionQueryKey });
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Code ungültig"); }
  }

  return (
    <main className="max-w-2xl py-12">
      <h1 className="text-3xl font-semibold">Einstellungen</h1>
      <section className="ui-panel mt-6 space-y-4"><h2 className="text-xl font-semibold">Erscheinungsbild</h2><p className="text-sm ui-muted">Hell, Dunkel oder die Einstellung Ihres Geräts. Diese Präferenz enthält keine Finanz- oder Sitzungsdaten.</p><ThemeSwitcher /></section>
      {settings.isPending && <p className="mt-5 text-zinc-400">Lade Einstellungen…</p>}
      {settings.isError && <p role="alert" className="mt-5 text-rose-400">{settings.error.message}</p>}
      {notice && <p role="status" className="mt-5 text-emerald-400">{notice}</p>}
      {error && <p role="alert" className="mt-5 text-rose-400">{error}</p>}
      {settings.data && <SettingsForm initial={settings.data} onNotice={setNotice} onError={setError} />}
      <section className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="text-xl font-semibold">Zwei-Faktor-Authentifizierung</h2>
        {session.data?.user?.totp_enabled ? <p className="mt-3 text-emerald-400">Aktiv</p> : <>
          <p className="mt-3 text-sm text-zinc-400">Zusätzlicher Einmalcode bei jeder Anmeldung.</p>
          {!setup && <button onClick={startTotp} className="mt-5 rounded-md border border-emerald-500 px-5 py-3 text-emerald-400">Einrichten</button>}
          {setup && <div className="mt-5 space-y-4">
            <p className="text-sm">Secret in eine Authenticator-App eingeben:</p>
            <code className="block break-all rounded bg-zinc-950 p-3 text-emerald-300">{setup.secret}</code>
            <p className="text-xs text-zinc-500">Einrichtungslink (otpauth):</p>
            <code className="block break-all rounded bg-zinc-950 p-3 text-xs">{setup.provisioning_uri}</code>
            <form onSubmit={confirmTotp} className="space-y-4">
              <label className="block text-sm">Sechsstelligen Code bestätigen
                <input required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value)} className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3" />
              </label>
              <button className="rounded-md bg-emerald-500 px-5 py-3 font-semibold text-zinc-950">Aktivieren</button>
            </form>
          </div>}
        </>}
      </section>
    </main>
  );
}
