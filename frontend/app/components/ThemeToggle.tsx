"use client";

import { useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "waos-theme-preference";

type ThemePreference = "system" | "light" | "dark";

function resolveTheme(preference: ThemePreference) {
  if (preference === "system") {
    if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) return "dark";
    return "light";
  }
  return preference;
}

function applyTheme(preference: ThemePreference) {
  const root = document.documentElement;
  const resolved = resolveTheme(preference);
  root.dataset.themePreference = preference;
  root.dataset.theme = resolved;
}

export default function ThemeToggle() {
  const [preference, setPreference] = useState<ThemePreference>("system");

  useEffect(() => {
    const saved = (window.localStorage.getItem(STORAGE_KEY) as ThemePreference | null) || "system";
    setPreference(saved);
    applyTheme(saved);

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => {
      const current = (window.localStorage.getItem(STORAGE_KEY) as ThemePreference | null) || "system";
      if (current === "system") applyTheme("system");
    };
    media.addEventListener?.("change", listener);
    return () => media.removeEventListener?.("change", listener);
  }, []);

  const options = useMemo(
    () => [
      { value: "system" as const, label: "Auto" },
      { value: "light" as const, label: "Claro" },
      { value: "dark" as const, label: "Oscuro" },
    ],
    [],
  );

  function updatePreference(next: ThemePreference) {
    setPreference(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  }

  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-1 shadow-[var(--shadow-soft)]" role="group" aria-label="Cambiar tema">
      {options.map((option) => {
        const active = option.value === preference;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => updatePreference(option.value)}
            aria-pressed={active}
            className={[
              "min-h-10 rounded-full px-3 text-xs font-semibold tracking-[0.14em] transition sm:px-3.5",
              active
                ? "bg-[color:var(--surface-elevated)] text-[color:var(--text-primary)] shadow-[var(--shadow-soft)]"
                : "text-[color:var(--text-secondary)] hover:bg-[color:var(--surface-elevated)]/70 hover:text-[color:var(--text-primary)]",
            ].join(" ")}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
