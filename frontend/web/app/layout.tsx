import type { Metadata } from "next";
import type { ReactNode } from "react";
import { cookies } from "next/headers";

import { ThemeProvider, type Theme } from "@/components/ui/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Investment Intelligence",
  description: "Private Investment Intelligence Platform",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const preference = (await cookies()).get("iip_theme")?.value;
  const theme: Theme = preference === "dark" || preference === "light" ? preference : "system";
  return (
    <html lang="de-CH" data-theme={theme}>
      <body className="min-h-screen antialiased">
        <ThemeProvider initial={theme}>{children}</ThemeProvider>
      </body>
    </html>
  );
}
