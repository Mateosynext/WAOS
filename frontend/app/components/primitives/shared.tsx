import type { ReactNode } from "react";

export type IconName =
  | "dashboard"
  | "briefcase"
  | "catalog"
  | "image"
  | "promo"
  | "bot"
  | "insights"
  | "sales"
  | "flow"
  | "calendar"
  | "channel"
  | "client"
  | "stack"
  | "chat"
  | "logs"
  | "rocket"
  | "clock"
  | "plug"
  | "shield"
  | "gear"
  | "usage"
  | "spark"
  | "check"
  | "alert"
  | "money"
  | "stats"
  | "play"
  | "target"
  | "wand"
  | "route"
  | "palette"
  | "layers"
  | "folder"
  | "tool"
  | "support"
  | "refresh";

export type UiTone = "slate" | "green" | "blue" | "gold" | "red" | "sky" | "amber";

export function toneClass(tone: string) {
  const tones: Record<string, string> = {
    slate: "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]",
    green: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]",
    blue: "border-[color:var(--info-border)] bg-[color:var(--info-soft)] text-[color:var(--info-text)]",
    gold: "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]",
    red: "border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] text-[color:var(--danger-text)]",
    sky: "border-[color:var(--info-border)] bg-[color:var(--info-soft)] text-[color:var(--info-text)]",
    amber: "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]",
  };
  return tones[tone] || tones.slate;
}

