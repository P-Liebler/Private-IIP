"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { OperatorRole } from "@/lib/product-navigation";

export type Capabilities = Record<OperatorRole, boolean>;
const denied: Capabilities = { data_operator: false, ml_operator: false, operations_operator: false };
const Context = createContext<{ permissions: Capabilities; pending: boolean }>({ permissions: denied, pending: true });
export function CapabilitiesProvider({ userId, children }: { userId: string; children: ReactNode }) {
  const result = useQuery({ queryKey: ["capabilities", userId], queryFn: () => api<Capabilities>("/auth/capabilities"), retry: false });
  return <Context.Provider value={{ permissions: result.data ?? denied, pending: result.isPending }}>{children}</Context.Provider>;
}
export const useCapabilities = () => useContext(Context);
