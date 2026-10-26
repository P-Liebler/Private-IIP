"use client";

import { createContext, useContext, useState, useSyncExternalStore, type ReactNode } from "react";
import { Moon, Sun, Monitor } from "lucide-react";

export type Theme = "light" | "dark" | "system";
const ThemeContext = createContext<{ theme: Theme; resolved: "light" | "dark"; setTheme: (theme: Theme) => void }>({ theme: "system", resolved: "light", setTheme: () => {} });
function subscribe(callback: () => void) {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}

export function ThemeProvider({ initial, children }: { initial: Theme; children: ReactNode }) {
  const [theme, update] = useState<Theme>(initial);
  const dark = useSyncExternalStore(subscribe, () => window.matchMedia("(prefers-color-scheme: dark)").matches, () => false);
  const setTheme = (next: Theme) => {
    document.documentElement.dataset.theme = next;
    // Preference only: no session tokens, identifiers or financial data.
    document.cookie = `iip_theme=${next}; Path=/; Max-Age=31536000; SameSite=Lax${location.protocol === "https:" ? "; Secure" : ""}`;
    update(next);
  };
  return <ThemeContext.Provider value={{ theme, resolved: theme === "system" ? dark ? "dark" : "light" : theme, setTheme }}>{children}</ThemeContext.Provider>;
}
export const useTheme = () => useContext(ThemeContext);

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const Icon = theme === "system" ? Monitor : theme === "dark" ? Moon : Sun;
  return <label className="flex items-center gap-2"><Icon size={16} aria-hidden="true" /><span className="sr-only">Darstellung</span><select aria-label="Darstellung" value={theme} onChange={e => setTheme(e.target.value as Theme)} className="!min-h-9 !border-0 !bg-transparent !p-1 text-xs"><option value="system">System</option><option value="light">Hell</option><option value="dark">Dunkel</option></select></label>;
}
