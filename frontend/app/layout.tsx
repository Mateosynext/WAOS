import "./globals.css";
import type { ReactNode } from "react";
import { headers } from "next/headers";
import AnalyticsTracker from "./components/AnalyticsTracker";
import CookieConsentBanner from "./components/CookieConsentBanner";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "WAOS · Operación clara para super admin y portal cliente",
  description:
    "WAOS ordena ventas, inbox, releases y portal cliente con una navegación clara, onboarding corto y lenguaje simple.",
};

const themeInitScript = `
(function () {
  try {
    var key = 'waos-theme-preference';
    var saved = localStorage.getItem(key) || 'system';
    var systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var resolved = saved === 'system' ? (systemDark ? 'dark' : 'light') : saved;
    document.documentElement.dataset.themePreference = saved;
    document.documentElement.dataset.theme = resolved;
  } catch (error) {
    document.documentElement.dataset.themePreference = 'system';
    document.documentElement.dataset.theme = 'light';
  }
})();`;

export default async function RootLayout({ children }: { children: ReactNode }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <html lang="es" suppressHydrationWarning>
      <body>
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <a href="#main-content" className="skip-link">Saltar al contenido</a>
        <AnalyticsTracker />
        {children}
        <CookieConsentBanner />
      </body>
    </html>
  );
}
