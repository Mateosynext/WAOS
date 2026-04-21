import Link from "next/link";
import AppNavLink from "../AppNavLink";
import { clientNavigation } from "./config";

export function SegmentedLinks({ items }: { items: Array<{ href: string; label: string; active?: boolean }> }) {
  return <div className="flex flex-wrap gap-2">{items.map((item) => <Link key={`${item.href}-${item.label}`} href={item.href} className={item.active ? "primary-btn" : "secondary-btn"}>{item.label}</Link>)}</div>;
}

export function PortalTabs() {
  return (
    <nav aria-label="Secciones del portal cliente" className="flex gap-2 overflow-x-auto pb-1">
      {clientNavigation.map((item) => (
        <AppNavLink
          key={item.href}
          href={item.href}
          className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-full border border-transparent px-4 py-2.5 text-sm font-medium text-[color:var(--text-secondary)] transition hover:border-[color:var(--accent-border)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--text-primary)]"
          activeClassName="inline-flex min-h-11 shrink-0 items-center justify-center rounded-full border border-[color:var(--accent-border)] bg-[color:var(--surface-strong)] px-4 py-2.5 text-sm font-semibold text-[color:var(--text-primary)] shadow-[var(--shadow-soft)]"
        >
          {item.label}
        </AppNavLink>
      ))}
    </nav>
  );
}

export function SecondaryNav({ items }: { items: Array<{ href: string; label: string; active?: boolean }> }) {
  return (
    <div className="flex flex-wrap gap-2 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-2">
      {items.map((item) => (
        <Link key={`${item.href}-${item.label}`} href={item.href} className={item.active ? "primary-btn" : "secondary-btn"}>
          {item.label}
        </Link>
      ))}
    </div>
  );
}
