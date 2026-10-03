"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type LoginResult, type Session } from "@/lib/api";

export const sessionQueryKey = ["session"] as const;

export function getSession() {
  return api<Session>("/auth/session");
}

export function useSession() {
  return useQuery({ queryKey: sessionQueryKey, queryFn: getSession });
}

export function login(username: string, password: string) {
  return api<LoginResult>("/auth/login", {
    method: "POST", body: JSON.stringify({ username, password }),
  });
}

export function verifyTotp(challenge: string, code: string) {
  return api<{ status: "authenticated" }>("/auth/totp/verify", {
    method: "POST", body: JSON.stringify({ challenge, code }),
  });
}

export function logout() {
  return api<void>("/auth/logout", { method: "POST" });
}
