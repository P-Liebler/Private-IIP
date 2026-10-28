import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const development = process.env.NODE_ENV === "development";
  const configuredApi = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";
  // Same-origin Core builds use /api/v1. A configured separate origin is also
  // needed by the existing local standalone acceptance environment.
  const apiOrigin = /^https?:\/\//.test(configuredApi) ? new URL(configuredApi).origin : "";
  const policy = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${development ? " 'unsafe-eval'" : ""}`,
    // Radix and chart placement use style attributes. This remaining allowance
    // is explicit; it never permits inline script execution.
    "style-src 'self' 'unsafe-inline'",
    `connect-src 'self' ${apiOrigin}${development ? " ws: wss:" : ""}`.trim(),
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'",
  ].join("; ");
  const headers = new Headers(request.headers);
  // Never trust client-supplied nonce/CSP headers.
  headers.set("x-nonce", nonce);
  headers.set("Content-Security-Policy", policy);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Content-Security-Policy", policy);
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export const config = {
  matcher: ["/((?!api/|_next/static|_next/image|favicon.ico).*)"],
};
