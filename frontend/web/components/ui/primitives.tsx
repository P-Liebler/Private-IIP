"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type RefObject, type SelectHTMLAttributes } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as Tooltip from "@radix-ui/react-tooltip";
import * as RadixTabs from "@radix-ui/react-tabs";
import { Command } from "cmdk";
import { AlertCircle, ArrowRight, Check, Clock3, FileUp, HelpCircle, Inbox, RefreshCw, X } from "lucide-react";
import { areaFor, destinationFor } from "@/lib/product-navigation";
import { money, ratio } from "@/lib/portfolio-format";

export function Button({ variant = "default", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "quiet" | "danger" }) {
  return <button className={`ui-button ${variant === "primary" ? "ui-button-primary" : variant === "quiet" ? "ui-button-quiet" : variant === "danger" ? "ui-button-danger" : ""} ${className}`} {...props} />;
}
export function PageHeader({ title, description, action }: { title: ReactNode; description?: ReactNode; action?: ReactNode }) {
  const path = usePathname();
  return <div className="ui-page-header"><div><p className="ui-kicker">{areaFor(path).label}</p><h1>{title}</h1><p>{description ?? destinationFor(path)?.description}</p></div>{action && <div className="flex flex-wrap gap-2">{action}</div>}</div>;
}
export function FinancialMetric({ value, currency = "CHF", percentage = false, semantic = false }: { value: string | null | undefined; currency?: string; percentage?: boolean; semantic?: boolean }) {
  const valid = value !== null && value !== undefined && value.trim() !== "" && Number.isFinite(Number(value));
  const direction = valid && semantic ? Number(value) < 0 ? "ui-negative" : Number(value) > 0 ? "ui-positive" : "" : "";
  return <span className={direction} style={{ fontVariantNumeric: "tabular-nums" }}>{!valid ? "Nicht verfügbar" : percentage ? ratio(value) : money(value, currency)}</span>;
}
export function SummaryCard({ title, value, detail, icon, featured = false }: { title: string; value: ReactNode; detail?: ReactNode; icon?: ReactNode; featured?: boolean }) {
  return <article className={`ui-panel ${featured ? "sm:col-span-2" : ""}`}><div className="flex items-center justify-between gap-3"><h2 className="text-sm font-medium ui-muted">{title}</h2>{icon}</div><div className="ui-metric-value my-3">{value}</div>{detail && <div className="text-xs ui-muted">{detail}</div>}</article>;
}
const stateText: Record<string, string> = {
  COMPLETE: "Vollständig bewertet", AVAILABLE: "Verfügbar", CURRENT: "Aktueller Datenstand", DELAYED: "Tages-Schlusskurs", STALE: "Veraltet", MISSING: "Daten fehlen", INVALID: "Prüfung erforderlich", PARTIAL: "Unvollständig", HISTORICAL_ONLY: "Historischer Datenstand", SOURCE_BLOCKED: "Quelle nicht freigegeben", UNKNOWN: "Noch nicht geprüft", BLOCKED: "Freigabe erforderlich", APPROVED: "Freigabe dokumentiert", SHADOW: "Prognose im Testbetrieb", EXPERIMENT: "Experimentell", NO_RELIABLE_FORECAST: "Keine verlässliche Prognose", INSUFFICIENT_DATA: "Daten reichen nicht aus", DATA_UNAVAILABLE: "Nicht verfügbar", GATED: "Voraussetzungen fehlen", FAILED: "Fehlgeschlagen", SUCCEEDED: "Auftrag abgeschlossen", PENDING: "Wartet auf Verarbeitung", RUNNING: "Wird verarbeitet", MANUAL_IMPORT: "Eigener Dateiimport", SOURCE_GATE_REQUIRED: "Quellenfreigabe prüfen",
};
export const humanStatus = (status: string) => stateText[status] ?? status.replaceAll("_", " ");
export function StatusIndicator({ status, detail = false }: { status: string; detail?: boolean }) {
  const tone = ["FAILED", "INVALID"].includes(status) ? "danger" : ["PARTIAL", "MISSING", "STALE", "BLOCKED", "UNKNOWN", "GATED", "SOURCE_BLOCKED", "INSUFFICIENT_DATA", "NO_RELIABLE_FORECAST"].includes(status) ? "warning" : ["COMPLETE", "AVAILABLE", "CURRENT", "SUCCEEDED"].includes(status) ? "good" : "neutral";
  return <span className="ui-status" data-tone={tone}>{tone === "good" ? <Check size={12} aria-hidden="true" /> : tone === "warning" || tone === "danger" ? <AlertCircle size={12} aria-hidden="true" /> : <Clock3 size={12} aria-hidden="true" />}{humanStatus(status)}{detail && humanStatus(status) !== status && <span className="sr-only"> · {status}</span>}</span>;
}
export function DataFreshness({ date, source, age, status }: { date?: string | null; source?: string | null; age?: number | null; status?: string }) {
  return <div className="flex flex-wrap items-center gap-2 text-xs ui-muted"><Clock3 size={14} aria-hidden="true" /><span>{date ? `Stand ${date}` : "Datenstand nicht verfügbar"}</span>{age !== undefined && age !== null && <span>· {age} {age === 1 ? "Tag" : "Tage"} alt</span>}{source && <span>· {source}</span>}{status && <StatusIndicator status={status} />}</div>;
}
export function EmptyState({ title, description, action }: { title: string; description: ReactNode; action?: ReactNode }) {
  return <section className="ui-state"><Inbox size={24} className="shrink-0 ui-muted" aria-hidden="true" /><div><h2>{title}</h2><p>{description}</p>{action && <div className="mt-4">{action}</div>}</div></section>;
}
export function ErrorState({ error, retry }: { error: Error | string; retry?: () => void }) {
  return <section className="ui-state" role="alert"><AlertCircle size={24} className="shrink-0 ui-negative" aria-hidden="true" /><div><h2>Diese Informationen konnten nicht geladen werden</h2><p>{typeof error === "string" ? error : error.message}</p>{retry && <Button onClick={retry} className="mt-4"><RefreshCw size={14} />Erneut versuchen</Button>}</div></section>;
}
export function LoadingSkeleton({ label = "Informationen werden geladen", rows = 3 }: { label?: string; rows?: number }) {
  return <div role="status" aria-label={label} className="space-y-3"><span className="sr-only">{label}</span>{Array.from({ length: rows }, (_, i) => <div key={i} className="ui-skeleton" style={{ width: `${100 - i * 12}%`, height: i === 0 ? 32 : 16 }} />)}</div>;
}
export function ContextualHelp({ title, children }: { title: string; children: ReactNode }) {
  return <Tooltip.Provider delayDuration={250}><Tooltip.Root><Tooltip.Trigger asChild><button type="button" aria-label={title} className="ui-icon-button ui-button-quiet"><HelpCircle size={16} /></button></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="ui-tooltip" sideOffset={8}>{children}<Tooltip.Arrow /></Tooltip.Content></Tooltip.Portal></Tooltip.Root></Tooltip.Provider>;
}
export function ConfirmationDialog({ title, description, trigger, onConfirm, busy = false, open: controlledOpen, onOpenChange, returnFocus }: { title: string; description: ReactNode; trigger?: ReactNode; onConfirm: () => Promise<unknown>; busy?: boolean; open?: boolean; onOpenChange?: (value: boolean) => void; returnFocus?: RefObject<HTMLElement | null> }) {
  const [localOpen, setLocalOpen] = useState(false); const [error, setError] = useState(""); const [pending, setPending] = useState(false);
  const open = controlledOpen ?? localOpen;
  const setOpen = (next: boolean) => { setLocalOpen(next); onOpenChange?.(next); };
  const blocked = busy || pending;
  return <Dialog.Root open={open} onOpenChange={value => { if (!blocked) setOpen(value); }}>{trigger && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}<Dialog.Portal><Dialog.Overlay className="ui-overlay" /><Dialog.Content className="ui-dialog" onCloseAutoFocus={event => { if (returnFocus?.current) { event.preventDefault(); returnFocus.current.focus(); } }}><Dialog.Title>{title}</Dialog.Title><Dialog.Description asChild><div className="ui-muted mt-3">{description}</div></Dialog.Description>{error && <p role="alert" className="ui-negative mt-3">{error}</p>}<div className="mt-6 flex justify-end gap-3"><Dialog.Close asChild><Button disabled={blocked}>Abbrechen</Button></Dialog.Close><Button variant="primary" disabled={blocked} onClick={async () => { if (blocked) return; setPending(true); setError(""); try { await onConfirm(); setOpen(false); } catch (e) { setError(e instanceof Error ? e.message : "Aktion fehlgeschlagen"); } finally { setPending(false); } }}>{blocked ? "Wird verarbeitet…" : "Ausdrücklich bestätigen"}</Button></div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
export function DetailDrawer({ title, description, children, trigger }: { title: string; description: string; children: ReactNode; trigger: ReactNode }) {
  return <Dialog.Root><Dialog.Trigger asChild>{trigger}</Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="ui-overlay" /><Dialog.Content className="ui-dialog ui-drawer"><div className="mb-6 flex justify-between gap-4"><div><Dialog.Title>{title}</Dialog.Title><Dialog.Description className="ui-muted mt-2">{description}</Dialog.Description></div><Dialog.Close asChild><Button aria-label="Detailansicht schließen" className="ui-icon-button"><X size={18} /></Button></Dialog.Close></div>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}
export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return <ol className="ui-stepper" aria-label="Fortschritt">{steps.map((step, i) => <li key={step} aria-current={i === current ? "step" : undefined}>{step}{i < steps.length - 1 && <ArrowRight size={12} aria-hidden="true" />}</li>)}</ol>;
}
export function Tabs({ items, value, onChange, label }: { items: { value: string; label: string; content: ReactNode }[]; value: string; onChange: (value: string) => void; label: string }) {
  return <RadixTabs.Root value={value} onValueChange={onChange}><RadixTabs.List className="ui-tabs" aria-label={label}>{items.map(i => <RadixTabs.Trigger value={i.value} key={i.value}>{i.label}</RadixTabs.Trigger>)}</RadixTabs.List>{items.map(i => <RadixTabs.Content value={i.value} key={i.value} className="pt-6">{i.content}</RadixTabs.Content>)}</RadixTabs.Root>;
}
export function AccessibleSelect({ label, children, ...props }: SelectHTMLAttributes<HTMLSelectElement> & { label: string; children: ReactNode }) {
  const id = useId(); return <label htmlFor={id} className="grid gap-2 text-sm">{label}<select id={id} {...props}>{children}</select></label>;
}
export function CurrencyInput({ label, currency, error, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; currency: string; error?: string }) {
  const id = useId(); return <label htmlFor={id} className="grid gap-2 text-sm">{label}<span className="flex items-center gap-3"><input id={id} inputMode="decimal" aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} className="w-full" {...props} /><span className="ui-muted">{currency}</span></span>{error && <span id={`${id}-error`} className="ui-negative">{error}</span>}</label>;
}
export function DateInput({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const id = useId(); return <label htmlFor={id} className="grid gap-2 text-sm">{label}<input type="date" id={id} {...props} /></label>;
}
export function FileDropzone({ label, file, onFile, accept = ".csv,text/csv", maxBytes = 5_000_000 }: { label: string; file: File | null; onFile: (file: File | null) => void; accept?: string; maxBytes?: number }) {
  const [dragging, setDragging] = useState(false); const [error, setError] = useState(""); const id = useId();
  function choose(value: File | null) { if (value && value.size > maxBytes) { setError(`Die Datei ist zu groß. Maximal ${Math.floor(maxBytes / 1_000_000)} MB.`); onFile(null); } else { setError(""); onFile(value); } }
  return <div className="ui-dropzone" data-dragging={dragging} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files[0] ?? null); }}><FileUp size={24} className="ui-muted" aria-hidden="true" /><label htmlFor={id} className="font-medium">{label}</label><p className="text-xs ui-muted">Datei hineinziehen oder auswählen. Das Original wird unverändert aufbewahrt.</p><input id={id} type="file" accept={accept} aria-describedby={error ? `${id}-error` : undefined} onChange={e => choose(e.target.files?.[0] ?? null)} />{file && <p className="text-sm" role="status">{file.name} · {Math.ceil(file.size / 1024)} KB</p>}{error && <p id={`${id}-error`} role="alert" className="ui-negative">{error}</p>}</div>;
}
export function SearchCombobox({ label, placeholder, options, onSearch, onSelect, busy = false }: { label: string; placeholder?: string; options: { id: string; label: string; detail?: string }[]; onSearch: (query: string) => void; onSelect: (id: string) => void; busy?: boolean }) {
  return <Command shouldFilter={false} label={label}><Command.Input aria-label={label} placeholder={placeholder ?? "Name, ISIN oder Ticker suchen…"} onValueChange={onSearch} /><Command.List aria-label="Suchergebnisse">{busy && <Command.Loading>Suche läuft…</Command.Loading>}<Command.Empty>Kein eindeutiger Treffer. Kennung oder Börse prüfen.</Command.Empty>{options.map(o => <Command.Item key={o.id} value={o.id} onSelect={() => onSelect(o.id)}><span className="block font-medium">{o.label}</span>{o.detail && <span className="text-xs ui-muted">{o.detail}</span>}</Command.Item>)}</Command.List></Command>;
}
export function ActionList({ actions }: { actions: { label: string; description: string; href: string }[] }) {
  return <ul className="divide-y divide-zinc-800">{actions.map(a => <li key={a.href}><Link href={a.href} className="flex items-center justify-between gap-4 py-4"><span><span className="block font-medium">{a.label}</span><span className="text-xs ui-muted">{a.description}</span></span><ArrowRight size={16} className="shrink-0 ui-muted" aria-hidden="true" /></Link></li>)}</ul>;
}
