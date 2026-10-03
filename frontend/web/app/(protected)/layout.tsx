import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { ProtectedShell } from "@/components/protected-shell";
import type { Session } from "@/lib/api";

export default async function ProtectedLayout({ children }: { children: ReactNode }) {
  const cookieName = process.env.SESSION_COOKIE_NAME ?? "investment_session";
  const token = (await cookies()).get(cookieName)?.value;
  if (!token) redirect("/login");

  let session: Session | null = null;
  try {
    const response = await fetch(`${process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000/api/v1"}/auth/session`, {
      headers: { Cookie: `${cookieName}=${token}` }, cache: "no-store",
    });
    if (response.ok) session = (await response.json()) as Session;
  } catch {
    // A missing API is treated as an unavailable session.
  }
  if (!session?.authenticated || !session.user) redirect("/login");
  return <ProtectedShell user={session.user}>{children}</ProtectedShell>;
}
