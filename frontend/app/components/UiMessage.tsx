import { ReactNode } from "react";

type Tone = "info" | "success" | "warning" | "error";
const toneClass: Record<Tone, string> = {
  info: "border-sky-400/[0.20] bg-sky-400/[0.10] text-sky-50",
  success: "border-emerald-400/[0.20] bg-emerald-400/[0.10] text-emerald-50",
  warning: "border-amber-400/[0.20] bg-amber-400/[0.10] text-amber-50",
  error: "border-rose-400/[0.20] bg-rose-400/[0.10] text-rose-50",
};
export function UiMessage({ title, children, tone = "info" }: { title: string; children: ReactNode; tone?: Tone }) {
  return <div className={`rounded-3xl border p-4 text-sm ${toneClass[tone]}`}><div className="font-semibold text-white">{title}</div><div className="mt-2 leading-6 text-slate-100">{children}</div></div>;
}
export function FieldError({ message }: { message?: string | null }) { return message ? <div className="mt-1 text-xs font-medium text-rose-300">{message}</div> : null; }
