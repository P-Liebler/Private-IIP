"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Action = { instrument_name: string; type: string; date: string; ratio: string | null;
  cash_amount_per_share: string | null; currency: string | null; source_id: string;
  ledger_quantity_before_ex_date: string | null; cost_confirmation_required: boolean; manual_effect_count: number };

export function CorporateActionReview({ portfolioId, accountId, versionId, onApplied }: {
  portfolioId: string; accountId: string; versionId: string; onApplied: () => void;
}) {
  const [opened, setOpened] = useState(false), [fee, setFee] = useState(""), [tax, setTax] = useState("");
  const [adoptManual, setAdoptManual] = useState(false);
  const action = useQuery({ queryKey: ["action-preview", portfolioId, accountId, versionId], enabled: opened,
    queryFn: () => api<Action>(`/portfolios/${portfolioId}/corporate-actions/${versionId}/preview?account_id=${accountId}`) });
  const apply = useMutation({ mutationFn: () => api(`/portfolios/${portfolioId}/corporate-actions/apply`, { method: "POST",
    body: JSON.stringify({ account_id: accountId, action_version_id: versionId, adopt_manual: adoptManual,
      fee: action.data?.cost_confirmation_required ? fee : null, tax: action.data?.cost_confirmation_required ? tax : null }) }), onSuccess: onApplied });
  return <div className="mt-3 rounded border border-zinc-700 p-3"><button onClick={() => setOpened(!opened)} className="text-emerald-400 underline">Corporate Action prüfen</button>
    {opened && action.data && <form onSubmit={event => { event.preventDefault(); apply.mutate(); }} className="mt-3 space-y-3">
      <p>{action.data.instrument_name} · {action.data.type} · Ex-Datum {action.data.date}</p>
      <p>Verhältnis: {action.data.ratio ?? "—"} · Brutto je Aktie: {action.data.cash_amount_per_share ?? "—"} {action.data.currency} · Ledger-Bestand vor Ex-Datum: {action.data.ledger_quantity_before_ex_date ?? "DATA_UNAVAILABLE"}</p>
      <p className="text-xs text-zinc-400">Quelle: {action.data.source_id} · Version: {versionId}. Frühere Splits müssen zuerst geprüft und angewendet werden.</p>
      {action.data.manual_effect_count > 0 && <label className="block text-sm"><input type="checkbox" checked={adoptManual} onChange={event => setAdoptManual(event.target.checked)} /> Vorhandene manuelle Buchung nach Prüfung verknüpfen. Menge/Betrag, Währung und Kosten müssen exakt übereinstimmen; es wird kein zweiter Effekt gebucht.</label>}
      {action.data.cost_confirmation_required && <><p className="text-sm text-amber-400">Gebühr und Quellensteuer laut Beleg bestätigen. Auch null muss ausdrücklich eingegeben werden. Die Buchung verwendet das wirtschaftliche Ex-Datum.</p>
        <label className="block">Bestätigte Dividenden-Gebühr<input required inputMode="decimal" value={fee} onChange={event => setFee(event.target.value)} className="ml-2 rounded border border-zinc-700 bg-zinc-950 p-2" /></label>
        <label className="block">Bestätigte Quellensteuer<input required inputMode="decimal" value={tax} onChange={event => setTax(event.target.value)} className="ml-2 rounded border border-zinc-700 bg-zinc-950 p-2" /></label></>}
      <button disabled={apply.isPending} className="rounded bg-emerald-500 px-3 py-2 text-zinc-950">Geprüften Effekt buchen</button>
    </form>}
    {action.isPending && opened && <p>Wird geladen…</p>}{[action, apply].map((result, index) => result.isError && <p key={index} role="alert">{result.error.message}</p>)}
  </div>;
}
