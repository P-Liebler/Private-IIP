"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Activity, Bell, ChartNoAxesCombined, ChevronRight, Compass, LayoutDashboard, LogOut, Menu, Settings2, Sparkles, Wallet, X, ShieldCheck } from "lucide-react";
import { api, type User } from "@/lib/api";
import { logout as endSession } from "@/lib/auth";
import { navigation, areaFor, destinationFor } from "@/lib/product-navigation";
import { QueryProvider } from "@/components/query-provider";
import { CapabilitiesProvider, useCapabilities } from "@/components/capabilities";
import { ThemeSwitcher } from "@/components/ui/theme-provider";
import { Button, EmptyState, LoadingSkeleton } from "@/components/ui/primitives";

export function ProtectedShell({ user, children }: { user: User; children: ReactNode }) {
  // Private query caches are scoped to this authenticated identity and destroyed
  // when the protected layout unmounts. No cross-user financial cache survives.
  return <QueryProvider key={user.id}><CapabilitiesProvider userId={user.id}><AppShell user={user}>{children}</AppShell></CapabilitiesProvider></QueryProvider>;
}

const areaIcons = [LayoutDashboard, Wallet, Compass, ChartNoAxesCombined, Activity, Settings2];
function PrimaryNavigation({ close }: { close?: () => void }) {
  const path = usePathname(); const active = areaFor(path);
  return <nav className="app-primary-nav" aria-label="Primärnavigation">{navigation.map((area, index) => {
    const Icon = areaIcons[index];
    return <Link href={area.href} key={area.id} aria-label={area.label} aria-current={active.id === area.id ? "page" : undefined} onClick={close}><Icon size={20} aria-hidden="true" /><span className="nav-label">{area.label}</span></Link>;
  })}</nav>;
}
function MobileNavigation() {
  const [open, setOpen] = useState(false);
  return <Dialog.Root open={open} onOpenChange={setOpen}><Dialog.Trigger asChild><Button className="app-mobile-trigger ui-icon-button" aria-label="Navigation öffnen"><Menu size={20} /></Button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="ui-overlay" /><Dialog.Content className="ui-dialog"><div className="mb-6 flex items-start justify-between gap-4"><div><Dialog.Title>Ihr Arbeitsbereich</Dialog.Title><Dialog.Description className="ui-muted mt-2">Sechs Bereiche für Ihr Portfolio und seine Daten.</Dialog.Description></div><Dialog.Close asChild><Button className="ui-icon-button" aria-label="Navigation schließen"><X size={18} /></Button></Dialog.Close></div><PrimaryNavigation close={() => setOpen(false)} /><Link href="/assistant" onClick={() => setOpen(false)} className="ui-button mt-6 w-full"><Sparkles size={16} />Assistent öffnen</Link></Dialog.Content></Dialog.Portal></Dialog.Root>;
}

function AppShell({ user, children }: { user: User; children: ReactNode }) {
  const queryClient = useQueryClient();
  const path = usePathname(); const active = areaFor(path); const destination = destinationFor(path);
  const { permissions, pending } = useCapabilities();
  const blocked = destination?.operator && !permissions[destination.operator];
  const notifications = useQuery({ queryKey: ["notifications", user.id], queryFn: () => api<{ unread_count: number }>("/notifications"), refetchInterval: 60000 });
  const [error, setError] = useState("");
  async function logout() {
    try {
      await endSession();
      queryClient.clear();
      window.location.replace("/login");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Abmeldung fehlgeschlagen");
    }
  }
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">Zum Inhalt springen</a>
      <aside className="app-sidebar"><Link href="/dashboard" className="app-brand"><span className="app-brand-mark"><ChartNoAxesCombined size={20} aria-hidden="true" /></span><span>Private IIP<span className="block text-[10px] font-normal tracking-wide ui-muted">INVESTMENT INTELLIGENCE</span></span></Link><PrimaryNavigation /><div className="app-sidebar-bottom"><Link href="/assistant" className="ui-button"><Sparkles size={16} /><span className="nav-label">Assistent fragen</span></Link><p className="nav-label text-xs ui-muted flex gap-2"><ShieldCheck size={14} className="shrink-0" aria-hidden="true" />Privater Arbeitsbereich<br />Ihre Entscheidungen bleiben bei Ihnen.</p></div></aside>
      <div className="app-main"><header className="app-topbar"><div className="flex items-center gap-3"><MobileNavigation /><span className="text-sm font-medium">{active.label}</span><ChevronRight size={14} className="ui-muted hidden sm:block" aria-hidden="true" /><span className="text-xs ui-muted desktop-label">{destination?.label ?? (path.startsWith("/portfolios/") ? "Portfoliodetails" : path.startsWith("/instrument/") ? "Instrumentdetails" : "Privater Arbeitsbereich")}</span></div><div className="app-topbar-actions"><ThemeSwitcher /><Link href="/alerts" className="ui-button ui-icon-button ui-button-quiet relative" aria-label={`Benachrichtigungen${notifications.data ? `: ${notifications.data.unread_count} ungelesen` : ""}`}><Bell size={18} />{notifications.data && notifications.data.unread_count > 0 && <span className="absolute right-1 top-1 size-2 rounded-full bg-emerald-500" />}</Link><Link href="/settings" className="ui-button ui-button-quiet desktop-label text-xs" aria-label="Benutzerkonto">{user.username}</Link><Button onClick={logout} className="ui-icon-button ui-button-quiet" aria-label="Abmelden"><LogOut size={17} /></Button></div></header>
      <nav className="app-subnav" aria-label={`${active.label}: Unterbereiche`}>{active.destinations.filter(d => !d.operator || permissions[d.operator]).map(d => <Link key={d.href} href={d.href} aria-current={path === d.href ? "page" : undefined}>{d.label}</Link>)}</nav>
      <div id="main-content" className="app-content" tabIndex={-1}>{error && <p role="alert" className="ui-negative mb-4">{error}</p>}{blocked ? pending ? <LoadingSkeleton label="Berechtigung wird geprüft" /> : <EmptyState title="Dieser Bereich ist für Betreiberpersonen vorgesehen" description="Die erforderliche Berechtigung ist für dieses Konto nicht eingerichtet. Ihre Portfoliofunktionen bleiben verfügbar." action={<Link href="/dashboard" className="ui-button">Zur Übersicht</Link>} /> : children}</div>
      </div>
    </div>
  );
}
