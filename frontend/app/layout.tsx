import "./globals.css";
import type { ReactNode } from "react";
import AnalyticsTracker from "./components/AnalyticsTracker";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "WAOS · Operación clara para super admin y portal cliente",
  description:
    "WAOS ordena ventas, inbox, releases y portal cliente con una navegación clara, onboarding corto y lenguaje simple.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <a href="#main-content" className="skip-link">Saltar al contenido</a>
        <AnalyticsTracker />
        {children}
      </body>
    </html>
  );
}
