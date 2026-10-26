"use client";

import { useState, useSyncExternalStore, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSession, login, sessionQueryKey, verifyTotp } from "@/lib/auth";
import { QueryProvider } from "@/components/query-provider";

const subscribe = () => () => {};

export default function LoginPage() {
  return <QueryProvider><LoginForm /></QueryProvider>;
}

function LoginForm() {
  const hydrated = useSyncExternalStore(subscribe, () => true, () => false);
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (challenge) {
        await verifyTotp(challenge, code);
      } else {
        const result = await login(username, password);
        setPassword("");
        if (result.status === "totp_required") {
          setChallenge(result.challenge);
          return;
        }
      }
      await queryClient.invalidateQueries({ queryKey: sessionQueryKey });
      await queryClient.fetchQuery({ queryKey: sessionQueryKey, queryFn: getSession });
      window.location.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Anmeldung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">Private Investment Intelligence</p>
      <h1 className="text-3xl font-semibold">Anmelden</h1>
      <p className="mt-3 text-sm text-zinc-400">Zugang nur für zuvor administrativ angelegte Konten.</p>
      <form onSubmit={submit} className="mt-8 space-y-5 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        {challenge ? (
          <>
            <label className="block text-sm">Code aus der Authenticator-App
              <input autoFocus autoComplete="one-time-code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required value={code} onChange={(event) => setCode(event.target.value)} className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3" />
            </label>
            <button type="button" onClick={() => { setChallenge(null); setCode(""); setError(""); }} className="text-sm text-zinc-400 underline">Andere Anmeldung</button>
          </>
        ) : (
          <>
            <label className="block text-sm">Benutzername
              <input disabled={!hydrated || busy} autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3" />
            </label>
            <label className="block text-sm">Passwort
              <input disabled={!hydrated || busy} type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3" />
            </label>
          </>
        )}
        {error && <p role="alert" className="text-sm text-rose-400">{error}</p>}
        <button disabled={!hydrated || busy} className="w-full rounded-md bg-emerald-500 p-3 font-semibold text-zinc-950 disabled:opacity-50">{busy ? "Bitte warten…" : challenge ? "Code prüfen" : "Anmelden"}</button>
      </form>
    </main>
  );
}
