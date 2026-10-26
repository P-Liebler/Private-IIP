"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { ToastRegion, notify } from "@/components/ui/toast";

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    mutationCache: new MutationCache({
      onSuccess: () => notify("Anfrage abgeschlossen. Ergebnis und Hinweise prüfen."),
      onError: error => notify(error.message),
    }),
    defaultOptions: { queries: { retry: 1, staleTime: 15_000, refetchOnWindowFocus: true }, mutations: { retry: false } },
  }));
  useEffect(() => {
    const invalidate = (event: Event) => {
      const path = (event as CustomEvent<string>).detail;
      if (/\/notifications\//.test(path)) void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      if (/transactions|market-data\/imports|\/imports\/|corporate-actions/.test(path)) {
        const keys = new Set(["valuation", "summary", "portfolio-dashboard", "transactions", "allocation", "performance", "instrument", "prices", "data-quality", "data-sources"]);
        void queryClient.invalidateQueries({ predicate: q => keys.has(String(q.queryKey[0])) });
      }
    };
    window.addEventListener("iip:data-changed", invalidate);
    return () => { window.removeEventListener("iip:data-changed", invalidate); queryClient.clear(); };
  }, [queryClient]);
  return <QueryClientProvider client={queryClient}>{children}<ToastRegion /></QueryClientProvider>;
}
