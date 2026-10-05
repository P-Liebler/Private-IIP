"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { type User } from "@/lib/api";
import { logout as endSession } from "@/lib/auth";

export function ProtectedShell({ user, children }: { user: User; children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  async function logout() {
    try {
      await endSession();
      queryClient.clear();
      router.replace("/login");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Abmeldung fehlgeschlagen");
    }
  }
  return (
    <div className="mx-auto min-h-screen max-w-5xl px-6 py-8">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <Link href="/dashboard" className="font-semibold text-emerald-400">Investment Intelligence</Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/dashboard" className="hover:text-emerald-400">Übersicht</Link>
          <Link href="/instruments" className="hover:text-emerald-400">Instrumente</Link>
          <Link href="/settings/data-sources" className="hover:text-emerald-400">Datenquellen</Link>
          <Link href="/settings" className="hover:text-emerald-400">Einstellungen</Link>
          <span className="text-zinc-400">{user.username}</span>
          <button onClick={logout} className="rounded border border-zinc-700 px-3 py-2 hover:border-emerald-400">Abmelden</button>
        </nav>
      </header>
      {error && <p role="alert" className="mt-4 text-rose-400">{error}</p>}
      {children}
    </div>
  );
}