export function Icon({ name, className = "h-4 w-4" }: { name: IconName; className?: string }) {
  const shared = {
    className,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "dashboard": return <svg {...shared}><rect x="3" y="3" width="8" height="8" rx="2" /><rect x="13" y="3" width="8" height="5" rx="2" /><rect x="13" y="10" width="8" height="11" rx="2" /><rect x="3" y="13" width="8" height="8" rx="2" /></svg>;
    case "briefcase": return <svg {...shared}><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><rect x="3" y="7" width="18" height="13" rx="3" /><path d="M3 12h18" /></svg>;
    case "catalog": return <svg {...shared}><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 0-3 3z" /><path d="M5 4v16a3 3 0 0 1 3-3h11" /></svg>;
    case "image": return <svg {...shared}><rect x="3" y="4" width="18" height="16" rx="3" /><circle cx="9" cy="10" r="1.5" /><path d="m21 16-4.5-4.5a2 2 0 0 0-2.8 0L7 18" /></svg>;
    case "promo": return <svg {...shared}><path d="M20 12V8a2 2 0 0 0-2-2h-4l-2-3-2 3H6a2 2 0 0 0-2 2v4l-1.5 2L4 16v4a2 2 0 0 0 2 2h4l2 3 2-3h4a2 2 0 0 0 2-2v-4l1.5-2z" /><path d="M9 12h6" /></svg>;
    case "bot": return <svg {...shared}><rect x="6" y="8" width="12" height="10" rx="3" /><path d="M9 8V5a3 3 0 0 1 6 0v3" /><circle cx="10" cy="13" r="1" /><circle cx="14" cy="13" r="1" /><path d="M9 17h6" /></svg>;
    case "insights": return <svg {...shared}><path d="M4 19V5" /><path d="M20 19H4" /><rect x="7" y="11" width="3" height="6" rx="1" /><rect x="12" y="8" width="3" height="9" rx="1" /><rect x="17" y="5" width="3" height="12" rx="1" /></svg>;
    case "sales": return <svg {...shared}><path d="M12 2v20" /><path d="M17 6.5c0-1.7-2.2-3-5-3s-5 1.3-5 3 1.5 2.6 5 3 5 1.3 5 3-2.2 3-5 3-5-1.3-5-3" /></svg>;
    case "flow": return <svg {...shared}><circle cx="6" cy="6" r="2" /><circle cx="18" cy="6" r="2" /><circle cx="18" cy="18" r="2" /><path d="M8 6h8" /><path d="M18 8v8" /><path d="M16 18H8" /><path d="m8 18-2-2" /></svg>;
    case "calendar": return <svg {...shared}><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M8 3v4" /><path d="M16 3v4" /><path d="M3 10h18" /></svg>;
    case "channel": return <svg {...shared}><path d="M7 7h10" /><path d="M7 12h10" /><path d="M7 17h6" /><rect x="3" y="4" width="18" height="16" rx="3" /></svg>;
    case "client": return <svg {...shared}><rect x="7" y="2.5" width="10" height="19" rx="3" /><path d="M10 6h4" /><circle cx="12" cy="18" r="0.7" /></svg>;
    case "stack": return <svg {...shared}><path d="m12 3 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4" /><path d="m4 17 8 4 8-4" /></svg>;
    case "chat": return <svg {...shared}><path d="M7 18l-4 3V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3H7z" /><path d="M8 9h8" /><path d="M8 13h5" /></svg>;
    case "logs": return <svg {...shared}><path d="M8 6h12" /><path d="M8 12h12" /><path d="M8 18h12" /><path d="M4 6h.01" /><path d="M4 12h.01" /><path d="M4 18h.01" /></svg>;
    case "rocket": return <svg {...shared}><path d="M5 19c2.5-1 4-2.5 5-5" /><path d="M14 10 9 15" /><path d="m12 4 8 8" /><path d="M20 8c0-2-2-4-4-4-3 0-6 2-7 4l-2 5 5-2c2-1 4-4 4-7Z" /></svg>;
    case "clock": return <svg {...shared}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
    case "plug": return <svg {...shared}><path d="M9 8V3" /><path d="M15 8V3" /><path d="M8 8h8v3a4 4 0 0 1-4 4v6" /><path d="M8 8v3" /><path d="M16 8v3" /></svg>;
    case "shield": return <svg {...shared}><path d="M12 3 5 6v5c0 5 3.5 8.5 7 10 3.5-1.5 7-5 7-10V6l-7-3Z" /><path d="m9.5 12 1.7 1.7 3.8-3.8" /></svg>;
    case "gear": return <svg {...shared}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a2 2 0 1 1-4 0v-.2a1 1 0 0 0-.6-.9 1 1 0 0 0-1.1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a2 2 0 1 1 0-4h.2a1 1 0 0 0 .9-.6 1 1 0 0 0-.2-1.1l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4a2 2 0 1 1 4 0v.2a1 1 0 0 0 .6.9 1 1 0 0 0 1.1-.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6H20a2 2 0 1 1 0 4h-.2a1 1 0 0 0-.9.6Z" /></svg>;
    case "usage": return <svg {...shared}><path d="M12 3v18" /><path d="M6 8h8a3 3 0 0 1 0 6H10a3 3 0 0 0 0 6h8" /></svg>;
    case "spark": return <svg {...shared}><path d="m12 3 2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2L12 3Z" /></svg>;
    case "check": return <svg {...shared}><circle cx="12" cy="12" r="9" /><path d="m8.5 12.5 2.2 2.2 4.8-5" /></svg>;
    case "alert": return <svg {...shared}><path d="M12 3 2.5 19.5h19Z" /><path d="M12 9v4" /><path d="M12 16h.01" /></svg>;
    case "money": return <svg {...shared}><rect x="3" y="6" width="18" height="12" rx="3" /><circle cx="12" cy="12" r="2.5" /><path d="M7 12h.01" /><path d="M17 12h.01" /></svg>;
    case "stats": return <svg {...shared}><path d="M4 19h16" /><path d="m6 16 4-5 3 2 5-7" /><path d="M18 6h0" /></svg>;
    case "play": return <svg {...shared}><circle cx="12" cy="12" r="9" /><path d="m10 9 5 3-5 3z" /></svg>;
    case "target": return <svg {...shared}><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" /></svg>;
    case "wand": return <svg {...shared}><path d="m4 20 7-7" /><path d="m14 6 4-4" /><path d="m15 3 1 2" /><path d="m20 8 1 2" /><path d="M10 5l1.5 3.5L15 10l-3.5 1.5L10 15l-1.5-3.5L5 10l3.5-1.5L10 5Z" /></svg>;
    case "route": return <svg {...shared}><circle cx="6" cy="6" r="2" /><circle cx="18" cy="18" r="2" /><path d="M8 6h5a3 3 0 0 1 3 3v3" /><path d="m15 15 3 3" /><path d="M18 15v3h-3" /></svg>;
    case "palette": return <svg {...shared}><path d="M12 3a9 9 0 1 0 0 18h1.2a2.8 2.8 0 0 0 0-5.6H12a2 2 0 0 1 0-4h4a5 5 0 0 0 0-10Z" /><circle cx="7.5" cy="11" r="1" /><circle cx="9.5" cy="7.5" r="1" /><circle cx="14" cy="7" r="1" /></svg>;
    case "layers": return <svg {...shared}><path d="m12 4 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4" /><path d="m4 16 8 4 8-4" /></svg>;
    case "folder": return <svg {...shared}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z" /></svg>;
    case "tool": return <svg {...shared}><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17v3h3l5.3-5.3a4 4 0 0 0 5.4-5.4l-2.3 2.3-3-1 1-3z" /></svg>;
    case "support": return <svg {...shared}><path d="M12 17v.01" /><path d="M9.1 9a3 3 0 1 1 5.8 1c0 2-3 2-3 5" /><circle cx="12" cy="12" r="9" /></svg>;
    case "refresh": return <svg {...shared}><path d="M20 11a8 8 0 1 0 2 5.3" /><path d="M20 4v7h-7" /></svg>;
    default: return <svg {...shared}><circle cx="12" cy="12" r="9" /></svg>;
  }
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "amber" | "red" | "sky" | "gold" }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em] ${toneClass(tone)}`}>{children}</span>;
}

export function ThemeBadge({ label, tone = "slate" }: { label: string; tone?: "slate" | "green" | "gold" | "red" | "blue" | "sky" }) {
  return <Badge tone={tone === "blue" ? "sky" : tone}>{label}</Badge>;
}
