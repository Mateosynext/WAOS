import "./globals.css";
import type { ReactNode } from "react";
import AnalyticsTracker from "./components/AnalyticsTracker";
export const dynamic = "force-dynamic";
export const metadata = { title: "WAOS · Super admin y portal cliente", description: "WAOS ordena el trabajo de punta a punta: crear, conectar, gestionar y dar mantenimiento en modo super admin, con un portal cliente claro y sin lenguaje técnico." };
export default function RootLayout({ children }: { children: ReactNode }) { return <html lang="es"><body><AnalyticsTracker />{children}</body></html>; }
