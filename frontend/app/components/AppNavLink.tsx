"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

function isActive(pathname: string, href: string, exact = false) {
  if (href === "/") return pathname === "/";
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppNavLink({
  href,
  children,
  className,
  activeClassName,
  inactiveClassName = "",
  exact = false,
}: {
  href: string;
  children: ReactNode;
  className?: string;
  activeClassName?: string;
  inactiveClassName?: string;
  exact?: boolean;
}) {
  const pathname = usePathname();
  const active = isActive(pathname, href, exact);
  const resolvedClassName = [className, active ? activeClassName : inactiveClassName].filter(Boolean).join(" ");
  return <Link href={href} className={resolvedClassName} aria-current={active ? "page" : undefined}>{children}</Link>;
}
