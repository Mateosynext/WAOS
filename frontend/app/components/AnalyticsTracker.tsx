"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { trackFrontendEvent } from "../lib/analytics";
import { hasAnalyticsConsent } from "../lib/legal-consent";

export default function AnalyticsTracker() {
  const pathname = usePathname();

  useEffect(() => {
    if (pathname && hasAnalyticsConsent()) trackFrontendEvent("page_view", pathname);
  }, [pathname]);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (!hasAnalyticsConsent()) return;
      const target = event.target as HTMLElement | null;
      const clickable = target?.closest("a.primary-btn,button.primary-btn,a.secondary-btn,button.secondary-btn") as HTMLElement | null;
      if (!clickable) return;
      const label = clickable.textContent?.trim() || clickable.getAttribute("aria-label") || clickable.getAttribute("href") || "cta";
      trackFrontendEvent("ui_click", window.location.pathname, label);
    }
    window.addEventListener("click", onClick);
    return () => window.removeEventListener("click", onClick);
  }, []);

  return null;
}
