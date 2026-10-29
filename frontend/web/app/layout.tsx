import type { Metadata } from "next";
import type { ReactNode } from "react";
import { cookies, headers } from "next/headers";

import { ThemeProvider, type Theme } from "@/components/ui/theme-provider";
import { CspStyleNonce } from "@/components/ui/csp-style-nonce";
import "./globals.css";

export const metadata: Metadata = {
  title: "Investment Intelligence",
  description: "Private Investment Intelligence Platform",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const preference = (await cookies()).get("iip_theme")?.value;
  const theme: Theme = preference === "dark" || preference === "light" ? preference : "system";
  const nonce = (await headers()).get("x-nonce") ?? "";
  return (
    <html lang="de-CH" data-theme={theme}>
      <body className="min-h-screen antialiased">
        <CspStyleNonce nonce={nonce}>
          <ThemeProvider initial={theme}>{children}</ThemeProvider>
        </CspStyleNonce>
      </body>
    </html>
  );
}
