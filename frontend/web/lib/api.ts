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

function explain(code: string, fallback: string, status: number): string {
  if (code === "REQUEST_KEY_CONFLICT") return "Diese Anfrage wurde bereits mit anderen Angaben verwendet. Zuerst die vorhandenen Portfolios oder Buchungen prüfen; eine Wiederholung darf keine zweite, abweichende Buchung anlegen.";
  if (code === "INVALID_CREDENTIALS") return "Benutzername oder Passwort ist nicht korrekt. Bitte prüfen und erneut versuchen.";
  if (code === "INVALID_TOTP") return "Der Bestätigungscode ist ungültig oder abgelaufen. Bitte einen aktuellen Code aus Ihrer Authenticator-App verwenden.";
  if (code === "DOCUMENT_REMOVED") return "Dieses Dokument wurde aus der aktiven Bibliothek entfernt. Frühere Auditbelege bleiben erhalten.";
  if (status === 401) return "Ihre Sitzung ist abgelaufen. Bitte erneut anmelden.";
  if (status === 403) return "Für diese Aktion fehlt die Berechtigung oder eine erforderliche Freigabe. Eine autorisierte Betreiberperson kann die Voraussetzungen prüfen.";
  if (/SOURCE|RIGHTS|GATE/.test(code)) return "Diese Datenquelle ist für den benötigten Zweck noch nicht freigegeben. Unter Datenquellen die Voraussetzungen prüfen oder eine eigene zulässige Datei importieren.";
  if (status === 429) return "Zu viele Anfragen. Bitte die angezeigte Wartezeit beachten und später erneut versuchen.";
  if (status >= 500) return "Der Dienst ist momentan nicht verfügbar. Ihre zuletzt gespeicherten Daten bleiben erhalten. Bitte später erneut versuchen.";
  return fallback;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init.headers },
  }); } catch { throw new ApiError(0, "NETWORK_UNAVAILABLE", "Keine Verbindung zum Dienst. Verbindung prüfen und erneut versuchen; ein Import wird nicht automatisch wiederholt."); }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const validation = Array.isArray(body.detail) ? body.detail.map((x: { loc?: string[]; msg?: string }) => `${x.loc?.slice(1).join(" / ") ?? "Eingabe"}: ${x.msg ?? "Bitte prüfen"}`).join("; ") : undefined;
    const code = body.error?.code ?? "REQUEST_FAILED";
    throw new ApiError(response.status, code, explain(code, body.error?.message ?? validation ?? "Die Anfrage konnte nicht abgeschlossen werden. Eingaben prüfen und erneut versuchen.", response.status));
  }
  if (typeof window !== "undefined" && init.method && !["GET", "HEAD"].includes(init.method.toUpperCase())) window.dispatchEvent(new CustomEvent("iip:data-changed", { detail: path }));
  return response.status === 204 ? (undefined as T) : (await response.json()) as T;
}
