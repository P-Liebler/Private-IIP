"use client";

import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { bookingRequestKey, clearBookingRequestKey } from "@/lib/booking-request";
import { api } from "@/lib/api";
import { listPortfolios, listAccounts, getValuation, listTransactions, type Portfolio, type Account } from "@/lib/api/portfolios";
import { Button, CurrencyInput, DateInput, ErrorState, FinancialMetric, LoadingSkeleton, PageHeader, StatusIndicator, Stepper } from "@/components/ui/primitives";
import { TransactionCsvImport } from "@/components/transaction-csv-import";
import { MarketDataImport } from "@/components/market-data-import";

const steps = ["Portfolio", "Konto", "Startguthaben", "Transaktionen", "Marktdaten", "Prüfen"];

export function PortfolioSetupWizard() {
  const params = useSearchParams(), router = useRouter(), cache = useQueryClient();
  const id = params.get("portfolio") ?? "";
  const requested = Number(params.get("step") ?? "0");
  const current = id ? Math.min(5, Math.max(1, Number.isInteger(requested) ? requested : 1)) : 0;
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("CHF");
  const [accountName, setAccountName] = useState("");
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [cashConfirmed, setCashConfirmed] = useState(false);
  const [day, setDay] = useState(new Date().toISOString().slice(0, 10));
  const portfolios = useQuery({ queryKey: ["portfolios"], queryFn: listPortfolios });
  const portfolio = portfolios.data?.find(p => p.id === id);
  const accounts = useQuery({ queryKey: ["accounts", id], queryFn: () => listAccounts(id), enabled: !!portfolio });
  const transactions = useQuery({ queryKey: ["transactions", id], queryFn: () => listTransactions(id), enabled: !!portfolio });
  const valuation = useQuery({ queryKey: ["valuation", id], queryFn: () => getValuation(id), enabled: !!portfolio && current === 5 });
  const activeAccounts = accounts.data?.filter(a => !a.archived_at) ?? [];
  const selectedAccount = activeAccounts.find(a => a.id === accountId) ?? activeAccounts[0];
  const go = (step: number, portfolioId = id) => { const next = new URLSearchParams(window.location.search); next.set("portfolio", portfolioId); next.set("step", String(step)); router.replace(`/portfolios/new?${next}`); };
  const createPortfolio = useMutation({ mutationFn: () => api<Portfolio>("/portfolios", { method: "POST", headers: { "Idempotency-Key": bookingRequestKey("setup_portfolio") }, body: JSON.stringify({ name, base_currency: currency }) }), onSuccess: async row => { clearBookingRequestKey("setup_portfolio"); await cache.invalidateQueries({ queryKey: ["portfolios"] }); go(1, row.id); } });
  const createAccount = useMutation({ mutationFn: () => api<Account>(`/portfolios/${id}/accounts`, { method: "POST", headers: { "Idempotency-Key": bookingRequestKey("setup_account") }, body: JSON.stringify({ name: accountName, account_type: "BROKER", default_currency: portfolio?.base_currency }) }), onSuccess: async row => { clearBookingRequestKey("setup_account"); setAccountId(row.id); setAccountName(""); await cache.invalidateQueries({ queryKey: ["accounts", id] }); go(2); } });
  const deposit = useMutation({ mutationFn: () => api(`/portfolios/${id}/transactions`, { method: "POST", headers: { "Idempotency-Key": bookingRequestKey("setup_cash") }, body: JSON.stringify({ account_id: selectedAccount?.id, type: "DEPOSIT", trade_date: day, currency: portfolio?.base_currency, amount, fee: "0", tax: "0", notes: "Startguthaben aus Einrichtung; vom Benutzer bestätigt" }) }), onSuccess: async () => { clearBookingRequestKey("setup_cash"); setCashConfirmed(false); setAmount(""); await cache.invalidateQueries({ queryKey: ["transactions", id] }); go(3); } });
  if (portfolios.isPending) return <LoadingSkeleton />;
  if (portfolios.isError) return <ErrorState error={portfolios.error} retry={() => { void portfolios.refetch(); }} />;
  if (id && !portfolio) return <ErrorState error="Dieses Portfolio ist nicht verfügbar. Öffnen Sie ein eigenes Portfolio oder beginnen Sie eine neue Einrichtung." />;
  return <main className="space-y-8"><PageHeader title="Ihr Portfolio einrichten" description="Ein geführter Weg vom leeren Depot zur nachvollziehbaren Bewertung. Sie können später über diesen Link fortfahren." />
    <Stepper steps={steps} current={current} />
    {current > 0 && <p className="text-sm ui-muted">{portfolio?.name} · Basiswährung {portfolio?.base_currency} · Gespeicherte Buchungen bleiben auch beim Verlassen erhalten.</p>}
    {current === 0 && <form className="ui-panel max-w-xl space-y-5" onSubmit={e => { e.preventDefault(); if (!createPortfolio.isPending) createPortfolio.mutate(); }}>
      <h2 className="text-xl font-semibold">Wie heißt Ihr Portfolio?</h2><p className="ui-muted text-sm">Zum Beispiel Ihr langfristiges Depot. Die Basiswährung dient zur Bewertung; Originalwährungen bleiben erhalten.</p>
      <label className="grid gap-2">Portfolio-Name<input required maxLength={120} value={name} onChange={e => setName(e.target.value)} /></label>
      <label className="grid gap-2">Basiswährung<select value={currency} onChange={e => setCurrency(e.target.value)}><option>CHF</option><option>EUR</option><option>USD</option></select></label>
      <Button variant="primary" disabled={createPortfolio.isPending}>Portfolio anlegen und weiter</Button>{createPortfolio.isError && <ErrorState error={createPortfolio.error} />}
    </form>}
    {current === 1 && <section className="ui-panel max-w-xl space-y-5"><h2 className="text-xl font-semibold">Ein Konto für Ihre Buchungen</h2><p className="ui-muted text-sm">Das Konto bildet Ihr Depot beim Broker ab. Es wird keine Verbindung zum Broker hergestellt.</p>
      {activeAccounts.length > 0 && <><label className="grid gap-2">Vorhandenes Konto<select value={selectedAccount?.id ?? ""} onChange={e => setAccountId(e.target.value)}>{activeAccounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label><Button variant="primary" onClick={() => go(2)}>Mit diesem Konto weiter</Button></>}
      <form className="space-y-4" onSubmit={e => { e.preventDefault(); if (!createAccount.isPending) createAccount.mutate(); }}><label className="grid gap-2">Neues Konto benennen<input required maxLength={120} value={accountName} onChange={e => setAccountName(e.target.value)} placeholder="Zum Beispiel: Mein Depot" /></label><Button disabled={createAccount.isPending}>Konto anlegen und weiter</Button></form>
      {accounts.isError && <ErrorState error={accounts.error} />}{createAccount.isError && <ErrorState error={createAccount.error} />}
    </section>}
    {current === 2 && <form className="ui-panel max-w-xl space-y-5" onSubmit={e => { e.preventDefault(); if (!deposit.isPending && cashConfirmed) deposit.mutate(); }}>
      <h2 className="text-xl font-semibold">Mit Cash beginnen — optional</h2><p className="text-sm ui-muted">Nur einen tatsächlich belegten Geldeingang erfassen. Wenn Ihre CSV den Startbestand bereits enthält, überspringen Sie diesen Schritt.</p>
      <CurrencyInput label="Belegter Geldeingang" currency={portfolio?.base_currency ?? "CHF"} required value={amount} onChange={e => setAmount(e.target.value)} pattern="[0-9]+(\.[0-9]{1,8})?" placeholder="Betrag mit Dezimalpunkt" />
      <DateInput label="Buchungsdatum" required value={day} onChange={e => setDay(e.target.value)} />
      <p className="text-xs ui-muted">Konto: {selectedAccount?.name ?? "Bitte zuerst ein Konto anlegen"}. Bestehende Buchungen: {transactions.data?.length ?? "wird geladen"}.</p>
      <label className="block text-sm"><input type="checkbox" checked={cashConfirmed} onChange={e => setCashConfirmed(e.target.checked)} /> Ich habe Konto, Datum, Währung und Betrag geprüft und bestätige diese Buchung.</label>
      <div className="flex flex-wrap gap-3"><Button variant="primary" disabled={!selectedAccount || !cashConfirmed || deposit.isPending}>Geldeingang buchen und weiter</Button><Button type="button" onClick={() => go(3)}>Ohne Cash-Buchung weiter</Button></div>
      {deposit.isError && <ErrorState error={deposit.error} />}
    </form>}
    {current === 3 && <><TransactionCsvImport portfolioId={id} accounts={activeAccounts} onImported={() => { void cache.invalidateQueries({ queryKey: ["transactions", id] }); }} /><div className="flex flex-wrap gap-3"><Button variant="primary" onClick={() => go(4)}>Weiter zu Kursen und Währungen</Button><Link className="ui-button" href={`/portfolios/${id}?tab=Transaktionen`}>Einzelne Buchung oder Startposition erfassen</Link></div><p className="text-xs ui-muted">Startpositionen ohne belegten Einstand bleiben ohne Gewinnberechnung. Sie müssen keine vollständige Historie erfinden.</p></>}
    {current === 4 && <><MarketDataImport embedded /><Button variant="primary" onClick={() => go(5)}>Bewertung prüfen</Button></>}
    {current === 5 && <section className="ui-panel space-y-5"><h2 className="text-xl font-semibold">Ihr aktueller Bewertungsstand</h2>{valuation.isPending && <LoadingSkeleton />}{valuation.isError && <ErrorState error={valuation.error} />}{valuation.data && <><StatusIndicator status={valuation.data.status} /><p className="text-3xl"><FinancialMetric value={valuation.data.total_value_base} currency={valuation.data.base_currency} /></p><p className="text-sm ui-muted">{valuation.data.holdings.length} Positionen · {valuation.data.issues.length} Hinweise. Fehlende oder veraltete Daten verhindern einen vollständigen Gesamtwert.</p></>}<Link className="ui-button ui-button-primary" href={`/portfolios/${id}`}>Portfolio öffnen</Link><p className="text-sm ui-muted">Ein eingerichtetes Portfolio ist keine Produktions- oder Quellenfreigabe. Offene Datenprobleme und Betriebsfreigaben bleiben sichtbar.</p></section>}
    {current > 0 && <div className="flex flex-wrap gap-3"><Button onClick={() => go(Math.max(1, current - 1))} disabled={current === 1}>Vorheriger Schritt</Button><Link className="ui-button" href={`/portfolios/${id}`}>Einrichtung später fortsetzen</Link></div>}
  </main>;
}
