"use client";

import Link from "next/link";
import type { Valuation } from "@/lib/api/portfolios";
import { HoldingProvenance } from "@/components/portfolio-data-actions";
import { DataTable } from "@/components/ui/data-table";
import { Button, DetailDrawer, FinancialMetric, StatusIndicator } from "@/components/ui/primitives";
import { ratio } from "@/lib/portfolio-format";

export function HoldingsTable({ valuation }: { valuation: Valuation }) {
  return <DataTable label="Aktuelle Positionen" rows={valuation.holdings} rowKey={h => `${h.account_id}-${h.instrument_id}`} searchText={h => `${h.name} ${h.isin ?? ""} ${h.ticker ?? ""} ${h.currency}`} columns={[
    { id: "name", label: "Instrument", sortValue: h => h.name, render: h => <><Link className="font-medium underline" href={`/instrument/${h.instrument_id}`}>{h.name}</Link><p className="text-xs ui-muted mt-1">{h.isin ?? h.ticker ?? "Kennung fehlt"} · {h.mic ?? "Börse ungeprüft"}</p></> },
    { id: "quantity", label: "Stückzahl", numeric: true, sortValue: h => Number(h.quantity), render: h => h.quantity },
    { id: "price", label: "Schlusskurs", numeric: true, render: h => <><FinancialMetric value={h.price} currency={h.currency} /><p className="text-xs ui-muted">{h.price_date ?? "Kein Kursdatum"}</p></> },
    { id: "value", label: `Marktwert (${valuation.base_currency})`, numeric: true, sortValue: h => h.market_value_base === null ? null : Number(h.market_value_base), render: h => <FinancialMetric value={h.market_value_base} currency={valuation.base_currency} /> },
    { id: "pnl", label: "Unrealisiert (vorläufig)", numeric: true, sortValue: h => h.unrealized_pnl_base_at_valuation_fx == null || h.valuation_status !== "CURRENT" ? null : Number(h.unrealized_pnl_base_at_valuation_fx), render: h => <FinancialMetric value={h.valuation_status === "CURRENT" ? h.unrealized_pnl_base_at_valuation_fx : null} currency={valuation.base_currency} semantic /> },
    { id: "weight", label: "Anteil", numeric: true, sortValue: h => h.weight === null ? null : Number(h.weight), render: h => h.weight === null ? "Nicht verfügbar" : ratio(h.weight) },
    { id: "quality", label: "Datenqualität", render: h => <StatusIndicator status={h.valuation_status} /> },
    { id: "source", label: "Quelle & Details", render: h => <DetailDrawer title={h.name} description="Kurs, Währung, Quelle und fehlende Bewertungsgrundlagen." trigger={<Button>Details</Button>}><HoldingProvenance holding={h} /><p className="mt-4">Einstand: <FinancialMetric value={h.cost_basis_native} currency={h.currency} /></p><p className="mt-3 text-xs ui-muted">Gewinn/Verlust ist vorläufig, solange Dividenden und Splits nicht vollständig nachgewiesen sind. Unbekannte Einstandswerte bleiben unbekannt.</p></DetailDrawer> },
  ]} empty="Noch keine offenen Positionen. Buchungen oder einen belegten Startbestand erfassen." />;
}
