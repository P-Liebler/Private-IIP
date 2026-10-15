"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export const field = "rounded border border-zinc-700 bg-zinc-950 p-2 disabled:opacity-50";
export function Result({ value }: { value: unknown }) {
  return <pre className="max-h-[40rem] overflow-auto whitespace-pre-wrap rounded border border-zinc-800 p-4 text-xs">{JSON.stringify(value, null, 2)}</pre>;
}
export function PortfolioSelect({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  const [rows, setRows] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api<{ id: string; name: string }[]>("/portfolios").then(setRows).catch(e => setError(String(e))); }, []);
  return <label className="block">Portfolio <select aria-label="Portfolio" className={field} value={value} onChange={e => onChange(e.target.value)}><option value="">Bitte waehlen</option>{rows.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>{error && <span role="alert">{error}</span>}</label>;
}
