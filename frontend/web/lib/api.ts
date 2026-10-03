export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type User = { id: string; username: string; totp_enabled: boolean };
export type Session = { authenticated: boolean; user: User | null };
export type Settings = { timezone: string; base_currency: string };
export type LoginResult =
  | { status: "authenticated"; user: User }
  | { status: "totp_required"; challenge: string };

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.error?.code ?? "REQUEST_FAILED", body.error?.message ?? "Anfrage fehlgeschlagen");
  }
  return response.status === 204 ? (undefined as T) : (await response.json()) as T;
}
