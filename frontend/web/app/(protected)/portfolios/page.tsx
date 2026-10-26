"use client";

import { PortfolioCard } from "@/components/portfolio-card";
import Link from "next/link";
import { PageHeader } from "@/components/ui/primitives";
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { bookingRequestKey, clearBookingRequestKey } from "@/lib/booking-request";
import { api } from "@/lib/api";
import { listPortfolios, type Portfolio } from "@/lib/api/portfolios";

export default function PortfoliosPage() {
  const cache = useQueryClient();
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("CHF");
  const portfolios = useQuery({ queryKey: ["portfolios"], queryFn: listPortfolios });
  const create = useMutation({ mutationFn: () => api<Portfolio>("/portfolios", { method: "POST", headers: { "Idempotency-Key": bookingRequestKey("portfolio") },
    body: JSON.stringify({ name, base_currency: currency }) }),
    onSuccess: () => { clearBookingRequestKey("portfolio"); setName(""); cache.invalidateQueries({ queryKey: ["portfolios"] }); } });
  function submit(event: FormEvent) { event.preventDefault(); create.mutate(); }
  return <main className="space-y-8 py-10">
    <PageHeader title="Portfolios" description="Depots, Buchungen und Bewertungen aus geprüften Daten." action={<Link className="ui-button ui-button-primary" href="/portfolios/new">Geführt einrichten</Link>} />
    <form onSubmit={submit} className="grid gap-3 rounded-xl border border-zinc-800 bg-zinc-900 p-5 sm:grid-cols-[1fr_auto_auto]">
      <input aria-label="Portfolio-Name" required maxLength={120} value={name} onChange={event => setName(event.target.value)} placeholder="Portfolio-Name" className="rounded border border-zinc-700 bg-zinc-950 p-3" />
      <select aria-label="Basiswährung" value={currency} onChange={event => setCurrency(event.target.value)} className="rounded border border-zinc-700 bg-zinc-950 p-3"><option>CHF</option><option>EUR</option><option>USD</option></select>
      <button disabled={create.isPending} className="rounded bg-emerald-500 px-5 py-3 font-semibold text-zinc-950">Erstellen</button>
    </form>
    {create.isError && <p role="alert" className="text-rose-400">{create.error.message}</p>}
    {portfolios.isPending && <p>Lade Portfolios…</p>}
    {portfolios.isError && <p role="alert" className="text-rose-400">{portfolios.error.message}</p>}
    {portfolios.data?.length === 0 && <p>Noch keine Portfolios angelegt.</p>}
    <ul className="grid gap-4 sm:grid-cols-2">{portfolios.data?.map(item => <li key={item.id}><PortfolioCard portfolio={item} /></li>)}</ul>
  </main>;
}
