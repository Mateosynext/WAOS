"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function InboxKeyboardShortcuts({
  urls,
  currentIndex,
  openHref,
}: {
  urls: string[];
  currentIndex: number;
  openHref?: string | null;
}) {
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.getAttribute("contenteditable") === "true") return;
      if (event.key.toLowerCase() === "j" && urls.length) {
        event.preventDefault();
        router.push(urls[Math.min(currentIndex + 1, urls.length - 1)]);
      }
      if (event.key.toLowerCase() === "k" && urls.length) {
        event.preventDefault();
        router.push(urls[Math.max(currentIndex - 1, 0)]);
      }
      if (event.key.toLowerCase() === "o" && openHref) {
        event.preventDefault();
        router.push(openHref);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [currentIndex, openHref, router, urls]);

  return <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-xs text-slate-400">Shortcuts: <span className="mono-pill">J</span> siguiente · <span className="mono-pill">K</span> anterior · <span className="mono-pill">O</span> abrir hilo</div>;
}
